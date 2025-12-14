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
    """Сюда Telegram присылает уведомления"""
    try:
        data = await request.json()
        print(f"📥 RAW UPDATE: {data}") # Видим ВСЁ, что прислал Телеграм
    except Exception as e:
        print(f"❌ JSON ERROR: {e}")
        return {"status": "error"}
    
    # Проверяем структуру
    if "message" not in data:
        print("⚠️ Update has no 'message'. Skipping.")
        return {"status": "ignored"}
    
    msg = data["message"]
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "")
    
    print(f"📨 Processing: ChatID={chat_id}, Text='{text}'")

    # Логика связывания: /start <код>
    if text.startswith("/start"):
        parts = text.split(" ")
        print(f"🧐 Parsing start command. Parts: {parts}")

        if len(parts) > 1:
            code = parts[1]
            print(f"🔑 Extract code: {code}. Searching DB...")
            
            # Ищем пользователя
            try:
                # ВАЖНО: Используем single(), чтобы сразу получить объект или ошибку
                response = supabase.table("profiles").select("id").eq("verification_code", code).execute()
                print(f"🗄️ DB Response: {response.data}")
                
                if response.data:
                    user_id = response.data[0]['id']
                    print(f"✅ User found: {user_id}. Updating...")
                    
                    # Обновляем
                    upd = supabase.table("profiles").update({
                        "telegram_chat_id": str(chat_id),
                        "verification_code": None 
                    }).eq("id", user_id).execute()
                    print(f"💾 Update Result: {upd.data}")
                    
                    send_tg_message(chat_id, "✅ Успешно! Ваш Telegram привязан к Sunday AI.")
                else:
                    print("❌ Code not found in DB.")
                    send_tg_message(chat_id, "❌ Код не найден. Попробуйте снова через сайт.")
            except Exception as e:
                print(f"❌ DB ERROR: {e}")
                send_tg_message(chat_id, "❌ Ошибка базы данных.")
        else:
            print("⚠️ Start without code.")
            send_tg_message(chat_id, "Нажми кнопку на сайте, чтобы получить код.")

    return {"status": "ok"}