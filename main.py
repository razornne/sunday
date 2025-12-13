from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Настройки
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
app = FastAPI()

# Модель входящего вебхука (от Cloudflare/SendGrid)
class IncomingEmail(BaseModel):
    sender: str        # От кого: newsletter@substack.com
    recipient: str     # Кому: nikita.x9z@sunday.me
    subject: str
    body_plain: str
    body_html: str | None = None

@app.post("/webhook/email")
async def receive_email(email: IncomingEmail):
    print(f"📨 Incoming: {email.sender} -> {email.recipient}")

    # 1. Ищем пользователя по его виртуальному адресу (Alias)
    # Например, если письмо пришло на nikita.x9z@sunday.me, ищем, чей это адрес.
    user_query = supabase.table("profiles").select("id").eq("inbox_alias", email.recipient).execute()
    
    if not user_query.data:
        print(f"❌ User not found for alias: {email.recipient}")
        # Возвращаем 200, чтобы почтовый сервер не слал повторы, но ничего не делаем
        return {"status": "User not found, email ignored"}
    
    user_id = user_query.data[0]['id']
    print(f"👤 Found User ID: {user_id}")

    # 2. Проверяем подписку (Whitelist) - Опционально
    # Если мы хотим принимать письма ТОЛЬКО от тех, кого юзер добавил в список
    sub_query = supabase.table("subscriptions").select("*")\
        .eq("user_id", user_id)\
        .ilike("sender_email", email.sender).execute() # ilike - регистронезависимо
    
    # Если хочешь пока принимать ВСЁ подряд - закомментируй этот блок if:
    if not sub_query.data:
         print(f"⚠️ Sender {email.sender} is not in whitelist. Ignoring.")
         return {"status": "Sender not allowed"}

    # 3. Сохраняем письмо с привязкой к юзеру
    data = {
        "user_id": user_id,  # <-- ВАЖНО: Привязка к юзеру
        "sender": email.sender,
        "subject": email.subject,
        "body_text": email.body_plain,
        "raw_html": email.body_html,
        "is_processed": False
    }
    
    try:
        supabase.table("raw_emails").insert(data).execute()
        print("✅ Email saved to DB.")
        return {"status": "success"}
    except Exception as e:
        print(f"❌ DB Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))