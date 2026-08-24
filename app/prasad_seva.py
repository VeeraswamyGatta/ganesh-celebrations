import streamlit as st
import pandas as pd
import datetime
import pytz
from datetime import datetime as dt, time as dttime
from .db import get_connection
from .email_utils import send_email

def prasad_seva_tab():
    laddu_winners_option = "Laddu Auction Winners"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT laddu_number, winner_name, amount FROM laddu_winners ORDER BY laddu_number ASC LIMIT 3")
    laddu_winners = [
        {"laddu": row[0], "name": row[1], "amount": row[2]} for row in cursor.fetchall()
    ]
    is_admin = st.session_state.get("admin_logged_in", False)
    # Define tab_names for admin/non-admin
    if is_admin:
        tab_names = [
            "Add Prasad Seva",
            "Edit/Delete Prasad Seva Entry",
            "Prasad Seva Summary",
            "Prasad Seva Sponsors List",
            "Total Served by Name/Group"
        ]
    else:
        tab_names = [
            "Add Prasad Seva",
            "Prasad Seva Summary",
            "Prasad Seva Sponsors List",
            "Total Served by Name/Group"
        ]
    # Prepend Laddu Auction Winners as default option
    tab_names = [laddu_winners_option] + tab_names
    selected_tab = st.selectbox("Select Section", tab_names, index=tab_names.index("Add Prasad Seva"))

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
        st.session_state["prasad_group_names"] = ""
        st.session_state["prasad_group_items"] = ""
        st.session_state["prasad_group_apartment"] = ""
        st.session_state["prasad_individual_name"] = ""
        st.session_state["prasad_individual_apartment"] = ""
        st.session_state["prasad_num_people"] = 1
        min_date = datetime.date(2026, 9, 14)
        st.session_state["prasad_seva_date"] = min_date
        st.session_state["prasad_pooja_time"] = "Evening Pooja"
        st.session_state["prasad_filter_date"] = None
        st.session_state["prasad_filter_name"] = ""
        st.session_state["clear_prasad_form"] = False
        st.rerun()
    # ...existing code...

    if selected_tab == "Add Prasad Seva":
        st.markdown("### ➕ Add Prasad Seva")
        prasad_form = st.form("add_prasad_seva_form")
        prasad_submit_disabled = st.session_state.get("prasad_submission_in_progress", False)
        seva_type = prasad_form.radio("Type", ["Group", "Individual"], horizontal=True, key="prasad_seva_type_tab0")
        names = []
        item_names = []
        if seva_type == "Group":
            names_str = prasad_form.text_area("Enter Names (comma separated)", key="prasad_group_names", placeholder="e.g. FullName1, FullName2, FullName3")
            names = [n.strip() for n in names_str.split(',') if n.strip()]
            items_str = prasad_form.text_area("Enter Item Names (comma separated)", key="prasad_group_items", placeholder="e.g. Pulihora, Kheer/Payasam, Modak, Puran Poli")
            item_names = [i.strip() for i in items_str.split(',') if i.strip()]
            apartment = prasad_form.text_input("Apartment Number", key="prasad_group_apartment", placeholder="e.g. 323")
        else:
            name = prasad_form.text_input("Name", key="prasad_individual_name", placeholder="e.g. Full Name")
            names = [name.strip()] if name.strip() else []
            item_name = prasad_form.text_input("Item Name", placeholder="e.g. Modak")
            item_names = [item_name.strip()] if item_name.strip() else []
            apartment = prasad_form.text_input("Apartment Number", key="prasad_individual_apartment", placeholder="e.g. 1203")

        num_people = prasad_form.number_input("How many people are you bringing item for?", min_value=1, value=st.session_state.get('prasad_num_people', 1), key="prasad_num_people")
        min_date = datetime.date(2026, 9, 14)
        selected_date = st.session_state.get("prasad_seva_date", min_date)
        if selected_date < min_date:
            selected_date = min_date
            st.session_state["prasad_seva_date"] = selected_date
        seva_date = prasad_form.date_input(
            "Date",
            value=selected_date,
            min_value=min_date,
            key="prasad_seva_date"
        )
        pooja_options = ["Morning Pooja", "Evening Pooja"]
        if seva_date == datetime.date(2026, 9, 14):
            pooja_options = ["Evening Pooja"]
        pooja_time = prasad_form.radio("Pooja Time", pooja_options, horizontal=True, key="prasad_pooja_time")

        if prasad_form.form_submit_button("✅ Add Prasad Seva", disabled=prasad_submit_disabled, type="primary"):
            st.session_state["prasad_submission_in_progress"] = True
            prasad_status = st.status("Adding Prasad Seva...", expanded=False)
            if not names:
                st.session_state["prasad_submission_in_progress"] = False
                prasad_status.update(label="Please complete the required fields", state="error", expanded=True)
                st.error("Please enter at least one name.")
            elif not item_names:
                st.session_state["prasad_submission_in_progress"] = False
                prasad_status.update(label="Please complete the required fields", state="error", expanded=True)
                st.error("Please enter at least one item name.")
            elif not apartment.strip():
                st.session_state["prasad_submission_in_progress"] = False
                prasad_status.update(label="Please complete the required fields", state="error", expanded=True)
                st.error("Apartment Number is required.")
            elif not num_people:
                st.session_state["prasad_submission_in_progress"] = False
                prasad_status.update(label="Please complete the required fields", state="error", expanded=True)
                st.error("Number of people is required.")
            elif not seva_date:
                st.session_state["prasad_submission_in_progress"] = False
                prasad_status.update(label="Please complete the required fields", state="error", expanded=True)
                st.error("Date is required.")
            elif not pooja_time:
                st.session_state["prasad_submission_in_progress"] = False
                prasad_status.update(label="Please complete the required fields", state="error", expanded=True)
                st.error("Pooja Time is required.")
            else:
                st.info("Add Prasad Seva is in progress...")
                for item in item_names:
                    if hasattr(cursor, 'execute') and hasattr(cursor.connection, 'account'):
                        cursor.execute(
                            "INSERT INTO prasad_seva (seva_type, names, item_name, num_people, apartment, seva_date, pooja_time, created_by, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (seva_type, ', '.join(names), item, num_people, apartment, seva_date, pooja_time, st.session_state.get('admin_full_name', 'User'), 'active')
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO prasad_seva (seva_type, names, item_name, num_people, apartment, seva_date, pooja_time, created_by, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (seva_type, ', '.join(names), item, num_people, apartment, seva_date, pooja_time, st.session_state.get('admin_full_name', 'User'), 'active')
                        )
                conn.commit()
                submitted_info = {
                    "Type": seva_type,
                    "Names": ', '.join(names),
                    "Item Name(s)": ', '.join(item_names),
                    "Apartment": apartment,
                    "Number of People": num_people,
                    "Date": seva_date.strftime('%d-%b-%Y'),
                    "Pooja Time": pooja_time
                }
                st.session_state["prasad_last_submission"] = submitted_info
                st.session_state["prasad_submission_in_progress"] = False
                prasad_status.update(label="Prasad Seva added", state="complete", expanded=False)
                st.success("✅ Added seva successfully")
                st.session_state["clear_prasad_form"] = True
                st.rerun()

    elif selected_tab == "Prasad Seva Summary":
        cursor.execute("SELECT seva_date, pooja_time, SUM(num_people) FROM prasad_seva WHERE status='active' GROUP BY seva_date, pooja_time")
        metrics_rows = cursor.fetchall()
        min_date = datetime.date(2026, 9, 14)
        max_date = datetime.date(2026, 9, 20)
        all_dates = pd.date_range(min_date, max_date).date
        pooja_times = ["Morning Pooja", "Evening Pooja"]
        grid = pd.DataFrame([(d, p) for d in all_dates for p in pooja_times], columns=["Date", "Pooja Time"])
        metrics_df = pd.DataFrame(metrics_rows, columns=["Date", "Pooja Time", "Total People Served"])
        metrics_df["Date"] = pd.to_datetime(metrics_df["Date"]).dt.date
        merged_df = grid.merge(metrics_df, on=["Date", "Pooja Time"], how="left").fillna({"Total People Served": 0})
        merged_df["Total People Served"] = merged_df["Total People Served"].astype(int)
        merged_df = merged_df[~((merged_df["Date"] == datetime.date(2026, 9, 14)) & (merged_df["Pooja Time"] == "Morning Pooja"))]
        merged_df["Date"] = merged_df["Date"].apply(lambda d: f"<span style='font-size:16px;'>&#128197;</span> <b>{pd.to_datetime(d).strftime('%d-%b-%Y')}</b>")
        merged_df["Pooja Time"] = merged_df["Pooja Time"].apply(lambda t: f"<span style='font-size:18px;'>{'🌅' if t=='Morning Pooja' else '🌇'}</span> <b>{t.replace('Pooja','')}</b>")
        merged_df["Total People Served"] = merged_df["Total People Served"].apply(lambda x: f"<span style='background-color:#FFECB3;color:#6D4C41;padding:4px 12px;border-radius:16px;font-weight:bold;display:inline-block;text-align:center;'>{x}</span>")
        cursor.execute("SELECT SUM(num_people) FROM prasad_seva WHERE status='active'")
        total_sponsored = cursor.fetchone()[0] or 0
        st.markdown(f"<h4 style='text-align:center;color:#388E3C;background:#C8E6C9;padding:7px;border-radius:10px;margin-bottom:0.5em;font-size:1.1em;'>🎉 Total People Served Count (All Days): <span style='color:#1B5E20;'>{total_sponsored}</span></h4>", unsafe_allow_html=True)
        st.markdown(merged_df.to_html(escape=False, index=False, justify='center'), unsafe_allow_html=True)
        raw_metrics_df = merged_df.copy()
        raw_metrics_df["Date"] = pd.to_datetime(raw_metrics_df["Date"].str.extract(r'<b>(.*?)</b>')[0], format='%d-%b-%Y')
        raw_metrics_df["Pooja Time"] = raw_metrics_df["Pooja Time"].str.extract(r'<b>(.*?)</b>')[0]
        raw_metrics_df["Total People Served"] = raw_metrics_df["Total People Served"].str.extract(r'>(\d+)<')[0].fillna(0).astype(int)
        csv_summary = raw_metrics_df.to_csv(index=False)
        st.download_button(label="📥", data=csv_summary, file_name="prasad_seva_summary.csv", mime="text/csv", key="download_summary_tab1")

    elif selected_tab == "Prasad Seva Sponsors List":
        min_date = datetime.date(2026, 9, 14)
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        filter_date = filter_col1.date_input("Filter by Date", value=None, min_value=min_date, key="prasad_filter_date_tab2")
        filter_name = filter_col2.text_input("Filter by Name", value="", key="prasad_filter_name_tab2")
        pooja_time_options = ["All", "Morning Pooja", "Evening Pooja"]
        filter_pooja_time = filter_col3.selectbox("Filter by Pooja Time", pooja_time_options, key="prasad_filter_pooja_time_tab2")
        query = "SELECT id, seva_type, names, item_name, num_people, apartment, seva_date, pooja_time, created_by, status FROM prasad_seva WHERE status='active'"
        filters = []
        params = []
        if filter_date:
            filters.append("seva_date = %s")
            params.append(filter_date)
        if filter_name:
            filters.append("names ILIKE %s")
            params.append(f"%{filter_name}%")
        if filter_pooja_time != "All":
            filters.append("pooja_time = %s")
            params.append(filter_pooja_time)
        if filters:
            query += " AND " + " AND ".join(filters)
        query += " ORDER BY seva_date, CASE WHEN pooja_time='Morning Pooja' THEN 0 ELSE 1 END, names, id"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        if rows and len(rows) > 0:
            df = pd.DataFrame(rows, columns=["ID", "Type", "Names", "Item Name", "How many people are you bringing item for", "Apartemnt Number", "Date", "Pooja Time", "Created By", "Status"])
            if "Status" in df.columns:
                df = df.drop(columns=["Status"])
            # Split into active and past based on CST date
            cst = pytz.timezone('US/Central')
            now_cst = dt.now(cst)
            today_cst = now_cst.date()
            df_active = df[pd.to_datetime(df["Date"]).dt.date >= today_cst]
            df_past = df[pd.to_datetime(df["Date"]).dt.date < today_cst]
            tab1, tab2 = st.tabs(["Active", "Past"])
            for tab, df_tab, label in [(tab1, df_active, "Active"), (tab2, df_past, "Past")]:
                with tab:
                    if len(df_tab) > 0:
                        df_display = df_tab.drop(columns=["ID", "Created By"])
                        df_display["Date"] = df_display["Date"].apply(lambda d: f"<span style='font-size:16px;'>&#128197;</span> <b>{pd.to_datetime(d).strftime('%d-%b-%Y')}</b>")
                        def pooja_time_display(row):
                            if row["Date"].startswith("<span") and "14-Sep-2026" in row["Date"] and row["Pooja Time"].find("Morning") != -1:
                                return ""
                            return f"<span style='font-size:18px;'>{'🌅' if row['Pooja Time']=='Morning Pooja' else '🌇'}</span> <b>{row['Pooja Time'].replace('Pooja','')}</b>"
                        df_display["Pooja Time"] = df_display.apply(pooja_time_display, axis=1)
                        df_display["Type"] = df_display["Type"].apply(lambda t: f"<span style='background-color:{'#B2DFDB' if t=='Group' else '#FFCCBC'};color:#4E342E;padding:4px 10px;border-radius:12px;font-weight:bold;'>{'👥 Group' if t=='Group' else '🧑 Individual'}</span>")
                        df_display["Apartemnt Number"] = df_display["Apartemnt Number"].apply(lambda apt: f"<span style='font-size:16px;'>&#127968;</span> <b>{apt}</b>" if apt else "")
                        df_display["Names"] = df_display["Names"].apply(lambda n: f"<span style='font-size:16px;'>&#128100;</span> <b>{n}</b>" if n else "")
                        df_display["Item Name"] = df_display["Item Name"].apply(lambda item: f"<span style='font-size:16px;'>&#127858;</span> <b>{item}</b>" if item else "")
                        df_display["How many people are you bringing item for"] = df_display["How many people are you bringing item for"].apply(lambda x: f"<span style='background-color:#FFECB3;color:#6D4C41;padding:4px 12px;border-radius:16px;font-weight:bold;display:inline-block;text-align:center;'>{x}</span>")
                        # Sort by Date, Pooja Time (morning before evening), then Name
                        df_display["_date_sort"] = pd.to_datetime(df_tab["Date"])
                        df_display["_pooja_sort"] = df_tab["Pooja Time"].apply(lambda x: 0 if str(x).lower().find("morning") != -1 else 1)
                        df_display = df_display.sort_values(by=["_date_sort", "_pooja_sort", "Names"])
                        df_display = df_display.drop(columns=["_date_sort", "_pooja_sort"])
                        df_display.index = range(1, len(df_display) + 1)
                        st.markdown(df_display.to_html(escape=False, index=True, justify='center'), unsafe_allow_html=True)
                        raw_sponsors_df = df_tab.drop(columns=["ID", "Created By"])
                        csv_sponsors = raw_sponsors_df.to_csv(index=False)
                        st.download_button(label="📥", data=csv_sponsors, file_name=f"prasad_seva_sponsors_list_{label.lower()}.csv", mime="text/csv", key=f"download_sponsors_tab_{label.lower()}")
                        if st.session_state.get('admin_logged_in', False):
                            if st.button(f"Send Prasad Seva Details to Email ({label})"):
                                cursor.execute("SELECT email FROM notification_emails")
                                notification_emails = [row[0] for row in cursor.fetchall() if row[0]]
                                html_table = df_tab.drop(columns=["ID", "Created By"]).to_html(index=False, border=1, justify='center')
                                send_email(
                                    f"Prasad Seva Sponsors List ({label})",
                                    f"<b>Current Prasad Seva List ({label})</b><br><br>{html_table}",
                                    notification_emails
                                )
                                st.success("✅ Email sent!")
                    else:
                        st.info(f"No {label} Prasad Seva entries yet.")
        else:
            st.info("No Prasad Seva entries yet.")

    elif selected_tab == "Total Served by Name/Group":
        st.markdown("<h5 style='margin-bottom:0.2em;'>🧑👥 Total Served by Name/Group</h5>", unsafe_allow_html=True)
        cursor.execute("SELECT names, SUM(num_people) as total_served FROM prasad_seva WHERE status='active' GROUP BY names ORDER BY total_served DESC")
        name_rows = cursor.fetchall()
        if name_rows and len(name_rows) > 0:
            name_df = pd.DataFrame(name_rows, columns=["Name/Group", "Total Served"])
            name_df["Name/Group"] = name_df["Name/Group"].apply(lambda n: f"<span style='font-size:16px;'>&#128100;</span> <b>{n}</b>" if n else "")
            name_df["Total Served"] = name_df["Total Served"].apply(lambda x: f"<span style='background-color:#FFECB3;color:#6D4C41;padding:4px 12px;border-radius:16px;font-weight:bold;display:inline-block;text-align:center;'>{x}</span>")
            st.markdown(name_df.to_html(escape=False, index=False, justify='center'), unsafe_allow_html=True)
            csv_name = name_df[['Name/Group', 'Total Served']].to_csv(index=False)
            st.download_button(label="📥", data=csv_name, file_name="prasad_seva_total_served_by_name.csv", mime="text/csv", key="download_total_served_tab2")
        else:
            st.info("No Prasad Seva entries yet.")

    elif selected_tab == "Edit/Delete Prasad Seva Entry":
        query = "SELECT id, seva_type, names, item_name, num_people, apartment, seva_date, pooja_time, created_by, status FROM prasad_seva WHERE status='active' ORDER BY seva_date, pooja_time, id"
        cursor.execute(query)
        rows = cursor.fetchall()
        if rows and len(rows) > 0:
            df = pd.DataFrame(rows, columns=["ID", "Type", "Names", "Item Name", "How many people are you bringing item for", "Apartemnt Number", "Date", "Pooja Time", "Created By", "Status"])
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
                action = st.radio("Action", ["Edit", "Delete"], key=f"edit_delete_action_{selected_id}")
                if action == "Edit":
                    st.markdown(f"<b>Type:</b> " + (f"<span style='background-color:#B2DFDB;color:#4E342E;padding:4px 10px;border-radius:12px;font-weight:bold;'>👥 Group</span>" if entry['Type']=='Group' else f"<span style='background-color:#FFCCBC;color:#4E342E;padding:4px 10px;border-radius:12px;font-weight:bold;'>🧑 Individual</span>"), unsafe_allow_html=True)
                    st.markdown(f"<b>Names:</b> <span style='font-size:16px;'>&#128100;</span> <b>{entry['Names']}</b>", unsafe_allow_html=True)
                    new_item = st.text_input("Item Name", value=entry["Item Name"], key=f"edit_item_{selected_id}")
                    new_num = st.number_input("How many people are you bringing item for?", min_value=1, value=int(entry["How many people are you bringing item for"]), key=f"edit_num_{selected_id}")
                    st.markdown(f"<b>Apartment Number:</b> <span style='font-size:16px;'>&#127968;</span> <b>{entry['Apartemnt Number']}</b>", unsafe_allow_html=True)
                    min_date = datetime.date(2026, 9, 14)
                    current_date = pd.to_datetime(entry["Date"]).date() if pd.notna(entry["Date"]) else min_date
                    new_date = st.date_input("Date", value=current_date, min_value=min_date, key=f"edit_prasad_date_{selected_id}")
                    pooja_options = ["Morning Pooja", "Evening Pooja"]
                    if new_date == datetime.date(2026, 9, 14):
                        pooja_options = ["Evening Pooja"]
                    if entry["Pooja Time"] in pooja_options:
                        pooja_index = pooja_options.index(entry["Pooja Time"])
                    else:
                        pooja_index = 0
                    new_pooja_time = st.radio("Pooja Time", pooja_options, index=pooja_index, key=f"edit_prasad_time_{selected_id}")
                    if st.button("Update Prasad Seva", key=f"update_prasad_{selected_id}"):
                        cursor.execute(
                            "UPDATE prasad_seva SET seva_type=%s, names=%s, item_name=%s, num_people=%s, apartment=%s, seva_date=%s, pooja_time=%s, status=%s WHERE id=%s",
                            (entry["Type"], entry["Names"], new_item, new_num, entry["Apartemnt Number"], new_date, new_pooja_time, 'active', selected_id)
                        )
                        conn.commit()
                        st.success("✅ Updated!")
                        st.rerun()
                elif action == "Delete":
                    entered_name = st.text_input(f"Type the name to confirm deletion ({entry['Names']})", key=f"delete_name_{selected_id}")
                    confirm_message = f"Type <b>{entry['Names']}</b> above and click Delete to confirm."
                    st.markdown(confirm_message, unsafe_allow_html=True)
                    if st.button("Delete Prasad Seva", key=f"delete_prasad_{selected_id}"):
                        if entered_name.strip() == entry['Names']:
                            cursor.execute("UPDATE prasad_seva SET status='inactive' WHERE id=%s", (selected_id,))
                            conn.commit()
                            st.success("🗑️ Deleted!")
                            st.rerun()
                        else:
                            st.warning(f"Please type the exact name '{entry['Names']}' to confirm deletion.")
        else:
            st.info("No Prasad Seva entries available to edit or delete.")

    st.markdown("---")
