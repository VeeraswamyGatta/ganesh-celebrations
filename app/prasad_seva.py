import streamlit as st
import pandas as pd
import datetime
import re
import textwrap
import pytz
from streamlit_option_menu import option_menu
from datetime import datetime as dt, time as dttime
from .db import get_connection
from .email_utils import send_email

SPONSOR_TABLE_CSS = """
<style>
.sponsor-table-wrap {
    overflow-x: auto;
    border: 1px solid #dce7df;
    border-radius: 8px;
    background: #ffffff;
    box-shadow: 0 4px 14px rgba(44, 92, 62, 0.08);
}
.sponsor-table {
    width: 100%;
    min-width: 620px;
    table-layout: fixed;
    border-collapse: separate;
    border-spacing: 0;
    color: #22372b;
    font-size: 0.9rem;
}
.sponsor-table th {
    background: #eff7f1;
    color: #1f5135;
    font-weight: 700;
    padding: 0.55rem 0.45rem;
    border: 0;
    border-bottom: 2px solid #b8d5c0;
    white-space: normal;
    text-align: left;
}
.sponsor-table td {
    padding: 0.55rem 0.45rem;
    border: 0;
    border-bottom: 1px solid #e6eee8;
    vertical-align: middle;
    line-height: 1.25;
    overflow-wrap: anywhere;
    text-align: left;
}
.sponsor-table tbody tr:nth-child(even) td { background: #fbfdfb; }
.sponsor-table tbody tr:hover td { background: #fff8e7; }
.sponsor-table tbody tr:last-child td { border-bottom: 0; }
.sponsor-table th:first-child,
.sponsor-table td:first-child {
    width: 5%;
    text-align: center;
    color: #a35715;
    font-weight: 700;
}
.sponsor-table th:nth-child(2),
.sponsor-table td:nth-child(2) { width: 22%; }
.sponsor-table th:nth-child(3),
.sponsor-table td:nth-child(3) { width: 18%; }
.sponsor-table th:nth-child(4),
.sponsor-table td:nth-child(4) { width: 11%; }
.sponsor-table th:nth-child(5),
.sponsor-table td:nth-child(5) { width: 8%; }
.sponsor-table th:nth-child(6),
.sponsor-table td:nth-child(6) {
    width: 17%;
    white-space: nowrap;
}
.sponsor-table th:nth-child(7),
.sponsor-table td:nth-child(7) {
    width: 19%;
    white-space: nowrap;
}
.sponsor-table th:nth-child(7),
.sponsor-table td:nth-child(7) { width: 13%; }
.sponsor-table td:nth-child(2) b { font-weight: 600; }
.sponsor-table td span {
    max-width: 100%;
}
@media (max-width: 640px) {
    .sponsor-table-wrap { border-radius: 6px; overflow-x: hidden; }
    .sponsor-table {
        width: 100%;
        min-width: 0;
        table-layout: fixed;
        font-size: 0.68rem;
    }
    .sponsor-table th, .sponsor-table td {
        padding: 0.38rem 0.2rem;
        line-height: 1.12;
        overflow-wrap: anywhere;
    }
    .sponsor-table th:first-child,
    .sponsor-table td:first-child { width: 6%; }
    .sponsor-table th:nth-child(2),
    .sponsor-table td:nth-child(2) { width: 30%; }
    .sponsor-table th:nth-child(3),
    .sponsor-table td:nth-child(3) { width: 19%; }
    .sponsor-table th:nth-child(4),
    .sponsor-table td:nth-child(4) { width: 14%; }
    .sponsor-table th:nth-child(5),
    .sponsor-table td:nth-child(5) { width: 16%; }
    .sponsor-table th:nth-child(6),
    .sponsor-table td:nth-child(6) { width: 15%; white-space: normal; }
    .sponsor-table td:nth-child(4) span {
        padding: 3px 5px !important;
        border-radius: 10px !important;
    }
    .sponsor-table td:nth-child(5) span { font-size: 0.65rem !important; }
    .sponsor-table td:nth-child(5) span:first-child,
    .sponsor-table td:nth-child(6) span:first-child { font-size: 0.8rem !important; }
}
</style>
"""


def get_pooja_options_for_date(seva_date):
    start_date = datetime.date(2026, 9, 14)
    end_date = datetime.date(2026, 9, 20)
    if seva_date is None:
        seva_date = start_date
    if seva_date == end_date:
        return ["Morning Pooja"]
    return ["Evening Pooja"] if seva_date == start_date else ["Morning Pooja", "Evening Pooja"]


def is_prasad_seva_visible_in_table(seva_date, pooja_time, now_cst):
    """Hide today's morning seva from the table after 3 PM Central time."""
    return not (
        seva_date == now_cst.date()
        and now_cst.time() >= dttime(15, 0)
        and "morning" in str(pooja_time).lower()
    )


def get_available_prasad_pooja_options(seva_date, now_cst):
    return [
        option
        for option in get_pooja_options_for_date(seva_date)
        if is_prasad_seva_visible_in_table(seva_date, option, now_cst)
    ]


def is_prasad_seva_in_past_table(seva_date, pooja_time, now_cst):
    return seva_date < now_cst.date() or not is_prasad_seva_visible_in_table(seva_date, pooja_time, now_cst)


def format_prasad_summary_insight(label, value, variant=""):
    if value == "None":
        return ""
    variant_class = f" {variant}" if variant else ""
    return (
        f"<div class='prasad-summary-insight{variant_class}'>"
        f"<span class='prasad-summary-insight-label'>{label}</span>"
        f"<div class='prasad-summary-insight-value'>{value}</div>"
        "</div>"
    )


def get_prasad_slot_status(seva_date, pooja_time, now_cst):
    if seva_date < now_cst.date():
        return "completed"
    if seva_date > now_cst.date():
        return "upcoming"
    pooja_time = str(pooja_time).lower()
    if "morning" in pooja_time:
        return "current" if now_cst.time() < dttime(15, 0) else "completed"
    if "evening" in pooja_time:
        return "current" if now_cst.time() >= dttime(15, 0) else "upcoming"
    return "upcoming"


def get_prasad_slot_sort_key(slot):
    seva_date, pooja_time = slot
    pooja_order = 0 if "morning" in str(pooja_time).lower() else 1
    return seva_date, pooja_order


def normalize_prasad_name_group(name):
    name = " ".join(str(name or "").split())
    return re.sub(r"\s*(?:&|,|\band\b)\s*", " and ", name, flags=re.IGNORECASE).casefold()


def display_prasad_name_group(name):
    name = " ".join(str(name or "").split())
    return re.sub(r"\s*(?:&|,|\band\b)\s*", " & ", name, flags=re.IGNORECASE)


def prasad_seva_tab():
    laddu_winners_option = "Laddu Auction Winners"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT laddu_number, winner_name, amount FROM laddu_winners ORDER BY laddu_number ASC LIMIT 3")
    laddu_winners = [
        {"laddu": row[0], "name": row[1], "amount": row[2]} for row in cursor.fetchall()
    ]
    is_admin = st.session_state.get("admin_logged_in", False)
    # Define tab_names for all users by default
    tab_names = [
        "Prasad Seva",
        "Stats",
        laddu_winners_option,
    ]
    if st.session_state.get("prasad_tab") in ("Prasad Seva Stats", "Prasad Seva Summary", "Total Served by Name/Group"):
        st.session_state["prasad_tab"] = "Stats"
    if "prasad_tab" not in st.session_state or st.session_state["prasad_tab"] not in tab_names:
        st.session_state["prasad_tab"] = "Prasad Seva"
    selected_tab = option_menu(
        "Prasad Seva Management",
        tab_names,
        icons=["plus-circle", "trophy", "pencil-square", "bar-chart", "people", "person-lines-fill"][:len(tab_names)],
        menu_icon="gift",
        default_index=tab_names.index(st.session_state["prasad_tab"]),
        orientation="horizontal",
        key="prasad_seva_management_menu_v2",
        styles={
            "container": {
                "padding": "0.5rem 0.75rem",
                "background": "linear-gradient(135deg, #ffffff 0%, #fffaf0 100%)",
                "border": "1.5px solid #e4ddd7",
                "border-radius": "16px",
                "box-shadow": "0 4px 16px rgba(80, 38, 28, 0.1)",
                "margin-bottom": "1.4rem",
            },
            "icon": {"color": "#8b1737", "font-size": "1rem"},
            "nav-link": {
                "font-size": "0.82rem",
                "font-weight": "600",
                "text-align": "center",
                "margin": "0 4px",
                "padding": "0.55rem 0.85rem",
                "border-radius": "12px",
                "color": "#5d4037",
                "--hover-color": "#f5efe6",
            },
            "nav-link-selected": {
                "background": "linear-gradient(135deg, #6a1b1b 0%, #8b1737 100%)",
                "color": "#ffffff",
                "font-weight": "700",
                "box-shadow": "0 4px 12px rgba(106, 27, 27, 0.3)",
            },
            "menu-title": {"color": "#5d4037", "font-weight": "800", "font-size": "0.95rem", "margin-right": "1rem"},
        },
    )
    st.session_state["prasad_tab"] = selected_tab

    if selected_tab == laddu_winners_option:
        st.markdown(
            """
            <div style='max-width:520px;margin:0 auto 18px auto;background:#FFFDE7;border-radius:18px;box-shadow:0 2px 12px #FFD18033;padding:28px 18px;'>
                <div style='font-size:1.15em;font-weight:600;color:#BF360C;text-align:center;margin-bottom:12px;'>
                    Welcome to Ganesh Celebrations 2026! We are delighted to celebrate another year together with our wonderful community.<br>
                    Thank you for your continued support, enthusiasm, and teamwork in making these celebrations special.<br>
                    Please see below the Laddu Auction winners from our memorable 2025 celebrations.<br>
                    Congratulations to all who took part, and special wishes to the winners!
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        # Winners Table
        # Improved table design: Rank, Winner(s), Amount (admin only)
        table_html = """
        <style>
        .laddu-table { width:100%; border-collapse:separate; border-spacing:0 8px; margin-top:10px; }
        .laddu-table th { background:#FFD180; color:#6D4C41; font-weight:700; padding:10px 16px; border-radius:8px 8px 0 0; font-size:1.08em; }
        .laddu-table td { background:#FFFDE7; padding:10px 16px; border-radius:0 0 8px 8px; font-size:1.05em; }
        .laddu-rank { font-weight:700; color:#D84315; text-align:center; }
        .laddu-winner { font-weight:500; color:#4E342E; }
        .laddu-amount { font-weight:700; color:#388E3C; text-align:right; }
        </style>
        <table class='laddu-table'>
            <tr>
                <th>Laddu</th>
                <th>Winner(s)</th>
"""
        table_html += "                <th>Amount</th>\n"
        table_html += "            </tr>\n"
        for winner in laddu_winners:
            table_html += "            <tr>\n"
            table_html += f"                <td class='laddu-rank'>{winner['laddu']}</td>\n"
            table_html += f"                <td class='laddu-winner'>{winner['name']}</td>\n"
            table_html += f"                <td class='laddu-amount'>{winner['amount']}</td>\n"
            table_html += "            </tr>\n"
        table_html += "        </table>\n"
        st.markdown(table_html, unsafe_allow_html=True)
        return
    # --- Clear Add Prasad Seva form fields if needed ---
    if st.session_state.get("clear_prasad_form", False):
        st.session_state["prasad_individual_name"] = ""
        st.session_state["prasad_num_people"] = 1
        today_cst = dt.now(pytz.timezone("US/Central")).date()
        st.session_state["prasad_seva_date"] = today_cst
        st.session_state["prasad_pooja_time"] = "Evening Pooja"
        st.session_state["prasad_filter_date"] = None
        st.session_state["prasad_filter_name"] = ""
        st.session_state["clear_prasad_form"] = False
        st.session_state["prasad_inline_action"] = "view"
        st.rerun()

    st.markdown(
        """
        <style>
        .st-key-prasad_action_row [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-wrap: nowrap !important;
            gap: 0.45rem;
        }
        .st-key-prasad_action_row [data-testid="stHorizontalBlock"] > div {
            flex: 1 1 0 !important;
            min-width: 0 !important;
        }
        div[data-testid="stButton"] > button {
            width: 100%;
            border-radius: 14px;
            border: 1px solid #d7a95a;
            background: linear-gradient(135deg, #fffaf0 0%, #f5d7a2 100%);
            color: #4a2d1b;
            font-weight: 700;
            font-size: 0.96rem;
            padding: 0.72rem 0.9rem;
            box-shadow: 0 8px 18px rgba(120, 76, 31, 0.18);
            transition: all 0.2s ease;
        }
        div[data-testid="stButton"] > button:hover {
            border-color: #b87d36;
            background: linear-gradient(135deg, #fffdf9 0%, #f7e0b4 100%);
            box-shadow: 0 10px 22px rgba(120, 76, 31, 0.22);
        }
        div[data-testid="stButton"] > button:focus {
            box-shadow: 0 0 0 0.2rem rgba(184, 122, 56, 0.25);
        }
        @media (max-width: 640px) {
            .st-key-prasad_action_row [data-testid="stHorizontalBlock"] {
                flex-wrap: nowrap !important;
            }
            .st-key-prasad_action_row [data-testid="stHorizontalBlock"] > div {
                flex: 1 1 33.33% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if selected_tab == "Prasad Seva":
        st.markdown(
            """
            <div style='background: linear-gradient(135deg, #fff9f0 0%, #fce7cc 100%); border: 1px solid #d7a35a; border-radius: 14px; padding: 0.9rem 1rem; margin-bottom: 1rem; box-shadow: 0 4px 14px rgba(154, 96, 22, 0.12);'>
                <div style='font-size:1rem; font-weight:800; color:#7a3d12; margin-bottom:0.35rem;'>🙏 Prasad Preparation Note</div>
                <div style='font-size:0.95rem; color:#4d2c18; line-height:1.5;'>Kindly prepare the Prasad without garlic and onion.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.container(key="prasad_action_row"):
        if selected_tab == "Prasad Seva":
            action_columns = st.columns(3)
            with action_columns[0]:
                if st.button("Add", key="prasad_inline_add_button", use_container_width=True):
                    st.session_state["prasad_inline_action"] = "view" if st.session_state.get("prasad_inline_action") == "add" else "add"
                    st.rerun()
            with action_columns[1]:
                if st.button("Edit", key="prasad_inline_edit_button", use_container_width=True):
                    st.session_state["prasad_inline_action"] = "view" if st.session_state.get("prasad_inline_action") == "edit" else "edit"
                    st.rerun()
            with action_columns[2]:
                if st.button("Delete", key="prasad_inline_delete_button", use_container_width=True):
                    st.session_state["prasad_inline_action"] = "view" if st.session_state.get("prasad_inline_action") == "delete" else "delete"
                    st.rerun()

    if selected_tab == "Prasad Seva" and st.session_state.get("prasad_inline_action") == "add":
        st.markdown(
            """
            <style>
            div[data-testid="stForm"] .stBaseButton button {
                border-radius: 12px;
            }
            div[data-testid="stRadio"] > div {
                gap: 0.6rem;
            }
            div[data-testid="stRadio"] label {
                background: #ffffff;
                border: 1px solid #d9c6d7;
                border-radius: 12px;
                padding: 0.55rem 0.85rem;
                margin: 0.1rem 0;
                color: #3f2d3d;
            }
            div[data-testid="stRadio"] > div[role="radiogroup"] {
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
            }
            button[kind="primary"] {
                background: linear-gradient(135deg, #2a5c7a 0%, #3d7e9b 100%);
                border: none;
                border-radius: 12px;
                font-weight: 700;
                box-shadow: 0 8px 18px rgba(42, 92, 122, 0.18);
            }
            .stDateInput > div > div,
            .stTextInput > div > div,
            .stTextArea > div > div,
            .stNumberInput > div > div {
                background: #fffdfd;
                border-radius: 12px;
                border: 1px solid #d6c5d2;
            }
            .stDateInput [data-testid="stWidgetLabel"],
            .stTextInput [data-testid="stWidgetLabel"],
            .stTextArea [data-testid="stWidgetLabel"],
            .stNumberInput [data-testid="stWidgetLabel"],
            .stRadio [data-testid="stWidgetLabel"] {
                font-size: 1rem;
                font-weight: 700;
                color: #3e2b3d;
            }
            .stRadio > div:nth-child(2) {
                background: #f4eef3;
                border: 1px solid #dbc9d8;
                border-radius: 14px;
                padding: 0.35rem 0.4rem;
            }
            .stRadio > div:nth-child(2) > div {
                display: flex !important;
                flex-direction: row !important;
                align-items: center;
                gap: 0.7rem;
            }
            .stRadio > div:nth-child(2) label {
                min-width: 150px;
            }
            .pooja-time-card {
                background: #fff9f5;
                border: 1px solid #e3ced5;
                border-radius: 14px;
                padding: 0.7rem 0.8rem 0.55rem 0.8rem;
                margin-top: 0.1rem;
                margin-bottom: 0.75rem;
            }
            .pooja-time-label {
                font-size: 1rem;
                font-weight: 700;
                color: #3e2b3d;
                margin-bottom: 0.45rem;
                display: block;
            }
            .pooja-time-card .stCheckbox {
                margin-top: 0.15rem;
                margin-bottom: 0.15rem;
            }
            .selected-day-banner {
                display: flex;
                align-items: baseline;
                gap: 0.5rem;
                background: linear-gradient(135deg, #fff7e8 0%, #fff1d2 100%);
                border: 1px solid #e7c27d;
                border-left: 4px solid #c9872f;
                border-radius: 10px;
                color: #5f3a1d;
                padding: 0.6rem 0.75rem;
                margin: 0.15rem 0 0.8rem;
            }
            .selected-day-kicker {
                color: #8a5b2a;
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.02em;
                text-transform: none !important;
            }
            .selected-day-banner strong {
                font-size: 1rem;
            }
            .st-key-prasad_pooja_time_row [data-testid="stHorizontalBlock"] {
                display: grid !important;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.5rem;
            }
            .st-key-prasad_pooja_time_row [data-testid="column"] {
                min-width: 0 !important;
                width: auto !important;
                box-sizing: border-box;
                background: #fffdf9;
                border: 1px solid #e3ced5;
                border-radius: 11px;
                padding: 0.2rem 0.4rem 0.1rem;
            }
            .st-key-prasad_pooja_time_row .stCheckbox {
                margin: 0;
            }
            .st-key-prasad_pooja_time_row .stCheckbox label {
                color: #3f2d3d;
                font-weight: 600;
                white-space: nowrap;
            }
            [data-testid="stHorizontalBlock"] {
                gap: 0.75rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        today_cst = dt.now(pytz.timezone("US/Central")).date()
        selected_date = st.session_state.get("prasad_seva_date", today_cst)
        if selected_date < today_cst:
            selected_date = today_cst
            st.session_state["prasad_seva_date"] = selected_date

        def reset_prasad_pooja_selection():
            st.session_state["prasad_pooja_times"] = []
            for option in ("Morning Pooja", "Evening Pooja"):
                st.session_state[f"prasad_pooja_checkbox_{option}"] = False

        seva_date = st.date_input(
            "Date",
            value=selected_date,
            min_value=today_cst,
            key="prasad_seva_date",
            on_change=reset_prasad_pooja_selection,
        )

        prasad_form = st.form("add_prasad_seva_form")
        prasad_submit_disabled = st.session_state.get("prasad_submission_in_progress", False)
        seva_type = "Individual"
        prasad_form.markdown(
            f"<div class='selected-day-banner'><span class='selected-day-kicker' style='text-transform:none !important;'>Selected Seva Day</span><strong>{seva_date.strftime('%A')}</strong></div>",
            unsafe_allow_html=True,
        )
        prasad_form.markdown("<div class='pooja-time-label'>Pooja Time</div>", unsafe_allow_html=True)

        pooja_container = prasad_form.container(key="prasad_pooja_time_row")
        with pooja_container:
            pooja_options = get_available_prasad_pooja_options(seva_date, dt.now(pytz.timezone("US/Central")))
            selected_poojas = []
            pooja_checkbox_columns = pooja_container.columns(2 if len(pooja_options) > 1 else 1, gap="small")
            for index, option in enumerate(pooja_options):
                display_option = {
                    "Morning Pooja": "Morning",
                    "Evening Pooja": "Evening",
                }.get(option, option)
                default_value = option == "Evening Pooja" and seva_date == datetime.date(2026, 9, 14)
                if option in st.session_state.get("prasad_pooja_times", []):
                    default_value = True
                with pooja_checkbox_columns[index]:
                    is_checked = st.checkbox(
                        display_option,
                        value=default_value,
                        key=f"prasad_pooja_checkbox_{option}",
                    )
                if is_checked:
                    selected_poojas.append(option)
            st.session_state["prasad_pooja_times"] = selected_poojas
            pooja_time = ", ".join(selected_poojas)

        name = prasad_form.text_input("Name", key="prasad_individual_name", placeholder="e.g. Full Name")
        names = [name.strip()] if name.strip() else []
        item_name = prasad_form.text_input("Item Name", placeholder="e.g. Modak")
        item_names = [item_name.strip()] if item_name.strip() else []

        num_people = prasad_form.number_input("Serving count", min_value=1, value=st.session_state.get('prasad_num_people', 1), key="prasad_num_people")

        if prasad_form.form_submit_button("Add Prasad Seva", disabled=prasad_submit_disabled, type="primary"):
            st.session_state["prasad_submission_in_progress"] = True
            if not names:
                st.session_state["prasad_submission_in_progress"] = False
                prasad_form.error("Please enter at least one name.")
            elif not item_names:
                st.session_state["prasad_submission_in_progress"] = False
                prasad_form.error("Please enter at least one item name.")
            elif num_people < 1:
                st.session_state["prasad_submission_in_progress"] = False
                prasad_form.error("Serving count must be at least 1.")
            elif not seva_date:
                st.session_state["prasad_submission_in_progress"] = False
                prasad_form.error("Date is required.")
            elif seva_date < today_cst:
                st.session_state["prasad_submission_in_progress"] = False
                prasad_form.error("Past dates cannot be added. Please select today or a future date.")
            elif not pooja_time:
                st.session_state["prasad_submission_in_progress"] = False
                prasad_form.error("Please select at least one Pooja Time.")
            else:
                st.info("Add Prasad Seva is in progress...")
                for item in item_names:
                    if hasattr(cursor, 'execute') and hasattr(cursor.connection, 'account'):
                        cursor.execute(
                            "INSERT INTO prasad_seva (seva_type, names, item_name, num_people, apartment, seva_date, pooja_time, created_by, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (seva_type, ', '.join(names), item, num_people, None, seva_date, pooja_time, st.session_state.get('admin_full_name', 'User'), 'active')
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO prasad_seva (seva_type, names, item_name, num_people, apartment, seva_date, pooja_time, created_by, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (seva_type, ', '.join(names), item, num_people, None, seva_date, pooja_time, st.session_state.get('admin_full_name', 'User'), 'active')
                        )
                conn.commit()
                submitted_info = {
                    "Names": ', '.join(names),
                    "Item Name(s)": ', '.join(item_names),
                    "Number of People": num_people,
                    "Date": seva_date.strftime('%d-%b-%Y'),
                    "Pooja Time": pooja_time
                }
                st.session_state["prasad_last_submission"] = submitted_info
                st.session_state["prasad_submission_in_progress"] = False
                st.success("✅ Added seva successfully")
                st.session_state["clear_prasad_form"] = True
                st.rerun()

    elif selected_tab == "Stats":
        cursor.execute("SELECT seva_date, pooja_time, SUM(num_people) FROM prasad_seva WHERE status='active' GROUP BY seva_date, pooja_time")
        metrics_rows = cursor.fetchall()
        min_date = datetime.date(2026, 9, 14)
        max_date = datetime.date(2026, 9, 20)
        all_dates = pd.date_range(min_date, max_date).date
        grid = pd.DataFrame(
            [(d, p) for d in all_dates for p in get_pooja_options_for_date(d)],
            columns=["Date", "Pooja Time"],
        )
        metrics_df = pd.DataFrame(metrics_rows, columns=["Date", "Pooja Time", "Total People Served"])
        metrics_df["Date"] = pd.to_datetime(metrics_df["Date"]).dt.date
        merged_df = grid.merge(metrics_df, on=["Date", "Pooja Time"], how="left").fillna({"Total People Served": 0})
        merged_df["Total People Served"] = merged_df["Total People Served"].astype(int)
        active_slots = int((merged_df["Total People Served"] > 0).sum())
        zero_slots = merged_df[merged_df["Total People Served"] == 0]

        def format_slot_list(slots):
            if slots.empty:
                return "None"
            return "<br>".join(
                f"{pd.to_datetime(row['Date']).strftime('%d-%b')} · {row['Pooja Time']}"
                for _, row in slots.iterrows()
            )

        zero_slot_text = format_slot_list(zero_slots)
        total_sponsored = int(merged_df["Total People Served"].sum())
        cursor.execute(
            "SELECT names, seva_date, pooja_time FROM prasad_seva "
            "WHERE status='active' AND NOT (seva_date = '2026-09-20' AND pooja_time = 'Evening Pooja')"
        )
        participant_rows = cursor.fetchall()
        participant_groups = {
            (normalize_prasad_name_group(name), seva_date, pooja_time)
            for name, seva_date, pooja_time in participant_rows
            if normalize_prasad_name_group(name)
        }
        total_members = len({group[0] for group in participant_groups})
        members_by_slot = {}
        for normalized_name, seva_date, pooja_time in participant_groups:
            slot_key = (seva_date, pooja_time)
            members_by_slot.setdefault(slot_key, set()).add(normalized_name)
        now_cst = dt.now(pytz.timezone("US/Central"))
        slot_service_totals = {
            (row["Date"], row["Pooja Time"]): row["Total People Served"]
            for _, row in merged_df.iterrows()
        }
        served_labels = {
            "completed": "servings served",
            "current": "servings in progress",
            "upcoming": "servings expected",
        }
        slot_member_text = "<br>".join(
            f"<span class='prasad-slot-{status}'>"
            f"<b>{seva_date.strftime('%d-%b')} · {pooja_time.replace(' Pooja', '')}</b>"
            f" &nbsp; {len(names)} members · {slot_service_totals.get((seva_date, pooja_time), 0)} {served_labels[status]}"
            "</span>"
            for (seva_date, pooja_time), names in sorted(
                members_by_slot.items(), key=lambda item: get_prasad_slot_sort_key(item[0])
            )
            for status in [get_prasad_slot_status(seva_date, pooja_time, now_cst)]
        ) or "None"
        summary_insights = "".join(
            (
                format_prasad_summary_insight("No service yet", zero_slot_text, "warning"),
                format_prasad_summary_insight("Participation by slot", slot_member_text),
            )
        )
        st.markdown(
            """
            <style>
            .prasad-summary {
                margin: 0.25rem auto 1rem;
                padding: 1.15rem 1.25rem 1.25rem;
                border: 1px solid #d7e5d2;
                border-radius: 20px;
                background: linear-gradient(135deg, #f4fbf0 0%, #fffaf0 100%);
                box-shadow: 0 10px 24px rgba(71, 96, 55, 0.1);
            }
            .prasad-summary-kicker {
                color: #7a4b22;
                font-size: 0.75rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }
            .prasad-summary-title {
                margin: 0.2rem 0 0.35rem;
                color: #254d35;
                font-family: Georgia, serif;
                font-size: 1.55rem;
                font-weight: 700;
            }
            .prasad-summary-copy {
                margin: 0;
                color: #5d6e5b;
                font-size: 0.9rem;
            }
            .prasad-summary-metrics {
                display: flex;
                gap: 0.6rem;
                margin-top: 1rem;
            }
            .prasad-summary-metric {
                flex: 1;
                min-width: 0;
                padding: 0.65rem 0.8rem;
                border: 1px solid rgba(126, 160, 111, 0.28);
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.72);
            }
            .prasad-summary-metric-label {
                color: #6e7f6b;
                font-size: 0.72rem;
                font-weight: 700;
            }
            .prasad-summary-metric-value {
                display: block;
                margin-top: 0.15rem;
                color: #2e7d32;
                font-size: 1.2rem;
                font-weight: 800;
            }
            .prasad-summary-insights {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.6rem;
                margin-top: 0.7rem;
            }
            .prasad-summary-insight {
                min-height: 4.5rem;
                padding: 0.65rem 0.75rem;
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(126, 160, 111, 0.28);
            }
            .prasad-summary-insight-label {
                display: block;
                margin-bottom: 0.25rem;
                color: #6e7f6b;
                font-size: 0.7rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.04em;
            }
            .prasad-summary-insight-value {
                color: #405344;
                font-size: 0.78rem;
                font-weight: 700;
                line-height: 1.45;
            }
            .prasad-summary-insight.warning { border-color: #f0d59d; background: #fffaf0; }
            .prasad-summary-insight.warning .prasad-summary-insight-label { color: #a86b1f; }
            .prasad-summary-insight.demand { border-color: #e9c2b5; background: #fff7f3; }
            .prasad-summary-insight.demand .prasad-summary-insight-label { color: #b14f32; }
            .prasad-slot-completed { color: #6f625b; }
            .prasad-slot-current { color: #176b3a; background: #edf8ee; }
            .prasad-slot-upcoming { color: #9a5a13; background: #fff8e7; }
            .prasad-summary-table-wrap {
                overflow: hidden;
                border: 1px solid #dfe9df;
                border-radius: 16px;
                background: #ffffff;
                box-shadow: 0 8px 20px rgba(62, 84, 59, 0.08);
            }
            .prasad-summary-table {
                width: 100%;
                border-collapse: collapse;
                color: #26382a;
                font-size: 0.92rem;
            }
            .prasad-summary-table th {
                padding: 0.72rem 0.65rem;
                background: #315c3c;
                color: #ffffff;
                font-size: 0.78rem;
                font-weight: 800;
                letter-spacing: 0.02em;
                text-align: left;
            }
            .prasad-summary-table td {
                padding: 0.72rem 0.65rem;
                border-bottom: 1px solid #e7eee5;
                vertical-align: middle;
            }
            .prasad-summary-table tbody tr:nth-child(even) td { background: #f8fbf7; }
            .prasad-summary-table tbody tr:hover td { background: #fff8e6; }
            .prasad-summary-table tbody tr:last-child td { border-bottom: 0; }
            .prasad-summary-table th:first-child,
            .prasad-summary-table td:first-child { width: 38%; }
            .prasad-summary-table th:nth-child(2),
            .prasad-summary-table td:nth-child(2) { width: 37%; }
            .prasad-summary-table th:last-child,
            .prasad-summary-table td:last-child { width: 25%; }
            @media (max-width: 640px) {
                .prasad-summary { padding: 1rem 0.85rem; border-radius: 16px; }
                .prasad-summary-title { font-size: 1.3rem; }
                .prasad-summary-copy { font-size: 0.82rem; }
                .prasad-summary-insights { grid-template-columns: 1fr; }
                .prasad-summary-insight { min-height: auto; }
                .prasad-summary-table { font-size: 0.82rem; }
                .prasad-summary-table th, .prasad-summary-table td { padding: 0.62rem 0.45rem; }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        merged_df["Date"] = merged_df["Date"].apply(lambda d: f"<span style='font-size:16px;'>&#128197;</span> <b>{pd.to_datetime(d).strftime('%d-%b-%Y')}</b>")
        merged_df["Total People Served"] = merged_df["Total People Served"].apply(lambda x: f"<span style='background-color:#FFECB3;color:#6D4C41;padding:4px 12px;border-radius:16px;font-weight:bold;display:inline-block;text-align:center;'>{x}</span>")
        st.markdown(
            f"""
            <section class='prasad-summary'>
                <div class='prasad-summary-metrics'>
                    <div class='prasad-summary-metric'>
                        <span class='prasad-summary-metric-label'>People served</span>
                        <strong class='prasad-summary-metric-value'>{total_sponsored}</strong>
                    </div>
                    <div class='prasad-summary-metric'>
                        <span class='prasad-summary-metric-label'>Active pooja slots</span>
                        <strong class='prasad-summary-metric-value'>{active_slots}</strong>
                    </div>
                    <div class='prasad-summary-metric'>
                        <span class='prasad-summary-metric-label'>Participating members</span>
                        <strong class='prasad-summary-metric-value'>{total_members}</strong>
                    </div>
                </div>
                <div class='prasad-summary-insights'>
                    {summary_insights}
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        raw_metrics_df = merged_df.copy()
        raw_metrics_df["Date"] = pd.to_datetime(raw_metrics_df["Date"].str.extract(r'<b>(.*?)</b>')[0], format='%d-%b-%Y')
        raw_metrics_df["Pooja Time"] = raw_metrics_df["Pooja Time"].str.extract(r'<b>(.*?)</b>')[0]
        raw_metrics_df["Total People Served"] = raw_metrics_df["Total People Served"].str.extract(r'>(\d+)<')[0].fillna(0).astype(int)
        raw_metrics_df.to_csv(index=False)

        cursor.execute("SELECT names, SUM(num_people) as total_served FROM prasad_seva WHERE status='active' AND NOT (seva_date = '2026-09-20' AND pooja_time = 'Evening Pooja') GROUP BY names ORDER BY names")
        name_rows = cursor.fetchall()
        grouped_name_totals = {}
        grouped_name_labels = {}
        for name, total_served in name_rows:
            normalized_name = normalize_prasad_name_group(name)
            grouped_name_totals[normalized_name] = grouped_name_totals.get(normalized_name, 0) + total_served
            grouped_name_labels.setdefault(normalized_name, display_prasad_name_group(name))
        name_rows = sorted(
            [
                (grouped_name_labels[normalized_name], total_served)
                for normalized_name, total_served in grouped_name_totals.items()
            ],
            key=lambda row: row[0].casefold(),
        )
        st.markdown(
            """
            <style>
            .prasad-group-section {
                margin-top: 0.6rem;
                padding-top: 0;
            }
            .prasad-group-table {
                width: 100%;
                border-collapse: collapse;
                color: #493b30;
                font-size: 0.8rem;
            }
            .prasad-group-table th {
                padding: 0.35rem 0.45rem;
                color: #8a5a2b;
                font-size: 0.68rem;
                text-align: left;
                text-transform: uppercase;
                letter-spacing: 0.04em;
            }
            .prasad-group-table td {
                padding: 0.35rem 0.45rem;
                border-top: 1px solid #f0e5d7;
                line-height: 1.15;
            }
            .prasad-group-table tbody tr:hover td { background: #fff4dd; }
            .prasad-group-table th:first-child,
            .prasad-group-table td:first-child { width: 7%; text-align: center; color: #b06b2b; font-weight: 800; }
            .prasad-group-table th:last-child,
            .prasad-group-table td:last-child { width: 30%; text-align: right; }
            @media (max-width: 640px) {
                .prasad-group-table { font-size: 0.74rem; }
                .prasad-group-table th, .prasad-group-table td { padding: 0.3rem 0.25rem; }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <section class='prasad-group-section'>
            """,
            unsafe_allow_html=True,
        )
        if name_rows:
            name_df = pd.DataFrame(name_rows, columns=["Name", "People Served"])
            name_df.insert(0, "#", range(1, len(name_df) + 1))
            name_df["Name"] = name_df["Name"].apply(
                lambda name: f"<b>{name}</b>" if name else ""
            )
            name_df["People Served"] = name_df["People Served"].apply(
                lambda count: f"<span style='background:#ffe7ad;color:#76501e;padding:2px 7px;border-radius:8px;font-weight:800;display:inline-block;'>{count}</span>"
            )
            group_table_html = name_df.to_html(
                escape=False, index=False, justify="left", classes="prasad-group-table"
            )
            st.markdown(group_table_html, unsafe_allow_html=True)
        else:
            st.info("No Prasad Seva entries yet.")
        st.markdown("</section>", unsafe_allow_html=True)

    elif selected_tab == "Prasad Seva" and st.session_state.get("prasad_inline_action") not in ("edit", "delete"):
        query = "SELECT id, seva_type, names, item_name, num_people, apartment, seva_date, pooja_time, created_by, status FROM prasad_seva WHERE status='active' AND NOT (seva_date = '2026-09-20' AND pooja_time = 'Evening Pooja')"
        query += " ORDER BY seva_date, CASE WHEN pooja_time='Morning Pooja' THEN 0 ELSE 1 END, names, id"
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows and len(rows) > 0:
            df = pd.DataFrame(rows, columns=["ID", "Type", "Names", "Item Name", "Serving count", "Apartemnt Number", "Date", "Pooja Time", "Created By", "Status"])
            if "Status" in df.columns:
                df = df.drop(columns=["Status"])
            # Split into active and past based on CST date
            cst = pytz.timezone('US/Central')
            now_cst = dt.now(cst)
            today_cst = now_cst.date()
            df_active = df[pd.to_datetime(df["Date"]).dt.date >= today_cst]
            df_active = df_active[
                df_active.apply(
                    lambda row: is_prasad_seva_visible_in_table(row["Date"], row["Pooja Time"], now_cst),
                    axis=1,
                )
            ]
            df_past = df[
                df.apply(
                    lambda row: is_prasad_seva_in_past_table(row["Date"], row["Pooja Time"], now_cst),
                    axis=1,
                )
            ]
            selected_table_view = st.session_state.get("prasad_table_view", "Active")
            if selected_table_view not in ("Active", "Past"):
                selected_table_view = "Active"
            for df_tab, label in [(df_active, "Active"), (df_past, "Past")]:
                if label != selected_table_view:
                    continue
                toolbar_key = f"prasad-sponsor-toolbar-{label.lower()}"
                st.markdown(
                    textwrap.dedent(f"""
                    <style>
                    .st-key-prasad_view_active button,
                    .st-key-prasad_view_past button {{
                        width: 100%;
                        border-radius: 8px !important;
                        font-size: 0.8rem !important;
                        font-weight: 700 !important;
                        white-space: nowrap !important;
                    }}
                    .st-key-prasad_view_active button {{
                        border: 1px solid #2e7d32 !important;
                        background: #f1f8e9 !important;
                        color: #2e7d32 !important;
                    }}
                    .st-key-prasad_view_past button {{
                        border: 1px solid #a86b1f !important;
                        background: #fff8e7 !important;
                        color: #8a5a2b !important;
                    }}
                    .st-key-prasad_view_active button[kind="primary"] {{
                        background: linear-gradient(135deg, #2e7d32, #43a047) !important;
                        color: #ffffff !important;
                    }}
                    .st-key-prasad_view_past button[kind="primary"] {{
                        background: linear-gradient(135deg, #a86b1f, #c8872f) !important;
                        color: #ffffff !important;
                    }}
                    .st-key-prasad-filter button {{
                        width: 100%;
                        border: 1px solid #8b1737 !important;
                        border-radius: 8px !important;
                        background: #fff7f7 !important;
                        color: #8b1737 !important;
                        font-weight: 700 !important;
                    }}
                    @media (max-width: 640px) {{
                        .st-key-{toolbar_key} [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; }}
                        .st-key-{toolbar_key} [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
                            min-width: 0 !important;
                        }}
                    }}
                    </style>
                    """),
                    unsafe_allow_html=True,
                )
                with st.container(key=toolbar_key):
                    active_column, past_column, _, search_column = st.columns([1.8, 1.8, 5.2, 1.8])
                    with active_column:
                        if st.button(
                            "Active",
                            key="prasad_view_active",
                            type="primary" if selected_table_view == "Active" else "secondary",
                            use_container_width=True,
                        ) and selected_table_view != "Active":
                            st.session_state["prasad_table_view"] = "Active"
                            st.rerun()
                    with past_column:
                        if st.button(
                            "Past",
                            key="prasad_view_past",
                            type="primary" if selected_table_view == "Past" else "secondary",
                            use_container_width=True,
                        ) and selected_table_view != "Past":
                            st.session_state["prasad_table_view"] = "Past"
                            st.rerun()
                    with search_column:
                        with st.popover("Filter 🔍", help="Search sponsors", use_container_width=True):
                            filter_name = st.text_input(
                                "Name", value="", key=f"prasad_filter_name_{label.lower()}"
                            )
                            filter_date = st.date_input(
                                "Date", value=None, min_value=today_cst, key=f"prasad_filter_date_{label.lower()}"
                            )
                            filter_pooja_time = st.selectbox(
                                "Pooja Time",
                                ["All", "Morning Pooja", "Evening Pooja", "Evening Pooja for Kids"],
                                key=f"prasad_filter_pooja_time_{label.lower()}",
                            )
                    filtered_df_tab = df_tab
                    if filter_name:
                        filtered_df_tab = filtered_df_tab[
                            filtered_df_tab["Names"].str.contains(filter_name, case=False, na=False)
                        ]
                    if filter_date:
                        filtered_df_tab = filtered_df_tab[
                            pd.to_datetime(filtered_df_tab["Date"]).dt.date == filter_date
                        ]
                    if filter_pooja_time != "All":
                        filtered_df_tab = filtered_df_tab[filtered_df_tab["Pooja Time"] == filter_pooja_time]
                    if len(filtered_df_tab) > 0:
                        df_display = filtered_df_tab.drop(columns=["ID", "Created By"])
                        df_display = df_display.drop(columns=["Apartemnt Number"], errors="ignore")
                        df_display["Date"] = df_display["Date"].apply(lambda d: f"<b>{pd.to_datetime(d).strftime('%d-%b-%Y')}</b>")
                        def pooja_time_display(row):
                            return f"<b>{row['Pooja Time'].replace('Pooja', '')}</b>"
                        df_display["Pooja Time"] = df_display.apply(pooja_time_display, axis=1)
                        df_display["Names"] = df_display.apply(
                            lambda r: f"<b>{r['Names']}</b>" if r["Names"] else "",
                            axis=1,
                        )
                        df_display = df_display.drop(columns=["Type"])
                        df_display["Item Name"] = df_display["Item Name"].apply(lambda item: f"<b>{item}</b>" if item else "")
                        df_display["Serving count"] = df_display["Serving count"].apply(lambda x: f"<span style='background-color:#FFECB3;color:#6D4C41;padding:4px 12px;border-radius:16px;font-weight:bold;display:inline-block;text-align:center;'>{x}</span>")
                        # Sort by Date, Pooja Time (morning before evening), then Name
                        df_display["_date_sort"] = pd.to_datetime(filtered_df_tab["Date"])
                        df_display["_pooja_sort"] = filtered_df_tab["Pooja Time"].apply(lambda x: 0 if str(x).lower().find("morning") != -1 else 1)
                        df_display = df_display.sort_values(by=["_date_sort", "_pooja_sort", "Names"])
                        df_display = df_display.drop(columns=["_date_sort", "_pooja_sort"])
                        df_display.index = range(1, len(df_display) + 1)
                        table_html = df_display.to_html(
                            escape=False, index=True, justify='center', classes="sponsor-table"
                        )
                        st.markdown(
                            f"{SPONSOR_TABLE_CSS}<div class='sponsor-table-wrap'>{table_html}</div>",
                            unsafe_allow_html=True,
                        )
                        if st.session_state.get('admin_logged_in', False):
                            if st.button(f"Send Prasad Seva Details to Email ({label})"):
                                cursor.execute("SELECT email FROM notification_emails")
                                notification_emails = [row[0] for row in cursor.fetchall() if row[0]]
                                html_table = filtered_df_tab.drop(columns=["ID", "Created By", "Apartemnt Number"], errors="ignore").to_html(index=False, border=1, justify='center')
                                send_email(
                                    f"Prasad Seva Sponsors List ({label})",
                                    f"<b>Current Prasad Seva List ({label})</b><br><br>{html_table}",
                                    notification_emails
                                )
                                st.success("✅ Email sent!")
                    else:
                        st.info(f"No {label} Prasad Seva entries match these filters.")
        else:
            st.info("No Prasad Seva entries yet.")

    if selected_tab == "Prasad Seva" and st.session_state.get("prasad_inline_action") in ("edit", "delete"):
        query = "SELECT id, seva_type, names, item_name, num_people, apartment, seva_date, pooja_time, created_by, status FROM prasad_seva WHERE status='active' AND NOT (seva_date = '2026-09-20' AND pooja_time = 'Evening Pooja') ORDER BY seva_date, pooja_time, id"
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows and len(rows) > 0:
            df = pd.DataFrame(rows, columns=["ID", "Type", "Names", "Item Name", "Serving count", "Apartemnt Number", "Date", "Pooja Time", "Created By", "Status"])
            if "Status" in df.columns:
                df = df.drop(columns=["Status"])
            def is_editable(row):
                entry_date = pd.to_datetime(row["Date"]).date()
                pooja_time = str(row["Pooja Time"]).strip().lower()
                cst = pytz.timezone('US/Central')
                now_cst = dt.now(cst)
                today_cst = now_cst.date()
                if entry_date > today_cst:
                    return True
                elif entry_date < today_cst:
                    return False
                else:
                    if "morning" in pooja_time:
                        return now_cst.time() < dttime(6, 0)
                    elif "evening" in pooja_time:
                        return now_cst.time() < dttime(17, 0)
                    else:
                        return False
            df = df[df.apply(is_editable, axis=1)]
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            df["_pooja_sort"] = df["Pooja Time"].apply(lambda x: 0 if str(x).lower().find("morning") != -1 else 1)
            df = df.sort_values(by=["Date", "_pooja_sort", "Names"]).drop(columns=["_pooja_sort"])
            options = ["Select an option"] + [
                f"{row['Names']} | {pd.to_datetime(row['Date']).strftime('%d-%b-%Y')} | {row['Pooja Time']}"
                for _, row in df.iterrows()
            ]
            selected_idx = st.selectbox("Choose an entry to Edit/Delete", range(len(options)), format_func=lambda i: options[i], key="edit_delete_selectbox")
            entry = None
            if selected_idx != 0:
                selected_id = df["ID"].tolist()[selected_idx-1]
                entry = df[df["ID"]==selected_id].iloc[0]
            if entry is not None:
                if st.session_state.get("prasad_inline_action") == "edit":
                    new_names = st.text_input("Names", value=str(entry["Names"]), key=f"edit_names_{selected_id}")
                    new_item = st.text_input("Item Name", value=entry["Item Name"], key=f"edit_item_{selected_id}")
                    new_num = st.number_input(
                        "Serving count",
                        min_value=1,
                        value=max(1, int(entry["Serving count"])),
                        key=f"edit_num_{selected_id}",
                    )
                    min_date = datetime.date(2026, 9, 14)
                    current_date = pd.to_datetime(entry["Date"]).date() if pd.notna(entry["Date"]) else min_date
                    new_date = st.date_input("Date", value=current_date, min_value=min_date, key=f"edit_prasad_date_{selected_id}")
                    pooja_options = get_available_prasad_pooja_options(new_date, dt.now(pytz.timezone("US/Central")))
                    if entry["Pooja Time"] in pooja_options:
                        pooja_index = pooja_options.index(entry["Pooja Time"])
                    else:
                        pooja_index = 0
                    new_pooja_time = st.radio("Pooja Time", pooja_options, index=pooja_index, key=f"edit_prasad_time_{selected_id}")
                    if st.button("Update Prasad Seva", key=f"update_prasad_{selected_id}"):
                        if new_num < 1:
                            st.warning("Serving count must be at least 1.")
                        else:
                            cursor.execute(
                                "UPDATE prasad_seva SET seva_type=%s, names=%s, item_name=%s, num_people=%s, seva_date=%s, pooja_time=%s, status=%s WHERE id=%s",
                                ("Individual", new_names.strip(), new_item, new_num, new_date, new_pooja_time, 'active', selected_id)
                            )
                            conn.commit()
                            st.session_state["prasad_inline_action"] = "view"
                            st.success("✅ Updated!")
                            st.rerun()
                elif st.session_state.get("prasad_inline_action") == "delete":
                    entered_name = st.text_input(f"Type the name to confirm deletion ({entry['Names']})", key=f"delete_name_{selected_id}")
                    confirm_message = f"Type <b>{entry['Names']}</b> above and click Delete to confirm."
                    st.markdown(confirm_message, unsafe_allow_html=True)
                    if st.button("Delete Prasad Seva", key=f"delete_prasad_{selected_id}"):
                        if entered_name.strip() == entry['Names']:
                            cursor.execute("UPDATE prasad_seva SET status='inactive' WHERE id=%s", (selected_id,))
                            conn.commit()
                            st.session_state.pop("edit_delete_selectbox", None)
                            st.session_state["prasad_inline_action"] = "view"
                            st.success("🗑️ Deleted!")
                            st.rerun()
                        else:
                            st.warning(f"Please type the exact name '{entry['Names']}' to confirm deletion.")
        else:
            st.info("No Prasad Seva entries available to edit or delete.")

    st.markdown("---")
