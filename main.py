from fastapi import FastAPI, Request
from pydantic import BaseModel
from supabase import create_client
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

class EmailPayload(BaseModel):
    sender: str
    recipient: str
    subject: str
    body_plain: str
    body_html: str = ""

def forward_urgent_email(to_email, original_subject, body_html, body_plain):
    """Мгновенная пересылка сервисных писем"""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Sunday Forwarder <{os.environ.get('EMAIL_USER')}>"
        msg['To'] = to_email
        msg['Subject'] = f"🔔 [Sunday Action Required] {original_subject}"
        msg.attach(MIMEText(body_html or body_plain, 'html' if body_html else 'plain'))
        
        with smtplib.SMTP(os.environ.get("SMTP_SERVER", "smtp.gmail.com"), 587) as server:
            server.starttls()
            server.login(os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASS"))
            server.sendmail(os.environ.get("EMAIL_USER"), to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Forward error: {e}")
        return False

@app.post("/webhook/email")
async def handle_email(email: EmailPayload):
    # 1. Находим пользователя по адресу sundayai.dev
    res = supabase.table("profiles").select("*").eq("personal_email", email.recipient).execute()
    if not res.data:
        return {"status": "error", "message": "User not found"}
    
    user = res.data[0]
    
    # 2. Проверяем, не является ли письмо подтверждением подписки
    urgent_keywords = ["confirm", "verify", "welcome", "subscription", "activate", "action required"]
    is_urgent = any(word in email.subject.lower() for word in urgent_keywords)
    
    if is_urgent:
        forward_urgent_email(user['email'], email.subject, email.body_html, email.body_plain)
    
    # 3. Сохраняем в базу как обычно
    supabase.table("raw_emails").insert({
        "user_id": user['id'],
        "sender": email.sender,
        "subject": email.subject,
        "body_plain": email.body_plain,
        "body_html": email.body_html
    }).execute()
    
    return {"status": "ok", "urgent": is_urgent}

@app.get("/")
def home(): return "Sunday AI Backend is Live"