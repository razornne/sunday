import os
import json
import smtplib
import requests
import google.generativeai as genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
import markdown

# Загружаем настройки
load_dotenv()

# --- 1. КОНФИГУРАЦИЯ ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Настройки почты для отправки отчетов
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")

# Инициализация клиентов
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_KEY)

# --- 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def send_email_report(to_email, subject, html_body):
    """Отправляет готовый дайджест на почту юзера"""
    if not EMAIL_USER or not EMAIL_PASS:
        print("⚠️ Ошибка: Данные почты (SMTP) не настроены.")
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
        print(f"❌ Ошибка SMTP: {e}")
        return False

def get_ai_synthesis(emails_text, profile):
    """Генерирует дайджест через Gemini"""
    model = genai.GenerativeModel("gemini-2.5-pro")
    
    prompt = f"""
    Твоя роль: {profile.get('role', 'Аналитик')}. 
    Твои интересы: {profile.get('focus_areas')}.
    
    ЗАДАЧА: Сделай краткий и ценный обзор следующих писем.
    Верни строго JSON:
    {{
      "big_picture": "одно предложение о главном за неделю",
      "trends": [
        {{"title": "заголовок тренда", "insight": "почему это важно для этой роли"}}
      ],
      "noise_filter": "что ты проигнорировал (реклама, спам)"
    }}

    ПИСЬМА:
    {emails_text}
    """
    
    try:
        response = model.generate_content(prompt)
        # Очистка от markdown-обертки JSON
        clean_json = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        return None

# --- 3. ОСНОВНОЙ ПРОЦЕСС ---

def main():
    # Определяем текущий момент (в UTC)
    now = datetime.utcnow()
    current_day = now.strftime("%A")
    current_hour = now.strftime("%H:00")
    
    print(f"⏰ Проверка расписания: {current_day} {current_hour} UTC")

    # 1. Находим пользователей, которым пора отправлять отчет именно сейчас
    users_res = supabase.table("profiles")\
        .select("*")\
        .eq("digest_day", current_day)\
        .eq("digest_time", current_hour)\
        .execute()
    
    active_users = users_res.data
    if not active_users:
        print("💤 Для этого часа запланированных отчетов нет.")
        return

    print(f"✅ Найдено пользователей для обработки: {len(active_users)}")

    for user in active_users:
        uid = user['id']
        email_addr = user['email']
        
        # 2. Собираем новые письма именно этого пользователя
        emails_res = supabase.table("raw_emails")\
            .select("*")\
            .eq("user_id", uid)\
            .eq("processed", False)\
            .execute()
        
        new_emails = emails_res.data
        if not new_emails:
            print(f"📪 У {email_addr} нет новых писем. Пропускаем.")
            continue

        print(f"📧 Обработка {len(new_emails)} писем для {email_addr}...")

        # Формируем контекст для AI
        context = ""
        email_ids = []
        for e in new_emails:
            context += f"От: {e['sender']}\nТема: {e['subject']}\nТекст: {e['body_plain'][:2000]}\n---\n"
            email_ids.append(e['id'])

        # 3. Генерируем дайджест
        synthesis = get_ai_synthesis(context, user)
        if not synthesis:
            continue

        # 4. Сохраняем и отправляем
        digest_obj = {
            "user_id": uid,
            "structured_content": synthesis,
            "source_email_ids": email_ids,
            "subject": f"Sunday Brief: {synthesis['big_picture'][:50]}..."
        }
        
        supabase.table("digests").insert(digest_obj).execute()

        # HTML-письмо (дизайн совпадает с дашбордом)
        html_report = f"""
        <div style="font-family: sans-serif; color: #333; max-width: 600px;">
            <h2 style="color: #2e86de;">☀️ Ваш Sunday Brief</h2>
            <div style="background: #f0f7ff; padding: 15px; border-radius: 8px; border-left: 4px solid #2e86de;">
                <strong>Общая картина:</strong><br>{synthesis['big_picture']}
            </div>
            <h3>Главные инсайты:</h3>
            {''.join([f"<b>{t['title']}</b><p>{t['insight']}</p>" for t in synthesis['trends']])}
            <hr>
            <p style="font-size: 11px; color: #999;">Отфильтрованный шум: {synthesis['noise_filter']}</p>
        </div>
        """
        
        if send_email_report(email_addr, digest_obj['subject'], html_report):
            # 5. Помечаем письма как обработанные
            for eid in email_ids:
                supabase.table("raw_emails").update({"processed": True}).eq("id", eid).execute()
            print(f"🚀 Дайджест для {email_addr} успешно отправлен!")

if __name__ == "__main__":
    main()