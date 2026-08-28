import streamlit as st
import pandas as pd
import datetime
import re
import base64
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


SPONSORSHIP_ITEM_IMAGES = [
    ("garland", "https://images.unsplash.com/photo-1523438885200-e635ba2c371e?auto=format&fit=crop&w=240&q=80"),
    ("decoration", "https://images.unsplash.com/photo-1600707429839-9c5e08977c1d?auto=format&fit=crop&w=240&q=80"),
    ("priest", "https://images.unsplash.com/photo-1622551897017-b28fa6f8a5f5?auto=format&fit=crop&w=240&q=80"),
    ("prasadam", "https://images.unsplash.com/photo-1626804475297-41608ea09aeb?auto=format&fit=crop&w=240&q=80"),
    ("pooja", "https://images.unsplash.com/photo-1603006905003-be475563bc59?auto=format&fit=crop&w=240&q=80"),
    ("visarjan", "https://images.unsplash.com/photo-1524498250077-390f9e378fc0?auto=format&fit=crop&w=240&q=80"),
    ("nimarjan", "https://images.unsplash.com/photo-1524498250077-390f9e378fc0?auto=format&fit=crop&w=240&q=80"),
    ("idol", "https://images.unsplash.com/photo-1601058268499-e52658b8bb88?auto=format&fit=crop&w=240&q=80"),
]
SPONSORSHIP_DEFAULT_IMAGE = "https://images.unsplash.com/photo-1603006905003-be475563bc59?auto=format&fit=crop&w=240&q=80"


def get_sponsorship_item_image(item_name, image_blob=None, image_filename=None):
    """Match a sponsorship item name to a themed image by keyword."""
    if image_blob:
        if isinstance(image_blob, memoryview):
            image_blob = image_blob.tobytes()
        extension = (image_filename or "").lower().rsplit(".", 1)[-1]
        mime_type = "image/png" if extension == "png" else "image/jpeg"
        return f"data:{mime_type};base64,{base64.b64encode(image_blob).decode('ascii')}"
    name_lower = (item_name or "").lower()
    for keyword, image_url in SPONSORSHIP_ITEM_IMAGES:
        if keyword in name_lower:
            return image_url
    return SPONSORSHIP_DEFAULT_IMAGE


# Place all sponsorship and donation logic here

@st.fragment
def sponsorship_tab(dashboard_only=False):
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
        .sponsor-item-card {
            border: 1px solid #ead8a9;
            border-radius: 12px;
            background: #ffffff;
            padding: 0.45rem;
            margin: 0.4rem 0 0.3rem;
            box-shadow: 0 3px 10px rgba(93, 64, 55, 0.08);
        }
        .sponsor-item-image {
            display: block;
            width: 100%;
            height: auto;
            max-width: 100%;
            max-height: 170px;
            object-fit: contain;
            background: #faf7f0;
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }
        .sponsor-item-card-title {
            color: #8b1737;
            font-size: 0.78rem;
            font-weight: 800;
            text-align: center;
            line-height: 1.3;
        }
        .sponsor-item-card-meta {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 0.25rem 0.45rem;
            margin-top: 0.35rem;
            font-size: 0.7rem;
            text-align: center;
        }
        .sponsor-items-heading {
            margin: 0.4rem 0 0.9rem;
            color: #7d1736;
            font-size: 1.2rem;
            font-weight: 850;
            letter-spacing: 0.01em;
            border-left: 4px solid #d58a16;
            padding-left: 0.65rem;
        }
        .sponsor-item-amount {
            color: #8b1737;
            font-weight: 800;
        }
        .sponsor-item-availability {
            color: #2e7d32;
            font-weight: 700;
        }
        div[data-testid='stForm'] .stHorizontalBlock {
            flex-wrap: nowrap !important;
            align-items: center;
        }
        div[data-testid='stForm'] .stHorizontalBlock > div {
            min-width: 0 !important;
        }
        div[data-testid='stForm'] div[data-testid='stCheckbox']:has(input[id*="sponsor_toggle_"]) label p:before {
            font-size: 0.72rem;
            white-space: nowrap;
        }
        div[data-testid='stCheckbox']:has(input[id*="sponsor_toggle_"]) {
            margin-top: 0.4rem;
        }
        div[data-testid='stCheckbox']:has(input[id*="sponsor_toggle_"]) label {
            display: flex !important;
            align-items: center;
            justify-content: center;
            width: 100%;
            min-height: 2.2rem;
            padding: 0.35rem 0.45rem;
            border: 1px solid #8b1737;
            border-radius: 999px;
            background: linear-gradient(135deg, #8b1737, #bd4260);
            box-shadow: 0 3px 8px rgba(139, 23, 55, 0.2);
            cursor: pointer;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        div[data-testid='stForm'] div[data-testid='stCheckbox'] label {
            display: flex !important;
            align-items: center;
            justify-content: center;
            min-height: 2.2rem;
            padding: 0.35rem 0.55rem;
            border: 1px solid #8b1737;
            border-radius: 999px;
            background: linear-gradient(135deg, #8b1737, #bd4260);
            box-shadow: 0 3px 8px rgba(139, 23, 55, 0.2);
            cursor: pointer;
        }
        div[data-testid='stForm'] div[data-testid='stCheckbox'] label p {
            color: #ffffff !important;
            font-size: 0.76rem !important;
            font-weight: 800 !important;
            white-space: nowrap;
        }
        div[data-testid='stForm'] div[data-testid='stCheckbox'] label span[data-baseweb="checkbox"] {
            display: none;
        }
        div[data-testid='stForm'] div[data-testid='stCheckbox']:has(input:checked) label {
            border-color: #236b2a;
            background: linear-gradient(135deg, #236b2a, #43a047);
            box-shadow: 0 3px 8px rgba(46, 125, 50, 0.24);
        }
        div[data-testid='stCheckbox']:has(input[id*="sponsor_toggle_"]) label:hover {
            transform: translateY(-1px);
            box-shadow: 0 5px 12px rgba(139, 23, 55, 0.3);
        }
        div[data-testid='stCheckbox']:has(input[id*="sponsor_toggle_"]) label p {
            color: #ffffff !important;
            font-weight: 800 !important;
            margin: 0 !important;
            font-size: 0 !important;
        }
        div[data-testid='stCheckbox']:has(input[id*="sponsor_toggle_"]) label p:before {
            content: "Sponsor Now";
            font-size: 0.9rem;
        }
        div[data-testid='stCheckbox']:has(input[id*="sponsor_toggle_"]:checked) label {
            border-color: #236b2a;
            background: linear-gradient(135deg, #236b2a, #43a047);
            box-shadow: 0 3px 8px rgba(46, 125, 50, 0.24);
        }
        div[data-testid='stCheckbox']:has(input[id*="sponsor_toggle_"]:checked) label p:before {
            content: "\2713 Selected (tap to remove)";
            font-size: 0.82rem;
        }
        div[data-testid='stCheckbox']:has(input[id*="sponsor_toggle_"]) label span[data-baseweb="checkbox"] {
            display: none;
        }
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
            .sponsorship-summary { padding: 0.8em !important; }
            .sponsorship-summary-title { font-size: 1.12em !important; }
            .sponsorship-summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 0.55em !important; }
            .sponsorship-summary-card { padding: 0.7em !important; }
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
    slots_filled_count = total_slots - remaining_slots
    slot_pct = round((slots_filled_count / total_slots * 100), 1) if total_slots else 0
    collection_pct = round((total_received / total_combined * 100), 1) if total_combined else 0

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
            "<div style='padding:1.1em; border-radius:14px; background:#ede7f6; border-top:4px solid #7e57c2; box-shadow:0 3px 10px rgba(126,87,194,0.12);'>"
            "<div style='color:#5e35b1; font-size:0.86em; font-weight:700;'>📅 TODAY SUBMITTED</div>"
            f"<div style='margin-top:0.35em; font-size:1.4em; color:#4527a0; font-weight:800;'>${today_total:,.2f}</div>"
            "<div style='color:#6a5a8a; font-size:0.82em;'>Today's submissions</div>"
            "</div>"
        )

    if dashboard_only:
        st.markdown("""
<div style='margin:0.65rem 0 0.85rem; padding:0.9rem 1rem; border:1px solid #d8e2cd; border-left:5px solid #2e7d32; border-radius:10px; background:linear-gradient(110deg,#fffdf3,#edf7ee);'>
    <div style='color:#1b5e20; font-size:1rem; font-weight:800;'>Welcome to Terrazzo Ganesh Celebrations 2026!</div>
    <div style='margin-top:0.28rem; color:#455a64; font-size:0.88rem; line-height:1.5;'>
        📅 14th Sep 2026 to 20th Sep 2026 <span style='color:#2e7d32;'>(7 days)</span><br>
        📍 3C Garagge 🙏 (Raghava)
    </div>
    <div style='margin-top:0.55rem; color:#37474f; font-size:0.87rem; line-height:1.55;'>
        We warmly welcome you to join this year’s celebration by sponsoring any of the major items listed below. The cost for each item will be shared among the selected sponsors based on available slots. You may also contribute any amount of your choice as a donation.
    </div>
    <div style='margin-top:0.42rem; color:#2e7d32; font-size:0.87rem; font-weight:700; line-height:1.5;'>
        Your generous support will help us make this year’s festivities vibrant and memorable for our entire community.
    </div>
</div>
""", unsafe_allow_html=True)
        st.markdown(f"""
{style_html}
<div class='sponsorship-summary' style='max-width:1080px; margin:1.2em auto 1.5em; padding:1.2em; border:1px solid #d7ccc8; border-radius:20px; background:linear-gradient(135deg,#fffdf7 0%,#f1f8e9 100%); box-shadow:0 8px 24px rgba(93,64,55,0.12);'>
    <div style='display:flex; align-items:center; justify-content:space-between; gap:1em; margin:0 0 1em; padding:0 0.35em;'>
        <div class='sponsorship-summary-title' style='font-size:1.45em; color:#3e2723; font-weight:800;'>Sponsorship &amp; Donation Summary</div>
    </div>
    <div class='sponsorship-summary-grid' style='display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:0.8em;'>
        <div class='sponsorship-summary-card' style='padding:1.1em; border-radius:14px; background:#fff8e1; border-top:4px solid #ffb300; box-shadow:0 3px 10px rgba(255,179,0,0.12);'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
                <span style='color:#8d6e63; font-size:0.86em; font-weight:700;'>🪔 SLOTS</span>
                <span style='background:#ffe082; color:#5d4037; font-size:0.75rem; font-weight:800; padding:2px 7px; border-radius:8px;'>{slot_pct}% filled</span>
            </div>
            <div style='margin-top:0.35em; font-size:1.55em; color:#3e2723; font-weight:800;'>{slots_html} <span style='color:#8d6e63; font-size:0.7em;'>/ {total_slots}</span></div>
            <div style='color:#795548; font-size:0.82em; margin-top:0.2em;'>{slots_filled_count} filled &bull; {remaining_slots} open</div>
            <div style='width:100%; background:#ffe082; height:6px; border-radius:99px; margin-top:0.5em; overflow:hidden;'>
                <div style='width:{min(slot_pct, 100.0)}%; background:#f57c00; height:100%; border-radius:99px;'></div>
            </div>
        </div>
        <div class='sponsorship-summary-card' style='padding:1.1em; border-radius:14px; background:#e8f5e9; border-top:4px solid #43a047; box-shadow:0 3px 10px rgba(67,160,71,0.12);'>
            <div style='color:#2e7d32; font-size:0.86em; font-weight:700;'>💰 SUBMITTED</div>
            <div style='margin-top:0.35em; font-size:1.4em; color:#1b5e20; font-weight:800;'>${total_combined:,.2f}</div>
            <div style='color:#558b2f; font-size:0.82em; margin-top:0.2em;'>${total_sponsored:,.2f} sponsored + ${total_donated:,.2f} donated</div>
            <div style='color:#7cb342; font-size:0.75em; margin-top:0.45em;'>Pledged by community</div>
        </div>
        <div class='sponsorship-summary-card' style='padding:1.1em; border-radius:14px; background:#e3f2fd; border-top:4px solid #1e88e5; box-shadow:0 3px 10px rgba(30,136,229,0.12);'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
                <span style='color:#1565c0; font-size:0.86em; font-weight:700;'>📥 AMOUNT RECEIVED</span>
                <span style='background:#bbdefb; color:#0d47a1; font-size:0.75rem; font-weight:800; padding:2px 7px; border-radius:8px;'>{collection_pct}%</span>
            </div>
            <div style='margin-top:0.35em; font-size:1.4em; color:#0d47a1; font-weight:800;'>${total_received:,.2f}</div>
            <div style='color:#546e7a; font-size:0.82em; margin-top:0.2em;'>Pending: <strong>${total_pending:,.2f}</strong></div>
            <div style='width:100%; background:#bbdefb; height:6px; border-radius:99px; margin-top:0.5em; overflow:hidden;'>
                <div style='width:{min(collection_pct, 100.0)}%; background:#1976d2; height:100%; border-radius:99px;'></div>
            </div>
        </div>
        <div class='sponsorship-summary-card' style='padding:1.1em; border-radius:14px; background:#fce4ec; border-top:4px solid #d81b60; box-shadow:0 3px 10px rgba(216,27,96,0.12);'>
            <div style='color:#ad1457; font-size:0.86em; font-weight:700;'>👛 AVAILABLE WALLET</div>
            <div style='margin-top:0.35em; font-size:1.4em; color:#880e4f; font-weight:800;'>${available_wallet:,.2f}</div>
            <div style='color:#6d4c41; font-size:0.82em; margin-top:0.2em;'>Total received &minus; approved expenses</div>
            <div style='color:#ad1457; font-size:0.75em; margin-top:0.45em;'>Net funds ready for use</div>
        </div>
        {today_card_html}
</div>
""", unsafe_allow_html=True)
        sponsored_tab, donations_tab = st.tabs(["Sponsored Items", "Donations"])
        with sponsored_tab:
            cursor.execute("SELECT sponsorship, COUNT(*) FROM sponsors WHERE sponsorship IS NOT NULL AND sponsorship != '' GROUP BY sponsorship")
            sponsored_counts = dict(cursor.fetchall())
            cursor.execute("SELECT item, amount, sponsor_limit, image_blob, image_filename FROM sponsorship_items ORDER BY id")
            dashboard_items = cursor.fetchall()
            if dashboard_items:
                # Show 0 available slots (fully sponsored) first with distinct highlight!
                dashboard_items = sorted(
                    dashboard_items,
                    key=lambda row: (
                        (row[2] - sponsored_counts.get(row[0], 0)) > 0,  # 0 available comes first (False < True)
                        -(sponsored_counts.get(row[0], 0)),             # most sponsored next
                        row[0]                                          # alphabetical
                    )
                )
                for item_name, cost, sponsor_limit, image_blob, image_filename in dashboard_items:
                    sponsor_count = sponsored_counts.get(item_name, 0)
                    available_count = sponsor_limit - sponsor_count
                    item_slot_pct = round((sponsor_count / sponsor_limit * 100), 1) if sponsor_limit else 0
                    cursor.execute("SELECT name FROM sponsors WHERE sponsorship = %s", (item_name,))
                    sponsor_names = [escape(str(row[0])) for row in cursor.fetchall() if row[0]]
                    sponsor_chips = "".join(
                        f"<span class='sponsor-name-chip'>{name}</span>" for name in sponsor_names
                    ) or "<span style='color:#78909c; font-size:0.84rem;'>No sponsors yet</span>"
                    image_url = get_sponsorship_item_image(item_name, image_blob, image_filename)
                    
                    if available_count <= 0:
                        card_bg = "linear-gradient(135deg, #f9fff8 0%, #edf7ed 100%)"
                        border_style = "border: 1.5px solid #a5d6a7; border-left: 6px solid #2e7d32;"
                        badge_html = "<span style='background:#2e7d32; color:#ffffff; font-size:0.74rem; font-weight:800; padding:2px 8px; border-radius:12px; letter-spacing:0.02em;'>🎉 FULLY SPONSORED</span>"
                        avail_html = (
                            "<div style='margin-top:0.34rem;'>"
                            "<div style='display:flex; justify-content:space-between; align-items:center;'>"
                            f"<span style='color:#2e7d32; font-size:0.82rem; font-weight:800;'>✅ All {sponsor_limit} slots filled</span>"
                            "<span style='background:#c8e6c9; color:#1b5e20; font-size:0.72rem; font-weight:800; padding:1px 6px; border-radius:6px;'>100%</span>"
                            "</div>"
                            "<div style='width:100%; background:#c8e6c9; height:6px; border-radius:99px; margin-top:0.3em; overflow:hidden;'>"
                            "<div style='width:100%; background:#2e7d32; height:100%; border-radius:99px;'></div>"
                            "</div>"
                            "</div>"
                        )
                    else:
                        card_bg = "linear-gradient(135deg, #fffdf8 0%, #fffbf2 100%)"
                        border_style = "border: 1px solid #e0d7c6; border-left: 6px solid #e65100;"
                        badge_html = f"<span style='background:#fff3e0; color:#e65100; font-size:0.74rem; font-weight:700; padding:2px 8px; border-radius:12px;'>⏳ {available_count} open</span>"
                        avail_html = (
                            "<div style='margin-top:0.34rem;'>"
                            "<div style='display:flex; justify-content:space-between; align-items:center;'>"
                            f"<span style='color:#d84315; font-size:0.82rem; font-weight:800;'>{sponsor_count} of {sponsor_limit} filled &bull; <span style='color:#e65100; font-weight:700;'>{available_count} open</span></span>"
                            f"<span style='background:#ffe082; color:#5d4037; font-size:0.72rem; font-weight:800; padding:1px 6px; border-radius:6px;'>{item_slot_pct}%</span>"
                            "</div>"
                            "<div style='width:100%; background:#ffe082; height:6px; border-radius:99px; margin-top:0.3em; overflow:hidden;'>"
                            f"<div style='width:{min(item_slot_pct, 100.0)}%; background:#f57c00; height:100%; border-radius:99px;'></div>"
                            "</div>"
                            "</div>"
                        )

                    card_html = (
                        f"<div class='sponsor-option' style='display:flex; gap:0.8rem; margin:0.65rem 0; padding:0.85rem; {border_style} background:{card_bg}; border-radius:12px; box-shadow:0 3px 10px rgba(0,0,0,0.06);'>"
                        f"<img src='{image_url}' alt='{escape(str(item_name))}' style='width:76px; height:76px; flex:0 0 76px; object-fit:cover; border-radius:8px; border:1px solid #ead8a9;'>"
                        "<div style='min-width:0; flex:1;'>"
                        "<div style='display:flex; justify-content:space-between; align-items:flex-start; gap:0.5rem; flex-wrap:wrap;'>"
                        f"<strong style='color:#3e2723; font-size:0.96rem; line-height:1.3;'>{escape(str(item_name))}</strong>"
                        "<div style='display:flex; align-items:center; gap:0.4rem;'>"
                        f"{badge_html}"
                        f"<span style='white-space:nowrap; color:#bf360c; font-size:0.85rem; font-weight:800;'>${cost / sponsor_limit:,.2f}</span>"
                        "</div>"
                        "</div>"
                        f"{avail_html}"
                        "<div style='margin-top:0.38rem; color:#546e7a; font-size:0.78rem;'>Sponsored by</div>"
                        f"<div class='sponsor-name-list' style='margin-top:0.18rem;'>{sponsor_chips}</div>"
                        "</div>"
                        "</div>"
                    )
                    st.markdown(card_html, unsafe_allow_html=True)
            else:
                st.info("No sponsorships have been submitted yet.")
        with donations_tab:
            cursor.execute("SELECT name, donation, submitted_at FROM sponsors WHERE donation IS NOT NULL AND donation > 0 ORDER BY submitted_at DESC")
            donor_rows = cursor.fetchall()
            if donor_rows:
                donation_rows = [
                    {
                        "Donor": row[0] or "Anonymous",
                        "Donation": f"${float(row[1]):,.2f}",
                        "Submitted": row[2].strftime("%d %b %Y") if row[2] else "",
                    }
                    for row in donor_rows
                ]
                st.dataframe(donation_rows, use_container_width=True, hide_index=True)
            else:
                st.info("No donations have been submitted yet.")
        return

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
        submitted_data = st.session_state['submitted_data']
        items_val = submitted_data.get("Sponsorship Items", [])
        donation_val = submitted_data.get("Donation", None)
        total_val = submitted_data.get("Contributed Amount", None)
        how_to_pay = submitted_data.get("How to Pay", None)

        item_breakdown_html = ""
        if items_val:
            if isinstance(items_val, list):
                chips = "".join(
                    f"<div style='background:#f1f8e9; border:1px solid #c5e1a5; color:#2e7d32; font-weight:700; font-size:0.86rem; padding:5px 10px; border-radius:8px; margin-bottom:4px; display:inline-block; margin-right:6px;'>"
                    f"🏷️ {escape(str(item))}"
                    f"</div>"
                    for item in items_val
                )
                item_breakdown_html = chips
            else:
                item_breakdown_html = f"<span style='color:#2e7d32; font-weight:700;'>{escape(str(items_val))}</span>"
        else:
            item_breakdown_html = "<span style='color:#78909c;'>None</span>"

        email_val = submitted_data.get("Email")
        gothram_val = submitted_data.get("Gothram")
        mobile_val = submitted_data.get("Mobile")

        email_display = escape(str(email_val)) if email_val else "<span style='color:#90a4ae;'>Not provided</span>"
        gothram_display = escape(str(gothram_val)) if gothram_val else "<span style='color:#90a4ae;'>Not provided</span>"
        phone_display = escape(str(mobile_val)) if mobile_val else "<span style='color:#90a4ae;'>Not provided</span>"

        donation_row_html = ""
        if donation_val:
            donation_row_html = (
                f"<tr>"
                f"<td style='padding:9px 12px; color:#546e7a; font-weight:700; width:38%; border-bottom:1px solid #f0eae1;'>💝 Additional Donation</td>"
                f"<td style='padding:9px 12px; color:#1b5e20; font-weight:800; border-bottom:1px solid #f0eae1;'>{escape(str(donation_val))}</td>"
                f"</tr>"
            )

        total_banner_html = ""
        if total_val:
            total_banner_html = (
                "<div style='background:linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%); border:1.5px solid #a5d6a7; border-radius:12px; padding:0.9rem 1.2rem; display:flex; justify-content:space-between; align-items:center; margin-top:1rem; margin-bottom:0.75rem;'>"
                "<div>"
                "<div style='color:#2e7d32; font-size:0.8rem; font-weight:700;'>TOTAL CONTRIBUTED AMOUNT</div>"
                "<div style='color:#558b2f; font-size:0.75rem;'>Sponsorships + Donations</div>"
                "</div>"
                f"<div style='color:#1b5e20; font-size:1.55rem; font-weight:850;'>{escape(str(total_val))}</div>"
                "</div>"
            )

        how_to_pay_html = ""
        if how_to_pay:
            how_to_pay_html = (
                f"<div style='margin-top:1rem; padding:1rem 1.2rem; background:#fff8e1; border:1px solid #ffe082; border-left:5px solid #f57c00; border-radius:12px;'>"
                f"<div style='color:#e65100; font-weight:800; font-size:0.92rem; margin-bottom:0.35rem;'>💳 Payment Information</div>"
                f"<div style='color:#455a64; font-size:0.88rem; line-height:1.5;'>{how_to_pay}</div>"
                f"</div>"
            )

        thank_you_card_html = (
            "<div style='max-width:680px; margin:1rem auto 1.5rem; background:linear-gradient(135deg, #ffffff 0%, #fffdf7 100%); border:1.5px solid #ead8a9; border-radius:16px; box-shadow:0 6px 20px rgba(93,64,55,0.09); overflow:hidden;'>"
            "<div style='background:linear-gradient(90deg, #1b5e20 0%, #2e7d32 100%); padding:1.1rem 1.4rem; color:#ffffff;'>"
            "<div style='font-size:1.25rem; font-weight:800; letter-spacing:0.01em;'>🎉 Thank You for Your Submission!</div>"
            "<div style='font-size:0.85rem; opacity:0.95; margin-top:3px;'>Your sponsorship / donation has been successfully recorded.</div>"
            "</div>"
            "<div style='padding:1.2rem 1.4rem;'>"
            "<table style='width:100%; border-collapse:collapse; font-size:0.92rem;'>"
            f"<tr><td style='padding:9px 12px; color:#546e7a; font-weight:700; width:38%; border-bottom:1px solid #f0eae1;'>👤 Name</td><td style='padding:9px 12px; color:#263238; font-weight:700; border-bottom:1px solid #f0eae1;'>{escape(str(submitted_data.get('Name', '')))}</td></tr>"
            f"<tr><td style='padding:9px 12px; color:#546e7a; font-weight:700; border-bottom:1px solid #f0eae1;'>🏢 Apartment</td><td style='padding:9px 12px; color:#263238; font-weight:700; border-bottom:1px solid #f0eae1;'>{escape(str(submitted_data.get('Apartment', '')))}</td></tr>"
            f"<tr><td style='padding:9px 12px; color:#546e7a; font-weight:700; border-bottom:1px solid #f0eae1;'>📧 Email</td><td style='padding:9px 12px; color:#1565c0; border-bottom:1px solid #f0eae1;'>{email_display}</td></tr>"
            f"<tr><td style='padding:9px 12px; color:#546e7a; font-weight:700; border-bottom:1px solid #f0eae1;'>🪔 Gothram</td><td style='padding:9px 12px; color:#263238; border-bottom:1px solid #f0eae1;'>{gothram_display}</td></tr>"
            f"<tr><td style='padding:9px 12px; color:#546e7a; font-weight:700; border-bottom:1px solid #f0eae1;'>📱 Mobile</td><td style='padding:9px 12px; color:#263238; border-bottom:1px solid #f0eae1;'>{phone_display}</td></tr>"
            f"<tr><td style='padding:10px 12px; color:#546e7a; font-weight:700; vertical-align:top; border-bottom:1px solid #f0eae1;'>🏷️ Sponsorship Items</td><td style='padding:10px 12px; border-bottom:1px solid #f0eae1;'>{item_breakdown_html}</td></tr>"
            f"{donation_row_html}"
            "</table>"
            f"{total_banner_html}"
            f"{how_to_pay_html}"
            "</div>"
            "</div>"
        )
        st.markdown(thank_you_card_html, unsafe_allow_html=True)
        home_col1, home_col2, home_col3 = st.columns([1, 1.2, 1])
        with home_col2:
            if st.button('🏠 Return to Dashboard', key='home_button', type='primary', use_container_width=True):
                st.session_state['show_submission'] = False
                st.session_state['submitted_data'] = None
                st.session_state['main_navigation'] = 'Dashboard'
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
        selected_items_list = pending_submission.get("selected_items", [])
        donation_val = pending_submission.get("donation", 0.0)
        total_val = pending_submission.get("contributed_amount", 0.0)

        # Get item pricing for display
        item_breakdown_html = ""
        if selected_items_list:
            format_strings = ','.join(['%s'] * len(selected_items_list))
            cursor.execute(
                f"SELECT item, amount, sponsor_limit FROM sponsorship_items WHERE item IN ({format_strings})",
                tuple(selected_items_list),
            )
            item_price_map = {r[0]: (r[1] / r[2] if r[2] else r[1]) for r in cursor.fetchall()}
            chips = "".join(
                f"<div style='background:#f1f8e9; border:1px solid #c5e1a5; color:#2e7d32; font-weight:700; font-size:0.86rem; padding:5px 10px; border-radius:8px; margin-bottom:4px; display:inline-block; margin-right:6px;'>"
                f"🏷️ {escape(str(item))} &bull; <span style='color:#bf360c;'>${item_price_map.get(item, 0.0):,.2f}</span>"
                f"</div>"
                for item in selected_items_list
            )
            item_breakdown_html = chips
        else:
            item_breakdown_html = "<span style='color:#78909c;'>No sponsorship items selected</span>"

        email_display = escape(str(pending_submission['email'])) if pending_submission['email'] else "<span style='color:#90a4ae;'>Not provided</span>"
        gothram_display = escape(str(pending_submission['gothram'])) if pending_submission['gothram'] else "<span style='color:#90a4ae;'>Not provided</span>"
        phone_display = escape(str(pending_submission['phone'])) if pending_submission['phone'] else "<span style='color:#90a4ae;'>Not provided</span>"

        donation_row_html = ""
        if donation_val > 0:
            donation_row_html = (
                f"<tr>"
                f"<td style='padding:9px 12px; color:#546e7a; font-weight:700; width:38%; border-bottom:1px solid #f0eae1;'>💝 Additional Donation</td>"
                f"<td style='padding:9px 12px; color:#1b5e20; font-weight:800; border-bottom:1px solid #f0eae1;'>${donation_val:,.2f}</td>"
                f"</tr>"
            )

        confirm_card_html = (
            "<div style='max-width:680px; margin:1rem auto 1.5rem; background:linear-gradient(135deg, #ffffff 0%, #fffdf7 100%); border:1.5px solid #ead8a9; border-radius:16px; box-shadow:0 6px 20px rgba(93,64,55,0.09); overflow:hidden;'>"
            "<div style='background:linear-gradient(90deg, #6a1b1b 0%, #8b1737 100%); padding:1rem 1.4rem; color:#ffffff;'>"
            "<div style='font-size:1.15rem; font-weight:800; letter-spacing:0.01em;'>📋 Review &amp; Confirm Your Submission</div>"
            "<div style='font-size:0.82rem; opacity:0.9; margin-top:2px;'>Please verify your details below before final submission.</div>"
            "</div>"
            "<div style='padding:1.2rem 1.4rem;'>"
            "<table style='width:100%; border-collapse:collapse; font-size:0.92rem; margin-bottom:1rem;'>"
            f"<tr><td style='padding:9px 12px; color:#546e7a; font-weight:700; width:38%; border-bottom:1px solid #f0eae1;'>👤 Name</td><td style='padding:9px 12px; color:#263238; font-weight:700; border-bottom:1px solid #f0eae1;'>{escape(str(pending_submission['name']))}</td></tr>"
            f"<tr><td style='padding:9px 12px; color:#546e7a; font-weight:700; border-bottom:1px solid #f0eae1;'>🏢 Apartment</td><td style='padding:9px 12px; color:#263238; font-weight:700; border-bottom:1px solid #f0eae1;'>{escape(str(pending_submission['apartment']))}</td></tr>"
            f"<tr><td style='padding:9px 12px; color:#546e7a; font-weight:700; border-bottom:1px solid #f0eae1;'>📧 Email</td><td style='padding:9px 12px; color:#1565c0; border-bottom:1px solid #f0eae1;'>{email_display}</td></tr>"
            f"<tr><td style='padding:9px 12px; color:#546e7a; font-weight:700; border-bottom:1px solid #f0eae1;'>🪔 Gothram</td><td style='padding:9px 12px; color:#263238; border-bottom:1px solid #f0eae1;'>{gothram_display}</td></tr>"
            f"<tr><td style='padding:9px 12px; color:#546e7a; font-weight:700; border-bottom:1px solid #f0eae1;'>📱 Mobile</td><td style='padding:9px 12px; color:#263238; border-bottom:1px solid #f0eae1;'>{phone_display}</td></tr>"
            f"<tr><td style='padding:10px 12px; color:#546e7a; font-weight:700; vertical-align:top; border-bottom:1px solid #f0eae1;'>🏷️ Sponsorship Items</td><td style='padding:10px 12px; border-bottom:1px solid #f0eae1;'>{item_breakdown_html}</td></tr>"
            f"{donation_row_html}"
            "</table>"
            "<div style='background:linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%); border:1.5px solid #a5d6a7; border-radius:12px; padding:0.9rem 1.2rem; display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;'>"
            "<div>"
            "<div style='color:#2e7d32; font-size:0.8rem; font-weight:700;'>TOTAL CONTRIBUTION</div>"
            "<div style='color:#558b2f; font-size:0.75rem;'>Sponsorships + Donations</div>"
            "</div>"
            f"<div style='color:#1b5e20; font-size:1.55rem; font-weight:850;'>${total_val:,.2f}</div>"
            "</div>"
            "</div>"
            "</div>"
        )
        st.markdown(confirm_card_html, unsafe_allow_html=True)

        confirm_col, edit_col = st.columns(2)
        submission_in_progress = st.session_state.get("sponsorship_confirmation_in_progress", False)
        if confirm_col.button(
            "✅ Confirm & Submit",
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
        if edit_col.button("✏️ Edit Details", use_container_width=True, disabled=submission_in_progress):
            st.session_state["sponsorship_name"] = pending_submission["name"]
            st.session_state["sponsorship_apartment"] = pending_submission["apartment"]
            st.session_state["sponsorship_email"] = pending_submission["email"]
            st.session_state["sponsorship_gothram"] = pending_submission["gothram"]
            st.session_state["sponsorship_mobile"] = pending_submission["phone"]
            st.session_state["sponsorship_donation_amount"] = pending_submission["donation"]
            for item in pending_submission["available_items"]:
                toggle_key = f"sponsor_toggle_{re.sub(r'[^a-z0-9]+', '_', item.lower())}"
                st.session_state[toggle_key] = item in pending_submission["selected_items"]
            st.session_state["pending_sponsorship"] = None
            st.rerun()
        return

    sponsorship_form = st.form("sponsorship_form")
    name = apartment = email = gothram = mobile = ""
    if show_submission_inputs:
        sponsorship_form.markdown("""
<div style='background:linear-gradient(135deg,#e3f2fd 0%,#e8eaf6 100%); border:1px solid #90caf9; border-radius:10px; padding:0.8em 1.1em; margin-bottom:0.8em;'>
    <div style='font-size:1.02em; color:#1565c0; line-height:1.55;'>
        🙏 Please fill in your details below to participate in the <strong>Ganesh Chaturthi celebrations</strong> and support the event through sponsorship or donation.
        Your information helps us coordinate the festivities and keep you updated!
    </div>
</div>
""", unsafe_allow_html=True)

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

    cursor.execute("SELECT sponsorship, COUNT(*) FROM sponsors WHERE sponsorship IS NOT NULL AND sponsorship != '' GROUP BY sponsorship")
    sponsorship_counts = dict(cursor.fetchall())
    cursor.execute("SELECT item, amount, sponsor_limit, image_blob, image_filename FROM sponsorship_items ORDER BY id")
    item_rows = cursor.fetchall()
    available_items = [
        (item, cost, limit, image_blob, image_filename, limit - sponsorship_counts.get(item, 0))
        for item, cost, limit, image_blob, image_filename in item_rows
        if limit - sponsorship_counts.get(item, 0) > 0
    ]
    sponsorship_form.markdown(
        "<div class='sponsor-items-heading'>Select Items to Sponsor</div>",
        unsafe_allow_html=True,
    )
    selected_items = []
    cards_per_row = 1
    for row_start in range(0, len(available_items), cards_per_row):
        row_items = available_items[row_start:row_start + cards_per_row]
        card_cols = sponsorship_form.columns(len(row_items))
        for card_col, (item, cost, limit, image_blob, image_filename, remaining) in zip(card_cols, row_items):
            per_slot = cost / limit if limit else cost
            toggle_key = f"sponsor_toggle_{re.sub(r'[^a-z0-9]+', '_', item.lower())}"
            has_uploaded_image = image_blob is not None and len(image_blob) > 0
            with card_col.container(border=True):
                image_col, details_col = st.columns([0.62, 0.38], gap="small")
                if has_uploaded_image:
                    image_col.markdown(
                        f"<img class='sponsor-item-image' src='{get_sponsorship_item_image(item, image_blob, image_filename)}' alt='{escape(str(item))}'>",
                        unsafe_allow_html=True,
                    )
                    image_col.markdown(
                        f"<div class='sponsor-item-card-meta'><span class='sponsor-item-amount'>${per_slot:,.2f}</span><span class='sponsor-item-availability'>&bull; {remaining} available</span></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    image_col.empty()
                    details_col.markdown(
                        f"""
<div class='sponsor-item-card-title'>{escape(str(item))}</div>
<div class='sponsor-item-card-meta'><span class='sponsor-item-amount'>${per_slot:,.2f}</span><span class='sponsor-item-availability'>&bull; {remaining} available</span></div>
""",
                        unsafe_allow_html=True,
                    )
                is_selected = details_col.checkbox("Sponsor Now", key=toggle_key)
            if is_selected:
                selected_items.append(item)

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

    if show_submission_inputs:
        name = sponsorship_form.text_input("👤 Your Name", placeholder="E.g., Raghava Rao", key="sponsorship_name")
        apartment = sponsorship_form.text_input("🏢 Your Apartment Number", placeholder="E.g., 305", key="sponsorship_apartment")
        email = sponsorship_form.text_input("📧 Email Address (optional)", placeholder="your@email.com", key="sponsorship_email")
        gothram = sponsorship_form.text_input("🪔 Gothram (optional)", placeholder="E.g., Bharadwaja, Kashyapa, etc.", key="sponsorship_gothram")
        mobile = sponsorship_form.text_input("📱 Mobile Number (optional)", placeholder="E.g., 5121234567", key="sponsorship_mobile")

    def validate_us_phone(phone):
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 10:
            return True, f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return False, phone

    def format_name(name_str):
        return ' '.join(word.capitalize() for word in (name_str or "").strip().split())

    validation_errors = st.session_state.get("sponsorship_validation_errors", [])
    if validation_errors:
        sponsorship_form.error("Please complete the required fields before submitting:")
        for error in validation_errors:
            sponsorship_form.markdown(f"- {error}")

    submit_disabled = st.session_state.get('submission_in_progress', False)

    if show_submission_inputs:
        submit_review = sponsorship_form.form_submit_button(
            "Review",
            disabled=submit_disabled,
            type="primary",
        )
        if submit_review:
            name_val = format_name(st.session_state.get("sponsorship_name", name))
            apt_val = str(st.session_state.get("sponsorship_apartment", apartment) or "").strip()
            email_val = str(st.session_state.get("sponsorship_email", email) or "").strip()
            gothram_val = str(st.session_state.get("sponsorship_gothram", gothram) or "").strip()
            mobile_val = str(st.session_state.get("sponsorship_mobile", mobile) or "").strip()
            try:
                donation_val = float(st.session_state.get("sponsorship_donation_amount", donation) or 0.0)
            except Exception:
                donation_val = 0.0

            selected_items_val = [
                row[0] for row in available_items
                if st.session_state.get(f"sponsor_toggle_{re.sub(r'[^a-z0-9]+', '_', row[0].lower())}", False)
            ]

            errors = []
            if not name_val:
                errors.append("Name is required.")
            if not apt_val:
                errors.append("Apartment Number is required.")
            else:
                try:
                    apt_num = int(apt_val)
                    if not 100 <= apt_num <= 1600:
                        errors.append("Apartment Number must be between 100 and 1600.")
                except ValueError:
                    errors.append("Apartment Number must be a number between 100 and 1600.")
            if not selected_items_val and donation_val == 0:
                errors.append("Please sponsor at least one item or donate an amount.")
            if email_val and ('@' not in email_val or not email_val.lower().endswith('.com')):
                errors.append("Please enter a valid email address (must contain '@' and end with .com)")

            phone_fmt = mobile_val
            if mobile_val:
                phone_valid, phone_fmt = validate_us_phone(mobile_val)
                if not phone_valid:
                    errors.append("Please enter a valid 10-digit US phone number.")

            if errors:
                st.session_state["sponsorship_validation_errors"] = errors
                st.rerun()
            else:
                st.session_state["sponsorship_validation_errors"] = []
                sponsorship_total = 0
                if selected_items_val:
                    format_strings = ','.join(['%s'] * len(selected_items_val))
                    cursor.execute(
                        f"SELECT amount, sponsor_limit FROM sponsorship_items WHERE item IN ({format_strings})",
                        tuple(selected_items_val),
                    )
                    sponsorship_total = sum(row[0] / row[1] if row[1] else 0 for row in cursor.fetchall())
                contributed_amount = round(sponsorship_total + donation_val, 2)
                st.session_state['pending_sponsorship'] = {
                    "name": name_val,
                    "email": email_val,
                    "gothram": gothram_val,
                    "phone": phone_fmt.strip(),
                    "apartment": apt_val,
                    "selected_items": selected_items_val.copy(),
                    "available_items": [row[0] for row in available_items],
                    "donation": float(donation_val),
                    "contributed_amount": contributed_amount,
                }
                st.rerun()
