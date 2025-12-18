from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional
from supabase import create_client
import os
import smtplib
import email
from email.policy import default
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# Модель в точности по твоим логам
class EmailPayload(BaseModel):
    sender: str
    recipient: str
    subject: Optional[str] = "No Subject"
    raw_email: str # Cloudflare присылает всё письмо строкой

def extract_body(raw_content: str):
    """Парсит сырое письмо и достает из него текстовую часть"""
    msg = email.message_from_string(raw_content, policy=default)
    body_plain = ""
    body_html = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                body_plain = part.get_payload(decode=True).decode(errors='ignore')
            elif content_type == "text/html":
                body_html = part.get_payload(decode=True).decode(errors='ignore')
    else:
        body_plain = msg.get_payload(decode=True).decode(errors='ignore')
        
    return body_plain, body_html

def forward_urgent_email(to_email, subject, content_html):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Sunday Forwarder <{os.environ.get('EMAIL_USER')}>"
        msg['To'] = to_email
        msg['Subject'] = f"🔔 [Action Required] {subject}"
        msg.attach(MIMEText(content_html, 'html'))
        
        with smtplib.SMTP(os.environ.get("SMTP_SERVER", "smtp.gmail.com"), 587) as server:
            server.starttls()
            server.login(os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASS"))
            server.sendmail(os.environ.get("EMAIL_USER"), to_email, msg.as_string())
    except Exception as e:
        print(f"Forward error: {e}")

@app.post("/webhook/email")
async def handle_email(payload: EmailPayload):
    # 1. Достаем текст из сырого письма
    body_plain, body_html = extract_body(payload.raw_email)
    
    # 2. Ищем пользователя
    res = supabase.table("profiles").select("*").eq("personal_email", payload.recipient).execute()
    if not res.data:
        return {"status": "ignored", "reason": "user_not_found"}
    
    user = res.data[0]
    
    # 3. Проверка на срочность (для пересылки)
    urgent_keywords = ["confirm", "verify", "welcome", "subscription", "activate"]
    is_urgent = any(word in payload.subject.lower() for word in urgent_keywords)
    
    if is_urgent:
        forward_urgent_email(user['email'], payload.subject, body_html or body_plain)
    
    # 4. Сохраняем в базу (body_plain нужен для ИИ в воскресенье)
    supabase.table("raw_emails").insert({
        "user_id": user['id'],
        "sender": payload.sender,
        "subject": payload.subject,
        "body_plain": body_plain[:5000], # Ограничиваем размер для базы
        "body_html": body_html[:5000]
    }).execute()
    
    return {"status": "ok"}

@app.get("/")
def home(): return "Sunday AI Backend is Active"