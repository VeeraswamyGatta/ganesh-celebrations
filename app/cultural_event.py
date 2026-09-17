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
.cultural-section-heading {
    margin: 1.15rem 0 0.55rem;
    color: #4e2922;
    font-size: 1.35rem;
    font-weight: 900;
}
.cultural-section-note {
    margin-bottom: 0.7rem;
    color: #b42318;
    font-size: 0.9rem;
    font-weight: 800;
}
.cultural-order-table {
    width: 100%;
    margin: 0.35rem 0 1rem;
    border-collapse: separate;
    border-spacing: 0 0.45rem;
    font-family: "Trebuchet MS", Georgia, serif;
}
.cultural-order-table th {
    padding: 0.65rem 0.75rem;
    background: #6a1b1b;
    color: #fffaf0;
    font-size: 0.8rem;
    letter-spacing: 0.02em;
    text-align: left;
    text-transform: none;
}
.cultural-order-table th:first-child { border-radius: 9px 0 0 9px; }
.cultural-order-table th:last-child { border-radius: 0 9px 9px 0; }
.cultural-order-table td {
    padding: 0.72rem 0.75rem;
    border-top: 1px solid #eadcc6;
    border-bottom: 1px solid #eadcc6;
    background: #fffdf8;
    color: #493a35;
    font-size: 0.92rem;
}
.cultural-order-table td:first-child {
    border-left: 1px solid #eadcc6;
    color: #a64b12;
    font-weight: 900;
}
.cultural-order-table td:last-child { border-right: 1px solid #eadcc6; }
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
    border: 0 !important;
    border-radius: 10px !important;
    background: linear-gradient(135deg, #9d2738 0%, #6a1b1b 100%) !important;
    color: #fff !important;
    font-weight: 800 !important;
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
    padding: 0.55rem 1.15rem 1.15rem;
    border: 1px solid #eadcc6;
    border-radius: 16px;
    background: linear-gradient(180deg, #fffefb 0%, #f7f1e9 100%);
    box-shadow: 0 8px 20px rgba(105, 76, 52, 0.08);
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

TGT_DEFAULT_DISCLAIMERS = [
    "Registration is mandatory. Participation is allowed only for registered participants; spot participation is not allowed.",
    "If your performance requires an audio track, send the audio file with the participant name to Purna (7209007378) via WhatsApp only.",
    "Due to technical limitations, songs cannot be played directly from YouTube or another online source. Only audio files shared with the organizers in advance will be played.",
    "The organizers will announce the performance sequence at the event based on available time and event circumstances.",
    "Parents and participants must not insist that children perform first or pressure the organizers at the performance area.",
    "Only parents or guardians of children aged 3-6 years may accompany them in the performance area. Parents of children in other age groups must remain in the audience area.",
    "Because this event is part of the Lord Ganesha celebrations, only devotional songs are permitted. Film songs are not permitted.",
    "I have read and agree to all of the above registration requirements.",
]


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
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS created_by TEXT")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS modified_by TEXT")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS modified_at TIMESTAMP")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS deleted_by TEXT")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP")
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active'")

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
                "Traditional Fashion Show and Terrazzo Got Talent registration. The program begins after the completion of Lord Ganesha Evening Pooja.",
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
    return program_id


def _manage_tgt_disclaimers(conn, cursor, program_id, disclaimers, description):
    st.markdown('<div class="cultural-section-heading">Agreement management</div>', unsafe_allow_html=True)
    if disclaimers:
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
    else:
        st.info("No agreement points have been added yet.")

    management_view = option_menu(
        "Agreement actions",
        ["Add", "Edit", "Delete", "Event Description"],
        icons=["plus-circle", "pencil-square", "trash", "file-text"],
        menu_icon="list-ul",
        default_index=0,
        orientation="horizontal",
        key="tgt_agreement_management_view",
        styles={
            "container": {"padding": "0.25rem", "background": "#fffaf0", "border": "1px solid #eadcc6", "border-radius": "12px"},
            "icon": {"color": "#a64b12", "font-size": "0.95rem"},
            "nav-link": {"font-size": "0.82rem", "font-weight": "700", "color": "#6d625b"},
            "nav-link-selected": {"background": "#6a1b1b", "color": "#ffffff"},
        },
    )

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
        if st.button("Delete Agreement", key="tgt_delete_disclaimer", type="primary"):
            cursor.execute(
                "DELETE FROM event_registration_disclaimers WHERE id=%s AND program_id=%s",
                (selected_id, program_id),
            )
            conn.commit()
            st.success("Agreement deleted successfully.")
            st.rerun()
    else:
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
    conn = get_connection()
    cursor = conn.cursor()
    try:
        program_id = _ensure_tgt_registration_tables(cursor)
        conn.commit()
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
            "SELECT id, participant_name, age_group, performance_type, apartment_numbers, created_by, modified_by, modified_at, deleted_by, deleted_at, status FROM event_registrations WHERE program_id=%s AND COALESCE(status, 'active')='active' ORDER BY id",
            (program_id,),
        )
        registrations = cursor.fetchall()
    except Exception:
        conn.rollback()
        raise

    if program is None:
        st.warning("Registration is currently unavailable.")
        return

    title, event_date, event_time, location, description = program
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
        </section>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("admin_logged_in", False):
        admin_submenu = option_menu(
            None,
            ["Manage Agreements", "Registration"],
            icons=["file-earmark-text", "person-plus"],
            default_index=0,
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
            st.markdown(
                f'<div class="cultural-description"><strong>About this event</strong><br>{html.escape(str(description or ""))}</div>',
                unsafe_allow_html=True,
            )
            _manage_tgt_disclaimers(conn, cursor, program_id, disclaimers, description)
            return

    if not is_admin:
        st.markdown(
            f'<div class="cultural-description"><strong>About this event</strong><br>{html.escape(str(description or ""))}</div>',
            unsafe_allow_html=True,
        )

    admin_participant_action = st.session_state.get("tgt_participant_action", "Participating details")
    if st.session_state.get("admin_logged_in", False):
        action_columns = st.columns(4)
        action_labels = [
            ("Participating details", "tgt_participant_details_button"),
            ("Add", "tgt_participant_add_button"),
            ("Edit", "tgt_participant_edit_button"),
            ("Delete", "tgt_participant_delete_button"),
        ]
        for action_column, (action_label, action_key) in zip(action_columns, action_labels):
            with action_column:
                if st.button(action_label, key=action_key, use_container_width=True):
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
                edited_performance = st.selectbox(
                    "What are you performing?",
                    TGT_PERFORMANCE_OPTIONS,
                    index=TGT_PERFORMANCE_OPTIONS.index(selected_registration[3])
                    if selected_registration[3] in TGT_PERFORMANCE_OPTIONS else 0,
                )
                edited_apartment = st.text_input("Apartment Number(s)", value=selected_registration[4])
                if st.form_submit_button("Save Participant", type="primary"):
                    edited_values = [edited_name.strip(), edited_age.strip(), edited_apartment.strip()]
                    if not all(edited_values):
                        st.error("Please complete all participant fields.")
                    else:
                        cursor.execute(
                            "UPDATE event_registrations SET participant_name=%s, age_group=%s, performance_type=%s, apartment_numbers=%s, modified_by=%s, modified_at=CURRENT_TIMESTAMP WHERE id=%s AND program_id=%s",
                            (*edited_values[:2], edited_performance, edited_values[2], st.session_state.get("admin_full_name", "Admin"), selected_registration_id, program_id),
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
        if not st.session_state.get("admin_logged_in", False):
            if st.button("Add Registration", key="tgt_add_registration", use_container_width=True, type="primary"):
                st.session_state.cultural_event_show_form = True
                st.rerun()

        st.markdown('<div class="cultural-section-heading">Participating details</div>', unsafe_allow_html=True)
        if registrations:
            if st.session_state.get("admin_logged_in", False):
                export_frame = pd.DataFrame(
                    [
                        {
                            "Participant / Group": name,
                            "Age Group": age_group,
                            "Performance": performance_type,
                            "Apartment Number(s)": apartment_numbers,
                            "Created By": created_by or "",
                            "Last Modified By": modified_by or "",
                            "Last Modified At": str(modified_at or ""),
                        }
                        for _, name, age_group, performance_type, apartment_numbers, created_by, modified_by, modified_at, _, _, _ in registrations
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
                st.download_button(
                    "Download Participating Details (XLSX)",
                    data=export_buffer.getvalue(),
                    file_name="cultural_event_participants.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_cultural_event_participants",
                    use_container_width=True,
                )
            if st.session_state.get("admin_logged_in", False):
                table_headers = "<th>Participant / Group</th><th>Age Group</th><th>Performance</th><th>Created By</th><th>Last Modified By</th><th>Last Modified At</th>"
                table_rows = "".join(
                    f"<tr><td>{html.escape(str(name))}</td><td>{html.escape(str(age_group))}</td><td>{html.escape(str(performance_type))}</td><td>{html.escape(str(created_by or ''))}</td><td>{html.escape(str(modified_by or ''))}</td><td>{html.escape(str(modified_at or ''))}</td></tr>"
                    for _, name, age_group, performance_type, _, created_by, modified_by, modified_at, _, _, _ in registrations
                )
            else:
                table_headers = "<th>Participant / Group</th><th>Age Group</th><th>Performance</th>"
                table_rows = "".join(
                    f"<tr><td>{html.escape(str(name))}</td><td>{html.escape(str(age_group))}</td><td>{html.escape(str(performance_type))}</td></tr>"
                    for _, name, age_group, performance_type, *_ in registrations
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
        st.markdown(
            '<div class="cultural-attention-note"><span class="cultural-attention-title">A kind request before you register</span><br>Please take a moment to read each point carefully and check every acknowledgement box. Your cooperation helps us conduct the program smoothly and respectfully.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="cultural-section-heading">Important requests</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="cultural-section-note">Each acknowledgement is required before submitting the registration.</div>',
            unsafe_allow_html=True,
        )
        agreements = []
        for index, (disclaimer_id, _, disclaimer, is_required) in enumerate(disclaimers, start=1):
            agreement = st.checkbox(
                f"{index}. {disclaimer}",
                key=f"tgt_disclaimer_agreement_{program_id}_{disclaimer_id}",
            )
            agreements.append((is_required, agreement))

        st.markdown('<div class="cultural-section-heading">Participant details</div>', unsafe_allow_html=True)
        participant_name = st.text_input("Participant Name/Group Participants Names")
        age_group = st.text_input(
            "Age/Age Group (example: 30 or 30-40)",
            placeholder="Enter age or age range, e.g. 30 or 30-40",
        )
        performance_type = st.selectbox("What are you performing?", TGT_PERFORMANCE_OPTIONS)
        apartment_numbers = st.text_input("Apartment Number(s)")
        validation_message = st.empty()
        submitted = st.form_submit_button("Submit Registration")

    if submitted:
        required_values = {
            "Participant Name/Group Participants Names": participant_name.strip(),
            "Apartment Number(s)": apartment_numbers.strip(),
        }
        missing_fields = [label for label, value in required_values.items() if not value]
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
                    (program_id, participant_name.strip(), age_group.strip(), performance_type, apartment_numbers.strip(), st.session_state.get("admin_full_name", "Public registration")),
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
