from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# Обновленная модель: используем Alias, чтобы FastAPI понимал стандартные поля почты
class EmailPayload(BaseModel):
    sender: str = Field(..., alias="from") # Cloudflare шлет "from", мы читаем как "sender"
    recipient: str = Field(..., alias="to") # Cloudflare шлет "to"
    subject: str
    body_plain: str = Field(..., alias="text") # Cloudflare шлет "text"
    body_html: str = ""

    class Config:
        populate_by_name = True

def forward_urgent_email(to_email, original_subject, body_html, body_plain):
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
    # Логируем для отладки в консоль Render
    print(f"Incoming email from {email.sender} to {email.recipient}")

    # 1. Находим пользователя по адресу sundayai.dev
    res = supabase.table("profiles").select("*").eq("personal_email", email.recipient).execute()
    if not res.data:
        # Если такого ящика нет, не даем 422, а просто вежливо отвечаем 200, 
        # чтобы Cloudflare не долбил нас ошибками
        return {"status": "ignored", "reason": "user_not_found"}
    
    user = res.data[0]
    
    # 2. Проверка на "срочность"
    urgent_keywords = ["confirm", "verify", "welcome", "subscription", "activate", "action required"]
    is_urgent = any(word in email.subject.lower() for word in urgent_keywords)
    
    if is_urgent:
        forward_urgent_email(user['email'], email.subject, email.body_html, email.body_plain)
    
    # 3. Сохранение в базу
    supabase.table("raw_emails").insert({
        "user_id": user['id'],
        "sender": email.sender,
        "subject": email.subject,
        "body_plain": email.body_plain,
        "body_html": email.body_html
    }).execute()
    
    return {"status": "ok"}

@app.get("/")
def home(): return "Sunday AI Backend is Live"