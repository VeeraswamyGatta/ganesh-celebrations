import streamlit as st

# Custom button styles for events section
st.markdown('''
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
    .stButton > button {
        background-color: #2E7D32 !important;
        color: #fff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        margin-bottom: 0.5em;
    }
    .stButton > button:hover {
        background-color: #388e3c !important;
        color: #fff !important;
    }
    </style>
''', unsafe_allow_html=True)
import pandas as pd
import datetime
from .db import get_connection

def events_tab():
    st.session_state['active_tab'] = 'Events'
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
        tab_add, tab_active, tab_past, tab_edit = st.tabs(["Add Event", "Active Events", "Past Events", "Edit/Delete Event"])

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
