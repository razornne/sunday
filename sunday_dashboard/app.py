import streamlit as st
import streamlit_shadcn_ui as ui
import streamlit.components.v1 as components
from supabase import create_client
import os
from dotenv import load_dotenv
import pandas as pd
import uuid
from datetime import datetime, timedelta
import extra_streamlit_components as stx # Библиотека для куки

# 1. Config & Styles
st.set_page_config(page_title="Sunday AI", page_icon="☕", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Карточка Инсайта */
    .insight-card {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .insight-title {
        color: #111827;
        font-weight: 700;
        font-size: 18px;
        margin-bottom: 12px;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .insight-body {
        color: #374151;
        font-size: 16px;
        line-height: 1.6;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* Big Picture (Синий) */
    .big-picture-box {
        background-color: #eff6ff;
        border-left: 5px solid #3b82f6;
        padding: 20px;
        border-radius: 8px;
        color: #1e3a8a;
        font-size: 16px;
        line-height: 1.6;
        margin-bottom: 25px;
    }
    
    /* Action Items (Розовый) */
    .action-item {
        background-color: #fdf2f8;
        border: 1px solid #fbcfe8;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        color: #831843;
        font-weight: 500;
    }

    /* Inbox Address Box (Зеленый контейнер убрали, заменили на st.code для копирования) */
</style>
""", unsafe_allow_html=True)

# 2. Load Env
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if not url or not key: st.stop()

@st.cache_resource
def init_connection():
    return create_client(url, key)

supabase = init_connection()

# --- HELPERS ---
def get_user_uuid(email):
    """Ищет пользователя по личному email ИЛИ по сгенерированному (@sundayai.dev)"""
    try:
        email = email.strip().lower() # Очистка ввода
        # Синтаксис Supabase: Ищем совпадение в personal_email ИЛИ inbox_email
        response = supabase.table("profiles").select("id") \
            .or_(f"personal_email.eq.{email},inbox_email.eq.{email}") \
            .execute()
        
        if response.data: return response.data[0]['id']
        return None
    except: return None

def get_user_digests(user_uuid):
    try:
        response = supabase.table("digests").select("*").eq("user_id", user_uuid).order("period_start", desc=True).execute()
        return response.data
    except: return []

def get_user_profile(user_uuid):
    try:
        response = supabase.table("profiles").select("*").eq("id", user_uuid).execute()
        if response.data: return response.data[0]
        return {}
    except: return {}

def update_user_profile(user_uuid, updates):
    try:
        supabase.table("profiles").update(updates).eq("id", user_uuid).execute()
        return True
    except Exception as e:
        st.error(f"Error saving profile: {e}")
        return False
    
def create_user_profile(email):
    """Создает нового пользователя. ID генерируем сами."""
    try:
        # 1. Генерируем ID
        new_id = str(uuid.uuid4())
        
        # 2. Проверяем дубликат
        existing = get_user_uuid(email)
        if existing:
            return None, "User already exists. Please login."
            
        # 3. Создаем
        data = {
            "id": new_id,
            "personal_email": email, 
            "role": "Founder", 
            "focus_areas": ["General Tech"]
        }
        supabase.table("profiles").insert(data).execute()
        
        return new_id, None
    except Exception as e:
        return None, str(e)
    
def get_live_demo_data():
    """Берет реальный последний дайджест админа для демо-режима"""
    # 👇 ВСТАВЬ СЮДА СВОЙ UUID, КОТОРЫЙ ТЫ СКОПИРОВАЛ ИЗ SUPABASE
    ADMIN_UUID = "aa1a97d8-a102-4945-9390-239a6b6c5d68" 
    
    try:
        # Пытаемся достать последний отчет этого юзера
        response = supabase.table("digests") \
            .select("*") \
            .eq("user_id", ADMIN_UUID) \
            .order("period_start", desc=True) \
            .limit(1) \
            .execute()
            
        if response.data:
            return response.data[0]
        else:
            # Если у админа нет дайджестов, возвращаем фейк
            return get_fallback_data()
    except Exception as e:
        print(f"Demo fetch error: {e}")
        return get_fallback_data()

def get_fallback_data():
    """Запасной вариант (хардкод), если база не отвечает"""
    return {
        "id": "demo_fallback",
        "period_start": datetime.now() - timedelta(days=7),
        "period_end": datetime.now(),
        "summary_text": "<b>AI Models War.</b><br>This is a fallback demo data because the live fetch failed. But normally you'd see a real digest here.",
        "structured_content": {
            "trends": [{"title": "Live Demo Offline", "insight": "Could not connect to database to fetch the admin's digest."}],
            "action_items": ["Check your internet connection", "Refresh the page"],
            "noise_filter": "N/A"
        }
    }

# --- MAIN APP ---
def main():
    # 1. МЕНЕДЖЕР КУКИ (Cookies)
    cookie_manager = stx.CookieManager()
    
    # Инициализация сессии
    if 'user_email' not in st.session_state: st.session_state.user_email = None
    if 'user_uuid' not in st.session_state: st.session_state.user_uuid = None
    
    # --- НОВОЕ: State для Демо ---
    if 'demo_mode' not in st.session_state: st.session_state.demo_mode = False

    # ПРОВЕРКА КУКИ ПРИ ЗАГРУЗКЕ
    if not st.session_state.user_uuid and not st.session_state.demo_mode:
        cookie_uuid = cookie_manager.get('sunday_user_uuid')
        if cookie_uuid:
            prof = get_user_profile(cookie_uuid)
            if prof:
                st.session_state.user_uuid = cookie_uuid
                st.session_state.user_email = prof.get('personal_email')

    with st.sidebar:
        st.title("Sunday AI ☕")
        
        # --- ЛОГИН / РЕГИСТРАЦИЯ / ДЕМО ---
        # Показываем форму входа ТОЛЬКО если нет юзера И не включено демо
        if not st.session_state.user_email and not st.session_state.demo_mode:
            
            # === ГЛАВНАЯ КНОПКА ДЛЯ ОНБОРДИНГА ===
            st.info("Stop drowning in newsletters. See what Sunday AI can do for you.")
            if st.button("👀 See Live Demo (Instant)", type="primary", use_container_width=True):
                st.session_state.demo_mode = True
                st.rerun()
            # =====================================

            st.markdown("---")
            st.caption("Or sign in to your account")

            mode = st.radio("Auth Mode", ["Sign In", "Sign Up"], label_visibility="collapsed")
            
            email_input = st.text_input("Email", placeholder="you@example.com")
            
            if mode == "Sign In":
                if st.button("Log In", use_container_width=True):
                    if not email_input:
                        st.warning("Please enter email.")
                    else:
                        uuid_found = get_user_uuid(email_input)
                        if uuid_found:
                            st.session_state.user_email = email_input
                            st.session_state.user_uuid = uuid_found
                            cookie_manager.set('sunday_user_uuid', uuid_found, expires_at=datetime.now() + timedelta(days=30))
                            st.success("Welcome back!")
                            st.rerun()
                        else:
                            st.error("User not found.")
                            
            elif mode == "Sign Up":
                if st.button("Create Account", use_container_width=True):
                    if not email_input:
                        st.warning("Please enter email.")
                    else:
                        new_uuid, error = create_user_profile(email_input)
                        if new_uuid:
                            st.session_state.user_email = email_input
                            st.session_state.user_uuid = new_uuid
                            cookie_manager.set('sunday_user_uuid', new_uuid, expires_at=datetime.now() + timedelta(days=30))
                            st.success("Account created!")
                            st.rerun()
                        else:
                            st.error(f"Error: {error}")
            
            # БЛОКИРУЕМ КОНТЕНТ, ЕСЛИ МЫ НЕ В ДЕМО И НЕ ЗАЛОГИНЕНЫ
            st.stop() 
            
        # --- МЕНЮ (ЕСЛИ ЗАЛОГИНЕН ИЛИ ДЕМО) ---
        else:
            if st.session_state.demo_mode:
                st.warning("👀 You are in DEMO mode")
                st.markdown("Like what you see?")
                if st.button("🚀 Create Free Account", type="primary", use_container_width=True):
                    st.session_state.demo_mode = False
                    st.rerun()
            else:
                st.caption(f"👤 {st.session_state.user_email}")
            
            st.divider()
            
            # Меню доступно, но в демо только "My Briefs" имеет смысл
            page_options = ["My Briefs"]
            if not st.session_state.demo_mode:
                page_options.append("Settings")
            
            page = st.radio("Menu", page_options, label_visibility="collapsed")
            
            st.divider()
            
            if not st.session_state.demo_mode:
                if st.button("Sign Out", use_container_width=True):
                    try: cookie_manager.delete('sunday_user_uuid')
                    except: pass
                    st.session_state.user_email = None
                    st.session_state.user_uuid = None
                    st.rerun()
            else:
                if st.button("Exit Demo", use_container_width=True):
                    st.session_state.demo_mode = False
                    st.rerun()

    # --- PAGE 1: MY BRIEFS ---
    if page == "My Briefs":
        if st.session_state.demo_mode:
            st.title("Strategic Reports (Live Demo)")
            
            # 👇 ИЗМЕНЕНИЕ ЗДЕСЬ: Зовем новую функцию
            demo_digest = get_live_demo_data() 
            digests = [demo_digest]
            
            ui.card(title="👋 Welcome to Sunday AI", content="You are viewing a REAL generated digest from the creator's inbox. This updates automatically every Sunday.", key="welcome_msg")
        else:
            # (остальной код без изменений)
            st.title("Strategic Reports")
            digests = get_user_digests(st.session_state.user_uuid)
        
        if not digests:
            ui.card(title="No Briefs Yet", content="Forward emails to your Sunday address to generate reports.", key="empty")
        else:
            # Selector Logic
            options = {}
            for d in digests:
                try:
                    s = pd.to_datetime(d.get('period_start')).strftime('%b %d')
                    e = pd.to_datetime(d.get('period_end')).strftime('%b %d')
                    label = f"Week: {s} - {e}"
                except:
                    label = f"Digest #{d['id']}"
                options[label] = d

            sel = st.selectbox("Select Report:", list(options.keys()))
            brief = options[sel]
            
            # Parsing
            raw_data = brief.get('structured_content', {})
            trends = []
            actions = []
            noise = "N/A"
            
            if isinstance(raw_data, dict):
                trends = raw_data.get('trends', [])
                actions = raw_data.get('action_items', [])
                noise = raw_data.get('noise_filter', '')
            elif isinstance(raw_data, list):
                trends = raw_data

            big_picture = brief.get('summary_text') or brief.get('big_picture')

            # Rendering
            if big_picture:
                st.markdown("### 🌍 The Big Picture")
                st.markdown(f'<div class="big-picture-box">{big_picture}</div>', unsafe_allow_html=True)
            
            st.divider()

            st.markdown("### 📊 Key Strategic Insights")
            if trends:
                for t in trends:
                    title = t.get('title') or "Insight"
                    content = t.get('insight') or t.get('content') or "..."
                    
                    st.markdown(f"""
                    <div class="insight-card">
                        <div class="insight-title">{title}</div>
                        <div class="insight-body">{content}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("No trends generated.")

            st.divider()

            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown("### 🚀 Action Items")
                if actions:
                    for act in actions:
                        st.markdown(f'<div class="action-item">☐ {act}</div>', unsafe_allow_html=True)
                else:
                    st.caption("No actions.")
            
            with c2:
                st.markdown("### 🛡️ Process Stats")
                st.info(noise)

    # --- PAGE 2: SETTINGS ---
    elif page == "Settings" and not st.session_state.demo_mode:
        # Весь код Settings без изменений
        st.title("⚙️ Personalization")
        
        profile = get_user_profile(st.session_state.user_uuid)
        
        if not profile:
            st.error("Profile not found.")
        else:
            inbox_email = profile.get('inbox_email') or "Generating..."
            
            st.markdown("### 📬 Your Sunday Inbox")
            st.info("Forward your newsletters to this address:")
            st.code(inbox_email, language="text")
            
            st.markdown("""
            <div style="margin-top: -10px; margin-bottom: 20px; font-size: 14px;">
                <a href="https://support.google.com/mail/answer/10957?hl=en" target="_blank" style="text-decoration: none; color: #2563eb;">
                    📚 How to set up auto-forwarding in Gmail →
                </a>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()

            with st.container():
                st.markdown("### 🧠 AI Analyst Configuration")
                st.caption("Customize how Sunday AI analyzes your content.")

                with st.form("settings_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        current_role = profile.get('role') or "Founder"
                        new_role = st.text_input("Your Role", value=current_role)
                        current_day = profile.get('digest_day') or "Sunday"
                        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                        try: idx = days.index(current_day)
                        except: idx = 6
                        new_day = st.selectbox("Digest Day", days, index=idx)

                    with col2:
                        current_focus = profile.get('focus_areas') or []
                        if not isinstance(current_focus, list): current_focus = []
                        focus_str = ", ".join(current_focus)
                        new_focus_str = st.text_area("Focus Areas", value=focus_str, height=100)
                        current_time = profile.get('digest_time') or "09:00"
                        new_time = st.time_input("Delivery Time (UTC)", value=pd.to_datetime(str(current_time)).time())

                    st.divider()
                    submitted = st.form_submit_button("💾 Save Preferences", type="primary")
                    
                    if submitted:
                        final_focus_list = [x.strip() for x in new_focus_str.split(',') if x.strip()]
                        updates = {
                            "role": new_role,
                            "focus_areas": final_focus_list,
                            "digest_day": new_day,
                            "digest_time": str(new_time)
                        }
                        if update_user_profile(st.session_state.user_uuid, updates):
                            st.success("✅ Settings updated!")
                            st.rerun()

if __name__ == "__main__":
    main()