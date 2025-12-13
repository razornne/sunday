import imaplib
import email
from email.header import decode_header
import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from supabase import create_client, Client

load_dotenv()

# Настройки
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
IMAP_SERVER = os.environ.get("IMAP_SERVER")

# Фильтры
ALLOWED_SENDERS = [
    "newsletters@hi.wellfound.com",
    "blog@tomtunguz.com",
    "datadrivenvc@newsletter.datadrivenvc.io"
    "updates@schwarzenegger.com"
]
DATE_SINCE = "01-Dec-2025"

def aggressive_clean_html(html_content):
    """Жесткая очистка HTML для экономии токенов"""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 1. Удаляем технический мусор
    for element in soup(["script", "style", "head", "title", "meta", "noscript", "iframe", "svg"]):
        element.extract()
        
    # 2. Удаляем структурный мусор (хедеры, футеры, меню)
    # Многие письма используют div class="footer" или тег <footer>
    for element in soup.find_all(attrs={"class": re.compile(r"footer|header|nav|menu|copyright|social", re.I)}):
        element.extract()
    for element in soup(["footer", "header", "nav", "aside"]):
        element.extract()

    # 3. Достаем текст с разделителями
    text = soup.get_text(separator=" ")
    
    # 4. Удаляем лишние пробелы и пустые строки (Regex)
    # Заменяем любые последовательности пробелов/табов/энтеров на один пробел
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 5. Удаляем фразы-паразиты (Unsubscribe и т.д.)
    # Просто обрезаем текст, если встречаем типичные футерные фразы
    stop_phrases = ["Unsubscribe", "Manage your preferences", "View in browser", "Посмотреть в браузере", "Отписаться"]
    for phrase in stop_phrases:
        if phrase in text:
            # Иногда это вырезает лишнее, но для экономии токенов риск оправдан
            # Можно сделать split и взять первую часть, но безопаснее просто удалить саму фразу и 100 символов после
            pass 

    return text

def connect_to_mail():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        return mail
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        exit()

def fetch_emails():
    print(f"🔌 Подключаюсь к почте (фильтр: с {DATE_SINCE})...")
    mail = connect_to_mail()
    mail.select("inbox")
    
    found_count = 0

    for sender_email in ALLOWED_SENDERS:
        print(f"🔎 Отправитель: {sender_email}...")
        try:
            search_criteria = f'(UNSEEN FROM "{sender_email}" SINCE "{DATE_SINCE}")'
            status, messages = mail.search(None, search_criteria)
        except Exception as e:
            continue
            
        email_ids = messages[0].split()
        if not email_ids: continue

        print(f"   Найдено: {len(email_ids)}")

        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        subject = "No Subject"
                        if msg["Subject"]:
                            h = decode_header(msg["Subject"])[0]
                            subject = h[0].decode(h[1] or "utf-8") if isinstance(h[0], bytes) else h[0]
                        
                        real_sender = msg.get("From")
                        
                        # Извлекаем контент
                        body_content = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/html":
                                    try:
                                        body_content = part.get_payload(decode=True).decode(errors="ignore")
                                        break # Нашли HTML - выходим, он приоритетнее
                                    except: pass
                                elif part.get_content_type() == "text/plain" and not body_content:
                                    try:
                                        body_content = part.get_payload(decode=True).decode(errors="ignore")
                                    except: pass
                        else:
                            try:
                                body_content = msg.get_payload(decode=True).decode(errors="ignore")
                            except: pass

                        # Чистим!
                        clean_text = aggressive_clean_html(body_content)
                        
                        # Если текст всё еще огромный (>15000 символов), обрезаем его жестко
                        # Это защита от гигантских лонгридов
                        if len(clean_text) > 15000:
                            clean_text = clean_text[:15000] + "..."

                        if not clean_text: continue

                        data = {
                            "sender": real_sender,
                            "subject": subject,
                            "body_text": clean_text,
                            "raw_html": body_content, # Оставляем оригинал на всякий случай
                            "is_processed": False 
                        }
                        
                        # Используем upsert или просто insert (Supabase ID разрулит)
                        supabase.table("raw_emails").insert(data).execute()
                        found_count += 1
                        print(f"   ✅ Сохранено: {subject[:30]}... ({len(clean_text)} chars)")

            except Exception as e:
                print(f"   Error: {e}")

    mail.close()
    mail.logout()
    print(f"🏁 Всего сохранено: {found_count}")

if __name__ == "__main__":
    fetch_emails()