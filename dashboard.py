import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Sunday AI", page_icon="☀️", layout="wide")
load_dotenv()

# --- СТИЛИ ДЛЯ ТЕМНОЙ ТЕМЫ ---
st.markdown("""
    <style>
    /* Адаптивные карточки дайджестов */
    .digest-card {
        padding: 1.5rem;
        border-radius: 0.75rem;
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 1rem;
        background-color: rgba(128, 128, 128, 0.05);
    }
    
    /* Красивый акцент на Big Picture */
    .big-picture-box {
        padding: 1rem;
        border-left: 4px solid #2e86de;
        background-color: rgba(46, 134, 222, 0.1);
        border-radius: 0.4rem;
        margin: 1rem 0;
    }

    /* Настройка шрифтов для читаемости в темной теме */
    .stMarkdown p {
        line-height: 1.6;
    }
    </style>
""", unsafe_allow_html=True)

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

# --- ФУНКЦИЯ СОХРАНЕНИЯ ---
def save_user_settings(user_id, role, focus, day, hour, tz):
    try:
        focus_list = [f.strip() for f in focus.split(",") if f.strip()]
        supabase.table("profiles").update({
            "role": role, "focus_areas": focus_list,
            "digest_day": day, "digest_time": hour, "timezone": tz
        }).eq("id", user_id).execute()
        st.success("✅ Настройки сохранены!")
        return True
    except Exception as e:
        st.error(f"Ошибка: {e}")
        return False

def main():
    if 'user' not in st.session_state:
        st.title("☀️ Sunday AI")
        email_input = st.text_input("Ваш Email").strip().lower()
        if st.button("Войти"):
            res = supabase.table("profiles").select("*").eq("email", email_input).execute()
            if res.data:
                st.session_state['user'] = res.data[0]
                st.rerun()
            else: st.error("Пользователь не найден")
        st.stop()

    user = st.session_state['user']

    with st.sidebar:
        st.title("Sunday AI")
        st.write(f"Аккаунт: **{user['email']}**")
        page = st.radio("Меню", ["📊 Дайджесты", "⚙️ Настройки"])
        st.divider()
        if st.button("Выход"):
            del st.session_state['user']
            st.rerun()

    if page == "⚙️ Настройки":
        st.header("Настройки профиля")
        
        # Виджет личного адреса
        st.markdown(f"""
            <div style="background-color: rgba(46, 134, 222, 0.1); padding: 15px; border-radius: 10px; border: 1px solid #2e86de;">
                <strong>📬 Твой персональный адрес:</strong><br>
                <code style="font-size: 1.2rem; color: #2e86de;">{user.get('personal_email', 'не назначен')}</code>
            </div>
        """, unsafe_allow_html=True)
        st.caption("Любая рассылка, отправленная на этот адрес, попадет в твой отчет.")

        with st.form("settings"):
            role = st.text_input("Роль (кто вы?)", value=user.get('role', 'Founder'))
            focus = st.text_area("Фокусы (через запятую)", value=", ".join(user.get('focus_areas', []) or []))
            
            st.divider()
            st.subheader("Когда присылать отчет?")
            c1, c2 = st.columns(2)
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day = c1.selectbox("День", days, index=days.index(user.get('digest_day', 'Sunday')))
            
            hours = [f"{h:02d}:00" for h in range(24)]
            hour = c2.selectbox("Время (UTC)", hours, index=hours.index(user.get('digest_time', '09:00')[:5]))

            if st.form_submit_button("Сохранить"):
                save_user_settings(user['id'], role, focus, day, hour, "UTC")

    elif page == "📊 Дайджесты":
        st.header("Твои еженедельные отчеты")
        res = supabase.table("digests").select("*").eq("user_id", user['id']).order("created_at", desc=True).execute()
        
        if not res.data:
            st.info("Здесь появятся ваши первые отчеты.")
        else:
            for d in res.data:
                date_label = d['created_at'][:10]
                with st.expander(f"📦 Отчет за {date_label}: {d.get('subject', 'Weekly Update')}"):
                    content = d.get('structured_content', {})
                    
                    # Big Picture в специальном блоке
                    st.markdown(f"""
                        <div class="big-picture-box">
                            <strong>🌍 Общая картина:</strong><br>
                            {content.get('big_picture', 'Нет данных')}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Тренды в карточках
                    for trend in content.get('trends', []):
                        st.markdown(f"""
                            <div class="digest-card">
                                <h4>{trend.get('title', 'Тренд')}</h4>
                                {trend.get('insight', '')}
                            </div>
                        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()