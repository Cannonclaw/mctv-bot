# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Client portal invoices page — view invoices and payment status."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import require_portal_auth, get_portal_user
from services.supabase_client import query_table
from services.portal_ui import inject_portal_css, render_portal_sidebar, render_portal_footer, load_portal_client

st.set_page_config(
    page_title="Invoices - MCTV Client Portal",
    page_icon="\U0001F4B0",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_portal_css()
require_portal_auth()

user = get_portal_user()
render_portal_sidebar(user)
client = load_portal_client(user)

client_id = client.get("id", "")

st.markdown("## Invoices")
st.caption(f"{client.get('business_name', '')} | Payment History")
st.divider()

# ── Fetch invoices ──────────────────────────────────────────────────────────

try:
    invoices = query_table("invoices", filters={"client_id": client_id}, order="-issued_date")
except Exception:
    st.error("Unable to load your invoices. Please try again later.")
    invoices = []

if not invoices:
    st.info("No invoices yet. Your invoices will appear here once your contract is active.")
    render_portal_footer()
    st.stop()

# Summary
overdue = [i for i in invoices if i.get("status") == "overdue"]
pending = [i for i in invoices if i.get("status") in ("sent", "viewed")]
paid = [i for i in invoices if i.get("status") == "paid"]
def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

total_owed = sum(_safe_float(i.get("amount", 0)) for i in overdue + pending)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Pending", len(pending))
m2.metric("Overdue", len(overdue))
m3.metric("Paid", len(paid))
m4.metric("Total Owed", f"${total_owed:,.2f}")

st.divider()

for inv in invoices:
    inv_num = inv.get("invoice_number", "")
    amount = _safe_float(inv.get("amount", 0))
    status = inv.get("status", "draft")
    due_date = inv.get("due_date", "")
    issued = inv.get("issued_date", "")
    paid_date = inv.get("paid_date", "")

    status_emoji = {
        "draft": "\u270F\uFE0F",
        "sent": "\U0001F4E8",
        "viewed": "\U0001F440",
        "overdue": "\U0001F534",
        "paid": "\u2705",
        "void": "\u26D4",
    }.get(status, "\u26AA")

    with st.expander(
        f"{status_emoji} **Invoice {inv_num}** — ${amount:,.2f} | "
        f"Due: {due_date} | {status.title()}",
        expanded=(status in ("overdue", "sent")),
    ):
        ic1, ic2 = st.columns(2)
        with ic1:
            st.text(f"Invoice #: {inv_num}")
            st.text(f"Amount: ${amount:,.2f}")
            st.text(f"Description: {inv.get('description', 'Monthly advertising')}")
        with ic2:
            st.text(f"Issued: {issued}")
            st.text(f"Due: {due_date}")
            st.text(f"Status: {status.title()}")
            if paid_date:
                st.text(f"Paid: {paid_date}")

        if inv.get("notes"):
            st.caption(f"Notes: {inv.get('notes')}")

        if status == "overdue":
            st.warning("This invoice is past due. Please contact your MCTV representative to arrange payment.")

render_portal_footer()
