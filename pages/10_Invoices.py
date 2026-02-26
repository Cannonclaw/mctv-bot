# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Internal invoice management — create, send, track payments, and AR aging."""

import streamlit as st
import sys
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.supabase_client import is_configured
from services.invoice_service import (
    create_invoice, get_all_invoices, get_invoice, update_invoice,
    delete_invoice, send_invoice, mark_paid, void_invoice,
    mark_overdue, check_and_mark_overdue, generate_monthly_invoices,
    get_ar_aging, get_invoice_summary,
    get_overdue_invoices, send_bulk_reminders,
    record_partial_payment, get_payment_history, get_balance_due,
)
import json
from services.portal_service import get_all_clients, get_client
from services.contract_service import get_contracts_for_client

st.set_page_config(page_title="Invoices - MCTV Bot", page_icon="\U0001F4B0", layout="wide")

if not check_password():
    st.stop()

if not is_configured():
    st.warning("Supabase is not configured yet.")
    st.markdown(
        "Set `SUPABASE_URL`, `SUPABASE_KEY`, and `SUPABASE_SERVICE_KEY` in your environment."
    )
    st.stop()


# ── Page header ─────────────────────────────────────────────────────────────

st.markdown("## Invoice Management")
st.caption("Create invoices, track payments, send reminders, and monitor accounts receivable.")

# ── Summary metrics ─────────────────────────────────────────────────────────

try:
    summary = get_invoice_summary()
except Exception:
    st.error("Unable to load invoice summary.")
    summary = {}

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Invoices", summary.get("total", 0))
c2.metric("Drafts", summary.get("draft", 0))
c3.metric("Sent", summary.get("sent", 0))
c4.metric("Overdue", summary.get("overdue", 0))
c5.metric("Outstanding", f"${summary.get('total_outstanding', 0):,.2f}")
c6.metric("Collected", f"${summary.get('total_collected', 0):,.2f}")

st.divider()

# ── Search ─────────────────────────────────────────────────────────────────
invoice_search = st.text_input("🔍 Search invoices...", key="invoice_search",
                               placeholder="Search by invoice number, client name, or status")

# ── Tabs ────────────────────────────────────────────────────────────────────

tab_list, tab_create, tab_aging, tab_tools = st.tabs([
    "All Invoices", "Create Invoice", "AR Aging", "Batch Tools"
])


# ── TAB: All Invoices ──────────────────────────────────────────────────────

with tab_list:
    filter_col1, filter_col2 = st.columns([3, 7])
    with filter_col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Draft", "Sent", "Overdue", "Paid", "Void"],
            index=0,
            key="inv_status_filter",
        )

    status_val = status_filter.lower() if status_filter != "All" else None
    try:
        invoices = get_all_invoices(status=status_val)
    except Exception:
        st.error("Unable to load invoices. Please try again later.")
        invoices = []

    # Build client name cache for search filtering
    _inv_client_cache = {}
    for _inv in invoices:
        _cid = _inv.get("client_id", "")
        if _cid and _cid not in _inv_client_cache:
            _cl = get_client(_cid)
            _inv_client_cache[_cid] = _cl.get("business_name", "Unknown") if _cl else "Unknown"

    # Apply search filter
    if invoice_search:
        _q = invoice_search.strip().lower()
        invoices = [
            i for i in invoices
            if _q in (i.get("invoice_number", "") or "").lower()
            or _q in (i.get("status", "") or "").lower()
            or _q in _inv_client_cache.get(i.get("client_id", ""), "Unknown").lower()
        ]

    if not invoices:
        st.info("No invoices found. Use the 'Create Invoice' tab to get started.")
    else:
        st.caption(f"Showing {len(invoices)} invoice(s)")

        for inv in invoices:
            iid = inv.get("id", "")
            inv_num = inv.get("invoice_number", "")
            amount = float(inv.get("amount", 0))
            istatus = inv.get("status", "draft")
            due_date = inv.get("due_date", "")
            issued_date = inv.get("issued_date", "")
            paid_date = inv.get("paid_date", "")
            client_id = inv.get("client_id", "")

            # Get client name (use cache)
            client_name = _inv_client_cache.get(client_id, "Unknown")

            # Status emoji
            status_emoji = {
                "draft": "\u270F\uFE0F",
                "sent": "\U0001F4E8",
                "viewed": "\U0001F440",
                "overdue": "\U0001F534",
                "paid": "\u2705",
                "void": "\u26D4",
            }.get(istatus, "\u26AA")

            with st.expander(
                f"{status_emoji} **{inv_num}** — {client_name} | "
                f"${amount:,.2f} | Due: {due_date} | {istatus.title()}",
                expanded=False,
            ):
                # ── Balance / partial payment info ─────────────────
                amount_paid = float(inv.get("amount_paid", 0))
                balance_due = max(amount - amount_paid, 0.0)

                det1, det2 = st.columns(2)
                with det1:
                    st.markdown("**Invoice Details**")
                    st.text(f"Invoice #: {inv_num}")
                    st.text(f"Client: {client_name}")
                    st.text(f"Amount: ${amount:,.2f}")
                    if amount_paid > 0:
                        st.text(f"Paid: ${amount_paid:,.2f}")
                        st.text(f"Balance Due: ${balance_due:,.2f}")
                    st.text(f"Description: {inv.get('description', '')}")
                with det2:
                    st.markdown("**Dates & Status**")
                    st.text(f"Issued: {issued_date}")
                    st.text(f"Due: {due_date}")
                    st.text(f"Status: {istatus.title()}")
                    if paid_date:
                        st.text(f"Paid: {paid_date}")
                    period_start = inv.get("period_start", "")
                    period_end = inv.get("period_end", "")
                    if period_start:
                        st.text(f"Period: {period_start} to {period_end}")
                    last_reminder = inv.get("last_reminder_sent", "")
                    if last_reminder:
                        st.text(f"Last Reminder: {last_reminder}")

                # ── Payment History ────────────────────────────────
                payments_raw = inv.get("payments")
                payments_list = []
                if payments_raw:
                    if isinstance(payments_raw, str):
                        try:
                            payments_list = json.loads(payments_raw)
                        except (json.JSONDecodeError, TypeError):
                            payments_list = []
                    elif isinstance(payments_raw, list):
                        payments_list = payments_raw

                if payments_list:
                    st.markdown("**Payment History**")
                    for pidx, pmt in enumerate(payments_list, 1):
                        pmt_amt = float(pmt.get("amount", 0))
                        pmt_date = pmt.get("date", "")
                        pmt_method = pmt.get("method", "")
                        pmt_ref = pmt.get("reference", "")
                        ref_str = f" (Ref: {pmt_ref})" if pmt_ref else ""
                        st.caption(
                            f"  {pidx}. ${pmt_amt:,.2f} — {pmt_method} on {pmt_date}{ref_str}"
                        )

                if inv.get("notes"):
                    st.caption(f"Notes: {inv.get('notes')}")

                st.divider()

                # ── Action buttons ──────────────────────────────────
                act1, act2, act3, act4, act5, act6 = st.columns(6)

                with act1:
                    if istatus == "draft":
                        if st.button("Send Invoice", key=f"send_inv_{iid}",
                                     type="primary", width='stretch'):
                            result = send_invoice(iid)
                            if result:
                                st.success("Invoice sent. Client notified.")
                                st.rerun()
                            else:
                                st.error("Failed to send invoice.")

                with act2:
                    if istatus in ("sent", "viewed", "overdue"):
                        if st.button("Mark Paid", key=f"pay_inv_{iid}",
                                     type="primary", width='stretch'):
                            st.session_state[f"show_pay_{iid}"] = True

                with act3:
                    if istatus in ("sent", "viewed", "overdue"):
                        if st.button("Record Payment", key=f"partial_inv_{iid}",
                                     width='stretch'):
                            st.session_state[f"show_partial_{iid}"] = True

                with act4:
                    if istatus in ("sent", "viewed"):
                        if st.button("Mark Overdue", key=f"overdue_inv_{iid}",
                                     width='stretch'):
                            result = mark_overdue(iid)
                            if result:
                                st.success("Marked overdue. Reminder sent.")
                                st.rerun()

                with act5:
                    if istatus in ("draft", "sent", "viewed", "overdue"):
                        if st.button("Void", key=f"void_inv_{iid}",
                                     width='stretch'):
                            st.session_state[f"confirm_void_{iid}"] = True

                with act6:
                    if istatus in ("draft", "void"):
                        if st.button("Delete", key=f"del_inv_{iid}",
                                     width='stretch'):
                            st.session_state[f"confirm_del_inv_{iid}"] = True

                # ── Mark paid form ──────────────────────────────────
                if st.session_state.get(f"show_pay_{iid}"):
                    st.markdown("---")
                    pay_col1, pay_col2 = st.columns(2)
                    with pay_col1:
                        pay_date = st.date_input("Payment Date", value=date.today(),
                                                 key=f"pay_date_{iid}")
                    with pay_col2:
                        if st.button("Confirm Payment", key=f"confirm_pay_{iid}",
                                     type="primary", width='stretch'):
                            result = mark_paid(iid, pay_date.isoformat())
                            if result:
                                st.success(f"Invoice {inv_num} marked as paid.")
                                del st.session_state[f"show_pay_{iid}"]
                                st.rerun()
                        if st.button("Cancel", key=f"cancel_pay_{iid}",
                                     width='stretch'):
                            del st.session_state[f"show_pay_{iid}"]
                            st.rerun()

                # ── Record partial payment form ─────────────────────
                if st.session_state.get(f"show_partial_{iid}"):
                    st.markdown("---")
                    st.markdown("**Record a Payment**")
                    max_balance = max(amount - amount_paid, 0.01)
                    pp1, pp2 = st.columns(2)
                    with pp1:
                        partial_amount = st.number_input(
                            "Payment Amount ($)", min_value=0.01,
                            max_value=max_balance, value=min(max_balance, max_balance),
                            step=50.0, key=f"partial_amt_{iid}",
                        )
                        partial_date = st.date_input(
                            "Payment Date", value=date.today(),
                            key=f"partial_date_{iid}",
                        )
                    with pp2:
                        partial_method = st.selectbox(
                            "Payment Method",
                            ["Check", "Cash", "Card", "ACH", "Other"],
                            key=f"partial_method_{iid}",
                        )
                        partial_ref = st.text_input(
                            "Reference / Note (optional)",
                            placeholder="Check #, transaction ID, etc.",
                            key=f"partial_ref_{iid}",
                        )

                    pp_btn1, pp_btn2 = st.columns(2)
                    with pp_btn1:
                        if st.button("Submit Payment", key=f"submit_partial_{iid}",
                                     type="primary", width='stretch'):
                            result = record_partial_payment(
                                invoice_id=iid,
                                amount=partial_amount,
                                payment_date=partial_date.isoformat(),
                                method=partial_method,
                                reference=partial_ref,
                            )
                            if result:
                                new_bal = max(amount - amount_paid - partial_amount, 0)
                                if new_bal <= 0:
                                    st.success(f"Payment recorded. Invoice {inv_num} is now PAID IN FULL.")
                                else:
                                    st.success(
                                        f"Payment of ${partial_amount:,.2f} recorded. "
                                        f"Remaining balance: ${new_bal:,.2f}"
                                    )
                                del st.session_state[f"show_partial_{iid}"]
                                st.rerun()
                            else:
                                st.error("Failed to record payment.")
                    with pp_btn2:
                        if st.button("Cancel", key=f"cancel_partial_{iid}",
                                     width='stretch'):
                            del st.session_state[f"show_partial_{iid}"]
                            st.rerun()

                # ── Void confirmation ───────────────────────────────
                if st.session_state.get(f"confirm_void_{iid}"):
                    st.warning(f"Void invoice {inv_num}?")
                    vc1, vc2 = st.columns(2)
                    with vc1:
                        void_reason = st.text_input("Reason", key=f"void_reason_{iid}")
                        if st.button("Yes, Void", key=f"yes_void_{iid}",
                                     width='stretch'):
                            void_invoice(iid, reason=void_reason)
                            st.success("Invoice voided.")
                            del st.session_state[f"confirm_void_{iid}"]
                            st.rerun()
                    with vc2:
                        if st.button("Cancel", key=f"no_void_{iid}",
                                     width='stretch'):
                            del st.session_state[f"confirm_void_{iid}"]
                            st.rerun()

                # ── Delete confirmation ─────────────────────────────
                if st.session_state.get(f"confirm_del_inv_{iid}"):
                    st.warning(f"Permanently delete invoice {inv_num}?")
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        if st.button("Yes, Delete", key=f"yes_del_inv_{iid}",
                                     width='stretch'):
                            delete_invoice(iid)
                            del st.session_state[f"confirm_del_inv_{iid}"]
                            st.rerun()
                    with dc2:
                        if st.button("Cancel", key=f"no_del_inv_{iid}",
                                     width='stretch'):
                            del st.session_state[f"confirm_del_inv_{iid}"]
                            st.rerun()


# ── TAB: Create Invoice ────────────────────────────────────────────────────

with tab_create:
    st.markdown("### Create New Invoice")

    clients = get_all_clients()
    if not clients:
        st.warning("No clients found. Add a client first.")
        st.page_link("pages/8_Clients.py", label="Go to Client Management", icon="\U0001F465")
        st.stop()

    client_options = {
        f"{c.get('business_name', 'Unknown')} ({c.get('contact_name', '')})": c.get("id", "")
        for c in clients
    }

    with st.form("new_invoice_form"):
        # Client selection
        selected_label = st.selectbox("Client *", options=list(client_options.keys()))
        selected_client_id = client_options.get(selected_label, "")

        # Contract association (optional)
        client_contracts = []
        if selected_client_id:
            client_contracts = get_contracts_for_client(selected_client_id)

        contract_options = {"None": ""}
        for con in client_contracts:
            label = f"{con.get('title', 'Contract')} (${float(con.get('monthly_rate', 0)):,.2f}/mo)"
            contract_options[label] = con.get("id", "")

        selected_contract_label = st.selectbox(
            "Associated Contract (optional)",
            options=list(contract_options.keys()),
        )
        selected_contract_id = contract_options.get(selected_contract_label, "")

        # Amount and description
        fc1, fc2 = st.columns(2)
        with fc1:
            # Pre-fill amount from contract if selected
            default_amount = 350.0
            if selected_contract_id:
                for con in client_contracts:
                    if con.get("id") == selected_contract_id:
                        default_amount = float(con.get("monthly_rate", 350))
                        break

            amount = st.number_input("Amount ($) *", min_value=0.01,
                                     value=default_amount, step=50.0)

        with fc2:
            description = st.text_input("Description",
                                        value="Monthly advertising",
                                        placeholder="Monthly advertising")

        # Dates
        dt1, dt2, dt3 = st.columns(3)
        with dt1:
            due_date = st.date_input("Due Date",
                                     value=date.today() + timedelta(days=30))
        with dt2:
            period_start = st.date_input("Period Start",
                                         value=date.today().replace(day=1))
        with dt3:
            next_month = (date.today().replace(day=28) + timedelta(days=4)).replace(day=1)
            period_end_default = next_month - timedelta(days=1)
            period_end = st.date_input("Period End", value=period_end_default)

        notes = st.text_area("Internal Notes", height=60,
                             placeholder="Notes (not visible to client)")

        submitted = st.form_submit_button("Create Invoice", type="primary",
                                          width='stretch')

        if submitted:
            if not selected_client_id:
                st.error("Please select a client.")
            elif amount <= 0:
                st.error("Amount must be greater than zero.")
            else:
                with st.spinner("Creating invoice..."):
                    result = create_invoice(
                        client_id=selected_client_id,
                        amount=amount,
                        description=description,
                        due_date=due_date.isoformat(),
                        contract_id=selected_contract_id,
                        period_start=period_start.isoformat(),
                        period_end=period_end.isoformat(),
                        notes=notes,
                    )
                    if result:
                        inv_num = result.get("invoice_number", "")
                        st.success(f"Invoice **{inv_num}** created for ${amount:,.2f}.")

                        # Auto-sync to QuickBooks if connected
                        try:
                            from services.quickbooks_service import is_connected, sync_invoice_to_qb
                            if is_connected():
                                client_data = get_client(selected_client_id)
                                if client_data:
                                    qb_inv = sync_invoice_to_qb(result, client_data)
                                    if qb_inv:
                                        st.info(f"Synced to QuickBooks (QB #{qb_inv.get('DocNumber', '')})")
                        except Exception as qb_err:
                            st.caption(f"QB sync skipped: {qb_err}")

                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Failed to create invoice. Check logs.")


# ── TAB: AR Aging ───────────────────────────────────────────────────────────

with tab_aging:
    st.markdown("### Accounts Receivable Aging Report")
    st.caption("Outstanding balances broken down by how long they've been due.")

    try:
        aging = get_ar_aging()
    except Exception:
        st.error("Unable to load AR aging data.")
        aging = {}

    # Summary bar
    st.markdown(
        f"**Total Outstanding: ${aging.get('total_outstanding', 0):,.2f}** "
        f"across {aging.get('total_invoices', 0)} invoice(s)"
    )

    st.divider()

    # Aging buckets
    buckets = [
        ("Current (not yet due)", "current", "\U0001F7E2"),
        ("1-30 Days Past Due", "past_30", "\U0001F7E1"),
        ("31-60 Days Past Due", "past_60", "\U0001F7E0"),
        ("61-90 Days Past Due", "past_90", "\U0001F534"),
        ("90+ Days Past Due", "past_90_plus", "\U0001F6A8"),
    ]

    for label, key, emoji in buckets:
        bucket = aging.get(key, {})
        count = bucket.get("count", 0)
        total = bucket.get("total", 0)

        if count > 0:
            with st.expander(f"{emoji} **{label}** — {count} invoice(s) | ${total:,.2f}",
                             expanded=True):
                for inv in bucket.get("invoices", []):
                    client = get_client(inv.get("client_id", ""))
                    cname = client.get("business_name", "Unknown") if client else "Unknown"
                    st.markdown(
                        f"- **{inv.get('invoice_number', '')}** — {cname} | "
                        f"${float(inv.get('amount', 0)):,.2f} | Due: {inv.get('due_date', '')}"
                    )
        else:
            st.markdown(f"{emoji} **{label}** — No invoices")


# ── TAB: Batch Tools ────────────────────────────────────────────────────────

with tab_tools:
    st.markdown("### Batch Operations")

    st.markdown("#### Check for Overdue Invoices")
    st.caption("Scan all sent invoices and automatically mark past-due ones as overdue. Sends reminder emails.")

    if st.button("Run Overdue Check", type="primary", width='stretch',
                 key="run_overdue_check"):
        with st.spinner("Scanning invoices..."):
            count = check_and_mark_overdue()
            if count > 0:
                st.success(f"Marked {count} invoice(s) as overdue. Reminders sent.")
            else:
                st.info("No new overdue invoices found. All caught up.")

    st.divider()

    # ── Send Payment Reminders ────────────────────────────────────
    st.markdown("#### Send Payment Reminders")
    st.caption("Send email and SMS reminders to all clients with overdue invoices.")

    try:
        overdue_list = get_overdue_invoices()
        overdue_count = len(overdue_list)
    except Exception:
        overdue_list = []
        overdue_count = 0

    if overdue_count > 0:
        overdue_total = sum(
            float(i.get("amount", 0)) - float(i.get("amount_paid", 0))
            for i in overdue_list
        )
        st.markdown(
            f"**{overdue_count} overdue invoice(s)** totaling "
            f"**${overdue_total:,.2f}** in outstanding balances."
        )

        if st.button("Send Reminders to All Overdue", type="primary",
                     width='stretch', key="send_bulk_reminders"):
            with st.spinner(f"Sending reminders to {overdue_count} client(s)..."):
                results = send_bulk_reminders()
                if results["sent"] > 0:
                    st.success(
                        f"Sent {results['sent']} reminder(s) successfully. "
                        f"Failed: {results['failed']}"
                    )
                    for inv_num in results["invoices"]:
                        st.caption(f"  Reminder sent for {inv_num}")
                else:
                    st.warning("No reminders could be sent. Check SMTP configuration.")
    else:
        st.info("No overdue invoices found. All payments are current.")

    st.divider()

    st.markdown("#### Generate Monthly Invoices")
    st.caption(
        "Automatically create draft invoices for all active contracts. "
        "One invoice per contract for the current billing period."
    )

    if st.button("Generate Monthly Invoices", width='stretch',
                 key="gen_monthly"):
        with st.spinner("Generating invoices for active contracts..."):
            created = generate_monthly_invoices()
            if created:
                st.success(f"Created {len(created)} draft invoice(s). Review them in the All Invoices tab.")
                for inv in created:
                    st.caption(f"  {inv.get('invoice_number', '')} — ${float(inv.get('amount', 0)):,.2f}")
            else:
                st.info("No new invoices needed. All active contracts already invoiced for this period.")

    # ── QuickBooks Sync ──────────────────────────────────────────────
    st.divider()

    try:
        from services.quickbooks_service import (
            is_connected as qb_is_connected,
            sync_all_clients as qb_sync_all_clients,
            sync_unpaid_invoices as qb_sync_unpaid,
            sync_invoice_to_qb,
        )

        if qb_is_connected():
            st.markdown("#### QuickBooks Sync")
            st.caption("Sync invoices and payments with QuickBooks Online.")

            qb_col1, qb_col2 = st.columns(2)

            with qb_col1:
                st.markdown("**Sync Payments from QB**")
                st.caption(
                    "Check QuickBooks for payments on outstanding invoices and "
                    "auto-mark them as paid in the portal."
                )
                if st.button("\U0001F4B0 Sync Payments from QuickBooks",
                             type="primary", width='stretch',
                             key="batch_qb_payments"):
                    with st.spinner("Checking QuickBooks for payments..."):
                        result = qb_sync_unpaid()
                        if result.get("newly_paid", 0) > 0:
                            st.success(
                                f"Found {result['newly_paid']} new payment(s)! "
                                f"Checked {result['checked']} invoice(s)."
                            )
                        else:
                            st.info(
                                f"No new payments found. "
                                f"Checked {result.get('checked', 0)} invoice(s)."
                            )

            with qb_col2:
                st.markdown("**Push All Invoices to QB**")
                st.caption(
                    "Sync all unsent/sent invoices to QuickBooks. "
                    "Creates customers automatically if needed."
                )
                if st.button("\U0001F4E4 Push Invoices to QuickBooks",
                             width='stretch', key="batch_qb_push"):
                    with st.spinner("Syncing invoices to QuickBooks..."):
                        all_invs = get_all_invoices()
                        pushed = 0
                        failed = 0
                        for inv in all_invs:
                            if inv.get("status") in ("draft", "sent", "viewed", "overdue"):
                                client_data = get_client(inv.get("client_id", ""))
                                if client_data:
                                    try:
                                        qb_inv = sync_invoice_to_qb(inv, client_data)
                                        if qb_inv:
                                            pushed += 1
                                        else:
                                            failed += 1
                                    except Exception:
                                        failed += 1
                        st.success(f"Pushed {pushed} invoice(s) to QuickBooks. Failed: {failed}")

        else:
            st.markdown("#### QuickBooks")
            st.info(
                "QuickBooks is not connected. Go to **Settings** to connect "
                "your QuickBooks Online account for invoice and payment sync."
            )
            st.page_link("pages/3_Settings.py", label="Go to Settings", icon="\u2699\uFE0F")

    except ImportError:
        pass  # QB service not available, skip silently
