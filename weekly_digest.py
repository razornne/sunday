import os
import json
import smtplib
import requests
import google.generativeai as genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart  # <--- Вот он, потерянный герой!
from supabase import create_client, Client
from dotenv import load_dotenv
from email.utils import parseaddr
from datetime import date, datetime
import markdown

load_dotenv()

# --- CONFIGURATION ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# --- HELPER FUNCTIONS ---

def send_telegram_alert(chat_id, text):
    """Sends a push notification to Telegram."""
    if not TG_TOKEN or not chat_id: return False
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except: pass

def send_email_report(to_email, subject, html_content):
    """Sends the rich HTML digest via SMTP."""
    if not EMAIL_USER or not EMAIL_PASS: 
        print("⚠️ Email creds missing.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = "Sunday AI <bot@sundayai.dev>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
        print(f"📧 Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email Error: {e}")
        return False

# --- CORE ANALYTICS ENGINE ---

def synthesize_week(emails_context, user_profile):
    """
    The Brain: Converts raw text batches into structured intelligence.
    """
    model = genai.GenerativeModel("gemini-2.5-flash") 
    
    role = user_profile.get('role', 'General User')
    focus = ", ".join(user_profile.get('focus_areas', [])) or "General Tech"
    
    prompt = f"""
    ROLE:
    You are an elite Chief of Staff for a user with the role: "{role}".
    Their specific focus areas are: {focus}.

    OBJECTIVE:
    Synthesize the provided batch of emails into a high-value "Sunday Brief".
    DO NOT summarize email by email. Instead, synthesize information into trends and insights.
    
    CORE RULES:
    1. **Signal over Noise:** Prioritize emails with higher "Trust Score". If a low-trust source contradicts a high-trust one, ignore the low-trust one.
    2. **Synthesis:** If multiple emails talk about the same topic, combine them into one powerful insight.
    3. **Personalization:** Explain WHY this matters for a "{role}".
    4. **Structure:** Use Markdown for formatting.

    INPUT DATA (List of emails):
    {emails_context}

    OUTPUT FORMAT (Strict JSON only):
    {{
        "big_picture": "One paragraph (Markdown). The overarching narrative of the week.",
        "trends": [
            {{
                "title": "Trend Title (Start with an Emoji)",
                "insight": "Deep analysis: What happened and why it matters? (Markdown)",
                "sources_indices": [1, 3] 
            }}
        ],
        "noise_filter": "List of topics you filtered out.",
        "telegram_teaser": "Punchy teaser (max 400 chars) with emoji."
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"⚠️ AI Synthesis Error: {e}")
        return None

def main():
    print("🚀 Starting Weekly Synthesizer (v0.1 - SaaS Edition)...")
    
    # 1. LOAD CONFIGURATION
    try:
        subs_resp = supabase.table("subscriptions").select("*").execute()
        subs_map = {} 
        
        user_ids = set()
        for s in subs_resp.data:
            if not s.get('is_active'): continue
            key = s['sender_email'].strip().lower()
            if key not in subs_map: subs_map[key] = []
            subs_map[key].append(s)
            user_ids.add(s['user_id'])
            
        if not user_ids:
            print("💤 No active users found.")
            return

        profiles_resp = supabase.table("profiles").select("*").in_("id", list(user_ids)).execute()
        profiles_map = {p['id']: p for p in profiles_resp.data}
        
        print(f"✅ Config loaded. Processing for {len(profiles_map)} users.")

    except Exception as e:
        print(f"❌ Config Loading Error: {e}")
        return

    # 2. COLLECT RAW EMAILS
    raw_resp = supabase.table("raw_emails").select("*").eq("processed", False).execute()
    raw_emails = raw_resp.data
    
    if not raw_emails:
        print("💤 No new emails to process.")
        return

    user_batches = {} 
    processed_ids = [] 

    for email in raw_emails:
        sender_raw = email.get('sender', '')
        _, clean_email = parseaddr(sender_raw)
        sender_key = clean_email.strip().lower()
        
        subscribers = subs_map.get(sender_key)
        
        if not subscribers:
            print(f"🗑️ Skipping email from {sender_key}")
            processed_ids.append(email['id'])
            continue
            
        for sub in subscribers:
            uid = sub['user_id']
            if uid not in user_batches: user_batches[uid] = []
            
            user_batches[uid].append({
                "index": len(user_batches[uid]) + 1,
                "id": email['id'], 
                "subject": email.get('subject', 'No Subject'),
                "body": email.get('body_plain') or email.get('body_html') or "",
                "trust": sub.get('trust_score', 5),
                "alias": sub.get('source_alias') or sender_key
            })
            
        if email['id'] not in processed_ids:
            processed_ids.append(email['id'])

    # 3. SYNTHESIZE & DELIVER
    for uid, batch in user_batches.items():
        profile = profiles_map.get(uid)
        if not profile: continue
        
        print(f"🧠 Synthesizing digest for {profile.get('email')} (Batch size: {len(batch)})...")
        
        context_str = ""
        email_ids = []
        for item in batch:
            safe_body = item['body'][:8000] 
            context_str += f"\n--- EMAIL #{item['index']} ---\n"
            context_str += f"From: {item['alias']} (Trust Score: {item['trust']}/10)\n"
            context_str += f"Subject: {item['subject']}\n"
            context_str += f"Content: {safe_body}\n"
            email_ids.append(item['id'])
            
        ai_result = synthesize_week(context_str, profile)
        
        if not ai_result:
            print("❌ AI Generation Failed.")
            continue
            
        # 4. SAVE & SEND
        digest_data = {
            "user_id": uid,
            "period_end": datetime.now().isoformat(),
            "source_email_ids": email_ids, # Теперь это массив чисел, всё ок!
            "structured_content": ai_result,
            "subject": f"Sunday Brief: {ai_result.get('trends', [{}])[0].get('title', 'Weekly Update')}",
            "summary_text": ai_result.get('big_picture', ''), 
            "telegram_text": ai_result.get('telegram_teaser', ''),
            "is_sent": True
        }
        
        try:
            supabase.table("digests").insert(digest_data).execute()
            print("💾 Digest saved to DB.")
        except Exception as e:
            print(f"❌ DB Save Error: {e}")

        # Telegram
        if profile.get('telegram_chat_id'):
            msg = f"{ai_result.get('telegram_teaser')}\n\n🔗 [Open Dashboard](https://sunday-digest.streamlit.app)"
            send_telegram_alert(profile.get('telegram_chat_id'), msg)
            
        # Email
        if profile.get('email'):
            trends_html = ""
            for t in ai_result.get('trends', []):
                refs = ", ".join([f"[{i}]" for i in t.get('sources_indices', [])])
                trends_html += f"<h3>{t['title']} <span style='font-size:12px;color:#888'>{refs}</span></h3>"
                trends_html += markdown.markdown(t['insight'])
            
            full_html = f"""
            <html><body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; line-height: 1.6; color: #333;">
                <div style="text-align:center; padding: 20px 0;">
                    <h1 style="color: #2e86de; margin:0;">Sunday Brief</h1>
                    <p style="color: #666; font-size: 14px;">One inbox in. One decision-ready brief out.</p>
                </div>
                <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; font-style: italic; color: #555;">
                    {ai_result.get('big_picture')}
                </div>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                {trends_html}
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">Filtered Noise: {ai_result.get('noise_filter')}</p>
            </body></html>
            """
            send_email_report(profile.get('email'), digest_data['subject'], full_html)

    # 5. CLEANUP
    if processed_ids:
        for pid in processed_ids:
            supabase.table("raw_emails").update({"processed": True}).eq("id", pid).execute()
        print(f"🧹 Marked {len(processed_ids)} emails as processed.")

if __name__ == "__main__":
    main()