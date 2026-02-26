# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Shared UI components for the MCTV Client Portal.

Centralizes CSS, sidebar navigation, and footer so every portal page
stays consistent without duplicating 50+ lines of boilerplate.
"""

import streamlit as st
from services.auth import portal_logout
from services.config_service import load_config


# ── Portal CSS ──────────────────────────────────────────────────────────────

PORTAL_CSS = """
<style>
    :root { --navy: #1B1F3B; --gold: #C5A55A; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #1B1F3B; }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 { color: white; }
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] a span,
    [data-testid="stSidebar"] a p,
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] span,
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p { color: white !important; }
    [data-testid="stSidebar"] a:hover span,
    [data-testid="stSidebar"] a:hover p { color: #C5A55A !important; }

    /* Hide default chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""


def inject_portal_css():
    """Inject the portal-wide CSS. Call once at the top of each portal page."""
    st.markdown(PORTAL_CSS, unsafe_allow_html=True)


# ── Portal Sidebar ──────────────────────────────────────────────────────────

def render_portal_sidebar(user: dict):
    """Render the standard portal sidebar with nav links and logout.

    Args:
        user: Dict from get_portal_user() with full_name, email, etc.
    """
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

        if st.button("Log Out", width='stretch'):
            portal_logout()
            st.switch_page("pages/portal_login.py")

        config = load_config()
        company = config.get("company", {})
        st.caption(company.get("name", "MCTV Elite Advertising"))
        st.caption(company.get("website", "www.mctvofms.com"))
        st.page_link("pages/portal_terms.py", label="Terms of Service", icon="\U0001F4CB")


# ── Portal Footer ───────────────────────────────────────────────────────────

def render_portal_footer():
    """Render a consistent footer at the bottom of portal pages."""
    config = load_config()
    company = config.get("company", {})
    markets = config.get("markets", {})

    company_name = company.get("name", "MCTV Elite Advertising")
    legal_name = company.get("legal_name", "MCTV Digital")

    # Build market list from active markets in config
    active_markets = [
        name for name, info in markets.items()
        if info.get("status") == "active"
    ]
    market_str = " | ".join(active_markets) if active_markets else "Oxford | Starkville | Tupelo"

    st.divider()
    st.markdown(
        f"""
        <div style="text-align: center; color: #888; font-size: 0.8rem; padding: 0.5rem 0;">
            <p>{company_name} | {market_str}</p>
            <p>&copy; 2026 {legal_name}, Inc. All rights reserved.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Client Load Helper ─────────────────────────────────────────────────────

def load_portal_client(user: dict):
    """Load the client record for the current portal user.

    Returns the client dict, or calls st.stop() if the client isn't set up yet.
    """
    from services.portal_service import get_client_by_user_id

    try:
        client = get_client_by_user_id(user.get("user_id", ""))
    except Exception:
        st.error("Unable to load your account. Please try again later or contact MCTV support.")
        st.stop()
        return None  # unreachable but keeps type checkers happy

    if not client:
        st.warning("Your account is being set up. Please check back soon or contact your MCTV representative.")
        st.stop()
        return None

    return client
