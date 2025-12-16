from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import os
import email
from email.utils import parseaddr
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = FastAPI()

# --- КОНФИГУРАЦИЯ ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- МОДЕЛИ ДАННЫХ ---
class EmailPayload(BaseModel):
    sender: str
    recipient: str
    subject: str
    raw_email: str 

# --- ФУНКЦИИ ---
def parse_email(raw_content):
    """Парсит сырое письмо"""
    msg = email.message_from_string(raw_content)
    body_plain = ""
    body_html = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if "attachment" in str(part.get("Content-Disposition")): continue
            try: payload = part.get_payload(decode=True).decode(errors="ignore")
            except: continue
            if ctype == "text/plain" and not body_plain: body_plain = payload
            elif ctype == "text/html" and not body_html: body_html = payload
    else:
        try:
            payload = msg.get_payload(decode=True).decode(errors="ignore")
            body_plain = payload
            if msg.get_content_type() == "text/html": body_html = payload
        except: pass
    return body_plain, body_html

def send_tg_message(chat_id, text):
    if not TG_TOKEN: return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text})
    except: pass

# --- РОУТЫ ---

@app.get("/")
def read_root():
    return {"status": "Sunday AI Backend Active (v0.2) 🚀"}

# 1. ПРИЕМ ПИСЕМ (ОТ Cloudflare)
@app.post("/webhook/email")
async def receive_email(payload: EmailPayload):
    try:
        # 1. Очищаем адрес получателя (на всякий случай)
        _, clean_recipient = parseaddr(payload.recipient)
        clean_recipient = clean_recipient.strip().lower()

        print(f"📨 Incoming mail for: {clean_recipient}")

        # 2. Ищем Владельца адреса (Фейс-контроль)
        # Мы ищем юзера, у которого personal_email совпадает с получателем
        user_res = supabase.table("profiles").select("id").eq("personal_email", clean_recipient).execute()
        
        if not user_res.data:
            print(f"⛔ User not found for email: {clean_recipient}. Rejecting.")
            # Возвращаем OK, чтобы Cloudflare не пытался слать снова, но не сохраняем
            return {"status": "ignored_unknown_user"}
        
        user_id = user_res.data[0]['id']
        print(f"✅ User identified: {user_id}")

        # 3. Парсим и Сохраняем
        plain, html = parse_email(payload.raw_email)
        if not html and plain: html = f"<div>{plain.replace(chr(10), '<br>')}</div>"
        
        data = {
            "user_id": user_id,  # <--- ВАЖНО: Привязываем письмо к юзеру
            "sender": payload.sender,
            "recipient": payload.recipient,
            "subject": payload.subject, 
            "body_plain": plain, 
            "body_html": html,
            "processed": False
        }
        
        supabase.table("raw_emails").insert(data).execute()
        print("💾 Email saved to DB.")
        
        return {"status": "ok"}

    except Exception as e:
        print(f"❌ Error receiving email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. ПРИЕМ СООБЩЕНИЙ ТЕЛЕГРАМ (Webhook)
@app.post("/webhook/telegram")
async def receive_telegram(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        return {"status": "error"}
    
    if "message" not in data: return {"status": "ignored"}
    
    msg = data["message"]
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "")
    
    # Логика связывания: /start <код>
    if text.startswith("/start"):
        parts = text.split(" ")
        if len(parts) > 1:
            code = parts[1]
            try:
                response = supabase.table("profiles").select("id").eq("verification_code", code).single().execute()
                if response.data:
                    user_id = response.data['id']
                    supabase.table("profiles").update({
                        "telegram_chat_id": str(chat_id),
                        "verification_code": None 
                    }).eq("id", user_id).execute()
                    send_tg_message(chat_id, "✅ Успешно! Ваш Telegram привязан к Sunday AI.")
                else:
                    send_tg_message(chat_id, "❌ Код не найден.")
            except Exception as e:
                print(f"DB Error: {e}")
        else:
            send_tg_message(chat_id, "Привет! Возьми код на сайте dashboard.")

    return {"status": "ok"}