import os
import json
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv
from email.utils import parseaddr

load_dotenv()

# Настройки
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

def generate_summary(text):
    # ИСПОЛЬЗУЕМ НОВУЮ МОДЕЛЬ FLASH (Она быстрее и работает)
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    safe_text = text[:15000] if text else "No text" # Увеличил лимит, flash переварит больше
    
    prompt = f"""
    Ты - редактор дайджеста. Сделай краткую выжимку из текста.
    Текст: {safe_text} 
    
    Верни JSON с двумя полями:
    1. "summary_text": Подробный пересказ (Markdown) на русском языке.
    2. "telegram_text": Короткий пост (макс 400 символов) с эмодзи.
    
    Верни ТОЛЬКО чистый JSON, без ```json``` и лишних слов.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️ Error generating AI: {e}")
        return None

def main():
    print("🚀 Starting Summarizer (Gemini Flash Edition)...")

    # 1. ЗАГРУЖАЕМ ПОДПИСКИ
    try:
        all_subs = supabase.table("subscriptions").select("*").execute().data
        subs_map = {}
        for s in all_subs:
            # Пропускаем, если user_id не заполнен (защита от None)
            if not s.get('user_id'):
                continue
                
            # Считаем активным, если is_active True или NULL (по умолчанию)
            is_active = s.get('is_active')
            if is_active is False: 
                continue

            email_key = s['sender_email'].strip().lower()
            if email_key not in subs_map:
                subs_map[email_key] = []
            subs_map[email_key].append(s['user_id'])
            
        print(f"✅ Active whitelist loaded. Users ready: {len(subs_map)}")

    except Exception as e:
        print(f"❌ Error loading subscriptions: {e}")
        return

    # 2. ИЩЕМ ПИСЬМА
    response = supabase.table("raw_emails").select("*").eq("processed", False).execute()
    emails = response.data

    if not emails:
        print("💤 No new emails.")
        return

    print(f"📨 Found {len(emails)} new emails.")

    for email_obj in emails:
        raw_sender = email_obj.get('sender', '')
        name, clean_email = parseaddr(raw_sender)
        final_sender = clean_email.strip().lower() if clean_email else raw_sender.lower()
        
        print(f"Processing: '{final_sender}'")

        user_ids = subs_map.get(final_sender)

        if not user_ids:
            print(f"❌ '{final_sender}' not in whitelist. Skipping.")
            supabase.table("raw_emails").update({"processed": True}).eq("id", email_obj['id']).execute()
            continue
        
        print(f"✅ Generating digest for {len(user_ids)} user(s)...")

        # Генерируем AI
        content = email_obj.get('body_plain') or email_obj.get('body_html') or ""
        ai_raw = generate_summary(content)
        
        if not ai_raw:
            print("⚠️ AI generation failed.")
            continue
            
        # Чистим JSON
        cleaned_json = ai_raw.replace("```json", "").replace("```", "").strip()
        
        try:
            ai_data = json.loads(cleaned_json)
        except:
            print(f"⚠️ JSON Parse Error. AI Output: {cleaned_json[:50]}...")
            continue

        # Сохраняем
        for uid in user_ids:
            digest_data = {
                "user_id": uid,
                "raw_email_id": email_obj['id'],
                "subject": email_obj.get('subject'),
                "summary_text": ai_data.get('summary_text', 'Error'),
                "telegram_text": ai_data.get('telegram_text', 'Error'),
                "is_sent": False
            }
            supabase.table("digests").insert(digest_data).execute()
            print(f"🎉 Digest saved for user {uid}")

        # Помечаем готовым
        supabase.table("raw_emails").update({"processed": True}).eq("id", email_obj['id']).execute()

if __name__ == "__main__":
    main()