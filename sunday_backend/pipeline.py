import os
import json
import re
import smtplib
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from google import genai
from supabase import create_client, Client
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Загрузка .env
load_dotenv()

# --- CONFIG (БЕЗОПАСНАЯ ИНИЦИАЛИЗАЦИЯ) ---
# Чтобы Streamlit не падал, если ключи еще не прогрузились
try:
    import streamlit as st
    def get_secret(key): return os.environ.get(key) or st.secrets.get(key)
except:
    def get_secret(key): return os.environ.get(key)

SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
GEMINI_KEY = get_secret("GEMINI_API_KEY")
EMAIL_USER = get_secret("EMAIL_USER")
EMAIL_PASS = get_secret("EMAIL_PASS")

# 1. Supabase Init
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Supabase Init Error: {e}")
        supabase = None
else:
    print("⚠️ Supabase Keys Missing")
    supabase = None

# 2. Gemini Init (БЕЗ ЭТОГО APP.PY УПАДЕТ ПРИ ИМПОРТЕ)
if GEMINI_KEY:
    try:
        client = genai.Client(api_key=GEMINI_KEY)
    except Exception as e:
        print(f"⚠️ Gemini Client Error: {e}")
        client = None
else:
    print("⚠️ GEMINI_API_KEY Missing")
    client = None

# --- UTILS ---

def clean_json_response(text):
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()

def generate_email_html(digest_data):
    summary = digest_data.get('big_picture', 'See details below.')
    current_date = datetime.now().strftime('%B %d, %Y')
    
    html = f"""
    <html>
    <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #111; margin: 0;">Sunday Brief ☕</h1>
            <p style="color: #666; font-size: 14px;">{current_date}</p>
        </div>
        <div style="background: #eff6ff; padding: 25px; border-radius: 12px; margin-bottom: 30px; border-left: 6px solid #3b82f6;">
            <h2 style="color: #1e3a8a; margin-top: 0; font-size: 18px;">🌍 The Big Picture</h2>
            <p style="line-height: 1.6; font-size: 16px; color: #1e40af; margin-bottom: 0;">{summary}</p>
        </div>
        <h3 style="border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 30px;">📊 Key Strategic Insights</h3>
    """
    
    trends = digest_data.get('trends', [])
    if not trends:
        html += "<p style='color: #777; font-style: italic;'>No major trends detected this week.</p>"
    
    for t in trends:
        title = t.get('title', 'Insight')
        body = t.get('insight', '')
        html += f"""
        <div style="margin-bottom: 25px;">
            <h4 style="margin: 0 0 8px 0; color: #111827; font-size: 16px; font-weight: 700;">{title}</h4>
            <p style="margin: 0; color: #4b5563; font-size: 15px; line-height: 1.5;">{body}</p>
        </div>
        """

    actions = digest_data.get('action_items', [])
    if actions:
        html += """
        <div style="background: #fff1f2; padding: 20px; border-radius: 12px; margin-top: 30px; border: 1px solid #fecdd3;">
            <h3 style="color: #9f1239; margin-top: 0; font-size: 16px;">🚀 Action Items</h3>
            <ul style="margin-bottom: 0; padding-left: 20px;">"""
        for act in actions:
            html += f"<li style='color: #881337; margin-bottom: 8px; font-size: 15px;'>{act}</li>"
        html += "</ul></div>"

    html += """
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center;">
            <p style="color: #9ca3af; font-size: 12px;">by Sunday AI</p>
        </div>
    </body>
    </html>
    """
    return html

def send_email(to_email, subject, html_body):
    if not EMAIL_USER or not EMAIL_PASS:
        print("⚠️ SMTP credentials missing.")
        return False
        
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Sunday AI <{EMAIL_USER}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(smtp_server, 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
        print(f"📨 Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ SMTP Error: {e}")
        return False

# ==========================================
# 🍳 STAGE 1: JUNIOR CHEF (Email Summarizer)
# ==========================================
def summarize_single_email(email_body, sender, subject):
    """
    Анализирует ОДНО письмо.
    """
    if not client: return None

    # ТВОЙ ОРИГИНАЛЬНЫЙ ПРОМПТ
    prompt = f"""
    ROLE: You are an Expert Content Analyst for a Newsletter Aggregator.
    
    OBJECTIVE: Extract the core value from this email. 
    
    CRITICAL RULES:
    1. **NEWSLETTERS ARE GOLD.** Unlike standard filters, you MUST treat Newsletters (Substack, beehiiv, Medium, Industry Reports) as HIGH PRIORITY content.
    2. Ignore transactional fluff (password resets, login codes, delivery updates) -> Mark as 'Noise'.
    3. Ignore pure marketing spam (Buy now 50% off) -> Mark as 'Noise'.
    4. If it's a Newsletter: Extract the main topic and a detailed summary of the insights.

    INPUT EMAIL:
    From: {sender}
    Subject: {subject}
    Body: {email_body[:8000]} (truncated)

    OUTPUT JSON format only:
    {{
        "category": "Newsletter" | "Personal" | "Transactional" | "Noise",
        "topic": "Short title of the topic (e.g. 'AI Agent Frameworks' or 'Crypto Market Update')",
        "summary": "3-4 sentences packed with the actual facts/insights from the text. Be specific.",
        "importance": 1-5 (5 = High Signal Newsletter, 1 = Spam/Noise)
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-3-pro-preview", # <-- ТВОЯ МОДЕЛЬ
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(clean_json_response(response.text))
    except Exception as e:
        print(f"⚠️ Junior Chef Error: {e}")
        return None

# ==========================================
# 👨‍🍳 STAGE 2: HEAD CHEF (Smart Contextual Synthesis)
# ==========================================
def synthesize_weekly_report(summaries, user_profile):
    """
    Пишет отчет, учитывая РАЗНЫЕ интересы пользователя.
    """
    if not client: return None

    context_text = ""
    for item in summaries:
        context_text += f"- [{item['topic']}] ({item['category']}): {item['summary']} (Signal: {item['importance']}/5)\n\n"

    role = user_profile.get('role', 'Founder')
    focus_areas = ", ".join(user_profile.get('focus_areas', []) or ["General Tech"])

    # ТВОЙ ОРИГИНАЛЬНЫЙ ПРОМПТ
    prompt = f"""
    ROLE: You are an Elite Strategic Advisor for a {role}.
    
    USER PROFILE & INTERESTS:
    The user is a polymath with a diverse portfolio of interests. 
    **Their Focus Areas:** {focus_areas}.

    INPUT DATA:
    A list of pre-summarized items from various newsletters (SaaS, Defense, Finance, etc.).

    TASK:
    Create a "Deep-Dive Strategic Brief" that respects the DIVERSITY of the input.
    
    CRITICAL INSTRUCTIONS (The "Smart Context" Logic):
    1. **MATCH THE LENS:** When analyzing a trend, view it through the lens of the specific Focus Area it belongs to. 
    2. **SYNTHESIZE, DON'T LIST:** If you see 3 items about Defense, combine them into ONE deep insight.
    3. **DENSITY & DEPTH:** Write comprehensive paragraphs (100-150 words per trend). Explain the "So What?"

    OUTPUT JSON:
    {{
      "big_picture": "A rich 3-4 sentence editorial synthesizing the macro vibe across ALL interests.",
      "trends": [
        {{ 
            "title": "Insight Headline (Specific to the Industry)", 
            "insight": "Deep analysis. Context + Strategic Implication for that specific Focus Area." 
        }}
      ],
      "action_items": ["Strategic task 1", "Review item 2"],
      "noise_filter": "Processed X inputs..."
    }}

    DATA:
    {context_text}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", # <-- ТВОЯ МОДЕЛЬ
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(clean_json_response(response.text))
    except Exception as e:
        print(f"⚠️ Head Chef Error: {e}")
        return None

# ==========================================
# 🚀 PUBLIC FUNCTION: RUN DIGEST
# ==========================================

def run_digest(user_id):
    if not supabase or not client:
        print("❌ Pipeline halted: Missing API Keys.")
        return False

    print(f"🚀 Starting pipeline for user: {user_id}")
    
    try:
        # 1. Получаем профиль
        user_res = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if not user_res.data:
            print("❌ User not found")
            return False
        
        user = user_res.data[0]
        
        # 2. Обработка сырых писем (Junior Chef)
        raw_emails = supabase.table("raw_emails") \
            .select("*") \
            .eq("user_id", user_id) \
            .neq("processing_status", "summarized") \
            .execute()
        
        if raw_emails.data:
            print(f"  🍳 Cooking {len(raw_emails.data)} raw emails...")
            for email in raw_emails.data:
                summary_data = summarize_single_email(
                    email['body_plain'], email['sender'], email['subject']
                )
                if summary_data:
                    supabase.table("email_summaries").insert({
                        "user_id": user_id,
                        "source_email_id": email['id'],
                        "topic": summary_data.get('topic', 'No Topic'),
                        "summary": summary_data.get('summary', ''),
                        "category": summary_data.get('category', 'Noise'),
                        "importance": summary_data.get('importance', 1)
                    }).execute()
                    
                    supabase.table("raw_emails").update({"processing_status": "summarized"}) \
                        .eq("id", email['id']).execute()

        # 3. Генерация отчета (Head Chef)
        pending_summaries = supabase.table("email_summaries") \
            .select("*") \
            .eq("user_id", user_id) \
            .is_("digest_id", "null") \
            .gt("importance", 2) \
            .execute()
            
        if not pending_summaries.data:
            print("  💤 Not enough content (high importance) for a digest.")
            return False
            
        print(f"  👨‍🍳 Head Chef synthesising {len(pending_summaries.data)} items...")
        
        final_brief = synthesize_weekly_report(pending_summaries.data, user)
        
        if final_brief:
            digest_res = supabase.table("digests").insert({
                "user_id": user_id,
                "user_email": user.get('personal_email'),
                "summary_text": final_brief.get('big_picture'),
                "structured_content": final_brief, 
                "period_start": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
                "period_end": datetime.now(timezone.utc).isoformat(),
                "is_sent": True 
            }).execute()
            
            new_digest_id = digest_res.data[0]['id']
            summary_ids = [s['id'] for s in pending_summaries.data]
            supabase.table("email_summaries").update({"digest_id": new_digest_id}) \
                .in_("id", summary_ids).execute()

            print("  ✨ Digest Created!")

            email_html = generate_email_html(final_brief)
            send_email(user.get('personal_email'), f"☕ Your Sunday Brief", email_html)
            
            return True
        
        return False
    except Exception as e:
        print(f"❌ CRITICAL PIPELINE ERROR: {e}")
        return False

if __name__ == "__main__":
    print("Run this file via app.py or scheduler.py")