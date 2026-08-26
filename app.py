import streamlit as st
from streamlit_option_menu import option_menu
import datetime
import time


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

SESSION_IDLE_TIMEOUT_SECONDS = 10 * 60


def end_session():
    st.session_state.user_logged_in = False
    st.session_state.admin_logged_in = False
    st.session_state.pop("admin_full_name", None)
    st.session_state.pop("admin_audit_name_pending", None)
    st.session_state.pop("last_activity_at", None)


def enforce_idle_timeout():
    if not (st.session_state.user_logged_in or st.session_state.admin_logged_in):
        return

    now = time.monotonic()
    last_activity_at = st.session_state.get("last_activity_at", now)
    if now - last_activity_at >= SESSION_IDLE_TIMEOUT_SECONDS:
        end_session()
        st.session_state.session_timed_out = True
    else:
        st.session_state.last_activity_at = now




# ---------- User Login on Landing Page ----------
USER_USERNAME = st.secrets["user_username"]
USER_PASSWORD = st.secrets["user_password"]

if "user_logged_in" not in st.session_state:
    st.session_state.user_logged_in = False

enforce_idle_timeout()

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
    if st.session_state.pop("session_timed_out", False):
        st.warning("Your session expired after 10 minutes of inactivity. Please log in again.")
    if st.session_state.get("admin_audit_name_pending", False):
        with st.form("admin_audit_name_form"):
            full_name = st.text_input(
                "📝 Your Full Name (for audit trail) *",
                placeholder="Enter your full name",
            )
            save_name = st.form_submit_button("Continue", use_container_width=True)
        if save_name:
            if not full_name.strip():
                st.error("Your Full Name is required for audit trail.")
            else:
                st.session_state.admin_full_name = full_name.strip()
                st.session_state.admin_logged_in = True
                st.session_state.admin_audit_name_pending = False
                st.session_state.last_activity_at = time.monotonic()
                st.success("✅ Admin access granted!")
                st.rerun()
    else:
        with st.form("login_form"):
            user = st.text_input("👤 Username")
            pwd = st.text_input("🔒 Password", type="password")
            login = st.form_submit_button("Login", use_container_width=True)
        if login:
            username = user.strip().lower()
            password = pwd.strip()
            if username == ADMIN_USERNAME.lower() and password == get_admin_password():
                st.session_state.admin_audit_name_pending = True
                st.rerun()
            elif username == USER_USERNAME.lower() and password == USER_PASSWORD:
                st.session_state.user_logged_in = True
                st.session_state.user_apartment = ""
                st.session_state.last_activity_at = time.monotonic()
                st.success("✅ User login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
else:
    # Show menu based on role after successful login
    if st.session_state.admin_logged_in:
        menu_items = ["Contributions", "Events", "Prasad Seva", "Statistics", "Expenses", "Sponsorship Payment Details", "Admin"]
        menu_icons = ["gift", "calendar-event", "award", "bar-chart", "cash-coin", "credit-card", "lock"]
    elif st.session_state.user_logged_in:
        menu_items = ["Contributions", "Events", "Prasad Seva", "Statistics", "Expenses"]
        menu_icons = ["gift", "calendar-event", "award", "bar-chart", "cash-coin"]
    else:
        menu_items = []
        menu_icons = []
    if menu_items:
        menu_column, logout_column = st.columns([0.94, 0.06])
        with menu_column:
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
        with logout_column:
            if st.button(":material/logout:", help="Logout", key="logout_button", use_container_width=True):
                end_session()
                st.session_state.pop('is_admin', None)
                st.rerun()

        if main_menu == "Contributions":
            from app.sponsorship import sponsorship_tab
            sponsorship_tab()
        elif main_menu == "Events":
            if 'admin_full_name' not in st.session_state or not st.session_state['admin_full_name']:
                st.session_state['admin_full_name'] = ''
            from app.events import events_tab
            events_tab()
        elif main_menu == "Prasad Seva":
            from app.prasad_seva import prasad_seva_tab
            prasad_seva_tab()
        elif main_menu == "Statistics":
            # Set is_admin flag for statistics
            st.session_state['is_admin'] = st.session_state.admin_logged_in
            from app.statistics import statistics_tab
            statistics_tab()
        elif main_menu == "Expenses":
            from app.expenses import expenses_tab
            expenses_tab()
        elif st.session_state.admin_logged_in and main_menu == "Sponsorship Payment Details":
            from app.admin import admin_tab
            admin_tab(menu="Sponsorship Payment Details")
        elif st.session_state.admin_logged_in and main_menu == "Admin":
            if 'admin_full_name' not in st.session_state:
                st.session_state.admin_full_name = ''
            from app.admin import admin_tab
            admin_menu = option_menu(
                "Admin Sections",
                [
                    "Sponsorship Record",
                    "Sponsorship Items",
                    "Committee Members",
                    "Manage Notification Emails"
                ],
                icons=["pencil-square", "list-task", "people-fill", "envelope-fill"],
                menu_icon="gear",
                default_index=0,
                orientation="vertical"
            )
            admin_tab(menu=admin_menu)
