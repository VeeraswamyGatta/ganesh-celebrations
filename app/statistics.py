import streamlit as st

# Custom button styles for statistics section
st.markdown('''
    <style>
    .stButton > button {
        background-color: #1565C0 !important;
        color: #fff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        margin-bottom: 0.5em;
    }
    .stButton > button:hover {
        background-color: #1976d2 !important;
        color: #fff !important;
    }
    </style>
''', unsafe_allow_html=True)
import pandas as pd
import datetime
import altair as alt
from .db import get_connection
from .email_utils import send_email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def statistics_tab():
    # --- Combined PayPal + Cash Total ---
    st.session_state['active_tab'] = 'Statistics'
    is_admin = st.session_state.get('is_admin', False)
    # --- Audit trail: Your Full Name ---
    # Removed audit trail full name requirement as requested
    # (Removed duplicate display of audit name in statistics page)
    conn = get_connection()
    cursor = conn.cursor()

    # Build sponsorship records with the correct per-item amount.
    raw_df = pd.read_sql(
        "SELECT name, apartment, gothram, sponsorship, donation FROM sponsors ORDER BY id",
        conn,
    )
    raw_df.columns = [c.lower() for c in raw_df.columns]
    cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items")
    item_amt_map = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
    records = []
    for _, row in raw_df.iterrows():
        # pd.read_sql can return NaN (truthy) instead of None for NULL text columns, so use pd.notna()
        has_sponsorship = pd.notna(row['sponsorship']) and bool(str(row['sponsorship']).strip())
        if has_sponsorship:
            amt, limit = item_amt_map.get(row['sponsorship'], (0, 1))
            per_item_amt = round(amt / limit, 2) if limit else amt
            records.append({
                'Name': row['name'],
                'Apartment': row['apartment'],
                'Gothram': row['gothram'],
                'Amount': per_item_amt
            })
        if pd.notna(row['donation']) and row['donation'] > 0:
            records.append({
                'Name': row['name'],
                'Apartment': row['apartment'],
                'Gothram': row['gothram'],
                'Amount': row['donation']
            })
    df = pd.DataFrame(records)
    st.markdown("### 📋 Sponsorship Records")
    aggregation = {'Amount': 'sum'}
    if is_admin:
        aggregation.update({'Apartment': 'first', 'Gothram': 'first'})
    if not df.empty:
        df_display = df.groupby('Name', as_index=False, sort=True).agg(aggregation)
        df_display['Amount'] = df_display['Amount'].astype(float).round(2)
    else:
        df_display = pd.DataFrame(columns=['Name', 'Apartment', 'Gothram', 'Amount'])

    records_tab, chart_tab = st.tabs(["Records", "Chart"])
    with records_tab:
        display_columns = ['Name', 'Apartment', 'Gothram', 'Amount'] if is_admin else ['Name', 'Amount']
        table_df = df_display[display_columns].copy()
        table_df.index = range(1, len(table_df) + 1)

        filter_cols = st.columns(3 if is_admin else 2)
        name_filter = filter_cols[0].text_input("Filter by Name", value="", key="stats_name_filter")
        if is_admin:
            apartment_filter = filter_cols[1].text_input("Filter by Apartment", value="", key="stats_apartment_filter")
            gothram_filter = filter_cols[2].text_input("Filter by Gothram", value="", key="stats_gothram_filter")
        else:
            apartment_filter = ""
            gothram_filter = ""

        filtered_table = table_df.copy()
        if name_filter:
            filtered_table = filtered_table[filtered_table['Name'].astype(str).str.contains(name_filter, case=False, na=False)]
        if is_admin and apartment_filter:
            filtered_table = filtered_table[filtered_table['Apartment'].astype(str).str.contains(apartment_filter, case=False, na=False)]
        if is_admin and gothram_filter:
            filtered_table = filtered_table[filtered_table['Gothram'].astype(str).str.contains(gothram_filter, case=False, na=False)]

        filtered_table = filtered_table.reset_index(drop=True)
        filtered_table.index = range(1, len(filtered_table) + 1)

        st.dataframe(filtered_table, use_container_width=True)
        csv_records = filtered_table.copy()
        if not csv_records.empty and 'Amount' in csv_records.columns:
            csv_records['Amount'] = csv_records['Amount'].apply(lambda x: float(x))
        st.download_button(
            label="Download filtered records (CSV)",
            data=csv_records.to_csv(index=False),
            file_name="sponsorship_records_filtered.csv",
            mime="text/csv",
            key="stats_records_download"
        )

    with chart_tab:
        if df_display.empty:
            st.info("No sponsorship records available to chart.")
        else:
            chart_data = df_display[['Name', 'Amount']].sort_values('Amount', ascending=True)
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Amount:Q', title='Aggregated Amount'),
                y=alt.Y('Name:N', title='Name', sort='-x'),
                tooltip=[alt.Tooltip('Name:N', title='Name'), alt.Tooltip('Amount:Q', format='$,.2f')],
            ).properties(height=max(300, len(chart_data) * 35))
            st.altair_chart(chart, use_container_width=True)
    if not df.empty:
        df_amt = df.copy()
        df_amt['Amount'] = df_amt['Amount'].apply(lambda x: float(x))
        total_amt = df_amt['Amount'].sum()
        st.markdown(f"<div style='font-size:1.1em; color:#1565C0; font-weight:bold; margin-top:0.5em;'>Total Amount (All Records): <span style='color:#2E7D32;'>{total_amt:,.2f}</span></div>", unsafe_allow_html=True)

    def send_csv_email(subject, body, df_csv, filename):
        import io
        cursor.execute("SELECT email FROM notification_emails WHERE email IS NOT NULL AND email != ''")
        recipients = list({row[0].strip() for row in cursor.fetchall() if row[0]})
        if not recipients:
            st.warning("No notification emails found.")
            return
        EMAIL_SENDER = st.secrets["email_sender"]
        EMAIL_PASSWORD = st.secrets["email_password"]
        SMTP_SERVER = st.secrets["smtp_server"]
        SMTP_PORT = st.secrets["smtp_port"]
        df_csv_out = df_csv.copy()
        if not df_csv_out.empty:
            if 'Name' in df_csv_out.columns:
                df_csv_out = df_csv_out.sort_values(by=["Name"]).reset_index(drop=True)
            df_csv_out['Amount'] = df_csv_out['Amount'].apply(lambda x: float(x))
            total_amt = df_csv_out['Amount'].sum()
            total_row = {col: '' for col in df_csv_out.columns}
            total_row['Name'] = 'TOTAL'
            total_row['Amount'] = total_amt
            df_csv_out = pd.concat([df_csv_out, pd.DataFrame([total_row])], ignore_index=True)
        for recipient in recipients:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            csv_buffer = io.StringIO()
            df_csv_out.to_csv(csv_buffer, index=False)
            part = MIMEText(csv_buffer.getvalue(), 'csv')
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)
            try:
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                    server.starttls()
                    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                    server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
            except Exception as e:
                st.error(f"Failed to send email to {recipient}: {e}")

    if is_admin:
        if st.button("Send Sponsored Records Report (CSV)"):
            audit_name = st.session_state.get('admin_full_name', '')
            body = f"""
    <b>Sponsored Records Report (CSV attached)</b><br><br>
    Total records: {len(df)}<br>
    Date: {datetime.date.today()}<br>
    Triggered Report by: <b>{audit_name}</b><br>
    """
            send_csv_email(
                "Ganesh Chaturthi Sponsorship - Sponsored Records CSV Report",
                body,
                df,
                f"sponsored_records_{datetime.date.today()}.csv"
            )
            st.success("Sponsored records report sent!")

    # Available items report
    cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items ORDER BY id")
    items = cursor.fetchall()
    cursor.execute("SELECT sponsorship, COUNT(*) FROM sponsors GROUP BY sponsorship")
    counts = dict(cursor.fetchall())
    available_data = []
    for item, amount, limit in items:
        count = counts.get(item, 0)
        remaining = limit - count
        available_data.append({
            "Item": item,
            "Amount": amount,
            "Total Slot": limit,
            "Remaining Slot Available": remaining
        })
    df_available = pd.DataFrame(available_data)

    st.markdown("### 📋 Available Sponsorship Items")
    avail_filter_cols = st.columns([1.2, 1])
    avail_name_filter = avail_filter_cols[0].text_input("Filter available items by name", value="", key="stats_available_item_filter")
    avail_filtered = df_available.copy()
    if avail_name_filter:
        avail_filtered = avail_filtered[avail_filtered['Item'].astype(str).str.contains(avail_name_filter, case=False, na=False)]
    avail_filtered = avail_filtered.reset_index(drop=True)
    st.dataframe(avail_filtered, use_container_width=True)
    st.download_button(
        label="Download available items (CSV)",
        data=avail_filtered.to_csv(index=False),
        file_name="available_sponsorship_items.csv",
        mime="text/csv",
        key="stats_available_download"
    )

    # Move the CSV export button here
    if is_admin:
        if st.button("Send Available Items Report (CSV)", key="available_items_csv_btn"):
            audit_name = st.session_state.get('admin_full_name', '')
            body = f"""
    <b>Available Sponsorship Items Report (CSV attached)</b><br><br>
    Date: {datetime.date.today()}<br>
    Triggered Report by: <b>{audit_name}</b><br>
    """
            send_csv_email(
                "Ganesh Chaturthi Sponsorship - Available Items CSV Report",
                body,
                df_available,
                f"available_items_{datetime.date.today()}.csv"
            )
            st.success("Available items report sent!")


    # Removed Bar Chart of Sponsorships as requested
    # Removed Bar Chart of Sponsorships as requested
