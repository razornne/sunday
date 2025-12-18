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

# --- CONFIGURATION ---
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def send_email(to_email, subject, html_body):
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
        print(f"Error sending email: {e}")
        return False

def get_ai_synthesis(emails_text, profile):
    """
    The 'Perfect' Prompt Engine
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    role = profile.get('role', 'Professional')
    focus = ", ".join(profile.get('focus_areas', []))
    
    prompt = f"""
    ROLE: You are an elite Strategy Consultant and Chief of Staff for a user who is a "{role}".
    THEIR FOCUS: {focus}.
    
    TASK: Analyze the provided batch of emails and synthesize them into a high-signal "Sunday Brief". 
    Your goal is to save the user hours of reading by providing deep insights, not just summaries.

    ANALYSIS RULES:
    1. SYNTHESIZE: If multiple emails discuss the same topic, group them into one powerful trend.
    2. SO WHAT?: For every trend, explain why it matters specifically to a "{role}" with focus on {focus}.
    3. SIGNAL OVER NOISE: Ruthlessly ignore transactional notifications, login alerts, and marketing fluff unless they represent a major industry shift.
    4. ACTIONABLE: Highlight any hidden opportunities or risks mentioned in the texts.

    OUTPUT FORMAT (Strict JSON only):
    {{
      "big_picture": "A 2-sentence sophisticated executive summary of the week's narrative.",
      "trends": [
        {{
          "title": "Short, punchy title with a relevant emoji",
          "insight": "High-density analysis explaining the 'so what'. Use Markdown for bolding key terms."
        }}
      ],
      "noise_filter": "Briefly mention what types of fluff you discarded (e.g., '14 marketing promos from X and Y')."
    }}

    EMAILS DATA:
    {emails_text}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean potential markdown wrapping
        raw_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(raw_text)
    except Exception as e:
        print(f"AI Synthesis failed: {e}")
        return None

def get_html_template(synthesis):
    """
    Premium Email Design
    """
    trends_html = "".join([f"""
        <div style="margin-bottom: 25px; padding: 20px; border-radius: 12px; border: 1px solid #eef2f6; background-color: #ffffff;">
            <h3 style="margin: 0 0 10px 0; color: #1a73e8; font-size: 18px; font-weight: 600;">{t['title']}</h3>
            <div style="color: #3c4043; font-size: 15px; line-height: 1.6;">{t['insight']}</div>
        </div>
    """ for t in synthesis.get('trends', [])])

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f9fa; padding: 30px; margin: 0;">
        <div style="max-width: 600px; margin: auto; background-color: transparent;">
            <div style="padding-bottom: 20px; text-align: left;">
                <span style="font-size: 24px; font-weight: 800; color: #1a73e8;">Sunday AI</span>
                <div style="color: #70757a; font-size: 14px; margin-top: 5px;">Your Intelligence Briefing</div>
            </div>

            <div style="background: linear-gradient(135deg, #1a73e8 0%, #1557b0 100%); padding: 30px; border-radius: 16px; color: white; margin-bottom: 30px; box-shadow: 0 4px 20px rgba(26, 115, 232, 0.2);">
                <h2 style="margin: 0 0 10px 0; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9;">The Big Picture</h2>
                <p style="margin: 0; font-size: 18px; line-height: 1.5; font-weight: 500;">{synthesis.get('big_picture')}</p>
            </div>

            <h2 style="font-size: 16px; color: #3c4043; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 20px; padding-left: 5px;">Deep Insights</h2>
            {trends_html}

            <div style="text-align: center; margin-top: 30px; padding: 20px; border-top: 1px solid #dadce0;">
                <p style="color: #70757a; font-size: 12px; line-height: 1.6;">
                    <strong>Noise Filter:</strong> {synthesis.get('noise_filter')}<br>
                    Generated by Sunday AI for your secure inbox.
                </p>
                <div style="margin-top: 15px;">
                    <a href="https://sunday-digest.streamlit.app" style="color: #1a73e8; text-decoration: none; font-size: 13px; font-weight: 600;">Manage Settings</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

def main():
    now = datetime.utcnow()
    cur_day, cur_hour = now.strftime("%A"), now.strftime("%H:00")
    print(f"🚀 Sunday AI Run: {cur_day} {cur_hour} UTC")

    # 1. Fetch users scheduled for THIS specific hour
    users = supabase.table("profiles").select("*").eq("digest_day", cur_day).execute()
    
    for user in users.data:
        # Check time match
        if user.get('digest_time', '09:00')[:5] != cur_hour[:5]:
            continue
            
        print(f"📦 Processing brief for: {user['email']}")
        
        # 2. Fetch unread emails
        emails = supabase.table("raw_emails").select("*").eq("user_id", user['id']).eq("processed", False).execute()
        
        if not emails.data:
            print(f"💤 No new data for {user['email']}. Skipping.")
            continue

        # 3. Prepare AI context
        context = ""
        for e in emails.data:
            context += f"SOURCE: {e['sender']}\nSUBJECT: {e['subject']}\nCONTENT: {e['body_plain'][:2000]}\n---\n"

        # 4. Generate & Deliver
        synthesis = get_ai_synthesis(context, user)
        if synthesis:
            html_report = get_html_template(synthesis)
            subject = f"Sunday Brief: {synthesis['big_picture'][:50]}..."
            
            if send_email(user['email'], subject, html_report):
                # Save to DB history
                supabase.table("digests").insert({
                    "user_id": user['id'], 
                    "structured_content": synthesis, 
                    "subject": subject
                }).execute()
                
                # Mark as processed
                for e in emails.data:
                    supabase.table("raw_emails").update({"processed": True}).eq("id", e['id']).execute()
                print(f"✅ Success: Brief delivered to {user['email']}")
            else:
                print(f"❌ Failed to send email to {user['email']}")

if __name__ == "__main__":
    main()