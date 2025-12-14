import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# 1. Настройка страницы
st.set_page_config(page_title="Sunday AI", page_icon="☀️")
st.title("☀️ Sunday AI Digest")

# 2. Загрузка секретов
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    st.error("❌ Ошибка: Не найдены ключи Supabase в .env файле.")
    st.stop()

# Инициализация Supabase
@st.cache_resource
def init_supabase():
    return create_client(url, key)

supabase = init_supabase()

# 3. Управление сессией (кто вошел?)
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
        st.success("Регистрация успешна! Проверьте почту для подтверждения (если включено) или просто войдите.")
    except Exception as e:
        st.error(f"Ошибка регистрации: {e}")

def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- ИНТЕРФЕЙС ---

# ЕСЛИ ПОЛЬЗОВАТЕЛЬ НЕ ВОШЕЛ
if not st.session_state.user:
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])

    with tab1:
        email_in = st.text_input("Email", key="login_email")
        pass_in = st.text_input("Пароль", type="password", key="login_pass")
        if st.button("Войти"):
            login(email_in, pass_in)

    with tab2:
        email_reg = st.text_input("Email", key="reg_email")
        pass_reg = st.text_input("Пароль", type="password", key="reg_pass")
        if st.button("Зарегистрироваться"):
            register(email_reg, pass_reg)

# ЕСЛИ ПОЛЬЗОВАТЕЛЬ ВОШЕЛ
else:
    user = st.session_state.user
    email = user.email
    
    # Боковая панель
    with st.sidebar:
        st.write(f"👤 **{email}**")
        if st.button("Выйти"):
            logout()
    
    st.header("📚 Мои Дайджесты")
    
    # Загружаем дайджесты из базы для этого юзера
    # ВАЖНО: Сейчас мы покажем ВСЕ дайджесты для теста.
    # Позже настроим фильтр .eq("user_id", user.id)
    try:
        response = supabase.table("digests").select("*").order("created_at", desc=True).limit(5).execute()
        digests = response.data
        
        if not digests:
            st.info("У вас пока нет дайджестов. Отправьте письмо боту!")
        else:
            for d in digests:
                with st.expander(f"📅 Дайджест от {d['created_at'][:10]}"):
                    st.markdown(d['telegram_text']) # Или original_text, смотря что храним
                    st.caption(f"ID: {d['id']}")
                    
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")

    st.divider()
    st.subheader("⚙️ Настройки")
    st.info("Здесь скоро будет подключение Telegram и ваш личный адрес для пересылки.")