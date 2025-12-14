import os
import json
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv
from email.utils import parseaddr # <--- ЭТО ВАЖНО

load_dotenv()

# Настройки
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

def generate_summary(text):
    model = genai.GenerativeModel('gemini-pro')
    # Обрезаем текст, чтобы не перегрузить токенами
    safe_text = text[:8000] if text else "No text"
    
    prompt = f"""
    Ты - редактор технического дайджеста. Твоя задача - сделать краткую выжимку из письма.
    
    Письмо:
    {safe_text} 
    
    Сделай 2 версии ответа в формате JSON (без Markdown разметки):
    1. "summary_text": Подробный пересказ (Markdown) для сайта. Выдели главные мысли.
    2. "telegram_text": Очень короткий пост для Telegram (макс 400 символов). Начни с эмодзи.
    
    Верни ТОЛЬКО валидный JSON.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating AI: {e}")
        return None

def main():
    print("🚀 Starting Summarizer...")

    # 1. Берем НЕОБРАБОТАННЫЕ письма
    response = supabase.table("raw_emails").select("*").eq("processed", False).execute()
    emails = response.data

    if not emails:
        print("💤 No new emails to process.")
        return

    print(f"📨 Found {len(emails)} new emails.")

    for email_obj in emails:
        raw_sender = email_obj.get('sender', '')
        
        # --- МАГИЯ ЗДЕСЬ: Чистим адрес ---
        # Превращаем "Name <email@site.com>" в "email@site.com"
        name, clean_email = parseaddr(raw_sender)
        
        # Если parseaddr не справился, пробуем взять как есть, но в нижнем регистре
        final_sender_check = clean_email.lower() if clean_email else raw_sender.lower()
        
        print(f"Processing: {final_sender_check} (Original: {raw_sender})")

        # 2. Ищем ВЛАДЕЛЬЦА подписки
        # Ищем совпадение по чистому email
        sub_response = supabase.table("subscriptions").select("user_id")\
            .ilike("sender_email", final_sender_check)\
            .eq("is_active", True).execute()
        
        subscriptions = sub_response.data

        if not subscriptions:
            print(f"❌ Sender '{final_sender_check}' is not in whitelist. Marking as processed.")
            supabase.table("raw_emails").update({"processed": True}).eq("id", email_obj['id']).execute()
            continue
        
        print(f"✅ Found subscription! Generating digest...")

        # Генерируем AI контент
        # Берем plain текст, если его нет - пробуем почистить html (упрощенно)
        content_to_summarize = email_obj.get('body_plain')
        if not content_to_summarize and email_obj.get('body_html'):
             content_to_summarize = email_obj.get('body_html') # В идеале тут нужен clean_html, но пока так

        ai_json_str = generate_summary(content_to_summarize)
        
        if not ai_json_str:
            print("⚠️ AI failed to generate summary.")
            continue
            
        # Чистим JSON от лишних символов (AI любит добавлять ```json)
        cleaned_json = ai_json_str.replace("```json", "").replace("```", "").strip()
        
        try:
            ai_data = json.loads(cleaned_json)
        except Exception as e:
            print(f"⚠️ Failed to parse JSON: {e}. Raw: {cleaned_json[:50]}...")
            continue

        # 3. Сохраняем дайджесты
        for sub in subscriptions:
            user_id = sub['user_id']
            
            digest_data = {
                "user_id": user_id,
                "raw_email_id": email_obj['id'],
                "subject": email_obj.get('subject'),
                "summary_text": ai_data.get('summary_text', 'Error parsing'),
                "telegram_text": ai_data.get('telegram_text', 'Error parsing'),
                "is_sent": False
            }
            
            try:
                supabase.table("digests").insert(digest_data).execute()
                print(f"🎉 Digest saved for user {user_id}")
            except Exception as e:
                print(f"❌ DB Error: {e}")

        # 4. Помечаем письмо как обработанное
        supabase.table("raw_emails").update({"processed": True}).eq("id", email_obj['id']).execute()

if __name__ == "__main__":
    main()