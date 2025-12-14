from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import email
from email.header import decode_header
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = FastAPI()

# Подключение к базе
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Новая модель: ждем raw_email вместо готовых кусков
class EmailPayload(BaseModel):
    sender: str
    recipient: str
    subject: str
    raw_email: str 

def parse_email(raw_content):
    """Парсит сырое письмо и возвращает (text, html)"""
    msg = email.message_from_string(raw_content)
    body_plain = ""
    body_html = ""

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))

            if "attachment" in cdispo:
                continue

            try:
                payload = part.get_payload(decode=True).decode(errors="ignore")
            except:
                continue

            if ctype == "text/plain" and not body_plain:
                body_plain = payload
            elif ctype == "text/html" and not body_html:
                body_html = payload
    else:
        # Не мультипарт (обычный текст)
        try:
            payload = msg.get_payload(decode=True).decode(errors="ignore")
            body_plain = payload
            if msg.get_content_type() == "text/html":
                body_html = payload
        except:
            pass
            
    return body_plain, body_html

@app.post("/webhook/email")
async def receive_email(payload: EmailPayload):
    print(f"📩 Parsing email from: {payload.sender}")
    
    try:
        # 1. Парсим сырое письмо
        plain, html = parse_email(payload.raw_email)
        
        # Если HTML нет, пробуем сделать его из текста (заменяем переносы на <br>)
        if not html and plain:
            html = f"<div>{plain.replace(chr(10), '<br>')}</div>"

        # 2. Готовим данные
        data = {
            "sender": payload.sender,
            "recipient": payload.recipient,
            "subject": payload.subject,
            "body_plain": plain,
            "body_html": html, # Теперь здесь будет реальный HTML!
            "processed": False
        }

        # 3. Сохраняем
        supabase.table("raw_emails").insert(data).execute()
        
        print("✅ Parsed & Saved successfully")
        return {"status": "ok"}

    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))