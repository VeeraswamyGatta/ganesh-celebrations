import streamlit as st
import streamlit.components.v1 as components
from streamlit_option_menu import option_menu
import datetime
import time
import base64
from io import BytesIO

from app.login_audit import end_login_audit, get_today_visit_count, start_login_audit, touch_login_audit


st.set_page_config(page_title="Terrazzo Ganesh Celebrations 2026", page_icon="🙏", layout="wide")
from PIL import Image
ganesh_img = Image.open("ganesh.png")
ganesh_image_buffer = BytesIO()
ganesh_img.save(ganesh_image_buffer, format="PNG")
ganesh_image_base64 = base64.b64encode(ganesh_image_buffer.getvalue()).decode("ascii")


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
    /* Hide Streamlit header to give more space */
    header {
        display: none !important;
    }
    .block-container {
        padding: 2rem;
        padding-top: 2rem;
        border-radius: 10px;
    }
    div[class*="st-key-logout_button"] {
        display: none !important;
    }
    /* Make landing nav buttons display in one row */
    [data-testid="column"] {
        flex: 1 !important;
        min-width: 0 !important;
        display: flex !important;
        flex-direction: column !important;
    }
    .stColumns {
        display: flex !important;
        gap: 0.75rem !important;
        flex-direction: row !important;
        width: 100% !important;
    }
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        gap: 0.75rem !important;
        flex-direction: row !important;
        width: 100% !important;
    }
    /* Ensure login nav items are in one row */
    div[class*="st-key-landing_nav_login"],
    div[class*="st-key-landing_nav_prasad_seva"],
    div[class*="st-key-landing_nav_events"] {
        width: 33.33% !important;
        flex: 1 !important;
        display: flex !important;
        flex-direction: column !important;
    }
    .nav-pills:not(.flex-column) {
        margin-top: 0.4rem;
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
        padding: 1.35rem;
        max-width: 640px;
        border: 1px solid #d7e3d4;
        border-radius: 12px;
        background: linear-gradient(135deg, #fffaf0 0%, #ffffff 52%, #edf7ee 100%);
        box-shadow: 0 10px 24px rgba(46, 125, 50, 0.1);
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
    .landing-event-label {
        position: relative;
        z-index: 1;
        margin: 0 auto 0.85rem;
        color: #2e7d32;
        font-size: 0.8rem;
        line-height: 1.2;
        font-weight: 800;
        text-align: center;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
    .landing-event-label:after {
        content: "";
        display: block;
        width: 42px;
        height: 2px;
        margin: 0.45rem auto 0;
        background: #e6a92f;
    }
    div[class*="st-key-landing_nav_login"],
    div[class*="st-key-landing_nav_prasad_seva"],
    div[class*="st-key-landing_nav_events"] {
        width: 33.33% !important;
        flex: 1 !important;
        display: flex !important;
        flex-direction: column !important;
    }
    /* Parent container for landing nav - force horizontal layout */
    [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_login"]),
    [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_prasad_seva"]),
    [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_events"]) {
        display: flex !important;
        flex-direction: row !important;
        gap: 0.75rem !important;
        width: 100% !important;
    }
    [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_login"]) > [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_prasad_seva"]) > [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_events"]) > [data-testid="stColumn"] {
        flex: 1 !important;
        width: 33.33% !important;
    }
    div[class*="st-key-landing_nav_login"] button,
    div[class*="st-key-landing_nav_prasad_seva"] button,
    div[class*="st-key-landing_nav_events"] button {
        width: 100% !important;
        min-height: 3.3rem !important;
        border: 1px solid #e4ddd7 !important;
        border-radius: 10px !important;
        background: #ffffff !important;
        color: #8b1737 !important;
        font-size: 0.95rem !important;
        font-weight: 800 !important;
        box-shadow: 0 2px 6px rgba(80, 38, 28, 0.08) !important;
    }
    div[class*="st-key-landing_nav_login"] button p:before,
    div[class*="st-key-landing_nav_prasad_seva"] button p:before,
    div[class*="st-key-landing_nav_events"] button p:before {
        display: block;
        margin-bottom: 0.35rem;
        font-size: 1.4rem;
        font-weight: 400;
        line-height: 1;
    }
    div[class*="st-key-landing_nav_login"] button p:before { content: "⌂"; }
    div[class*="st-key-landing_nav_prasad_seva"] button p:before { content: "♨"; }
    div[class*="st-key-landing_nav_events"] button p:before { content: "▣"; }
    div[class*="st-key-landing_nav_login"] button:hover,
    div[class*="st-key-landing_nav_prasad_seva"] button:hover,
    div[class*="st-key-landing_nav_events"] button:hover,
    div[class*="st-key-landing_nav_login"] button:focus-visible,
    div[class*="st-key-landing_nav_prasad_seva"] button:focus-visible,
    div[class*="st-key-landing_nav_events"] button:focus-visible,
    div[class*="st-key-landing_nav_login"] button:active,
    div[class*="st-key-landing_nav_prasad_seva"] button:active,
    div[class*="st-key-landing_nav_events"] button:active {
        background: #f5f0e8 !important;
        color: #8b1737 !important;
        border-color: #d7ccc8 !important;
    }
    div[class*="st-key-landing_nav_login"] button[kind="primary"],
    div[class*="st-key-landing_nav_prasad_seva"] button[kind="primary"],
    div[class*="st-key-landing_nav_events"] button[kind="primary"] {
        background: linear-gradient(135deg, #6a1b1b, #8b1737) !important;
        color: #ffffff !important;
        border-color: #6a1b1b !important;
        box-shadow: 0 3px 8px rgba(106, 27, 27, 0.22) !important;
    }
    div[class*="st-key-landing_nav_login"] button:hover p,
    div[class*="st-key-landing_nav_prasad_seva"] button:hover p,
    div[class*="st-key-landing_nav_events"] button:hover p,
    div[class*="st-key-landing_nav_login"] button:focus-visible p,
    div[class*="st-key-landing_nav_prasad_seva"] button:focus-visible p,
    div[class*="st-key-landing_nav_events"] button:focus-visible p,
    div[class*="st-key-landing_nav_login"] button:active p,
    div[class*="st-key-landing_nav_prasad_seva"] button:active p,
    div[class*="st-key-landing_nav_events"] button:active p {
        color: inherit !important;
    }
    .landing-title .landing-kicker {
        display: inline;
        margin-right: 0.45rem;
        font-size: inherit;
        font-weight: inherit;
        letter-spacing: 0;
        text-transform: none;
        vertical-align: middle;
    }
    .landing-subtitle {
        position: relative;
        z-index: 1;
        max-width: 650px;
        margin: 0;
        color: #546e7a;
        font-size: 1.05rem;
    }
    .landing-showcase {
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .landing-image {
        display: block;
        width: 118px;
        height: auto;
        flex: 0 0 118px;
        object-fit: contain;
        padding: 0.25rem;
        border: 2px solid #f0cf88;
        border-radius: 10px;
        background: #ffffff;
        box-shadow: 0 6px 14px rgba(127, 92, 31, 0.16);
    }
    .landing-details {
        flex: 1;
        display: grid;
        align-content: center;
        gap: 0.45rem;
    }
    .landing-detail {
        color: #2e7d32;
        font-size: 0.8rem;
        font-weight: 700;
        line-height: 1.35;
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
            padding: 1.2rem 0.6rem 2rem;
        }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] div[class*="st-key-main_nav_dashboard"]) {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 0.2rem !important;
            align-items: center !important;
            padding: 0.35rem 0.2rem !important;
            border-radius: 14px !important;
            background: linear-gradient(135deg, #ffffff 0%, #fffdf8 100%) !important;
            border: 1px solid #ead8a9 !important;
            box-shadow: 0 4px 14px rgba(93, 64, 55, 0.08) !important;
            margin-bottom: 1rem !important;
            overflow-x: auto !important;
        }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] div[class*="st-key-main_nav_dashboard"]) > [data-testid="stColumn"] {
            flex: 1 0 64px !important;
            width: auto !important;
            min-width: 64px !important;
        }
        div[class*="st-key-main_nav_"] button {
            min-height: 3.4rem !important;
            padding: 0.25rem 0.1rem !important;
            border: 1px solid #f0eae1 !important;
            border-radius: 10px !important;
            background: #ffffff !important;
            color: #4f5360 !important;
            font-size: 0.62rem !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }
        div[class*="st-key-main_nav_"] button p {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 0.18rem !important;
            margin: 0 !important;
            white-space: nowrap !important;
        }
        div[class*="st-key-main_nav_"] button [data-testid="stIconMaterial"] {
            font-size: 1.1rem !important;
        }
        div[class*="st-key-main_nav_"] button:hover,
        div[class*="st-key-main_nav_"] button:focus-visible,
        div[class*="st-key-main_nav_"] button:active {
            background: #f6f1fa !important;
            color: #642196 !important;
            outline: 0 !important;
        }
        div[class*="st-key-main_nav_"] button[kind="primary"] {
            background: linear-gradient(135deg, #6a1b1b, #8b1737) !important;
            color: #ffffff !important;
            border-color: #6a1b1b !important;
            box-shadow: 0 3px 8px rgba(106, 27, 27, 0.25) !important;
        }
        div[class*="st-key-landing_nav_login"] button,
        div[class*="st-key-landing_nav_prasad_seva"] button,
        div[class*="st-key-landing_nav_events"] button {
            min-height: 3.2rem !important;
            border: 1px solid #ead8a9 !important;
            border-radius: 10px !important;
            background: #ffffff !important;
            color: #4f5360 !important;
            font-size: 0.72rem !important;
            font-weight: 700 !important;
            box-shadow: 0 2px 6px rgba(39, 31, 29, 0.05) !important;
            line-height: 1.1 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        div[class*="st-key-landing_nav_login"] button[kind="primary"],
        div[class*="st-key-landing_nav_prasad_seva"] button[kind="primary"],
        div[class*="st-key-landing_nav_events"] button[kind="primary"] {
            background: linear-gradient(135deg, #6a1b1b, #8b1737) !important;
            color: #ffffff !important;
            border-color: #6a1b1b !important;
            box-shadow: 0 3px 8px rgba(106, 27, 27, 0.22) !important;
        }
        div[class*="st-key-landing_nav_login"] button p,
        div[class*="st-key-landing_nav_prasad_seva"] button p,
        div[class*="st-key-landing_nav_events"] button p {
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            margin: 0 !important;
        }
        div[class*="st-key-main_navigation"] .nav-pills:not(.flex-column) {
            position: relative !important;
            z-index: 10 !important;
            display: flex !important;
            flex-wrap: nowrap !important;
            gap: 0.25rem !important;
            overflow-x: auto !important;
            overflow-y: visible !important;
            border: 1px solid #e4ddd7;
            border-radius: 12px;
            background: #ffffff !important;
            box-shadow: 0 3px 12px rgba(80, 38, 28, 0.08) !important;
            padding: 0.8rem !important;
            margin: 0.5rem 0 1.2rem !important;
            scrollbar-width: thin;
        }
        div[class*="st-key-main_navigation"] .nav-pills:not(.flex-column)::-webkit-scrollbar { display: none; }
        div[class*="st-key-main_navigation"] .nav-pills:not(.flex-column) > li {
            flex: 1 0 auto !important;
        }
        div[class*="st-key-main_navigation"] .nav-pills:not(.flex-column) .nav-link {
            min-height: 2.8rem !important;
            padding: 0.4rem 0.8rem !important;
            border-radius: 10px !important;
            flex-direction: row;
            gap: 0.4rem !important;
            font-size: 0.85rem !important;
            line-height: 1.2;
            white-space: nowrap !important;
        }
        div[class*="st-key-main_navigation"] .nav-pills:not(.flex-column) .nav-link i {
            font-size: 1.05rem !important;
        }
        div[class*="st-key-main_navigation"] .nav-pills:not(.flex-column) .nav-link.active,
        div[class*="st-key-main_navigation"] .nav-pills:not(.flex-column) .nav-link:hover {
            background: linear-gradient(135deg, #6a1b1b, #8b1737) !important;
            color: #ffffff !important;
            box-shadow: 0 3px 10px rgba(106, 27, 27, 0.22) !important;
        }
        div[class*="st-key-main_navigation"] .nav-pills:not(.flex-column) .nav-link.active i,
        div[class*="st-key-main_navigation"] .nav-pills:not(.flex-column) .nav-link:hover i {
            color: #ffffff !important;
        }
        div[class*="st-key-landing_navigation"] {
            position: relative;
            z-index: 10;
            padding: 0.8rem 0.5rem;
            border: 1px solid #e4ddd7;
            border-radius: 12px;
            background: #ffffff;
            box-shadow: 0 3px 12px rgba(80, 38, 28, 0.08);
            margin: 0.5rem 0 1.2rem;
            overflow: visible !important;
        }
        div[class*="st-key-landing_navigation"] [role="radiogroup"] {
            display: flex;
            justify-content: space-around;
            gap: 0.25rem;
        }
        div[class*="st-key-landing_navigation"] label {
            flex: 1;
            justify-content: center;
            margin: 0;
            color: #694f43;
            font-size: 0.78rem;
            font-weight: 700;
        }
        div[class*="st-key-landing_navigation"] label > div:first-child {
            display: none;
        }
        .landing-hero {
            margin-top: 0.4rem;
            padding: 1rem;
            border-radius: 10px;
        }
        .landing-subtitle {
            font-size: 0.95rem;
        }
        .landing-image {
            width: 96px;
            flex-basis: 96px;
            padding: 0.2rem;
        }
        .landing-showcase {
            gap: 0.75rem;
        }
        .landing-detail {
            font-size: 0.76rem;
        }
        /* Ensure landing nav buttons stay in one row on mobile */
        [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_login"]),
        [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_prasad_seva"]),
        [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_events"]) {
            display: flex !important;
            flex-direction: row !important;
            gap: 0.5rem !important;
            width: 100% !important;
        }
        [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_login"]) > [data-testid="stColumn"],
        [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_prasad_seva"]) > [data-testid="stColumn"],
        [data-testid="stHorizontalBlock"]:has([class*="st-key-landing_nav_events"]) > [data-testid="stColumn"] {
            flex: 1 !important;
            width: 33.33% !important;
            min-width: 0 !important;
        }
        div[class*="st-key-landing_nav_login"],
        div[class*="st-key-landing_nav_prasad_seva"],
        div[class*="st-key-landing_nav_events"] {
            width: 100% !important;
        }
    }
    /* Global Rich Table & DataFrame Styling */
    div[data-testid="stDataFrame"] {
        border: 1.5px solid #e1bee7 !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 18px rgba(106, 27, 154, 0.08) !important;
        background: #ffffff !important;
        overflow: hidden !important;
        padding: 2px !important;
    }
    .rich-table-card {
        background: linear-gradient(135deg, #ffffff 0%, #fffdf7 100%);
        border: 1.5px solid #ead8a9;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 6px 20px rgba(93, 64, 55, 0.09);
        margin-bottom: 1.2rem;
    }
    .rich-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e0d7c6;
        font-size: 0.9rem;
    }
    .rich-table th {
        background: linear-gradient(135deg, #6a1b1b 0%, #8b1737 100%);
        color: #ffffff;
        font-weight: 700;
        padding: 12px 16px;
        text-align: left;
        letter-spacing: 0.01em;
    }
    .rich-table td {
        padding: 11px 16px;
        color: #263238;
        border-bottom: 1px solid #f0eae1;
    }
    .rich-table tr:last-child td {
        border-bottom: none;
    }
    .rich-table tr:nth-child(even) {
        background-color: #fcf9f2;
    }
    .rich-table tr:hover {
        background-color: #f5efe6;
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
if "auth_loading" not in st.session_state:
    st.session_state.auth_loading = False

enforce_idle_timeout()

if st.session_state.get("auth_loading"):
    st.markdown(
        """
        <div style='display:flex; align-items:center; justify-content:center; min-height:45vh; flex-direction:column; gap:0.8rem;'>
            <div style='width:54px; height:54px; border:5px solid rgba(46,125,50,0.15); border-top:5px solid #2e7d32; border-radius:50%; animation:spin 0.9s linear infinite;'></div>
            <div style='font-size:1.05rem; font-weight:700; color:#2e7d32;'>Logging in...</div>
        </div>
        <style>
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.auth_loading = False
    st.rerun()

show_login_form = False
# Only show the initial menu if not logged in
if not st.session_state.user_logged_in and not st.session_state.admin_logged_in:
    if "landing_navigation" not in st.session_state:
        st.session_state.landing_navigation = "Login"
    selected_landing_navigation = st.session_state.landing_navigation

    # Show navigation menu at the top
    nav_cols = st.columns(3)
    nav_items = [
        ("Login", "landing_nav_login"),
        ("Prasad Seva", "landing_nav_prasad_seva"),
        ("Events", "landing_nav_events"),
    ]
    for idx, (label, key_name) in enumerate(nav_items):
        with nav_cols[idx]:
            is_active = st.session_state.landing_navigation == label
            if st.button(
                label,
                key=key_name,
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                st.session_state.landing_navigation = label
                selected_landing_navigation = label
                st.session_state.scroll_to_top = True

    # Then show the landing hero section below
    st.markdown(
        f"""
        <section class="landing-hero">
            <div class="landing-event-label">Ganesh Celebrations 2026</div>
            <div class="landing-showcase">
                <img class="landing-image" src="data:image/png;base64,{ganesh_image_base64}" alt="Lord Ganesh">
                <div class="landing-details">
                    <span class="landing-detail">🗓️ 14–20 September 2026</span>
                    <span class="landing-detail">📍 3C Garage</span>
                    <span class="landing-detail">🙏 Austin, Texas</span>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("scroll_to_top"):
        components.html("<script>window.parent.scrollTo({top: 0, behavior: 'instant'});</script>", height=0)
        st.session_state["scroll_to_top"] = False

    initial_menu = selected_landing_navigation
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
                    st.session_state.auth_loading = True
                    st.session_state.admin_audit_name_pending = True
                    st.rerun()
                elif username == USER_USERNAME.lower() and password == USER_PASSWORD:
                    st.session_state.auth_loading = True
                    st.session_state.user_logged_in = True
                    st.session_state.user_apartment = ""
                    st.session_state.login_audit_session_id = start_login_audit("User", USER_USERNAME)
                    st.session_state.last_activity_at = time.monotonic()
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
        menu_items = ["Dashboard", "Donate", "Statistics", "Prasad", "Expenses", "Payments", "Admin"]
        menu_icons = ["bar-chart", "gift", "chart-line", "award", "cash-coin", "credit-card", "lock"]
    elif st.session_state.user_logged_in:
        menu_items = ["Dashboard", "Donate", "Statistics", "Prasad", "Expenses"]
        menu_icons = ["bar-chart", "gift", "chart-line", "award", "cash-coin"]
    else:
        menu_items = []
        menu_icons = []
    if menu_items:
        if st.session_state.get("main_navigation") not in menu_items:
            st.session_state.main_navigation = "Dashboard"

        menu_labels = {
            "Dashboard": ":material/dashboard: Home",
            "Donate": ":material/volunteer_activism: Donate",
            "Statistics": ":material/trending_up: Stats",
            "Prasad": ":material/restaurant: Prasad",
            "Expenses": ":material/receipt_long: Expenses",
            "Payments": ":material/credit_card: Pay",
            "Admin": ":material/admin_panel_settings: Admin",
        }
        menu_columns = st.columns(len(menu_items))
        for idx, menu_item in enumerate(menu_items):
            with menu_columns[idx]:
                is_active = st.session_state.main_navigation == menu_item
                if st.button(
                    menu_labels[menu_item],
                    key=f"main_nav_{menu_item.lower()}",
                    type="primary" if is_active else "secondary",
                    use_container_width=True,
                ):
                    st.session_state.main_navigation = menu_item
                    st.session_state.scroll_to_top = True
                    st.rerun()

        if st.session_state.get("scroll_to_top"):
            components.html("<script>window.parent.scrollTo({top: 0, behavior: 'instant'});</script>", height=0)
            st.session_state["scroll_to_top"] = False

        main_menu = st.session_state.main_navigation
        if st.button(":material/logout:", help="Logout", key="logout_button"):
            end_session()
            st.session_state.pop('is_admin', None)
            st.rerun()

        if main_menu == "Dashboard":
            from app.sponsorship import sponsorship_tab
            sponsorship_tab(dashboard_only=True)
        elif main_menu == "Donate":
            from app.sponsorship import sponsorship_tab
            sponsorship_tab()
        elif main_menu == "Statistics":
            from app.statistics import statistics_tab
            statistics_tab()
        elif main_menu == "Prasad":
            from app.prasad_seva import prasad_seva_tab
            prasad_seva_tab()
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
                        <div style="color:#2e7d32; font-size:0.9rem; font-weight:700;">TODAY'S VISITS</div>
                        <div style="color:#263238; font-size:2rem; font-weight:800; line-height:1.15; margin-top:0.25rem;">{total_visits}</div>
                        <div style="color:#546e7a; font-size:0.9rem; margin-top:0.2rem;">Today's Date &nbsp;•&nbsp; {today_label}</div>
                        <div style="color:#546e7a; font-size:0.9rem; margin-top:0.55rem;">Admin: <strong>{admin_visits}</strong> &nbsp;&nbsp;|&nbsp;&nbsp; Users: <strong>{user_visits}</strong></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            except Exception:
                st.warning("Today's visit count is currently unavailable.")
            admin_menu = option_menu(
                "Admin Sections",
                [
                    "User Login Activity",
                    "Sponsorship Record",
                    "Sponsorship Items",
                    "Committee Members",
                    "Manage Notification Emails"
                ],
                icons=["bar-chart-fill", "pencil-square", "card-checklist", "people-fill", "envelope-paper-fill"],
                menu_icon="shield-lock-fill",
                default_index=0,
                orientation="horizontal",
                key="admin_sections_menu",
                styles={
                    "container": {
                        "padding": "0.5rem 0.75rem",
                        "background": "linear-gradient(135deg, #ffffff 0%, #f9f4fc 100%)",
                        "border": "1.5px solid #e1bee7",
                        "border-radius": "16px",
                        "box-shadow": "0 4px 16px rgba(106, 27, 154, 0.1)",
                        "margin-bottom": "1.4rem",
                    },
                    "icon": {
                        "color": "#6A1B9A",
                        "font-size": "1rem"
                    },
                    "nav-link": {
                        "font-size": "0.85rem",
                        "font-weight": "600",
                        "text-align": "center",
                        "margin": "0 4px",
                        "padding": "0.55rem 0.9rem",
                        "border-radius": "12px",
                        "color": "#4a148c",
                        "--hover-color": "#f3e5f5"
                    },
                    "nav-link-selected": {
                        "background": "linear-gradient(135deg, #6A1B9A 0%, #8e24aa 100%)",
                        "color": "#ffffff",
                        "font-weight": "700",
                        "box-shadow": "0 4px 12px rgba(106, 27, 154, 0.3)"
                    },
                    "menu-title": {
                        "color": "#4a148c",
                        "font-weight": "800",
                        "font-size": "1.05rem",
                        "margin-right": "1rem"
                    }
                }
            )
            admin_tab(menu=admin_menu)
