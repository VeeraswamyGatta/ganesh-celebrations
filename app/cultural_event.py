import datetime
import html
from io import BytesIO
import re

import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu

from .db import get_connection


CULTURAL_EVENT_CSS = """
<style>
.cultural-hero {
    padding: 1.5rem 1.6rem;
    margin: 0 0 1rem;
    border: 1px solid #e4c27a;
    border-radius: 18px;
    background: linear-gradient(135deg, #fff8e8 0%, #fffdf8 52%, #eef7ef 100%);
    box-shadow: 0 10px 24px rgba(105, 76, 52, 0.12);
}
.cultural-kicker {
    color: #a64b12;
    font-size: 0.78rem;
    font-weight: 900;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.cultural-title {
    margin-top: 0.35rem;
    color: #4e2922;
    font-size: clamp(1.45rem, 3vw, 2.35rem);
    font-weight: 900;
    line-height: 1.15;
}
.cultural-description {
    margin: 0.8rem 0 1rem;
    padding: 0.8rem 0.95rem;
    border: 1px solid #e5c36f;
    border-left: 5px solid #c8691d;
    border-radius: 11px;
    background: linear-gradient(110deg, #fff8e7 0%, #fffdf8 100%);
    color: #5f3c1d;
    font-size: 0.98rem;
    line-height: 1.55;
}
.cultural-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin-top: 1rem;
}
.cultural-meta-item {
    padding: 0.48rem 0.75rem;
    border: 1px solid #d7e3d4;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.72);
    color: #28543a;
    font-size: 0.84rem;
    font-weight: 800;
}
.cultural-note {
    position: relative;
    margin-top: 1rem;
    padding: 0.7rem 0.85rem;
    border-left: 4px solid #c8691d;
    border-radius: 8px;
    background: rgba(255, 248, 231, 0.82);
    color: #b42318;
    font-size: 0.9rem;
    font-weight: 800;
    line-height: 1.45;
}
.cultural-note strong {
    color: #b42318;
}
.cultural-note::before,
.cultural-note::after {
    position: absolute;
    color: #ef8f20;
    font-size: 0.85rem;
    font-weight: 900;
}
.cultural-note::before {
    content: "✦";
    top: 0.35rem;
    right: 0.55rem;
}
.cultural-note::after {
    content: "✧";
    right: 1.5rem;
    bottom: 0.35rem;
}
.cultural-section-heading {
    margin: 0.7rem 0 0.4rem;
    color: #4e2922;
    font-size: 1.05rem;
    font-weight: 900;
}
.cultural-participating-heading {
    margin-top: 0.25rem;
}
.cultural-inline-label {
    margin: 0;
    color: #4e2922;
    font-size: 1.05rem;
    font-weight: 900;
    line-height: 2.4rem;
    white-space: nowrap;
}
.cultural-filter-label {
    display: flex;
    align-items: center;
    min-height: 2.35rem;
    color: #6d625b;
    font-size: 0.82rem;
    font-weight: 700;
    line-height: 1.2;
    white-space: nowrap;
}
.cultural-section-note {
    margin-bottom: 0.7rem;
    color: #b42318;
    font-size: 0.9rem;
    font-weight: 800;
}
.cultural-order-table {
    width: 100%;
    margin: 0.15rem 0 0.45rem;
    border-collapse: separate;
    border-spacing: 0 0.1rem;
    font-family: "Trebuchet MS", Georgia, serif;
}
.cultural-order-table th {
    padding: 0.32rem 0.45rem;
    background: #6a1b1b;
    color: #fffaf0;
    font-size: 0.7rem;
    letter-spacing: 0.02em;
    line-height: 1.2;
    text-align: left;
    text-transform: none;
}
.cultural-order-table th:first-child { border-radius: 9px 0 0 9px; }
.cultural-order-table th:last-child { border-radius: 0 9px 9px 0; }
.cultural-order-table td {
    padding: 0.3rem 0.45rem;
    border-top: 1px solid #eadcc6;
    border-bottom: 1px solid #eadcc6;
    background: #fffdf8;
    color: #493a35;
    font-size: 0.8rem;
    line-height: 1.3;
    vertical-align: middle;
}
.cultural-order-table td:first-child {
    border-left: 1px solid #eadcc6;
    color: #a64b12;
    font-weight: 900;
}
.cultural-order-table td:last-child { border-right: 1px solid #eadcc6; }
.cultural-performance-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.4rem;
    margin: 0.25rem 0 0.55rem;
}
.cultural-performance-stat {
    position: relative;
    min-height: 3.45rem;
    padding: 0.55rem 0.7rem 0.5rem;
    overflow: hidden;
    border: 1px solid #eadcc6;
    border-left: 4px solid #c8691d;
    border-radius: 10px;
    background: linear-gradient(135deg, #fffdf8 0%, #f7eee3 100%);
    box-shadow: 0 4px 10px rgba(105, 76, 52, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.8);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.cultural-performance-stat:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 14px rgba(105, 76, 52, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.9);
}
.cultural-performance-stat:nth-child(1) {
    border-left-color: #6a1b1b;
    background: linear-gradient(135deg, #fff8e8 0%, #f5e1d0 100%);
}
.cultural-performance-stat:nth-child(3) { border-left-color: #2e7d32; }
.cultural-performance-stat:nth-child(4) { border-left-color: #1565c0; }
.cultural-performance-stat:nth-child(5) { border-left-color: #7e57c2; }
.cultural-performance-stat:nth-child(6) { border-left-color: #00838f; }
.cultural-performance-stat:nth-child(2) { border-left-color: #ef6c00; }
.cultural-performance-stat:nth-child(1) .cultural-performance-stat-count {
    color: #6a1b1b;
}
.cultural-performance-stat::after {
    position: absolute;
    right: -0.25rem;
    bottom: -0.65rem;
    color: rgba(166, 75, 18, 0.1);
    content: "✦";
    font-size: 2.8rem;
    line-height: 1;
}
.cultural-performance-stat-label {
    display: block;
    color: #6d625b;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.01em;
    line-height: 1.2;
}
.cultural-performance-stat-count {
    display: block;
    margin-top: 0.12rem;
    color: #6a1b1b;
    font-size: 1.45rem;
    font-weight: 900;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(255, 255, 255, 0.7);
}
.cultural-performance-stat-unit {
    display: inline-block;
    margin-left: 0.25rem;
    color: #8b6f61;
    font-size: 0.63rem;
    font-weight: 700;
}
@media (max-width: 560px) {
    .cultural-performance-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.cultural-order-empty {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 0.35rem 0 1rem;
    padding: 1rem 1.1rem;
    border: 1px solid #c9dfca;
    border-left: 5px solid #2e7d32;
    border-radius: 13px;
    background: linear-gradient(110deg, #eef7ef 0%, #fffdf8 100%);
    color: #28543a;
    font-family: "Trebuchet MS", Georgia, serif;
    font-size: 0.95rem;
    font-weight: 700;
    line-height: 1.5;
}
div[class*="st-key-tgt_add_registration"] button {
    min-height: 2.45rem !important;
    padding: 0.55rem 0.85rem !important;
    border: 1px solid #ffb300 !important;
    border-radius: 14px !important;
    background: linear-gradient(135deg, #ff8f00 0%, #ff5e00 45%, #d81b60 100%) !important;
    color: #ffffff !important;
    font-weight: 800 !important;
    box-shadow: 0 5px 14px rgba(255, 94, 0, 0.25) !important;
}
div[class*="st-key-tgt_participant_details_button"] button,
div[class*="st-key-tgt_participant_add_button"] button,
div[class*="st-key-tgt_participant_edit_button"] button,
div[class*="st-key-tgt_participant_delete_button"] button {
    min-height: 2.35rem !important;
    padding: 0.45rem 0.35rem !important;
    border: 0 !important;
    border-radius: 9px !important;
    color: #ffffff !important;
    font-size: 0.78rem !important;
    font-weight: 800 !important;
    white-space: nowrap !important;
}
div[class*="st-key-tgt_participant_details_button"] button { background: #6a1b1b !important; }
div[class*="st-key-tgt_participant_add_button"] button { background: #2e7d32 !important; }
div[class*="st-key-tgt_participant_edit_button"] button { background: #1565c0 !important; }
div[class*="st-key-tgt_participant_delete_button"] button { background: #c62828 !important; }
div[class*="st-key-tgt_agreement_actions"] {
    margin: 0.35rem 0 1.05rem !important;
    padding-bottom: 0.2rem !important;
}
div[class*="st-key-tgt_agreement_add_button"] button,
div[class*="st-key-tgt_agreement_edit_button"] button,
div[class*="st-key-tgt_agreement_delete_button"] button,
div[class*="st-key-tgt_agreement_description_button"] button {
    min-height: 2.35rem !important;
    padding: 0.45rem 0.35rem !important;
    border: 0 !important;
    border-radius: 9px !important;
    color: #ffffff !important;
    font-size: 0.78rem !important;
    font-weight: 800 !important;
    white-space: nowrap !important;
}
div[class*="st-key-tgt_agreement_add_button"] button { background: #ef5350 !important; }
div[class*="st-key-tgt_agreement_edit_button"] button { background: #1565c0 !important; }
div[class*="st-key-tgt_agreement_delete_button"] button { background: #ad1457 !important; }
div[class*="st-key-tgt_agreement_description_button"] button { background: #ef6c00 !important; }
div[class*="st-key-download_cultural_event_participants"] button {
    width: 2.35rem !important;
    min-height: 2.35rem !important;
    padding: 0.35rem !important;
    border: 1px solid #eadcc6 !important;
    border-radius: 9px !important;
    background: #fff8e8 !important;
    color: #6a1b1b !important;
}
.cultural-form-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 0.2rem 0 0.9rem;
    padding: 0.75rem 0.9rem;
    border: 1px solid #d7e3d4;
    border-radius: 11px;
    background: linear-gradient(110deg, #eef7ef 0%, #fffaf0 100%);
    color: #28543a;
    font-size: 1rem;
    font-weight: 900;
}
.cultural-agreement-list {
    margin: 0.35rem 0 1rem;
    padding: 0.35rem 0.75rem;
    border: 1px solid #eadcc6;
    border-radius: 13px;
    background: #fffdf8;
}
.cultural-agreement-row {
    display: flex;
    align-items: flex-start;
    gap: 0.7rem;
    padding: 0.65rem 0.2rem;
    border-bottom: 1px solid #f0e6d8;
    color: #493a35;
    font-family: "Trebuchet MS", Georgia, serif;
    font-size: 0.9rem;
    line-height: 1.45;
}
.cultural-agreement-row:last-child { border-bottom: 0; }
.cultural-agreement-number {
    flex: 0 0 1.65rem;
    color: #a64b12;
    font-weight: 900;
}
.cultural-agreement-required {
    margin-left: auto;
    padding: 0.18rem 0.45rem;
    border-radius: 999px;
    background: #fff1d6;
    color: #8b3f12;
    font-size: 0.7rem;
    font-weight: 900;
    white-space: nowrap;
}
div[data-testid="stCheckbox"] label {
    color: #b42318 !important;
    font-family: "Trebuchet MS", Georgia, serif !important;
    font-size: 0.95rem !important;
    font-weight: 800 !important;
    line-height: 1.55 !important;
}
div[data-testid="stCheckbox"] label p {
    color: #b42318 !important;
    font-weight: 800 !important;
}
div[data-testid="stForm"]:has(.cultural-form-marker) {
    padding: 0.15rem 1.15rem 1.15rem;
    border: 1px solid #eadcc6;
    border-radius: 16px;
    background: linear-gradient(180deg, #fffefb 0%, #f7f1e9 100%);
    box-shadow: 0 8px 20px rgba(105, 76, 52, 0.08);
}
div[data-testid="stForm"]:has(.cultural-form-marker) .cultural-section-heading {
    margin-top: 0.3rem;
}
.cultural-form-marker {
    display: none;
}
.cultural-attention-note {
    margin: 0.15rem 0 0.9rem;
    padding: 0.8rem 0.95rem;
    border: 1px solid #e5c36f;
    border-left: 5px solid #c8691d;
    border-radius: 11px;
    background: linear-gradient(110deg, #fff8e7 0%, #fffdf8 100%);
    color: #5f3c1d;
    font-size: 0.9rem;
    line-height: 1.5;
}
.cultural-attention-title {
    color: #8b3f12;
    font-weight: 900;
}
div[data-testid="stForm"] .stFormSubmitButton button {
    min-height: 2.8rem;
    border: 0;
    border-radius: 10px;
    background: linear-gradient(135deg, #9d2738 0%, #6a1b1b 100%);
    color: #fff;
    font-weight: 800;
}
</style>
"""


TGT_PERFORMANCE_OPTIONS = [
    "Traditional Fashion Show",
    "Classical Dance",
    "Music / Singing",
    "Playing Instruments",
    "Play / Skit",
]

TGT_PERFORMANCE_DISPLAY = {
    "Music / Singing": "Music or Singing",
    "Playing Instruments": "Instrumental Music",
    "Play / Skit": "Play or Skit",
}


def _registration_performances(performance_type):
    values = performance_type if isinstance(performance_type, (list, tuple)) else str(performance_type or "").split(",")
    display_to_option = {display: option for option, display in TGT_PERFORMANCE_DISPLAY.items()}
    return [
        display_to_option.get(str(value).strip(), str(value).strip())
        for value in values
        if str(value).strip()
    ]


def _format_performances(performance_type):
    return ", ".join(
        TGT_PERFORMANCE_DISPLAY.get(option, option)
        for option in _registration_performances(performance_type)
    )


def _merge_display_registrations(registrations, performance_filter="All"):
    merged = {}
    for registration in registrations:
        registration_id, name, age_group, performance_type = registration[:4]
        performances = _registration_performances(performance_type)
        if performance_filter != "All" and performance_filter not in performances:
            continue
        if performance_filter != "All":
            performances = [performance_filter]
        key = (str(name).strip().casefold(), str(age_group).strip().casefold())
        if key not in merged:
            merged[key] = [*registration]
            merged[key][3] = list(performances)
        else:
            for performance in performances:
                if performance not in merged[key][3]:
                    merged[key][3].append(performance)

    display_registrations = []
    for registration in merged.values():
        registration[3] = ", ".join(
            TGT_PERFORMANCE_DISPLAY.get(performance, performance)
            for performance in TGT_PERFORMANCE_OPTIONS
            if performance in registration[3]
        )
        display_registrations.append(tuple(registration))
    return display_registrations

TGT_DEFAULT_DISCLAIMERS = [
    "Registration is mandatory. Participation is allowed only for registered participants; spot participation is not allowed.",
    "If your performance requires an audio track, send the audio file with the participant name to Purna (7209007378) via WhatsApp only.",
    "Due to technical limitations, songs cannot be played directly from YouTube or another online source. Only audio files shared with the organizers in advance will be played.",
    "The organizers will announce the performance order at the event and determine the sequence based on available time and event circumstances.",
    "Parents and participants must not insist that children perform first or pressure the organizers at the performance area.",
    "Only parents or guardians of children aged 3-6 years may accompany them in the performance area. Parents of children in other age groups must remain in the audience area.",
    "Because this event is part of the Lord Ganesha celebrations, only devotional songs are permitted. Film songs are not permitted.",
    "I have read and agree to all of the above registration requirements.",
]

TGT_EVENT_NOTE = "The program begins after the completion of Lord Ganesha Evening Pooja."


def _ensure_tgt_registration_tables(cursor):
    is_snowflake = hasattr(cursor.connection, "account")
    if is_snowflake:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS event_registration_programs (
                id NUMBER AUTOINCREMENT,
                slug VARCHAR NOT NULL UNIQUE,
                title VARCHAR NOT NULL,
                event_date DATE NOT NULL,
                event_time VARCHAR NOT NULL,
                location VARCHAR NOT NULL,
                description VARCHAR,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                PRIMARY KEY (id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS event_registration_disclaimers (
                id NUMBER AUTOINCREMENT,
                program_id NUMBER NOT NULL,
                sort_order NUMBER NOT NULL,
                disclaimer_text VARCHAR NOT NULL,
                is_required BOOLEAN DEFAULT TRUE,
                PRIMARY KEY (id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS event_registrations (
                id NUMBER AUTOINCREMENT,
                program_id NUMBER NOT NULL,
                participant_name VARCHAR NOT NULL,
                age_group VARCHAR NOT NULL,
                performance_type VARCHAR NOT NULL,
                apartment_numbers VARCHAR NOT NULL,
                agreed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                PRIMARY KEY (id)
            )
            """
        )
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS created_by VARCHAR")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS modified_by VARCHAR")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS modified_at TIMESTAMP_NTZ")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS deleted_by VARCHAR")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP_NTZ")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'active'")
    else:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS event_registration_programs (
                id SERIAL PRIMARY KEY,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                event_date DATE NOT NULL,
                event_time TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS event_registration_disclaimers (
                id SERIAL PRIMARY KEY,
                program_id INTEGER NOT NULL,
                sort_order INTEGER NOT NULL,
                disclaimer_text TEXT NOT NULL,
                is_required BOOLEAN DEFAULT TRUE
            )
            """
        )
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS created_by TEXT")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS modified_by TEXT")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS modified_at TIMESTAMP")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS deleted_by TEXT")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active'")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS event_registrations (
                id SERIAL PRIMARY KEY,
                program_id INTEGER NOT NULL,
                participant_name TEXT NOT NULL,
                age_group TEXT NOT NULL,
                performance_type TEXT NOT NULL,
                apartment_numbers TEXT NOT NULL,
                agreed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    cursor.execute(
        "SELECT id FROM event_registration_programs WHERE slug=%s AND active=TRUE",
        ("terrazzo-ganesha-events-2026",),
    )
    program_row = cursor.fetchone()
    if program_row is None:
        cursor.execute(
            """
            INSERT INTO event_registration_programs
                (slug, title, event_date, event_time, location, description)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                "terrazzo-ganesha-events-2026",
                "Terrazzo Ganesha Events - Traditional Fashion Show and Terrazzo Got Talent (TGT)",
                datetime.date(2026, 9, 19),
                "7:00 PM onwards",
                "Terrazzo Courtyard",
                TGT_EVENT_NOTE,
            ),
        )
        cursor.execute(
            "SELECT id FROM event_registration_programs WHERE slug=%s AND active=TRUE",
            ("terrazzo-ganesha-events-2026",),
        )
        program_row = cursor.fetchone()

    program_id = program_row[0]
    cursor.execute(
        "SELECT COUNT(*) FROM event_registration_disclaimers WHERE program_id=%s",
        (program_id,),
    )
    if cursor.fetchone()[0] == 0:
        for sort_order, disclaimer in enumerate(TGT_DEFAULT_DISCLAIMERS, start=1):
            cursor.execute(
                "INSERT INTO event_registration_disclaimers (program_id, sort_order, disclaimer_text, is_required) VALUES (%s, %s, %s, %s)",
                (program_id, sort_order, disclaimer, True),
            )
    cursor.execute(
        "UPDATE event_registration_disclaimers SET disclaimer_text=%s WHERE program_id=%s AND disclaimer_text=%s",
        (
            TGT_DEFAULT_DISCLAIMERS[3],
            program_id,
            "The organizers will announce the performance sequence at the event based on available time and event circumstances.",
        ),
    )
    return program_id


@st.cache_resource(show_spinner=False)
def _initialize_tgt_registration_tables():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if not hasattr(cursor.connection, "account"):
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtext('ganesh_cultural_event_schema'))"
            )
        program_id = _ensure_tgt_registration_tables(cursor)
        conn.commit()
        return program_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def _manage_tgt_disclaimers(conn, cursor, program_id, disclaimers, description):
    st.markdown('<div class="cultural-section-heading">Agreement management</div>', unsafe_allow_html=True)
    management_actions = [
        ("Add", "tgt_agreement_add_button"),
        ("Edit", "tgt_agreement_edit_button"),
        ("Delete", "tgt_agreement_delete_button"),
        ("Event Description", "tgt_agreement_description_button"),
    ]
    management_view = st.session_state.get("tgt_agreement_management_view", "List")
    with st.container(
        horizontal=True,
        wrap=False,
        vertical_alignment="center",
        gap="small",
        key="tgt_agreement_actions",
    ):
        for action_label, action_key in management_actions:
            if st.button(
                action_label,
                key=action_key,
                type="primary" if management_view == action_label else "secondary",
                width="stretch",
            ):
                st.session_state.tgt_agreement_management_view = (
                    "List" if management_view == action_label else action_label
                )
                st.rerun()

    if management_view == "List" and disclaimers:
        agreement_rows = []
        for index, (_, _, text, is_required) in enumerate(disclaimers, start=1):
            required_badge = '<span class="cultural-agreement-required">Required</span>' if is_required else ""
            agreement_rows.append(
                f"<div class='cultural-agreement-row'><span class='cultural-agreement-number'>{index}.</span><span>{html.escape(str(text))}</span>{required_badge}</div>"
            )
        st.markdown(
            f"<div class='cultural-agreement-list'>{''.join(agreement_rows)}</div>",
            unsafe_allow_html=True,
        )
    elif management_view == "List":
        st.info("No agreement points have been added yet.")

    if management_view == "Add":
        with st.form("tgt_add_disclaimer_form"):
            new_disclaimer = st.text_area("Agreement text", placeholder="Enter the request or agreement point.")
            new_is_required = st.checkbox("Required acknowledgement", value=True)
            if st.form_submit_button("Add Agreement", type="primary"):
                clean_disclaimer = new_disclaimer.strip()
                if not clean_disclaimer:
                    st.error("Please enter agreement text.")
                else:
                    cursor.execute(
                        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM event_registration_disclaimers WHERE program_id=%s",
                        (program_id,),
                    )
                    next_sort_order = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO event_registration_disclaimers (program_id, sort_order, disclaimer_text, is_required) VALUES (%s, %s, %s, %s)",
                        (program_id, next_sort_order, clean_disclaimer, new_is_required),
                    )
                    conn.commit()
                    st.success("Agreement added successfully.")
                    st.rerun()

    elif management_view == "Edit":
        if not disclaimers:
            st.info("No agreements are available to edit.")
            return
        disclaimer_options = {disclaimer_id: text for disclaimer_id, _, text, _ in disclaimers}
        selected_id = st.selectbox(
            "Select agreement to edit",
            list(disclaimer_options),
            format_func=lambda disclaimer_id: disclaimer_options[disclaimer_id],
            key="tgt_edit_disclaimer_id",
        )
        selected_disclaimer = next(row for row in disclaimers if row[0] == selected_id)
        with st.form("tgt_edit_disclaimer_form"):
            edited_text = st.text_area("Agreement text", value=selected_disclaimer[2])
            edited_required = st.checkbox("Required acknowledgement", value=bool(selected_disclaimer[3]))
            if st.form_submit_button("Save Agreement", type="primary"):
                clean_disclaimer = edited_text.strip()
                if not clean_disclaimer:
                    st.error("Agreement text cannot be empty.")
                else:
                    cursor.execute(
                        "UPDATE event_registration_disclaimers SET disclaimer_text=%s, is_required=%s WHERE id=%s AND program_id=%s",
                        (clean_disclaimer, edited_required, selected_id, program_id),
                    )
                    conn.commit()
                    st.success("Agreement updated successfully.")
                    st.rerun()

    elif management_view == "Delete":
        if not disclaimers:
            st.info("No agreements are available to delete.")
            return
        disclaimer_options = {disclaimer_id: text for disclaimer_id, _, text, _ in disclaimers}
        selected_id = st.selectbox(
            "Select agreement to delete",
            list(disclaimer_options),
            format_func=lambda disclaimer_id: disclaimer_options[disclaimer_id],
            key="tgt_delete_disclaimer_id",
        )
        st.warning("Deleting an agreement removes it from the registration form for everyone.")
        st.info(f"To confirm deletion, enter agreement ID: {selected_id}")
        confirmation_id = st.text_input(
            "Agreement ID confirmation",
            key="tgt_delete_disclaimer_confirmation",
            placeholder=f"Enter {selected_id}",
        )
        if st.button("Delete Agreement", key="tgt_delete_disclaimer", type="primary"):
            if confirmation_id.strip() != str(selected_id):
                st.error("The agreement ID does not match. Agreement was not deleted.")
            else:
                cursor.execute(
                    "DELETE FROM event_registration_disclaimers WHERE id=%s AND program_id=%s",
                    (selected_id, program_id),
                )
                conn.commit()
                st.success("Agreement deleted successfully.")
                st.rerun()
    elif management_view == "Event Description":
        with st.form("tgt_edit_description_form"):
            edited_description = st.text_area(
                "Event description",
                value=description or "",
                height=160,
            )
            if st.form_submit_button("Save Event Description", type="primary"):
                clean_description = edited_description.strip()
                if not clean_description:
                    st.error("Event description cannot be empty.")
                else:
                    cursor.execute(
                        "UPDATE event_registration_programs SET description=%s WHERE id=%s",
                        (clean_description, program_id),
                    )
                    conn.commit()
                    st.success("Event description updated successfully.")
                    st.rerun()


def cultural_event_tab():
    with st.spinner("Loading cultural event details..."):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM event_registration_programs WHERE slug=%s AND active=TRUE",
            ("terrazzo-ganesha-events-2026",),
        )
        program_row = cursor.fetchone()
        if program_row is None:
            st.warning("Registration is currently unavailable.")
            return
        program_id = program_row[0]
        cursor.execute(
            "SELECT title, event_date, event_time, location, description FROM event_registration_programs WHERE id=%s AND active=TRUE",
            (program_id,),
        )
        program = cursor.fetchone()
        cursor.execute(
            "SELECT id, sort_order, disclaimer_text, is_required FROM event_registration_disclaimers WHERE program_id=%s ORDER BY sort_order, id",
            (program_id,),
        )
        disclaimers = cursor.fetchall()
        cursor.execute(
            "SELECT id, participant_name, age_group, performance_type, apartment_numbers, created_by, modified_by, modified_at, deleted_by, deleted_at, status FROM event_registrations WHERE program_id=%s AND COALESCE(status, 'active')='active' ORDER BY LOWER(participant_name), id",
            (program_id,),
        )
        registrations = cursor.fetchall()
        display_registrations = _merge_display_registrations(registrations)

    if program is None:
        st.warning("Registration is currently unavailable.")
        return

    title, event_date, event_time, location, description = program
    if description and description.startswith("Traditional Fashion Show and Terrazzo Got Talent registration."):
        description = TGT_EVENT_NOTE
    is_admin = st.session_state.get("admin_logged_in", False)
    st.markdown(CULTURAL_EVENT_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <section class="cultural-hero">
            <div class="cultural-kicker">Terrazzo Ganesha Celebrations 2026</div>
            <div class="cultural-title">{title}</div>
            <div class="cultural-meta">
                <span class="cultural-meta-item">Date: {event_date.strftime('%A, %d %B %Y')}</span>
                <span class="cultural-meta-item">Time: {event_time}</span>
                <span class="cultural-meta-item">Location: {location}</span>
            </div>
            <div class="cultural-note"><strong>Note:</strong> {html.escape(str(description or ''))}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("admin_logged_in", False):
        admin_submenu = option_menu(
            None,
            ["Manage Agreements", "Registration"],
            icons=["file-earmark-text", "person-plus"],
            default_index=1,
            orientation="horizontal",
            key="cultural_event_admin_submenu",
            styles={
                "container": {"padding": "0.25rem", "background": "#fffaf0", "border": "1px solid #eadcc6", "border-radius": "12px"},
                "icon": {"color": "#a64b12", "font-size": "0.95rem"},
                "nav-link": {"font-size": "0.82rem", "font-weight": "700", "color": "#6d625b"},
                "nav-link-selected": {"background": "#6a1b1b", "color": "#ffffff"},
            },
        )
        if admin_submenu == "Manage Agreements":
            _manage_tgt_disclaimers(conn, cursor, program_id, disclaimers, description)
            return

    admin_participant_action = st.session_state.get("tgt_participant_action", "Participating details")
    if st.session_state.get("admin_logged_in", False):
        action_labels = [
            ("Participating details", "tgt_participant_details_button"),
            ("Add", "tgt_participant_add_button"),
            ("Edit", "tgt_participant_edit_button"),
            ("Delete", "tgt_participant_delete_button"),
        ]
        with st.container(horizontal=True, wrap=False, vertical_alignment="center", gap="small"):
            for action_label, action_key in action_labels:
                if st.button(action_label, key=action_key, width="stretch"):
                    st.session_state.tgt_participant_action = action_label
                    st.rerun()

    if admin_participant_action in {"Edit", "Delete"}:
        if not registrations:
            st.info("No participating details are available.")
            return
        registration_options = {
            registration_id: name
            for registration_id, name, _, _, _, *_ in registrations
        }
        selected_registration_id = st.selectbox(
            "Select participant",
            list(registration_options),
            format_func=lambda registration_id: registration_options[registration_id],
            key="tgt_selected_registration",
        )
        selected_registration = next(
            registration for registration in registrations if registration[0] == selected_registration_id
        )

        if admin_participant_action == "Edit":
            with st.form("tgt_edit_registration_form"):
                edited_name = st.text_input("Participant Name/Group Participants Names", value=selected_registration[1])
                edited_age = st.text_input("Age/Age Group", value=selected_registration[2])
                edited_performance = st.multiselect(
                    "What are you performing?",
                    TGT_PERFORMANCE_OPTIONS,
                    default=_registration_performances(selected_registration[3]),
                )
                edited_apartment = st.text_input("Apartment Number(s)", value=selected_registration[4])
                if st.form_submit_button("Save Participant", type="primary"):
                    edited_values = [edited_name.strip(), edited_age.strip(), edited_apartment.strip()]
                    if not all(edited_values):
                        st.error("Please complete all participant fields.")
                    else:
                        cursor.execute(
                            "UPDATE event_registrations SET participant_name=%s, age_group=%s, performance_type=%s, apartment_numbers=%s, modified_by=%s, modified_at=CURRENT_TIMESTAMP WHERE id=%s AND program_id=%s",
                            (*edited_values[:2], ", ".join(edited_performance), edited_values[2], st.session_state.get("admin_full_name", "Admin"), selected_registration_id, program_id),
                        )
                        conn.commit()
                        st.success("Participant updated successfully.")
                        st.rerun()
        else:
            st.warning(f"This will remove {selected_registration[1]} from the participating details.")
            confirmation_name = st.text_input(
                "Type the participant name to confirm deletion",
                key="tgt_delete_registration_confirmation",
            )
            if st.button("Delete Participant", key="tgt_delete_registration", type="primary"):
                if confirmation_name.strip() != str(selected_registration[1]).strip():
                    st.error("Please type the participant name exactly to confirm deletion.")
                else:
                    admin_name = st.session_state.get("admin_full_name", "Admin")
                    cursor.execute(
                        "UPDATE event_registrations SET status='deleted', deleted_by=%s, deleted_at=CURRENT_TIMESTAMP, modified_by=%s, modified_at=CURRENT_TIMESTAMP WHERE id=%s AND program_id=%s",
                        (admin_name, admin_name, selected_registration_id, program_id),
                    )
                    conn.commit()
                    st.success("Participant deleted successfully.")
                    st.session_state.tgt_participant_action = "Participating details"
                    st.rerun()
        return

    show_registration_form = st.session_state.get("cultural_event_show_form", False)
    if admin_participant_action == "Add":
        show_registration_form = True

    if not show_registration_form:
        with st.container(horizontal=True, wrap=False, vertical_alignment="center", gap="small"):
            st.markdown('<div class="cultural-inline-label">Participating details</div>', unsafe_allow_html=True)
            if not st.session_state.get("admin_logged_in", False):
                if st.button("✨ Click here to add registration ✨", key="tgt_add_registration", type="primary", width="content"):
                    st.session_state.cultural_event_show_form = True
                    st.rerun()
        if registrations:
            with st.container(horizontal=True, wrap=False, vertical_alignment="center", gap="small"):
                st.markdown('<div class="cultural-filter-label">Filter by performance</div>', unsafe_allow_html=True)
                performance_filter = st.selectbox(
                    "Filter by performance",
                    ["All"] + TGT_PERFORMANCE_OPTIONS,
                    format_func=lambda option: "All performances" if option == "All" else TGT_PERFORMANCE_DISPLAY.get(option, option),
                    label_visibility="collapsed",
                    key="tgt_performance_filter",
                )
                download_placeholder = st.empty()
            display_registrations = _merge_display_registrations(registrations, performance_filter)
            performance_counts = {performance: 0 for performance in TGT_PERFORMANCE_OPTIONS}
            for registration in display_registrations:
                for performance in _registration_performances(registration[3]):
                    if performance in performance_counts:
                        performance_counts[performance] += 1
            stats_performances = (
                TGT_PERFORMANCE_OPTIONS
                if performance_filter == "All"
                else [performance_filter]
            )
            stats_items = [("Total Participants / Groups", len(display_registrations))] + [
                (TGT_PERFORMANCE_DISPLAY.get(performance, performance), performance_counts[performance])
                for performance in stats_performances
            ]
            stats_html = "".join(
                f'<div class="cultural-performance-stat"><span class="cultural-performance-stat-label">{html.escape(label)}</span><span class="cultural-performance-stat-count">{count}<span class="cultural-performance-stat-unit">Participant / Group</span></span></div>'
                for label, count in stats_items
            )
            st.markdown(
                f'<div class="cultural-performance-stats">{stats_html}</div>',
                unsafe_allow_html=True,
            )
            if not display_registrations:
                st.info("No participants match the selected performance.")
                return
            if st.session_state.get("admin_logged_in", False):
                export_frame = pd.DataFrame(
                    [
                        {
                            "Participant / Group": name,
                            "Age Group": age_group,
                            "Performance": _format_performances(performance_type),
                            "Apartment Number(s)": apartment_numbers,
                            "Created By": created_by or "",
                            "Last Modified By": modified_by or "",
                            "Last Modified At": str(modified_at or ""),
                        }
                        for _, name, age_group, performance_type, apartment_numbers, created_by, modified_by, modified_at, _, _, _ in display_registrations
                    ]
                )
                export_buffer = BytesIO()
                with pd.ExcelWriter(export_buffer, engine="xlsxwriter") as writer:
                    export_frame.to_excel(writer, index=False, sheet_name="Participants")
                    worksheet = writer.sheets["Participants"]
                    worksheet.set_column("A:A", 30)
                    worksheet.set_column("B:B", 14)
                    worksheet.set_column("C:C", 24)
                    worksheet.set_column("D:D", 20)
                    worksheet.set_column("E:G", 22)
                with download_placeholder.container():
                    st.download_button(
                        "",
                        data=export_buffer.getvalue(),
                        file_name="cultural_event_participants.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_cultural_event_participants",
                        help="Download participation details as an XLSX file",
                        icon=":material/download:",
                    )
            if st.session_state.get("admin_logged_in", False):
                table_headers = "<th>Participant / Group</th><th>Age Group</th><th>Performance</th><th>Created By</th><th>Last Modified By</th><th>Last Modified At</th><th>Apartment Number(s)</th>"
                table_rows = "".join(
                    f"<tr><td>{html.escape(str(name))}</td><td>{html.escape(str(age_group))}</td><td>{html.escape(str(performance_type))}</td><td>{html.escape(str(created_by or ''))}</td><td>{html.escape(str(modified_by or ''))}</td><td>{html.escape(str(modified_at or ''))}</td><td>{html.escape(str(apartment_numbers))}</td></tr>"
                    for _, name, age_group, performance_type, apartment_numbers, created_by, modified_by, modified_at, _, _, _ in display_registrations
                )
            else:
                table_headers = "<th>Participant / Group</th><th>Age Group</th><th>Performance</th><th>Apartment Number(s)</th>"
                table_rows = "".join(
                    f"<tr><td>{html.escape(str(name))}</td><td>{html.escape(str(age_group))}</td><td>{html.escape(str(performance_type))}</td><td>{html.escape(str(apartment_numbers))}</td></tr>"
                    for _, name, age_group, performance_type, apartment_numbers, *_ in display_registrations
                )
            st.markdown(
                f"""
                <table class="cultural-order-table">
                    <thead><tr>{table_headers}</tr></thead>
                    <tbody>{table_rows}</tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="cultural-order-empty"><span>🌿</span><span>Participating details will appear here after registrations are received.</span></div>',
                unsafe_allow_html=True,
            )
        return

    st.markdown(
        '<div class="cultural-form-header">Registration details and acknowledgements</div>',
        unsafe_allow_html=True,
    )

    with st.form("tgt_registration_form"):
        st.markdown('<span class="cultural-form-marker"></span>', unsafe_allow_html=True)
        st.markdown('<div class="cultural-section-heading">Participant details</div>', unsafe_allow_html=True)
        participant_name = st.text_input("Participant Name/Group Participants Names")
        age_group = st.text_input(
            "Age/Age Group (example: 30 or 30-40)",
            placeholder="Enter age or age range, e.g. 30 or 30-40",
        )
        performance_type = st.multiselect("What are you performing?", TGT_PERFORMANCE_OPTIONS)
        apartment_numbers = st.text_input("Apartment Number(s)")

        st.markdown('<div class="cultural-section-heading">Important requests</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="cultural-section-note">All acknowledgement boxes below are required before submitting the registration.</div>',
            unsafe_allow_html=True,
        )
        agreements = []
        for index, (disclaimer_id, _, disclaimer, is_required) in enumerate(disclaimers, start=1):
            agreement = st.checkbox(
                f"{index}. {disclaimer}",
                key=f"tgt_disclaimer_agreement_{program_id}_{disclaimer_id}",
            )
            agreements.append((is_required, agreement))

        validation_message = st.empty()
        submitted = st.form_submit_button("Submit Registration")

    if submitted:
        required_values = {
            "Participant Name/Group Participants Names": participant_name.strip(),
            "Apartment Number(s)": apartment_numbers.strip(),
        }
        missing_fields = [label for label, value in required_values.items() if not value]
        if not performance_type:
            missing_fields.append("Performance")
        normalized_age_group = re.sub(r"\s+", "", age_group.strip())
        age_format_is_valid = bool(re.fullmatch(r"\d{1,3}(?:-\d{1,3})?", normalized_age_group))
        age_range_is_valid = True
        if age_format_is_valid and "-" in normalized_age_group:
            start_age, end_age = (int(value) for value in normalized_age_group.split("-"))
            age_range_is_valid = start_age <= end_age
        if not normalized_age_group:
            missing_fields.append("Age/Age Group")
        elif not age_format_is_valid or not age_range_is_valid:
            validation_message.error("Age/Age Group must be a number or range such as 30 or 30-40.")
        missing_agreements = any(
            is_required and not agreement for is_required, agreement in agreements
        )
        if missing_fields:
            validation_message.error(
                "Please complete these required fields: " + ", ".join(missing_fields) + "."
            )
        if missing_agreements:
            validation_message.error(
                "Please read and check every acknowledgement box before submitting your registration."
            )
        if not missing_fields and age_format_is_valid and age_range_is_valid and not missing_agreements:
            try:
                cursor.execute(
                    "INSERT INTO event_registrations (program_id, participant_name, age_group, performance_type, apartment_numbers, created_by, status) VALUES (%s, %s, %s, %s, %s, %s, 'active')",
                    (program_id, participant_name.strip(), age_group.strip(), ", ".join(performance_type), apartment_numbers.strip(), st.session_state.get("admin_full_name", "Public registration")),
                )
                conn.commit()
                st.session_state.cultural_event_show_form = False
                if st.session_state.get("admin_logged_in", False):
                    st.session_state.tgt_participant_action = "Participating details"
                for disclaimer_id, _, _, _ in disclaimers:
                    st.session_state.pop(
                        f"tgt_disclaimer_agreement_{program_id}_{disclaimer_id}",
                        None,
                    )
                st.rerun()
            except Exception as exc:
                conn.rollback()
                st.error(f"Registration could not be submitted: {exc}")
