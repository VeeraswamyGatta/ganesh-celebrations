import streamlit as st

SEATING_CSS = '''
    <style>
    .seating-hero {
        display: flex;
        align-items: center;
        gap: 1rem;
        background: linear-gradient(135deg, #fff7e6 0%, #f7efe8 45%, #edf7f0 100%);
        border: 1px solid rgba(170, 125, 77, 0.3);
        border-radius: 22px;
        padding: 1.2rem 1.3rem;
        box-shadow: 0 16px 36px rgba(105, 76, 52, 0.12);
        margin-bottom: 1.2rem;
    }
    .seating-hero-icon {
        width: 62px;
        height: 62px;
        border-radius: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #d98a2f 0%, #bf6b18 100%);
        color: white;
        font-size: 1.8rem;
        box-shadow: inset 0 2px 10px rgba(255,255,255,0.2);
    }
    .seating-hero-text {
        flex: 1;
    }
    .seating-hero-title {
        font-size: 2rem;
        font-weight: 900;
        line-height: 1.1;
        color: #3a2a1b;
        letter-spacing: -0.03em;
    }
    .seating-hero-subtitle {
        margin-top: 0.35rem;
        color: #5c4f46;
        font-size: 0.97rem;
        line-height: 1.5;
    }
    .seating-hero-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin-top: 0.5rem;
    }
    .seating-legend-item {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.35rem 0.55rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.55);
        border: 1px solid rgba(128, 102, 80, 0.18);
        color: #56473d;
        font-size: 0.8rem;
        font-weight: 800;
    }
    .seating-legend-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.2rem;
        height: 1.2rem;
        border-radius: 50%;
        background: rgba(255,255,255,0.6);
    }
    .seating-day-card {
        background: linear-gradient(180deg, #fffefc 0%, #f7f1eb 100%);
        border: 1px solid rgba(167, 141, 123, 0.35);
        border-radius: 20px;
        padding: 1rem 1rem 0.9rem;
        margin: 0.85rem 0;
        box-shadow: 0 10px 24px rgba(126, 102, 82, 0.09);
    }
    .seating-day-header {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        padding-bottom: 0.8rem;
        border-bottom: 1px solid rgba(122, 98, 88, 0.2);
        margin-bottom: 0.8rem;
    }
    .seating-day-icon {
        width: 38px;
        height: 38px;
        border-radius: 12px;
        background: linear-gradient(135deg, #f6d08a 0%, #e7ae42 100%);
        color: #4d2f06;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        font-weight: 900;
    }
    .seating-day-title {
        font-size: 1.2rem;
        font-weight: 900;
        color: #7a4500;
        letter-spacing: 0.02em;
    }
    .seating-day-summary {
        display: flex;
        align-items: stretch;
        gap: 0.75rem;
        flex-wrap: wrap;
        margin-bottom: 0.6rem;
    }
    .seating-day-summary-box {
        display: flex;
        align-items: stretch;
        gap: 0.75rem;
        width: 100%;
        margin-bottom: 0.9rem;
        padding: 0.75rem;
        border-radius: 18px;
        background: linear-gradient(135deg, #f7f8e4 0%, #eef7ea 100%);
        border: 2px solid rgba(56, 142, 60, 0.7);
        box-shadow: 0 10px 20px rgba(76, 140, 92, 0.12);
    }
    .seating-date-chip {
        min-height: 56px;
        min-width: 150px;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.8rem 0.9rem;
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(255,255,255,0.28), rgba(255,255,255,0.12));
        border: 1px solid rgba(107, 74, 15, 0.18);
        color: #5c3b00;
        font-size: 1rem;
        font-weight: 900;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
    }
    .seating-date-icon {
        width: 28px;
        height: 28px;
        border-radius: 9px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: rgba(255,255,255,0.35);
        font-size: 1rem;
    }
    .seating-summary-content {
        flex: 1;
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        align-items: stretch;
        row-gap: 0.6rem;
    }
    .seating-slot-pill {
        flex: 1 1 0;
        min-height: 56px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.45rem;
        padding: 0.65rem 0.7rem;
        border-radius: 14px;
        background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(231,244,234,0.9) 100%);
        border: 1px solid rgba(76, 140, 92, 0.35);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
    }
    .seating-slot-list {
        display: flex;
        flex-direction: row;
        flex-wrap: wrap;
        gap: 0.7rem;
    }
    .seating-slot-row {
        flex: 1 1 220px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        padding: 0.8rem 0.9rem;
        border-radius: 14px;
        background: linear-gradient(180deg, rgba(255,255,255,0.85), rgba(242,236,229,0.75));
        border: 1px solid rgba(180, 160, 146, 0.4);
    }
    .seating-slot-label {
        font-size: 1.05rem;
        font-weight: 900;
        color: #234d3d;
        letter-spacing: 0.02em;
        min-width: 24px;
        text-align: center;
    }
    .seating-slot-stat {
        color: #4a5b61;
        font-size: 0.85rem;
        line-height: 1.2;
        font-weight: 800;
    }
    .seating-slot-meta {
        color: #6f4d22;
        font-size: 0.72rem;
        font-weight: 900;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    .seating-slot-low {
        color: #a64b12;
        font-weight: 900;
    }
    .seating-slot-full {
        color: #8a2e1e;
        font-weight: 900;
    }
    .seating-slot-full {
        color: #a63d2b;
        font-weight: 900;
    }
    .seating-day-names {
        margin-top: 0.85rem;
        border-top: 1px solid rgba(122, 98, 88, 0.2);
        padding-top: 0.85rem;
    }
    .seating-day-names [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-wrap: nowrap !important;
        gap: 0.45rem !important;
        align-items: center !important;
        overflow-x: auto !important;
    }
    .seating-day-names [data-testid="stHorizontalBlock"] > div {
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 0 !important;
    }
    .seating-day-names-label {
        font-size: 0.75rem;
        font-weight: 900;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #6d5a52;
        margin-bottom: 0.5rem;
    }
    .seating-name-list {
        display: flex;
        flex-direction: column;
        gap: 0.45rem;
        color: #2f3f45;
    }
    .seating-name-inline-row {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0.38rem 0.7rem;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(255,255,255,0.85) 0%, rgba(233,248,236,0.95) 100%);
        border: 1px solid rgba(46, 125, 50, 0.9);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(46, 125, 50, 0.08);
        min-height: 2.2rem;
        width: 100%;
        text-align: center;
        position: relative;
    }
    .seating-name-inline-text {
        font-size: 0.95rem;
        line-height: 1.2;
        color: #1d5e2a;
        font-weight: 900;
        white-space: nowrap;
    }
    .seating-name-inline-actions {
        margin-left: 0.25rem;
        font-size: 1rem;
        line-height: 1;
        color: #7a4500;
    }
    .seating-slot-row-inline {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.2rem;
        margin-top: 0.2rem;
        padding-bottom: 0.15rem;
    }
    .seating-slot-names-wrap {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.15rem;
        flex: 1;
        min-width: 0;
    }
    button[title*="Delete "] {
        position: absolute !important;
        right: 0.4rem !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        background: rgba(220, 53, 69, 0.1) !important;
        border: 1px solid rgba(220, 53, 69, 0.9) !important;
        border-radius: 50% !important;
        box-shadow: none !important;
        color: #b42318 !important;
        padding: 0 !important;
        min-width: auto !important;
        width: 1.35rem !important;
        height: 1.35rem !important;
        font-size: 0.82rem !important;
        line-height: 1 !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    button[title*="Delete "]:hover {
        background: rgba(220, 53, 69, 0.16) !important;
        border-color: rgba(220, 53, 69, 1) !important;
        color: #991b1b !important;
    }
    div[data-testid="stColumn"] {
        position: relative !important;
    }
    .seating-name-inline-actions {
        display: flex;
        align-items: center;
        gap: 0.1rem;
        font-size: 1rem;
        color: #7a4500;
    }
    .seating-empty {
        color: #64757d;
        font-size: 0.96rem;
        font-style: italic;
        padding: 0.35rem 0;
    }
    div[data-testid="stForm"] {
        margin-top: 0.85rem;
        padding: 1rem;
        border-radius: 18px;
        background: linear-gradient(180deg, #fffdfc 0%, #f5efe7 100%);
        border: 1px solid rgba(167, 141, 123, 0.35);
        box-shadow: 0 8px 18px rgba(126, 102, 82, 0.08);
    }
    div[data-testid="stForm"] .stButton > button {
        background: linear-gradient(135deg, #c8691d 0%, #a94d04 100%);
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.1rem !important;
        font-weight: 800 !important;
        box-shadow: 0 8px 18px rgba(169, 77, 4, 0.24);
    }
    div[data-testid="stForm"] .stButton > button:hover {
        background: linear-gradient(135deg, #d97725 0%, #b6570f 100%) !important;
        color: white !important;
    }
    div[data-testid="stForm"] .stTextInput > div > div > input,
    div[data-testid="stForm"] .stSelectbox > div > div > div,
    div[data-testid="stForm"] .stRadio > div {
        border-radius: 12px !important;
    }
    div[class*="st-key-ganesh_add_"] .stButton > button {
        background: linear-gradient(135deg, #c8691d 0%, #a94d04 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.1rem !important;
        font-weight: 800 !important;
        box-shadow: 0 8px 18px rgba(169, 77, 4, 0.24);
    }
    div[class*="st-key-ganesh_add_"] .stButton > button:hover {
        background: linear-gradient(135deg, #d97725 0%, #b6570f 100%) !important;
        color: white !important;
    }
    </style>
'''

# Custom button styles for events section
EVENTS_CSS = '''
    <style>
    .event-card {
        position: relative;
        overflow: hidden;
        display: flex;
        gap: 1.2rem;
        border: 1px solid #d7ccc8;
        border-left: 6px solid #bf360c;
        border-radius: 16px;
        background: linear-gradient(120deg, #fffaf0 0%, #f1f8e9 100%);
        box-shadow: 0 8px 20px rgba(93, 64, 55, 0.11);
        padding: 1.25rem 1.4rem;
        margin-bottom: 1rem;
    }
    .event-date-block {
        flex: 0 0 88px;
        align-self: stretch;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        background: #fff3e0;
        color: #bf360c;
        text-align: center;
    }
    .event-date-icon { font-size: 1.35rem; }
    .event-date-label {
        margin-top: 0.35rem;
        font-size: 0.8rem;
        font-weight: 800;
        line-height: 1.25;
    }
    .event-card-content { flex: 1; min-width: 0; }
    .event-time-badge {
        display: inline-block;
        margin-bottom: 0.85rem;
        padding: 0.38rem 0.7rem;
        border-radius: 999px;
        background: #e8f5e9;
        color: #2e7d32;
        font-size: 0.86rem;
        font-weight: 800;
    }
    .event-card.past {
        border-left-color: #90a4ae;
        background: linear-gradient(120deg, #f5f5f5 0%, #eceff1 100%);
        box-shadow: 0 4px 12px rgba(84, 110, 122, 0.08);
    }
    .event-card-title {
        color: #3e2723;
        font-size: 1.3rem;
        font-weight: 800;
        line-height: 1.25;
        margin-bottom: 0.8rem;
    }
    .event-card.past .event-card-title { color: #607d8b; }
    .event-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin-bottom: 0.9rem;
    }
    .event-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.42rem 0.7rem;
        border: 1px solid #c5d9c0;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.76);
        color: #2e7d32;
        font-size: 0.88rem;
        font-weight: 700;
    }
    .event-description {
        padding-top: 0.85rem;
        border-top: 1px solid rgba(93, 64, 55, 0.14);
        color: #546e7a;
        font-size: 0.96rem;
        line-height: 1.55;
    }
    @media (max-width: 640px) {
        .event-card { gap: 0.8rem; padding: 1rem; }
        .event-date-block { flex-basis: 70px; }
        .event-date-label { font-size: 0.72rem; }
        .event-card-title { font-size: 1.08rem; }
    }
    @media (max-width: 640px) {
        .seating-day-card { margin: 0.85rem 0 1rem; padding: 0.85rem 0.8rem 0.95rem; }
        .seating-day-summary-box { margin-bottom: 1rem; padding: 0.7rem; }
        .seating-summary-content { row-gap: 0.7rem; }
        .seating-slot-pill { min-height: 52px; }
        .seating-day-names { margin-top: 0.95rem; padding-top: 0.95rem; }
    }
    </style>
'''
import pandas as pd
import datetime
from .db import get_connection


def _ensure_ganesh_pooja_seating_table(cursor):
    if hasattr(cursor.connection, "account"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS GANESH_POOJA_SEATING (
                id NUMBER AUTOINCREMENT START 1 INCREMENT 1,
                name VARCHAR,
                pooja_date DATE,
                pooja_time VARCHAR,
                created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                status VARCHAR DEFAULT 'active'
            )
            """
        )
    else:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ganesh_pooja_seating (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                pooja_date DATE NOT NULL,
                pooja_time TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
            """
        )


def _get_seating_capacity():
    try:
        capacity = st.secrets.get("ganesh_pooja_seating_capacity", 5)
        return max(1, int(capacity))
    except Exception:
        return 5


def _get_seating_dates():
    start_date = datetime.date(2026, 9, 14)
    end_date = datetime.date(2026, 9, 20)
    return [start_date + datetime.timedelta(days=offset) for offset in range((end_date - start_date).days + 1)]


def _get_seating_pooja_options_for_date(seating_date):
    start_date = datetime.date(2026, 9, 14)
    end_date = datetime.date(2026, 9, 20)
    if seating_date == start_date:
        return ["Evening Pooja"]
    if seating_date == end_date:
        return ["Morning Pooja"]
    return ["Morning Pooja", "Evening Pooja"]


def _ganesh_pooja_seating_tab():
    st.markdown(SEATING_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="seating-hero">
            <div class="seating-hero-icon">🪔</div>
            <div class="seating-hero-text">
                <div class="seating-hero-title">Ganesh Pooja Seating</div>
                <div class="seating-hero-subtitle">Choose a day and reserve a pooja slot.</div>
                <div class="seating-hero-legend">
                    <span class="seating-legend-item"><span class="seating-legend-icon">🌅</span> Morning</span>
                    <span class="seating-legend-item"><span class="seating-legend-icon">🌙</span> Evening</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    conn = get_connection()
    cursor = conn.cursor()
    _ensure_ganesh_pooja_seating_table(cursor)
    conn.commit()

    capacity = _get_seating_capacity()
    seating_dates = _get_seating_dates()

    cursor.execute(
        "SELECT pooja_date, pooja_time, COUNT(*) FROM ganesh_pooja_seating WHERE status='active' GROUP BY pooja_date, pooja_time"
    )
    counts_rows = cursor.fetchall()
    counts_by_slot = {(row[0], row[1]): row[2] for row in counts_rows}

    cursor.execute(
        "SELECT id, name, pooja_date, pooja_time FROM ganesh_pooja_seating WHERE status='active' ORDER BY pooja_date, pooja_time, name"
    )
    registrations = cursor.fetchall()

    registrations_by_date = {}
    for registration in registrations:
        registrations_by_date.setdefault(registration[2], []).append(registration)

    for current_date in seating_dates:
        options = _get_seating_pooja_options_for_date(current_date)
        names_for_day = registrations_by_date.get(current_date, [])

        summary_parts = []
        summary_parts.append(
            f"<div class=\"seating-date-chip\"><span class=\"seating-date-icon\">📅</span>{current_date.strftime('%d-%b-%Y')}</div>"
        )

        for option in options:
            count = counts_by_slot.get((current_date, option), 0)
            remaining = max(capacity - count, 0)
            slot_state = "FULL" if count >= capacity else f"{remaining} slot(s) left"
            icon = "🌅" if option == "Morning Pooja" else "🌙"
            summary_parts.append(
                f"<div class=\"seating-slot-pill\"><span class=\"seating-slot-label\">{icon}</span><span class=\"seating-slot-stat\">{count}/{capacity}</span><span class=\"seating-slot-meta\">{slot_state}</span></div>"
            )

        st.markdown(
            f"<div class=\"seating-day-summary-box\"><div class=\"seating-summary-content\">{' '.join(summary_parts)}</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown("<div class=\"seating-day-names\">", unsafe_allow_html=True)

        names_by_slot = {option: [] for option in options}
        for reg_id, name_value, _, time_value in names_for_day:
            names_by_slot.setdefault(time_value, []).append((reg_id, name_value))

        has_any_registrations = False

        for option in options:
            slot_icon = "🌅" if option == "Morning Pooja" else "🌙"
            slot_label = option.replace(" Pooja", "")
            registrations_for_slot = names_by_slot.get(option, [])

            if registrations_for_slot:
                has_any_registrations = True
                st.markdown(f"**{slot_icon} {slot_label}**")

                for reg_id, name_value in registrations_for_slot:
                    name_col, delete_col = st.columns([6, 1])
                    with name_col:
                        st.markdown(
                            f'<div class="seating-name-inline-row"><span class="seating-name-inline-text">{name_value}</span></div>',
                            unsafe_allow_html=True,
                        )
                    with delete_col:
                        if st.button(
                            "✕",
                            key=f"delete_seating_{reg_id}",
                            help=f"Delete {name_value}",
                            use_container_width=False,
                        ):
                            cursor.execute(
                                "UPDATE ganesh_pooja_seating SET status='deleted' WHERE id=%s",
                                (reg_id,),
                            )
                            conn.commit()
                            st.rerun()

        if not has_any_registrations:
            st.markdown('<div class="seating-empty">No registrations yet.</div>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        add_button_key = f"ganesh_add_{current_date.isoformat()}"
        if st.button("Add Entry", key=add_button_key):
            st.session_state["ganesh_add_day"] = current_date

        if st.session_state.get("ganesh_add_day") == current_date:
            with st.form(f"ganesh_add_form_{current_date.isoformat()}"):
                new_name = st.text_input("Name", key=f"ganesh_name_{current_date.isoformat()}")
                selected_slot = st.radio(
                    "Pooja Time",
                    options,
                    horizontal=True,
                    key=f"ganesh_slot_{current_date.isoformat()}",
                    format_func=lambda slot: "🌅" if slot == "Morning Pooja" else "🌙",
                )
                submitted = st.form_submit_button("Save")

                if submitted:
                    clean_name = new_name.strip()
                    if not clean_name:
                        st.error("Please enter a name.")
                    else:
                        current_count = counts_by_slot.get((current_date, selected_slot), 0)
                        if current_count >= capacity:
                            st.error(
                                f"This slot is full. The limit for {selected_slot} on {current_date.strftime('%d-%b-%Y')} is {capacity}."
                            )
                        else:
                            cursor.execute(
                                "INSERT INTO ganesh_pooja_seating (name, pooja_date, pooja_time, status) VALUES (%s, %s, %s, %s)",
                                (clean_name, current_date, selected_slot, 'active')
                            )
                            conn.commit()
                            st.session_state.pop("ganesh_add_day", None)
                            st.rerun()


def events_tab():
    requested_tab = str(st.query_params.get("tab", "")).strip().lower()
    requested_view = str(st.query_params.get("view", "")).strip().lower()
    is_ganesh_pooja_seating_requested = requested_tab in {
        "ganesh-pooja-seating",
        "ganesh_pooja_seating",
        "pooja-seating",
        "seating",
    } or requested_view in {
        "ganesh-pooja-seating",
        "ganesh_pooja_seating",
        "pooja-seating",
        "seating",
    }

    if is_ganesh_pooja_seating_requested:
        _ganesh_pooja_seating_tab()
        return

    st.session_state['active_tab'] = 'Events'
    # Inject CSS on every rerun: module-level st.markdown only executes on first
    # import, so the styles were lost after login/logout reruns.
    st.markdown(EVENTS_CSS, unsafe_allow_html=True)
    conn = get_connection()
    cursor = conn.cursor()
    # Admin credentials for add/edit/delete
    ADMIN_USERNAME = st.secrets["admin_user"]
    ADMIN_PASSWORD_BASE = st.secrets["admin_pass"]
    def get_admin_password():
        today_day = datetime.date.today().strftime('%d')
        return f"{ADMIN_PASSWORD_BASE}{today_day}"

    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        # User view: Active Events, Past Events
        cursor.execute("SELECT id, title, event_date, event_time, link, description FROM events ORDER BY event_date, event_time")
        events = cursor.fetchall()
        if events:
            df_events = pd.DataFrame(events, columns=["ID", "Event Name", "Date", "Time", "Link", "Description"])
            display_df = df_events.drop(columns=["ID", "Link"])
            import pytz
            cst = pytz.timezone('US/Central')
            today_cst = datetime.datetime.now(cst).date()
            # Check for parsing issues
            display_df['Date_obj'] = pd.to_datetime(display_df['Date'], errors='coerce').dt.date
            if display_df['Date_obj'].isnull().all():
                st.warning("All event dates failed to parse. Check date format in database. Showing all events as active.")
                upcoming_df = display_df.copy()
                past_df = pd.DataFrame(columns=display_df.columns)
            else:
                upcoming_df = display_df[display_df['Date_obj'] >= today_cst]
                past_df = display_df[display_df['Date_obj'] < today_cst]
            tab1, tab2 = st.tabs(["Active Events", "Past Events"])
            with tab1:
                if not upcoming_df.empty:
                    for idx, row in upcoming_df.iterrows():
                        st.markdown(f"""
                        <div class='event-card'>
                            <div class='event-date-block'>
                                <div class='event-date-icon'>📅</div>
                                <div class='event-date-label'>{row['Date']}</div>
                            </div>
                            <div class='event-card-content'>
                                <div class='event-card-title'>{row['Event Name']}</div>
                                <div class='event-time-badge'>⏰ {row['Time']}</div>
                                <div class='event-description'>{row['Description'] or 'Join us for this special celebration.'}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No active events.")
            with tab2:
                if not past_df.empty:
                    for idx, row in past_df.iterrows():
                        st.markdown(f"""
                        <div class='event-card past'>
                            <div class='event-date-block'>
                                <div class='event-date-icon'>📅</div>
                                <div class='event-date-label'>{row['Date']}</div>
                            </div>
                            <div class='event-card-content'>
                                <div class='event-card-title'>{row['Event Name']}</div>
                                <div class='event-time-badge'>⏰ {row['Time']}</div>
                                <div class='event-description'>{row['Description'] or 'Event completed.'}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No past events.")
        else:
            st.info("No events added yet.")
    # Only show admin login prompt if not logged in as user

    # Admin is logged in: show full add/edit/delete UI

    if st.session_state.get('admin_logged_in', False):
        # Admin view: Add Event, Active Events, Past Events, Edit/Delete Event
        if "events" not in st.session_state or st.session_state.get("refresh_events", True):
            cursor.execute("SELECT id, title, event_date, event_time, link, description FROM events ORDER BY event_date, event_time")
            events = cursor.fetchall()
            st.session_state.events = events
            st.session_state.refresh_events = False
        else:
            events = st.session_state.events

        df_events = pd.DataFrame(events, columns=["ID", "Event Name", "Date", "Time", "Link", "Description"]) if events else pd.DataFrame(columns=["ID", "Event Name", "Date", "Time", "Link", "Description"])
        display_df = df_events.drop(columns=["ID", "Link"]) if not df_events.empty else pd.DataFrame()
        import pytz
        cst = pytz.timezone('US/Central')
        today_cst = datetime.datetime.now(cst).date()
        if not display_df.empty:
            display_df['Date_obj'] = pd.to_datetime(display_df['Date'], errors='coerce').dt.date
            if display_df['Date_obj'].isnull().all():
                st.warning("All event dates failed to parse. Check date format in database. Showing all events as active.")
                upcoming_df = display_df.copy()
                past_df = pd.DataFrame(columns=display_df.columns)
            else:
                upcoming_df = display_df[display_df['Date_obj'] >= today_cst]
                past_df = display_df[display_df['Date_obj'] < today_cst]
        else:
            display_df['Date_obj'] = []
            upcoming_df = pd.DataFrame()
            past_df = pd.DataFrame()
        tab_active, tab_past, tab_add, tab_edit = st.tabs(["Active Events", "Past Events", "Add Event", "Edit/Delete Event"])

        with tab_add:
            st.markdown("### ➕ Add New Event")
            with st.form("add_event_form"):
                new_title = st.text_input("Event Title")
                new_date = st.date_input("Event Date", value=datetime.date.today())
                new_time = st.time_input("Event Time", value=datetime.time(0,0))
                new_description = st.text_area("Description (optional)")
                submitted = st.form_submit_button("Add Event")
                if submitted:
                    if not new_title.strip():
                        st.error("Event title is required.")
                    else:
                        try:
                            if hasattr(cursor, 'execute') and hasattr(cursor.connection, 'account'):
                                cursor.execute(
                                    "INSERT INTO events (title, event_date, event_time, link, description) VALUES (%s, %s, %s, %s, %s)",
                                    (new_title, new_date, new_time, None, new_description)
                                )
                            else:
                                cursor.execute(
                                    "INSERT INTO events (title, event_date, event_time, link, description) VALUES (%s, %s, %s, %s, %s)",
                                    (new_title, new_date, new_time, None, new_description)
                                )
                            conn.commit()
                            st.success("✅ Event added successfully!")
                            st.session_state.refresh_events = True
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Failed to add event: {e}")

        with tab_active:
            if not upcoming_df.empty:
                for idx, row in upcoming_df.iterrows():
                    st.markdown(f"""
                    <div class='event-card'>
                        <div class='event-card-title'>{row['Event Name']}</div>
                        <div class='event-meta'>
                            <span class='event-badge'>📅 {row['Date']}</span>
                            <span class='event-badge'>⏰ {row['Time']}</span>
                        </div>
                        <div class='event-description'>{row['Description'] or 'Join us for this special celebration.'}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No active events.")

        with tab_past:
            if not past_df.empty:
                for idx, row in past_df.iterrows():
                    st.markdown(f"""
                    <div class='event-card past'>
                        <div class='event-card-title'>{row['Event Name']}</div>
                        <div class='event-meta'>
                            <span class='event-badge'>📅 {row['Date']}</span>
                            <span class='event-badge'>⏰ {row['Time']}</span>
                        </div>
                        <div class='event-description'>{row['Description'] or 'Event completed.'}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No past events.")

        with tab_edit:
            if not df_events.empty:
                selected_event_id = st.selectbox(
                    "Select Event to Edit/Delete",
                    df_events["ID"].tolist(),
                    format_func=lambda x: df_events[df_events["ID"] == x]["Event Name"].values[0],
                    key="select_event_edit_delete_bottom"
                )

                if selected_event_id:
                    event_row = df_events[df_events["ID"] == selected_event_id].iloc[0]
                    tab1, tab2 = st.tabs(["Edit Event", "Delete Event"])

                    with tab1:
                        edited_title = st.text_input("Edit Event Title", value=event_row["Event Name"], key="edit_event_title_bottom")
                        edited_date = st.date_input(
                            "Edit Event Date",
                            value=pd.to_datetime(event_row["Date"]).date() if pd.notna(event_row["Date"]) else datetime.date.today(),
                            key="edit_event_date_bottom"
                        )
                        if pd.notna(event_row["Time"]):
                            if isinstance(event_row["Time"], datetime.time):
                                default_time = event_row["Time"]
                            else:
                                default_time = pd.to_datetime(event_row["Time"]).time()
                        else:
                            default_time = datetime.time(0,0)
                        edited_time = st.time_input("Edit Event Time", value=default_time, key="edit_event_time_bottom")
                        edited_description = st.text_area("Edit Description (optional)", value=event_row["Description"] if pd.notna(event_row["Description"]) else "", key="edit_event_description_bottom")
                        if st.button("Update Event", key="update_event_bottom"):
                            if not edited_title.strip():
                                st.error("Event title is required.")
                            else:
                                try:
                                    cursor.execute(
                                        "UPDATE events SET title=%s, event_date=%s, event_time=%s, link=%s, description=%s WHERE id=%s",
                                        (edited_title, edited_date, edited_time, None, edited_description, selected_event_id)
                                    )
                                    conn.commit()
                                    st.success("✅ Event updated successfully!")
                                    st.session_state.refresh_events = True
                                    st.rerun()
                                except Exception as e:
                                    conn.rollback()
                                    st.error(f"❌ Failed to update event: {e}")

                    with tab2:
                        st.markdown("#### Delete this event?")
                        st.markdown(f"**Title:** {event_row['Event Name']}")
                        st.markdown(f"**Date:** {event_row['Date']}")
                        st.markdown(f"**Time:** {event_row['Time']}")
                        st.markdown(f"**Description:** {event_row['Description']}")
                        if st.button("Delete Event", key="delete_event_bottom"):
                            try:
                                cursor.execute("DELETE FROM events WHERE id=%s", (selected_event_id,))
                                conn.commit()
                                st.success("🗑️ Event deleted successfully!")
                                st.session_state.refresh_events = True
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"❌ Failed to delete event: {e}")
            else:
                st.info("No events available to edit or delete.")
