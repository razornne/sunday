import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

load_dotenv()

# Настройки
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# РОЛЬ (для контекста)
USER_ROLE = "Tech Founder"

# Промпт требует вернуть JSON
model = genai.GenerativeModel(
    model_name="gemini-2.5-pro", # или gemini-1.5-pro-latest
    generation_config={"response_mime_type": "application/json"},
    system_instruction=f"""
    You are an Elite Tech Editor. create TWO distinct versions of a digest.
    User Role: {USER_ROLE}.
    
    ### INPUT PROCESSING
    1. Filter out garbage (ads, intros, footers).
    2. Merge related stories into single bullets.
    3. IMPORTANT: Do NOT generate a "Meta" or "Stats" section in the JSON. The system adds it automatically.

    ### OUTPUT FORMAT (JSON)
    Return a JSON object with exactly two keys: "telegram_digest" and "email_digest".

    --------------------------------------------------------
    1. "telegram_digest" (Markdown) - Optimized for Mobile Reading
    Structure requirements:
    - Use neat spacing (empty lines between blocks).
    - Links must be embedded: [Source Name](URL).
    - NO indentation at the start of lines.
    
    Template:
    # 🔥 Top Story: [Title]
    [1 sentence summary of the main event]
    
    • [Detail 1]
    • [Detail 2]
    
    **Why it matters:** [Insight/Analysis]

    # 🚀 VC & Startups
    • [Fact] → [Implication]. ([Source Name](URL))
    • [Fact] → [Implication]. ([Source Name](URL))

    # 🤖 AI & Tech
    • [Fact] → [Implication]. ([Source Name](URL))

    --------------------------------------------------------
    2. "email_digest" (HTML) - Journalistic Style
    Structure requirements:
    - Use <h3> for headers.
    - Use <p> for text.
    - Use <ul><li> for lists.
    - Use <strong> for emphasis.
    
    Template:
    <h3>🔥 Top Story: [Title]</h3>
    <p><b>Why it matters:</b> [Insight]</p>
    <p>[Context/Summary]</p>
    <ul>
        <li>[Detail 1] <a href="URL">Source</a></li>
        <li>[Detail 2]</li>
    </ul>

    <h3>🚀 VC & Startups</h3>
    <ul>
        <li>[Fact] → [Implication]. <a href="URL">Source</a></li>
    </ul>
    """
)

def generate_digest():
    print("💎 Generating Beautified Digest (JSON Mode)...")

    # 1. Забираем письма
    response = supabase.table("raw_emails").select("*").eq("is_processed", False).execute()
    emails = response.data

    if not emails:
        print("No new emails.")
        return

    # 2. Готовим данные
    clean_content = ""
    unique_sources = set()
    total_chars = 0
    ids_to_update = []

    for email in emails:
        # Увеличим лимит для Pro модели, чтобы она вникла в детали
        body_part = email['body_text'][:10000]
        unique_sources.add(email['sender'])
        total_chars += len(body_part)
        clean_content += f"\n--- SOURCE: {email['sender']} ---\nSUBJECT: {email['subject']}\n{body_part}\n"
        ids_to_update.append(email['id'])

    print(f"📦 Input: {len(emails)} emails, {total_chars} chars.")

    try:
        # 3. Генерация
        user_prompt = f"Generate digests based on this data:\n{clean_content}"
        response = model.generate_content(user_prompt)
        
        # Парсим JSON
        result = json.loads(response.text)
        
        tg_text = result.get("telegram_digest", "Error generating Telegram text")
        email_html = result.get("email_digest", "Error generating Email HTML")

        # 4. Добавляем статистику (Python) - ОДИН РАЗ
        # Используем моноширинный шрифт для цифр в ТГ (`code`)
        meta_stats = f"\n\n📦 `Meta: {len(emails)} emails, {len(unique_sources)} sources`"
        tg_text += meta_stats
        
        # 5. Сохраняем
        data_to_insert = {
            "telegram_text": tg_text,
            "email_html": email_html
        }
        supabase.table("digests").insert(data_to_insert).execute()

        # 6. Помечаем как обработанные
        for eid in ids_to_update:
            supabase.table("raw_emails").update({"is_processed": True}).eq("id", eid).execute()

        print("✅ Success! Beautified formats saved.")

    except Exception as e:
        print(f"❌ Error: {e}")
        try: print("Raw response:", response.text) 
        except: pass

if __name__ == "__main__":
    generate_digest()