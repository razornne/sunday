import streamlit as st
from supabase import create_client, Client
import os
import json
from dotenv import load_dotenv

# --- 1. НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="Sunday AI | Dashboard",
    page_icon="☀️",
    layout="wide"
)

load_dotenv()

# --- 2. СТИЛИЗАЦИЯ (Адаптация под темную тему) ---
st.markdown("""
    <style>
    /* Карточки трендов */
    .digest-card {
        padding: 1.2rem;
        border-radius: 0.8rem;
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 1rem;
        background-color: rgba(128, 128, 128, 0.05);
    }
    /* Блок Big Picture */
    .big-picture-box {
        padding: 1rem;
        border-left: 4px solid #2e86de;
        background-color: rgba(46, 134, 222, 0.1);
        border-radius: 0.4rem;
        margin-bottom: 1.5rem;
    }
    /* Заголовки */
    .stMarkdown h4 {
        color: #2e86de;
        margin-top: 0;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. ПОДКЛЮЧЕНИЕ К БАЗЕ ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_connection()

# --- 4. ЛОГИКА СОХРАНЕНИЯ ---
def save_user_settings(user_id, role, focus, day, hour):
    try:
        focus_list = [f.strip() for f in focus.split(",") if f.strip()]
        data = {
            "role": role,
            "focus_areas": focus_list,
            "digest_day": day,
            "digest_time": hour
        }
        supabase.table("profiles").update(data).eq("id", user_id).execute()
        st.success("✅ Настройки сохранены!")
        return True
    except Exception as e:
        st.error(f"Ошибка сохранения: {e}")
        return False

# --- 5. ОСНОВНОЙ ИНТЕРФЕЙС ---
def main():
    if 'user' not in st.session_state:
        st.title("☀️ Sunday AI")
        email_input = st.text_input("Введите ваш Email").strip().lower()
        if st.button("Войти"):
            res = supabase.table("profiles").select("*").eq("email", email_input).execute()
            if res.data:
                st.session_state['user'] = res.data[0]
                st.rerun()
            else:
                st.error("Пользователь не найден")
        st.stop()

    user = st.session_state['user']

    # Сайдбар
    with st.sidebar:
        st.title("Sunday AI")
        st.write(f"Логин: **{user['email']}**")
        page = st.radio("Навигация", ["📊 Мои дайджесты", "⚙️ Настройки"])
        st.divider()
        if st.button("Выйти"):
            del st.session_state['user']
            st.rerun()

    # СТРАНИЦА: НАСТРОЙКИ
    if page == "⚙️ Настройки":
        st.header("Настройки интеллекта")
        
        st.info(f"📬 **Ваш инбокс для подписок:** `{user.get('personal_email', 'не назначен')}`")

        with st.form("settings_form"):
            role = st.text_input("Ваша роль", value=user.get('role', 'Founder'))
            focus = st.text_area("Области интереса (через запятую)", value=", ".join(user.get('focus_areas', []) or []))
            
            st.divider()
            st.subheader("Расписание доставки (UTC)")
            c1, c2 = st.columns(2)
            
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            current_day = user.get('digest_day', 'Sunday')
            # Защита на случай, если в базе старые данные (число)
            if not isinstance(current_day, str): current_day = "Sunday"
            day = c1.selectbox("День недели", days, index=days.index(current_day))
            
            hours = [f"{h:02d}:00" for h in range(24)]
            current_time = user.get('digest_time', '09:00')[:5]
            hour = c2.selectbox("Время отправки", hours, index=hours.index(current_time))

            if st.form_submit_button("Сохранить"):
                if save_user_settings(user['id'], role, focus, day, hour):
                    user.update({"role": role, "digest_day": day, "digest_time": hour})
                    st.session_state['user'] = user

    # СТРАНИЦА: ДАЙДЖЕСТЫ
    elif page == "📊 Мои дайджесты":
        st.header("Ваши отчеты")
        res = supabase.table("digests").select("*").eq("user_id", user['id']).order("created_at", desc=True).execute()
        
        if not res.data:
            st.info("Здесь появятся ваши отчеты. Настройте расписание и отправьте письма!")
        else:
            for d in res.data:
                date_label = d['created_at'][:10]
                with st.expander(f"📦 Дайджест от {date_label}: {d.get('subject', 'Weekly Update')}"):
                    
                    # --- ЗАЩИТА ОТ ОШИБОК ДАННЫХ ---
                    content = d.get('structured_content', {})
                    if isinstance(content, str):
                        try: content = json.loads(content)
                        except: 
                            st.write(content)
                            continue

                    if not isinstance(content, dict):
                        st.warning("Некорректный формат данных.")
                        continue

                    # Вывод Big Picture
                    st.markdown(f"""
                        <div class="big-picture-box">
                            <strong>🌍 Общая картина:</strong><br>
                            {content.get('big_picture', 'Информации нет')}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Вывод Трендов
                    for trend in content.get('trends', []):
                        st.markdown(f"""
                            <div class="digest-card">
                                <h4>{trend.get('title', 'Тренд')}</h4>
                                {trend.get('insight', '')}
                            </div>
                        """, unsafe_allow_html=True)
                    
                    if content.get('noise_filter'):
                        st.caption(f"🗑️ Отфильтровано: {content.get('noise_filter')}")

if __name__ == "__main__":
    main()