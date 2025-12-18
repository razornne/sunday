import os
import json
import smtplib
from google import genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# --- INITIALIZATION ---
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
# Инициализация нового клиента Google AI
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
        print(f"❌ SMTP Error: {e}")
        return False

def get_ai_synthesis(emails_text, profile):
    role = profile.get('role', 'Professional')
    focus = ", ".join(profile.get('focus_areas', []))
    
    prompt = f"""
    ROLE: Elite Strategy Consultant for a "{role}".
    FOCUS: {focus}.
    TASK: Synthesize these emails into a JSON "Sunday Brief".
    FORMAT: {{ "big_picture": "...", "trends": [{{ "title": "...", "insight": "..." }}], "noise_filter": "..." }}
    EMAILS: {emails_text}
    """
    
    try:
        # Новый метод вызова Gemini 1.5 Flash
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return None

def get_html_template(synthesis):
    trends_html = "".join([f"""
        <div style="margin-bottom: 20px; padding: 15px; border-radius: 10px; border: 1px solid #eef2f6; background-color: #ffffff;">
            <h3 style="margin: 0 0 8px 0; color: #1a73e8; font-size: 16px;">{t['title']}</h3>
            <div style="color: #3c4043; font-size: 14px; line-height: 1.5;">{t['insight']}</div>
        </div>
    """ for t in synthesis.get('trends', [])])

    return f"""
    <html>
    <body style="font-family: sans-serif; background-color: #f8f9fa; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <div style="background: #1a73e8; color: white; padding: 25px; text-align: center;">
                <h1 style="margin: 0; font-size: 22px;">☀️ Sunday AI Brief</h1>
            </div>
            <div style="padding: 25px;">
                <div style="background: #f0f7ff; border-left: 4px solid #1a73e8; padding: 15px; margin-bottom: 25px;">
                    <strong style="color: #1a73e8;">The Big Picture:</strong><br>
                    <span style="font-size: 15px;">{synthesis.get('big_picture')}</span>
                </div>
                {trends_html}
            </div>
            <div style="background: #f1f3f4; padding: 15px; text-align: center; font-size: 11px; color: #70757a;">
                Noise Filtered: {synthesis.get('noise_filter')} | © 2025 Sunday AI
            </div>
        </div>
    </body>
    </html>
    """

def main():
    now = datetime.utcnow()
    cur_day, cur_hour = now.strftime("%A"), now.strftime("%H:00")
    print(f"🚀 Sunday AI Engine Started | Day: {cur_day} | Time: {cur_hour} UTC")

    # 1. Загружаем всех пользователей на текущий день
    users = supabase.table("profiles").select("*").eq("digest_day", cur_day).execute()
    
    if not users.data:
        print(f"💤 No users scheduled for {cur_day}.")
        return

    for user in users.data:
        user_sched = user.get('digest_time', '09:00')[:5]
        
        # ЛОГ: Показываем, кого проверяем
        print(f"👤 Checking user: {user['email']} (Scheduled: {user_sched})")
        
        if user_sched != cur_hour[:5]:
            print(f"   ⏩ Skipping: Not time yet.")
            continue
            
        # 2. Ищем новые письма
        emails = supabase.table("raw_emails").select("*").eq("user_id", user['id']).eq("processed", False).execute()
        
        if not emails.data:
            print(f"   📪 No new emails to process.")
            continue

        print(f"   📨 Processing {len(emails.data)} emails...")

        context = "\n".join([f"SOURCE: {e['sender']}\nSUBJECT: {e['subject']}\nCONTENT: {e['body_plain'][:1500]}\n---" for e in emails.data])

        # 3. Синтез и отправка
        synthesis = get_ai_synthesis(context, user)
        if synthesis:
            html_body = get_html_template(synthesis)
            subject = f"Sunday Brief: {synthesis['big_picture'][:45]}..."
            
            if send_email(user['email'], subject, html_body):
                # История и пометка об обработке
                supabase.table("digests").insert({"user_id": user['id'], "structured_content": synthesis, "subject": subject}).execute()
                for e in emails.data:
                    supabase.table("raw_emails").update({"processed": True}).eq("id", e['id']).execute()
                print(f"   ✅ Brief delivered!")
            else:
                print(f"   ❌ Email delivery failed.")

if __name__ == "__main__":
    main()