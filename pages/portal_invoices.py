"""Client portal invoices page — view invoices and payment status."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import require_portal_auth, get_portal_user, portal_logout
from services.portal_service import get_client_by_user_id
from services.supabase_client import query_table

st.set_page_config(
    page_title="Invoices - MCTV Client Portal",
    page_icon="\U0001F4B0",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1B1F3B; }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 { color: white; }
    [data-testid="stSidebar"] a, [data-testid="stSidebar"] a span,
    [data-testid="stSidebar"] a p,
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] span,
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p { color: white !important; }
    [data-testid="stSidebar"] a:hover span,
    [data-testid="stSidebar"] a:hover p { color: #C5A55A !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

require_portal_auth()
user = get_portal_user()

with st.sidebar:
    st.markdown("## MCTV Client Portal")
    st.markdown(f"*{user.get('full_name', '')}*")
    st.divider()
    st.markdown("**Navigation**")
    st.page_link("pages/portal_dashboard.py", label="Dashboard", icon="\U0001F3E0")
    st.page_link("pages/portal_contract.py", label="My Contract", icon="\U0001F4DD")
    st.page_link("pages/portal_invoices.py", label="Invoices", icon="\U0001F4B0")
    st.page_link("pages/portal_creative.py", label="Creative Requests", icon="\U0001F3A8")
    st.page_link("pages/portal_reports.py", label="Reports", icon="\U0001F4CA")
    st.page_link("pages/portal_profile.py", label="My Profile", icon="\U0001F464")
    st.divider()
    if st.button("Log Out", use_container_width=True):
        portal_logout()
        st.switch_page("pages/portal_login.py")
    st.caption("MCTV Elite Advertising")

# ── Load client ─────────────────────────────────────────────────────────────

client = get_client_by_user_id(user.get("user_id", ""))
if not client:
    st.warning("Your account is being set up. Please check back soon.")
    st.stop()

client_id = client.get("id", "")

st.markdown("## Invoices")
st.caption(f"{client.get('business_name', '')} | Payment History")
st.divider()

# ── Fetch invoices ──────────────────────────────────────────────────────────

invoices = query_table("invoices", filters={"client_id": client_id}, order="-issued_date")

if not invoices:
    st.info("No invoices yet. Your invoices will appear here once your contract is active.")
    st.stop()

# Summary
overdue = [i for i in invoices if i.get("status") == "overdue"]
pending = [i for i in invoices if i.get("status") in ("sent", "viewed")]
paid = [i for i in invoices if i.get("status") == "paid"]

m1, m2, m3 = st.columns(3)
m1.metric("Pending", len(pending))
m2.metric("Overdue", len(overdue))
m3.metric("Paid", len(paid))

st.divider()

for inv in invoices:
    inv_num = inv.get("invoice_number", "")
    amount = float(inv.get("amount", 0))
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
