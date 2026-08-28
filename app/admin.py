import streamlit as st
TABLE_HEADER_STYLE = "background-color:#6A1B9A;color:#fff;text-transform:capitalize;"

# Custom button styles for admin section
st.markdown('''
    <style>
    .stButton > button {
        background-color: #6A1B9A !important;
        color: #fff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        margin-bottom: 0.5em;
    }
    .stButton > button:hover {
        background-color: #8e24aa !important;
        color: #fff !important;
    }
    </style>
''', unsafe_allow_html=True)
import pandas as pd
import datetime
from .db import get_connection
from .email_utils import send_email
from .login_audit import ensure_login_audit_table


def ensure_sponsorship_item_image_columns(cursor):
    blob_type = "BINARY" if hasattr(cursor.connection, "account") else "BYTEA"
    cursor.execute(f"ALTER TABLE sponsorship_items ADD COLUMN IF NOT EXISTS image_blob {blob_type}")
    cursor.execute("ALTER TABLE sponsorship_items ADD COLUMN IF NOT EXISTS image_filename TEXT")

def admin_tab(menu="Sponsorship Items"):
    st.session_state['active_tab'] = 'Admin'
    conn = get_connection()
    cursor = conn.cursor()
    if menu == "User Login Activity":
        ensure_login_audit_table(conn)
        st.markdown("<h2 style='color: #6A1B9A;'>User Login Activity</h2>", unsafe_allow_html=True)

        today = datetime.date.today()
        filter_start, filter_end = st.columns(2)
        start_date = filter_start.date_input("Start Date", value=today - datetime.timedelta(days=9), key="login_activity_start")
        end_date = filter_end.date_input("End Date", value=today, key="login_activity_end")
        if start_date > end_date:
            st.error("Start Date must be on or before End Date.")
            return

        active_cutoff = datetime.datetime.now() - datetime.timedelta(minutes=10)
        cursor.execute(
            """
            SELECT COUNT(DISTINCT session_id)
            FROM user_login_audit
            WHERE logout_at IS NULL AND last_activity_at >= %s
            """,
            (active_cutoff,),
        )
        active_users = cursor.fetchone()[0] or 0
        st.metric("Active Users (last 10 minutes)", active_users)

        login_counts = pd.read_sql(
            """
            SELECT CAST(login_at AS DATE) AS login_date, COUNT(*) AS login_count
            FROM user_login_audit
            WHERE CAST(login_at AS DATE) BETWEEN %s AND %s
            GROUP BY CAST(login_at AS DATE)
            ORDER BY login_date
            """,
            conn,
            params=(start_date, end_date),
        )
        login_counts.columns = [str(column).lower() for column in login_counts.columns]
        if login_counts.empty:
            login_counts = pd.DataFrame(columns=["login_date", "login_count"])
        all_dates = pd.DataFrame({"login_date": pd.date_range(start_date, end_date)})
        login_counts["login_date"] = pd.to_datetime(login_counts["login_date"])
        login_counts = all_dates.merge(login_counts, on="login_date", how="left").fillna({"login_count": 0})
        login_counts["login_count"] = login_counts["login_count"].astype(int)
        st.bar_chart(login_counts.set_index("login_date"), y="login_count")

        audit_df = pd.read_sql(
            """
            SELECT user_role, username, ip_address, user_agent, login_at, last_activity_at, logout_at
            FROM user_login_audit
            WHERE CAST(login_at AS DATE) BETWEEN %s AND %s
            ORDER BY login_at DESC
            """,
            conn,
            params=(start_date, end_date),
        )
        audit_df.columns = [str(column).lower() for column in audit_df.columns]
        if audit_df.empty:
            audit_df = pd.DataFrame(columns=[
                "user_role", "username", "ip_address", "user_agent",
                "login_at", "last_activity_at", "logout_at",
            ])
        audit_df.index = audit_df.index + 1
        st.dataframe(audit_df, use_container_width=True)
        return

    # Always show Payment Details by default and display its tabs first
    if menu == "Sponsorship Payment Details" or menu is None:
        st.markdown("<h2 style='color: #6A1B9A;'>💳 Sponsorship Payment Details</h2>", unsafe_allow_html=True)
        def get_sponsor_df():
            df = pd.read_sql("SELECT name, SUM(COALESCE(donation,0)) AS donation_sum FROM sponsors GROUP BY name", conn)
            df.columns = [c.lower() for c in df.columns]
            cursor2 = conn.cursor()
            cursor2.execute("""
                SELECT s.name, SUM(COALESCE(si.amount,0) / NULLIF(si.sponsor_limit,0))
                FROM sponsors s
                JOIN sponsorship_items si ON si.item = s.sponsorship
                GROUP BY s.name
            """)
            sponsor_amt = {row[0]: float(row[1]) for row in cursor2.fetchall()}
            df["sponsorship_sum"] = df["name"].map(sponsor_amt).fillna(0).astype(float)
            df["donation_sum"] = df["donation_sum"].astype(float)
            df["total_amount"] = df["donation_sum"] + df["sponsorship_sum"]
            return df
        sponsor_df = get_sponsor_df()
        sponsor_names = sorted(sponsor_df["name"].tolist())
        payment_tabs = ["Add Payment Detail", "Received", "Not Received", "Mismatch Records", "Delete Payment Detail"]
        tab_add, tab_received, tab_not_received, tab_mismatch, tab_delete = st.tabs(payment_tabs)

        with tab_add:
            # Add Payment Detail tab
            df_pay_names = pd.read_sql("SELECT name FROM payment_details", conn)
            df_pay_names.columns = [c.lower() for c in df_pay_names.columns]
            paid_names_set = set(df_pay_names["name"].tolist())
            unpaid_names = [n for n in sponsor_names if n not in paid_names_set]
            name_options = ["-- Select Name --"] + unpaid_names if unpaid_names else ["-- No Names Available --"]
            if 'add_pay_selected_name' not in st.session_state or st.session_state['add_pay_selected_name'] not in name_options:
                st.session_state['add_pay_selected_name'] = name_options[0]
            def update_amount():
                name = st.session_state['add_pay_selected_name']
                amt = float(sponsor_df[sponsor_df["name"] == name]["total_amount"].values[0]) if name in sponsor_names else 0.0
                st.session_state['add_pay_amount_input'] = amt
            if 'add_pay_last_selected_name' not in st.session_state:
                st.session_state['add_pay_last_selected_name'] = st.session_state['add_pay_selected_name']
            if 'add_pay_amount_input' not in st.session_state:
                update_amount()
            name = st.selectbox("Name", name_options, key="add_pay_selected_name")
            payment_type = "Cash"
            if st.session_state['add_pay_last_selected_name'] != st.session_state['add_pay_selected_name']:
                update_amount()
                st.session_state['add_pay_zelle_acc_name'] = ""
                st.session_state['add_pay_last_selected_name'] = st.session_state['add_pay_selected_name']
            default_amount = st.session_state.get('add_pay_amount_input', 0.0)
            import pytz
            with st.form("add_payment_detail_form"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"Name: **{name}**")
                    amount = st.number_input("Amount (editable)", min_value=0.0, value=default_amount, step=1.0, format="%.2f", key="add_pay_amount_input")
                    st.write("Payment Type: **Cash**")
                with col2:
                    date = st.date_input("Date", key="add_pay_date")
                    try:
                        cursor.execute("SELECT name, apartment FROM committee_members WHERE recieve_cash_enable = TRUE ORDER BY name")
                        member_names = [row[0] for row in cursor.fetchall() if row[0]]
                    except Exception:
                        member_names = []
                    cash_collector_options = ["-- Select Cash Collector --"] + member_names
                    recieved_zelle_acc_name = st.selectbox("Cash Received By", cash_collector_options, key="add_pay_zelle_acc_name")
                    comments = st.text_input("Comments", key="add_pay_comments")
                submit = st.form_submit_button("Add Payment Detail")
                if submit:
                    if name == "-- Select Name --" or name == "-- No Names Available --":
                        st.warning("Please select a name before submitting.")
                    elif recieved_zelle_acc_name == "-- Select Cash Collector --":
                        st.warning("Please select the committee member who received the cash.")
                    else:
                        try:
                            tz = pytz.timezone('America/Chicago')
                            dt_naive = datetime.datetime.combine(date, datetime.time.min)
                            dt_cst = tz.localize(dt_naive)
                            date_cst = dt_cst.date()
                            payment_columns = set(pd.read_sql("SELECT * FROM payment_details LIMIT 0", conn).columns.str.lower())
                            if "recieved_zelle_acc_name" in payment_columns:
                                cursor.execute(
                                    "INSERT INTO payment_details (name, amount, date, comments, payment_type, recieved_zelle_acc_name) VALUES (%s, %s, %s, %s, %s, %s)",
                                    (name, amount, date_cst, comments, payment_type, recieved_zelle_acc_name)
                                )
                            else:
                                cursor.execute(
                                    "INSERT INTO payment_details (name, amount, date, comments, payment_type) VALUES (%s, %s, %s, %s, %s)",
                                    (name, amount, date_cst, comments, payment_type)
                                )
                            conn.commit()
                            st.success("✅ Payment detail added!")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Failed to add payment detail: {e}")

        with tab_received:
            # Received: Payment details table
            payment_columns = pd.read_sql("SELECT * FROM payment_details LIMIT 0", conn).columns.str.lower()
            zelle_column = ", recieved_zelle_acc_name" if "recieved_zelle_acc_name" in payment_columns else ""
            df_pay = pd.read_sql(f"SELECT id, name, amount, date, payment_type{zelle_column}, comments FROM payment_details ORDER BY date DESC, id DESC", conn)
            df_pay.columns = [c.lower() for c in df_pay.columns]
            if not df_pay.empty:
                comments_filter = st.text_input("Filter by Comments (contains)", value="")
                filtered_df = df_pay.copy()
                if comments_filter:
                    filtered_df = filtered_df[filtered_df["comments"].str.contains(comments_filter, case=False, na=False)]
                display_df = filtered_df.copy()
                if 'id' in display_df.columns:
                    display_df = display_df.drop(columns=["id"])
                display_df = display_df.sort_values(by=["name"]).reset_index(drop=True)
                total_amount = display_df["amount"].sum()
                display_df = display_df.rename(columns={
                    "name": "Name",
                    "amount": "Amount",
                    "date": "Date",
                    "payment_type": "Payment Type",
                    "recieved_zelle_acc_name": "Cash Received By",
                    "comments": "Comments"
                })
                display_df.index = display_df.index + 1
                st.dataframe(display_df, use_container_width=True)
                st.markdown(f"<div style='text-align:right; font-size:1.1em; margin-top:0.5em;'><b>Total Amount:</b> <span style='color:#6A1B9A;'>${total_amount:,.2f}</span></div>", unsafe_allow_html=True)
            else:
                st.info("No payment details found.")

        with tab_not_received:
            df_pay = pd.read_sql("SELECT name FROM payment_details", conn)
            df_pay.columns = [c.lower() for c in df_pay.columns]
            paid_names = set(df_pay["name"].tolist())
            not_received_df = sponsor_df[~sponsor_df["name"].isin(paid_names)][["name", "total_amount"]]
            not_received_df = not_received_df.rename(columns={"name": "Name", "total_amount": "Amount"})
            not_received_df = not_received_df.sort_values(by=["Name"]).reset_index(drop=True)
            not_received_df.index = not_received_df.index + 1
            if 'id' in not_received_df.columns:
                not_received_df = not_received_df.drop(columns=["id"])
            st.dataframe(not_received_df, use_container_width=True)
            st.markdown(f"<div style='text-align:right; font-size:1.1em; margin-top:0.5em;'><b>Total Not Received:</b> <span style='color:#6A1B9A;'>${not_received_df['Amount'].sum():,.2f}</span></div>", unsafe_allow_html=True)

        with tab_mismatch:
            df_pay = pd.read_sql("SELECT name, amount FROM payment_details", conn)
            df_pay.columns = [c.lower() for c in df_pay.columns]
            mismatch_rows = []
            for _, row in df_pay.iterrows():
                name = row["name"]
                sent_amount = float(row["amount"])
                sponsor_row = sponsor_df[sponsor_df["name"] == name]
                if not sponsor_row.empty:
                    submitted_amount = float(sponsor_row["total_amount"].values[0])
                    if abs(sent_amount - submitted_amount) > 0.01:
                        mismatch_rows.append({"Name": name, "Submitted Amount": submitted_amount, "Sent Amount": sent_amount})
            if mismatch_rows:
                mismatch_df = pd.DataFrame(mismatch_rows)
                mismatch_df = mismatch_df.sort_values(by=["Name"]).reset_index(drop=True)
                mismatch_df.index = mismatch_df.index + 1
                st.dataframe(mismatch_df, use_container_width=True)
            else:
                st.info("No mismatch records found.")

        with tab_delete:
            df_pay = pd.read_sql("SELECT id, name, amount, date, comments FROM payment_details ORDER BY name ASC, id DESC", conn)
            df_pay.columns = [c.lower() for c in df_pay.columns]
            if not df_pay.empty:
                st.markdown("<h3 style='color: #6A1B9A;'>🗑️ Delete Payment Detail</h3>", unsafe_allow_html=True)
                pay_names = df_pay["name"].tolist()
                name_options = ["-- Select Name --"] + pay_names if pay_names else ["-- No Names Available --"]
                selected_name = st.selectbox("Select Payment Record (by Name)", name_options)
                if selected_name == "-- Select Name --" or selected_name == "-- No Names Available --":
                    st.info("Please select a name to view or delete the payment record.")
                else:
                    pay_row = df_pay[df_pay.name == selected_name].iloc[0]
                    pay_id = int(pay_row["id"])
                    st.markdown(f"""
<div style='border:1px solid #ccc; border-radius:8px; padding:1em; margin-bottom:1em;'>
<b>Name:</b> {pay_row['name']}<br>
<b>Amount:</b> ${pay_row['amount']:,.2f}<br>
<b>Date:</b> {pay_row['date']}<br>
<b>Comments:</b> {pay_row['comments'] or ''}
</div>
""", unsafe_allow_html=True)
                    st.warning(f"To confirm deletion, enter the name '{pay_row['name']}' below and click Delete.")
                    confirm_name = st.text_input("Enter this name to delete the record:", "", key=f"delete_pay_confirm_{pay_id}")
                    if st.button("Delete Payment Detail"):
                        if confirm_name.strip() == pay_row['name']:
                            try:
                                cursor.execute("DELETE FROM payment_details WHERE id=%s", (pay_id,))
                                conn.commit()
                                st.success("🗑️ Payment detail deleted!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"❌ Failed to delete payment detail: {e}")
                        else:
                            st.error("Name entered does not match. Record not deleted.")
            else:
                st.info("No payment details found.")
        return

    if menu == "Sponsorship Items":
        st.markdown("<h2 style='color: #6A1B9A;'>Sponsorship Items</h2>", unsafe_allow_html=True)
        try:
            ensure_sponsorship_item_image_columns(cursor)
            conn.commit()
        except Exception as e:
            conn.rollback()
            st.error(f"Unable to prepare sponsorship item images: {e}")
            return
        df = pd.read_sql("SELECT * FROM sponsorship_items ORDER BY id", conn)
        df.columns = [c.lower() for c in df.columns]
        tabs = ["Add Sponsorship Item", "Sponsorship Items List", "Edit Sponsorship Item", "Delete Sponsorship Item"]
        tab_add, tab_list, tab_edit, tab_delete = st.tabs(tabs)

        with tab_add:
            st.markdown("<h3 style='color: #6A1B9A;'>➕ Add New Sponsorship Item</h3>", unsafe_allow_html=True)
            with st.form("add_item_form"):
                new_name = st.text_input("New Item Name")
                new_amt = st.number_input("Amount", min_value=0)
                new_lim = st.number_input("Limit", min_value=1, value=3)
                new_image = st.file_uploader(
                    "Upload Item Image (JPG/PNG, max 10MB)",
                    type=["jpg", "jpeg", "png"],
                    key="new_sponsorship_item_image",
                )
                if st.form_submit_button("Add Item"):
                    try:
                        if not new_name.strip():
                            st.error("Item name is required.")
                        elif new_image is not None and new_image.size > 10 * 1024 * 1024:
                            st.error("Image file size should not exceed 10 MB.")
                        elif new_image is not None and new_image.type not in ["image/jpeg", "image/png"]:
                            st.error("Only JPG and PNG files are allowed.")
                        else:
                            image_bytes = new_image.getvalue() if new_image is not None else None
                            image_filename = new_image.name if new_image is not None else None
                            cursor.execute(
                                "INSERT INTO sponsorship_items (item, amount, sponsor_limit, image_blob, image_filename) VALUES (%s, %s, %s, %s, %s)",
                                (new_name.strip(), float(new_amt), int(new_lim), image_bytes, image_filename),
                            )
                            conn.commit()
                            st.success("✅ New item added!")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Failed to add item: {e}")

        with tab_list:
            st.markdown("<h3 style='color: #6A1B9A;'>📋 Sponsorship Items List</h3>", unsafe_allow_html=True)
            df_display = df.copy()
            if "image_blob" in df_display.columns:
                df_display["Image Uploaded"] = df_display["image_blob"].notna().map({True: "Yes", False: "No"})
                df_display = df_display.drop(columns=["image_blob", "image_filename"])
            if 'id' in df_display.columns:
                df_display = df_display.drop(columns=["id"])
            df_display.index = df_display.index + 1
            st.dataframe(df_display)

        with tab_edit:
            st.markdown("<h3 style='color: #6A1B9A;'>✏️ Edit Sponsorship Item</h3>", unsafe_allow_html=True)
            item_names = df["item"].tolist()
            selected_item_name = st.selectbox("Select Item Name", item_names)
            item_row = df[df["item"] == selected_item_name].iloc[0]
            new_item_name = st.text_input("Item Name", value=item_row["item"])
            new_amount = st.number_input(
                "Amount",
                min_value=0.0,
                value=float(item_row["amount"]),
                step=1.0,
                format="%.2f",
                key=f"edit_sponsorship_amount_{item_row['id']}",
            )
            new_limit = st.number_input(
                "Limit",
                min_value=1,
                value=int(item_row["sponsor_limit"]),
                step=1,
                key=f"edit_sponsorship_limit_{item_row['id']}",
            )
            edit_image = st.file_uploader(
                "Replace Item Image (JPG/PNG, max 10MB)",
                type=["jpg", "jpeg", "png"],
                key=f"edit_sponsorship_item_image_{item_row['id']}",
            )
            if st.button("Update Item"):
                try:
                    if edit_image is not None and edit_image.size > 10 * 1024 * 1024:
                        st.error("Image file size should not exceed 10 MB.")
                    elif edit_image is not None and edit_image.type not in ["image/jpeg", "image/png"]:
                        st.error("Only JPG and PNG files are allowed.")
                    else:
                        image_sql = ""
                        image_values = []
                        if edit_image is not None:
                            image_sql = ", image_blob=%s, image_filename=%s"
                            image_values = [edit_image.getvalue(), edit_image.name]
                        cursor.execute(
                            f"UPDATE sponsorship_items SET item=%s, amount=%s, sponsor_limit=%s{image_sql} WHERE id=%s",
                            (new_item_name.strip(), float(new_amount), int(new_limit), *image_values, int(item_row["id"])),
                        )
                        conn.commit()
                        st.success("✅ Item updated successfully!")
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Failed to update: {e}")

        with tab_delete:
            st.markdown("<h3 style='color: #6A1B9A;'>🗑️ Delete Sponsorship Item</h3>", unsafe_allow_html=True)
            item_names = df["item"].tolist()
            selected_item_name = st.selectbox("Select Item to Delete", item_names)
            item_row = df[df["item"] == selected_item_name].iloc[0]
            st.write(f"Item: {item_row['item']}")
            st.write(f"Amount: ${float(item_row['amount']):,.2f}")
            st.write(f"Limit: {int(item_row['sponsor_limit'])}")
            if st.button("Delete Item"):
                try:
                    cursor.execute("DELETE FROM sponsorship_items WHERE id=%s", (item_row["id"],))
                    conn.commit()
                    st.success("🗑️ Sponsorship item deleted!")
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Failed to delete item: {e}")

    if menu == "Sponsorship Record":
        st.markdown("<h2 style='color: #6A1B9A;'>✏️ Edit Sponsorship Record</h2>", unsafe_allow_html=True)
        df_sponsors = pd.read_sql("SELECT * FROM sponsors ORDER BY id", conn)
        df_sponsors.columns = [c.lower() for c in df_sponsors.columns]
        if not df_sponsors.empty:
            display_df = df_sponsors.copy()
            def get_type(row):
                has_sponsorship = (
                    pd.notna(row['sponsorship'])
                    and bool(str(row['sponsorship']).strip())
                )
                donation_amount = float(row['donation']) if pd.notna(row['donation']) else 0
                if has_sponsorship:
                    return 'Sponsorship'
                elif donation_amount > 0:
                    return 'Donation'
                else:
                    return ''
            display_df['Type'] = display_df.apply(get_type, axis=1)
            # Pre-fetch sponsorship item amounts into a dict
            cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items")
            item_amounts = {}
            for row in cursor.fetchall():
                item, amount, sponsor_limit = row
                try:
                    per_sponsor = float(amount) / int(sponsor_limit) if sponsor_limit else float(amount)
                except Exception:
                    per_sponsor = float(amount)
                item_amounts[item] = per_sponsor
            # Compute a single amount column
            def get_amount(row):
                if row['Type'] == 'Sponsorship':
                    return item_amounts.get(row['sponsorship'], 0.0)
                if row['Type'] == 'Donation':
                    return float(row['donation']) if pd.notna(row['donation']) else 0.0
                return 0.0

            display_df['Donation/Sponsorship Amount'] = display_df.apply(get_amount, axis=1)
            display_df = display_df.drop(columns=['donation', 'id'])
            # Reorder columns
            col_order = ['name', 'email', 'mobile', 'apartment', 'gothram', 'sponsorship', 'Type', 'Donation/Sponsorship Amount']
            display_df = display_df[[c for c in col_order if c in display_df.columns]]
            display_df = display_df.rename(columns={col: col.replace('_', ' ').title() for col in display_df.columns})
            display_df = display_df.rename(columns={'Sponsorship': 'Sponsorship Item'})
            # Show table with index starting from 1 and sorted by Name, keep id column
            display_df_display = display_df.copy()
            if 'Name' in display_df_display.columns:
                display_df_display = display_df_display.sort_values(by=["Name"])
            elif 'name' in display_df_display.columns:
                display_df_display = display_df_display.sort_values(by=["name"])
            display_df_display.index = range(1, len(display_df_display) + 1)
            st.dataframe(display_df_display, use_container_width=True)
            # Sort sponsor names for selection
            sponsor_names = sorted(df_sponsors["name"].tolist())
            sponsor_name_options = ["-- Select a Name --"] + sponsor_names
            selected_name = st.selectbox("Select Sponsorship Record (by Name)", sponsor_name_options)
            if selected_name == "-- Select a Name --":
                st.info("Please select a name to view or edit the sponsorship record.")
                return
            # Sort df_sponsors by name for consistent lookup
            df_sponsors_sorted = df_sponsors.sort_values(by=["name"])
            sponsor_row = df_sponsors_sorted[df_sponsors_sorted.name == selected_name].iloc[0]
            sponsor_id = int(sponsor_row["id"])
            # Move Edit/Delete selection to the top
            action = st.radio("Choose Action", ["Edit Record", "Delete Record"], horizontal=True)
            if action == "Edit Record":
                edit_name = st.text_input("Name", value=sponsor_row["name"] or "", key=f"edit_name_{sponsor_id}")
                st.write(f"Apartment Number: {sponsor_row['apartment']}")
                # Editable Sponsorship Item field
                cursor.execute("SELECT item FROM sponsorship_items ORDER BY id")
                sponsorship_items_list = [row[0] for row in cursor.fetchall()]
                current_item = sponsor_row['sponsorship'] if sponsor_row['sponsorship'] else ''
                edit_sponsorship_item = st.selectbox(
                    "Sponsorship Item (editable)",
                    options=["N/A"] + sponsorship_items_list,
                    index=(sponsorship_items_list.index(current_item) + 1) if current_item in sponsorship_items_list else 0,
                    help="Select a sponsorship item or choose N/A for donation only."
                )
                edit_donation = st.number_input("Donation Amount (editable)", min_value=0.0, value=float(sponsor_row['donation'] or 0), step=1.0, format="%.2f", key=f"edit_donation_{sponsor_id}")
                # Editable optional fields
                edit_email = st.text_input("Email Address (optional)", value=sponsor_row["email"] or "", help="Enter Email to Subscribe the notifications to Your Email")
                edit_gothram = st.text_input("Gothram (optional)", value=sponsor_row["gothram"] if "gothram" in sponsor_row and sponsor_row["gothram"] is not None else "", key=f"edit_gothram_{sponsor_id}")
                edit_mobile = st.text_input("Mobile (optional, US format)", value=sponsor_row["mobile"] or "")
                if st.button("Update Sponsorship Record"):
                    errors = []
                    edit_name = edit_name.strip()
                    if not edit_name:
                        errors.append("Name is required.")
                    # Email validation
                    if edit_email.strip():
                        if '@' not in edit_email or not edit_email.strip().lower().endswith('.com'):
                            errors.append("Please enter a valid email address (must contain '@' and end with .com)")
                    # Mobile validation (optional, US format)
                    import re
                    def validate_us_phone(phone):
                        digits = re.sub(r'\D', '', phone)
                        if len(digits) == 10:
                            return True, f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                        return False, phone
                    phone_valid, phone_fmt = True, edit_mobile
                    if edit_mobile.strip():
                        phone_valid, phone_fmt = validate_us_phone(edit_mobile)
                        if not phone_valid:
                            errors.append("Please enter a valid 10-digit US phone number.")
                    # Validate sponsorship item
                    sponsorship_value = None if edit_sponsorship_item == "N/A" else edit_sponsorship_item
                    # Validate donation
                    if edit_donation < 0:
                        errors.append("Donation amount cannot be negative.")
                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        try:
                            cursor.execute(
                                "UPDATE sponsors SET name=%s, email=%s, mobile=%s, gothram=%s, sponsorship=%s, donation=%s WHERE id=%s",
                                (edit_name, edit_email, phone_fmt.strip(), edit_gothram, sponsorship_value, edit_donation, sponsor_id)
                            )
                            conn.commit()
                            st.success("✅ Sponsorship record updated!")
                            # Send only to notification_emails
                            cursor.execute("SELECT email FROM notification_emails")
                            notification_emails = [row[0] for row in cursor.fetchall() if row[0]]
                            admin_full_name = st.session_state.get('admin_full_name', 'Unknown')
                            if notification_emails:
                                send_email(
                                    "Ganesh Chaturthi Sponsorship Record Updated",
                                    f"""
    <b>Sponsorship Record Updated</b><br><br>
    <table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;'>
            <tr><th style='{TABLE_HEADER_STYLE}'>Name</th><td>{edit_name}</td></tr>
            <tr><th style='{TABLE_HEADER_STYLE}'>Email</th><td>{edit_email}</td></tr>
            <tr><th style='{TABLE_HEADER_STYLE}'>Gothram</th><td>{edit_gothram}</td></tr>
            <tr><th style='{TABLE_HEADER_STYLE}'>Mobile</th><td>{phone_fmt.strip()}</td></tr>
            <tr><th style='{TABLE_HEADER_STYLE}'>Apartment</th><td>{sponsor_row['apartment']}</td></tr>
            <tr><th style='{TABLE_HEADER_STYLE}'>Sponsorship Item</th><td>{sponsorship_value if sponsorship_value else 'N/A'}</td></tr>
            <tr><th style='{TABLE_HEADER_STYLE}'>Donation</th><td>${float(edit_donation):,.2f}</td></tr>
    </table>
    <br><b>Modified By:</b> {admin_full_name}
    """,
                                    notification_emails
                                )
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Failed to update sponsorship: {e}")
            elif action == "Delete Record":
                st.markdown("#### Delete this sponsorship record?")
                # Handle donation display: show $0.00 if None or not a number
                try:
                    donation_val = float(sponsor_row['donation']) if sponsor_row['donation'] not in (None, '', 0, '0', 'nan', 'NaN') else 0.0
                except Exception:
                    donation_val = 0.0
                st.markdown(f"""
<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;'>
    <tr><th style='{TABLE_HEADER_STYLE}'>Name</th><td>{sponsor_row['name']}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Email</th><td>{sponsor_row['email']}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Gothram</th><td>{sponsor_row['gothram']}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Mobile</th><td>{sponsor_row['mobile']}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Apartment</th><td>{sponsor_row['apartment']}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Sponsorship Item</th><td>{sponsor_row['sponsorship'] if sponsor_row['sponsorship'] else 'N/A'}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Donation</th><td>${donation_val:,.2f}</td></tr>
</table>
""", unsafe_allow_html=True)
                st.warning(f"To confirm deletion, enter the name '{sponsor_row['name']}' below and click Delete.")
                confirm_name = st.text_input("Enter this name to delete the record:", "", key=f"delete_confirm_{sponsor_id}")
                if st.button("Delete Sponsorship Record"):
                    if confirm_name.strip() == sponsor_row['name']:
                        try:
                            # Fetch notification emails
                            cursor.execute("SELECT email FROM notification_emails")
                            notification_emails = [row[0] for row in cursor.fetchall() if row[0]]
                            # Get admin full name for audit trail
                            admin_full_name = st.session_state.get('admin_full_name', 'Unknown')
                            # Prepare deleted record details with audit trail
                            deleted_details = f"""
<b>Sponsorship Record Deleted</b><br><br>
<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;'>
    <tr><th style='{TABLE_HEADER_STYLE}'>Name</th><td>{sponsor_row['name']}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Email</th><td>{sponsor_row['email']}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Gothram</th><td>{sponsor_row['gothram']}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Mobile</th><td>{sponsor_row['mobile']}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Apartment</th><td>{sponsor_row['apartment']}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Sponsorship Item</th><td>{sponsor_row['sponsorship'] if sponsor_row['sponsorship'] else 'N/A'}</td></tr>
    <tr><th style='{TABLE_HEADER_STYLE}'>Donation</th><td>${float(sponsor_row['donation'] or 0):,.2f}</td></tr>
</table>
<br><b>Modified By:</b> {admin_full_name}
"""
                            cursor.execute("DELETE FROM sponsors WHERE id=%s", (sponsor_id,))
                            conn.commit()
                            st.cache_data.clear()
                            # Send email to notification_emails
                            if notification_emails:
                                send_email(
                                    "Ganesh Chaturthi Sponsorship Record Deleted",
                                    deleted_details,
                                    notification_emails
                                )
                            st.success("🗑️ Sponsorship record deleted!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Failed to delete sponsorship record: {e}")
                    else:
                        st.error("Name entered does not match. Record not deleted.")
        else:
            st.info("No sponsorship records found.")
    if menu == "Committee Members":
        st.markdown("<h2 style='color: #6A1B9A;'>👥 Committee Members</h2>", unsafe_allow_html=True)
        try:
            df_members = pd.read_sql("SELECT id, name, apartment, recieve_cash_enable FROM committee_members ORDER BY name", conn)
            df_members.columns = [c.lower() for c in df_members.columns]
        except Exception as e:
            st.error(f"Unable to load committee members: {e}")
            return

        member_tabs = st.tabs(["Members List", "Add Member", "Edit Member", "Delete Member"])
        with member_tabs[1]:
            with st.form("add_committee_member_form"):
                new_member_name = st.text_input("Member Name")
                new_member_apartment = st.text_input("Apartment Number")
                new_member_cash_enable = st.checkbox("Enable for cash collection", value=False)
                if st.form_submit_button("Add Member"):
                    if not new_member_name.strip() or not new_member_apartment.strip():
                        st.warning("Member name and apartment number are required.")
                    else:
                        try:
                            cursor.execute(
                                "INSERT INTO committee_members (name, apartment, recieve_cash_enable) VALUES (%s, %s, %s)",
                                (new_member_name.strip(), new_member_apartment.strip(), new_member_cash_enable)
                            )
                            conn.commit()
                            st.success("✅ Committee member added!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Failed to add committee member: {e}")

        with member_tabs[0]:
            display_members = df_members.rename(columns={"name": "Name", "apartment": "Apartment Number", "recieve_cash_enable": "Cash Collection Enabled"})
            display_members = display_members.drop(columns=["id"])
            display_members.index = display_members.index + 1
            st.dataframe(display_members, use_container_width=True)

        with member_tabs[2]:
            if df_members.empty:
                st.info("No committee members found.")
            else:
                member_options = df_members["name"].tolist()
                updated_member = st.session_state.pop("updated_committee_member", None)
                if updated_member in member_options:
                    st.session_state["edit_committee_member_selection"] = updated_member
                    st.session_state["edit_committee_member_name"] = updated_member
                    updated_row = df_members[df_members["name"] == updated_member].iloc[0]
                    st.session_state["edit_committee_member_apartment"] = str(updated_row["apartment"] or "")
                    st.session_state["edit_committee_member_cash_enable"] = bool(updated_row["recieve_cash_enable"])

                def sync_member_name():
                    selected_name = st.session_state["edit_committee_member_selection"]
                    selected_row = df_members[df_members["name"] == selected_name].iloc[0]
                    st.session_state["edit_committee_member_name"] = selected_name
                    st.session_state["edit_committee_member_apartment"] = str(selected_row["apartment"] or "")
                    st.session_state["edit_committee_member_cash_enable"] = bool(selected_row["recieve_cash_enable"])
                    st.session_state["edit_committee_member_last_selection"] = selected_name

                selected_member = st.selectbox(
                    "Select Member to Edit",
                    member_options,
                    key="edit_committee_member_selection",
                    on_change=sync_member_name
                )
                member_row = df_members[df_members["name"] == selected_member].iloc[0]
                if st.session_state.get("edit_committee_member_last_selection") != selected_member:
                    st.session_state["edit_committee_member_name"] = member_row["name"]
                    st.session_state["edit_committee_member_apartment"] = str(member_row["apartment"] or "")
                    st.session_state["edit_committee_member_cash_enable"] = bool(member_row["recieve_cash_enable"])
                    st.session_state["edit_committee_member_last_selection"] = selected_member
                member_name = st.text_input("Member Name", key="edit_committee_member_name")
                member_apartment = st.text_input("Apartment Number", key="edit_committee_member_apartment")
                member_cash_enable = st.checkbox("Enable for cash collection", key="edit_committee_member_cash_enable")
                if st.button("Update Committee Member"):
                    if not member_name.strip() or not member_apartment.strip():
                        st.warning("Member name and apartment number are required.")
                    else:
                        try:
                            cursor.execute(
                                "UPDATE committee_members SET name=%s, apartment=%s, recieve_cash_enable=%s WHERE id=%s",
                                (member_name.strip(), member_apartment.strip(), member_cash_enable, int(member_row["id"]))
                            )
                            conn.commit()
                            st.session_state["updated_committee_member"] = member_name.strip()
                            st.success("✅ Committee member updated!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Failed to update committee member: {e}")

        with member_tabs[3]:
            if df_members.empty:
                st.info("No committee members found.")
            else:
                member_options = df_members["name"].tolist()
                selected_member = st.selectbox("Select Member to Delete", member_options)
                member_row = df_members[df_members["name"] == selected_member].iloc[0]
                st.write(f"Member: **{member_row['name']}**")
                st.write(f"Apartment Number: **{member_row['apartment']}**")
                st.write(f"Cash Collection Enabled: **{bool(member_row['recieve_cash_enable'])}**")
                if st.button("Delete Committee Member"):
                    try:
                        cursor.execute("DELETE FROM committee_members WHERE id=%s", (int(member_row["id"]),))
                        conn.commit()
                        st.success("✅ Committee member deleted!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Failed to delete committee member: {e}")

    if menu == "Manage Notification Emails":
        st.markdown("<h2 style='color: #6A1B9A;'>✉️ Manage Notification Emails</h2>", unsafe_allow_html=True)
        df_emails = pd.read_sql("SELECT * FROM notification_emails ORDER BY id", conn)
        df_emails.columns = [c.lower() for c in df_emails.columns]
        tabs = ["Add Notification Email", "Notification Emails List", "Edit Notification Email", "Delete Notification Email"]
        tab_add, tab_list, tab_edit, tab_delete = st.tabs(tabs)

        with tab_add:
            st.markdown("<h3 style='color: #6A1B9A;'>➕ Add Notification Email</h3>", unsafe_allow_html=True)
            with st.form("add_notification_email_form"):
                new_email = st.text_input("New Email Address")
                if st.form_submit_button("Add Email"):
                    try:
                        cursor.execute("INSERT INTO notification_emails (email) VALUES (%s)", (new_email.strip(),))
                        conn.commit()
                        st.success("✅ Notification email added!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Failed to add notification email: {e}")

        with tab_list:
            st.markdown("<h3 style='color: #6A1B9A;'>📋 Notification Emails List</h3>", unsafe_allow_html=True)
            display_emails = df_emails.drop(columns=["id"])
            display_emails.index = display_emails.index + 1
            st.dataframe(display_emails, use_container_width=True)

        with tab_edit:
            st.markdown("<h3 style='color: #6A1B9A;'>✏️ Edit Notification Email</h3>", unsafe_allow_html=True)
            email_list = df_emails["email"].tolist()
            selected_email = st.selectbox("Select Email to Edit", email_list)
            email_row = df_emails[df_emails.email == selected_email].iloc[0]
            email_id = int(email_row["id"])
            edit_email_val = st.text_input("Edit Email", value=email_row["email"], key="edit_notification_email")
            if st.button("Update Notification Email"):
                try:
                    cursor.execute("UPDATE notification_emails SET email=%s WHERE id=%s", (edit_email_val.strip(), email_id))
                    conn.commit()
                    st.success("✅ Notification email updated!")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Failed to update notification email: {e}")

        with tab_delete:
            st.markdown("<h3 style='color: #6A1B9A;'>🗑️ Delete Notification Email</h3>", unsafe_allow_html=True)
            email_list = df_emails["email"].tolist()
            selected_email = st.selectbox("Select Email to Delete", email_list)
            email_row = df_emails[df_emails.email == selected_email].iloc[0]
            email_id = int(email_row["id"])
            st.write(f"Email: {email_row['email']}")
            if st.button("Delete Notification Email"):
                try:
                    cursor.execute("DELETE FROM notification_emails WHERE id=%s", (email_id,))
                    conn.commit()
                    st.success("🗑️ Notification email deleted!")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Failed to delete notification email: {e}")
                    st.success("✅ New notification email added!")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Failed to add notification email: {e}")

