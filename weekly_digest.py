import os
import json
import smtplib
from google import genai
from google import genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# --- INITIALIZATION ---
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
# Инициализируем клиент Gemini
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def send_email(to_email, subject, html_body):
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
    """Генерация аналитического дайджеста через Gemini 1.5 Flash"""
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
        # Стабильный вызов модели без лишних префиксов
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.2 # Делаем ответы более стабильными
            )
        )
        # Обработка результата
        return json.loads(response.text)
    except Exception as e:
        print(f"   ❌ AI Synthesis Error: {e}")
        return None

def get_html_template(synthesis):
    """Дизайн письма в стиле современных тех-рассылок"""
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
                <p style="opacity: 0.8; margin-top: 10px; font-size: 14px;">Filtered intelligence for your week</p>
            </div>
            <div style="padding: 40px;">
                <div style="background: #f0f4ff; border-left: 5px solid #1a73e8; padding: 25px; border-radius: 8px; margin-bottom: 35px;">
                    <h2 style="margin: 0 0 10px 0; font-size: 13px; color: #1a73e8; text-transform: uppercase; letter-spacing: 1.5px;">The Big Picture</h2>
                    <p style="margin: 0; font-size: 17px; line-height: 1.5; color: #1a202c; font-weight: 500;">{synthesis.get('big_picture')}</p>
                </div>
                <h2 style="font-size: 13px; color: #718096; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 20px;">Key Insights</h2>
                {trends_html}
            </div>
            <div style="background: #f8fafc; padding: 25px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0;">
                <p style="margin: 0;"><strong>Noise Filter:</strong> {synthesis.get('noise_filter')}</p>
                <p style="margin-top: 10px;">© 2025 Sunday AI. Built for focus.</p>
            </div>
        </div>
    </div>
    """

def main():
    now = datetime.utcnow()
    cur_day, cur_hour = now.strftime("%A"), now.strftime("%H:00")
    print(f"🚀 Sunday AI Run | {cur_day} {cur_hour} UTC")

    # Получаем пользователей на сегодня
    users = supabase.table("profiles").select("*").eq("digest_day", cur_day).execute()
    
    if not users.data:
        print(f"💤 No users scheduled for today.")
        return

    for user in users.data:
        user_sched = user.get('digest_time', '09:00')[:5]
        print(f"👤 User: {user['email']} (Sched: {user_sched})")
        
        # Проверка времени
        if user_sched != cur_hour[:5]:
            print(f"   ⏩ Skipping (Scheduled for {user_sched})")
            continue
            
        # Получаем необработанные письма
        emails = supabase.table("raw_emails").select("*").eq("user_id", user['id']).eq("processed", False).execute()
        
        if not emails.data:
            print(f"   📪 No new emails found.")
            continue

        print(f"   📨 Synthesizing {len(emails.data)} emails...")
        # Формируем контекст для ИИ
        context = ""
        for e in emails.data:
            context += f"FROM: {e['sender']}\nSUBJ: {e['subject']}\nBODY: {e['body_plain'][:1200]}\n---\n"

        # Генерация дайджеста
        synthesis = get_ai_synthesis(context, user)
        if synthesis:
            html_body = get_html_template(synthesis)
            subject = f"Sunday Brief: {synthesis['big_picture'][:55]}..."
            
            if send_email(user['email'], subject, html_body):
                # Сохраняем результат и метим письма как прочитанные
                supabase.table("digests").insert({
                    "user_id": user['id'], 
                    "structured_content": synthesis, 
                    "subject": subject
                }).execute()
                for e in emails.data:
                    supabase.table("raw_emails").update({"processed": True}).eq("id", e['id']).execute()
                print(f"   ✅ Brief delivered successfully.")
            else:
                print(f"   ❌ Email failed to send.")

if __name__ == "__main__":
    main()