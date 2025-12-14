from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import os
import email
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
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text})

# --- РОУТЫ ---

@app.get("/")
def read_root():
    return {"status": "Sunday AI Backend Active 🚀"}

# 1. ПРИЕМ ПИСЕМ (От Cloudflare)
@app.post("/webhook/email")
async def receive_email(payload: EmailPayload):
    try:
        plain, html = parse_email(payload.raw_email)
        if not html and plain: html = f"<div>{plain.replace(chr(10), '<br>')}</div>"
        
        data = {
            "sender": payload.sender, "recipient": payload.recipient,
            "subject": payload.subject, "body_plain": plain, "body_html": html,
            "processed": False
        }
        supabase.table("raw_emails").insert(data).execute()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. ПРИЕМ СООБЩЕНИЙ ТЕЛЕГРАМ (Webhook)
@app.post("/webhook/telegram")
async def receive_telegram(request: Request):
    """Сюда Telegram присылает уведомления, когда кто-то пишет боту"""
    data = await request.json()
    
    # Проверяем, что это сообщение
    if "message" not in data:
        return {"status": "ignored"}
    
    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    # Логика связывания аккаунта: /start <код>
    if text.startswith("/start") and len(text) > 7:
        code = text.split(" ")[1] # Берем то, что после пробела
        print(f"🔗 Попытка привязки. Код: {code}, ChatID: {chat_id}")
        
        # Ищем пользователя с таким кодом
        response = supabase.table("profiles").select("id").eq("verification_code", code).execute()
        
        if response.data:
            user_id = response.data[0]['id']
            
            # Обновляем профиль: Сохраняем ID и стираем код (он одноразовый)
            supabase.table("profiles").update({
                "telegram_chat_id": str(chat_id),
                "verification_code": None 
            }).eq("id", user_id).execute()
            
            send_tg_message(chat_id, "✅ Успешно! Ваш Telegram привязан к Sunday AI. Теперь дайджесты будут приходить сюда.")
        else:
            send_tg_message(chat_id, "❌ Неверный или устаревший код ссылки. Попробуйте снова через сайт.")
    
    elif text == "/start":
        send_tg_message(chat_id, "Привет! Чтобы подключить меня, нажми кнопку 'Connect Telegram' в личном кабинете Sunday AI.")

    return {"status": "ok"}