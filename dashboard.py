import streamlit as st
from supabase import create_client, Client
import os
import json
from dotenv import load_dotenv

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sunday AI | Dashboard", page_icon="☀️", layout="wide")
load_dotenv()

# --- DATABASE CONNECTION ---
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

# --- AUTH HELPERS ---
def sign_in(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return res
    except Exception as e:
        st.error(f"Login failed: {e}")
        return None

def sign_up(email, password):
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        st.success("Registration successful! Check your email for confirmation (if enabled).")
        return res
    except Exception as e:
        st.error(f"Sign up failed: {e}")
        return None

# --- MAIN APP ---
def main():
    # Check session
    session = st.session_state.get('session')
    
    if not session:
        st.title("☀️ Sunday AI")
        auth_tab = st.tabs(["Login", "Create Account"])
        
        with auth_tab[0]: # LOGIN
            l_email = st.text_input("Email", key="l_email")
            l_pass = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login"):
                auth_res = sign_in(l_email, l_pass)
                if auth_res and auth_res.session:
                    st.session_state['session'] = auth_res.session
                    st.rerun()

        with auth_tab[1]: # SIGN UP
            s_email = st.text_input("Email", key="s_email")
            s_pass = st.text_input("Password (min 6 chars)", type="password", key="s_pass")
            if st.button("Sign Up"):
                sign_up(s_email, s_pass)
        st.stop()

    # Logged In Logic
    user_id = session.user.id
    
    # Fetch profile data from our table
    profile_res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if not profile_res.data:
        st.warning("Profile creating... Please refresh in a few seconds.")
        st.stop()
    
    user_data = profile_res.data[0]

    with st.sidebar:
        st.title("Sunday AI")
        st.write(f"Logged as: **{user_data['email']}**")
        page = st.radio("Navigation", ["📊 Briefs", "⚙️ Settings"])
        if st.button("Sign Out"):
            supabase.auth.sign_out()
            del st.session_state['session']
            st.rerun()

    if page == "⚙️ Settings":
        st.header("Account Intelligence")
        st.info(f"📬 **Your Inbox:** `{user_data.get('personal_email')}`")
        
        with st.form("settings"):
            role = st.text_input("Role", value=user_data.get('role', 'User'))
            p_email = st.text_input("Custom Sunday Address", value=user_data.get('personal_email'))
            # ... (other fields like digest_day, etc) ...
            
            if st.form_submit_button("Save Changes"):
                supabase.table("profiles").update({
                    "role": role, 
                    "personal_email": p_email
                }).eq("id", user_id).execute()
                st.success("Updated!")

    elif page == "📊 Briefs":
        st.header("Weekly Briefs")
        # Same as before, just filter by user_id
        res = supabase.table("digests").select("*").eq("user_id", user_id).execute()
        # ... (display logic) ...

if __name__ == "__main__":
    main()