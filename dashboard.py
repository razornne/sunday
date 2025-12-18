import streamlit as st
from supabase import create_client, Client
import os
import json
from dotenv import load_dotenv

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="Sunday AI | Dashboard",
    page_icon="☀️",
    layout="wide"
)

load_dotenv()

# --- 2. STYLING (Dark/Light mode friendly) ---
st.markdown("""
    <style>
    .digest-card {
        padding: 1.2rem;
        border-radius: 0.8rem;
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 1rem;
        background-color: rgba(128, 128, 128, 0.05);
    }
    .big-picture-box {
        padding: 1rem;
        border-left: 4px solid #2e86de;
        background-color: rgba(46, 134, 222, 0.1);
        border-radius: 0.4rem;
        margin-bottom: 1.5rem;
    }
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

# --- 4. DATA LOGIC ---
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
        st.success("✅ Settings updated!")
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False

# --- 5. MAIN APP ---
def main():
    if 'user' not in st.session_state:
        st.title("☀️ Sunday AI")
        email_input = st.text_input("Enter your Email").strip().lower()
        if st.button("Login"):
            res = supabase.table("profiles").select("*").eq("email", email_input).execute()
            if res.data:
                st.session_state['user'] = res.data[0]
                st.rerun()
            else:
                st.error("User not found.")
        st.stop()

    user = st.session_state['user']

    with st.sidebar:
        st.title("Sunday AI")
        st.write(f"Logged in: **{user['email']}**")
        page = st.radio("Navigation", ["📊 My Briefs", "⚙️ AI Settings"])
        st.divider()
        if st.button("Logout"):
            del st.session_state['user']
            st.rerun()

    # PAGE: SETTINGS
    if page == "⚙️ AI Settings":
        st.header("Intelligence & Schedule")
        
        st.info(f"📬 **Your Personal Sunday Email:** `{user.get('personal_email', 'not-assigned')}`")

        with st.form("settings_form"):
            role = st.text_input("Your Professional Role", value=user.get('role', 'Founder'))
            focus = st.text_area("Focus Areas (comma separated)", value=", ".join(user.get('focus_areas', []) or []))
            
            st.divider()
            st.subheader("Delivery Schedule (UTC)")
            c1, c2 = st.columns(2)
            
            # SAFE INDEX LOGIC
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            db_day = user.get('digest_day', 'Sunday')
            day_idx = days.index(db_day) if db_day in days else 6
            
            day = c1.selectbox("Preferred Day", days, index=day_idx)
            
            hours = [f"{h:02d}:00" for h in range(24)]
            db_time = str(user.get('digest_time', '09:00'))[:5]
            time_idx = hours.index(db_time) if db_time in hours else 9
            
            hour = c2.selectbox("Delivery Hour", hours, index=time_idx)

            # THE SUBMIT BUTTON
            if st.form_submit_button("Save Settings"):
                if save_user_settings(user['id'], role, focus, day, hour):
                    user.update({"role": role, "digest_day": day, "digest_time": hour})
                    st.session_state['user'] = user

    # PAGE: BRIEFS
    elif page == "📊 My Briefs":
        st.header("Your Weekly Reports")
        res = supabase.table("digests").select("*").eq("user_id", user['id']).order("created_at", desc=True).execute()
        
        if not res.data:
            st.info("No reports yet. Forward some emails and wait for your scheduled time!")
        else:
            for d in res.data:
                with st.expander(f"📦 Brief from {d['created_at'][:10]}: {d.get('subject', 'Update')}"):
                    content = d.get('structured_content', {})
                    if isinstance(content, str):
                        try: content = json.loads(content)
                        except: st.write(content); continue

                    st.markdown(f"""
                        <div class="big-picture-box">
                            <strong>🌍 The Big Picture:</strong><br>
                            {content.get('big_picture', 'No summary')}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    for trend in content.get('trends', []):
                        st.markdown(f"""
                            <div class="digest-card">
                                <h4 style="color:#2e86de; margin:0;">{trend.get('title', 'Trend')}</h4>
                                <p>{trend.get('insight', '')}</p>
                            </div>
                        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()