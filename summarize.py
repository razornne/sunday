import os
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Настройки
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

def generate_summary(text):
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    Ты - редактор технического дайджеста. Твоя задача - сделать краткую выжимку из письма.
    
    Письмо:
    {text[:8000]} 
    
    Сделай 2 версии ответа в формате JSON:
    1. "summary_text": Подробный пересказ (Markdown) для сайта. Выдели главные мысли, ссылки и инсайты.
    2. "telegram_text": Очень короткий пост для Telegram (макс 400 символов). Начни с эмодзи.
    
    Верни ТОЛЬКО валидный JSON без лишних слов.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating AI: {e}")
        return None

def main():
    print("🚀 Starting Summarizer...")

    # 1. Берем НЕОБРАБОТАННЫЕ письма (processed = FALSE)
    response = supabase.table("raw_emails").select("*").eq("processed", False).execute()
    emails = response.data

    if not emails:
        print("💤 No new emails to process.")
        return

    print(f"📨 Found {len(emails)} new emails.")

    for email in emails:
        sender = email.get('sender')
        print(f"Processing email from: {sender}")

        # 2. Ищем ВЛАДЕЛЬЦА подписки (Кто подписан на этого отправителя?)
        # ВАЖНО: Мы ищем user_id в таблице subscriptions, у которого sender_email совпадает
        sub_response = supabase.table("subscriptions").select("user_id")\
            .eq("sender_email", sender).eq("is_active", True).execute()
        
        subscriptions = sub_response.data

        if not subscriptions:
            print(f"❌ Sender {sender} is not in whitelist. Marking as processed & Skipping.")
            # Помечаем как обработанное, чтобы не застрять на нем вечно
            supabase.table("raw_emails").update({"processed": True}).eq("id", email['id']).execute()
            continue
        
        # Если подписано несколько людей на одну рассылку, создаем дайджест для КАЖДОГО
        import json
        
        # Генерируем AI контент (один раз на письмо)
        raw_text = email.get('body_plain', '') or "No text content"
        ai_json_str = generate_summary(raw_text)
        
        if not ai_json_str:
            print("⚠️ AI failed to generate summary.")
            continue
            
        # Чистим JSON от Markdown кавычек если они есть
        ai_json_str = ai_json_str.replace("```json", "").replace("```", "")
        
        try:
            ai_data = json.loads(ai_json_str)
        except:
            print("⚠️ Failed to parse JSON from AI.")
            continue

        # 3. Сохраняем дайджесты для всех подписчиков
        for sub in subscriptions:
            user_id = sub['user_id']
            
            digest_data = {
                "user_id": user_id,
                "raw_email_id": email['id'],
                "subject": email.get('subject'),
                "summary_text": ai_data.get('summary_text'),
                "telegram_text": ai_data.get('telegram_text'),
                "is_sent": False
            }
            
            supabase.table("digests").insert(digest_data).execute()
            print(f"✅ Digest created for user {user_id}")

        # 4. Помечаем письмо как обработанное
        supabase.table("raw_emails").update({"processed": True}).eq("id", email['id']).execute()

if __name__ == "__main__":
    main()