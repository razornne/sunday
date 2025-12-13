import os
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai
import time

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# 🚀 ИСПОЛЬЗУЕМ ФЛАГМАН: GEMINI 2.5 PRO
# Если будет ошибка 429/404, поменяй на "gemini-2.0-flash"
model = genai.GenerativeModel(
    model_name="gemini-2.5-pro", 
    system_instruction="""
    Role: Senior Tech Editor & Curator for an elite Telegram channel.
    Task: Synthesize a set of newsletters into a high-value, readable Weekly Digest.

    INPUT DATA: A collection of newsletter texts about Tech, VC, and Startups.
    
    GOAL: Don't just summarize. Curate. Identify the biggest trends and most valuable insights. 
    Group related stories from different sources together.

    CRITICAL RULES (LANGUAGE & FORMAT):
    1. LANGUAGE: ENGLISH ONLY. Keep the original terminology. Do NOT translate.
    2. FORMAT: Use Telegram-compatible HTML tags ONLY: <b>, <i>, <a href="...">.
    3. TONE: Professional, insightful, concise ("Axios style" - Smart Brevity).

    STRUCTURE OF THE DIGEST:
    
    ☕ <b>Sunday Digest</b>
    
    [One short sentence intro about the main theme of the week]
    
    <b>🔥 Top Story</b>
    [The most important news item from all emails combined]
    • The core fact.
    • <i>Why it matters:</i> One sentence analysis.
    <a href='...'>Source</a>
    
    [Separator if needed, or just new lines]

    <b>🚀 VC & Startups</b>
    • Bullet point with key insight. <a href='...'>Link</a> (Source)
    • Bullet point with key insight. <a href='...'>Link</a> (Source)

    <b>🤖 AI & Tech</b>
    • Bullet point with key insight. <a href='...'>Link</a> (Source)
    
    <b>📊 Data & Trends</b>
    • Bullet point with key insight. <a href='...'>Link</a> (Source)

    ----------------
    
    QUALITY GUIDELINES:
    - SYNTHESIZE: If multiple newsletters talk about the same topic, combine them into one bullet point.
    - NO FLUFF: Remove marketing intros, sponsor messages, and generic advice.
    - LINKS: You MUST preserve the original links. Embed them in the text.
    """
)

def generate_digest():
    print("💎 Generating Premium Digest (Gemini 2.5 Pro)...")

    # 1. Берем письма
    response = supabase.table("raw_emails").select("*").eq("is_processed", False).execute()
    emails = response.data

    if not emails:
        print("No new emails.")
        return

    # 2. Готовим контент (High Quality Mode)
    # Даем модели много текста (до 8000 символов на письмо), чтобы она уловила все детали.
    emails_content = ""
    ids_to_update = []
    
    for email in emails:
        body_text = email['body_text'][:8000] 
        
        emails_content += f"\n=== SOURCE: {email['sender']} ===\n"
        emails_content += f"SUBJECT: {email['subject']}\n"
        emails_content += f"CONTENT:\n{body_text}\n" 
        ids_to_update.append(email['id'])

    print(f"📦 Input size: {len(emails_content)} chars. Sending to AI...")

    try:
        # Добавляем паузу 2 секунды перед запросом, чтобы не спамить API (вежливость)
        time.sleep(2)
        
        user_prompt = f"Analyze these newsletters and create a high-quality synthesis (English):\n{emails_content}"
        
        response = model.generate_content(user_prompt)
        digest_text = response.text.replace("```html", "").replace("```", "").strip()
        
        # Сохраняем
        supabase.table("digests").insert({"content_html": digest_text}).execute()
        
        # Обновляем статус
        for eid in ids_to_update:
            supabase.table("raw_emails").update({"is_processed": True}).eq("id", eid).execute()

        print("✅ Premium Digest Created & Saved.")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Совет: Если ошибка '429 Quota', попробуй поменять модель на 'gemini-2.0-flash' в коде.")

if __name__ == "__main__":
    generate_digest()