import os
import json
import smtplib
import google.generativeai as genai 
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# --- CONFIG ---
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def send_email_report(to_email, subject, html_body):
    if not os.environ.get("EMAIL_USER"): return False
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Sunday AI <{os.environ.get('EMAIL_USER')}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))
        with smtplib.SMTP(os.environ.get("SMTP_SERVER", "smtp.gmail.com"), 587) as server:
            server.starttls()
            server.login(os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASS"))
            server.sendmail(os.environ.get("EMAIL_USER"), to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

def get_ai_synthesis(emails_text, profile):
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
    ROLE: {profile.get('role', 'Professional')}. 
    FOCUS: {profile.get('focus_areas')}.
    
    TASK: Synthesize the following emails into a high-value weekly brief.
    Return STRICT JSON:
    {{
      "big_picture": "one sentence overarching summary",
      "trends": [
        {{"title": "trend heading", "insight": "why this matters for the user's role"}}
      ],
      "noise_filter": "topics ignored as fluff"
    }}

    EMAILS:
    {emails_text}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(text)
    except: return None

def main():
    now = datetime.utcnow()
    current_day = now.strftime("%A")
    current_hour = now.strftime("%H:00")
    
    print(f"⏰ Checking schedule for: {current_day} {current_hour} UTC")

    users_res = supabase.table("profiles").select("*").eq("digest_day", current_day).execute()
    
    if not users_res.data:
        print("💤 No users scheduled for today.")
        return

    for user in users_res.data:
        user_time = user.get('digest_time', '09:00')[:5]
        if user_time != current_hour[:5]:
            continue

        uid = user['id']
        emails_res = supabase.table("raw_emails").select("*").eq("user_id", uid).eq("processed", False).execute()
        
        if not emails_res.data:
            print(f"📪 No new mail for {user['email']}")
            continue

        context = ""
        email_ids = []
        for e in emails_res.data:
            context += f"From: {e['sender']}\nSubj: {e['subject']}\nText: {e['body_plain'][:1500]}\n---\n"
            email_ids.append(e['id'])

        synthesis = get_ai_synthesis(context, user)
        if synthesis:
            digest_obj = {
                "user_id": uid,
                "structured_content": synthesis,
                "source_email_ids": email_ids,
                "subject": f"Sunday Brief: {synthesis['big_picture'][:50]}..."
            }
            supabase.table("digests").insert(digest_obj).execute()

            html_report = f"""
            <div style="font-family: sans-serif; color: #333; max-width: 600px;">
                <h2 style="color: #2e86de;">☀️ Your Sunday Brief</h2>
                <div style="background: #f0f7ff; padding: 15px; border-radius: 8px; border-left: 4px solid #2e86de;">
                    <strong>Big Picture:</strong><br>{synthesis['big_picture']}
                </div>
                <h3>Key Trends & Insights:</h3>
                {''.join([f"<b>{t['title']}</b><p>{t['insight']}</p>" for t in synthesis['trends']])}
                <hr>
                <p style="font-size: 11px; color: #999;">Noise Filtered: {synthesis['noise_filter']}</p>
            </div>
            """
            if send_email_report(user['email'], digest_obj['subject'], html_report):
                for eid in email_ids:
                    supabase.table("raw_emails").update({"processed": True}).eq("id", eid).execute()
                print(f"🚀 Brief sent to {user['email']}")

if __name__ == "__main__":
    main()