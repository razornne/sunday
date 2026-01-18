import os
import json
import smtplib
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google import genai
from supabase import create_client, Client
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Загрузка переменных окружения
load_dotenv()

# --- ИНИЦИАЛИЗАЦИЯ КЛИЕНТОВ ---
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"), 
    os.environ.get("SUPABASE_KEY")
)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def log_event(user_id, status, emails_count=0, error_msg=None):
    """Запись логов"""
    try:
        supabase.table("run_logs").insert({
            "user_id": user_id,
            "status": status,
            "emails_processed": emails_count,
            "error_message": error_msg
        }).execute()
    except Exception as e:
        print(f"   ⚠️ Ошибка записи лога: {e}")

def send_email(to_email, subject, html_body):
    """Отправка HTML-письма"""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Sunday AI <{os.environ.get('EMAIL_USER')}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(os.environ.get("SMTP_SERVER", "smtp.gmail.com"), 587) as server:
            server.starttls()
            server.login(os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASS"))
            server.sendmail(os.environ.get("EMAIL_USER"), to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"   ❌ SMTP Error: {e}")
        return False

def get_ai_synthesis(emails_text, profile):
    """Генерация через Gemini"""
    role = profile.get('role', 'Professional')
    focus = ", ".join(profile.get('focus_areas', []) or []) # Защита от None
    
    prompt = f"""
    ROLE: You are an Elite AI Chief of Staff. 
    CLIENT: A "{role}" focused on: {focus}.

    TASK: Synthesize these emails into a high-signal "Sunday Brief". 
    
    OUTPUT JSON:
    {{
      "big_picture": "Summary of the week in 2-3 sentences.",
      "trends": [
        {{ "title": "Topic Name", "insight": "Analysis..." }}
      ],
      "action_items": ["Task 1", "Task 2"],
      "noise_filter": "Summary of filtered emails."
    }}

    EMAILS:
    {emails_text}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", # Используем быструю модель (или 1.5-pro)
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'temperature': 0.2
            }
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"   ❌ AI Synthesis Error: {e}")
        return None

def get_html_template(synthesis):
    """HTML шаблон (сокращен для экономии места, логика та же)"""
    trends_html = "".join([f"""
        <div style="margin-bottom: 24px; padding: 20px; border-radius: 12px; border: 1px solid #eef2f6; background-color: #ffffff;">
            <h3 style="margin: 0 0 10px 0; color: #1a73e8; font-size: 18px;">{t['title']}</h3>
            <div style="color: #3c4043; font-size: 15px;">{t['insight']}</div>
        </div>
    """ for t in synthesis.get('trends', [])])

    actions_list = "".join([f"<li>{item}</li>" for item in synthesis.get('action_items', [])])
    
    return f"""
    <div style="font-family: sans-serif; background-color: #f4f7f9; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; border-radius: 12px; padding: 30px;">
            <h1 style="color: #1a73e8;">Sunday Brief</h1>
            <p style="font-size: 18px;">{synthesis.get('big_picture')}</p>
            <hr>
            {trends_html}
            <h3>⚠️ Actions</h3>
            <ul>{actions_list}</ul>
        </div>
    </div>
    """

def main():
    now = datetime.utcnow()
    # ДЛЯ ТЕСТОВ: Если хочешь запустить принудительно, закомментируй проверку времени ниже
    cur_day, cur_hour = now.strftime("%A"), now.strftime("%H:00")
    print(f"🚀 Sunday AI Run | {cur_day} {cur_hour} UTC")

    # 1. Берем пользователей (убедись, что колонки digest_day существуют, или убери фильтр для теста)
    users = supabase.table("profiles").select("*").execute()
    
    if not users.data:
        print("💤 Нет пользователей.")
        return

    for user in users.data:
        # Проверка времени (раскомментируй для продакшена)
        # if user.get('digest_day') != cur_day: continue
        
        # ВАЖНО: Используем personal_email, так как ты чистил таблицу
        email_addr = user.get('personal_email')
        if not email_addr:
            print(f"⚠️ У пользователя {user['id']} нет email, пропускаем.")
            continue

        print(f"👤 Обработка: {email_addr}")
        
        # 2. Ищем новые письма
        emails_query = supabase.table("raw_emails") \
            .select("*") \
            .eq("user_id", user['id']) \
            .eq("processed", False) \
            .execute()
        
        if not emails_query.data:
            print("   📪 Новых писем нет.")
            continue

        print(f"   📨 Писем: {len(emails_query.data)}")
        
        email_context = ""
        for e in emails_query.data:
            email_context += f"FROM: {e['sender']}\nSUBJ: {e['subject']}\nBODY: {e['body_plain'][:1000]}\n---\n"

        # 3. Генерация
        synthesis = get_ai_synthesis(email_context, user)
        
        if synthesis and "big_picture" in synthesis:
            html_email = get_html_template(synthesis)
            subject = f"Sunday Brief: {synthesis['big_picture'][:50]}..."
            
            # 4. Отправка
            if send_email(email_addr, subject, html_email):
                
                # --- ИСПРАВЛЕННАЯ ВСТАВКА В БАЗУ ---
                try:
                    supabase.table("digests").insert({
                        "user_id": user['id'],
                        "user_email": email_addr, # <--- ВАЖНО: Добавили email (он теперь required)
                        "summary_text": synthesis.get('big_picture'), # <--- ВАЖНО: Заполняем колонку
                        "structured_content": synthesis.get('trends', []), # Сохраняем только тренды или весь json
                        "is_sent": True, # <--- ВАЖНО: Ставим галочку
                        "period_start": (now - timedelta(days=7)).isoformat(),
                        "period_end": now.isoformat()
                    }).execute()
                    
                    # Помечаем письма как обработанные
                    for e in emails_query.data:
                        supabase.table("raw_emails").update({"processed": True}).eq("id", e['id']).execute()
                    
                    log_event(user['id'], "success", len(emails_query.data))
                    print("   ✅ Успех!")
                except Exception as db_err:
                    print(f"   ⚠️ Ошибка базы данных: {db_err}")
            else:
                log_event(user['id'], "error", error_msg="SMTP Fail")
        else:
            print("   ❌ ИИ вернул пустой ответ")

if __name__ == "__main__":
    main()