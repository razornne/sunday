import imaplib
import email
from email.header import decode_header
import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from supabase import create_client, Client

load_dotenv()

# --- НАСТРОЙКИ ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
IMAP_SERVER = "imap.gmail.com" # Обычно это для Gmail, если другой - поменяй в .env

# Дата, с которой начинаем сканировать (формат: DD-Mon-YYYY)
DATE_SINCE = "01-Dec-2025" 

def get_allowed_senders():
    """Берем список активных подписок из базы данных"""
    try:
        response = supabase.table("subscriptions").select("sender_email").eq("is_active", True).execute()
        # Превращаем [{'sender_email': 'a@b.com'}, ...] в ['a@b.com', ...]
        senders = [item['sender_email'] for item in response.data]
        print(f"📋 Загружено {len(senders)} подписок из базы данных.")
        return senders
    except Exception as e:
        print(f"❌ Ошибка получения подписок: {e}")
        return []

def aggressive_clean_html(html_content):
    """Жесткая очистка HTML для экономии токенов"""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 1. Удаляем технический мусор
    for element in soup(["script", "style", "head", "title", "meta", "noscript", "iframe", "svg"]):
        element.extract()
        
    # 2. Удаляем структурный мусор (хедеры, футеры)
    for element in soup.find_all(attrs={"class": re.compile(r"footer|header|nav|menu|copyright|social", re.I)}):
        element.extract()
    for element in soup(["footer", "header", "nav", "aside"]):
        element.extract()

    # 3. Достаем текст
    text = soup.get_text(separator=" ")
    
    # 4. Чистим пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 5. Удаляем фразы-паразиты
    stop_phrases = ["Unsubscribe", "Manage your preferences", "View in browser", "Посмотреть в браузере", "Отписаться"]
    for phrase in stop_phrases:
        if phrase in text:
            # Можно просто вырезать фразу, или обрезать текст после нее
            pass 

    return text

def connect_to_mail():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        return mail
    except Exception as e:
        print(f"❌ Ошибка подключения к IMAP: {e}")
        exit()

def fetch_emails():
    # 1. Получаем список от кого искать
    allowed_senders = get_allowed_senders()
    if not allowed_senders:
        print("⚠️ Нет активных подписок в базе. Скрипт остановлен.")
        return

    print(f"🔌 Подключаюсь к почте {EMAIL_USER} (с {DATE_SINCE})...")
    mail = connect_to_mail()
    mail.select("inbox")
    
    found_count = 0

    for sender_email in allowed_senders:
        print(f"🔎 Ищем письма от: {sender_email}...")
        try:
            # Поиск писем от конкретного отправителя с даты X
            search_criteria = f'(FROM "{sender_email}" SINCE "{DATE_SINCE}")'
            status, messages = mail.search(None, search_criteria)
        except Exception as e:
            print(f"   Ошибка поиска для {sender_email}: {e}")
            continue
            
        email_ids = messages[0].split()
        if not email_ids: 
            print("   Ничего не найдено.")
            continue

        print(f"   Найдено писем: {len(email_ids)}")

        for email_id in email_ids:
            try:
                # Скачиваем письмо
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # --- Декодируем тему ---
                        subject = "No Subject"
                        if msg["Subject"]:
                            h = decode_header(msg["Subject"])[0]
                            subject = h[0].decode(h[1] or "utf-8") if isinstance(h[0], bytes) else h[0]
                        
                        # --- От кого ---
                        real_sender = msg.get("From")
                        # Иногда sender приходит как "Name <email>". Нам бы по-хорошему чистый email, 
                        # но пока оставим как есть, summarize.py разберется.
                        
                        # --- Извлекаем тело ---
                        body_content = ""
                        html_content = "" # Сохраним оригинал HTML отдельно
                        
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))
                                
                                # Пропускаем вложения
                                if "attachment" in content_disposition:
                                    continue

                                try:
                                    payload = part.get_payload(decode=True).decode(errors="ignore")
                                except:
                                    continue

                                if content_type == "text/html":
                                    html_content = payload
                                    body_content = payload # Приоритет HTML для парсинга
                                elif content_type == "text/plain" and not body_content:
                                    body_content = payload
                        else:
                            # Не мультипарт (обычно простой текст)
                            try:
                                payload = msg.get_payload(decode=True).decode(errors="ignore")
                                body_content = payload
                                if msg.get_content_type() == "text/html":
                                    html_content = payload
                            except: pass

                        # --- Очистка и подготовка ---
                        clean_text = aggressive_clean_html(body_content)
                        
                        if len(clean_text) > 20000:
                            clean_text = clean_text[:20000] + "..."

                        if not clean_text: 
                            continue

                        # --- Сохранение в Supabase ---
                        data = {
                            "sender": real_sender, # Или sender_email из цикла, если хотим точно
                            "recipient": EMAIL_USER,
                            "subject": subject,
                            "body_plain": clean_text,
                            "body_html": html_content if html_content else body_content,
                            "processed": False 
                        }
                        
                        # Вставляем данные. Используем insert.
                        # Если хотим избежать дубликатов, в будущем можно проверять по связке (sender + subject + date)
                        supabase.table("raw_emails").insert(data).execute()
                        found_count += 1
                        print(f"   ✅ Сохранено: {subject[:40]}...")

            except Exception as e:
                print(f"   ❌ Ошибка обработки письма ID {email_id}: {e}")

    mail.close()
    mail.logout()
    print(f"\n🏁 Готово! Всего сохранено в базу: {found_count} писем.")

if __name__ == "__main__":
    fetch_emails()