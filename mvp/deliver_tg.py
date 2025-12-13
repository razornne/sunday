import requests
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_tg():
    print("✈️ Sending via Telegram...")
    
    # Берем последний дайджест
    response = supabase.table("digests").select("telegram_text").order("id", desc=True).limit(1).execute()
    
    if not response.data:
        print("Empty DB.")
        return

    text = response.data[0]['telegram_text']
    
    api_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown", # Важно: Markdown, не HTML
        "disable_web_page_preview": True
    }
    
    try:
        requests.post(api_url, json=payload).raise_for_status()
        print("✅ Telegram Sent!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    send_tg()