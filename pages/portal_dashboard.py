"""Client portal dashboard — personalized view for advertisers and hosts."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import (
    require_portal_auth, get_portal_user, get_portal_role,
    is_portal_advertiser, is_portal_host, portal_logout,
)
from services.portal_service import get_client_by_user_id, get_client_dashboard

st.set_page_config(
    page_title="Dashboard - MCTV Client Portal",
    page_icon="\U0001F4FA",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Portal CSS ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
    :root { --navy: #1B1F3B; --gold: #C5A55A; }

    [data-testid="stSidebar"] {
        background-color: #1B1F3B;
    }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: white;
    }
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] a span,
    [data-testid="stSidebar"] a p,
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] span,
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {
        color: white !important;
    }
    [data-testid="stSidebar"] a:hover span,
    [data-testid="stSidebar"] a:hover p {
        color: #C5A55A !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ── Auth Gate ───────────────────────────────────────────────────────────────

require_portal_auth()
user = get_portal_user()
role = get_portal_role()


# ── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## MCTV Client Portal")
    st.markdown(f"*Welcome, {user.get('full_name', 'there')}*")
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
    st.caption("www.mctvofms.com")


# ── Load Dashboard Data ────────────────────────────────────────────────────

client = get_client_by_user_id(user.get("user_id", ""))

if not client:
    st.warning("Your account is being set up. Please check back soon or contact your MCTV representative.")
    st.stop()

client_id = client.get("id", "")
dashboard = get_client_dashboard(client_id)

bname = client.get("business_name", "Your Business")
cstatus = client.get("status", "onboarding")


# ── Header ──────────────────────────────────────────────────────────────────

st.markdown(f"## Welcome, {user.get('full_name', 'there')}")
st.caption(f"{bname} | {role.title()} Portal")

st.divider()


# ── Summary Metrics ─────────────────────────────────────────────────────────

if is_portal_advertiser():
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Contracts", dashboard.get("active_contract_count", 0))
    m2.metric("Total Screens", dashboard.get("total_screens", 0))
    m3.metric("Pending Invoices", dashboard.get("pending_invoice_count", 0))

    # Next invoice info
    next_inv = dashboard.get("next_invoice")
    if next_inv:
        m4.metric("Next Due", f"${float(next_inv.get('amount', 0)):,.2f}",
                   delta=next_inv.get("due_date", ""), delta_color="off")
    else:
        m4.metric("Next Due", "None")

elif is_portal_host():
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Screens Hosted", dashboard.get("total_screens", 0))
    m2.metric("Active Contracts", dashboard.get("active_contract_count", 0))
    m3.metric("Status", cstatus.title())
    m4.metric("Creative Requests", len(dashboard.get("creative_requests", [])))


st.divider()


# ── Quick Action Cards ──────────────────────────────────────────────────────

st.markdown("### Quick Actions")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("#### Contract")
    contracts = dashboard.get("contracts", [])
    unsigned = [c for c in contracts if c.get("status") in ("sent", "viewed")]
    if unsigned:
        st.warning(f"{len(unsigned)} contract(s) awaiting your signature")
        if st.button("Review & Sign", type="primary", use_container_width=True,
                     key="dash_contract"):
            st.switch_page("pages/portal_contract.py")
    elif contracts:
        active = [c for c in contracts if c.get("status") in ("signed", "active")]
        if active:
            st.success(f"{len(active)} active contract(s)")
        st.button("View Contract", use_container_width=True, key="dash_view_contract",
                  on_click=lambda: st.switch_page("pages/portal_contract.py"))
    else:
        st.info("No contracts yet")

with col2:
    st.markdown("#### Invoices")
    invoices = dashboard.get("invoices", [])
    overdue = [i for i in invoices if i.get("status") == "overdue"]
    pending = [i for i in invoices if i.get("status") in ("sent", "viewed")]
    if overdue:
        st.error(f"{len(overdue)} overdue invoice(s)")
    elif pending:
        st.info(f"{len(pending)} pending invoice(s)")
    else:
        st.success("All caught up")
    if st.button("View Invoices", use_container_width=True, key="dash_invoices"):
        st.switch_page("pages/portal_invoices.py")

with col3:
    st.markdown("#### Creative")
    creatives = dashboard.get("creative_requests", [])
    in_progress = [r for r in creatives if r.get("status") in ("pending", "in_progress")]
    if in_progress:
        st.info(f"{len(in_progress)} request(s) in progress")
    else:
        st.caption("No active requests")
    if st.button("Submit Request", use_container_width=True, key="dash_creative"):
        st.switch_page("pages/portal_creative.py")

with col4:
    st.markdown("#### Reports")
    reports = dashboard.get("reports", [])
    if reports:
        latest = reports[0]
        st.success(f"Latest: {latest.get('title', 'Report')[:25]}")
    else:
        st.caption("No reports yet")
    if st.button("View Reports", use_container_width=True, key="dash_reports"):
        st.switch_page("pages/portal_reports.py")


# ── Recent Activity ─────────────────────────────────────────────────────────

st.divider()
st.markdown("### Recent Activity")

activity = dashboard.get("activity", [])

if activity:
    for event in activity[:10]:
        action = event.get("action", "")
        timestamp = event.get("created_at", "")[:16] if event.get("created_at") else ""
        entity = event.get("entity_type", "")

        # Icon based on entity type
        icon = {
            "contract": "\U0001F4DD",
            "invoice": "\U0001F4B0",
            "creative_request": "\U0001F3A8",
            "client_report": "\U0001F4CA",
            "client": "\U0001F465",
        }.get(entity, "\U0001F4AC")

        st.markdown(f"{icon} **{action}** — {timestamp}")
else:
    st.info("No recent activity. Your activity will appear here as you use the portal.")


# ── Account Status Banner ──────────────────────────────────────────────────

if cstatus == "onboarding":
    st.divider()
    st.info(
        "Your account is being set up. Your MCTV representative will be in touch "
        "with your contract details and next steps. In the meantime, feel free to "
        "explore the portal and submit any creative materials you'd like us to work with."
    )
