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
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 0.35rem;
        margin-top: 0.75rem;
        padding: 0.3rem 0.35rem 0;
        border-bottom: 1px solid #c8e6c9;
    }
    div[data-testid="stTabs"] [data-baseweb="tab"] {
        min-height: 2.4rem;
        padding: 0.55rem 0.9rem;
        border-radius: 8px 8px 0 0;
        color: #546e7a;
        font-weight: 700;
    }
    div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        color: #1b5e20;
        background: #e8f5e9;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: #2e7d32;
        height: 3px;
    }
    @media (max-width: 640px) {
        div[data-testid="stTabs"] [data-baseweb="tab"] {
            padding: 0.5rem 0.7rem;
            font-size: 0.86rem;
        }
    }
    </style>
''', unsafe_allow_html=True)
import pandas as pd
import datetime
import pytz
import altair as alt
from html import escape
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
        "SELECT name, apartment, gothram, sponsorship, donation, submitted_at FROM sponsors ORDER BY id",
        conn,
    )
    raw_df.columns = [c.lower() for c in raw_df.columns]
    cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items")
    item_amt_map = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
    records = []
    daily_records = []
    cst_tz = pytz.timezone("America/Chicago")
    for _, row in raw_df.iterrows():
        # pd.read_sql can return NaN (truthy) instead of None for NULL text columns, so use pd.notna()
        has_sponsorship = pd.notna(row['sponsorship']) and bool(str(row['sponsorship']).strip())
        submission_date = None
        if pd.notna(row['submitted_at']):
            submitted_dt = pd.to_datetime(row['submitted_at'], errors='coerce', utc=True)
            if pd.notna(submitted_dt):
                submission_date = submitted_dt.tz_convert(cst_tz).date()
        if has_sponsorship:
            amt, limit = item_amt_map.get(row['sponsorship'], (0, 1))
            per_item_amt = float(round(amt / limit, 2) if limit else amt)
            records.append({
                'Name': row['name'],
                'Apartment': row['apartment'],
                'Gothram': row['gothram'],
                'Amount': per_item_amt
            })
            if submission_date:
                daily_records.append({'Date': submission_date, 'Amount': per_item_amt})
        if pd.notna(row['donation']) and row['donation'] > 0:
            donation_amt = float(row['donation'])
            records.append({
                'Name': row['name'],
                'Apartment': row['apartment'],
                'Gothram': row['gothram'],
                'Amount': donation_amt
            })
            if submission_date:
                daily_records.append({'Date': submission_date, 'Amount': donation_amt})
    df = pd.DataFrame(records)
    aggregation = {'Amount': 'sum'}
    if is_admin:
        aggregation.update({'Apartment': 'first', 'Gothram': 'first'})
    if not df.empty:
        df_display = df.groupby('Name', as_index=False, sort=True).agg(aggregation)
        df_display['Amount'] = df_display['Amount'].astype(float).round(2)
    else:
        df_display = pd.DataFrame(columns=['Name', 'Apartment', 'Gothram', 'Amount'])

    daily_df = pd.DataFrame(daily_records)
    daily_export = daily_df.reindex(columns=['Date', 'Amount'])
    daily_export['Date'] = daily_export['Date'].astype(str)
    cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items ORDER BY id")
    available_items = cursor.fetchall()
    cursor.execute("SELECT sponsorship, COUNT(*) FROM sponsors GROUP BY sponsorship")
    sponsorship_counts = dict(cursor.fetchall())
    df_available = pd.DataFrame([
        {
            "Item": item,
            "Amount": amount,
            "Total Slot": limit,
            "Remaining Slot Available": limit - sponsorship_counts.get(item, 0),
        }
        for item, amount, limit in available_items
    ])

    daily_tab, sponsored_records_tab, available_items_tab = st.tabs([
        "📈 Daily Submitted",
        "📋 Sponsored Records",
        "🧾 Available Items",
    ])
    with daily_tab:
        st.download_button(
            "⬇️ Download daily amounts",
            data=daily_export.to_csv(index=False),
            file_name="daily_submitted_sponsorship_amount.csv",
            mime="text/csv",
            key="stats_daily_amount_download",
            help="Download daily submitted amounts",
        )
        if daily_df.empty:
            st.info("No dated sponsorship submissions available to chart.")
        else:
            daily_df = daily_df.groupby('Date', as_index=False)['Amount'].sum()
            daily_df['Amount'] = daily_df['Amount'].astype(float).round(2)
            daily_chart = alt.Chart(daily_df).mark_bar(color='#8b1737', size=22).encode(
                x=alt.X('Amount:Q', title='Submitted Amount ($)', axis=alt.Axis(format='$,.0f')),
                y=alt.Y('Date:T', title='Submission Date', sort='ascending', axis=alt.Axis(format='%d %b')),
                tooltip=[alt.Tooltip('Date:T', title='Date', format='%d %b %Y'), alt.Tooltip('Amount:Q', title='Amount', format='$,.2f')],
            )
            daily_labels = alt.Chart(daily_df).mark_text(dx=8, align='left', color='#3e2723', fontSize=12).encode(
                x='Amount:Q',
                y=alt.Y('Date:T', sort='ascending'),
                text=alt.Text('Amount:Q', format='$,.2f'),
            )
            st.markdown(
                f"<div style='display:inline-flex; align-items:center; gap:0.45rem; margin:0.7rem 0 0.35rem; padding:0.5rem 0.8rem; border:1px solid #e6c66a; border-radius:9px; background:#fff8e1; color:#6a1b1b; font-size:0.9rem; font-weight:800;'>💰 <span>Total submitted</span><strong style='color:#8b1737;'>${daily_df['Amount'].sum():,.2f}</strong></div>",
                unsafe_allow_html=True,
            )
            st.altair_chart(
                (daily_chart + daily_labels).properties(height=max(300, len(daily_df) * 30)).configure(
                    font='Trebuchet MS',
                    axis=alt.Axis(labelFont='Trebuchet MS', titleFont='Trebuchet MS'),
                    legend=alt.Legend(labelFont='Trebuchet MS', titleFont='Trebuchet MS'),
                ),
                use_container_width=True,
            )

    with available_items_tab:
        avail_filtered = df_available.copy()
        st.dataframe(avail_filtered.reset_index(drop=True), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️",
            data=avail_filtered.to_csv(index=False),
            file_name="available_sponsorship_items.csv",
            mime="text/csv",
            key="stats_available_download",
            help="Download available sponsorship items",
        )

    with sponsored_records_tab:
        records_tab, chart_tab = st.tabs(["Records", "Chart"])
    with records_tab:
        display_columns = ['Name', 'Apartment', 'Gothram', 'Amount'] if is_admin else ['Name', 'Amount']
        table_df = df_display[display_columns].copy()
        table_df.index = range(1, len(table_df) + 1)

        with st.popover("🔍", help="Search sponsored records"):
            name_filter = st.text_input("Name", value="", key="stats_name_filter")
            if is_admin:
                apartment_filter = st.text_input("Apartment", value="", key="stats_apartment_filter")
                gothram_filter = st.text_input("Gothram", value="", key="stats_gothram_filter")
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
        if filtered_table.empty:
            st.info("No sponsored records match the selected filters.")
        else:
            stats_headers = filtered_table.columns.tolist()
            stats_header_html = "".join(f"<th>{escape(str(column))}</th>" for column in stats_headers)
            stats_rows_html = "".join(
                "<tr>"
                + "".join(
                    f"<td class='stats-name-cell'>{escape(str(value))}</td>"
                    if column == "Name"
                    else f"<td class='stats-amount-cell'>${float(value):,.2f}</td>"
                    if column == "Amount"
                    else f"<td>{escape(str(value))}</td>"
                    for column, value in row.items()
                )
                + "</tr>"
                for _, row in filtered_table.iterrows()
            )
            st.markdown(
                f"""
<style>
    .stats-table-wrap {{ margin-top:0.7rem; overflow-x:auto; border:1px solid #e4ddd7; border-radius:12px; box-shadow:0 3px 10px rgba(106,27,27,0.08); }}
    .stats-table {{ width:100%; table-layout:fixed; border-collapse:collapse; color:#3e2723; font-size:0.82rem; }}
    .stats-table th {{ padding:0.65rem 0.55rem; background:#6a1b1b; color:#fffaf0; font-size:0.72rem; font-weight:800; letter-spacing:0.04em; text-align:left; text-transform:uppercase; }}
    .stats-table th:last-child, .stats-table td:last-child {{ text-align:right; }}
    .stats-table td {{ padding:0.62rem 0.55rem; border-top:1px solid #eee4dc; vertical-align:top; overflow-wrap:anywhere; }}
    .stats-table tr:nth-child(even) td {{ background:#fffaf5; }}
    .stats-name-cell {{ color:#3e2723; font-weight:700; }}
    .stats-amount-cell {{ color:#8b1737; font-weight:800; white-space:nowrap; }}
    @media (max-width:640px) {{
        .stats-table {{ font-size:0.75rem; }}
        .stats-table th, .stats-table td {{ padding:0.55rem 0.38rem; }}
        .stats-table th {{ font-size:0.64rem; }}
    }}
</style>
<div class='stats-table-wrap'><table class='stats-table'><thead><tr>{stats_header_html}</tr></thead><tbody>{stats_rows_html}</tbody></table></div>
""",
                unsafe_allow_html=True,
            )

    with chart_tab:
        if df_display.empty:
            st.info("No sponsorship records available to chart.")
        else:
            chart_data = df_display[['Name', 'Amount']].sort_values('Amount', ascending=True)
            st.caption(f"Total sponsored: ${chart_data['Amount'].sum():,.2f}")
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Amount:Q', title='Aggregated Amount'),
                y=alt.Y('Name:N', title='Name', sort='-x'),
                tooltip=[alt.Tooltip('Name:N', title='Name'), alt.Tooltip('Amount:Q', format='$,.2f')],
            ).properties(height=max(300, len(chart_data) * 35))
            st.altair_chart(chart, use_container_width=True)
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

    # Removed Bar Chart of Sponsorships as requested
    # Removed Bar Chart of Sponsorships as requested
