import os
import json
import smtplib
import requests
# Используем новый стандарт импорта, чтобы убрать предупреждение
import google.generativeai as genai 
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
import markdown

load_dotenv()

# --- 1. КОНФИГУРАЦИЯ ---
# Используем secrets для GitHub Actions или .env для локалки
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_KEY)

# --- 2. ФУНКЦИИ ---

def send_email_report(to_email, subject, html_body):
    if not EMAIL_USER or not EMAIL_PASS:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Sunday AI <{EMAIL_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))
        with smtplib.SMTP(SMTP_SERVER, 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"❌ SMTP Error: {e}")
        return False

def get_ai_synthesis(emails_text, profile):
    # Используем flash-модель для скорости и экономии
    model = genai.GenerativeModel("gemini-2.5-pro")
    prompt = f"""
    Role: {profile.get('role', 'User')}. Focus: {profile.get('focus_areas')}.
    Summarize these emails into JSON:
    {{
      "big_picture": "summary",
      "trends": [{{"title": "...", "insight": "..."}}],
      "noise_filter": "..."
    }}
    Emails: {emails_text}
    """
    try:
        response = model.generate_content(prompt)
        # Очистка от лишних символов
        text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(text)
    except: return None

# --- 3. MAIN ---

def main():
    # Работаем строго с UTC временем
    now = datetime.utcnow()
    current_day = now.strftime("%A") 
    current_hour = now.strftime("%H:00")
    
    print(f"⏰ Скрипт запущен: {current_day}, {current_hour} UTC")

    # ЗАПРОС К БАЗЕ: Теперь мы уверены, что digest_day — это text
    try:
        users_res = supabase.table("profiles")\
            .select("*")\
            .eq("digest_day", current_day)\
            .execute()
    except Exception as e:
        print(f"❌ Ошибка запроса к базе: {e}")
        return

    active_users = users_res.data
    if not active_users:
        print("💤 Нет запланированных отчетов на этот день.")
        return

    for user in active_users:
        # Проверяем время (отсекаем секунды если они есть в базе)
        user_time = user.get('digest_time', '09:00')[:5]
        if user_time != current_hour[:5]:
            continue

        uid = user['id']
        print(f"🧠 Обработка дайджеста для {user['email']}...")

        emails_res = supabase.table("raw_emails")\
            .select("*")\
            .eq("user_id", uid)\
            .eq("processed", False)\
            .execute()

        if not emails_res.data:
            print(f"📪 Новых писем нет.")
            continue

        # Сбор данных
        context = ""
        email_ids = []
        for e in emails_res.data:
            context += f"Subj: {e['subject']}\nText: {e['body_plain'][:1500]}\n---\n"
            email_ids.append(e['id'])

        synthesis = get_ai_synthesis(context, user)
        if synthesis:
            # Сохраняем в базу
            digest_obj = {
                "user_id": uid,
                "structured_content": synthesis,
                "source_email_ids": email_ids,
                "subject": f"Sunday Brief: {synthesis['big_picture'][:40]}..."
            }
            supabase.table("digests").insert(digest_obj).execute()

            # Отправка
            html = f"<h2>Ваш отчет</h2><p>{synthesis['big_picture']}</p>"
            if send_email_report(user['email'], digest_obj['subject'], html):
                # Помечаем письма обработанными
                for eid in email_ids:
                    supabase.table("raw_emails").update({"processed": True}).eq("id", eid).execute()
                print(f"✅ Отправлено!")

if __name__ == "__main__":
    main()