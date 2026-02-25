# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Client portal dashboard — personalized view for advertisers and hosts."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import (
    require_portal_auth, get_portal_user, get_portal_role,
    is_portal_advertiser, is_portal_host,
)
from services.portal_service import get_client_by_user_id, get_client_dashboard
from services.portal_ui import inject_portal_css, render_portal_sidebar, render_portal_footer

st.set_page_config(
    page_title="Dashboard - MCTV Client Portal",
    page_icon="\U0001F4FA",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_portal_css()
require_portal_auth()

user = get_portal_user()
role = get_portal_role()

render_portal_sidebar(user)


# ── Load Dashboard Data ────────────────────────────────────────────────────

is_admin = role in ("admin", "sales_rep")

try:
    client = get_client_by_user_id(user.get("user_id", ""))
except Exception:
    client = None

if not client and not is_admin:
    st.warning("Your account is being set up. Please check back soon or contact your MCTV representative.")
    render_portal_footer()
    st.stop()

client_id = client.get("id", "") if client else ""

try:
    dashboard = get_client_dashboard(client_id) if client_id else {}
except Exception:
    dashboard = {}

bname = client.get("business_name", "MCTV Admin") if client else "MCTV Admin"
cstatus = client.get("status", "active") if client else "active"


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
        if st.button("View Contract", type="primary", use_container_width=True,
                     key="dash_view_contract"):
            st.switch_page("pages/portal_contract.py")
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
    if st.button("View Invoices", type="primary", use_container_width=True, key="dash_invoices"):
        st.switch_page("pages/portal_invoices.py")

with col3:
    st.markdown("#### Creative")
    creatives = dashboard.get("creative_requests", [])
    in_progress = [r for r in creatives if r.get("status") in ("pending", "in_progress")]
    if in_progress:
        st.info(f"{len(in_progress)} request(s) in progress")
    else:
        st.caption("No active requests")
    if st.button("Submit Request", type="primary", use_container_width=True, key="dash_creative"):
        st.switch_page("pages/portal_creative.py")

with col4:
    st.markdown("#### Reports")
    reports = dashboard.get("reports", [])
    if reports:
        latest = reports[0]
        st.success(f"Latest: {latest.get('title', 'Report')[:25]}")
    else:
        st.caption("No reports yet")
    if st.button("View Reports", type="primary", use_container_width=True, key="dash_reports"):
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

render_portal_footer()
