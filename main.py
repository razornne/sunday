from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = FastAPI()

# Проверяем ключи
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: SUPABASE_URL or SUPABASE_KEY is missing.")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Supabase Connection Error: {e}")

# Модель данных (то, что присылает Cloudflare Worker)
class EmailPayload(BaseModel):
    sender: str
    recipient: str
    subject: str
    body_plain: str
    body_html: str | None = None

@app.get("/")
def read_root():
    return {"status": "Sunday AI Backend is running 🚀"}

@app.post("/webhook/email")
async def receive_email(payload: EmailPayload):
    """
    Принимает JSON от Cloudflare Worker и сохраняет в Supabase
    """
    print(f"📩 Incoming email from: {payload.sender}")
    
    try:
        # Готовим данные для вставки (соответствует новой структуре таблицы)
        data = {
            "sender": payload.sender,
            "recipient": payload.recipient,
            "subject": payload.subject,
            "body_plain": payload.body_plain,
            "body_html": payload.body_html,
            "processed": False  # Новое поле
        }

        # Вставляем в базу
        response = supabase.table("raw_emails").insert(data).execute()
        
        print("✅ Saved to DB successfully")
        return {"status": "ok", "message": "Email saved"}

    except Exception as e:
        print(f"❌ Error saving to Supabase: {e}")
        # Важно: если мы вернем 500, Cloudflare увидит ошибку в логах.
        # Сейчас мы возвращаем 400, чтобы Cloudflare знал, что что-то не так.
        raise HTTPException(status_code=500, detail=str(e))