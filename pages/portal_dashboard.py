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
from services.portal_service import (
    get_client_by_user_id, get_client_dashboard, get_host_dashboard,
)
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

_data_load_error = False

try:
    client = get_client_by_user_id(user.get("user_id", ""))
except Exception as e:
    print(f"[portal_dashboard] Failed to load client: {e}")
    client = None
    _data_load_error = True

if not client and not is_admin:
    if _data_load_error:
        st.error("We're having trouble loading your account. Please try refreshing the page.")
    else:
        st.warning("Your account is being set up. Please check back soon or contact your MCTV representative.")
    render_portal_footer()
    st.stop()

client_id = client.get("id", "") if client else ""
client_type = client.get("client_type", "advertiser") if client else "advertiser"

# Fetch the appropriate dashboard data
try:
    if client_type == "host":
        dashboard = get_host_dashboard(client_id) if client_id else {}
    else:
        dashboard = get_client_dashboard(client_id) if client_id else {}
except Exception as e:
    print(f"[portal_dashboard] Failed to load dashboard data: {e}")
    dashboard = {}
    _data_load_error = True

if _data_load_error and dashboard == {}:
    st.warning("Some data could not be loaded. You may see incomplete information below.")

bname = client.get("business_name", "MCTV Admin") if client else "MCTV Admin"
cstatus = client.get("status", "active") if client else "active"


# ── Header ──────────────────────────────────────────────────────────────────

st.markdown(f"## Welcome, {user.get('full_name', 'there')}")

if client_type == "host":
    venue_city = dashboard.get("venue_city", "")
    subtitle = f"{bname} | Venue Host" + (f" | {venue_city}" if venue_city else "")
    st.caption(subtitle)
else:
    st.caption(f"{bname} | {role.title()} Portal")

st.divider()


# ==========================================================================
# ADVERTISER DASHBOARD
# ==========================================================================

def _render_advertiser_dashboard(dash: dict, status: str):
    """Full advertiser dashboard: metrics, quick actions, recent activity."""

    # ── Summary Metrics ────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Contracts", dash.get("active_contract_count", 0))
    m2.metric("Total Screens", dash.get("total_screens", 0))
    m3.metric("Pending Invoices", dash.get("pending_invoice_count", 0))

    next_inv = dash.get("next_invoice")
    if next_inv:
        m4.metric("Next Due", f"${float(next_inv.get('amount', 0)):,.2f}",
                   delta=next_inv.get("due_date", ""), delta_color="off")
    else:
        m4.metric("Next Due", "None")

    st.divider()

    # ── Quick Actions ──────────────────────────────────────────────────────
    st.markdown("### Quick Actions")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("#### Contract")
        contracts = dash.get("contracts", [])
        unsigned = [c for c in contracts if c.get("status") in ("sent", "viewed")]
        if unsigned:
            st.warning(f"{len(unsigned)} contract(s) awaiting your signature")
            if st.button("Review & Sign", type="primary", width='stretch',
                         key="adv_dash_contract"):
                st.switch_page("pages/portal_contract.py")
        elif contracts:
            active = [c for c in contracts if c.get("status") in ("signed", "active")]
            if active:
                st.success(f"{len(active)} active contract(s)")
            if st.button("View Contract", type="primary", width='stretch',
                         key="adv_dash_view_contract"):
                st.switch_page("pages/portal_contract.py")
        else:
            st.info("No contracts yet")

    with col2:
        st.markdown("#### Invoices")
        invoices = dash.get("invoices", [])
        overdue = [i for i in invoices if i.get("status") == "overdue"]
        pending = [i for i in invoices if i.get("status") in ("sent", "viewed")]
        if overdue:
            st.error(f"{len(overdue)} overdue invoice(s)")
        elif pending:
            st.info(f"{len(pending)} pending invoice(s)")
        else:
            st.success("All caught up")
        if st.button("View Invoices", type="primary", width='stretch',
                     key="adv_dash_invoices"):
            st.switch_page("pages/portal_invoices.py")

    with col3:
        st.markdown("#### Creative")
        creatives = dash.get("creative_requests", [])
        in_progress = [r for r in creatives if r.get("status") in ("pending", "in_progress")]
        if in_progress:
            st.info(f"{len(in_progress)} request(s) in progress")
        else:
            st.caption("No active requests")
        if st.button("Submit Request", type="primary", width='stretch',
                     key="adv_dash_creative"):
            st.switch_page("pages/portal_creative.py")

    with col4:
        st.markdown("#### Reports")
        reports = dash.get("reports", [])
        if reports:
            latest = reports[0]
            st.success(f"Latest: {latest.get('title', 'Report')[:25]}")
        else:
            st.caption("No reports yet")
        if st.button("View Reports", type="primary", width='stretch',
                     key="adv_dash_reports"):
            st.switch_page("pages/portal_reports.py")

    # ── Recent Activity ────────────────────────────────────────────────────
    _render_recent_activity(dash)

    # ── Onboarding Banner ──────────────────────────────────────────────────
    if status == "onboarding":
        st.divider()
        st.info(
            "Your account is being set up. Your MCTV representative will be in touch "
            "with your contract details and next steps. In the meantime, feel free to "
            "explore the portal and submit any creative materials you'd like us to work with."
        )


# ==========================================================================
# HOST DASHBOARD
# ==========================================================================

def _render_host_dashboard(dash: dict, status: str):
    """Full host/venue dashboard: screens, free ads, activity, revenue share."""

    venue_name = dash.get("venue_name", "Your Venue")

    # ── Summary Metrics ────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Screens at Venue", dash.get("screens_at_venue", 0))
    m2.metric("Free Plays / Month", f"{dash.get('free_plays_per_month', 0):,}")
    m3.metric("Active Contracts", dash.get("active_contract_count", 0))

    rev_share = dash.get("revenue_share_amount", 0)
    if rev_share > 0:
        m4.metric("Revenue Share", f"${rev_share:,.2f}/mo")
    else:
        m4.metric("Status", status.title())

    st.divider()

    # ── Screen Status ──────────────────────────────────────────────────────
    st.markdown("### Screen Status")

    screens = dash.get("screens_at_venue", 0)
    contracts = dash.get("contracts", [])
    active_contracts = [c for c in contracts if c.get("status") in ("signed", "active")]

    if screens > 0:
        sc1, sc2 = st.columns(2)
        with sc1:
            st.success(f"{screens} screen(s) installed at {venue_name}")
            markets = set()
            for c in active_contracts:
                for mkt in (c.get("markets") or []):
                    markets.add(mkt)
            if markets:
                st.caption(f"Market(s): {', '.join(sorted(markets))}")
        with sc2:
            loop_min = dash.get("loop_minutes", 15)
            st.info(
                f"Each screen runs a **{loop_min}-minute content loop**, "
                f"rotating ads throughout the day."
            )
    else:
        st.info(
            "Screen installation is being scheduled. Your MCTV representative "
            "will coordinate the setup at your venue."
        )

    st.divider()

    # ── Free Advertising Summary ───────────────────────────────────────────
    st.markdown("### Your Free Advertising")
    st.caption(
        "As an MCTV host venue, you receive complimentary advertising "
        "on the screens at your location."
    )

    fa1, fa2, fa3 = st.columns(3)
    fa1.metric("Plays Per Hour", dash.get("free_plays_per_hour", 0))
    fa2.metric("Plays Per Day", f"{dash.get('free_plays_per_day', 0):,}")
    fa3.metric("Plays Per Month", f"{dash.get('free_plays_per_month', 0):,}")

    with st.expander("How to submit your content"):
        st.markdown(
            "**Submit your ads, logos, and promotional content through the Creative Requests page.** "
            "Our team will format your content for the screens and get it into rotation. "
            "You can update your content anytime."
        )
        if st.button("Submit Creative Request", type="primary", key="host_submit_creative"):
            st.switch_page("pages/portal_creative.py")

    st.divider()

    # ── Revenue Share ──────────────────────────────────────────────────────
    rev_share = dash.get("revenue_share_amount", 0)
    rev_contract = dash.get("revenue_share_contract")

    if rev_share > 0 and rev_contract:
        st.markdown("### Revenue Share")

        rev_contracts = dash.get("revenue_share_contracts", [])

        rs1, rs2, rs3 = st.columns(3)
        rs1.metric("Monthly Total", f"${rev_share:,.2f}")
        rs2.metric("Active Agreements", len(rev_contracts))

        end_date = rev_contract.get("end_date", "")
        rs3.metric("Renews / Ends", end_date if end_date else "Auto-Renew")

        # Show per-contract breakdown if multiple
        if len(rev_contracts) > 1:
            with st.expander("Revenue breakdown by contract"):
                for rc in rev_contracts:
                    rate = float(rc.get("monthly_rate", 0) or 0)
                    ctype = rc.get("contract_type", "host").replace("_", " ").title()
                    term = rc.get("term_months", 0)
                    st.markdown(f"- **{ctype}** — ${rate:,.2f}/mo ({term}-month term)")

        if st.button("View Contract Details", type="primary", key="host_view_rev_contract"):
            st.switch_page("pages/portal_contract.py")

        st.divider()

    # ── Advertiser Activity at Venue ───────────────────────────────────────
    st.markdown("### Advertiser Activity")

    invoices = dash.get("invoices", [])
    creative_reqs = dash.get("creative_requests", [])
    reports = dash.get("reports", [])

    aa1, aa2, aa3 = st.columns(3)
    aa1.metric("Contracts", len(contracts))
    aa2.metric("Creative Requests", len(creative_reqs))
    aa3.metric("Reports Available", len(reports))

    if reports:
        latest_report = reports[0]
        st.caption(f"Latest report: {latest_report.get('title', 'Venue Report')}")
        if st.button("View Reports", type="primary", key="host_view_reports"):
            st.switch_page("pages/portal_reports.py")

    st.divider()

    # ── Quick Actions ──────────────────────────────────────────────────────
    st.markdown("### Quick Actions")

    qa1, qa2, qa3 = st.columns(3)

    with qa1:
        st.markdown("#### Creative")
        in_progress = [r for r in creative_reqs
                       if r.get("status") in ("pending", "in_progress")]
        if in_progress:
            st.info(f"{len(in_progress)} request(s) in progress")
        else:
            st.caption("No active requests")
        if st.button("Submit Request", type="primary", width='stretch',
                     key="host_dash_creative"):
            st.switch_page("pages/portal_creative.py")

    with qa2:
        st.markdown("#### Reports")
        if reports:
            st.success(f"{len(reports)} report(s) available")
        else:
            st.caption("No reports yet")
        if st.button("View Reports", type="primary", width='stretch',
                     key="host_dash_reports"):
            st.switch_page("pages/portal_reports.py")

    with qa3:
        st.markdown("#### Profile")
        st.caption("Update your venue details")
        if st.button("Update Profile", type="primary", width='stretch',
                     key="host_dash_profile"):
            st.switch_page("pages/portal_profile.py")

    # ── Recent Activity ────────────────────────────────────────────────────
    _render_recent_activity(dash)

    # ── Onboarding Banner ──────────────────────────────────────────────────
    if status == "onboarding":
        st.divider()
        st.info(
            "Welcome to the MCTV network! Your screens are being set up. "
            "Your MCTV representative will coordinate installation and get "
            "your free advertising content into rotation. In the meantime, "
            "feel free to submit your creative materials through the portal."
        )


# ==========================================================================
# SHARED: Recent Activity
# ==========================================================================

def _render_recent_activity(dash: dict):
    """Render the recent activity feed (shared by both dashboard types)."""
    st.divider()
    st.markdown("### Recent Activity")

    activity = dash.get("activity", [])

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

            st.markdown(f"{icon} **{action}** -- {timestamp}")
    else:
        st.info("No recent activity. Your activity will appear here as you use the portal.")


# ==========================================================================
# RENDER — dispatch to the correct dashboard
# ==========================================================================

if client_type == "host":
    _render_host_dashboard(dashboard, cstatus)
else:
    _render_advertiser_dashboard(dashboard, cstatus)

render_portal_footer()
