import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai
import time

load_dotenv()

# Настройки
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Функция генерации для конкретного юзера
def process_user_digest(user_id, role, emails):
    print(f"   👤 User {user_id} (Role: {role}). Emails: {len(emails)}")

    # 1. Готовим контент
    clean_content = ""
    unique_sources = set()
    total_chars = 0
    ids_to_update = []

    for email in emails:
        body_part = email['body_text'][:10000] # Лимит на письмо
        unique_sources.add(email['sender'])
        total_chars += len(body_part)
        clean_content += f"\n--- SOURCE: {email['sender']} ---\nSUBJECT: {email['subject']}\n{body_part}\n"
        ids_to_update.append(email['id'])

    # 2. Настраиваем модель под РОЛЬ пользователя
    model = genai.GenerativeModel(
        model_name="gemini-2.5-pro", 
        generation_config={"response_mime_type": "application/json"},
        system_instruction=f"""
        You are an Elite AI Analyst. Create a personalized digest.
        TARGET AUDIENCE: {role if role else "General Tech Reader"}.
        
        ### INSTRUCTIONS
        1. Filter out garbage.
        2. Focus on what matters specifically for a {role}.
        3. If the role is "Investor", focus on deals/risks. If "Engineer", focus on code/tools.
        
        ### OUTPUT (JSON) with keys: "telegram_digest", "email_html"
        
        Structure for Telegram:
        # 🔥 Top Story
        ...
        # 🎯 Why this matters for you ({role})
        • [Insight 1]
        
        Structure for Email:
        <h3>🔥 Top Story</h3>
        ...
        <h3>🎯 Why this matters for you ({role})</h3>
        <ul><li>[Insight 1]</li></ul>
        """
    )

    try:
        # 3. Генерируем
        user_prompt = f"Digest these emails for a {role}:\n{clean_content}"
        response = model.generate_content(user_prompt)
        
        result = json.loads(response.text)
        tg_text = result.get("telegram_digest", "Error")
        email_html = result.get("email_html", "Error")

        # Добавляем статистику
        meta = f"\n\n📦 `Meta: {len(emails)} emails, {len(unique_sources)} sources`"
        tg_text += meta
        
        # 4. Сохраняем (ВАЖНО: с user_id)
        data = {
            "user_id": user_id,  # <-- ПРИВЯЗКА К ЮЗЕРУ
            "telegram_text": tg_text,
            "email_html": email_html
        }
        supabase.table("digests").insert(data).execute()

        # 5. Помечаем письма прочитанными
        for eid in ids_to_update:
            supabase.table("raw_emails").update({"is_processed": True}).eq("id", eid).execute()

        print("   ✅ Digest saved.")

    except Exception as e:
        print(f"   ❌ Error processing user {user_id}: {e}")
        # print(response.text) # раскомментируй для отладки

def main():
    print("💎 Starting SaaS Digest Generation...")

    # 1. Находим юзеров, у которых есть новые письма
    # Supabase не умеет делать "DISTINCT" в простом клиенте элегантно, 
    # поэтому берем все непрочитанные письма и группируем в Python.
    
    response = supabase.table("raw_emails").select("user_id, id, sender, subject, body_text")\
        .eq("is_processed", False).execute()
    
    all_emails = response.data

    if not all_emails:
        print("💤 No new emails for anyone.")
        return

    # Группировка: { 'user_uuid_123': [email1, email2], 'user_uuid_456': [email3] }
    user_buckets = {}
    for email in all_emails:
        uid = email['user_id']
        if not uid: continue # Пропускаем письма-сироты
        if uid not in user_buckets:
            user_buckets[uid] = []
        user_buckets[uid].append(email)

    print(f"found active users: {len(user_buckets)}")

    # 2. Обрабатываем каждого юзера отдельно
    for user_id, emails in user_buckets.items():
        # Получаем профиль юзера, чтобы узнать роль
        profile_res = supabase.table("profiles").select("role").eq("id", user_id).execute()
        
        role = "Tech Reader"
        if profile_res.data:
            role = profile_res.data[0].get('role', "Tech Reader")
        
        process_user_digest(user_id, role, emails)
        time.sleep(2) # Пауза между юзерами, чтобы не упереться в лимиты API

if __name__ == "__main__":
    main()