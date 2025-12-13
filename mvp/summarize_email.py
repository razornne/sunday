import os
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai
import time

load_dotenv()

# --- КОНФИГУРАЦИЯ ---
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# РОЛЬ ПОЛЬЗОВАТЕЛЯ (для персонализации)
# Можно менять на "ML Engineer", "Product Manager", "Investor" или оставить None
USER_ROLE = "Tech Founder" 

# Используем самую умную доступную модель
model = genai.GenerativeModel(
    model_name="gemini-2.5-pro", # или gemini-2.5-pro, если доступна
    system_instruction=f"""
    You are a strictly algorithmic Digest Generator. Your goal is to synthesize raw newsletters into a structured product.
    
    ### CONTEXT
    The user is a busy professional ({USER_ROLE if USER_ROLE else "General Tech Reader"}). 
    They need high-density information, zero fluff, and actionable insights.

    ### INPUT PROCESSING RULES
    1.  **Filter Garbage:** Ignore all greetings, footers, "unsubscribe" links, ads, and webinar promos.
    2.  **Synthesis:** If multiple emails mention the same event, MERGE them into a single bullet point.
    3.  **Fact-Checking:** Only output what is explicitly in the text. No hallucinations.
    4.  **Error Handling:** If the input text contains no news or valuable insights, output EXACTLY: "No meaningful content this week." and stop.

    ### STYLE GUIDELINES
    -   **No Meta-Talk:** NEVER say "The article mentions", "One newsletter discusses". Just state the fact.
    -   **Density:** Short sentences. High information density. No metaphors.
    -   **Format:** Facts → Insights.
    -   **Language:** English only.

    ### STRICT OUTPUT STRUCTURE (Markdown)

    # 🔥 Top Story
    [Select the single most significant news item of the week]
    [1-2 paragraphs summarizing the essence]
    
    * [Detail bullet 1]
    * [Detail bullet 2]
    
    **Why it matters:** [Specific impact analysis, not generalities]

    # 🚀 VC & Startups
    * [Fact/News] → [Mini-insight or implication]. ([Source Name])
    * [Fact/News] → [Mini-insight or implication]. ([Source Name])

    # 🤖 AI & Tech
    * [Fact/News] → [Mini-insight or implication]. ([Source Name])
    * [Fact/News] → [Mini-insight or implication]. ([Source Name])

    # 📊 Data & Trends
    * [Stat/Trend] → [Context]. ([Source Name])

    {"# 🎯 Why this matters for you (" + USER_ROLE + ")" if USER_ROLE else ""}
    {"* [Personalized insight 1 based on the role]" if USER_ROLE else ""}
    {"* [Personalized insight 2 based on the role]" if USER_ROLE else ""}

    ### END OF INSTRUCTION
    """
)

def generate_digest():
    print(f"💎 Generating Structured Digest (Role: {USER_ROLE})...")

    # 1. Забираем данные
    response = supabase.table("raw_emails").select("*").eq("is_processed", False).execute()
    emails = response.data

    if not emails:
        print("No new emails.")
        return

    # 2. Подготовка статистики (Meta Data)
    unique_sources = set()
    total_chars = 0
    clean_content = ""
    ids_to_update = []

    for email in emails:
        # Считаем статистику
        unique_sources.add(email['sender'])
        # Ограничиваем вход (8000 символов на письмо для качества)
        body_part = email['body_text'][:8000]
        total_chars += len(body_part)
        
        # Формируем контекст для AI
        clean_content += f"\n--- SOURCE: {email['sender']} ---\n"
        clean_content += f"SUBJECT: {email['subject']}\n"
        clean_content += f"{body_part}\n"
        
        ids_to_update.append(email['id'])

    print(f"📦 Stats: {len(emails)} emails, {len(unique_sources)} sources, {total_chars} chars.")

    try:
        # 3. Генерация через AI
        # Мы НЕ просим AI считать статистику, чтобы он не галлюцинировал. Мы добавим её сами.
        user_prompt = f"Generate the digest from this data:\n{clean_content}"
        
        response = model.generate_content(user_prompt)
        ai_output = response.text.replace("```html", "").replace("```markdown", "").replace("```", "").strip()

        # 4. Проверка на "пустой контент"
        if "No meaningful content" in ai_output:
            final_digest = "No meaningful content this week."
        else:
            # 5. Сборка финального продукта (AI текст + Python статистика)
            meta_summary = f"\n\n# 📦 Meta Summary\nCollected from {len(emails)} emails, {len(unique_sources)} sources, total input size {total_chars} chars."
            final_digest = ai_output + meta_summary

        # 6. Сохранение
        # Примечание: Мы сохраняем это как HTML (хоть это и Markdown), 
        # но deliver.py потом превратит \n в <br> и распарсит жирный шрифт.
        # Для идеального отображения в Telegram Markdown подходит лучше всего.
        
        supabase.table("digests").insert({"content_html": final_digest}).execute()
        
        # 7. Обновление статусов
        for eid in ids_to_update:
            supabase.table("raw_emails").update({"is_processed": True}).eq("id", eid).execute()

        print("✅ Structured Digest Created & Saved.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_digest()