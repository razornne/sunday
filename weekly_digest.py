import os
import json
import smtplib
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from supabase import create_client, Client
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Загрузка переменных окружения
load_dotenv()

# --- ИНИЦИАЛИЗАЦИЯ КЛИЕНТОВ ---
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"), 
    os.environ.get("SUPABASE_KEY")
)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def log_event(user_id, status, emails_count=0, error_msg=None):
    """Запись каждого запуска в таблицу run_logs для мониторинга бизнеса"""
    try:
        supabase.table("run_logs").insert({
            "user_id": user_id,
            "status": status,
            "emails_processed": emails_count,
            "error_message": error_msg
        }).execute()
    except Exception as e:
        print(f"   ⚠️ Ошибка записи лога: {e}")

def send_email(to_email, subject, html_body):
    """Отправка HTML-письма через SMTP"""
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
        print(f"   ❌ SMTP Error: {e}")
        return False

def get_ai_synthesis(emails_text, profile):
    """
    Генерация стратегического дайджеста через Gemini 1.5 Flash.
    Используется роль Chief of Staff для максимальной ценности контента.
    """
    role = profile.get('role', 'Professional')
    focus = ", ".join(profile.get('focus_areas', []))
    
    prompt = f"""
    ROLE: You are an Elite AI Chief of Staff and Strategic Consultant. 
    YOUR CLIENT: A high-level "{role}" whose primary focus is: {focus}.

    TASK: Analyze the provided email data and synthesize it into a high-signal "Sunday Brief". 
    Your goal is to save the client 2 hours of manual inbox review.

    STRATEGIC GUIDELINES:
    1. FILTER THE NOISE: Ignore automated notifications, password resets, and generic marketing unless they impact: {focus}.
    2. CONNECT THE DOTS: Identify patterns. Combine multiple related emails into one strategic trend.
    3. TONE: Professional, analytical, concise. Use "we" and "you" to build a partnership feel.
    4. DENSITY: Every word must add value. Avoid phrases like "In this email...".

    OUTPUT STRUCTURE (Strict JSON format):
    {{
      "big_picture": "Summary of the week in 2-3 sentences. Strategic vibe and most important takeaway.",
      "trends": [
        {{
          "title": "🔍 Topic Name (with emoji)",
          "insight": "Strategic analysis. Use **bold** for key names/dates. Explain WHY this matters."
        }}
      ],
      "action_items": [
        "Critical tasks, deadlines, or follow-ups (max 3)."
      ],
      "noise_filter": "Summary of what was filtered out (e.g. '12 newsletters and 5 Jira updates removed')."
    }}

    EMAIL DATA:
    {emails_text}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'temperature': 0.2
            }
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"   ❌ AI Synthesis Error: {e}")
        return None

def get_html_template(synthesis):
    """Профессиональный HTML-шаблон письма с адаптивным дизайном"""
    
    # Генерация блоков трендов
    trends_html = "".join([f"""
        <div style="margin-bottom: 24px; padding: 20px; border-radius: 12px; border: 1px solid #eef2f6; background-color: #ffffff;">
            <h3 style="margin: 0 0 10px 0; color: #1a73e8; font-size: 18px; font-weight: 600;">{t['title']}</h3>
            <div style="color: #3c4043; font-size: 15px; line-height: 1.6;">{t['insight']}</div>
        </div>
    """ for t in synthesis.get('trends', [])])

    # Генерация блока Action Items
    actions_list = "".join([f"<li style='margin-bottom: 8px;'>{item}</li>" for item in synthesis.get('action_items', [])])
    actions_section = ""
    if actions_list:
        actions_section = f"""
        <div style="margin-bottom: 35px; padding: 25px; border-radius: 12px; background-color: #fff9db; border: 1px solid #fab005;">
            <h3 style="margin: 0 0 12px 0; color: #f08c00; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;">⚠️ Action Items</h3>
            <ul style="margin: 0; padding-left: 20px; color: #2c2e33; font-size: 15px; line-height: 1.5;">{actions_list}</ul>
        </div>
        """

    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f7f9; padding: 40px 20px;">
        <div style="max-width: 600px; margin: auto; background: white; border-radius: 24px; overflow: hidden; box-shadow: 0 15px 35px rgba(0,0,0,0.05);">
            <div style="background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%); color: white; padding: 45px 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 30px; font-weight: 300; letter-spacing: 1px;">☀️ Sunday Brief</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.8; font-size: 15px;">Умный дайджест вашей почты</p>
            </div>
            
            <div style="padding: 40px;">
                <div style="background: #f0f4ff; border-left: 5px solid #1a73e8; padding: 25px; border-radius: 12px; margin-bottom: 35px;">
                    <h2 style="margin: 0 0 10px 0; font-size: 12px; color: #1a73e8; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 700;">The Big Picture</h2>
                    <p style="margin: 0; font-size: 17px; line-height: 1.6; color: #1a202c; font-weight: 500;">{synthesis.get('big_picture')}</p>
                </div>

                {actions_section}
                
                <h2 style="font-size: 12px; color: #718096; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 20px; font-weight: 700;">Key Insights</h2>
                {trends_html}
                
                <div style="margin-top: 40px; padding: 15px; border-radius: 8px; background-color: #f8fafc; border: 1px solid #e2e8f0; text-align: center;">
                    <p style="margin: 0; font-size: 12px; color: #64748b;">
                        <strong>Noise Filter:</strong> {synthesis.get('noise_filter')}
                    </p>
                </div>
            </div>
            
            <div style="background: #f8fafc; padding: 30px; text-align: center; border-top: 1px solid #e2e8f0;">
                <p style="margin: 0; font-size: 11px; color: #94a3b8; line-height: 1.4;">
                    Вы получили это письмо, так как Sunday AI проанализировал вашу входящую почту.<br>
                    © 2025 Sunday AI. Все права защищены.
                </p>
            </div>
        </div>
    </div>
    """

def main():
    now = datetime.utcnow()
    cur_day, cur_hour = now.strftime("%A"), now.strftime("%H:00")
    print(f"🚀 Sunday AI Run | {cur_day} {cur_hour} UTC")

    # 1. Поиск профилей на текущий день
    users = supabase.table("profiles").select("*").eq("digest_day", cur_day).execute()
    
    if not users.data:
        print(f"💤 Нет пользователей на {cur_day}.")
        return

    for user in users.data:
        user_sched = user.get('digest_time', '09:00')[:5]
        
        # 2. Проверка времени (UTC)
        if user_sched != cur_hour:
            continue
            
        print(f"👤 Обработка: {user['email']}")
        
        # 3. Сбор необработанных писем
        emails_query = supabase.table("raw_emails").select("*").eq("user_id", user['id']).eq("processed", False).execute()
        
        if not emails_query.data:
            print("   📪 Новых писем не найдено.")
            continue

        print(f"   📨 Анализ {len(emails_query.data)} сообщений...")
        
        email_context = ""
        for e in emails_query.data:
            email_context += f"SENDER: {e['sender']}\nSUBJECT: {e['subject']}\nCONTENT: {e['body_plain'][:1000]}\n---\n"

        # 4. Вызов ИИ
        synthesis = get_ai_synthesis(email_context, user)
        
        if synthesis and "big_picture" in synthesis:
            # 5. Формирование и отправка
            html_email = get_html_template(synthesis)
            subject = f"Sunday Brief: {synthesis['big_picture'][:55]}..."
            
            if send_email(user['email'], subject, html_email):
                # 6. Успешный финиш: запись в базу и логирование
                supabase.table("digests").insert({
                    "user_id": user['id'], 
                    "structured_content": synthesis,
                    "subject": subject
                }).execute()
                
                for e in emails_query.data:
                    supabase.table("raw_emails").update({"processed": True}).eq("id", e['id']).execute()
                
                log_event(user['id'], "success", emails_count=len(emails_query.data))
                print("   ✅ Письмо доставлено, данные обновлены.")
            else:
                log_event(user['id'], "error", error_msg="Ошибка SMTP")
        else:
            log_event(user['id'], "error", error_msg="Ошибка генерации ИИ")
            print("   ❌ Не удалось создать дайджест.")

if __name__ == "__main__":
    main()