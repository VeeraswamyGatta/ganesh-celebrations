import streamlit as st
import pandas as pd
import datetime
import base64
import textwrap
from streamlit_option_menu import option_menu
from .db import get_connection
from html import escape
import io


def expenses_tab():
    # --- Clear Add Expense form fields if needed ---
    if st.session_state.get("clear_expense_form", False):
        st.session_state["add_expense_category"] = ""
        st.session_state["add_expense_subcat"] = ""
        st.session_state["add_expense_amount"] = 0.0
        st.session_state["add_expense_date"] = datetime.date.today()
        st.session_state["add_expense_spentby"] = ""
        st.session_state["add_expense_comments"] = ""
    # File uploader cannot be cleared programmatically; do not show info to user
        st.session_state["clear_expense_form"] = False
        st.rerun()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM committee_members ORDER BY name")
        committee_member_names = [row[0] for row in cursor.fetchall() if row[0]]
    except Exception:
        committee_member_names = []
    spent_by_options = committee_member_names or ["-- No Committee Members Available --"]
    # Calculate wallet and expenses totals
    cursor.execute("SELECT COALESCE(SUM(amount),0) FROM payment_details")
    total_payments = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE status='active'")
    total_expenses = cursor.fetchone()[0]
    wallet_amount = total_payments - total_expenses
    blink_color = 'red' if wallet_amount < 500 else 'green'

    # Fetch expenses data
    loading_message = (
        "Cash/Zelle transfer details are loading..."
        if st.session_state.get("expenses_management_menu") == "Expense Reimbursements"
        else "Expense details are loading..."
    )
    with st.spinner(loading_message):
        cursor.execute("SELECT id, category, sub_category, amount, date, spent_by, comments, receipt_path, receipt_blob FROM expenses WHERE status='active' ORDER BY category, sub_category")
        rows = cursor.fetchall()
    columns = ["ID", "Category", "Sub Category", "Amount", "Date", "Spent By", "Comments", "Receipt", "Receipt Blob"]
    df = pd.DataFrame(rows, columns=columns)
    def format_comments(comments):
        if not comments:
            return ""
        import re
        # Split comments by newlines or pipes, keep each line separate
        lines = re.split(r'[\n|]+', comments)
        return lines
    df["Comments"] = df["Comments"].apply(format_comments)

    # Tabs for expense management and summaries
    # Determine tabs to show based on user role
    is_admin = st.session_state.get("admin_logged_in", False)
    if is_admin:
        section_names = ["Expenses", "Expense Reimbursements"]
    else:
        section_names = ["Expenses"]
    if st.session_state.get("expenses_management_menu") not in section_names:
        st.session_state.pop("expenses_management_menu", None)
    if "expenses_section" not in st.session_state or st.session_state["expenses_section"] not in section_names:
        st.session_state["expenses_section"] = section_names[0]
        st.session_state["expense_inline_action"] = None
    selected_section = option_menu(
        "",
        section_names,
        icons=["list-ul", "wallet2"][:len(section_names)],
        menu_icon="cash-stack",
        default_index=section_names.index(st.session_state["expenses_section"]),
        orientation="horizontal",
        key="expenses_management_menu",
        styles={
            "container": {
                "padding": "0.5rem 0.75rem",
                "background": "linear-gradient(135deg, #ffffff 0%, #fffaf0 100%)",
                "border": "1.5px solid #e4ddd7",
                "border-radius": "16px",
                "box-shadow": "0 4px 16px rgba(80, 38, 28, 0.1)",
                "margin-bottom": "1.4rem",
            },
            "icon": {"color": "#8b1737", "font-size": "1rem"},
            "nav-link": {
                "font-size": "0.82rem",
                "font-weight": "600",
                "text-align": "center",
                "margin": "0 4px",
                "padding": "0.55rem 0.85rem",
                "border-radius": "12px",
                "color": "#5d4037",
                "--hover-color": "#f5efe6",
            },
            "nav-link-selected": {
                "background": "linear-gradient(135deg, #6a1b1b 0%, #8b1737 100%)",
                "color": "#ffffff",
                "font-weight": "700",
                "box-shadow": "0 4px 12px rgba(106, 27, 27, 0.3)",
            },
            "menu-title": {"color": "#5d4037", "font-weight": "800", "font-size": "0.95rem", "margin-right": "1rem"},
        },
    )
    st.session_state["expenses_section"] = selected_section
    if selected_section != "Expenses":
        st.session_state["expense_inline_action"] = None
    if selected_section != "Expense Reimbursements":
        st.session_state["show_settlement_form"] = False
    # Settlements Section (admin only)
    if is_admin and selected_section == "Expense Reimbursements":
        st.markdown(
            """
            <style>
            .st-key-toggle_settlement_form button {
                min-height: 2.7rem;
                padding: 0.85rem 1.3rem;
                border: 1px solid #ffb300;
                border-radius: 14px;
                background: linear-gradient(135deg, #ff8f00 0%, #ff5e00 45%, #d81b60 100%);
                box-shadow: 0 8px 22px rgba(255, 94, 0, 0.28);
                color: #ffffff;
                font-size: 1rem;
                font-weight: 800;
                letter-spacing: 0.01em;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .st-key-toggle_settlement_form button:hover {
                background: linear-gradient(135deg, #ff8f00 0%, #ff5e00 45%, #d81b60 100%);
                box-shadow: 0 10px 26px rgba(216, 27, 96, 0.28), 0 0 18px rgba(255, 170, 0, 0.55);
                color: #ffffff;
                transform: translateY(-1px) scale(1.01);
            }
            .st-key-toggle_settlement_form {
                margin-top: 0.3rem;
                margin-bottom: 1rem;
            }
            .settlement-section-title {
                margin: 0.7rem 0 0.9rem;
                padding: 0.45rem 0.75rem;
                border-left: 4px solid #a51d3f;
                border-bottom: 1px solid #ead8a9;
                color: #6a1b1b;
                font-size: 1rem;
                font-weight: 800;
                letter-spacing: 0.01em;
                background: linear-gradient(90deg, #fff8e8 0%, rgba(255, 248, 232, 0) 100%);
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div class='settlement-section-title'>Cash/Zelle Transfer Summary</div>", unsafe_allow_html=True)
        settlement_success_message = st.session_state.pop("settlement_success_message", None)
        if settlement_success_message:
            st.success(settlement_success_message)
        show_settlement_form = st.session_state.get("show_settlement_form", False)
        toggle_label = "Click here to show cash balance" if show_settlement_form else "Click here to add settlement"
        if st.button(toggle_label, key="toggle_settlement_form"):
            st.session_state["show_settlement_form"] = not show_settlement_form
            st.rerun()
        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

        if show_settlement_form:
            st.markdown(
                """
                <style>
                .settlement-form-header {
                    margin: 1rem 0 1.1rem;
                    padding: 1rem 1.15rem;
                    border: 1px solid #ead8a9;
                    border-left: 5px solid #8b1737;
                    border-radius: 10px;
                    background: linear-gradient(135deg, #fffaf0 0%, #fff1d2 100%);
                }
                .settlement-form-title {
                    margin: 0;
                    color: #6a1b1b;
                    font-size: 1.15rem;
                    font-weight: 800;
                }
                .settlement-form-copy {
                    margin: 0.3rem 0 0;
                    color: #795548;
                    font-size: 0.86rem;
                }
                .st-key-add_settlement_btn button {
                    width: 100%;
                    min-height: 2.7rem;
                    border: 0;
                    border-radius: 8px;
                    background: linear-gradient(135deg, #6a1b1b 0%, #8b1737 100%);
                    color: #ffffff;
                    font-weight: 800;
                }
                </style>
                <div class='settlement-form-header'>
                    <p class='settlement-form-title'>Add Settlement</p>
                    <p class='settlement-form-copy'>Record a payment and keep the cash balance up to date.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Get total expense and settlement amount for each person
            with st.spinner("Loading settlement data..."):
                cursor.execute("SELECT spent_by, SUM(amount) FROM expenses WHERE status='active' GROUP BY spent_by")
                expense_rows = cursor.fetchall()
                expense_map = {row[0]: float(row[1]) for row in expense_rows if row[0] and row[1]}
                cursor.execute("SELECT name, SUM(amount) FROM settlements GROUP BY name")
                settlement_rows = cursor.fetchall()
            settlement_map = {row[0]: float(row[1]) for row in settlement_rows if row[0] and row[1]}
            # Only show names with (total expense - total settlement) > 0
            expense_names = []
            for name in sorted(expense_map.keys()):
                net_amount = expense_map.get(name, 0.0) - settlement_map.get(name, 0.0)
                if net_amount != 0:
                    expense_names.append(name)
            # Use index to control default selection, avoid setting session_state directly
            default_index = 0
            if "settlement_name" in st.session_state and st.session_state["settlement_name"] in expense_names:
                default_index = expense_names.index(st.session_state["settlement_name"])
            name = st.selectbox("Name", expense_names, index=default_index, key="settlement_name")
            # Set Amount field to (total expense - total settlement) for selected name
            default_amount = expense_map.get(name, 0.0) - settlement_map.get(name, 0.0)
            try:
                default_amount = float(default_amount)
            except Exception:
                default_amount = 0.0
            if (
                st.session_state.get("settlement_last_name") != name
                or st.session_state.get("settlement_last_default_amount") != default_amount
            ):
                st.session_state["settlement_amount"] = default_amount
                st.session_state["settlement_last_name"] = name
                st.session_state["settlement_last_default_amount"] = default_amount
            # Remove min_value to allow negative values
            amount = st.number_input("Amount", format="%.2f", key="settlement_amount")
            with st.spinner("Loading cash collectors..."):
                cursor.execute("SELECT * FROM payment_details LIMIT 0")
                payment_columns = [column[0].lower() for column in cursor.description]
                if "recieved_zelle_acc_name" in payment_columns:
                    cursor.execute(
                        "SELECT DISTINCT recieved_zelle_acc_name FROM payment_details "
                        "WHERE recieved_zelle_acc_name IS NOT NULL "
                        "AND TRIM(recieved_zelle_acc_name) <> '' "
                        "ORDER BY recieved_zelle_acc_name"
                    )
                    sent_by_options = [row[0] for row in cursor.fetchall()]
                else:
                    sent_by_options = []
            if not sent_by_options:
                sent_by_options = ["-- No Cash Collectors Available --"]
            sent_by = st.selectbox("Sent By", sent_by_options, key="settlement_sent_by")
            comments = st.text_area("Comments", key="settlement_comments")
            if st.button("Add Settlement", key="add_settlement_btn"):
                if sent_by == "-- No Cash Collectors Available --":
                    st.warning("Add a cash payment with a collector before adding a settlement.")
                else:
                    st.session_state["settlement_submission_in_progress"] = True
                    with st.spinner("Adding settlement..."):
                        cursor.execute("INSERT INTO settlements (name, amount, sent_by, comments) VALUES (%s, %s, %s, %s)", (name, amount, sent_by, comments))
                        conn.commit()
                    st.session_state["settlement_submission_in_progress"] = False
                    st.session_state["show_settlement_form"] = False
                    st.session_state["settlement_success_message"] = "Settlement added successfully."
                    # Clear form fields
                    # Do not clear widget keys after instantiation to avoid StreamlitAPIException
                    st.rerun()

        else:
            with st.spinner("Loading settlement data..."):
                cursor.execute("SELECT recieved_zelle_acc_name, SUM(amount) FROM payment_details GROUP BY recieved_zelle_acc_name")
                payment_rows = cursor.fetchall()
                cursor.execute("SELECT sent_by, COALESCE(SUM(amount),0) FROM settlements GROUP BY sent_by")
                settlement_rows = cursor.fetchall()
                cursor.execute("SELECT sent_by, name, amount FROM settlements ORDER BY sent_by, name, id")
                settlement_transfer_rows = cursor.fetchall()
            settlement_map = {row[0]: float(row[1] or 0) for row in settlement_rows}
            transfers_by_collector = {}
            for sent_by, recipient, amount in settlement_transfer_rows:
                if sent_by:
                    transfers_by_collector.setdefault(sent_by, []).append(
                        (recipient or "Unknown", float(amount or 0))
                    )
            wallet_summary = []
            for cash_collector, received_amount in payment_rows:
                if cash_collector and str(cash_collector).strip():
                    total_received = float(received_amount or 0)
                    total_settled = settlement_map.get(cash_collector, 0.0)
                    wallet_summary.append({
                        "Name": cash_collector,
                        "Received": total_received,
                        "Settled": total_settled,
                        "Available": total_received - total_settled,
                        "Transfers": transfers_by_collector.get(cash_collector, []),
                    })
            wallet_summary.sort(key=lambda item: (item["Available"] <= 0, item["Name"]))
            wallet_rows_html = []
            for row_number, wallet in enumerate(wallet_summary, start=1):
                balance_class = "wallet-positive" if wallet["Available"] > 0 else "wallet-zero-negative"
                transfer_lines = wallet["Transfers"] or [("No recorded transfers", 0)]
                transfers_html = "".join(
                    f"<div class='wallet-transfer-line'>{escape(str(recipient))} (${amount:,.2f})</div>"
                    for recipient, amount in transfer_lines
                )
                wallet_rows_html.append(
                    f"""
                    <tr class='wallet-summary-row {balance_class}'>
                        <td class='wallet-row-number'>{row_number}</td>
                        <td class='wallet-name'>
                            {escape(str(wallet['Name']))}
                            <div class='wallet-mobile-details'>
                                <span>Received: ${wallet['Received']:,.2f}</span>
                                <span>Settled: ${wallet['Settled']:,.2f}</span>
                                <span>Transfers: {transfers_html}</span>
                            </div>
                        </td>
                        <td class='wallet-received'>${wallet['Received']:,.2f}</td>
                        <td class='wallet-settled'>${wallet['Settled']:,.2f}</td>
                        <td class='wallet-calculation'><strong>${wallet['Available']:,.2f}</strong></td>
                        <td class='wallet-transfers'>{transfers_html}</td>
                    </tr>
                    """
                )
            total_received_all = sum(item["Received"] for item in wallet_summary)
            total_settled_all = sum(item["Settled"] for item in wallet_summary)
            total_available_all = sum(item["Available"] for item in wallet_summary)
            st.markdown(
                textwrap.dedent(
                    f"""
                    <style>
                    .wallet-summary-table {{
                        width: 100%; margin-top: 1rem; border-collapse: separate; border-spacing: 0;
                        height: auto; min-height: 0; min-width: 0; table-layout: fixed;
                        border: 1px solid #ead8a9; border-radius: 10px; overflow: hidden;
                        background: #fffdf8; color: #3f3028;
                        box-shadow: 0 3px 12px rgba(93, 64, 55, 0.08);
                    }}
                    .wallet-summary-table th, .wallet-summary-table td {{
                        height: auto; padding: 0.55rem 0.6rem; text-align: left; vertical-align: middle;
                        border-bottom: 1px solid #eee3cf;
                        border-right: 1px solid #f0e4cf;
                    }}
                    .wallet-summary-table th:last-child, .wallet-summary-table td:last-child {{ border-right: 0; }}
                    .wallet-summary-table th {{
                        background: linear-gradient(135deg, #6a1b1b, #8b1737);
                        color: #fff; font-size: 0.78rem; font-weight: 800;
                        letter-spacing: 0.02em;
                    }}
                    .wallet-summary-row:nth-child(even) {{ background: #fff8e8; }}
                    .wallet-summary-row.wallet-positive {{ background: #edf8ee; }}
                    .wallet-summary-row.wallet-zero-negative {{ background: #fff0f0; }}
                    .wallet-summary-row:hover {{ background: #fff0c2; }}
                    .wallet-summary-row:last-child td {{ border-bottom: 0; }}
                    .wallet-row-number {{ width: 2.5rem; color: #8b6b35; font-weight: 800; }}
                    .wallet-summary-table th:nth-child(1), .wallet-summary-table td:nth-child(1) {{ width: 5%; }}
                    .wallet-summary-table th:nth-child(2), .wallet-summary-table td:nth-child(2) {{ width: 20%; }}
                    .wallet-summary-table th:nth-child(3), .wallet-summary-table td:nth-child(3) {{ width: 14%; }}
                    .wallet-summary-table th:nth-child(4), .wallet-summary-table td:nth-child(4) {{ width: 14%; }}
                    .wallet-summary-table th:nth-child(5), .wallet-summary-table td:nth-child(5) {{ width: 27%; }}
                    .wallet-summary-table th:nth-child(6), .wallet-summary-table td:nth-child(6) {{ width: 20%; }}
                    .wallet-name {{
                        color: #6a1b1b;
                        font-size: 0.9rem;
                        font-weight: 700;
                        white-space: normal;
                        overflow-wrap: anywhere;
                    }}
                    .wallet-received {{ color: #1565c0; font-weight: 700; white-space: nowrap; }}
                    .wallet-settled {{ color: #c62828; font-weight: 700; white-space: nowrap; }}
                    .wallet-calculation {{ color: #5d4037; overflow-wrap: anywhere; }}
                    .wallet-calculation b {{ padding: 0 0.35rem; color: #8b6b35; }}
                    .wallet-calculation strong {{ color: #2e7d32; font-size: 1.02rem; }}
                    .wallet-transfers {{ color: #5d4037; font-size: 0.78rem; line-height: 1.4; overflow-wrap: anywhere; }}
                    .wallet-transfer-line + .wallet-transfer-line {{ margin-top: 0.2rem; }}
                    .wallet-mobile-details {{ display: none; }}
                    .wallet-total-strip {{
                        display: flex; flex-wrap: wrap; gap: 0.7rem; margin: 0.9rem 0 1.5rem;
                    }}
                    .wallet-total-card {{
                        flex: 1 1 12rem; padding: 0.7rem 0.9rem; border-radius: 8px;
                        border: 1px solid #ead8a9; background: #fff8e8;
                    }}
                    .wallet-total-label {{ display: block; color: #795548; font-size: 0.75rem; font-weight: 700; }}
                    .wallet-total-value {{ display: block; margin-top: 0.15rem; font-size: 1.1rem; font-weight: 800; }}
                    @media (max-width: 640px) {{
                        .wallet-table-scroll {{ overflow-x: visible; width: 100%; }}
                        .wallet-summary-table {{ min-width: 0; width: 100%; table-layout: fixed; }}
                        .wallet-summary-table th, .wallet-summary-table td {{ padding: 0.45rem 0.5rem; }}
                        .wallet-summary-table th:nth-child(3), .wallet-summary-table td:nth-child(3),
                        .wallet-summary-table th:nth-child(4), .wallet-summary-table td:nth-child(4),
                        .wallet-summary-table th:nth-child(6), .wallet-summary-table td:nth-child(6) {{ display: none; }}
                        .wallet-summary-table th:nth-child(1), .wallet-summary-table td:nth-child(1) {{ width: 9%; }}
                        .wallet-summary-table th:nth-child(2), .wallet-summary-table td:nth-child(2) {{ width: 61%; }}
                        .wallet-summary-table th:nth-child(5), .wallet-summary-table td:nth-child(5) {{ width: 30%; }}
                        .wallet-mobile-details {{ display: block; margin-top: 0.25rem; color: #795548; font-size: 0.68rem; font-weight: 600; line-height: 1.4; }}
                        .wallet-mobile-details > span {{ display: block; }}
                    }}
                    </style>
                    <div class='wallet-table-scroll'>
                        <table class='wallet-summary-table'>
                            <thead><tr>
                                <th>#</th><th>Cash/Zelle Collector</th><th>Total Received</th>
                                <th>Total Settled</th><th>Available Bal</th><th>Transferred To (Amount)</th>
                            </tr></thead>
                            <tbody>{''.join(wallet_rows_html)}</tbody>
                        </table>
                    </div>
                    <div class='wallet-total-strip'>
                        <div class='wallet-total-card'><span class='wallet-total-label'>Total Received</span><span class='wallet-total-value' style='color:#1565c0;'>${total_received_all:,.2f}</span></div>
                        <div class='wallet-total-card'><span class='wallet-total-label'>Total Settled</span><span class='wallet-total-value' style='color:#c62828;'>${total_settled_all:,.2f}</span></div>
                        <div class='wallet-total-card'><span class='wallet-total-label'>Total Available</span><span class='wallet-total-value' style='color:#2e7d32;'>${total_available_all:,.2f}</span></div>
                    </div>
                    """
                ).strip(),
                unsafe_allow_html=True,
            )
            st.markdown("<div class='settlement-section-title'>Expense Reimbursement Details</div>", unsafe_allow_html=True)
            with st.spinner("Loading Cash/Zelle transfer details..."):
                cursor.execute("SELECT spent_by, SUM(amount) FROM expenses WHERE status='active' GROUP BY spent_by")
                spent_rows = cursor.fetchall()
                spent_dict = {row[0]: row[1] for row in spent_rows}
                cursor.execute("SELECT name, amount, sent_by, comments FROM settlements ORDER BY name, id")
                settlement_rows = cursor.fetchall()
            settlement_by_name = {}
            for settlement_name, settlement_amount, settlement_sent_by, settlement_comment in settlement_rows:
                settlement_by_name.setdefault(settlement_name, []).append(
                    (settlement_amount or 0, settlement_sent_by or "", settlement_comment or "")
                )
            # Show all names, even if their net amount is zero or negative
            all_names = set(spent_dict.keys()) | set(settlement_by_name.keys())
            summary = []
            for name in sorted(all_names):
                total_spent = float(spent_dict.get(name, 0) or 0)
                settlement_details = settlement_by_name.get(name, [])
                received_amounts = [float(amount) for amount, _, _ in settlement_details]
                total_received = sum(received_amounts)
                received_comments = "\n".join(
                    f"Transferred by {sent_by}: {comment.strip()} (${amount:,.2f})"
                    if comment.strip()
                    else f"Transferred by {sent_by} (${amount:,.2f})"
                    for amount, sent_by, comment in settlement_details
                )
                pending_amount = total_spent - total_received
                summary.append({
                    "Name": name,
                    "Total Spent Amount": total_spent,
                    "Total Received Amount": total_received,
                    "Pending Transaction Amount": pending_amount,
                    "Comments": received_comments,
                    "Received Amounts": received_amounts,
                })
            cols = ["Name", "Total Spent Amount", "Total Received Amount", "Pending Transaction Amount", "Comments"]
            summary_df = pd.DataFrame(summary, columns=cols)
            if not summary_df.empty:
                summary_df.index = summary_df.index + 1
            # Reorder columns to show Pending Transaction Amount before Comments
            summary_df = summary_df[cols]
            summary_rows_html = []
            summary_df = summary_df.sort_values(
                by="Pending Transaction Amount",
                key=lambda values: values.le(0),
                kind="stable",
            )
            for row_number, row in enumerate(summary_df.to_dict("records"), start=1):
                comment_lines = str(row["Comments"] or "").splitlines() or [""]
                received_amounts = next(
                    (item["Received Amounts"] for item in summary if item["Name"] == row["Name"]),
                    [],
                )
                if received_amounts:
                    amount_breakdown = " + ".join(f"${amount:,.2f}" for amount in received_amounts)
                    comment_lines.append(
                        f"Total received: {amount_breakdown} = ${sum(received_amounts):,.2f}"
                    )
                comments_html = "".join(
                    f"<div class='settlement-comment-line'>{escape(line)}</div>"
                    for line in comment_lines
                )
                balance_class = "settlement-positive" if row["Pending Transaction Amount"] > 0 else "settlement-zero-negative"
                summary_rows_html.append(
                    f"""
                    <tr class='settlement-summary-row {balance_class}'>
                        <td class='settlement-row-number'>{row_number}</td>
                        <td class='settlement-name'>{escape(str(row['Name']))}</td>
                        <td class='settlement-amount'>${float(row['Total Spent Amount']):,.2f}</td>
                        <td class='settlement-amount settlement-received'>${float(row['Total Received Amount']):,.2f}</td>
                        <td class='settlement-amount settlement-pending'>${float(row['Pending Transaction Amount']):,.2f}</td>
                        <td class='settlement-comments-cell'>{comments_html}</td>
                    </tr>
                    """
                )
            st.html(
                textwrap.dedent(
                    f"""
                <style>
                .settlements-summary-table {{
                    width: 100%;
                    margin-top: 1rem;
                    min-width: 0;
                    table-layout: fixed;
                    border-collapse: separate;
                    border-spacing: 0;
                    overflow: hidden;
                    border: 1px solid #ead8a9;
                    border-radius: 10px;
                    background: #fffdf8;
                    color: #3f3028;
                    box-shadow: 0 3px 12px rgba(93, 64, 55, 0.08);
                }}
                .settlements-summary-table th, .settlements-summary-table td {{
                    padding: 0.55rem 0.6rem;
                    border-bottom: 1px solid #eee3cf;
                    border-right: 1px solid #f0e4cf;
                    text-align: left;
                    vertical-align: top;
                }}
                .settlements-summary-table th:last-child, .settlements-summary-table td:last-child {{ border-right: 0; }}
                .settlements-summary-table th {{
                    padding-top: 0.65rem;
                    padding-bottom: 0.65rem;
                    background: linear-gradient(135deg, #6a1b1b, #8b1737);
                    color: #ffffff;
                    font-size: 0.7rem;
                    font-weight: 800;
                    letter-spacing: 0.02em;
                    overflow-wrap: anywhere;
                }}
                .settlements-summary-table th:first-child {{ border-top-left-radius: 9px; }}
                .settlements-summary-table th:last-child {{ border-top-right-radius: 9px; }}
                .settlement-summary-row:nth-child(even) {{ background: #fff8e8; }}
                .settlement-summary-row.settlement-positive {{ background: #edf8ee; }}
                .settlement-summary-row.settlement-zero-negative {{ background: #fff0f0; }}
                .settlement-summary-row:hover {{ background: #fff0c2; }}
                .settlement-summary-row:last-child td {{ border-bottom: 0; }}
                .settlement-row-number {{
                    width: 2rem;
                    color: #8b6b35;
                    font-weight: 800;
                }}
                .settlement-name {{
                    color: #6a1b1b;
                    font-size: 0.9rem;
                    font-weight: 700;
                    white-space: normal;
                    overflow-wrap: anywhere;
                }}
                .settlement-amount {{
                    color: #5d4037;
                    font-size: 0.82rem;
                    font-variant-numeric: tabular-nums;
                    white-space: normal;
                    overflow-wrap: anywhere;
                }}
                .settlement-received {{ color: #2e7d32; font-weight: 700; }}
                .settlement-pending {{ color: #c62828; font-weight: 800; }}
                .settlements-summary-table th:nth-child(1),
                .settlements-summary-table td:nth-child(1) {{ width: 4%; }}
                .settlements-summary-table th:nth-child(2),
                .settlements-summary-table td:nth-child(2) {{ width: 20%; }}
                .settlements-summary-table th:nth-child(3),
                .settlements-summary-table td:nth-child(3),
                .settlements-summary-table th:nth-child(4),
                .settlements-summary-table td:nth-child(4),
                .settlements-summary-table th:nth-child(5),
                .settlements-summary-table td:nth-child(5) {{ width: 14%; }}
                .settlement-comments-cell {{
                    width: 34%;
                    color: #5d4037;
                    line-height: 1.45;
                    overflow-wrap: anywhere;
                }}
                .settlement-comment-line + .settlement-comment-line {{ margin-top: 0.25rem; }}
                </style>
                <div style='width:100%; overflow-x:auto;'>
                    <table class='settlements-summary-table'>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Spent By</th>
                                <th>Total<br>Spent</th>
                                <th>Cash/Zelle<br>Reimbursed</th>
                                <th>Balance<br>Due</th>
                                <th>Cash/Zelle<br>Details</th>
                            </tr>
                        </thead>
                        <tbody>{''.join(summary_rows_html)}</tbody>
                    </table>
                </div>
                    """
                ).strip(),
            )

            # Send Settlements Report via Email button
            if is_admin and st.button("📧 Send Settlements Report via Email", key="send_settlements_email"):
                try:
                        # Ensure email column exists in committee_members
                        try:
                            cursor.execute("ALTER TABLE committee_members ADD COLUMN email TEXT")
                            conn.commit()
                        except Exception:
                            pass
                    
                        # Get recipients from both notification_emails and committee_members
                        cursor.execute("SELECT email FROM notification_emails WHERE email IS NOT NULL AND email != ''")
                        recipients = [row[0] for row in cursor.fetchall()]
                    
                        try:
                            cursor.execute("SELECT email FROM committee_members WHERE email IS NOT NULL AND email != ''")
                            committee_emails = [row[0] for row in cursor.fetchall()]
                            recipients.extend(committee_emails)
                        except Exception:
                            pass
                    
                        # Remove duplicates
                        recipients = list(set(recipients))
                    
                        if not recipients:
                            st.error("❌ No recipients found. Add emails to notification_emails or committee_members.")
                        else:
                            # Build HTML email body
                            settlement_html = """
                            <html>
                            <body style="font-family: Arial, sans-serif; color: #333;">
                                <h2 style="color: #6a1b1b;">📋 Settlements Report</h2>
                                <p>Date: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
                                <table border="1" cellpadding="10" cellspacing="0" style="width:100%; border-collapse: collapse; margin-top: 20px;">
                                    <tr style="background-color: #6a1b1b; color: white;">
                                        <th>Name</th>
                                        <th>Total Spent</th>
                                        <th>Total Received</th>
                                        <th>Pending Amount</th>
                                        <th>Comments</th>
                                    </tr>
                            """
                        
                            for _, row in summary_df.iterrows():
                                settlement_html += f"""
                                    <tr style="border-bottom: 1px solid #ddd;">
                                        <td>{row['Name']}</td>
                                        <td style="text-align: right;">${float(row['Total Spent Amount']):,.2f}</td>
                                        <td style="text-align: right;">${float(row['Total Received Amount']):,.2f}</td>
                                        <td style="text-align: right; color: {'green' if row['Pending Transaction Amount'] <= 0 else 'red'};">
                                            ${abs(float(row['Pending Transaction Amount'])):,.2f}
                                        </td>
                                        <td>{row['Comments'].replace(chr(10), '<br>')}</td>
                                    </tr>
                                """
                        
                            settlement_html += """
                                </table>
                            </body>
                            </html>
                            """
                        
                            # Send emails to all recipients
                            import smtplib
                            from email.mime.multipart import MIMEMultipart
                            from email.mime.text import MIMEText
                        
                            email_sender = st.secrets.get("email_sender")
                            email_password = st.secrets.get("email_password")
                            smtp_server = st.secrets.get("smtp_server", "smtp.gmail.com")
                            smtp_port = st.secrets.get("smtp_port", 587)
                        
                            sent_count = 0
                            failed_recipients = []
                        
                            for recipient in recipients:
                                try:
                                    msg = MIMEMultipart("alternative")
                                    msg["Subject"] = f"Settlements Report - {datetime.now().strftime('%Y-%m-%d')}"
                                    msg["From"] = email_sender
                                    msg["To"] = recipient
                                
                                    msg.attach(MIMEText(settlement_html, "html"))
                                
                                    with smtplib.SMTP(smtp_server, smtp_port) as server:
                                        server.starttls()
                                        server.login(email_sender, email_password)
                                        server.send_message(msg)
                                
                                    sent_count += 1
                                except Exception as e:
                                    failed_recipients.append(f"{recipient} ({str(e)})")
                        
                            if sent_count > 0:
                                st.success(f"✅ Settlements report sent to {sent_count} recipient(s)!")
                            if failed_recipients:
                                st.warning(f"⚠️ Failed to send to: {', '.join(failed_recipients)}")
                
                except Exception as e:
                    st.error(f"❌ Failed to send settlements report: {e}")
    if is_admin and selected_section == "Expenses":
        st.markdown(
            """
            <style>
            .st-key-expense_inline_actions {
                margin: 0.2rem 0 1rem;
                padding: 0.55rem;
                overflow: hidden;
                border: 1px solid #ead8a9;
                border-radius: 14px;
                background: linear-gradient(135deg, #fffdf7 0%, #f1f8e9 100%);
                box-shadow: 0 4px 14px rgba(93, 64, 55, 0.1);
            }
            .st-key-expense_inline_actions [data-testid="stHorizontalBlock"] {
                flex-wrap: nowrap !important;
                gap: 0.45rem !important;
                overflow: hidden;
            }
            .st-key-expense_inline_actions [data-testid="stColumn"] {
                min-width: 0 !important;
                flex: 1 1 0 !important;
            }
            .st-key-expense_inline_actions button {
                min-height: 2.45rem !important;
                border: 1px solid #d8b15a !important;
                border-radius: 10px !important;
                background: #ffffff !important;
                color: #6a1b1b !important;
                font-size: 0.78rem !important;
                font-weight: 800 !important;
                white-space: nowrap !important;
                box-shadow: 0 2px 6px rgba(106, 27, 27, 0.1) !important;
            }
            .st-key-expense_inline_actions button:hover {
                border-color: #8b1737 !important;
                background: #fff8e1 !important;
                transform: translateY(-1px);
            }
            @media (max-width: 640px) {
                .st-key-expense_inline_actions {
                    margin-bottom: 0.8rem;
                    padding: 0.42rem;
                }
                .st-key-expense_inline_actions [data-testid="stColumn"] {
                    min-width: 0 !important;
                    flex-basis: 0 !important;
                }
                .st-key-expense_inline_actions button {
                    min-height: 2.25rem !important;
                    padding: 0.35rem 0.4rem !important;
                    font-size: 0.65rem !important;
                }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        expense_success_message = st.session_state.pop("expense_success_message", None)
        if expense_success_message:
            st.success(expense_success_message)
        with st.container(key="expense_inline_actions"):
            action_columns = st.columns(3)
            if action_columns[0].button("➕ Add", key="expense_inline_add", use_container_width=True):
                st.session_state["expense_inline_action"] = "add"
                st.rerun()
            if action_columns[1].button("✏️ Edit", key="expense_inline_edit", disabled=df.empty, use_container_width=True):
                st.session_state["expense_inline_action"] = "edit"
                st.rerun()
            if action_columns[2].button("🗑️ Delete", key="expense_inline_delete", disabled=df.empty, use_container_width=True):
                st.session_state["expense_inline_action"] = "delete"
                st.rerun()

    if is_admin and selected_section == "Expenses" and st.session_state.get("expense_inline_action") == "add":
            cursor.execute("SELECT item FROM sponsorship_items")
            categories = [row[0] for row in cursor.fetchall()]
            if "Miscellaneous" not in categories:
                categories.append("Miscellaneous")
            MAX_RECEIPT_SIZE_MB = 1
            MAX_RECEIPT_SIZE_BYTES = MAX_RECEIPT_SIZE_MB * 1024 * 1024
            expense_form = st.form("add_expense_form")
            expense_submit_disabled = st.session_state.get("expense_submission_in_progress", False)
            uploaded_receipt = expense_form.file_uploader(f"Upload Receipt (JPG/PNG, max {MAX_RECEIPT_SIZE_MB}MB)", type=["jpg", "jpeg", "png"], key="add_expense_receipt")
            receipt_path = None
            receipt_bytes = None
            receipt_filename = None
            if uploaded_receipt is not None:
                if uploaded_receipt.size > MAX_RECEIPT_SIZE_BYTES:
                    st.error(f"Receipt file size should not exceed {MAX_RECEIPT_SIZE_MB} MB.")
                elif uploaded_receipt.type not in ["image/jpeg", "image/png"]:
                    st.error("Only JPG and PNG files are allowed.")
                else:
                    import uuid
                    ext = uploaded_receipt.name.split('.')[-1]
                    receipt_filename = f"receipt_{uuid.uuid4().hex}.{ext}"
                    receipt_bytes = uploaded_receipt.read()
                    receipt_path = receipt_filename
            category = expense_form.selectbox("Category", categories, key="add_expense_category")
            sub_category = expense_form.text_input("Sub Category", placeholder="e.g. Decoration, Snacks", key="add_expense_subcat")
            amount = expense_form.number_input("Amount", format="%.2f", key="add_expense_amount")
            date = expense_form.date_input("Date", value=datetime.date.today(), key="add_expense_date")
            spent_by = expense_form.selectbox("Spent By", spent_by_options, key="add_expense_spentby")
            comments = expense_form.text_area("Comments", value="", placeholder="Any additional details", key="add_expense_comments")
            if expense_form.form_submit_button("Add Expense", disabled=expense_submit_disabled, type="primary"):
                st.session_state["expense_submission_in_progress"] = True
                expense_status = st.status("Adding expense...", expanded=False)
                if not category:
                    st.session_state["expense_submission_in_progress"] = False
                    expense_status.update(label="Please complete the required fields", state="error", expanded=True)
                    st.error("Category is required.")
                elif not sub_category.strip():
                    st.session_state["expense_submission_in_progress"] = False
                    expense_status.update(label="Please complete the required fields", state="error", expanded=True)
                    st.error("Sub Category is required.")
                # Remove validation for amount > 0 to allow negative values
                elif spent_by == "-- No Committee Members Available --":
                    st.session_state["expense_submission_in_progress"] = False
                    expense_status.update(label="Please complete the required fields", state="error", expanded=True)
                    st.error("Spent By is required.")
                elif uploaded_receipt is not None and (uploaded_receipt.size > MAX_RECEIPT_SIZE_BYTES or uploaded_receipt.type not in ["image/jpeg", "image/png"]):
                    st.session_state["expense_submission_in_progress"] = False
                    expense_status.update(label="Please choose a valid receipt", state="error", expanded=True)
                    st.error(f"Invalid receipt file. Only JPG/PNG under {MAX_RECEIPT_SIZE_MB}MB allowed.")
                else:
                    if hasattr(cursor, 'execute') and hasattr(cursor.connection, 'account'):  # crude check for Snowflake
                        cursor.execute("INSERT INTO expenses (category, sub_category, amount, date, spent_by, comments, receipt_path, receipt_blob, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active')", (category, sub_category, amount, date, spent_by, comments, receipt_path, receipt_bytes))
                    else:
                        cursor.execute("INSERT INTO expenses (category, sub_category, amount, date, spent_by, comments, receipt_path, receipt_blob, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active')", (category, sub_category, amount, date, spent_by, comments, receipt_path, receipt_bytes))
                    conn.commit()
                    # Fetch notification email recipients
                    cursor.execute("SELECT email FROM notification_emails")
                    recipients = [row[0] for row in cursor.fetchall()]
                    # Prepare email subject and body
                    subject = f"New Expense Added: {category} - {sub_category}"
                    with open("app/html/expense/expense_added_table.html", "r") as f:
                        html_template = f.read()
                    body = html_template.format(
                        category=category,
                        sub_category=sub_category,
                        amount=f"{amount:.2f}",
                        date=date,
                        spent_by=spent_by,
                        comments=comments
                    )
                    # Add Submitted by info after the table
                    admin_full_name = st.session_state.get("admin_full_name", "Admin")
                    body += f"<div style='margin-top:18px;font-size:1.08em;'><b>Submitted by:</b> <span style='color:#1976D2;'>{admin_full_name}</span></div>"
                    # Send email with receipt attached if present
                    from app.email_utils import send_email, send_email_with_attachment
                    if receipt_bytes:
                        mime_type = "image/jpeg" if receipt_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
                        for recipient in recipients:
                            send_email_with_attachment(subject, body, recipient, receipt_bytes, receipt_path, mime_type)
                    else:
                        send_email(subject, body, recipients)
                    st.session_state["expense_submission_in_progress"] = False
                    expense_status.update(label="Expense added", state="complete", expanded=False)
                    st.session_state["expense_success_message"] = "Expense added successfully and notification email sent."
                    # Set flag to clear input fields on next run
                    st.session_state["clear_expense_form"] = True
                    st.session_state["expense_inline_action"] = None
                    st.rerun()
    # Expenses List Section
    if selected_section == "Expenses" and not st.session_state.get("expense_inline_action"):
        category_options = ["All"] + sorted(df["Category"].dropna().unique().tolist())
        selected_category = st.session_state.get("filter_category", "All")
        selected_spent_by = st.session_state.get("filter_spent_by", "All") if is_admin else "All"
        filtered_df = df.copy()
        if selected_category != "All":
            filtered_df = filtered_df[filtered_df["Category"] == selected_category]

        if selected_spent_by != "All":
            filtered_df = filtered_df[filtered_df["Spent By"] == selected_spent_by]

        st.markdown(
            "<div style='height:1.25rem; clear:both;'></div>"
            "<div style='padding:0.7rem 0 0.55rem; border-top:1px solid #e4ddd7; color:#6a1b1b; font-size:1.05rem; font-weight:800;'>🧾 Detailed Expense Report</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:0.65rem;'></div>", unsafe_allow_html=True)
        with st.container(horizontal=True, wrap=True, vertical_alignment="center", gap="small"):
            st.markdown(
                '<div style="display:flex;align-items:center;min-height:2.35rem;color:#6d625b;font-size:0.82rem;font-weight:700;line-height:1.2;white-space:nowrap;">Filter by expense</div>',
                unsafe_allow_html=True,
            )
            st.selectbox(
                "Filter by category",
                category_options,
                index=category_options.index(selected_category) if selected_category in category_options else 0,
                format_func=lambda option: "All categories" if option == "All" else option,
                label_visibility="collapsed",
                key="filter_category",
            )
            if is_admin:
                spent_by_options = ["All"] + sorted(df["Spent By"].dropna().unique().tolist())
                st.selectbox(
                    "Filter by person",
                    spent_by_options,
                    index=spent_by_options.index(selected_spent_by) if selected_spent_by in spent_by_options else 0,
                    format_func=lambda option: "All people" if option == "All" else option,
                    label_visibility="collapsed",
                    key="filter_spent_by",
                )
                st.download_button(
                    "",
                    data=filtered_df.drop(columns=["Receipt Blob", "Comments"], errors="ignore").to_csv(index=False),
                    file_name="filtered_expenses.csv",
                    mime="text/csv",
                    key="download_filtered_expenses",
                    help="Download filtered expenses",
                    icon=":material/download:",
                )
        if filtered_df.empty:
            st.markdown(
                """
<div style="display:flex;align-items:center;gap:0.65rem;margin:0.15rem 0 0.8rem;padding:0.9rem 1rem;border:1px solid #eadcc6;border-left:4px solid #c8691d;border-radius:10px;background:linear-gradient(135deg,#fffdf8 0%,#f7eee3 100%);box-shadow:0 4px 10px rgba(105,76,52,0.1);color:#6d625b;font-family:'Trebuchet MS',Georgia,serif;font-size:0.9rem;font-weight:700;">
    <span style="font-size:1.15rem;">🧾</span>
    <span>No expenses match the selected filters.</span>
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            cat_summary = filtered_df.groupby("Category")["Amount"].sum().reset_index().sort_values(by="Amount", ascending=False)
            category_stats = "".join(
                f"<div class='expense-stat-card'><span class='expense-stat-label'>🗂️ {escape(str(row['Category']))}</span><span class='expense-stat-count'>${float(row['Amount']):,.2f}<span class='expense-stat-unit'>Total Amount</span></span></div>"
                for _, row in cat_summary.iterrows()
            )
            with open("app/html/expense/category_summary_card.html", "r") as f:
                card_template = f.read()
            st.markdown(
                card_template.format(
                    wallet_amount=float(wallet_amount),
                    total_payments=float(total_payments),
                    total_expenses=float(total_expenses),
                    wallet_percent=min(max(float(wallet_amount) / float(total_payments) * 100, 0), 100) if total_payments else 0,
                    table_rows=category_stats,
                ),
                unsafe_allow_html=True,
            )
            if is_admin:
                person_summary = (
                    filtered_df.assign(**{"Spent By": filtered_df["Spent By"].fillna("Unknown")})
                    .groupby("Spent By", as_index=False)["Amount"]
                    .sum()
                    .sort_values("Amount", ascending=False)
                    .rename(columns={"Spent By": "Name", "Amount": "Total Amount"})
                )
                person_stats = "".join(
                    f"<div class='expense-stat-card'><span class='expense-stat-label'>👤 {escape(str(row['Name']))}</span><span class='expense-stat-count'>${float(row['Total Amount']):,.2f}<span class='expense-stat-unit'>Total Amount</span></span></div>"
                    for _, row in person_summary.iterrows()
                )
                st.markdown(
                    f"""
<div class='expense-person-summary'>
<div class='expense-summary-heading'>👤 Expense Details by Person</div>
<div class='expense-stats-grid'>{person_stats}</div>
</div>
""",
                    unsafe_allow_html=True,
                )
            table_df = filtered_df.copy()
            table_df["Comments"] = table_df["Comments"].apply(
                lambda value: " | ".join(str(line).strip() for line in value if str(line).strip())
                if isinstance(value, list) else str(value or "")
            )
            table_df["ReceiptPath"] = table_df["Receipt"].apply(
                lambda value: value if isinstance(value, str) and value.strip() else ""
            )
            table_df["Receipt"] = table_df["Receipt"].apply(
                lambda value: "Available" if isinstance(value, str) and value.strip() else "Not attached"
            )
            table_df["Expense"] = table_df.apply(
                lambda row: f"{row['Category']} - {row['Sub Category']}" if row["Sub Category"] else str(row["Category"]),
                axis=1,
            )
            def build_receipt_html(row):
                receipt_name = str(row.get("ReceiptPath") or "")
                receipt_blob = row.get("Receipt Blob")
                if not receipt_name or not receipt_blob:
                    return "<span class='expense-table-receipt no-receipt'>Not attached</span>"
                if isinstance(receipt_blob, memoryview):
                    receipt_bytes = receipt_blob.tobytes()
                elif isinstance(receipt_blob, (bytearray, bytes)):
                    receipt_bytes = bytes(receipt_blob)
                else:
                    receipt_bytes = receipt_blob
                ext = receipt_name.rsplit(".", 1)[-1].lower() if "." in receipt_name else "png"
                mime_type = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
                data_uri = f"data:{mime_type};base64,{base64.b64encode(receipt_bytes).decode('ascii')}"
                return (
                    f"<div class='receipt-preview-inline'><img src='{data_uri}' class='receipt-preview-image' alt='Receipt preview' /></div>"
                )
            table_df["ReceiptHtml"] = table_df.apply(build_receipt_html, axis=1)
            report_columns = ["Expense", "Amount", "Date"]
            if is_admin:
                report_columns.append("Spent By")
            report_columns.extend(["ReceiptHtml", "Comments"])
            table_df = table_df[report_columns].sort_values(
                by="Date", ascending=False
            ).reset_index(drop=True)
            def build_expense_row(row):
                spent_by_cell = f"<td>{escape(str(row['Spent By'] or 'Unknown'))}</td>" if is_admin else ""
                return (
                    f"<tr>"
                    f"<td class='expense-table-name'>{escape(str(row['Expense']))}</td>"
                    f"<td class='expense-table-amount'>${float(row['Amount']):,.2f}</td>"
                    f"<td>{escape(str(row['Date']))}</td>"
                    f"{spent_by_cell}"
                    f"<td>{row['ReceiptHtml']}</td>"
                    f"<td>{escape(str(row['Comments']))}</td>"
                    f"</tr>"
                )

            expense_table_rows = "".join(
                build_expense_row(row)
                for _, row in table_df.iterrows()
            )
            report_headers = "<th>Expense</th><th>Amount</th><th>Date</th>"
            if is_admin:
                report_headers += "<th>Spent By</th>"
            report_headers += "<th>Receipt</th><th>Comments</th>"
            st.markdown(
                f"""
<style>
    .expense-table-wrap {{ margin-top:0.7rem; overflow-x:auto; border:1px solid #e4ddd7; border-radius:12px; box-shadow:0 3px 10px rgba(106,27,27,0.08); }}
    .expense-table {{ width:100%; min-width:0; table-layout:fixed; border-collapse:collapse; color:#3e2723; font-size:0.82rem; }}
    .expense-table th {{ padding:0.65rem 0.55rem; background:#6a1b1b; color:#fffaf0; font-size:0.72rem; font-weight:800; letter-spacing:0.04em; text-align:left; text-transform:uppercase; white-space:nowrap; vertical-align:middle; }}
    .expense-table th:nth-child(1) {{ width:40%; }}
    .expense-table th:nth-child(2) {{ width:14%; text-align:right; }}
    .expense-table th:nth-child(3) {{ width:16%; }}
    .expense-table th:nth-child(4) {{ width:12%; }}
    .expense-table th:nth-child(5) {{ width:18%; }}
    .expense-table-admin th:nth-child(1) {{ width:28%; }}
    .expense-table-admin th:nth-child(2) {{ width:12%; text-align:right; }}
    .expense-table-admin th:nth-child(3) {{ width:13%; }}
    .expense-table-admin th:nth-child(4) {{ width:15%; }}
    .expense-table-admin th:nth-child(5) {{ width:14%; }}
    .expense-table-admin th:nth-child(6) {{ width:18%; }}
    .expense-table td {{ padding:0.62rem 0.55rem; border-top:1px solid #eee4dc; vertical-align:top; overflow-wrap:anywhere; }}
    .expense-table tr:nth-child(even) td {{ background:#fffaf5; }}
    .expense-table-name {{ color:#3e2723; font-weight:700; line-height:1.35; }}
    .expense-table-amount {{ color:#8b1737; font-weight:800; text-align:right; white-space:nowrap; }}
    .expense-table-receipt {{ font-size:0.72rem; font-weight:700; }}
    .expense-table-receipt.has-receipt {{ color:#2e7d32; }}
    .expense-table-receipt.no-receipt {{ color:#8d6e63; }}
    .receipt-preview-inline {{ display:flex; align-items:center; justify-content:center; }}
    .receipt-preview-image {{ max-width:100%; max-height:90px; border-radius:8px; border:1px solid #e0d7cf; background:#fff; display:block; }}
    @media (max-width:640px) {{
        .expense-table {{ font-size:0.75rem; }}
        .expense-table th, .expense-table td {{ padding:0.55rem 0.38rem; }}
        .expense-table th {{ font-size:0.64rem; }}
        .expense-table th:nth-child(1) {{ width:36%; }}
        .expense-table th:nth-child(2) {{ width:15%; }}
        .expense-table th:nth-child(3) {{ width:16%; }}
        .expense-table th:nth-child(4) {{ width:12%; }}
        .expense-table th:nth-child(5) {{ width:21%; }}
        .expense-table-admin th:nth-child(1) {{ width:26%; }}
        .expense-table-admin th:nth-child(2) {{ width:13%; }}
        .expense-table-admin th:nth-child(3) {{ width:14%; }}
        .expense-table-admin th:nth-child(4) {{ width:16%; }}
        .expense-table-admin th:nth-child(5) {{ width:13%; }}
        .expense-table-admin th:nth-child(6) {{ width:18%; }}
    }}
</style>
<div class='expense-table-wrap'>
<table class='expense-table {'expense-table-admin' if is_admin else ''}'>
<thead><tr>{report_headers}</tr></thead>
<tbody>{expense_table_rows}</tbody>
</table>
</div>
""",
                unsafe_allow_html=True,
            )
        
        # Send Expenses Report via Email (admin only)
        if is_admin and st.button("📧 Send Expenses Report via Email", key="send_expenses_email"):
            # Ensure email column exists in committee_members
            try:
                cursor.execute("ALTER TABLE committee_members ADD COLUMN email TEXT")
                conn.commit()
            except Exception:
                pass  # Column might already exist
            
            # Get notification email recipients
            cursor.execute("SELECT email FROM notification_emails WHERE email IS NOT NULL AND email != ''")
            recipients = [row[0] for row in cursor.fetchall()]
            
            # Add committee members emails if they have one
            try:
                cursor.execute("SELECT email FROM committee_members WHERE email IS NOT NULL AND email != ''")
                committee_emails = [row[0] for row in cursor.fetchall()]
                recipients.extend(committee_emails)
            except Exception:
                pass  # Email column might not exist
            
            recipients = list(set(recipients))  # Remove duplicates
            
            if not recipients:
                st.warning("No notification emails found. Please add email addresses in Admin panel or Committee Members.")
            else:
                from app.email_utils import send_email, send_email_with_attachment
                import smtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
                from email.mime.base import MIMEBase
                from email import encoders
                
                EMAIL_SENDER = st.secrets["email_sender"]
                EMAIL_PASSWORD = st.secrets["email_password"]
                SMTP_SERVER = st.secrets["smtp_server"]
                SMTP_PORT = st.secrets["smtp_port"]
                
                admin_full_name = st.session_state.get("admin_full_name", "Admin")
                
                # Build email body with expense details
                expense_details_html = "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse; width:100%; margin-top:10px;'>"
                expense_details_html += "<tr style='background:#6a1b1b; color:#fff; font-weight:bold;'><th>ID</th><th>Expense</th><th>Amount</th><th>Date</th><th>Spent By</th><th>Comments</th></tr>"
                
                for _, row in filtered_df.iterrows():
                    spent_by = row.get("Spent By", "Unknown")
                    comments_display = " | ".join(row["Comments"]) if isinstance(row["Comments"], list) else str(row.get("Comments", ""))
                    expense_details_html += f"<tr><td>{row['ID']}</td><td>{escape(str(row['Category'])) + ' - ' + escape(str(row['Sub Category']))}</td><td>${float(row['Amount']):,.2f}</td><td>{row['Date']}</td><td>{escape(str(spent_by))}</td><td>{escape(comments_display)}</td></tr>"
                
                expense_details_html += "</table>"
                
                body = f"""
                <b>Expense Report Summary</b><br><br>
                <p>Total Expenses: <b>${float(filtered_df['Amount'].sum()):,.2f}</b></p>
                <p>Number of Expenses: <b>{len(filtered_df)}</b></p>
                <p>Date Generated: <b>{datetime.date.today()}</b></p>
                <p>Generated by: <b>{admin_full_name}</b></p>
                {expense_details_html}
                """
                
                # Send email with attachments for each receipt
                for recipient in recipients:
                    msg = MIMEMultipart()
                    msg['From'] = EMAIL_SENDER
                    msg['To'] = recipient
                    msg['Subject'] = f"Expense Report - {datetime.date.today()}"
                    msg.attach(MIMEText(body, 'html'))
                    
                    # Add receipt images as attachments
                    for _, row in filtered_df.iterrows():
                        receipt_blob = row.get("Receipt Blob")
                        receipt_path = row.get("ReceiptPath")
                        
                        if receipt_blob and isinstance(receipt_path, str) and receipt_path.strip():
                            try:
                                expense_id = row['ID']
                                spent_by = row.get("Spent By", "Unknown")
                                amount = float(row['Amount'])
                                
                                # Convert to bytes
                                if isinstance(receipt_blob, memoryview):
                                    receipt_bytes = receipt_blob.tobytes()
                                elif isinstance(receipt_blob, bytearray):
                                    receipt_bytes = bytes(receipt_blob)
                                else:
                                    receipt_bytes = receipt_blob
                                
                                # Create filename: id_name_amount.ext
                                ext = receipt_path.rsplit(".", 1)[-1].lower() if "." in receipt_path else "jpg"
                                filename = f"EXP_{expense_id:03d}_{spent_by.replace(' ', '_')}_{amount:.2f}.{ext}"
                                
                                # Determine MIME type
                                mime_type = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
                                
                                # Attach image
                                part = MIMEBase('application', 'octet-stream')
                                part.set_payload(receipt_bytes)
                                encoders.encode_base64(part)
                                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                                part.add_header('Content-Type', mime_type)
                                msg.attach(part)
                            except Exception as e:
                                st.warning(f"Could not attach receipt for expense {row['ID']}: {e}")
                    
                    # Send email
                    try:
                        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                            server.starttls()
                            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                            server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
                    except Exception as e:
                        st.error(f"Failed to send email to {recipient}: {e}")
                
                st.success("✅ Expense report sent to all notification emails and committee members!")

    # Expense Summary by Person Section (admin only)
    if is_admin and selected_section == "Expenses" and st.session_state.get("expense_inline_action") == "summary":
            cursor.execute("SELECT spent_by, SUM(amount) FROM expenses WHERE status='active' GROUP BY spent_by ORDER BY SUM(amount) DESC")
            summary_rows = cursor.fetchall()
            if summary_rows:
                summary_df = pd.DataFrame(summary_rows, columns=["Name", "Total Amount"])
                total_summary_amount = sum([row[1] for row in summary_rows if row[1] is not None])
                summary_df["Total Amount"] = summary_df["Total Amount"].apply(lambda x: f"<span style='background-color:#FFECB3;color:#6D4C41;padding:4px 12px;border-radius:16px;font-weight:bold;'>{x:.2f}</span>")
                st.markdown(summary_df.to_html(escape=False, index=False, justify='center'), unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:1.1em; font-weight:bold; margin-top:10px; text-align:right;'>Total Amount: <span style='color:#6D4C41'>{total_summary_amount:.2f}</span></div>", unsafe_allow_html=True)
            else:
                st.info("No expense summary available yet.")
    # Edit/Delete Expense Section (admin only)
    if is_admin and selected_section == "Expenses" and st.session_state.get("expense_inline_action") in ("edit", "delete"):
            if rows:
                categories = []
                cursor.execute("SELECT item FROM sponsorship_items")
                categories = [row[0] for row in cursor.fetchall()]
                if "Miscellaneous" not in categories:
                    categories.append("Miscellaneous")
                # Sort by ID
                sorted_df = df.sort_values(by="ID")
                expense_options = ["Choose an item"] + [f"ID {row['ID']} | Spent By: {row['Spent By']} | Amount: {row['Amount']}" for _, row in sorted_df.iterrows()]
                selected_idx = st.selectbox("Select Expense to Edit/Delete", range(len(expense_options)), format_func=lambda i: expense_options[i])
                if selected_idx == 0:
                    st.info("Please choose an expense to edit or delete.")
                else:
                    selected_id = sorted_df["ID"].tolist()[selected_idx-1]
                    entry = sorted_df[sorted_df["ID"]==selected_id].iloc[0].copy()
                    import re
                    amount_str = str(entry["Amount"])
                    amount_val = float(re.sub(r"[^0-9.]+", "", amount_str))
                    date_str = str(entry["Date"])
                    date_val = re.sub(r"[^0-9\-]", "", date_str)
                    try:
                        date_obj = pd.to_datetime(date_val).date()
                    except Exception:
                        date_obj = datetime.date.today()
                    edit_tab, delete_tab = st.tabs(["Edit", "Delete"])
                    with edit_tab:
                        new_category = st.selectbox("Category", categories, index=categories.index(entry["Category"]) if entry["Category"] in categories else 0, key=f"edit_category_{selected_id}")
                        new_sub_category = st.text_input("Sub Category", value=entry["Sub Category"])
                        new_amount = st.number_input("Amount", value=amount_val, format="%.2f")
                        new_date = st.date_input("Date", value=date_obj)
                        edit_spent_by_options = spent_by_options.copy()
                        if entry["Spent By"] not in edit_spent_by_options and entry["Spent By"]:
                            edit_spent_by_options.insert(0, entry["Spent By"])
                        new_spent_by = st.selectbox(
                            "Spent By",
                            edit_spent_by_options,
                            index=edit_spent_by_options.index(entry["Spent By"]) if entry["Spent By"] in edit_spent_by_options else 0,
                            key=f"edit_spent_by_{selected_id}"
                        )
                        plain_comments = entry["Comments"]
                        if isinstance(plain_comments, list):
                            plain_comments = "\n".join([str(line) for line in plain_comments if str(line).strip()])
                        plain_comments = re.sub(r"<[^>]+>", "", plain_comments)
                        plain_comments = plain_comments.replace("📝 ", "")
                        plain_comments = plain_comments.replace("&nbsp;|&nbsp;", " | ")
                        plain_comments = plain_comments.replace("&nbsp;", " ")
                        plain_comments = re.sub(r"(\$[0-9,.]+)", r"\1\n", plain_comments)
                        plain_comments = re.sub(r"\n\s*", "\n", plain_comments)
                        plain_comments = plain_comments.strip()
                        new_comments = st.text_area("Comments", value=plain_comments)
                        receipt_name = entry["Receipt"]
                        receipt_blob = entry["Receipt Blob"]
                        receipt_deleted = False
                        new_receipt_bytes = None
                        new_receipt_path = None
                        if isinstance(receipt_name, str) and receipt_name.strip() and receipt_blob:
                            st.markdown("<b>Current Receipt:</b>", unsafe_allow_html=True)
                            data = receipt_blob
                            if isinstance(data, memoryview):
                                data = data.tobytes()
                            elif isinstance(data, bytearray):
                                data = bytes(data)
                            st.download_button(
                                label="Download Receipt",
                                data=data,
                                file_name=receipt_name,
                                mime="image/jpeg" if receipt_name.lower().endswith((".jpg", ".jpeg")) else "image/png",
                                key=f"edit_download_{selected_id}"
                            )
                            if st.button("Delete Receipt", key=f"delete_receipt_{selected_id}"):
                                cursor.execute("UPDATE expenses SET receipt_path=NULL, receipt_blob=NULL WHERE id=%s", (selected_id,))
                                conn.commit()
                                st.success("Receipt deleted. You can upload a new one below.")
                                receipt_deleted = True
                                st.rerun()
                        else:
                            st.info("No receipt uploaded yet. You can upload one below.")
                        MAX_RECEIPT_SIZE_MB = 1
                        MAX_RECEIPT_SIZE_BYTES = MAX_RECEIPT_SIZE_MB * 1024 * 1024
                        uploaded_new_receipt = st.file_uploader(f"Upload New Receipt (JPG/PNG, max {MAX_RECEIPT_SIZE_MB}MB)", type=["jpg", "jpeg", "png"], key=f"edit_upload_receipt_{selected_id}")
                        if uploaded_new_receipt is not None:
                            if uploaded_new_receipt.size > MAX_RECEIPT_SIZE_BYTES:
                                st.error(f"Receipt file size should not exceed {MAX_RECEIPT_SIZE_MB} MB.")
                            elif uploaded_new_receipt.type not in ["image/jpeg", "image/png"]:
                                st.error("Only JPG and PNG files are allowed.")
                            else:
                                import uuid
                                ext = uploaded_new_receipt.name.split('.')[-1]
                                new_receipt_path = f"receipt_{uuid.uuid4().hex}.{ext}"
                                new_receipt_bytes = uploaded_new_receipt.read()
                        if st.button("Update Expense"):
                            if new_receipt_bytes and new_receipt_path:
                                cursor.execute("UPDATE expenses SET category=%s, sub_category=%s, amount=%s, date=%s, spent_by=%s, comments=%s, receipt_path=%s, receipt_blob=%s, status='active' WHERE id=%s", (new_category, new_sub_category, new_amount, new_date, new_spent_by, new_comments, new_receipt_path, new_receipt_bytes, selected_id))
                            else:
                                cursor.execute("UPDATE expenses SET category=%s, sub_category=%s, amount=%s, date=%s, spent_by=%s, comments=%s, status='active' WHERE id=%s", (new_category, new_sub_category, new_amount, new_date, new_spent_by, new_comments, selected_id))
                            conn.commit()
                            subject = f"Expense Edited: {new_category} - {new_sub_category}"
                            with open("app/html/expense/edit_expense_notification.html", "r") as f:
                                html_template = f.read()
                            body = html_template.format(
                                category=new_category,
                                sub_category=new_sub_category,
                                amount=f"{new_amount:.2f}",
                                date=new_date,
                                spent_by=new_spent_by,
                                comments=new_comments
                            )
                            with open("app/html/expense/expense_edited_table.html", "r") as f:
                                html_template = f.read()
                            body = html_template.format(
                                category=new_category,
                                sub_category=new_sub_category,
                                amount=f"{new_amount:.2f}",
                                date=new_date,
                                spent_by=new_spent_by,
                                comments=new_comments
                            )
                            recipients = [st.secrets.get("admin_email", "")]
                            if new_receipt_bytes and new_receipt_path:
                                mime_type = "image/jpeg" if new_receipt_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
                                from app.email_utils import send_email_with_attachment
                                send_email_with_attachment(subject, body, recipients[0], new_receipt_bytes, new_receipt_path, mime_type)
                            else:
                                from app.email_utils import send_email
                                send_email(subject, body, recipients)
                            st.success("✅ Updated and notification email sent!")
                            st.session_state["expense_inline_action"] = None
                            st.rerun()
                    with delete_tab:
                        entered_cat = st.text_input(f"Type the Category to confirm deletion ({entry['Category']})", key=f"delete_cat_{selected_id}")
                        subcat_display = entry['Sub Category'].strip()
                        entered_subcat = st.text_input(f"Type the Sub Category to confirm deletion ({subcat_display})", key=f"delete_subcat_{selected_id}")
                        confirm_message = f"Type <b>{entry['Category']}</b> and <b>{entry['Sub Category']}</b> above and click Delete to confirm."
                        st.markdown(confirm_message, unsafe_allow_html=True)
                        if st.button("Delete Expense", key=f"delete_expense_{selected_id}"):
                            if entered_cat.strip() == entry['Category'].strip() and entered_subcat.strip() == entry['Sub Category'].strip():
                                cursor.execute("UPDATE expenses SET status='inactive' WHERE id=%s", (selected_id,))
                                conn.commit()
                                subject = f"Expense Deleted: {entry['Category']} - {entry['Sub Category']}"
                                with open("app/html/expense/delete_expense_confirm.html", "r") as f:
                                    html_template = f.read()
                                body = html_template.format(
                                    category=entry['Category'],
                                    sub_category=entry['Sub Category'],
                                    amount=f"{entry['Amount']:.2f}",
                                    date=entry['Date'],
                                    spent_by=entry['Spent By'],
                                    comments=entry['Comments']
                                )
                                with open("app/html/expense/expense_deleted_table.html", "r") as f:
                                    html_template = f.read()
                                body = html_template.format(
                                    category=entry['Category'],
                                    sub_category=entry['Sub Category'],
                                    amount=f"{entry['Amount']:.2f}",
                                    date=entry['Date'],
                                    spent_by=entry['Spent By'],
                                    comments=entry['Comments']
                                )
                                cursor.execute("SELECT email FROM notification_emails")
                                recipients = [row[0] for row in cursor.fetchall()]
                                from app.email_utils import send_email
                                send_email(subject, body, recipients)
                                st.success("🗑️ Deleted and notification email sent!")
                                st.session_state["expense_inline_action"] = None
                                st.rerun()
                            else:
                                st.warning(f"Please type the exact Category '{entry['Category']}' and Sub Category '{entry['Sub Category']}' to confirm deletion.")
            else:
                st.info("No expenses recorded yet.")

