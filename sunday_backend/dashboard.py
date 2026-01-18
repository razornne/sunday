import streamlit as st
from supabase import create_client, Client
import os
import json
from dotenv import load_dotenv

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Sunday AI | Dashboard", page_icon="☀️", layout="wide")
load_dotenv()

# --- 2. STYLING ---
st.markdown("""
    <style>
    .digest-card { padding: 1.2rem; border-radius: 0.8rem; border: 1px solid rgba(128,128,128,0.2); margin-bottom: 1rem; background-color: rgba(128,128,128,0.05); }
    .big-picture-box { padding: 1rem; border-left: 4px solid #2e86de; background-color: rgba(46,134,222,0.1); border-radius: 0.4rem; margin-bottom: 1.5rem; }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATABASE CONNECTION ---
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

# --- 4. AUTH HELPERS ---
def sign_in(email, password):
    try:
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        st.error(f"Login failed: {e}")
        return None

def sign_up(email, password):
    try:
        supabase.auth.sign_up({"email": email, "password": password})
        st.success("Account created! You can now login.")
    except Exception as e:
        st.error(f"Registration failed: {e}")

# --- 5. MAIN APP ---
def main():
    # Check if we have a session in state
    if 'session' not in st.session_state:
        st.title("☀️ Sunday AI")
        auth_tabs = st.tabs(["Login", "Sign Up"])
        
        with auth_tabs[0]: # LOGIN
            l_email = st.text_input("Email", key="login_email").strip().lower()
            l_pass = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login"):
                res = sign_in(l_email, l_pass)
                if res and res.session:
                    st.session_state['session'] = res.session
                    st.rerun()

        with auth_tabs[1]: # SIGN UP
            s_email = st.text_input("Email", key="reg_email").strip().lower()
            s_pass = st.text_input("Password (min 6 chars)", type="password", key="reg_pass")
            if st.button("Create Account"):
                sign_up(s_email, s_pass)
        st.stop()

    # --- LOGGED IN AREA ---
    session = st.session_state['session']
    user_id = session.user.id

    # Fetch fresh profile data
    profile_res = supabase.table("profiles").select("*").eq("id", user_id).execute()
    if not profile_res.data:
        st.warning("Finalizing your profile... please refresh.")
        st.stop()
    
    user_data = profile_res.data[0]

    # Sidebar
    with st.sidebar:
        st.title("Sunday AI")
        st.write(f"Logged in as: **{user_data['email']}**")
        page = st.radio("Navigation", ["📊 My Briefs", "⚙️ AI Settings"])
        st.divider()
        if st.button("Sign Out"):
            supabase.auth.sign_out()
            del st.session_state['session']
            st.rerun()

    # PAGE: SETTINGS
    if page == "⚙️ AI Settings":
        st.header("Intelligence & Delivery Settings")
        st.info(f"📬 **Your Personal Sunday Inbox:** `{user_data.get('personal_email')}`")

        with st.form("settings_form"):
            col1, col2 = st.columns(2)
            role = col1.text_input("Professional Role", value=user_data.get('role', 'Founder'))
            p_email = col2.text_input("Custom Sunday Address", value=user_data.get('personal_email'))
            
            # FOCUS AREAS ARE BACK
            focus = st.text_area("Focus Areas (comma separated)", 
                                value=", ".join(user_data.get('focus_areas', []) or []))
            
            st.divider()
            st.subheader("Delivery Schedule (UTC)")
            c1, c2 = st.columns(2)
            
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            current_day = user_data.get('digest_day', 'Sunday')
            day = c1.selectbox("Day of Week", days, index=days.index(current_day) if current_day in days else 6)
            
            hours = [f"{h:02d}:00" for h in range(24)]
            current_time = str(user_data.get('digest_time', '09:00'))[:5]
            hour = c2.selectbox("Time (UTC)", hours, index=hours.index(current_time) if current_time in hours else 9)

            if st.form_submit_button("Save Settings"):
                focus_list = [f.strip() for f in focus.split(",") if f.strip()]
                update_data = {
                    "role": role,
                    "personal_email": p_email,
                    "focus_areas": focus_list,
                    "digest_day": day,
                    "digest_time": hour
                }
                supabase.table("profiles").update(update_data).eq("id", user_id).execute()
                st.success("✅ Settings saved!")
                # Update local session data
                user_data.update(update_data)

    # PAGE: BRIEFS
    elif page == "📊 My Briefs":
        st.header("Your Strategic Reports")
        res = supabase.table("digests").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        
        if not res.data:
            st.info("Your first brief will appear here soon.")
        else:
            for d in res.data:
                date_label = d['created_at'][:10]
                with st.expander(f"📦 Brief from {date_label}: {d.get('subject', 'Weekly Update')}"):
                    content = d.get('structured_content', {})
                    if isinstance(content, str): content = json.loads(content)

                    st.markdown(f"""
                        <div class="big-picture-box">
                            <strong>🌍 The Big Picture:</strong><br>{content.get('big_picture', 'N/A')}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    for trend in content.get('trends', []):
                        st.markdown(f"""
                            <div class="digest-card">
                                <h4 style="color:#2e86de; margin:0;">{trend.get('title', 'Trend')}</h4>
                                <p style="margin-top:10px;">{trend.get('insight', '')}</p>
                            </div>
                        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()