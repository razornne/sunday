import streamlit as st
from supabase import create_client, Client
import os
import json
from dotenv import load_dotenv

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sunday AI | Dashboard", page_icon="☀️", layout="wide")
load_dotenv()

# --- STYLING ---
st.markdown("""
    <style>
    .digest-card { padding: 1.2rem; border-radius: 0.8rem; border: 1px solid rgba(128,128,128,0.2); margin-bottom: 1rem; background-color: rgba(128,128,128,0.05); }
    .big-picture-box { padding: 1rem; border-left: 4px solid #2e86de; background-color: rgba(46,134,222,0.1); border-radius: 0.4rem; margin-bottom: 1.5rem; }
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

def save_settings(user_id, role, focus, day, hour):
    try:
        focus_list = [f.strip() for f in focus.split(",") if f.strip()]
        supabase.table("profiles").update({"role": role, "focus_areas": focus_list, "digest_day": day, "digest_time": hour}).eq("id", user_id).execute()
        st.success("✅ Settings updated!")
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def main():
    if 'user' not in st.session_state:
        st.title("☀️ Sunday AI")
        tabs = st.tabs(["Login", "Sign Up"])
        
        with tabs[0]: # LOGIN
            email_in = st.text_input("Primary Email", key="l_email").strip().lower()
            if st.button("Login"):
                res = supabase.table("profiles").select("*").eq("email", email_in).execute()
                if res.data:
                    st.session_state['user'] = res.data[0]
                    st.rerun()
                else: st.error("User not found.")
        
        with tabs[1]: # SIGN UP
            new_email = st.text_input("Your Real Email", key="s_email").strip().lower()
            username = st.text_input("Desired Username (for @sundayai.dev)").strip().lower()
            if st.button("Create Account"):
                if not new_email or not username: st.warning("Fill all fields")
                else:
                    personal_email = f"{username}@sundayai.dev"
                    # Check if exists
                    exists = supabase.table("profiles").select("id").eq("personal_email", personal_email).execute()
                    if exists.data: st.error("Username taken.")
                    else:
                        user_data = {"email": new_email, "personal_email": personal_email, "role": "Professional", "digest_day": "Sunday", "digest_time": "09:00"}
                        supabase.table("profiles").insert(user_data).execute()
                        st.success(f"Success! Your new inbox is {personal_email}. Now Login.")
        st.stop()

    user = st.session_state['user']
    with st.sidebar:
        st.title("Sunday AI")
        st.write(f"User: **{user['email']}**")
        page = st.radio("Menu", ["📊 My Briefs", "⚙️ AI Settings"])
        if st.button("Logout"):
            del st.session_state['user']
            st.rerun()

    if page == "⚙️ AI Settings":
        st.header("Intelligence & Delivery")
        st.info(f"📬 **Your Sunday Inbox:** `{user.get('personal_email')}`")
        with st.form("settings"):
            role = st.text_input("Your Role", value=user.get('role', 'Founder'))
            focus = st.text_area("Focus Areas (comma separated)", value=", ".join(user.get('focus_areas', []) or []))
            st.divider()
            c1, c2 = st.columns(2)
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            db_day = user.get('digest_day', 'Sunday')
            day = c1.selectbox("Day", days, index=days.index(db_day) if db_day in days else 6)
            hours = [f"{h:02d}:00" for h in range(24)]
            db_time = str(user.get('digest_time', '09:00'))[:5]
            hour = c2.selectbox("Hour (UTC)", hours, index=hours.index(db_time) if db_time in hours else 9)
            if st.form_submit_button("Save"):
                if save_settings(user['id'], role, focus, day, hour):
                    user.update({"role": role, "digest_day": day, "digest_time": hour})
                    st.session_state['user'] = user

    elif page == "📊 My Briefs":
        st.header("Your Sunday Reports")
        res = supabase.table("digests").select("*").eq("user_id", user['id']).order("created_at", desc=True).execute()
        if not res.data: st.info("No reports yet.")
        else:
            for d in res.data:
                with st.expander(f"📦 Brief from {d['created_at'][:10]}"):
                    content = d.get('structured_content', {})
                    if isinstance(content, str): content = json.loads(content)
                    st.markdown(f'<div class="big-picture-box"><strong>🌍 Summary:</strong><br>{content.get("big_picture")}</div>', unsafe_allow_html=True)
                    for t in content.get('trends', []):
                        st.markdown(f'<div class="digest-card"><h4>{t.get("title")}</h4>{t.get("insight")}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()