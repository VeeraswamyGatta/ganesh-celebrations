import streamlit as st
from streamlit_option_menu import option_menu
import datetime
import time

from app.login_audit import end_login_audit, get_today_visit_count, start_login_audit, touch_login_audit


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
        background: #fffaf0 !important;
        max-width: 900px !important;
        display: flex !important;
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        overflow-y: hidden !important;
        scrollbar-width: thin;
        border: 1px solid #d7ccc8 !important;
        border-radius: 18px !important;
        box-shadow: 0 8px 20px rgba(93, 64, 55, 0.14) !important;
        padding: 0.55rem !important;
        margin: 0 auto 1.2rem !important;
        font-family: "Trebuchet MS", Georgia, serif !important;
    }
    .nav-pills:not(.flex-column) {
        gap: 0.35rem !important;
    }
    .nav-pills:not(.flex-column) .nav-link {
        min-height: 3.1rem !important;
        width: 100% !important;
        border-radius: 12px !important;
        color: #5d4037 !important;
        font-size: 0.94rem !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
        flex: 0 0 auto !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.4rem !important;
        transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease;
    }
    .nav-pills:not(.flex-column) > li {
        flex: 1 1 0 !important;
        min-width: 0 !important;
    }
    .nav-pills:not(.flex-column) .nav-link i {
        color: #bf360c !important;
        font-size: 1.05rem;
    }
    .nav-pills:not(.flex-column) .nav-link.active,
    .nav-pills:not(.flex-column) .nav-link:hover {
        background: linear-gradient(135deg, #bf360c, #d84315) !important;
        color: #ffffff !important;
        box-shadow: 0 5px 12px rgba(191, 54, 12, 0.25) !important;
    }
    .nav-pills:not(.flex-column) .nav-link.active i,
    .nav-pills:not(.flex-column) .nav-link:hover i {
        color: #fff8e1 !important;
    }
    .nav-pills:not(.flex-column) .nav-link:hover {
        transform: translateY(-1px);
    }
    .landing-hero {
        position: relative;
        overflow: hidden;
        margin: 0.8rem auto 1.4rem;
        padding: 2.4rem 2.6rem 2.2rem;
        max-width: 900px;
        border: 1px solid #d7ccc8;
        border-radius: 22px;
        background: linear-gradient(115deg, #fff8e1 0%, #fffdf7 48%, #e8f5e9 100%);
        box-shadow: 0 12px 30px rgba(93, 64, 55, 0.13);
    }
    .landing-hero:after {
        content: "";
        position: absolute;
        right: -55px;
        top: -75px;
        width: 210px;
        height: 210px;
        border: 18px solid rgba(255, 183, 77, 0.2);
        border-radius: 50%;
    }
    .landing-kicker {
        color: #bf360c;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .landing-title {
        position: relative;
        z-index: 1;
        margin: 0.35rem 0 0.4rem;
        color: #3e2723;
        font-size: clamp(2rem, 4vw, 3.5rem);
        line-height: 1.05;
        font-weight: 800;
    }
    .landing-subtitle {
        position: relative;
        z-index: 1;
        max-width: 650px;
        margin: 0;
        color: #546e7a;
        font-size: 1.05rem;
    }
    .landing-details {
        position: relative;
        z-index: 1;
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 1.25rem;
    }
    .landing-detail {
        padding: 0.45rem 0.75rem;
        border: 1px solid #c5d9c0;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.72);
        color: #2e7d32;
        font-size: 0.88rem;
        font-weight: 700;
    }
    .login-panel-title {
        margin: 0;
        color: #3e2723;
        font-size: 1.55rem;
        font-weight: 800;
    }
    .login-panel-copy {
        margin: 0.25rem 0 1rem;
        color: #546e7a;
        font-size: 0.92rem;
    }
    [data-testid="stForm"] {
        border: 1px solid #d7ccc8 !important;
        border-radius: 18px !important;
        background: linear-gradient(135deg, #fffdf7 0%, #f1f8e9 100%) !important;
        box-shadow: 0 10px 26px rgba(93, 64, 55, 0.12) !important;
        padding: 1.5rem !important;
    }
    [data-testid="stFormSubmitButton"] button {
        min-height: 2.8rem !important;
        border: 0 !important;
        border-radius: 10px !important;
        background: linear-gradient(135deg, #2e7d32, #43a047) !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        box-shadow: 0 5px 12px rgba(46, 125, 50, 0.2) !important;
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
            overflow-x: visible !important;
        }
        .nav-pills:not(.flex-column) .nav-link {
            min-height: 2.8rem;
            padding: 0.55rem 0.3rem;
            font-size: 0.82rem;
            line-height: 1.15;
        }
        .landing-hero {
            margin-top: 0.4rem;
            padding: 1.7rem 1.25rem 1.5rem;
            border-radius: 17px;
        }
        .landing-subtitle {
            font-size: 0.95rem;
        }
    }
</style>
""", unsafe_allow_html=True)


# Initialize admin login state if not set
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

SESSION_IDLE_TIMEOUT_SECONDS = int(st.secrets.get("session_idle_timeout_seconds", 15 * 60))


def end_session():
    end_login_audit(st.session_state.get("login_audit_session_id"))
    st.session_state.user_logged_in = False
    st.session_state.admin_logged_in = False
    st.session_state.pop("admin_full_name", None)
    st.session_state.pop("admin_audit_name_pending", None)
    st.session_state.pop("last_activity_at", None)
    st.session_state.pop("login_audit_session_id", None)


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
        touch_login_audit(st.session_state.get("login_audit_session_id"))




# ---------- User Login on Landing Page ----------
USER_USERNAME = st.secrets["user_username"]
USER_PASSWORD = st.secrets["user_password"]

if "user_logged_in" not in st.session_state:
    st.session_state.user_logged_in = False

enforce_idle_timeout()

show_login_form = False
# Only show the initial menu if not logged in
if not st.session_state.user_logged_in and not st.session_state.admin_logged_in:
    st.markdown(
        """
        <section class="landing-hero">
            <div class="landing-kicker">Terrazzo Community • 2026</div>
            <h1 class="landing-title">Ganesh Celebrations</h1>
            <p class="landing-subtitle">A shared celebration of devotion, service, and community spirit.</p>
            <div class="landing-details">
                <span class="landing-detail">🗓️ 14–20 September 2026</span>
                <span class="landing-detail">📍 3C Garage</span>
                <span class="landing-detail">🙏 Austin, Texas</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    # Open on Login while keeping the public pages available.
    menu_left, menu_center, menu_right = st.columns([1, 1.15, 1])
    with menu_center:
        initial_menu = option_menu(
            "",
            ["Login", "Prasad Seva", "Events"],
            icons=["box-arrow-in-right", "award", "calendar-event"],
            menu_icon="cast",
            default_index=0,
            orientation="horizontal",
            styles={
                "container": {"padding": "0.55rem", "background-color": "#fffaf0", "border": "1px solid #d7ccc8", "border-radius": "16px", "box-shadow": "0 7px 18px rgba(93, 64, 55, 0.12)"},
                "icon": {"color": "#bf360c", "font-size": "1rem"},
                "nav-link": {"color": "#5d4037", "font-size": "0.92rem", "text-align": "center", "margin": "0 0.15rem", "border-radius": "9px"},
                "nav-link-selected": {"background-color": "#bf360c", "color": "#ffffff", "font-weight": "700"}
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
        timeout_minutes = SESSION_IDLE_TIMEOUT_SECONDS // 60
        timeout_text = (
            f"{SESSION_IDLE_TIMEOUT_SECONDS} seconds"
            if timeout_minutes == 0
            else f"{timeout_minutes} minutes"
        )
        st.warning(f"Your session expired after {timeout_text} of inactivity. Please log in again.")
    if st.session_state.get("admin_audit_name_pending", False):
        login_left, login_center, login_right = st.columns([1, 1.15, 1])
        with login_center:
            st.markdown(
                "<h2 class='login-panel-title'>Complete Admin Sign In</h2>"
                "<p class='login-panel-copy'>Add your name to continue securely.</p>",
                unsafe_allow_html=True,
            )
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
                st.session_state.login_audit_session_id = start_login_audit("Admin", ADMIN_USERNAME)
                st.session_state.last_activity_at = time.monotonic()
                st.success("✅ Admin access granted!")
                st.rerun()
    else:
        login_left, login_center, login_right = st.columns([1, 1.15, 1])
        with login_center:
            with st.form("login_form"):
                user = st.text_input("👤 Username")
                pwd = st.text_input("🔒 Password", type="password")
                login_error = st.empty()
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
                    st.session_state.login_audit_session_id = start_login_audit("User", USER_USERNAME)
                    st.session_state.last_activity_at = time.monotonic()
                    st.success("✅ User login successful!")
                    st.rerun()
                else:
                    login_error.markdown(
                        """
                        <div style="
                            margin: 0.35rem 0 0.75rem;
                            padding: 0.75rem 0.9rem;
                            border: 1px solid #ef9a9a;
                            border-left: 4px solid #d32f2f;
                            border-radius: 10px;
                            background: #ffebee;
                            color: #b71c1c;
                            font-size: 0.9rem;
                            font-weight: 700;
                            text-align: center;
                        ">
                            Invalid username or password.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
else:
    # Show menu based on role after successful login
    if st.session_state.admin_logged_in:
        menu_items = ["Contributions", "Events", "Prasad", "Stats", "Expenses", "Payments", "Admin"]
        menu_icons = ["gift", "calendar-event", "award", "bar-chart", "cash-coin", "credit-card", "lock"]
    elif st.session_state.user_logged_in:
        menu_items = ["Contributions", "Events", "Prasad", "Stats", "Expenses"]
        menu_icons = ["gift", "calendar-event", "award", "bar-chart", "cash-coin"]
    else:
        menu_items = []
        menu_icons = []
    if menu_items:
        menu_left, menu_column, logout_column = st.columns([0.1, 0.82, 0.08])
        with menu_column:
            main_menu = option_menu(
                "",
                menu_items,
                icons=menu_icons,
                menu_icon="cast",
                default_index=0,
                orientation="horizontal",
                styles={
                    "container": {"padding": "0.55rem", "background-color": "#fffaf0", "border": "1px solid #d7ccc8", "border-radius": "16px", "box-shadow": "0 7px 18px rgba(93, 64, 55, 0.12)"},
                    "icon": {"color": "#bf360c", "font-size": "1rem"},
                    "nav-link": {"color": "#5d4037", "font-size": "0.92rem", "text-align": "center", "margin": "0 0.15rem", "border-radius": "9px"},
                    "nav-link-selected": {"background-color": "#bf360c", "color": "#ffffff", "font-weight": "700"}
                }
            )
        with logout_column:
            if st.button(":material/logout:", help="Logout", key="logout_button", use_container_width=True):
                end_session()
                st.session_state.pop('is_admin', None)
                st.rerun()

        if st.session_state.admin_logged_in:
            try:
                admin_visits, user_visits, total_visits = get_today_visit_count()
                today_label = datetime.datetime.now().strftime("%A, %d %B %Y")
                st.markdown(
                    f"""
                    <div style="
                        margin: 1.2rem 0 1.5rem;
                        padding: 1.1rem 1.4rem;
                        border: 1px solid #c5d9c0;
                        border-left: 6px solid #2e7d32;
                        border-radius: 12px;
                        background: linear-gradient(100deg, #f1f8e9 0%, #fffde7 100%);
                        box-shadow: 0 3px 12px rgba(46, 125, 50, 0.12);
                    ">
                        <div style="color:#2e7d32; font-size:0.9rem; font-weight:700;">
                            TODAY'S VISITS
                        </div>
                        <div style="color:#263238; font-size:2rem; font-weight:800; line-height:1.15; margin-top:0.25rem;">
                            {total_visits}
                        </div>
                        <div style="color:#546e7a; font-size:0.9rem; margin-top:0.2rem;">
                            Today's Date &nbsp;•&nbsp; {today_label}
                        </div>
                        <div style="color:#546e7a; font-size:0.9rem; margin-top:0.55rem;">
                            Admin: <strong>{admin_visits}</strong>
                            &nbsp;&nbsp;|&nbsp;&nbsp;
                            Users: <strong>{user_visits}</strong>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            except Exception:
                st.warning("Today's visit count is currently unavailable.")

        if main_menu == "Contributions":
            from app.sponsorship import sponsorship_tab
            sponsorship_tab()
        elif main_menu == "Events":
            if 'admin_full_name' not in st.session_state or not st.session_state['admin_full_name']:
                st.session_state['admin_full_name'] = ''
            from app.events import events_tab
            events_tab()
        elif main_menu == "Prasad":
            from app.prasad_seva import prasad_seva_tab
            prasad_seva_tab()
        elif main_menu == "Stats":
            # Set is_admin flag for statistics
            st.session_state['is_admin'] = st.session_state.admin_logged_in
            from app.statistics import statistics_tab
            statistics_tab()
        elif main_menu == "Expenses":
            from app.expenses import expenses_tab
            expenses_tab()
        elif st.session_state.admin_logged_in and main_menu == "Payments":
            from app.admin import admin_tab
            admin_tab(menu="Sponsorship Payment Details")
        elif st.session_state.admin_logged_in and main_menu == "Admin":
            if 'admin_full_name' not in st.session_state:
                st.session_state.admin_full_name = ''
            from app.admin import admin_tab
            admin_menu = option_menu(
                "Admin Sections",
                [
                    "User Login Activity",
                    "Sponsorship Record",
                    "Sponsorship Items",
                    "Committee Members",
                    "Manage Notification Emails"
                ],
                icons=["bar-chart", "pencil-square", "list-task", "people-fill", "envelope-fill"],
                menu_icon="gear",
                default_index=0,
                orientation="vertical"
            )
            admin_tab(menu=admin_menu)
