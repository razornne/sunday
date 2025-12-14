import streamlit as st
from supabase import create_client, Client
import pandas as pd
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="Sunday AI",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Загрузка переменных (для локального запуска)
load_dotenv()

# --- ПОДКЛЮЧЕНИЕ К БАЗЕ ---
@st.cache_resource
def init_connection():
    # Пытаемся взять из секретов Streamlit (для Cloud) или из .env (локально)
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
    if not url or not key:
        st.error("❌ Database keys not found. Check .env or secrets.toml")
        st.stop()
        
    return create_client(url, key)

supabase = init_connection()

# --- CSS ДЛЯ КРАСОТЫ ---
st.markdown("""
    <style>
    .big-picture {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        margin-bottom: 25px;
    }
    .trend-title {
        font-size: 20px;
        font-weight: 600;
        color: #0e1117;
    }
    .noise-text {
        font-size: 12px;
        color: #888;
        font-style: italic;
    }
    </style>
""", unsafe_allow_html=True)

# --- ФУНКЦИИ ---

def login_user(email):
    """Ищет пользователя по email"""
    try:
        response = supabase.table("profiles").select("*").eq("email", email).execute()
        if response.data:
            return response.data[0]
        else:
            return None
    except Exception as e:
        st.error(f"Login error: {e}")
        return None

def save_profile_settings(user_id, role, focus_areas):
    """Обновляет настройки AI"""
    try:
        focus_list = [x.strip() for x in focus_areas.split(",") if x.strip()]
        
        supabase.table("profiles").update({
            "role": role,
            "focus_areas": focus_list
        }).eq("id", user_id).execute()
        
        st.success("✅ Profile updated! Next brief will adapt to this.")
        # Очищаем кэш данных, но не ресурсов (подключения к БД)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False

def get_digests(user_id):
    """Получает все дайджесты пользователя"""
    try:
        response = supabase.table("digests")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        return response.data
    except:
        return []

# --- ИНТЕРФЕЙС ---

def main():
    # 1. SIDEBAR / LOGIN
    with st.sidebar:
        st.title("☀️ Sunday AI")
        
        # Простая эмуляция авторизации
        if 'user' not in st.session_state:
            email_input = st.text_input("Login (Email)", placeholder="you@example.com")
            if st.button("Enter"):
                user = login_user(email_input.strip().lower())
                if user:
                    st.session_state['user'] = user
                    st.rerun() # <--- ИСПРАВЛЕНО (БЫЛО experimental_rerun)
                else:
                    st.error("User not found.")
            st.stop()
        
        else:
            user = st.session_state['user']
            st.write(f"👋 **{user['email']}**")
            
            if st.button("Logout"):
                del st.session_state['user']
                st.rerun() # <--- ИСПРАВЛЕНО

            st.divider()
            
            page = st.radio("Go to", ["My Briefs", "AI Settings"])

    # 2. СТРАНИЦА: НАСТРОЙКИ (AI SETTINGS)
    if page == "AI Settings":
        st.header("🧠 Intelligence Profile")
        st.write("Customize how Sunday AI analyzes your inbox.")
        
        current_role = user.get('role', 'General User')
        current_focus = ", ".join(user.get('focus_areas', []) or [])
        
        with st.form("settings_form"):
            new_role = st.text_input("Your Role", value=current_role, help="e.g. Founder, Investor, Frontend Dev")
            new_focus = st.text_area("Focus Areas (comma separated)", value=current_focus, help="e.g. SaaS Metrics, AI Agents, Crypto")
            
            submitted = st.form_submit_button("Save Changes")
            if submitted:
                if save_profile_settings(user['id'], new_role, new_focus):
                    user['role'] = new_role
                    user['focus_areas'] = [x.strip() for x in new_focus.split(",")]
                    st.session_state['user'] = user
                    st.rerun() # <--- ИСПРАВЛЕНО

    # 3. СТРАНИЦА: ДАЙДЖЕСТЫ (MY BRIEFS)
    elif page == "My Briefs":
        digests = get_digests(user['id'])
        
        if not digests:
            st.info("📭 No briefs yet. Wait for the next Sunday!")
        else:
            # ИСПРАВЛЕНИЕ: Добавляем время, чтобы видеть несколько тестов за день
            dates = {f"{d['created_at'][:10]} ({d['created_at'][11:16]})": d for d in digests}
            
            selected_date = st.selectbox("Select Digest", list(dates.keys()))
            current_digest = dates[selected_date]
            
            # --- ВИЗУАЛИЗАЦИЯ ОТЧЕТА ---
            content = current_digest.get('structured_content', {})
            
            if not isinstance(content, dict):
                st.warning("This is an old format digest.")
                st.markdown(current_digest.get('summary_text', 'No content'))
            else:
                st.title(current_digest.get('subject', 'Weekly Brief'))
                st.caption(f"Generated on {current_digest['created_at'][:16]}")
                
                # BIG PICTURE
                if content.get('big_picture'):
                    st.markdown(f"""
                        <div class="big-picture">
                            <h3>🌍 The Big Picture</h3>
                            {content['big_picture']}
                        </div>
                    """, unsafe_allow_html=True)
                
                # TRENDS
                st.subheader("🔥 Key Signals & Trends")
                
                trends = content.get('trends', [])
                if not trends:
                    st.write("No major trends detected.")
                    
                for t in trends:
                    with st.expander(f"{t.get('title', 'Trend')}", expanded=True):
                        st.markdown(t.get('insight', ''))
                        
                        indices = t.get('sources_indices', [])
                        if indices:
                            st.caption(f"📚 Sources: Emails {indices}")

                # NOISE FILTER
                st.divider()
                st.markdown(f"<p class='noise-text'>🗑️ Filtered Noise: {content.get('noise_filter', 'None')}</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()