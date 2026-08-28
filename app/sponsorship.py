import streamlit as st
import pandas as pd
import datetime
import re
from html import escape
from .db import get_connection
from .email_utils import send_email
from .notification_utils import get_notification_emails
import altair as alt
import requests
from bs4 import BeautifulSoup


@st.cache_data(ttl=300, show_spinner=False)
def get_paypal_total(paypal_link):
    """Fetch the public PayPal total at most once every five minutes."""
    if not paypal_link:
        return "(not configured)"
    try:
        response = requests.get(paypal_link, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        amount_tag = soup.find(class_="poolProgressBar-amount-raised")
        if amount_tag and amount_tag.text.strip():
            return amount_tag.text.strip()
        import re
        match = re.search(r"\$[0-9,.]+", response.text)
        return match.group(0) if match else "(not found)"
    except Exception:
        return "(unavailable)"

# Place all sponsorship and donation logic here

@st.fragment
def sponsorship_tab():
    # Helper to get total approved expense amount
    def get_total_expense_amount(conn):
        try:
            df = pd.read_sql("SELECT amount FROM expenses WHERE status = 'active'", conn)
            df.columns = [c.lower() for c in df.columns]
            if not df.empty:
                return df["amount"].astype(float).sum()
        except Exception:
            pass
        return 0.0
    st.session_state['active_tab'] = 'Sponsorship'
    conn = get_connection()
    cursor = conn.cursor()
    if (
        st.session_state.get('submission_in_progress', False)
        and not st.session_state.get('pending_sponsorship')
        and not st.session_state.get('submitted_data')
    ):
        st.session_state['submission_in_progress'] = False
    try:
        cursor.execute("SELECT name, apartment FROM committee_members WHERE recieve_cash_enable = TRUE ORDER BY name")
        cash_collectors = [
            f"{row[0]} (Apartment {row[1]})" for row in cursor.fetchall()
            if row[0] and row[1]
        ]
    except Exception:
        cash_collectors = []
    cash_payment_html = ""
    if cash_collectors:
        cash_payment_html = (
            "<br><b>Please reach out to one of these members for cash payment:</b><br>"
            + "<br>".join(
                f"<span style='color:#1565C0;'>{collector}</span>"
                for collector in cash_collectors
            )
        )
    st.markdown(
        """
        <style>
        .sponsor-option {
            background: linear-gradient(135deg, #fffdf5 0%, #f1f8e9 100%);
            border: 1px solid #c5d9c0;
            border-left: 5px solid #2e7d32;
            border-radius: 12px;
            padding: 14px 16px;
            margin: 8px 0 4px;
            box-shadow: 0 3px 10px rgba(46, 125, 50, 0.09);
        }
        .sponsor-option-closed {
            background: linear-gradient(135deg, #fffaf0 0%, #f5f5f5 100%);
            border-left-color: #90a4ae;
            box-shadow: 0 2px 8px rgba(84, 110, 122, 0.08);
        }
        .sponsor-option-title {
            color: #3e2723;
            font-size: 1.08rem;
            font-weight: 700;
        }
        .sponsor-option-price {
            color: #bf360c;
            font-size: 1.05rem;
            font-weight: 700;
            white-space: nowrap;
        }
        .sponsor-option-metrics {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 9px;
        }
        .sponsor-metric {
            background: rgba(255, 255, 255, 0.75);
            border: 1px solid #dce8d8;
            border-radius: 8px;
            color: #455a64;
            font-size: 0.88rem;
            padding: 5px 8px;
        }
        .sponsor-option-names {
            color: #546e7a;
            font-size: 0.9rem;
            margin-top: 10px;
        }
        .sponsor-option-names strong { color: #2e7d32; }
        .sponsor-name-label {
            display: block;
            margin-bottom: 0.45rem;
            color: #546e7a;
            font-size: 0.82rem;
            font-weight: 700;
        }
        .sponsor-name-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
        }
        .sponsor-name-chip {
            display: inline-block;
            padding: 0.3rem 0.55rem;
            border: 1px solid #dce8d8;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.78);
            color: #2e7d32;
            font-size: 0.8rem;
            font-weight: 700;
        }
        div[data-testid='stTextInput'] input,
        div[data-testid='stNumberInput'] input,
        div[data-testid='stTextArea'] textarea {
            background: #ffffff !important;
            border: 1px solid #b8c9b5 !important;
            border-radius: 9px !important;
            color: #263238 !important;
            min-height: 2.7rem;
            box-shadow: 0 1px 3px rgba(46, 125, 50, 0.08) !important;
        }
        div[data-testid='stTextInput'] input:focus,
        div[data-testid='stNumberInput'] input:focus,
        div[data-testid='stTextArea'] textarea:focus {
            border-color: #2e7d32 !important;
            box-shadow: 0 0 0 2px rgba(46, 125, 50, 0.16) !important;
        }
        div[data-testid='stTextInput'] input::placeholder,
        div[data-testid='stTextArea'] textarea::placeholder {
            color: #78909c !important;
            opacity: 1;
        }
        @media (max-width: 640px) {
            .sponsor-option { padding: 12px; }
            .sponsor-option-title { font-size: 1rem; }
            .sponsor-option-price { font-size: 0.98rem; }
            .sponsor-metric { font-size: 0.82rem; }
        }
        div[data-testid="stTooltipIcon"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- Combined PayPal + Cash Total ---
    # Get PayPal and Cash totals from payment_details table
    paypal_amount = 0.0
    zelle_amount = 0.0
    try:
        paypal_df = pd.read_sql("SELECT amount FROM payment_details WHERE payment_type = 'PayPal'", conn)
        paypal_df.columns = [c.lower() for c in paypal_df.columns]
        if not paypal_df.empty:
            paypal_amount = paypal_df["amount"].astype(float).sum()
    except Exception:
        paypal_amount = 0.0
    try:
        cash_df = pd.read_sql("SELECT amount FROM payment_details WHERE payment_type = 'Cash'", conn)
        cash_df.columns = [c.lower() for c in cash_df.columns]
        if not cash_df.empty:
            zelle_amount = cash_df["amount"].astype(float).sum()
    except Exception:
        zelle_amount = 0.0
    combined_total = paypal_amount + zelle_amount

    
    st.markdown("""
    <div style='background:linear-gradient(90deg,#fffde7 60%,#e3f2fd 100%); border-radius:14px; box-shadow:0 2px 12px #e0e0e0; padding:22px 28px; margin-bottom:22px; border:2px solid #ffe082;'>
        <div style='font-size:1.18em; font-family: Times New Roman, Calibri, Verdana, serif; color:#1565c0; font-weight:bold; margin-bottom:8px; text-align:center;'>
            🙏 Welcome to Terrazzo Ganesh Celebrations 2026!
        </div>
        <div style='font-size:1.13em; color: #E65100; margin-bottom:6px; text-align:center;'>
            <span style='font-size:1.08em; color:#444;'>📅 14th Sep 2026 to 20th Sep 2026 <span style='color:#388e3c;'>(7 days)</span></span><br>
            <span style='font-size:1.08em; color:#1565c0;'>📍 3C Garagge <span style='font-size:1.15em;vertical-align:middle;'>🙏</span> <span style='font-size:0.98em; color:#444;'>(Raghava)</span></span>
        </div>
        <div style='font-size:1.08em; color:#333; margin-bottom:6px;'>
            We warmly welcome you to join this year’s celebration by sponsoring any of the major items listed below. The cost for each item will be shared among the selected sponsors based on available slots. You may also contribute any amount of your choice as a donation.
        </div>
        <div style='font-size:1.08em; color:#388e3c; font-weight:500;'>
            Your generous support will help us make this year’s festivities vibrant and memorable for our entire community.
        </div>
    </div>
   """, unsafe_allow_html=True)





    # --- High-level statistics ---
    cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items")
    items = cursor.fetchall()
    total_slots = sum([row[2] for row in items])
    cursor.execute("SELECT sponsorship, donation FROM sponsors")
    sponsor_rows = cursor.fetchall()
    slots_filled = {}
    for s, _ in sponsor_rows:
        if s:
            slots_filled[s] = slots_filled.get(s, 0) + 1
    remaining_slots = sum([row[2] - slots_filled.get(row[0], 0) for row in items])
    total_donated = sum([row[1] for row in sponsor_rows if row[1]])
    cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items")
    sponsorship_items = cursor.fetchall()
    cursor.execute("SELECT sponsorship FROM sponsors")
    sponsored_counts = {}
    for row in cursor.fetchall():
        s = row[0]
        if s:
            sponsored_counts[s] = sponsored_counts.get(s, 0) + 1
    total_sponsored = 0
    for item, amount, limit in sponsorship_items:
        count = sponsored_counts.get(item, 0)
        if count > 0 and limit:
            total_sponsored += (amount / limit) * count
    total_sponsored = round(total_sponsored, 2)
    total_donated = round(total_donated, 2)
    total_combined = round(total_sponsored + total_donated, 2)
    paypal_link = st.secrets.get("paypal_link", "")
    total_paypal_received = get_paypal_total(paypal_link)
    blink_style = """
<style>
.blink-red {
    color: #d32f2f;
    font-weight: bold;
    animation: blinker 1s linear infinite;
}
@keyframes blinker {
    50% { opacity: 0; }
}
</style>
"""
    if remaining_slots > 0:
        slots_html = f"<span class='blink-red'>{remaining_slots}</span>"
        style_html = blink_style
    else:
        slots_html = f"<span style='color:#d32f2f;font-weight:bold'>{remaining_slots}</span>"
        style_html = ""

    total_received = float(combined_total)
    total_pending = float(total_combined) - total_received
    available_wallet = total_received - float(get_total_expense_amount(conn))

    # Today's submitted amount (sponsorships + donations submitted today)
    item_amt_map = {row[0]: (row[1], row[2]) for row in sponsorship_items}
    today_sponsored_amount = 0.0
    today_donated_amount = 0.0
    try:
        cursor.execute("SELECT sponsorship, donation, submitted_at FROM sponsors WHERE submitted_at IS NOT NULL")
        today_rows = cursor.fetchall()
        import pytz
        cst_tz = pytz.timezone('US/Central')
        utc_tz = pytz.utc
        today_date = datetime.datetime.now(cst_tz).date()
        for sponsorship_name, donation_amount, submitted_at in today_rows:
            try:
                if isinstance(submitted_at, str):
                    submitted_dt = pd.to_datetime(submitted_at, errors='coerce')
                    if pd.isna(submitted_dt):
                        continue
                    submitted_dt = submitted_dt.to_pydatetime()
                else:
                    submitted_dt = submitted_at
                # DB timestamps are stored in UTC; compare in US/Central "today"
                if submitted_dt.tzinfo is None:
                    submitted_dt = utc_tz.localize(submitted_dt)
                if submitted_dt.astimezone(cst_tz).date() != today_date:
                    continue
            except Exception:
                continue
            if sponsorship_name:
                amount, limit = item_amt_map.get(sponsorship_name, (0, 1))
                today_sponsored_amount += (amount / limit) if limit else amount
            if donation_amount:
                today_donated_amount += float(donation_amount)
    except Exception:
        pass
    today_total = round(today_sponsored_amount + today_donated_amount, 2)
    today_card_html = ""
    if today_total > 0:
        today_card_html = (
            "<div style='padding:1em; border-radius:14px; background:#ede7f6; border-top:4px solid #7e57c2;'>"
            "<div style='color:#5e35b1; font-size:0.86em; font-weight:700;'>📅 TODAY SUBMITTED</div>"
            f"<div style='margin-top:0.35em; font-size:1.35em; color:#4527a0; font-weight:800;'>${today_total:,.2f}</div>"
            "<div style='color:#6a5a8a; font-size:0.82em;'>Today's submissions</div>"
            "</div>"
        )

    st.markdown(f"""
{style_html}
<div style='max-width:1080px; margin:1.2em auto 1.5em; padding:1.2em; border:1px solid #d7ccc8; border-radius:20px; background:linear-gradient(135deg,#fffdf7 0%,#f1f8e9 100%); box-shadow:0 8px 24px rgba(93,64,55,0.12);'>
    <div style='display:flex; align-items:center; justify-content:space-between; gap:1em; margin:0 0 1em; padding:0 0.35em;'>
        <div style='font-size:1.45em; color:#3e2723; font-weight:800;'>Sponsorship &amp; Donation Summary</div>
    </div>
    <div style='display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:0.8em;'>
        <div style='padding:1em; border-radius:14px; background:#fff8e1; border-top:4px solid #ffb300;'>
            <div style='color:#8d6e63; font-size:0.86em; font-weight:700;'>🪔 SLOTS</div>
            <div style='margin-top:0.35em; font-size:1.55em; color:#3e2723; font-weight:800;'>{slots_html} <span style='color:#8d6e63; font-size:0.7em;'>/ {total_slots}</span></div>
            <div style='color:#795548; font-size:0.82em;'>Available sponsorship slots</div>
        </div>
        <div style='padding:1em; border-radius:14px; background:#e8f5e9; border-top:4px solid #43a047;'>
            <div style='color:#2e7d32; font-size:0.86em; font-weight:700;'>💰 SUBMITTED</div>
            <div style='margin-top:0.35em; font-size:1.35em; color:#1b5e20; font-weight:800;'>${total_combined:,.2f}</div>
            <div style='color:#558b2f; font-size:0.82em;'>${total_sponsored:,.2f} sponsored + ${total_donated:,.2f} donated</div>
        </div>
        <div style='padding:1em; border-radius:14px; background:#e3f2fd; border-top:4px solid #1e88e5;'>
            <div style='color:#1565c0; font-size:0.86em; font-weight:700;'>📥 AMOUNT RECEIVED</div>
            <div style='margin-top:0.35em; font-size:1.35em; color:#0d47a1; font-weight:800;'>${total_received:,.2f}</div>
            <div style='color:#546e7a; font-size:0.82em;'>Pending: ${total_pending:,.2f}</div>
        </div>
        <div style='padding:1em; border-radius:14px; background:#fce4ec; border-top:4px solid #d81b60;'>
            <div style='color:#ad1457; font-size:0.86em; font-weight:700;'>👛 AVAILABLE WALLET</div>
            <div style='margin-top:0.35em; font-size:1.35em; color:#880e4f; font-weight:800;'>${available_wallet:,.2f}</div>
            <div style='color:#6d4c41; font-size:0.82em;'>After approved expenses</div>
        </div>
        {today_card_html}
</div>
""", unsafe_allow_html=True)

    # --- Custom logic for user login and sponsorship limit ---
    show_submission_inputs = True
    sponsorship_limit = st.secrets.get("sponsorship_amount_limit", 0)
    # Only apply for user login, not admin
    if st.session_state.get("user_logged_in") and not st.session_state.get("admin_logged_in"):
        if sponsorship_limit and sponsorship_limit < total_combined:
            st.markdown("""
<div style='
    max-width: 520px;
    margin: 2em auto 1.5em auto;
    background: linear-gradient(90deg, #ffe0e0 0%, #fff3f3 100%);
    border-radius: 16px;
    box-shadow: 0 2px 12px rgba(211,47,47,0.08);
    padding: 1.7em 1.5em 1.2em 1.5em;
    border: 2px solid #d32f2f;
    text-align: center;
'>
    <div style='font-size:2em; color:#d32f2f; font-weight:bold; margin-bottom:0.3em;'>🎉 Sponsorship Goal Reached!</div>
    <div style='font-size:1.15em; color:#333; margin-bottom:0.7em;'>
        Thanks for reaching the sponsorship goal for the Ganesh Chaturthi celebration.<br>
        <span style='color:#d32f2f; font-weight:bold;'>We are sorry, direct submissions are now closed.</span>
    </div>
    <div style='font-size:1.08em; color:#1565c0; margin-bottom:0.5em;'>
        Please reach out in the <b>Ganesh Chaturthi celebrations 2025 WhatsApp group</b> to participate.<br>
        The team will collect your information and submit it for you.
    </div>
</div>
""", unsafe_allow_html=True)
            show_submission_inputs = False

    # Only show the info message if not on the submission thank you page and submission is allowed

    # Show submitted details if just submitted
    if st.session_state.get('show_submission') and st.session_state.get('submitted_data'):
        st.success('Thank you for your submission! Here are your submitted details:')
        submitted_data = st.session_state['submitted_data']
        # Build the card-style HTML in one string and render with unsafe_allow_html=True
        card_html = """
<div style='background:#f3e5f5;border-radius:12px;padding:1.5em 1.2em 1.2em 1.2em;margin-bottom:1em;box-shadow:0 2px 8px #d1c4e9;'>
    <h3 style='color:#6A1B9A;margin-top:0;margin-bottom:1em;'>Your Submitted Details</h3>
    <table style='width:100%;font-size:1.08em;'>
"""
        for k, v in submitted_data.items():
            if k == "How to Pay":
                card_html += """
    <tr><td colspan='2' style='padding-top:1em;padding-bottom:0.5em;'><b>How to Pay:</b></td></tr>
    <tr><td colspan='2' style='background:#ede7f6;padding:0.8em 1em;border-radius:8px;'>
                """ + v + """
    </td></tr>
                """
            elif isinstance(v, list):
                card_html += f"<tr><td style='font-weight:600;color:#6A1B9A;'>{k}:</td><td>{', '.join(str(i) for i in v)}</td></tr>"
            else:
                card_html += f"<tr><td style='font-weight:600;color:#6A1B9A;'>{k}:</td><td>{v}</td></tr>"
        card_html += "</table></div>"
        st.markdown(card_html, unsafe_allow_html=True)
        if st.button('🏠 Home', key='home_button'):
            st.session_state['show_submission'] = False
            st.session_state['submitted_data'] = None
            st.rerun()
        return

    def save_submission(pending):
        selected_items = pending["selected_items"]
        donation = pending["donation"]
        name_val = pending["name"]
        email = pending["email"]
        gothram = pending["gothram"]
        phone_fmt = pending["phone"]
        apartment = pending["apartment"]
        contributed_amount = pending["contributed_amount"]

        for item in selected_items:
            if hasattr(cursor, 'execute') and hasattr(cursor.connection, 'account'):
                cursor.execute("""
                    INSERT INTO sponsors (name, email, gothram, mobile, apartment, sponsorship, donation, submitted_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
                """, (name_val, email, gothram, phone_fmt, apartment, item, 0))
            else:
                cursor.execute("""
                    INSERT INTO sponsors (name, email, gothram, mobile, apartment, sponsorship, donation)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (name_val, email, gothram, phone_fmt, apartment, item, 0))
        if donation > 0:
            if hasattr(cursor, 'execute') and hasattr(cursor.connection, 'account'):
                cursor.execute("""
                    INSERT INTO sponsors (name, email, gothram, mobile, apartment, sponsorship, donation, submitted_at)
                    VALUES (%s, %s, %s, %s, %s, NULL, %s, CURRENT_TIMESTAMP())
                """, (name_val, email, gothram, phone_fmt, apartment, donation))
            else:
                cursor.execute("""
                    INSERT INTO sponsors (name, email, gothram, mobile, apartment, sponsorship, donation)
                    VALUES (%s, %s, %s, %s, %s, NULL, %s)
                """, (name_val, email, gothram, phone_fmt, apartment, donation))
        conn.commit()

        submitted_data = {
            "Name": name_val,
            "Email": email,
            "Gothram": gothram,
            "Mobile": phone_fmt,
            "Apartment": apartment
        }
        if selected_items:
            submitted_data["Sponsorship Items"] = selected_items.copy()
        if donation > 0:
            submitted_data["Donation"] = f"${donation:.2f}"
        if contributed_amount:
            submitted_data["Contributed Amount"] = f"${contributed_amount:.2f}"
        if cash_collectors:
            submitted_data["How to Pay"] = cash_payment_html.lstrip("<br>")

        notification_emails = get_notification_emails()
        recipients = list(notification_emails)
        if email.strip():
            recipients.append(email.strip())
        recipients = list(set(recipients))
        email_rows = f"""
  <tr><th>Name</th><td>{name_val}</td></tr>
  <tr><th>Email</th><td>{email}</td></tr>
  <tr><th>Gothram</th><td>{gothram}</td></tr>
  <tr><th>Mobile</th><td>{phone_fmt}</td></tr>
  <tr><th>Apartment</th><td>{apartment}</td></tr>
"""
        if selected_items:
            format_strings = ','.join(['%s'] * len(selected_items))
            cursor.execute(f"SELECT item, amount, sponsor_limit FROM sponsorship_items WHERE item IN ({format_strings})", tuple(selected_items))
            item_amounts = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
            for item in selected_items:
                amount, limit = item_amounts.get(item, (0, 1))
                per_item_amount = round(amount / limit, 2) if limit else amount
                email_rows += f"  <tr><th>Sponsorship Item</th><td>{item}</td><td><b>${per_item_amount:.2f}</b></td></tr>\n"
        if donation > 0:
            email_rows += f"  <tr><th>Donation</th><td>General Donation</td><td><b>${donation:.2f}</b></td></tr>\n"
        email_rows += f"  <tr><th colspan='2'>Total Contributed Amount</th><td><b>${contributed_amount:.2f}</b></td></tr>\n"
        send_email(
            "Ganesh Chaturthi Celebrations Sponsorship Program in Austin Texas",
            f"""
<b>New Sponsorship Submission</b><br><br>
<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;'>
{email_rows}
</table>
{cash_payment_html}
""",
            recipients
        )
        return submitted_data

    pending_submission = st.session_state.get("pending_sponsorship")
    if pending_submission:
        st.markdown("### Confirm Your Submission")
        confirmation_rows = [
            ("Name", pending_submission["name"]),
            ("Apartment", pending_submission["apartment"]),
            ("Email", pending_submission["email"] or "Not provided"),
            ("Gothram", pending_submission["gothram"] or "Not provided"),
            ("Mobile", pending_submission["phone"] or "Not provided"),
            ("Sponsorship Items", ", ".join(pending_submission["selected_items"]) or "None"),
            ("Donation (in addition to sponsorships)", f"${pending_submission['donation']:.2f}"),
            ("Total", f"${pending_submission['contributed_amount']:.2f}"),
        ]
        for label, value in confirmation_rows:
            label_col, value_col = st.columns([1, 2])
            label_col.markdown(f"**{label}**")
            value_col.write(value)
        confirm_col, edit_col = st.columns(2)
        submission_in_progress = st.session_state.get("sponsorship_confirmation_in_progress", False)
        if confirm_col.button(
            "Confirm Submission",
            type="primary",
            use_container_width=True,
            disabled=submission_in_progress,
        ):
            if submission_in_progress:
                st.stop()
            st.session_state["sponsorship_confirmation_in_progress"] = True
            try:
                with st.spinner("Saving your confirmed submission..."):
                    st.session_state["submitted_data"] = save_submission(pending_submission)
                st.session_state["pending_sponsorship"] = None
                st.session_state["show_submission"] = True
                st.rerun()
            except Exception as error:
                st.session_state["sponsorship_confirmation_in_progress"] = False
                conn.rollback()
                st.error(f"Submission failed: {error}")
        if edit_col.button("Edit Details", use_container_width=True, disabled=submission_in_progress):
            st.session_state["sponsorship_name"] = pending_submission["name"]
            st.session_state["sponsorship_apartment"] = pending_submission["apartment"]
            st.session_state["sponsorship_email"] = pending_submission["email"]
            st.session_state["sponsorship_gothram"] = pending_submission["gothram"]
            st.session_state["sponsorship_mobile"] = pending_submission["phone"]
            st.session_state["sponsorship_donation_amount"] = pending_submission["donation"]
            for item in pending_submission["available_items"]:
                st.session_state[item] = item in pending_submission["selected_items"]
            st.session_state["pending_sponsorship"] = None
            st.rerun()
        return

    sponsorship_form = st.form("sponsorship_form")
    # Only show submission inputs if allowed
    if show_submission_inputs:
        sponsorship_form.markdown("""
<div style='background:linear-gradient(135deg,#e3f2fd 0%,#e8eaf6 100%); border:1px solid #90caf9; border-radius:10px; padding:0.8em 1.1em; margin-bottom:0.8em;'>
    <div style='font-size:1.02em; color:#1565c0; line-height:1.55;'>
        🙏 Please fill in your details below to participate in the <strong>Ganesh Chaturthi celebrations</strong>.
        Your information helps us coordinate the festivities and keep you updated!
    </div>
</div>
""", unsafe_allow_html=True)
        name = sponsorship_form.text_input("👤 Your Name", placeholder="E.g., Raghava Rao", key="sponsorship_name")
        apartment = sponsorship_form.text_input("🏢 Your Apartment Number", placeholder="E.g., 305", key="sponsorship_apartment")
        email = sponsorship_form.text_input("📧 Email Address (optional)", placeholder="your@email.com", key="sponsorship_email")
        gothram = sponsorship_form.text_input("🪔 Gothram (optional)", placeholder="E.g., Bharadwaja, Kashyapa, etc.", key="sponsorship_gothram")
        mobile = sponsorship_form.text_input("📱 Mobile Number (optional)", placeholder="E.g., 5121234567", key="sponsorship_mobile")
    else:
        name = apartment = email = gothram = mobile = ""

    # --- High-level statistics ---
    # Get all sponsorship items
    cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items")
    items = cursor.fetchall()
    total_slots = sum([row[2] for row in items])
    # Get all sponsors
    cursor.execute("SELECT sponsorship, donation FROM sponsors")
    sponsor_rows = cursor.fetchall()
    # Calculate remaining slots
    slots_filled = {}
    for s, _ in sponsor_rows:
        if s:
            slots_filled[s] = slots_filled.get(s, 0) + 1
    remaining_slots = sum([row[2] - slots_filled.get(row[0], 0) for row in items])
    # Calculate totals
    total_donated = sum([row[1] for row in sponsor_rows if row[1]])
    # Calculate total sponsored amount (sum of all sponsorships)
    cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items")
    sponsorship_items = cursor.fetchall()
    cursor.execute("SELECT sponsorship FROM sponsors")
    sponsored_counts = {}
    for row in cursor.fetchall():
        s = row[0]
        if s:
            sponsored_counts[s] = sponsored_counts.get(s, 0) + 1
    total_sponsored = 0
    for item, amount, limit in sponsorship_items:
        count = sponsored_counts.get(item, 0)
        if count > 0 and limit:
            total_sponsored += (amount / limit) * count
    total_sponsored = round(total_sponsored, 2)
    total_donated = round(total_donated, 2)
    total_combined = round(total_sponsored + total_donated, 2)
    # Fetch PayPal pool amount from the public page
    paypal_link = st.secrets.get("paypal_link", "")
    total_paypal_received = get_paypal_total(paypal_link)
    # ...existing code...

    tab1, tab2 = st.tabs([
        "🛕 Sponsorship Items",
        "💰 Donation"
    ])
    selected_items = []
    with tab1:
        cursor.execute("SELECT sponsorship, COUNT(*) FROM sponsors GROUP BY sponsorship")
        counts = dict(cursor.fetchall())
        cursor.execute("SELECT item, amount, sponsor_limit FROM sponsorship_items ORDER BY id")
        rows = cursor.fetchall()
        rows = sorted(
            rows,
            key=lambda row: (
                row[2] - counts.get(row[0], 0) > 0,
                -(row[2] - counts.get(row[0], 0)),
            ),
        )
        fully_sponsored_heading_shown = False
        available_heading_shown = False
        for row in rows:
            item, cost, limit = row
            count = counts.get(item, 0)
            remaining = limit - count
            # Fetch sponsor names for this item
            cursor.execute("SELECT name FROM sponsors WHERE sponsorship = %s", (item,))
            sponsor_names = [n[0] for n in cursor.fetchall()]
            sponsor_names_html = "".join(
                f"<span class='sponsor-name-chip'>{escape(str(name))}</span>"
                for name in sponsor_names
            )
            if remaining > 0:
                remaining_str = f"<span class='blink' style='color:#d32f2f;font-weight:bold'>{remaining}</span>"
            else:
                remaining_str = f"{remaining}"
            per_slot = cost / limit if limit else cost
            def fmt_amt(val):
                return str(int(val)) if val == int(val) else str(val)
            # Modern card for fully sponsored items
            if remaining > 0:
                if not available_heading_shown:
                    st.markdown("### Available Sponsorships")
                    available_heading_shown = True
                st.markdown(
                    f"""
                    <div class='sponsor-option'>
                        <div style='display:flex;justify-content:space-between;align-items:flex-start;gap:12px;'>
                            <span class='sponsor-option-title'>{item}</span>
                            <span class='sponsor-option-price'>${fmt_amt(per_slot)} / slot</span>
                        </div>
                        <div class='sponsor-option-metrics'>
                            <span class='sponsor-metric'>Total: ${fmt_amt(cost)}</span>
                            <span class='sponsor-metric'>Slots: {limit}</span>
                            <span class='sponsor-metric'>Available: <strong>{remaining_str}</strong></span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if sponsor_names:
                    st.markdown(
                        f"<div class='sponsor-option-names'><span class='sponsor-name-label'>Sponsored by 🙏</span><div class='sponsor-name-list'>{sponsor_names_html}</div></div>",
                        unsafe_allow_html=True
                    )
                # Only show sponsor checkbox if slots are available
                if remaining > 0:
                    slot_word = "slot" if remaining == 1 else "slots"
                    item_selected = sponsorship_form.checkbox(
                        f"Select {item} **:green[${per_slot:,.2f}]** :red[**({remaining} {slot_word} available)**]",
                        key=item
                    )
                    if item_selected:
                        selected_items.append(item)
                st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
            else:
                if not fully_sponsored_heading_shown:
                    st.markdown("### Fully Sponsored Items")
                    fully_sponsored_heading_shown = True
                st.markdown(
                    f"""
                    <div class='sponsor-option sponsor-option-closed'>
                        <div style='display:flex;justify-content:space-between;align-items:flex-start;gap:12px;'>
                            <span class='sponsor-option-title'>{item}</span>
                            <span class='sponsor-option-price'>${fmt_amt(per_slot)} / slot</span>
                        </div>
                        <div class='sponsor-option-metrics'>
                            <span class='sponsor-metric'>Total: ${fmt_amt(cost)}</span>
                            <span class='sponsor-metric'>Slots: {limit}</span>
                            <span class='sponsor-metric'>Available: 0</span>
                        </div>
                        <div class='sponsor-option-names'>
                            <span class='sponsor-name-label'>Sponsored by 🙏</span>
                            <div class='sponsor-name-list'>{sponsor_names_html}</div>
                        </div>
                        <div style='margin-top:10px; color:#607d8b; font-size:0.86rem; font-weight:700;'>Fully sponsored</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.markdown("---")

    with tab2:
        # Show donor table before donation field
        cursor.execute("SELECT name, donation, submitted_at FROM sponsors WHERE donation IS NOT NULL AND donation > 0 ORDER BY submitted_at DESC")
        donor_rows = cursor.fetchall()
        # Only show donors with donation >= 5
        donor_rows_filtered = [row for row in donor_rows if row[1] >= 5]
        if donor_rows_filtered:
            donor_table_html = f"""
<div style='background:#ffffff; border-radius:10px; box-shadow:0 2px 8px rgba(46,125,50,0.08); padding:15px 18px; margin-bottom:16px; border:1px solid #d7e3d4;'>
    <div style='font-size:1.1em; font-weight:700; color:#2e7d32; margin-bottom:9px;'>🙏 Donor Support</div>
    <table style='width:100%; border-collapse:collapse; font-size:0.98em;'>
        <thead>
            <tr style='background:#f1f8e9;'>
                <th style='padding:8px 12px; color:#37474f; font-weight:600; border-bottom:1px solid #c5d9c0;'>Donor Name</th>
                <th style='padding:8px 12px; color:#37474f; font-weight:600; border-bottom:1px solid #c5d9c0;'>Amount</th>
                <th style='padding:8px 12px; color:#37474f; font-weight:600; border-bottom:1px solid #c5d9c0;'>Submitted</th>
            </tr>
        </thead>
        <tbody>
            {''.join([f"<tr><td style='padding:8px 12px; border-bottom:1px solid #edf3eb;'>{row[0]}</td><td style='padding:8px 12px; border-bottom:1px solid #edf3eb; color:#2e7d32; font-weight:bold;'>${row[1]}</td><td style='padding:8px 12px; border-bottom:1px solid #edf3eb; color:#546e7a;'>{row[2].strftime('%d-%b-%Y') if row[2] else ''}</td></tr>" for row in donor_rows_filtered])}
        </tbody>
    </table>
</div>
"""
            st.markdown(donor_table_html, unsafe_allow_html=True)
        cursor.execute("SELECT sponsor_limit FROM sponsorship_items")
        total_item_slots = sum([r[0] for r in cursor.fetchall()])
        cursor.execute("SELECT COUNT(*) FROM sponsors WHERE sponsorship IS NOT NULL AND sponsorship != ''")
        filled_item_slots = cursor.fetchone()[0]
        slots_available = (total_item_slots - filled_item_slots) > 0
        if slots_available:
            note_text = (
                "📌 Fill this only if you want to give <strong>MORE</strong> than your selected sponsorship items, "
                "or if you want to <strong>donate directly without selecting any sponsorship</strong>."
            )
        else:
            note_text = "📌 You can <strong>donate directly</strong> by entering an amount here."
        sponsorship_form.markdown(
            "<div style='font-size:1rem; font-weight:600; color:#31333F;'>Donation amount (optional)</div>"
            f"<div style='color:#e65100; font-size:0.9em; margin:4px 0 8px; line-height:1.5;'>{note_text}</div>",
            unsafe_allow_html=True
        )
        donation = sponsorship_form.number_input(
            "Donation amount (optional)",
            min_value=0.0,
            value=0.0,
            step=5.0,
            format="%.2f",
            key="sponsorship_donation_amount",
            label_visibility="collapsed"
        )

    def validate_us_phone(phone):
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 10:
            return True, f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return False, phone

    def format_name(name):
        return ' '.join(word.capitalize() for word in name.strip().split())

    validation_errors = st.session_state.get("sponsorship_validation_errors", [])
    if validation_errors:
        sponsorship_form.error("Please complete the required fields before submitting:")
        for error in validation_errors:
            sponsorship_form.markdown(f"- {error}")

    submit_disabled = st.session_state.get('submission_in_progress', False)
    def prepare_review():
        st.session_state['submission_in_progress'] = True
        errors = []
        name_val = format_name(name)
        if not name_val:
            errors.append("Name is required.")
        if not apartment.strip():
            errors.append("Apartment Number is required.")
        else:
            try:
                apt_num = int(apartment.strip())
                if not 100 <= apt_num <= 1600:
                    errors.append("Apartment Number must be between 100 and 1600.")
            except ValueError:
                errors.append("Apartment Number must be a number between 100 and 1600.")
        if not selected_items and donation == 0:
            errors.append("Please sponsor at least one item or donate an amount.")
        if email.strip() and ('@' not in email or not email.strip().lower().endswith('.com')):
            errors.append("Please enter a valid email address (must contain '@' and end with .com)")

        phone_fmt = mobile
        if mobile.strip():
            phone_valid, phone_fmt = validate_us_phone(mobile)
            if not phone_valid:
                errors.append("Please enter a valid 10-digit US phone number.")
        st.session_state['submission_in_progress'] = False
        if errors:
            st.session_state["sponsorship_validation_errors"] = errors
            return

        st.session_state["sponsorship_validation_errors"] = []
        sponsorship_total = 0
        if selected_items:
            format_strings = ','.join(['%s'] * len(selected_items))
            cursor.execute(
                f"SELECT amount, sponsor_limit FROM sponsorship_items WHERE item IN ({format_strings})",
                tuple(selected_items),
            )
            sponsorship_total = sum(row[0] / row[1] if row[1] else 0 for row in cursor.fetchall())
        contributed_amount = round(sponsorship_total + (donation if donation else 0), 2)
        st.session_state['pending_sponsorship'] = {
            "name": name_val,
            "email": email.strip(),
            "gothram": gothram.strip(),
            "phone": phone_fmt.strip(),
            "apartment": apartment.strip(),
            "selected_items": selected_items.copy(),
            "available_items": [row[0] for row in rows],
            "donation": float(donation or 0),
            "contributed_amount": contributed_amount,
        }

    if show_submission_inputs:
        sponsorship_form.form_submit_button(
            "Review",
            disabled=submit_disabled,
            type="primary",
            on_click=prepare_review,
        )
