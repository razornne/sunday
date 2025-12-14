import os
import json
import smtplib
import requests
import google.generativeai as genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client
from dotenv import load_dotenv
from email.utils import parseaddr
import markdown

load_dotenv()

# --- КОНФИГУРАЦИЯ ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Настройки доставки
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# --- ФУНКЦИИ ОТПРАВКИ ---

def send_telegram_alert(chat_id, text):
    """Отправляет сообщение в Telegram"""
    if not chat_id or not TG_TOKEN:
        print("⚠️ Telegram token or Chat ID missing. Skipping TG.")
        return False
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown" # Чтобы работала жирность и ссылки
    }
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            print(f"✈️ Telegram sent to {chat_id}")
            return True
        else:
            print(f"❌ Telegram Error: {r.text}")
    except Exception as e:
        print(f"❌ Telegram Exception: {e}")
    return False

def send_email_digest(to_email, subject, markdown_body):
    """Отправляет дайджест на почту"""
    if not to_email or not EMAIL_USER:
        print("⚠️ Email creds missing. Skipping Email.")
        return False

    try:
        # Превращаем Markdown в красивый HTML
        html_content = markdown.markdown(markdown_body)
        
        # Оборачиваем в простой шаблон
        full_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2e86de;">☀️ Sunday Digest: {subject}</h2>
            <hr>
            {html_content}
            <hr>
            <p style="font-size: 12px; color: #777;">Создано AI специально для вас.</p>
        </body>
        </html>
        """

        msg = MIMEMultipart()
        msg['From'] = f"Sunday AI <{EMAIL_USER}>"
        msg['To'] = to_email
        msg['Subject'] = f"☀️ Digest: {subject}"
        msg.attach(MIMEText(full_html, 'html'))

        # Отправка через Gmail SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
        
        print(f"📧 Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email Sending Error: {e}")
        return False

# --- ОСНОВНАЯ ЛОГИКА ---

def generate_summary(text):
    model = genai.GenerativeModel("models/gemini-2.5-pro")

    safe_text = text[:20000] if text else "No text"
    
    prompt = f"""
    Ты - личный ассистент. Сделай выжимку из текста письма.
    Текст: {safe_text} 
    
    Верни JSON:
    1. "summary_text": Подробный, структурированный пересказ (Markdown). Используй заголовки и списки.
    2. "telegram_text": Короткий тизер для мессенджера (макс 500 знаков). Начни с яркого эмодзи, отражающего суть. В конце добавь призыв "Проверь почту для деталей".
    
    Верни ТОЛЬКО JSON.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        return None

def main():
    print("🚀 Starting Omni-Channel Summarizer...")

    # 1. ЗАГРУЖАЕМ ПОДПИСКИ И ПРОФИЛИ
    # Нам нужно достать telegram_chat_id и email пользователя из таблицы profiles
    print("📋 Loading subscriptions & profiles...")
    try:
        # Забираем активные подписки и сразу данные профиля (через join user_id)
        # В Supabase-py join делается сложно, поэтому сделаем два запроса для надежности
        
        all_subs = supabase.table("subscriptions").select("*").execute().data
        
        # Собираем уникальные user_id
        user_ids_list = list(set([s['user_id'] for s in all_subs if s.get('user_id')]))
        
        # Загружаем профили этих юзеров
        if user_ids_list:
            profiles_resp = supabase.table("profiles").select("id, email, telegram_chat_id").in_("id", user_ids_list).execute()
            profiles_map = {p['id']: p for p in profiles_resp.data}
        else:
            profiles_map = {}

        # Строим карту: Email отправителя -> Список получателей (их данные)
        subs_map = {}
        for s in all_subs:
            if not s.get('user_id'): continue
            if s.get('is_active') is False: continue # Пропускаем выключенные

            email_key = s['sender_email'].strip().lower()
            if email_key not in subs_map:
                subs_map[email_key] = []
            
            # Добавляем полные данные юзера в список
            user_data = profiles_map.get(s['user_id'])
            if user_data:
                subs_map[email_key].append(user_data)
            
        print(f"✅ Config loaded. Rules count: {len(subs_map)}")

    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return

    # 2. ИЩЕМ ПИСЬМА
    response = supabase.table("raw_emails").select("*").eq("processed", False).execute()
    emails = response.data

    if not emails:
        print("💤 No new emails.")
        return

    print(f"📨 Found {len(emails)} new emails.")

    for email_obj in emails:
        # Парсим отправителя
        raw_sender = email_obj.get('sender', '')
        name, clean_email = parseaddr(raw_sender)
        final_sender = clean_email.strip().lower() if clean_email else raw_sender.lower()
        
        print(f"Processing letter from: '{final_sender}'")

        recipients = subs_map.get(final_sender)

        if not recipients:
            print(f"❌ Not in whitelist. Marking as processed.")
            supabase.table("raw_emails").update({"processed": True}).eq("id", email_obj['id']).execute()
            continue
        
        print(f"✅ Sending to {len(recipients)} recipients...")

        # Генерируем AI
        content = email_obj.get('body_plain') or email_obj.get('body_html') or ""
        ai_raw = generate_summary(content)
        
        if not ai_raw:
            print("⚠️ AI generation failed.")
            continue
            
        cleaned_json = ai_raw.replace("```json", "").replace("```", "").strip()
        try:
            ai_data = json.loads(cleaned_json)
        except:
            print(f"⚠️ JSON Parse Error.")
            continue

        # 3. РАССЫЛКА И СОХРАНЕНИЕ
        for user in recipients:
            uid = user['id']
            tg_id = user.get('telegram_chat_id')
            user_email = user.get('email')
            
            # А. Сохраняем в базу (для Сайта)
            digest_data = {
                "raw_email_id": email_obj['id'],
                "subject": email_obj.get('subject'),
                "summary_text": ai_data.get('summary_text', 'Error'),
                "telegram_text": ai_data.get('telegram_text', 'Error'),
                "is_sent": True # Сразу ставим True, так как сейчас отправим
            }
            try:
                supabase.table("digests").insert(digest_data).execute()
                print(f"   💾 Saved to DB for {user_email}")
            except Exception as e:
                print(f"   ❌ DB Save error: {e}")

            # Б. Отправляем в Telegram
            if tg_id:
                tg_msg = f"{ai_data.get('telegram_text')}\n\n🔗 [Читать на сайте](https://sunday-digest.streamlit.app)"
                send_telegram_alert(tg_id, tg_msg)
            
            # В. Отправляем на Email
            if user_email:
                send_email_digest(user_email, email_obj.get('subject'), ai_data.get('summary_text'))

        # Помечаем письмо обработанным
        supabase.table("raw_emails").update({"processed": True}).eq("id", email_obj['id']).execute()

if __name__ == "__main__":
    main()