import streamlit as st
from supabase import create_client
import os
import uuid
import time
from dotenv import load_dotenv

# 1. Настройка страницы
st.set_page_config(page_title="Sunday AI", page_icon="☀️", layout="wide")

# 2. Загрузка секретов
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
DOMAIN = "sundayai.dev" # Твой домен

# --- НАСТРОЙКИ БОТА ---
BOT_USERNAME = "sundayfeed_bot"

if not url or not key:
    st.error("❌ Ошибка: Не найдены ключи Supabase в .env файле.")
    st.stop()

# Инициализация Supabase
@st.cache_resource
def init_supabase():
    return create_client(url, key)

supabase = init_supabase()

# 3. Управление сессией
if 'user' not in st.session_state:
    st.session_state.user = None

# --- ФУНКЦИИ ---

def login(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = response.user
        st.success("Успешный вход! 🚀")
        st.rerun()
    except Exception as e:
        st.error(f"Ошибка входа: {e}")

def register(email, password):
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        st.success("Регистрация успешна! Теперь вы можете войти.")
    except Exception as e:
        st.error(f"Ошибка регистрации: {e}")

def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- ИНТЕРФЕЙС ---

st.title("☀️ Sunday AI")

# ЕСЛИ ПОЛЬЗОВАТЕЛЬ НЕ ВОШЕЛ
if not st.session_state.user:
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])

    with tab1:
        email_in = st.text_input("Email", key="login_email")
        pass_in = st.text_input("Пароль", type="password", key="login_pass")
        if st.button("Войти", type="primary"):
            login(email_in, pass_in)

    with tab2:
        email_reg = st.text_input("Email", key="reg_email")
        pass_reg = st.text_input("Пароль", type="password", key="reg_pass")
        if st.button("Зарегистрироваться"):
            register(email_reg, pass_reg)

# ЛИЧНЫЙ КАБИНЕТ
else:
    user = st.session_state.user
    
    # Загружаем профиль пользователя из базы
    try:
        profile = supabase.table("profiles").select("*").eq("id", user.id).single().execute()
        p_data = profile.data if profile.data else {}
    except:
        p_data = {}

    # Боковая панель
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/869/869869.png", width=50)
        st.write(f"👤 **{user.email}**")
        st.divider()
        if st.button("Выйти"):
            logout()

    # Вкладки
    tab_digests, tab_settings = st.tabs(["📚 Мои Дайджесты", "⚙️ Настройки"])
    
    # --- ВКЛАДКА: ДАЙДЖЕСТЫ ---
    with tab_digests:
        try:
            # Загружаем дайджесты ТОЛЬКО этого пользователя
            response = supabase.table("digests").select("*").eq("user_id", user.id).order("created_at", desc=True).limit(20).execute()
            digests = response.data
            
            if not digests:
                st.info("📭 У вас пока нет дайджестов.")
                st.markdown(f"""
                **Как получить первый дайджест?**
                1. Добавьте свою почту в настройки (если еще нет).
                2. Перешлите интересное письмо на `bot@{DOMAIN}`.
                """)
            else:
                for d in digests:
                    date_str = d['created_at'][:10]
                    subject = d.get('subject', 'Без темы')
                    
                    with st.expander(f"📅 {date_str} | {subject}"):
                        st.caption(f"Original Email ID: {d.get('raw_email_id')}")
                        # Текст саммари (Markdown)
                        st.markdown(d.get('summary_text', 'Нет текста'))
                        st.divider()
                        st.caption("Версия для Telegram:")
                        st.info(d.get('telegram_text', 'Нет текста'))

        except Exception as e:
            st.error(f"Ошибка загрузки: {e}")

    # --- ВКЛАДКА: НАСТРОЙКИ ---
    with tab_settings:
        st.header("Настройки доставки")
        
        # 1. Личный адрес (Пока общий)
        st.info(f"📧 Пересылайте письма на: **bot@{DOMAIN}**")
        
        st.divider()

        # 2. Telegram (Deep Linking)
        st.subheader("🔗 Подключение Telegram")
        
        tg_id = p_data.get('telegram_chat_id')

        if tg_id:
            st.success(f"✅ Telegram успешно подключен!")
            st.code(f"Chat ID: {tg_id}", language="text")
            
            if st.button("❌ Отключить Telegram"):
                supabase.table("profiles").update({"telegram_chat_id": None}).eq("id", user.id).execute()
                st.toast("Telegram отключен")
                time.sleep(1)
                st.rerun()
        else:
            st.warning("⚠️ Telegram не подключен. Уведомления приходить не будут.")
            
            st.write("Нажмите кнопку ниже, чтобы автоматически связать аккаунт:")
            
            # Кнопка генерации ссылки
            if st.button("🚀 Подключить Бота"):
                # А. Генерируем уникальный код
                code = str(uuid.uuid4())
                
                # Б. Сохраняем код в базу к этому юзеру
                try:
                    supabase.table("profiles").update({"verification_code": code}).eq("id", user.id).execute()
                    
                    # В. Формируем ссылку
                    link = f"https://t.me/{BOT_USERNAME}?start={code}"
                    
                    # Г. Показываем красивую кнопку-ссылку (HTML хак для Streamlit)
                    st.markdown(f'''
                        <a href="{link}" target="_blank" style="text-decoration: none;">
                            <button style="
                                background-color: #24A1DE; 
                                color: white; 
                                border: none; 
                                padding: 12px 24px; 
                                border-radius: 8px; 
                                font-size: 16px; 
                                font-weight: bold; 
                                cursor: pointer;
                                display: flex;
                                align-items: center;
                                gap: 10px;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                                transition: background-color 0.3s;
                            ">
                                ✈️ Перейти в Telegram и нажать Start
                            </button>
                        </a>
                    ''', unsafe_allow_html=True)
                    
                    st.info("☝️ После того как нажмете 'Start' в боте, вернитесь сюда и обновите страницу.")
                    
                except Exception as e:
                    st.error(f"Ошибка генерации ссылки: {e}")
            
            if st.button("🔄 Я нажал Start, обновить статус"):
                st.rerun()