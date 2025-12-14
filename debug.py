import os
from supabase import create_client
from dotenv import load_dotenv
from email.utils import parseaddr

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def debug_compare():
    print("🕵️‍♂️ НАЧИНАЕМ РАССЛЕДОВАНИЕ...")
    
    # 1. Загружаем подписки
    subs = supabase.table("subscriptions").select("*").execute().data
    print(f"\n📋 В БАЗЕ ЕСТЬ {len(subs)} ПОДПИСОК:")
    whitelist = []
    for s in subs:
        # Используем repr(), чтобы видеть скрытые символы типа \n или пробелов
        print(f"   ID: {s['id']} | Email: {repr(s['sender_email'])}")
        whitelist.append(s['sender_email'].strip().lower())

    # 2. Загружаем последнее письмо
    # Берем ЛЮБОЕ письмо, даже processed=true, просто последнее добавленное
    emails = supabase.table("raw_emails").select("*").order("created_at", desc=True).limit(1).execute().data
    
    if not emails:
        print("\n❌ В базе нет писем!")
        return

    email = emails[0]
    raw_sender = email['sender']
    
    print(f"\n📨 ПОСЛЕДНЕЕ ПИСЬМО:")
    print(f"   Отправитель (Raw): {repr(raw_sender)}")
    
    # 3. Эмулируем логику очистки
    name, clean_email = parseaddr(raw_sender)
    final_email = clean_email.strip().lower()
    
    print(f"   После очистки (parseaddr): {repr(clean_email)}")
    print(f"   Финальная строка для поиска: {repr(final_email)}")
    
    # 4. СРАВНЕНИЕ
    print(f"\n⚔️ БИТВА СТРОК:")
    if final_email in whitelist:
        print(f"   ✅ УРА! Совпадение найдено! '{final_email}' есть в списке.")
    else:
        print(f"   ❌ ПРОВАЛ. '{final_email}' НЕТ в списке.")
        print("   Давай сравним посимвольно с первым в списке:")
        
        if subs:
            db_email = subs[0]['sender_email'].strip().lower()
            print(f"   Письмо: '{final_email}'")
            print(f"   База:   '{db_email}'")
            
            if final_email == db_email:
                print("   (Они равны! Значит проблема была в регистре или пробелах)")
            else:
                print("   (Они НЕ равны. Смотри внимательно на буквы выше)")

if __name__ == "__main__":
    debug_compare()