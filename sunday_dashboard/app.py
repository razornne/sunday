import sys
import os

# --- 1. НАСТРОЙКА ПУТЕЙ (Чтобы видеть соседнюю папку) ---
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    backend_path = os.path.join(parent_dir, 'sunday_backend')
    sys.path.append(backend_path)
    from pipeline import run_digest # Импортируем нашу функцию
except Exception as e:
    print(f"⚠️ Warning: Could not import backend logic. Error: {e}")
    # Заглушка, чтобы приложение не упало при старте
    def run_digest(uid): return False

# --- 2. ИМПОРТЫ ---
import streamlit as st
import streamlit_shadcn_ui as ui
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd
import uuid
from datetime import datetime, timedelta
import extra_streamlit_components as stx

# --- 3. CONFIG ---
st.set_page_config(page_title="Sunday AI", page_icon="☕", layout="wide")

# --- CUSTOM CSS (MOBILE OPTIMIZED) ---
st.markdown("""
<style>
    /* Мобильная адаптация */
    @media (max-width: 640px) {
        .block-container {
            padding-top: 1.5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        h1 { font-size: 2rem !important; }
        .stButton button { width: 100% !important; }
        [data-testid="stToolbar"] { visibility: hidden; height: 0%; }
        .insight-card { padding: 16px !important; margin-bottom: 12px !important; }
    }
    
    /* Стили карточек */
    .insight-card {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .insight-title { color: #111827; font-weight: 700; font-size: 18px; margin-bottom: 8px; }
    .insight-body { color: #374151; font-size: 16px; line-height: 1.6; }
    
    .big-picture-box {
        background-color: #eff6ff; border-left: 5px solid #3b82f6;
        padding: 20px; border-radius: 8px; color: #1e3a8a;
        margin-bottom: 25px; line-height: 1.6;
    }
    .action-item {
        background-color: #fdf2f8; border: 1px solid #fbcfe8;
        padding: 15px; border-radius: 8px; margin-bottom: 10px; color: #831843; font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# 4. Load Env & DB
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if not url or not key: st.error("Supabase keys missing!"); st.stop()

@st.cache_resource
def init_connection():
    return create_client(url, key)

supabase = init_connection()

# --- HELPERS ---

def get_user_uuid(email):
    try:
        email = email.strip().lower()
        response = supabase.table("profiles").select("id") \
            .or_(f"personal_email.eq.{email},inbox_email.eq.{email}").execute()
        return response.data[0]['id'] if response.data else None
    except: return None

def get_user_digests(user_uuid):
    try:
        response = supabase.table("digests").select("*").eq("user_id", user_uuid).order("period_start", desc=True).execute()
        return response.data
    except: return []

def get_user_profile(user_uuid):
    try:
        response = supabase.table("profiles").select("*").eq("id", user_uuid).execute()
        return response.data[0] if response.data else {}
    except: return {}

def update_user_profile(user_uuid, updates):
    try:
        supabase.table("profiles").update(updates).eq("id", user_uuid).execute()
        return True
    except Exception as e: st.error(f"Error: {e}"); return False

def create_user_profile(email):
    try:
        new_id = str(uuid.uuid4())
        existing = get_user_uuid(email)
        if existing: return None, "User exists. Please login."
        data = {"id": new_id, "personal_email": email, "role": "Founder", "focus_areas": ["General Tech"]}
        supabase.table("profiles").insert(data).execute()
        return new_id, None
    except Exception as e: return None, str(e)

# --- DEMO HELPER (ВАЖНО: ВСТАВЬ СВОЙ UUID) ---
def get_live_demo_data():
    # 👇👇👇 НЕ ЗАБУДЬ ВЕРНУТЬ СЮДА СВОЙ UUID ПЕРЕД ПУШЕМ 👇👇👇
    ADMIN_UUID = "ТВОЙ_UUID_ЗДЕСЬ" 
    try:
        response = supabase.table("digests").select("*").eq("user_id", ADMIN_UUID).order("period_start", desc=True).limit(1).execute()
        if response.data: return response.data[0]
        return get_fallback_data()
    except: return get_fallback_data()

def get_fallback_data():
    return {
        "id": "fake", "summary_text": "<b>Demo Offline.</b> Could not fetch live data.",
        "structured_content": {"trends": [{"title": "Welcome", "insight": "This is a placeholder because the live demo fetch failed."}]}
    }

# --- MAIN APP ---
def main():
    cookie_manager = stx.CookieManager()
    
    if 'user_email' not in st.session_state: st.session_state.user_email = None
    if 'user_uuid' not in st.session_state: st.session_state.user_uuid = None
    if 'demo_mode' not in st.session_state: st.session_state.demo_mode = False

    # Auto-Login via Cookie (skipped if Demo Mode is active)
    if not st.session_state.user_uuid and not st.session_state.demo_mode:
        cookie_uuid = cookie_manager.get('sunday_user_uuid')
        if cookie_uuid:
            prof = get_user_profile(cookie_uuid)
            if prof:
                st.session_state.user_uuid = cookie_uuid
                st.session_state.user_email = prof.get('personal_email')

    # === ЛОГИКА ОТОБРАЖЕНИЯ ===
    
    with st.sidebar:
        st.title("Sunday AI ☕")
        
        # 1. AUTH / SIDEBAR LOGIC
        if not st.session_state.user_email and not st.session_state.demo_mode:
            # Кнопка демо в сайдбаре (для ПК)
            st.info("Stop drowning in newsletters.")
            if st.button("👀 See Live Demo", type="primary", use_container_width=True, key="sb_demo_btn"):
                st.session_state.demo_mode = True
                st.rerun()
            
            st.divider()
            
            # Форма входа
            mode = st.radio("Auth Mode", ["Sign In", "Sign Up"], label_visibility="collapsed")
            email_input = st.text_input("Email", placeholder="you@example.com")
            
            if mode == "Sign In":
                if st.button("Log In", use_container_width=True):
                    uid = get_user_uuid(email_input)
                    if uid:
                        st.session_state.user_email = email_input
                        st.session_state.user_uuid = uid
                        cookie_manager.set('sunday_user_uuid', uid, expires_at=datetime.now() + timedelta(days=30))
                        st.rerun()
                    else: st.error("User not found.")
            else:
                if st.button("Create Account", use_container_width=True):
                    uid, err = create_user_profile(email_input)
                    if uid:
                        st.session_state.user_email = email_input
                        st.session_state.user_uuid = uid
                        cookie_manager.set('sunday_user_uuid', uid, expires_at=datetime.now() + timedelta(days=30))
                        st.rerun()
                    else: st.error(err)
            
        else:
            # Юзер залогинен ИЛИ Демо
            if st.session_state.demo_mode:
                st.warning("👀 DEMO MODE")
                if st.button("🚀 Sign Up Free", type="primary", use_container_width=True, key="sb_signup"):
                    st.session_state.demo_mode = False
                    st.rerun()
                if st.button("Exit Demo", use_container_width=True, key="sb_exit"):
                    st.session_state.demo_mode = False
                    st.rerun()
            else:
                st.caption(f"👤 {st.session_state.user_email}")
                if st.button("Sign Out", use_container_width=True):
                    try: cookie_manager.delete('sunday_user_uuid')
                    except: pass
                    st.session_state.user_email = None; st.session_state.user_uuid = None
                    st.rerun()
            
            st.divider()
            page = st.radio("Menu", ["My Briefs", "Settings"] if not st.session_state.demo_mode else ["My Briefs"], label_visibility="collapsed")

    # === ГЛАВНЫЙ ЭКРАН (CONTENT) ===

    # Если мы НЕ залогинены и НЕ в демо -> Показываем приветствие и кнопку для мобилок
    if not st.session_state.user_email and not st.session_state.demo_mode:
        col1, col2, col3 = st.columns([1,2,1])
        with col2: st.title("Sunday AI ☕")
        st.markdown("<h3 style='text-align: center; color: gray;'>Your personal AI Analyst.</h3>", unsafe_allow_html=True)
        st.write("")
        
        # Кнопка для мобильных (дублирует функционал)
        if st.button("👀 See Live Demo (Instant)", type="primary", use_container_width=True, key="main_demo_btn"):
             st.session_state.demo_mode = True
             st.rerun()
        st.divider()
        st.stop() # Останавливаем рендер

    # --- TAB: MY BRIEFS ---
    if page == "My Briefs":
        
        # === 🚨 MOBILE FIX: КНОПКИ ВЫХОДА ИЗ ДЕМО (В ПОТОКЕ) ===
        if st.session_state.demo_mode:
            st.info("👀 You are viewing a Live Demo.")
            mob_col1, mob_col2 = st.columns(2)
            with mob_col1:
                if st.button("🚀 Sign Up Free", type="primary", use_container_width=True, key="mobile_signup_btn"):
                    st.session_state.demo_mode = False
                    st.rerun()
            with mob_col2:
                if st.button("Exit Demo", type="secondary", use_container_width=True, key="mobile_exit_btn"):
                    st.session_state.demo_mode = False
                    st.rerun()
            st.divider()
        # ========================================================

        if st.session_state.demo_mode:
            st.title("Strategic Reports (Live Demo)")
            digest_data = get_live_demo_data()
            digests = [digest_data]
            ui.card(title="👋 Welcome!", content="This is a REAL digest generated from the admin's inbox.", key="welcome")
        else:
            st.title("Strategic Reports")
            digests = get_user_digests(st.session_state.user_uuid)
        
        if not digests:
            ui.card(title="No Briefs Yet", content="Forward emails to start.", key="empty")
        else:
            # FIX: Превращаем ID в строку перед срезом, чтобы не было ошибки int
            options = {f"Digest #{str(d.get('id', '0'))[:4]}": d for d in digests}
            sel = st.selectbox("Select Report:", list(options.keys()))
            brief = options[sel]
            
            raw = brief.get('structured_content', {})
            big_pic = brief.get('summary_text')
            
            if big_pic:
                st.markdown("### 🌍 The Big Picture")
                st.markdown(f'<div class="big-picture-box">{big_pic}</div>', unsafe_allow_html=True)
            
            st.divider()
            st.markdown("### 📊 Key Insights")
            
            trends = raw.get('trends', []) if isinstance(raw, dict) else []
            if trends:
                for t in trends:
                    st.markdown(f"""<div class="insight-card"><div class="insight-title">{t.get('title','')}</div><div class="insight-body">{t.get('insight','')}</div></div>""", unsafe_allow_html=True)
            else: st.info("No trends found.")

            st.divider()
            st.markdown("### 🚀 Action Items")
            actions = raw.get('action_items', []) if isinstance(raw, dict) else []
            for act in actions: st.markdown(f'<div class="action-item">☐ {act}</div>', unsafe_allow_html=True)

    # --- TAB: SETTINGS ---
    elif page == "Settings" and not st.session_state.demo_mode:
        st.title("⚙️ Personalization")
        prof = get_user_profile(st.session_state.user_uuid)
        if prof:
            st.info(f"Forward to: **{prof.get('inbox_email')}**")
            
            with st.form("settings"):
                c1, c2 = st.columns(2)
                with c1:
                    role = st.text_input("Role", value=prof.get('role', 'Founder'))
                    day = st.selectbox("Day", ["Monday", "Sunday"], index=0 if prof.get('digest_day') == "Monday" else 1)
                with c2:
                    focus = st.text_area("Focus Areas", value=", ".join(prof.get('focus_areas', [])))
                    time_val = st.time_input("Time (UTC)", value=pd.to_datetime(str(prof.get('digest_time', '09:00:00'))).time())
                
                if st.form_submit_button("Save"):
                    update_user_profile(st.session_state.user_uuid, {
                        "role": role, 
                        "focus_areas": [x.strip() for x in focus.split(',')],
                        "digest_day": day,
                        "digest_time": str(time_val)
                    })
                    st.success("Saved!")
                    st.rerun()
            
            st.divider()
            st.markdown("### ⚡️ Manual Trigger")
            st.caption("Generate digest immediately.")
            if st.button("Generate Now", type="secondary", use_container_width=True):
                with st.spinner("Chef is cooking... (30-60s)"):
                    if run_digest(st.session_state.user_uuid):
                        st.success("Done! Check 'My Briefs'.")
                        st.balloons()
                    else:
                        st.warning("Not enough new emails.")

if __name__ == "__main__":
    main()