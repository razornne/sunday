import os
import json
import smtplib
from datetime import datetime
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

def send_email(to_email, subject, html_body):
    """Отправка письма через SMTP"""
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
    """Генерация аналитики через Gemini 1.5 Flash"""
    role = profile.get('role', 'Professional')
    focus = ", ".join(profile.get('focus_areas', []))
    
    prompt = f"""
    ROLE: Elite Strategy Consultant for a "{role}".
    THEIR FOCUS: {focus}.
    TASK: Synthesize these emails into a JSON "Sunday Brief".
    
    OUTPUT STRUCTURE (Strict JSON):
    {{
      "big_picture": "Summary of the week in 2 sentences.",
      "trends": [
        {{ "title": "Topic with Emoji", "insight": "Strategic analysis (use **bold** for keywords)" }}
      ],
      "noise_filter": "What fluff was ignored."
    }}

    EMAIL DATA:
    {emails_text}
    """
    
    try:
        # Используем словарь для конфига, чтобы избежать ошибок импорта types
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'temperature': 0.1
            }
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"   ❌ AI Synthesis Error: {e}")
        return None

def get_html_template(synthesis):
    """Красивый HTML-шаблон для письма"""
    trends_html = "".join([f"""
        <div style="margin-bottom: 24px; padding: 20px; border-radius: 12px; border: 1px solid #eef2f6; background-color: #ffffff;">
            <h3 style="margin: 0 0 10px 0; color: #1a73e8; font-size: 18px; font-weight: 600;">{t['title']}</h3>
            <div style="color: #3c4043; font-size: 15px; line-height: 1.6;">{t['insight']}</div>
        </div>
    """ for t in synthesis.get('trends', [])])

    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f7f9; padding: 40px 20px;">
        <div style="max-width: 600px; margin: auto; background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.05);">
            <div style="background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%); color: white; padding: 40px; text-align: center;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 300; letter-spacing: 1px;">☀️ Sunday Brief</h1>
            </div>
            <div style="padding: 40px;">
                <div style="background: #f0f4ff; border-left: 5px solid #1a73e8; padding: 25px; border-radius: 8px; margin-bottom: 35px;">
                    <h2 style="margin: 0 0 10px 0; font-size: 13px; color: #1a73e8; text-transform: uppercase; letter-spacing: 1.5px;">The Big Picture</h2>
                    <p style="margin: 0; font-size: 17px; line-height: 1.5; color: #1a202c; font-weight: 500;">{synthesis.get('big_picture')}</p>
                </div>
                {trends_html}
            </div>
            <div style="background: #f8fafc; padding: 25px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0;">
                <strong>Noise Filter:</strong> {synthesis.get('noise_filter')}
            </div>
        </div>
    </div>
    """

def main():
    now = datetime.utcnow()
    cur_day, cur_hour = now.strftime("%A"), now.strftime("%H:00")
    print(f"🚀 Sunday AI Run | {cur_day} {cur_hour} UTC")

    # 1. Получаем пользователей, у которых сегодня день дайджеста
    users = supabase.table("profiles").select("*").eq("digest_day", cur_day).execute()
    
    if not users.data:
        print(f"💤 No users scheduled for {cur_day}.")
        return

    for user in users.data:
        user_sched = user.get('digest_time', '09:00')[:5]
        print(f"👤 User: {user['email']} (Sched: {user_sched})")
        
        # 2. Проверка времени (строгое соответствие часа)
        if user_sched != cur_hour:
            print(f"   ⏩ Skipping (Wait for {user_sched})")
            continue
            
        # 3. Получаем только необработанные письма этого пользователя
        emails = supabase.table("raw_emails").select("*").eq("user_id", user['id']).eq("processed", False).execute()
        
        if not emails.data:
            print(f"   📪 No new emails to process.")
            continue

        print(f"   📨 Synthesizing {len(emails.data)} emails...")
        
        # Склеиваем текст писем для ИИ
        context = ""
        for e in emails.data:
            context += f"SENDER: {e['sender']}\nSUBJECT: {e['subject']}\nCONTENT: {e['body_plain'][:1000]}\n---\n"

        # 4. Анализ через Gemini
        synthesis = get_ai_synthesis(context, user)
        
        if synthesis:
            html_body = get_html_template(synthesis)
            subject = f"Sunday Brief: {synthesis['big_picture'][:50]}..."
            
            # 5. Отправка и сохранение результата
            if send_email(user['email'], subject, html_body):
                # Записываем дайджест в БД
                supabase.table("digests").insert({
                    "user_id": user['id'], 
                    "structured_content": synthesis, 
                    "subject": subject
                }).execute()
                
                # Помечаем письма как обработанные
                for e in emails.data:
                    supabase.table("raw_emails").update({"processed": True}).eq("id", e['id']).execute()
                    
                print(f"   ✅ Success: Delivered and updated.")
            else:
                print(f"   ❌ Failed: Email delivery error.")
        else:
            print(f"   ❌ Failed: AI synthesis failed.")

if __name__ == "__main__":
    main()