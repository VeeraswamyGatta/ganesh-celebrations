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
import io
import re
import zipfile
from .db import get_connection
from .email_utils import send_email
from .login_audit import ensure_login_audit_table, is_user_login_tracking_enabled
from .notification_utils import get_notification_emails


def ensure_sponsorship_item_image_columns(cursor):
    blob_type = "BINARY" if hasattr(cursor.connection, "account") else "BYTEA"
    cursor.execute(f"ALTER TABLE sponsorship_items ADD COLUMN IF NOT EXISTS image_blob {blob_type}")
    cursor.execute("ALTER TABLE sponsorship_items ADD COLUMN IF NOT EXISTS image_filename TEXT")


def admin_tab(menu="Sponsorship Items"):
    st.session_state['active_tab'] = 'Expenses' if menu == "Sponsorship Payment Details" else 'Admin'
    conn = get_connection()
    cursor = conn.cursor()
    if menu == "User Login Activity":
        if not is_user_login_tracking_enabled():
            return
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
        st.caption(f"Total logins: {login_counts['login_count'].sum():,}")
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

    # Show payment records with Received as the default view.
    if menu == "Sponsorship Payment Details" or menu is None:
        from streamlit_option_menu import option_menu
        
        # Redesigned horizontal menu bar using option_menu
        def get_sponsor_df():
            df = pd.read_sql(
                """
                SELECT
                    name,
                    MAX(apartment) AS apartment,
                    MAX(mobile) AS mobile,
                    MAX(email) AS email,
                    SUM(COALESCE(donation, 0)) AS donation_sum
                FROM sponsors
                GROUP BY name
                """,
                conn,
            )
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
        
        payment_action_key = "payment_action"
        if st.session_state.get(payment_action_key) not in (None, "add", "not_received", "delete"):
            st.session_state[payment_action_key] = None
        payment_notice = st.session_state.pop("payment_notice", None)
        if payment_notice:
            st.success(payment_notice)
        st.markdown(
            """
            <style>
            .st-key-payment_inline_actions [data-testid="stHorizontalBlock"] {
                flex-wrap: nowrap !important;
                gap: 0.45rem !important;
            }
            .st-key-payment_inline_actions [data-testid="stColumn"] {
                min-width: 0 !important;
                flex: 1 1 0 !important;
            }
            .st-key-payment_inline_actions button {
                min-height: 2.4rem !important;
                padding: 0.4rem 0.35rem !important;
                border: 1px solid #d8b15a !important;
                border-radius: 9px !important;
                background: #ffffff !important;
                color: #6a1b1b !important;
                font-size: 0.76rem !important;
                font-weight: 800 !important;
                white-space: nowrap !important;
                box-shadow: 0 2px 6px rgba(106, 27, 27, 0.1) !important;
            }
            .st-key-payment_inline_actions button:hover {
                border-color: #8b1737 !important;
                background: #fff8e1 !important;
                transform: translateY(-1px);
            }
            @media (max-width: 640px) {
                .st-key-payment_inline_actions [data-testid="stHorizontalBlock"] {
                    flex-wrap: nowrap !important;
                }
                .st-key-payment_inline_actions button {
                    padding: 0.35rem 0.2rem !important;
                    font-size: 0.66rem !important;
                }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        with st.container(key="payment_inline_actions"):
            payment_action_columns = st.columns(3)
            if payment_action_columns[0].button("➕ Add", key="payment_inline_add", use_container_width=True):
                if st.session_state.get(payment_action_key) == "add":
                    st.session_state[payment_action_key] = None
                    for key in (
                        "add_pay_amount_input",
                        "add_pay_last_selected_name",
                        "add_pay_selected_name",
                        "add_pay_zelle_acc_name",
                        "add_pay_date",
                        "add_pay_comments",
                    ):
                        st.session_state.pop(key, None)
                else:
                    st.session_state[payment_action_key] = "add"
                st.rerun()
            if payment_action_columns[1].button("Not Received", key="payment_inline_not_received", use_container_width=True):
                st.session_state[payment_action_key] = "not_received"
                st.rerun()
            if payment_action_columns[2].button("🗑️ Delete", key="payment_inline_delete", use_container_width=True):
                st.session_state[payment_action_key] = "delete"
                st.rerun()

        payment_menu = {
            "add": "Add Payment Detail",
            "not_received": "Not Received",
            "delete": "Delete Payment Detail",
        }.get(st.session_state.get(payment_action_key), "Received")

        if payment_menu == "Add Payment Detail":
            df_pay_names = pd.read_sql("SELECT name FROM payment_details", conn)
            df_pay_names.columns = [c.lower() for c in df_pay_names.columns]
            paid_names_set = set(df_pay_names["name"].tolist())
            unpaid_names = [name for name in sponsor_names if name not in paid_names_set]
            name_options = ["-- Select Name --"] + unpaid_names if unpaid_names else ["-- No Names Available --"]
            if "add_pay_selected_name" not in st.session_state or st.session_state["add_pay_selected_name"] not in name_options:
                st.session_state["add_pay_selected_name"] = name_options[0]

            def update_amount():
                selected_name = st.session_state["add_pay_selected_name"]
                amount = float(sponsor_df[sponsor_df["name"] == selected_name]["total_amount"].values[0]) if selected_name in sponsor_names else 0.0
                st.session_state["add_pay_amount_input"] = amount

            if "add_pay_last_selected_name" not in st.session_state:
                st.session_state["add_pay_last_selected_name"] = st.session_state["add_pay_selected_name"]
            if "add_pay_amount_input" not in st.session_state:
                update_amount()
            name = st.selectbox("Name", name_options, key="add_pay_selected_name")
            payment_type = "Cash"
            if st.session_state["add_pay_last_selected_name"] != st.session_state["add_pay_selected_name"]:
                update_amount()
                st.session_state["add_pay_zelle_acc_name"] = ""
                st.session_state["add_pay_last_selected_name"] = st.session_state["add_pay_selected_name"]
            default_amount = st.session_state.get("add_pay_amount_input", 0.0)
            import pytz
            with st.form("add_payment_detail_form"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"Name: **{name}**")
                    amount = st.number_input("Amount (editable)", min_value=0.0, value=default_amount, step=1.0, format="%.2f", key="add_pay_amount_input")
                with col2:
                    date = st.date_input("Date", key="add_pay_date")
                    if st.session_state.get("admin_login_role") == "admin_email":
                        recieved_zelle_acc_name = st.session_state.get("admin_committee_member_name", "")
                        st.write(f"Cash/Zelle collected by: **{recieved_zelle_acc_name}**")
                    else:
                        try:
                            cursor.execute("SELECT name, apartment FROM committee_members WHERE recieve_cash_enable = TRUE OR zelle_enable = TRUE ORDER BY name")
                            member_names = [row[0] for row in cursor.fetchall() if row[0]]
                        except Exception:
                            member_names = []
                        cash_collector_options = ["-- Select Received By --"] + member_names
                        recieved_zelle_acc_name = st.selectbox("Received By", cash_collector_options, key="add_pay_zelle_acc_name")
                    comments = st.text_input("Comments", key="add_pay_comments")
                submit = st.form_submit_button("Add Payment Detail")
                if submit:
                    if name == "-- Select Name --" or name == "-- No Names Available --":
                        st.warning("Please select a name before submitting.")
                    elif recieved_zelle_acc_name == "-- Select Received By --":
                        st.warning("Please select the committee member who received the payment.")
                    else:
                        try:
                            tz = pytz.timezone("America/Chicago")
                            dt_naive = datetime.datetime.combine(date, datetime.time.min)
                            date_cst = tz.localize(dt_naive).date()
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
                            st.session_state[payment_action_key] = None
                            st.session_state["payment_notice"] = "Payment detail added."
                            st.session_state.pop("add_pay_amount_input", None)
                            st.session_state.pop("add_pay_last_selected_name", None)
                            st.session_state.pop("add_pay_selected_name", None)
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Failed to add payment detail: {e}")

        elif payment_menu == "Received":
            # Received: Payment details table
            payment_columns = pd.read_sql("SELECT * FROM payment_details LIMIT 0", conn).columns.str.lower()
            zelle_column = ", recieved_zelle_acc_name" if "recieved_zelle_acc_name" in payment_columns else ""
            df_pay = pd.read_sql(f"SELECT id, name, amount, date, payment_type{zelle_column}, comments FROM payment_details ORDER BY date DESC, id DESC", conn)
            df_pay.columns = [c.lower() for c in df_pay.columns]
            _, search_col, download_col = st.columns([6, 2.5, 1])
            with search_col:
                payment_search = st.text_input("🔍 Search", value="", key="received_payment_search", label_visibility="collapsed", placeholder="Search payments")
            if not df_pay.empty:
                filtered_df = df_pay.copy()
                if payment_search:
                    matches = filtered_df.astype(str).apply(
                        lambda column: column.str.contains(payment_search, case=False, na=False, regex=False)
                    )
                    filtered_df = filtered_df[matches.any(axis=1)]
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
                    "recieved_zelle_acc_name": "Cash/Zelle Received By",
                    "comments": "Comments"
                })
                display_df.index = display_df.index + 1
                with download_col:
                    st.download_button("⬇️", data=display_df.to_csv(index=False), file_name="received_payments.csv", mime="text/csv", key="download_received_payments", help="Download received payments")
                st.dataframe(display_df, use_container_width=True)
                st.markdown(f"<div style='text-align:right; font-size:1.1em; margin-top:0.5em;'><b>Total Amount:</b> <span style='color:#6A1B9A;'>${total_amount:,.2f}</span></div>", unsafe_allow_html=True)
                if "recieved_zelle_acc_name" in filtered_df.columns:
                    chart_df = filtered_df.copy()
                    chart_df["recieved_zelle_acc_name"] = (
                        chart_df["recieved_zelle_acc_name"]
                        .fillna("Not specified")
                        .astype(str)
                        .str.strip()
                        .replace("", "Not specified")
                    )
                    chart_data = chart_df.groupby("recieved_zelle_acc_name")["amount"].sum().sort_values(ascending=False)
                    st.caption(f"Total received by collector: ${chart_data.sum():,.2f}")
                    st.bar_chart(chart_data.rename("Total Amount"))
            else:
                st.info("No payment details found.")

        elif payment_menu == "Not Received":
            df_pay = pd.read_sql("SELECT name FROM payment_details", conn)
            df_pay.columns = [c.lower() for c in df_pay.columns]
            paid_names = set(df_pay["name"].tolist())
            not_received_df = sponsor_df[~sponsor_df["name"].isin(paid_names)][
                ["name", "total_amount", "apartment", "mobile", "email"]
            ].rename(columns={
                "name": "Name",
                "total_amount": "Amount",
                "apartment": "Apartment",
                "mobile": "Mobile",
                "email": "Email",
            }).sort_values(by="Name").reset_index(drop=True)
            if sponsor_df.empty:
                st.info("No sponsor records are available yet.")
            elif not_received_df.empty:
                received_total = float(sponsor_df["total_amount"].sum())
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:1rem;margin:0.5rem 0 1rem;padding:1.1rem 1.25rem;border:1px solid #a9c9a9;border-left:6px solid #2e7d50;border-radius:10px;background:linear-gradient(110deg,#f0f8ef 0%,#fff8e8 100%);box-shadow:0 5px 16px rgba(38,91,57,0.12);">
                        <div style="display:flex;align-items:center;justify-content:center;flex:0 0 2.5rem;height:2.5rem;border-radius:50%;background:#2e7d50;color:#ffffff;font-size:1.25rem;font-weight:800;">✓</div>
                        <div>
                            <div style="color:#245b3d;font-size:1rem;font-weight:800;">All sponsor payments are received and recorded</div>
                            <div style="margin-top:0.25rem;color:#586b5c;font-size:0.85rem;">All {len(sponsor_df)} sponsor record(s) are accounted for · ${received_total:,.2f} recorded</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                _, search_col, download_col = st.columns([6, 2.5, 1])
                with search_col:
                    search_value = st.text_input(
                        "Search unpaid sponsors",
                        key="not_received_search",
                        label_visibility="collapsed",
                        placeholder="Search unpaid sponsors",
                    )
                filtered_not_received_df = not_received_df.copy()
                if search_value:
                    matches = filtered_not_received_df.astype(str).apply(
                        lambda column: column.str.contains(search_value, case=False, na=False, regex=False)
                    )
                    filtered_not_received_df = filtered_not_received_df[matches.any(axis=1)]
                if filtered_not_received_df.empty:
                    st.info("No unpaid sponsor records match this search.")
                else:
                    with download_col:
                        st.download_button(
                            "⬇️",
                            data=filtered_not_received_df.to_csv(index=False),
                            file_name="not_received_payments.csv",
                            mime="text/csv",
                            key="download_not_received_payments",
                            help="Download not received payments",
                        )
                    st.dataframe(filtered_not_received_df, hide_index=True, use_container_width=True)
                    st.markdown(
                        f"<div style='text-align:right; font-size:1.1em; margin-top:0.5em;'><b>Total Not Received:</b> <span style='color:#6A1B9A;'>${filtered_not_received_df['Amount'].sum():,.2f}</span></div>",
                        unsafe_allow_html=True,
                    )

        elif payment_menu == "Delete Payment Detail":
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
                                st.session_state[payment_action_key] = None
                                st.session_state["payment_notice"] = "Payment detail deleted."
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
        try:
            ensure_sponsorship_item_image_columns(cursor)
            conn.commit()
        except Exception as e:
            conn.rollback()
            st.error(f"Unable to prepare sponsorship item images: {e}")
            return
        df = pd.read_sql("SELECT * FROM sponsorship_items ORDER BY id", conn)
        df.columns = [c.lower() for c in df.columns]
        action_key = "sponsorship_item_action"
        if st.session_state.get(action_key) not in (None, "add", "edit", "delete"):
            st.session_state[action_key] = None
        item_notice = st.session_state.pop("sponsorship_item_notice", None)
        if item_notice:
            st.success(item_notice)
        st.markdown(
            """
            <style>
            .st-key-sponsorship_item_actions [data-testid="stHorizontalBlock"] { display:grid !important; grid-template-columns:repeat(3,minmax(0,1fr)) !important; gap:0.5rem !important; width:100% !important; }
            .st-key-sponsorship_item_actions [data-testid="column"], .st-key-sponsorship_item_actions [data-testid="stColumn"] { min-width:0 !important; width:auto !important; flex:initial !important; }
            .st-key-sponsorship_item_actions button { min-height:2.6rem !important; width:100% !important; padding:0.4rem 0.3rem !important; border:1px solid transparent !important; border-radius:8px !important; color:#fff !important; font-size:0.78rem !important; font-weight:800 !important; white-space:nowrap !important; box-shadow:0 4px 10px rgba(44,58,48,0.15) !important; }
            .st-key-sponsorship_item_add button { background:linear-gradient(110deg,#225b40,#347a55) !important; border-color:#b38a43 !important; }
            .st-key-sponsorship_item_edit button { background:linear-gradient(110deg,#176c70,#268b83) !important; border-color:#8bb7a8 !important; }
            .st-key-sponsorship_item_delete button { background:linear-gradient(110deg,#803b52,#a84d5e) !important; border-color:#c79782 !important; }
            @media (max-width:520px) { .st-key-sponsorship_item_actions button { min-height:2.4rem !important; padding:0.3rem 0.15rem !important; font-size:0.68rem !important; } }
            </style>
            """,
            unsafe_allow_html=True,
        )
        with st.container(key="sponsorship_item_actions"):
            action_columns = st.columns(3)
            if action_columns[0].button("➕ Add", key="sponsorship_item_add", use_container_width=True):
                st.session_state[action_key] = "add"
                st.rerun()
            if action_columns[1].button("✏️ Edit", key="sponsorship_item_edit", disabled=df.empty, use_container_width=True):
                st.session_state[action_key] = "edit"
                st.session_state.pop("sponsorship_item_edit_loaded_id", None)
                st.rerun()
            if action_columns[2].button("🗑️ Delete", key="sponsorship_item_delete", disabled=df.empty, use_container_width=True):
                st.session_state[action_key] = "delete"
                st.rerun()

        item_action = st.session_state.get(action_key)
        if item_action is None:
            if df.empty:
                st.info("No sponsorship items found.")
            else:
                display_items = df.drop(columns=["id", "image_blob", "image_filename"], errors="ignore")
                if "image_blob" in df.columns:
                    display_items["Image Uploaded"] = df["image_blob"].notna().map({True: "Yes", False: "No"})
                display_items.index = range(1, len(display_items) + 1)
                st.dataframe(display_items, hide_index=True, use_container_width=True)

        elif item_action == "add":
            st.subheader("Add Sponsorship Item")
            with st.form("add_item_form"):
                new_name = st.text_input("Item Name")
                new_amt = st.number_input("Amount", min_value=0.0, format="%.2f")
                new_lim = st.number_input("Limit", min_value=1, value=3)
                new_image = st.file_uploader(
                    "Upload Item Image (JPG/PNG, max 10MB)",
                    type=["jpg", "jpeg", "png"],
                    key="new_sponsorship_item_image",
                )
                add_item = st.form_submit_button("Add Item", use_container_width=True)
            if add_item:
                if not new_name.strip():
                    st.error("Item name is required.")
                elif new_image is not None and new_image.size > 10 * 1024 * 1024:
                    st.error("Image file size should not exceed 10 MB.")
                elif new_image is not None and new_image.type not in ["image/jpeg", "image/png"]:
                    st.error("Only JPG and PNG files are allowed.")
                else:
                    try:
                        image_bytes = new_image.getvalue() if new_image is not None else None
                        image_filename = new_image.name if new_image is not None else None
                        cursor.execute(
                            "INSERT INTO sponsorship_items (item, amount, sponsor_limit, image_blob, image_filename) VALUES (%s, %s, %s, %s, %s)",
                            (new_name.strip(), float(new_amt), int(new_lim), image_bytes, image_filename),
                        )
                        conn.commit()
                        st.session_state[action_key] = None
                        st.session_state["sponsorship_item_notice"] = "Sponsorship item added."
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Failed to add sponsorship item: {e}")
            if st.button("Cancel", key="sponsorship_item_cancel_add"):
                st.session_state[action_key] = None
                st.rerun()

    if menu == "Email Event Details":
        st.info("Send event data and stored receipts to committee members with an email address.")

        notification_addresses = get_notification_emails(cursor)
        recipient_names = {}
        try:
            cursor.execute("SELECT name, email FROM committee_members WHERE email IS NOT NULL AND email != ''")
            recipient_names.update({email: name for name, email in cursor.fetchall()})
        except Exception:
            pass
        try:
            cursor.execute("SELECT name, email FROM sponsors WHERE email IS NOT NULL AND email != ''")
            for name, email in cursor.fetchall():
                recipient_names.setdefault(email, name)
        except Exception:
            pass

        event_tables = [
            "sponsors",
            "expenses",
            "settlements",
            "payment_details",
            "committee_members",
            "sponsorship_items",
            "events",
            "prasad_seva",
            "ganesh_pooja_seating",
            "laddu_winners",
        ]
        try:
            cursor.execute("SELECT COUNT(*) FROM expenses WHERE receipt_blob IS NOT NULL")
            receipt_count = cursor.fetchone()[0] or 0
        except Exception:
            receipt_count = 0
        content_labels = {table_name: table_name.replace("_", " ").title() for table_name in event_tables}
        if receipt_count:
            content_labels["expense_receipts"] = f"Expense Receipts ({receipt_count})"
        content_options = list(content_labels)
        st.markdown("**Content to send**")
        content_select_col, content_clear_col = st.columns(2)
        with content_select_col:
            if st.button("☑️ Select All Content", use_container_width=True, key="select_all_event_content"):
                st.session_state["event_email_content"] = content_options
                st.rerun()
        with content_clear_col:
            if st.button("☐ Clear All Content", use_container_width=True, key="clear_all_event_content"):
                st.session_state["event_email_content"] = []
                st.rerun()
        if "event_email_content" not in st.session_state:
            st.session_state["event_email_content"] = content_options.copy()
        selected_content = st.multiselect(
            "Select content",
            options=content_options,
            default=content_options,
            format_func=lambda item: content_labels[item],
            key="event_email_content",
        )

        if notification_addresses:
            recipient_labels = {
                email: f"{recipient_names.get(email, 'Name not available')} | {email}"
                for email in notification_addresses
            }
            st.markdown("**Recipients**")
            recipient_table = pd.DataFrame([
                {"Name": recipient_names.get(email, "Name not available"), "Email": email}
                for email in notification_addresses
            ])
            st.dataframe(recipient_table, hide_index=True, use_container_width=True)
            select_col, clear_col = st.columns(2)
            with select_col:
                if st.button("☑️ Select All", use_container_width=True, key="select_all_event_emails"):
                    st.session_state["event_email_recipients"] = notification_addresses
                    st.rerun()
            with clear_col:
                if st.button("☐ Clear All", use_container_width=True, key="clear_all_event_emails"):
                    st.session_state["event_email_recipients"] = []
                    st.rerun()
            if "event_email_recipients" not in st.session_state:
                st.session_state["event_email_recipients"] = notification_addresses.copy()
            selected_recipients = st.multiselect(
                "Select recipients",
                options=notification_addresses,
                format_func=lambda email: recipient_labels[email],
                key="event_email_recipients",
            )
        else:
            selected_recipients = []
            st.warning("No committee member email addresses are configured. Add an email in Committee Members.")

        selected_content_names = [content_labels[item] for item in selected_content]
        content_summary = ", ".join(selected_content_names) if selected_content_names else "No content selected"
        st.markdown(
            f"""
            <div style="
                margin: 1rem 0 0.75rem;
                padding: 1rem 1.25rem;
                border: 1px solid #d7c2e8;
                border-left: 5px solid #6a1b9a;
                border-radius: 12px;
                background: linear-gradient(100deg, #fbf7ff 0%, #f1e8f8 100%);
                box-shadow: 0 3px 12px rgba(106, 27, 154, 0.12);
            ">
                <div style="color:#6a1b9a; font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.04em;">Ready to send</div>
                <div style="color:#34203f; font-size:1.15rem; font-weight:700; margin-top:0.2rem;">{len(selected_recipients)} recipient(s) · {len(selected_content)} content item(s)</div>
                <div style="color:#67556f; font-size:0.85rem; margin-top:0.35rem;">{content_summary}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("📧  Send Selected Event Details", type="primary", use_container_width=True, key="send_selected_event_details"):
            recipients = selected_recipients
            if not recipients:
                st.warning("Select at least one recipient before sending.")
            else:
                attachments = []
                exported_tables = []
                csv_files = []
                image_files = []
                for table_name in event_tables:
                    if table_name not in selected_content:
                        continue
                    try:
                        table_df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                        binary_columns = [
                            column for column in table_df.columns
                            if column.lower().endswith(("_blob", "_image"))
                        ]
                        if binary_columns:
                            table_df = table_df.drop(columns=binary_columns)
                        csv_bytes = table_df.to_csv(index=False).encode("utf-8")
                        attachments.append((
                            csv_bytes,
                            f"{table_name}.csv",
                            "text/csv",
                        ))
                        csv_files.append((f"{table_name}.csv", csv_bytes))
                        exported_tables.append(table_name)
                    except Exception:
                        continue

                if "expense_receipts" in selected_content:
                    try:
                        cursor.execute(
                            "SELECT id, receipt_path, receipt_blob FROM expenses "
                            "WHERE receipt_blob IS NOT NULL ORDER BY id"
                        )
                        for expense_id, receipt_path, receipt_blob in cursor.fetchall():
                            if isinstance(receipt_blob, memoryview):
                                receipt_bytes = receipt_blob.tobytes()
                            elif isinstance(receipt_blob, bytearray):
                                receipt_bytes = bytes(receipt_blob)
                            else:
                                receipt_bytes = receipt_blob
                            if not receipt_bytes:
                                continue
                            receipt_name = str(receipt_path or f"receipt_{expense_id}.bin").split("/")[-1]
                            attachments.append((
                                receipt_bytes,
                                f"receipt_{expense_id}_{receipt_name}",
                                "application/octet-stream",
                            ))
                            image_files.append((f"receipt_{expense_id}_{receipt_name}", receipt_bytes))
                    except Exception:
                        pass

                if csv_files or image_files:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                        for filename, file_bytes in csv_files:
                            archive.writestr(f"csv/{filename}", file_bytes)
                        for filename, file_bytes in image_files:
                            archive.writestr(f"images/{filename}", file_bytes)
                    attachments.append((
                        zip_buffer.getvalue(),
                        "ganesh_event_details.zip",
                        "application/zip",
                    ))

                if not attachments:
                    st.warning("No event data was available to attach.")
                else:
                    send_email(
                        "Ganesh Celebrations Event Details",
                        "Attached are the current event data exports and stored expense receipts.",
                        recipients,
                        attachments=attachments,
                    )
                    st.success(
                        f"Event details sent to {len(recipients)} recipient(s) "
                        f"with {len(exported_tables)} CSV file(s), "
                        f"{len(image_files)} image(s), and a combined ZIP archive."
                    )

    if menu == "Sponsorship Items" and item_action == "edit":
        if df.empty:
            st.info("No sponsorship items found.")
        else:
            st.subheader("Edit Sponsorship Item")
            selected_item_id = st.selectbox(
                "Select Item",
                df["id"].tolist(),
                format_func=lambda item_id: df.loc[df["id"] == item_id, "item"].iloc[0],
                key="sponsorship_item_edit_id",
            )
            item_row = df[df["id"] == selected_item_id].iloc[0]
            if st.session_state.get("sponsorship_item_edit_loaded_id") != selected_item_id:
                st.session_state["sponsorship_item_edit_name"] = str(item_row["item"] or "")
                st.session_state["sponsorship_item_edit_amount"] = float(item_row["amount"] or 0)
                st.session_state["sponsorship_item_edit_limit"] = int(item_row["sponsor_limit"] or 1)
                st.session_state["sponsorship_item_edit_loaded_id"] = selected_item_id
            with st.form("edit_sponsorship_item_form"):
                new_item_name = st.text_input("Item Name", key="sponsorship_item_edit_name")
                new_amount = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f", key="sponsorship_item_edit_amount")
                new_limit = st.number_input("Limit", min_value=1, step=1, key="sponsorship_item_edit_limit")
                edit_image = st.file_uploader(
                    "Replace Item Image (JPG/PNG, max 10MB)",
                    type=["jpg", "jpeg", "png"],
                    key=f"sponsorship_item_edit_image_{selected_item_id}",
                )
                update_item = st.form_submit_button("Update Item", use_container_width=True)
            if update_item:
                if not new_item_name.strip():
                    st.warning("Item name is required.")
                elif edit_image is not None and edit_image.size > 10 * 1024 * 1024:
                    st.error("Image file size should not exceed 10 MB.")
                elif edit_image is not None and edit_image.type not in ["image/jpeg", "image/png"]:
                    st.error("Only JPG and PNG files are allowed.")
                else:
                    try:
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
                        st.session_state[action_key] = None
                        st.session_state.pop("sponsorship_item_edit_loaded_id", None)
                        st.session_state["sponsorship_item_notice"] = "Sponsorship item updated."
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Failed to update sponsorship item: {e}")
            if st.button("Cancel", key="sponsorship_item_cancel_edit"):
                st.session_state[action_key] = None
                st.session_state.pop("sponsorship_item_edit_loaded_id", None)
                st.rerun()

    if menu == "Sponsorship Items" and item_action == "delete":
        if df.empty:
            st.info("No sponsorship items found.")
        else:
            st.subheader("Delete Sponsorship Item")
            selected_item_id = st.selectbox(
                "Select Item",
                df["id"].tolist(),
                format_func=lambda item_id: df.loc[df["id"] == item_id, "item"].iloc[0],
                key="sponsorship_item_delete_id",
            )
            item_row = df[df["id"] == selected_item_id].iloc[0]
            st.write(f"Item: **{item_row['item']}**")
            st.write(f"Amount: **${float(item_row['amount']):,.2f}**")
            st.write(f"Limit: **{int(item_row['sponsor_limit'])}**")
            delete_col, cancel_col = st.columns(2)
            if delete_col.button("Delete Item", key="sponsorship_item_confirm_delete", type="primary"):
                try:
                    cursor.execute("DELETE FROM sponsorship_items WHERE id=%s", (int(item_row["id"]),))
                    conn.commit()
                    st.session_state[action_key] = None
                    st.session_state["sponsorship_item_notice"] = "Sponsorship item deleted."
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Failed to delete sponsorship item: {e}")
            if cancel_col.button("Cancel", key="sponsorship_item_cancel_delete"):
                st.session_state[action_key] = None
                st.rerun()

    if menu == "Sponsorship Record":
        df_sponsors = pd.read_sql("SELECT * FROM sponsors ORDER BY id", conn)
        df_sponsors.columns = [c.lower() for c in df_sponsors.columns]
        if df_sponsors.empty:
            display_df_display = pd.DataFrame(columns=[
                "Name", "Email", "Mobile", "Apartment", "Gothram",
                "Sponsorship Item", "Type", "Donation/Sponsorship Amount",
            ])
        else:
            cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items")
            item_amounts = {}
            for item, amount, sponsor_limit in cursor.fetchall():
                try:
                    item_amounts[item] = float(amount) / int(sponsor_limit) if sponsor_limit else float(amount)
                except Exception:
                    item_amounts[item] = float(amount or 0)

            display_df = df_sponsors.copy()
            display_df["Type"] = display_df.apply(
                lambda row: "Sponsorship" if pd.notna(row["sponsorship"]) and str(row["sponsorship"]).strip()
                else "Donation" if float(row["donation"] or 0) > 0 else "",
                axis=1,
            )
            display_df["Donation/Sponsorship Amount"] = display_df.apply(
                lambda row: item_amounts.get(row["sponsorship"], 0.0)
                if row["Type"] == "Sponsorship" else float(row["donation"] or 0),
                axis=1,
            )
            display_df = display_df.drop(columns=["donation", "id"])
            columns = ["name", "email", "mobile", "apartment", "gothram", "sponsorship", "Type", "Donation/Sponsorship Amount"]
            display_df = display_df[[column for column in columns if column in display_df.columns]]
            display_df = display_df.rename(columns={column: column.replace("_", " ").title() for column in display_df.columns})
            display_df = display_df.rename(columns={"Sponsorship": "Sponsorship Item"})
            display_df_display = display_df.sort_values(by="Name").reset_index(drop=True)
            display_df_display.index = range(1, len(display_df_display) + 1)

        record_action_key = "sponsorship_record_action"
        if st.session_state.get(record_action_key) not in (None, "add", "edit", "delete"):
            st.session_state[record_action_key] = None
        record_notice = st.session_state.pop("sponsorship_record_notice", None)
        if record_notice:
            st.success(record_notice)
        st.markdown(
            """
            <style>
            .st-key-sponsorship_record_actions [data-testid="stHorizontalBlock"] { display:grid !important; grid-template-columns:repeat(3,minmax(0,1fr)) !important; gap:0.5rem !important; width:100% !important; }
            .st-key-sponsorship_record_actions [data-testid="column"], .st-key-sponsorship_record_actions [data-testid="stColumn"] { min-width:0 !important; width:auto !important; flex:initial !important; }
            .st-key-sponsorship_record_actions button { min-height:2.6rem !important; width:100% !important; padding:0.4rem 0.3rem !important; border:1px solid transparent !important; border-radius:8px !important; color:#fff !important; font-size:0.78rem !important; font-weight:800 !important; white-space:nowrap !important; box-shadow:0 4px 10px rgba(44,58,48,0.15) !important; }
            .st-key-sponsorship_record_add button { background:linear-gradient(110deg,#225b40,#347a55) !important; border-color:#b38a43 !important; }
            .st-key-sponsorship_record_edit button { background:linear-gradient(110deg,#176c70,#268b83) !important; border-color:#8bb7a8 !important; }
            .st-key-sponsorship_record_delete button { background:linear-gradient(110deg,#803b52,#a84d5e) !important; border-color:#c79782 !important; }
            @media (max-width:520px) { .st-key-sponsorship_record_actions button { min-height:2.4rem !important; padding:0.3rem 0.15rem !important; font-size:0.68rem !important; } }
            </style>
            """,
            unsafe_allow_html=True,
        )
        with st.container(key="sponsorship_record_actions"):
            action_columns = st.columns(3)
            if action_columns[0].button("➕ Add", key="sponsorship_record_add", use_container_width=True):
                st.session_state[record_action_key] = "add"
                st.rerun()
            if action_columns[1].button("✏️ Edit", key="sponsorship_record_edit", disabled=df_sponsors.empty, use_container_width=True):
                st.session_state[record_action_key] = "edit"
                st.session_state.pop("sponsorship_record_edit_loaded_id", None)
                st.rerun()
            if action_columns[2].button("🗑️ Delete", key="sponsorship_record_delete", disabled=df_sponsors.empty, use_container_width=True):
                st.session_state[record_action_key] = "delete"
                st.rerun()

        record_action = st.session_state.get(record_action_key)
        if record_action is None:
            if df_sponsors.empty:
                st.info("No sponsorship records found.")
            else:
                st.dataframe(display_df_display, hide_index=True, use_container_width=True)

        elif record_action == "add":
            st.subheader("Add Sponsorship Record")
            cursor.execute("SELECT item FROM sponsorship_items ORDER BY item")
            item_options = [row[0] for row in cursor.fetchall()]
            with st.form("add_sponsorship_record_form"):
                add_name = st.text_input("Name")
                add_email = st.text_input("Email Address (optional)")
                add_mobile = st.text_input("Mobile (optional, US format)")
                add_apartment = st.text_input("Apartment Number")
                add_gothram = st.text_input("Gothram (optional)")
                add_items = st.multiselect("Sponsorship Items", item_options)
                add_donation = st.number_input("Donation Amount", min_value=0.0, step=1.0, format="%.2f")
                save_record = st.form_submit_button("Add Record", use_container_width=True)
            if save_record:
                errors = []
                normalized_name = add_name.strip()
                normalized_apartment = add_apartment.strip()
                normalized_email = add_email.strip()
                phone_digits = re.sub(r"\D", "", add_mobile)
                phone_value = add_mobile.strip()
                if not normalized_name:
                    errors.append("Name is required.")
                if not normalized_apartment:
                    errors.append("Apartment number is required.")
                if not add_items and add_donation <= 0:
                    errors.append("Select a sponsorship item or enter a donation amount.")
                if normalized_email and ("@" not in normalized_email or not normalized_email.lower().endswith(".com")):
                    errors.append("Please enter a valid email address ending in .com.")
                if phone_value:
                    if len(phone_digits) != 10:
                        errors.append("Please enter a valid 10-digit US phone number.")
                    else:
                        phone_value = f"({phone_digits[:3]}) {phone_digits[3:6]}-{phone_digits[6:]}"
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        for item_name in add_items:
                            cursor.execute(
                                "INSERT INTO sponsors (name, email, gothram, mobile, apartment, sponsorship, donation, submitted_at) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)",
                                (normalized_name, normalized_email or None, add_gothram.strip() or None, phone_value or None, normalized_apartment, item_name, 0),
                            )
                        if add_donation > 0:
                            cursor.execute(
                                "INSERT INTO sponsors (name, email, gothram, mobile, apartment, sponsorship, donation, submitted_at) VALUES (%s, %s, %s, %s, %s, NULL, %s, CURRENT_TIMESTAMP)",
                                (normalized_name, normalized_email or None, add_gothram.strip() or None, phone_value or None, normalized_apartment, add_donation),
                            )
                        conn.commit()
                        notification_emails = get_notification_emails(cursor)
                        if notification_emails:
                            send_email(
                                "Sponsorship Record Added",
                                f"A sponsorship record was added for {normalized_name} ({normalized_apartment}).",
                                notification_emails,
                            )
                        st.session_state[record_action_key] = None
                        st.session_state["sponsorship_record_notice"] = "Sponsorship record added."
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Failed to add sponsorship record: {e}")
            if st.button("Cancel", key="sponsorship_record_cancel_add"):
                st.session_state[record_action_key] = None
                st.rerun()

        elif record_action in ("edit", "delete"):
            if df_sponsors.empty:
                st.info("No sponsorship records found.")
            else:
                cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items")
                item_amounts = {}
                for item_name, item_amount, sponsor_limit in cursor.fetchall():
                    try:
                        item_amounts[item_name] = float(item_amount) / int(sponsor_limit) if sponsor_limit else float(item_amount)
                    except Exception:
                        item_amounts[item_name] = float(item_amount or 0)

                def format_sponsor_record(sponsor_id):
                    selected = df_sponsors[df_sponsors["id"] == sponsor_id].iloc[0]
                    item_name = selected["sponsorship"] or "Donation"
                    amount = item_amounts.get(item_name, 0.0) if selected["sponsorship"] else float(selected["donation"] or 0)
                    return f"{selected['name']} · {item_name} · ${amount:,.2f} · #{sponsor_id}"

                record_id = st.selectbox(
                    "Select Sponsorship Record",
                    df_sponsors["id"].tolist(),
                    format_func=format_sponsor_record,
                    key=f"sponsorship_record_{record_action}_id",
                )
                sponsor_row = df_sponsors[df_sponsors["id"] == record_id].iloc[0]

                if record_action == "edit":
                    if st.session_state.get("sponsorship_record_edit_loaded_id") != record_id:
                        st.session_state["sponsorship_record_edit_name"] = str(sponsor_row["name"] or "")
                        st.session_state["sponsorship_record_edit_email"] = str(sponsor_row["email"] or "")
                        st.session_state["sponsorship_record_edit_mobile"] = str(sponsor_row["mobile"] or "")
                        st.session_state["sponsorship_record_edit_apartment"] = str(sponsor_row["apartment"] or "")
                        st.session_state["sponsorship_record_edit_gothram"] = str(sponsor_row["gothram"] or "")
                        st.session_state["sponsorship_record_edit_item"] = sponsor_row["sponsorship"] or "N/A"
                        st.session_state["sponsorship_record_edit_donation"] = float(sponsor_row["donation"] or 0)
                        st.session_state["sponsorship_record_edit_loaded_id"] = record_id
                    cursor.execute("SELECT item FROM sponsorship_items ORDER BY item")
                    sponsorship_items_list = [row[0] for row in cursor.fetchall()]
                    with st.form("edit_sponsorship_record_form"):
                        edit_name = st.text_input("Name", key="sponsorship_record_edit_name")
                        edit_email = st.text_input("Email Address (optional)", key="sponsorship_record_edit_email")
                        edit_mobile = st.text_input("Mobile (optional, US format)", key="sponsorship_record_edit_mobile")
                        edit_apartment = st.text_input("Apartment Number", key="sponsorship_record_edit_apartment")
                        edit_gothram = st.text_input("Gothram (optional)", key="sponsorship_record_edit_gothram")
                        edit_sponsorship_item = st.selectbox(
                            "Sponsorship Item",
                            ["N/A"] + sponsorship_items_list,
                            key="sponsorship_record_edit_item",
                        )
                        edit_donation = st.number_input("Donation Amount", min_value=0.0, step=1.0, format="%.2f", key="sponsorship_record_edit_donation")
                        update_record = st.form_submit_button("Update Record", use_container_width=True)
                    if update_record:
                        errors = []
                        if not edit_name.strip():
                            errors.append("Name is required.")
                        if not edit_apartment.strip():
                            errors.append("Apartment number is required.")
                        if edit_email.strip() and ("@" not in edit_email or not edit_email.strip().lower().endswith(".com")):
                            errors.append("Please enter a valid email address ending in .com.")
                        phone_digits = re.sub(r"\D", "", edit_mobile)
                        phone_value = edit_mobile.strip()
                        if phone_value:
                            if len(phone_digits) != 10:
                                errors.append("Please enter a valid 10-digit US phone number.")
                            else:
                                phone_value = f"({phone_digits[:3]}) {phone_digits[3:6]}-{phone_digits[6:]}"
                        if errors:
                            for error in errors:
                                st.error(error)
                        else:
                            sponsorship_value = None if edit_sponsorship_item == "N/A" else edit_sponsorship_item
                            try:
                                cursor.execute(
                                    "UPDATE sponsors SET name=%s, email=%s, mobile=%s, apartment=%s, gothram=%s, sponsorship=%s, donation=%s WHERE id=%s",
                                    (edit_name.strip(), edit_email.strip() or None, phone_value or None, edit_apartment.strip(), edit_gothram.strip() or None, sponsorship_value, edit_donation, int(record_id)),
                                )
                                conn.commit()
                                notification_emails = get_notification_emails(cursor)
                                if notification_emails:
                                    send_email(
                                        "Ganesh Chaturthi Sponsorship Record Updated",
                                        f"Sponsorship record updated for {edit_name.strip()} by {st.session_state.get('admin_full_name', 'Admin')}.",
                                        notification_emails,
                                    )
                                st.session_state[record_action_key] = None
                                st.session_state.pop("sponsorship_record_edit_loaded_id", None)
                                st.session_state["sponsorship_record_notice"] = "Sponsorship record updated."
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Failed to update sponsorship record: {e}")
                    if st.button("Cancel", key="sponsorship_record_cancel_edit"):
                        st.session_state[record_action_key] = None
                        st.session_state.pop("sponsorship_record_edit_loaded_id", None)
                        st.rerun()

                else:
                    st.write(f"Name: **{sponsor_row['name']}**")
                    st.write(f"Sponsorship Item: **{sponsor_row['sponsorship'] or 'Donation'}**")
                    st.write(f"Email: **{sponsor_row['email'] or 'Not provided'}**")
                    st.warning(f"To confirm deletion, enter the name '{sponsor_row['name']}' below.")
                    confirm_name = st.text_input("Confirm member name", key=f"sponsorship_record_delete_confirm_{record_id}")
                    delete_col, cancel_col = st.columns(2)
                    if delete_col.button("Delete Record", key="sponsorship_record_confirm_delete", type="primary"):
                        if confirm_name.strip() != str(sponsor_row["name"]):
                            st.error("Name entered does not match. Record not deleted.")
                        else:
                            try:
                                notification_emails = get_notification_emails(cursor)
                                cursor.execute("DELETE FROM sponsors WHERE id=%s", (int(record_id),))
                                conn.commit()
                                st.cache_data.clear()
                                if notification_emails:
                                    send_email(
                                        "Ganesh Chaturthi Sponsorship Record Deleted",
                                        f"Sponsorship record for {sponsor_row['name']} was deleted by {st.session_state.get('admin_full_name', 'Admin')}.",
                                        notification_emails,
                                    )
                                st.session_state[record_action_key] = None
                                st.session_state["sponsorship_record_notice"] = "Sponsorship record deleted."
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Failed to delete sponsorship record: {e}")
                    if cancel_col.button("Cancel", key="sponsorship_record_cancel_delete"):
                        st.session_state[record_action_key] = None
                        st.rerun()
    if menu == "Committee Members":
        try:
            cursor.execute("ALTER TABLE committee_members ADD COLUMN IF NOT EXISTS email TEXT")
            cursor.execute(
                "ALTER TABLE committee_members ADD COLUMN IF NOT EXISTS "
                "email_notification_enabled BOOLEAN NOT NULL DEFAULT FALSE"
            )
            cursor.execute("ALTER TABLE committee_members ALTER COLUMN email_notification_enabled SET DEFAULT FALSE")
            member_cols = pd.read_sql("SELECT * FROM committee_members LIMIT 0", conn).columns.str.lower().tolist()
            select_cols = ["id", "name", "apartment", "email", "email_notification_enabled", "recieve_cash_enable"]
            if "zelle_enable" in member_cols:
                select_cols.append("zelle_enable")
            df_members = pd.read_sql(f"SELECT {', '.join(select_cols)} FROM committee_members ORDER BY name", conn)
            df_members.columns = [c.lower() for c in df_members.columns]
            if "zelle_enable" not in df_members.columns:
                df_members["zelle_enable"] = False
        except Exception as e:
            st.error(f"Unable to load committee members: {e}")
            return

        action_key = "committee_member_action"
        if st.session_state.get(action_key) not in (None, "add", "edit", "delete"):
            st.session_state[action_key] = None
        member_notice = st.session_state.pop("committee_member_notice", None)
        if member_notice:
            st.success(member_notice)

        st.markdown(
            """
            <style>
            .st-key-committee_member_actions [data-testid="stHorizontalBlock"] {
                display: grid !important;
                grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
                gap: 0.5rem !important;
                width: 100% !important;
            }
            .st-key-committee_member_actions [data-testid="column"],
            .st-key-committee_member_actions [data-testid="stColumn"] {
                min-width: 0 !important;
                width: auto !important;
                flex: initial !important;
            }
            .st-key-committee_member_actions button {
                min-height: 2.65rem !important;
                width: 100% !important;
                padding: 0.45rem 0.35rem !important;
                border: 1px solid transparent !important;
                border-radius: 8px !important;
                color: #ffffff !important;
                font-size: 0.82rem !important;
                font-weight: 800 !important;
                white-space: nowrap !important;
                box-shadow: 0 4px 10px rgba(44, 58, 48, 0.16) !important;
                transition: transform 140ms ease, box-shadow 140ms ease;
            }
            .st-key-committee_member_add button {
                background: linear-gradient(110deg, #225b40, #347a55) !important;
                border-color: #b38a43 !important;
            }
            .st-key-committee_member_edit button {
                background: linear-gradient(110deg, #176c70, #268b83) !important;
                border-color: #8bb7a8 !important;
            }
            .st-key-committee_member_delete button {
                background: linear-gradient(110deg, #803b52, #a84d5e) !important;
                border-color: #c79782 !important;
            }
            .st-key-committee_member_actions button:hover {
                transform: translateY(-1px);
                box-shadow: 0 6px 14px rgba(44, 58, 48, 0.2) !important;
                color: #ffffff !important;
            }
            @media (max-width: 520px) {
                .st-key-committee_member_actions [data-testid="stHorizontalBlock"] {
                    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
                    gap: 0.35rem !important;
                }
                .st-key-committee_member_actions button {
                    min-height: 2.45rem !important;
                    padding: 0.35rem 0.15rem !important;
                    font-size: 0.7rem !important;
                }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        with st.container(key="committee_member_actions"):
            action_columns = st.columns(3)
            if action_columns[0].button("➕ Add", key="committee_member_add", use_container_width=True):
                st.session_state[action_key] = "add"
                st.rerun()
            if action_columns[1].button("✏️ Edit", key="committee_member_edit", disabled=df_members.empty, use_container_width=True):
                st.session_state[action_key] = "edit"
                st.session_state.pop("committee_member_edit_loaded_id", None)
                st.rerun()
            if action_columns[2].button("🗑️ Delete", key="committee_member_delete", disabled=df_members.empty, use_container_width=True):
                st.session_state[action_key] = "delete"
                st.rerun()

        member_action = st.session_state.get(action_key)
        if member_action is None:
            if df_members.empty:
                st.info("No committee members found.")
            else:
                display_members = df_members[
                    ["name", "apartment", "email", "email_notification_enabled", "recieve_cash_enable", "zelle_enable"]
                ].rename(columns={
                    "name": "Name",
                    "apartment": "Apartment",
                    "email": "Email",
                    "email_notification_enabled": "Notify",
                    "recieve_cash_enable": "Cash",
                    "zelle_enable": "Zelle",
                })
                st.dataframe(
                    display_members,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Notify": st.column_config.CheckboxColumn("Notify", help="Email notifications enabled"),
                        "Cash": st.column_config.CheckboxColumn("Cash"),
                        "Zelle": st.column_config.CheckboxColumn("Zelle"),
                    },
                )

        elif member_action == "add":
            st.subheader("Add Committee Member")
            with st.form("add_committee_member_form"):
                new_member_name = st.text_input("Member Name")
                new_member_apartment = st.text_input("Apartment Number")
                new_member_email = st.text_input("Email Address", placeholder="member@example.com")
                new_member_email_notification_enabled = st.checkbox("Enable email notifications", value=False)
                new_member_cash_enable = st.checkbox("Enable for cash collection", value=False)
                new_member_zelle_enable = st.checkbox("Enable for Zelle collection", value=False)
                add_member = st.form_submit_button("Add Member", use_container_width=True)
            if add_member:
                if not new_member_name.strip() or not new_member_apartment.strip():
                    st.warning("Member name and apartment number are required.")
                elif new_member_email_notification_enabled and not new_member_email.strip():
                    st.warning("An email address is required when email notifications are enabled.")
                else:
                    try:
                        cursor.execute(
                            "INSERT INTO committee_members (name, apartment, email, email_notification_enabled, recieve_cash_enable, zelle_enable) VALUES (%s, %s, %s, %s, %s, %s)",
                            (new_member_name.strip(), new_member_apartment.strip(), new_member_email.strip() or None, new_member_email_notification_enabled, new_member_cash_enable, new_member_zelle_enable),
                        )
                        conn.commit()
                        st.session_state[action_key] = None
                        st.session_state["committee_member_notice"] = "Committee member added."
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Failed to add committee member: {e}")
            if st.button("Cancel", key="committee_member_cancel_add"):
                st.session_state[action_key] = None
                st.rerun()

        elif member_action == "edit":
            if df_members.empty:
                st.info("No committee members found.")
            else:
                st.subheader("Edit Committee Member")
                selected_member_id = st.selectbox(
                    "Select Member",
                    df_members["id"].tolist(),
                    format_func=lambda member_id: df_members.loc[df_members["id"] == member_id, "name"].iloc[0],
                    key="committee_member_edit_id",
                )
                member_row = df_members[df_members["id"] == selected_member_id].iloc[0]
                if st.session_state.get("committee_member_edit_loaded_id") != selected_member_id:
                    st.session_state["committee_member_edit_name"] = str(member_row["name"] or "")
                    st.session_state["committee_member_edit_apartment"] = str(member_row["apartment"] or "")
                    st.session_state["committee_member_edit_email"] = str(member_row["email"] or "")
                    st.session_state["committee_member_edit_notify"] = bool(member_row["email_notification_enabled"])
                    st.session_state["committee_member_edit_cash"] = bool(member_row["recieve_cash_enable"])
                    st.session_state["committee_member_edit_zelle"] = bool(member_row["zelle_enable"])
                    st.session_state["committee_member_edit_loaded_id"] = selected_member_id
                with st.form("edit_committee_member_form"):
                    member_name = st.text_input("Member Name", key="committee_member_edit_name")
                    member_apartment = st.text_input("Apartment Number", key="committee_member_edit_apartment")
                    member_email = st.text_input("Email Address", key="committee_member_edit_email", placeholder="member@example.com")
                    member_email_notification_enabled = st.checkbox("Enable email notifications", key="committee_member_edit_notify")
                    member_cash_enable = st.checkbox("Enable for cash collection", key="committee_member_edit_cash")
                    member_zelle_enable = st.checkbox("Enable for Zelle collection", key="committee_member_edit_zelle")
                    update_member = st.form_submit_button("Update Member", use_container_width=True)
                if update_member:
                    if not member_name.strip() or not member_apartment.strip():
                        st.warning("Member name and apartment number are required.")
                    elif member_email_notification_enabled and not member_email.strip():
                        st.warning("An email address is required when email notifications are enabled.")
                    else:
                        try:
                            cursor.execute(
                                "UPDATE committee_members SET name=%s, apartment=%s, email=%s, email_notification_enabled=%s, recieve_cash_enable=%s, zelle_enable=%s WHERE id=%s",
                                (member_name.strip(), member_apartment.strip(), member_email.strip() or None, member_email_notification_enabled, member_cash_enable, member_zelle_enable, int(member_row["id"])),
                            )
                            conn.commit()
                            st.session_state[action_key] = None
                            st.session_state.pop("committee_member_edit_loaded_id", None)
                            st.session_state["committee_member_notice"] = "Committee member updated."
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Failed to update committee member: {e}")
                if st.button("Cancel", key="committee_member_cancel_edit"):
                    st.session_state[action_key] = None
                    st.session_state.pop("committee_member_edit_loaded_id", None)
                    st.rerun()

        elif member_action == "delete":
            if df_members.empty:
                st.info("No committee members found.")
            else:
                st.subheader("Delete Committee Member")
                selected_member_id = st.selectbox(
                    "Select Member",
                    df_members["id"].tolist(),
                    format_func=lambda member_id: df_members.loc[df_members["id"] == member_id, "name"].iloc[0],
                    key="committee_member_delete_id",
                )
                member_row = df_members[df_members["id"] == selected_member_id].iloc[0]
                st.write(f"Member: **{member_row['name']}**")
                st.write(f"Apartment: **{member_row['apartment']}**")
                st.write(f"Email: **{member_row.get('email') or 'Not set'}**")
                delete_col, cancel_col = st.columns(2)
                if delete_col.button("Delete Member", key="committee_member_confirm_delete", type="primary"):
                    try:
                        cursor.execute("DELETE FROM committee_members WHERE id=%s", (int(member_row["id"]),))
                        conn.commit()
                        st.session_state[action_key] = None
                        st.session_state["committee_member_notice"] = "Committee member deleted."
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Failed to delete committee member: {e}")
                if cancel_col.button("Cancel", key="committee_member_cancel_delete"):
                    st.session_state[action_key] = None
                    st.rerun()
