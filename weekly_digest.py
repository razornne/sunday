import os
import json
import smtplib
from google import genai
from google.genai import types # Добавили для типов данных
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# --- INITIALIZATION ---
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
# Явно указываем клиент для Gemini API
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
        # ИСПОЛЬЗУЕМ БОЛЕЕ СТАБИЛЬНОЕ ИМЯ МОДЕЛИ
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )
        # В новой библиотеке ответ лежит в .text или .parsed
        return json.loads(response.text)
    except Exception as e:
        print(f"   ❌ AI Synthesis Error: {e}")
        return None

def get_html_template(synthesis):
    trends_html = "".join([f"""
        <div style="margin-bottom: 20px; padding: 18px; border-radius: 12px; border: 1px solid #e8eaed; background-color: #ffffff;">
            <h3 style="margin: 0 0 10px 0; color: #1a73e8; font-size: 17px; font-weight: 600;">{t['title']}</h3>
            <div style="color: #3c4043; font-size: 14px; line-height: 1.6;">{t['insight']}</div>
        </div>
    """ for t in synthesis.get('trends', [])])

    return f"""
    <div style="font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f9fa; padding: 20px; color: #202124;">
        <div style="max-width: 600px; margin: auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
            <div style="background: #1a73e8; color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 400;">☀️ Sunday AI</h1>
            </div>
            <div style="padding: 30px;">
                <div style="background: #e8f0fe; border-left: 4px solid #1a73e8; padding: 20px; border-radius: 4px; margin-bottom: 30px;">
                    <h2 style="margin: 0 0 10px 0; font-size: 14px; color: #1a73e8; text-transform: uppercase; letter-spacing: 1px;">The Big Picture</h2>
                    <p style="margin: 0; font-size: 16px; line-height: 1.5; font-weight: 500;">{synthesis.get('big_picture')}</p>
                </div>
                {trends_html}
            </div>
            <div style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #70757a; border-top: 1px solid #e8eaed;">
                <strong>Noise Filter:</strong> {synthesis.get('noise_filter')}
            </div>
        </div>
    </div>
    """

def main():
    now = datetime.utcnow()
    cur_day, cur_hour = now.strftime("%A"), now.strftime("%H:00")
    print(f"🚀 Sunday AI Run | {cur_day} {cur_hour} UTC")

    users = supabase.table("profiles").select("*").eq("digest_day", cur_day).execute()
    
    for user in users.data:
        user_sched = user.get('digest_time', '09:00')[:5]
        print(f"👤 User: {user['email']} (Sched: {user_sched})")
        
        if user_sched != cur_hour[:5]:
            print(f"   ⏩ Skip.")
            continue
            
        emails = supabase.table("raw_emails").select("*").eq("user_id", user['id']).eq("processed", False).execute()
        
        if not emails.data:
            print(f"   📪 No new emails.")
            continue

        print(f"   📨 Processing {len(emails.data)} items...")
        context = "\n".join([f"SENDER: {e['sender']}\nSUBJECT: {e['subject']}\nCONTENT: {e['body_plain'][:1000]}\n---" for e in emails.data])

        synthesis = get_ai_synthesis(context, user)
        if synthesis:
            html_body = get_html_template(synthesis)
            subject = f"Sunday Brief: {synthesis['big_picture'][:50]}..."
            
            if send_email(user['email'], subject, html_body):
                supabase.table("digests").insert({"user_id": user['id'], "structured_content": synthesis, "subject": subject}).execute()
                for e in emails.data:
                    supabase.table("raw_emails").update({"processed": True}).eq("id", e['id']).execute()
                print(f"   ✅ Delivered.")

if __name__ == "__main__":
    main()