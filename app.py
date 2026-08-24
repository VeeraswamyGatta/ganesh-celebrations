import streamlit as st
from streamlit_option_menu import option_menu
import datetime
from app.db import get_connection
from app.sponsorship import sponsorship_tab
from app.events import events_tab
from app.statistics import statistics_tab
from app.admin import admin_tab


st.set_page_config(page_title="Terrazzo Ganesh Celebrations 2026", page_icon="🙏", layout="wide")
from PIL import Image
ganesh_img = Image.open("ganesh.png")


# ---------- Constants ----------

ADMIN_USERNAME = st.secrets["admin_user"]
ADMIN_PASSWORD_BASE = st.secrets["admin_pass"]
import pytz
def get_admin_password():
    cst = pytz.timezone('US/Central')
    now_utc = datetime.datetime.now(pytz.utc)
    now_cst = now_utc.astimezone(cst)
    today_day = now_cst.strftime('%d')
    return f"{ADMIN_PASSWORD_BASE}{today_day}"

# ---------- DB Setup ----------

conn = get_connection()


# ---------- Styling ----------
st.markdown("""
<style>
    .block-container {
        padding: 2rem;
        border-radius: 10px;
    }
    label > div[data-testid="stMarkdownContainer"] > p:first-child:before {
        content: "* ";
        color: red;
    }
    div[data-baseweb="input"] > div,
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="textarea"],
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border: 1px solid #c5d9c0 !important;
        border-radius: 9px !important;
        color: #263238 !important;
        box-shadow: 0 1px 3px rgba(46, 125, 50, 0.07) !important;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input,
    div[data-baseweb="textarea"] textarea,
    .stTextInput input,
    .stDateInput input,
    .stTimeInput input,
    .stNumberInput input,
    .stTextArea textarea {
        background-color: #ffffff !important;
        color: #263238 !important;
        -webkit-text-fill-color: #263238 !important;
    }
    input[type="text"],
    input[type="date"],
    input[type="time"],
    input[type="number"],
    textarea,
    .stTextInput input,
    .stDateInput input,
    .stTimeInput input,
    .stNumberInput input {
        background: #ffffff !important;
        background-color: #ffffff !important;
    }
    .stSelectbox [data-baseweb="select"] > div,
    .stSelectbox [data-baseweb="select"] > div > div {
        background: #ffffff !important;
        background-color: #ffffff !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] [role="combobox"],
    [data-testid="stSelectbox"] [data-baseweb="select"] [role="combobox"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] [role="combobox"] span {
        color: #263238 !important;
        -webkit-text-fill-color: #263238 !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] [role="combobox"] {
        min-height: 2.7rem;
    }
    [data-baseweb="popover"] [role="option"] {
        background: #ffffff !important;
        color: #263238 !important;
    }
    div[data-baseweb="input"] input:focus,
    div[data-baseweb="textarea"] textarea:focus {
        border-color: #2e7d32 !important;
        box-shadow: 0 0 0 2px rgba(46, 125, 50, 0.14) !important;
    }
    div[data-baseweb="input"] input::placeholder,
    div[data-baseweb="base-input"] input::placeholder,
    div[data-baseweb="textarea"] textarea::placeholder,
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #78909c !important;
        opacity: 1;
    }
    .nav-pills:not(.flex-column) {
        background: linear-gradient(135deg, #fff8e1 0%, #f1f8e9 52%, #e3f2fd 100%);
        border: 1px solid #d7ccc8;
        border-radius: 16px;
        box-shadow: 0 6px 18px rgba(93, 64, 55, 0.12);
        padding: 0.45rem;
        margin: 0 auto 1.2rem;
    }
    .nav-pills:not(.flex-column) {
        gap: 0.35rem;
    }
    .nav-pills:not(.flex-column) .nav-link {
        min-height: 3rem;
        border-radius: 11px;
        font-weight: 650;
        transition: transform 160ms ease, box-shadow 160ms ease;
    }
    .nav-pills:not(.flex-column) .nav-link:hover {
        transform: translateY(-1px);
        box-shadow: 0 3px 8px rgba(93, 64, 55, 0.14);
    }
    @media (max-width: 640px) {
        .block-container {
            padding: 1rem 0.7rem;
        }
        .nav-pills:not(.flex-column) {
            border-radius: 13px;
            padding: 0.35rem;
            margin-bottom: 0.8rem;
        }
        .nav-pills:not(.flex-column) {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.3rem;
        }
        .nav-pills:not(.flex-column) .nav-link {
            min-height: 2.8rem;
            padding: 0.55rem 0.3rem;
            font-size: 0.82rem;
            line-height: 1.15;
        }
    }
</style>
""", unsafe_allow_html=True)


# Initialize admin login state if not set
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False




# ---------- User Login on Landing Page ----------
USER_USERNAME = st.secrets["user_username"]
USER_PASSWORD = st.secrets["user_password"]

if "user_logged_in" not in st.session_state:
    st.session_state.user_logged_in = False

show_login_form = False
# Only show the initial menu if not logged in
if not st.session_state.user_logged_in and not st.session_state.admin_logged_in:
    # Open on Login while keeping the public pages available.
    initial_menu = option_menu(
        "Menu",
        ["Login", "Prasad Seva", "Events"],
        icons=["box-arrow-in-right", "award", "calendar-event"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#bf360c", "font-size": "1.1rem"},
            "nav-link": {"color": "#4e342e", "font-size": "0.95rem", "text-align": "center", "margin": "0"},
            "nav-link-selected": {"background-color": "#2e7d32", "color": "#ffffff"}
        }
    )
    if initial_menu == "Prasad Seva":
        from app.prasad_seva import prasad_seva_tab
        prasad_seva_tab()
    elif initial_menu == "Events":
        from app.events import events_tab
        events_tab()
    elif initial_menu == "Login":
        show_login_form = True
else:
    show_login_form = False
if show_login_form:
    role = st.selectbox("Login as", ["User", "Admin"], index=0)
    if role == "User":
        with st.form("user_login_form"):
            user = st.text_input("👤 Username", key="user_login_username")
            pwd = st.text_input("🔒 Password", type="password", key="user_login_password")
            login = st.form_submit_button("Login", help="Login as User", use_container_width=True)
        if login:
            user = user.strip().lower()
            pwd = pwd.strip().lower()
            errors = []
            if not user:
                errors.append("Username is required.")
            if not pwd:
                errors.append("Password is required.")
            apartment = None
            base_pwd = USER_PASSWORD
            apt_num = None
            if pwd.startswith(base_pwd) and len(pwd) > len(base_pwd):
                apt_str = pwd[len(base_pwd):]
                if apt_str.isdigit():
                    apt_num = int(apt_str)
                    if not (100 <= apt_num <= 1600):
                        pass
                    else:
                        apartment = apt_str
                else:
                    errors.append("Apartment Number must be numeric and follow the password.")
            elif pwd == base_pwd:
                apartment = None
            else:
                errors.append("Username or password is incorrect.")
            if user != USER_USERNAME:
                errors.append("Invalid username.")
            if errors:
                st.markdown("""
                <div style='background:#ffebee;border-radius:10px;padding:16px 18px;margin-bottom:12px;border:1px solid #e57373;'>
                    <span style='color:#d32f2f;font-size:1.1em;font-weight:bold;'>⚠️ Login Error</span>
                    <ul style='color:#d32f2f;margin-top:8px;'>
                        {} 
                    </ul>
                </div>
                """.format("".join([f"<li>{err}</li>" for err in errors])), unsafe_allow_html=True)
                st.info("For login issues, please reach out in the Ganesh Chaturthi celebrations 2025 WhatsApp group.")
            else:
                st.session_state.user_logged_in = True
                st.session_state.user_apartment = apartment if apartment else ""
                st.success("✅ User login successful!")
                st.rerun()
    else:
        with st.form("admin_login_form"):
            user = st.text_input("👤 Admin Username", key="admin_login_username")
            pwd = st.text_input("🔒 Admin Password", type="password", key="admin_login_password")
            full_name = st.text_input("📝 Your Full Name (for audit trail) *", key="admin_login_full_name", placeholder="Enter your full name")
            login = st.form_submit_button("Login", help="Login as Admin", use_container_width=True)
        if login:
            user = user.strip().lower()
            pwd = pwd.strip().lower()
            full_name = full_name.strip()
            errors = []
            if not user:
                errors.append("Username is required.")
            if not pwd:
                errors.append("Password is required.")
            if not full_name:
                errors.append("Your Full Name is required for audit trail.")
            if user == ADMIN_USERNAME and pwd == get_admin_password() and not errors:
                st.session_state.admin_logged_in = True
                st.session_state.admin_full_name = full_name
                st.success("✅ Admin access granted!")
                st.rerun()
            else:
                if not (user == ADMIN_USERNAME and pwd == get_admin_password()) and not errors:
                    errors.append("❌ Invalid admin credentials")
                if errors:
                    st.markdown("""
                    <div style='background:#ffebee;border-radius:10px;padding:16px 18px;margin-bottom:12px;border:1px solid #e57373;'>
                        <span style='color:#d32f2f;font-size:1.1em;font-weight:bold;'>⚠️ Login Error</span>
                        <ul style='color:#d32f2f;margin-top:8px;'>
                            {} 
                        </ul>
                    </div>
                    """.format("".join([f"<li>{err}</li>" for err in errors])), unsafe_allow_html=True)
else:
    # Show menu based on role after successful login
    if st.session_state.admin_logged_in:
        menu_items = ["Contributions", "Events", "Prasad Seva", "Statistics", "Expenses", "Admin"]
        menu_icons = ["gift", "calendar-event", "award", "bar-chart", "cash-coin", "lock"]
    elif st.session_state.user_logged_in:
        menu_items = ["Contributions", "Events", "Prasad Seva", "Statistics", "Expenses"]
        menu_icons = ["gift", "calendar-event", "award", "bar-chart", "cash-coin"]
    else:
        menu_items = []
        menu_icons = []
    if menu_items:
        main_menu = option_menu(
            "Menu",
            menu_items,
            icons=menu_icons,
            menu_icon="cast",
            default_index=0,
            orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#bf360c", "font-size": "1.1rem"},
                "nav-link": {"color": "#4e342e", "font-size": "0.95rem", "text-align": "center", "margin": "0"},
                "nav-link-selected": {"background-color": "#2e7d32", "color": "#ffffff"}
            }
        )
        if st.button("Logout", key="logout_button"):
            st.session_state.user_logged_in = False
            st.session_state.admin_logged_in = False
            st.session_state.pop('is_admin', None)
            st.rerun()

        if main_menu == "Contributions":
            sponsorship_tab()
        elif main_menu == "Events":
            if 'admin_full_name' not in st.session_state or not st.session_state['admin_full_name']:
                st.session_state['admin_full_name'] = ''
            events_tab()
        elif main_menu == "Prasad Seva":
            from app.prasad_seva import prasad_seva_tab
            prasad_seva_tab()
        elif main_menu == "Statistics":
            # Set is_admin flag for statistics
            st.session_state['is_admin'] = st.session_state.admin_logged_in
            statistics_tab()
        elif main_menu == "Expenses":
            from app.expenses import expenses_tab
            expenses_tab()
        elif st.session_state.admin_logged_in and main_menu == "Admin":
            if 'admin_full_name' not in st.session_state:
                st.session_state.admin_full_name = ''
            admin_menu = option_menu(
                "Admin Sections",
                [
                    "Payment Details",
                    "Sponsorship Record",
                    "Sponsorship Items",
                    "Manage Notification Emails"
                ],
                icons=["credit-card", "pencil-square", "list-task", "envelope-fill"],
                menu_icon="gear",
                default_index=0,
                orientation="vertical"
            )
            admin_tab(menu=admin_menu)
