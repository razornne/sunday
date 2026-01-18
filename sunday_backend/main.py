import os
import re
import email
from email.policy import default
from dotenv import load_dotenv

# 1. Загружаем переменные окружения
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from supabase import create_client
from bs4 import BeautifulSoup # Для создания текста из HTML, если plain text отсутствует

app = FastAPI()

# 2. НАСТРОЙКА CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://sunday-dashboard.vercel.app"], # Добавь свой прод домен, если есть
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Подключение к Supabase
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# --- МОДЕЛИ ДАННЫХ ---

# Для Лендинга (Waitlist)
class WaitlistSchema(BaseModel):
    email: str

# Для Cloudflare (В точности как шлет Worker)
class EmailPayload(BaseModel):
    sender: str
    recipient: str
    subject: Optional[str] = "No Subject"
    raw_email: str 
    timestamp: Optional[str] = None

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def extract_clean_email(text):
    """
    Превращает 'Ivan <ivan@sunday.dev>' -> 'ivan@sunday.dev'
    """
    match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    return match.group(0) if match else text

def parse_raw_email(raw_content):
    """
    Разбирает MIME-строку (сырое письмо) на заголовки, plain text и html.
    """
    msg = email.message_from_string(raw_content, policy=default)
    
    body_plain = ""
    body_html = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            
            # Пропускаем вложения (файлы)
            if 'attachment' in cdispo:
                continue
                
            try:
                # Если нашли чистый текст
                if ctype == 'text/plain' and not body_plain:
                    body_plain = part.get_content()
                # Если нашли HTML
                elif ctype == 'text/html' and not body_html:
                    body_html = part.get_content()
            except Exception as e:
                print(f"Error parsing part: {e}")
    else:
        # Если письмо простое (не multipart)
        try:
            payload = msg.get_content()
            if msg.get_content_type() == 'text/html':
                body_html = payload
            else:
                body_plain = payload
        except:
            # Fallback для старых форматов
            body_plain = msg.get_payload(decode=True).decode(errors='ignore')

    # Очистка от пробелов
    return (body_plain or "").strip(), (body_html or "").strip()

# --- РУЧКИ (ENDPOINTS) ---

@app.get("/")
def home(): 
    return "Sunday AI Backend is Active 🚀"

# 1. Ручка для ЛЕНДИНГА (Waitlist)
@app.post("/api/waitlist")
async def add_to_waitlist(data: WaitlistSchema):
    print(f"📝 Запрос в Waitlist: {data.email}")
    try:
        response = supabase.table("waitlist").insert({"email": data.email}).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        print(f"❌ Ошибка Supabase: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. Ручка для CLOUDFLARE (Входящие письма)
@app.post("/webhook/email")
async def handle_email(payload: EmailPayload):
    print(f"📨 Incoming from Worker. To: {payload.recipient}")

    # 1. Чистим адрес получателя (ключевой момент для роутинга)
    clean_recipient = extract_clean_email(payload.recipient)
    
    # 2. Ищем пользователя по его inbox_email (адрес @sunday.dev)
    res = supabase.table("profiles").select("*").eq("inbox_email", clean_recipient).execute()
    
    if not res.data:
        print(f"❌ User not found for inbox: {clean_recipient}")
        # Возвращаем 200, чтобы Cloudflare не пытался слать снова (или 404, если хочешь bouncing)
        return {"status": "ignored", "reason": "user_not_found"}
    
    user = res.data[0]
    user_id = user['id']
    print(f"✅ User identified: {user_id}")

    # 3. Парсим сырое письмо
    body_plain, body_html = parse_raw_email(payload.raw_email)
    
    # Fallback: Если plain text пустой, вытаскиваем текст из HTML (ИИ нужен текст)
    if not body_plain and body_html:
        try:
            body_plain = BeautifulSoup(body_html, "html.parser").get_text(separator="\n")
        except Exception as e:
            print(f"BS4 Error: {e}")
            body_plain = body_html # На крайний случай сохраняем как есть

    # 4. Сохраняем в базу (без урезания длины, Postgres справится)
    email_data = {
        "user_id": user_id,
        "sender": payload.sender,
        "subject": payload.subject,
        "body_plain": body_plain, 
        "body_html": body_html,
        "received_at": payload.timestamp,
        "processing_status": "pending" # <-- Важно для Pipeline!
    }
    
    try:
        supabase.table("raw_emails").insert(email_data).execute()
        print("💾 Email saved to DB")
        return {"status": "success"}
    except Exception as e:
        print(f"🔥 DB Error: {e}")
        # Не роняем воркер, просто логируем
        return {"status": "error", "detail": str(e)}