# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""MCTV Elite Advertising Bot - Main Streamlit Application.

Single entry point with a unified landing page offering three login paths:
1. Team Member — shared password for internal tools
2. Host Venue — Supabase email/password or magic link for venue partners
3. Advertiser — Supabase email/password or magic link for advertisers
"""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(Path(__file__).parent / ".env", override=True)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Page config must be the first Streamlit command
st.set_page_config(
    page_title="MCTV Elite Advertising Bot",
    page_icon="\U0001F4FA",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for MCTV branding
st.markdown("""
<style>
    /* MCTV Brand Colors */
    :root {
        --navy: #1B1F3B;
        --gold: #C5A55A;
    }

    /* Header styling */
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1B1F3B;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #C5A55A;
        margin-top: 0;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1B1F3B;
    }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: white;
    }
    /* Page link labels in sidebar */
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

    /* Success message styling */
    .stSuccess {
        background-color: #d4edda;
    }

    /* Hide default Streamlit menu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ── Imports ─────────────────────────────────────────────────────────────────

from services.auth import (
    check_team_auth, render_team_login_form, team_logout,
    check_portal_auth, check_password,
    portal_magic_link_callback, render_portal_login_form,
)

LOGO_PATH = Path(__file__).parent / "assets" / "branding" / "mctv_logo.png"


# ── Landing Page (unauthenticated) ──────────────────────────────────────────

LANDING_CSS = """
<style>
    .block-container { max-width: 900px; margin: 0 auto; }
    [data-testid="stSidebar"] { display: none !important; }
</style>
"""

CARD_TEMPLATE = """
<div style="background:#1B1F3B; border-radius:12px; padding:1.8rem 1.2rem;
            text-align:center; min-height:200px; display:flex; flex-direction:column;
            justify-content:center; align-items:center;">
    <p style="font-size:2.2rem; margin:0; line-height:1;">{icon}</p>
    <h3 style="color:white; margin:0.6rem 0 0.3rem; font-size:1.25rem;">{title}</h3>
    <p style="color:#C5A55A; font-size:0.88rem; margin:0; line-height:1.4;">{desc}</p>
</div>
"""


def _render_logo():
    """Render the centered MCTV logo."""
    if LOGO_PATH.exists():
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.image(str(LOGO_PATH), width='stretch')

    st.markdown(
        '<div style="text-align:center; padding:0 0 1rem;">'
        '<p style="color:#C5A55A; font-size:1.1rem; margin:0;">Indoor Digital Billboard Network</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_login_cards():
    """Render the 3 login option cards."""
    _render_logo()

    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        st.markdown(CARD_TEMPLATE.format(
            icon="\U0001F527", title="Team Member",
            desc="Internal tools, proposals,<br>reports &amp; client management"
        ), unsafe_allow_html=True)
        if st.button("Team Login", type="primary", width='stretch', key="btn_team"):
            st.session_state["login_mode"] = "team"
            st.rerun()

    with col2:
        st.markdown(CARD_TEMPLATE.format(
            icon="\U0001F3E2", title="Host Venue",
            desc="Manage your screens,<br>view reports &amp; submit content"
        ), unsafe_allow_html=True)
        if st.button("Host Login", type="primary", width='stretch', key="btn_host"):
            st.session_state["login_mode"] = "portal_host"
            st.rerun()

    with col3:
        st.markdown(CARD_TEMPLATE.format(
            icon="\U0001F4CA", title="Advertiser",
            desc="View your campaigns,<br>contracts &amp; invoices"
        ), unsafe_allow_html=True)
        if st.button("Advertiser Login", type="primary", width='stretch', key="btn_adv"):
            st.session_state["login_mode"] = "portal_advertiser"
            st.rerun()

    # Footer
    st.markdown(
        '<div style="text-align:center; color:#888; font-size:0.85rem; padding:2rem 0 0;">'
        '<p>MCTV Elite Advertising | Oxford | Starkville | Tupelo</p>'
        '<p>www.mctvofms.com | &copy; 2026 MCTV Digital, Inc.</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_team_login():
    """Render the team password login with a back button."""
    _render_logo()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        render_team_login_form()

        st.divider()
        if st.button("\u2190 Back to Login Options", width='stretch', key="back_team"):
            st.session_state["login_mode"] = None
            st.rerun()


def _render_portal_login(mode: str):
    """Render the Supabase portal login form with role-appropriate context."""
    is_host = mode == "portal_host"

    _render_logo()

    title = "Host Venue Login" if is_host else "Advertiser Login"
    subtitle = ("Manage your screens, content & reports" if is_host
                else "View your contracts, invoices & campaign performance")

    st.markdown(
        f'<div style="text-align:center; padding:0 0 0.5rem;">'
        f'<h2 style="color:#1B1F3B; margin:0;">{title}</h2>'
        f'<p style="color:#C5A55A; margin:0.3rem 0 0;">{subtitle}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        render_portal_login_form(context_title=title, context_subtitle=subtitle)

        st.divider()
        if st.button("\u2190 Back to Login Options", width='stretch', key="back_portal"):
            st.session_state["login_mode"] = None
            st.session_state.pop("show_reset_form", None)
            st.session_state.pop("use_magic_link", None)
            st.rerun()


def render_landing_page():
    """Render the unified landing page with 3 login options."""
    st.markdown(LANDING_CSS, unsafe_allow_html=True)

    # Handle magic link / recovery callbacks (redirected from portal_login.py)
    _token_hash = st.query_params.get("token_hash", "")
    _auth_type = st.query_params.get("type", "")

    if _token_hash and _auth_type in ("magiclink", "recovery"):
        st.query_params.clear()

        if _auth_type == "recovery":
            with st.spinner("Verifying reset link..."):
                result = portal_magic_link_callback(_token_hash, otp_type="recovery")
            if result:
                st.session_state["_recovery_mode"] = True
                st.session_state["_recovery_access_token"] = result.get("access_token", "")
                st.session_state["login_mode"] = "portal_advertiser"
                st.rerun()
            else:
                st.error("This reset link has expired or is invalid. Please request a new one.")
                st.stop()
        else:
            with st.spinner("Signing you in..."):
                result = portal_magic_link_callback(_token_hash, otp_type="magiclink")
            if result:
                st.success(f"Welcome, {result.get('full_name', 'there')}!")
                st.switch_page("pages/portal_dashboard.py")
            else:
                st.error("This magic link has expired or your email is not authorized.")
                st.stop()

    # Dispatch based on login_mode
    login_mode = st.session_state.get("login_mode")

    if login_mode == "team":
        _render_team_login()
    elif login_mode in ("portal_host", "portal_advertiser"):
        _render_portal_login(login_mode)
    else:
        _render_login_cards()


# ── Team Dashboard (authenticated) ─────────────────────────────────────────

def main():
    # Sidebar
    with st.sidebar:
        st.markdown("## MCTV ELITE ADVERTISING")
        st.markdown("*Indoor Digital Billboard Network*")
        st.divider()

        # API Key status
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if api_key and api_key != "your-api-key-here":
            st.success("Claude API: Connected")
        else:
            st.warning("Claude API: Not configured")
            st.caption("Set your key in Settings or .env file")

        creatomate_key = os.environ.get("CREATOMATE_API_KEY", "")
        if creatomate_key:
            st.success("Video API: Connected")
        else:
            st.caption("Video API: Not configured")

        st.divider()
        st.markdown("**Navigation**")
        st.page_link("app.py", label="Home", icon="\U0001F3E0")
        st.page_link("pages/1_Proposals.py", label="Proposal Generator", icon="\U0001F4DD")
        st.page_link("pages/2_Reports.py", label="Traction Reports", icon="\U0001F4CA")
        st.page_link("pages/5_Video_Ads.py", label="Video Ads", icon="\U0001F3AC")
        st.page_link("pages/7_Research.py", label="Prospect Research", icon="\U0001F50D")
        st.page_link("pages/4_Leads.py", label="Incoming Leads", icon="\U0001F4CB")
        st.page_link("pages/8_Clients.py", label="Client Management", icon="\U0001F465")
        st.page_link("pages/9_Contracts.py", label="Contracts", icon="\U0001F4DD")
        st.page_link("pages/10_Invoices.py", label="Invoices", icon="\U0001F4B0")
        st.page_link("pages/11_Creative.py", label="Creative Requests", icon="\U0001F3A8")
        st.page_link("pages/12_Messaging.py", label="SMS Messaging", icon="\U0001F4F1")
        st.page_link("pages/3_Settings.py", label="Settings", icon="\u2699\uFE0F")

        st.divider()
        st.page_link("pages/portal_login.py", label="Client Portal", icon="\U0001F310")

        st.divider()
        if st.button("Log Out", width='stretch', key="team_logout_btn"):
            team_logout()
            st.rerun()

        st.caption("MCTV Elite Advertising")
        st.caption("Oxford | Starkville | Tupelo")
        st.caption("www.mctvofms.com")
        st.caption("\u00A9 2026 MCTV Digital, Inc.")

    # Main content - Home page
    st.markdown('<p class="main-header">MCTV Elite Advertising Bot</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Generate proposals and traction reports in seconds</p>', unsafe_allow_html=True)

    st.divider()

    # Feature cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("### Proposals")
        st.markdown(
            "Create polished advertising proposals tailored to each client. "
            "6 types including Elite Advertiser, Host Media Kit, and more."
        )
        if st.button("Create Proposal", type="primary", width='stretch'):
            st.switch_page("pages/1_Proposals.py")

    with col2:
        st.markdown("### Prospect Research")
        st.markdown(
            "Research a prospect before your sales call. Get competitive intel, "
            "talking points, and objection responses in seconds."
        )
        if st.button("Research Prospect", type="primary", width='stretch'):
            st.switch_page("pages/7_Research.py")

    with col3:
        st.markdown("### Traction Reports")
        st.markdown(
            "Generate professional traction and ad performance reports "
            "from NTV360 data. Upload Excel exports or enter data manually."
        )
        if st.button("Create Report", type="primary", width='stretch'):
            st.switch_page("pages/2_Reports.py")

    with col4:
        st.markdown("### Video Ads")
        st.markdown(
            "Create professional video advertisements using AI-powered templates. "
            "Upload assets and generate broadcast-ready content."
        )
        if st.button("Create Video", type="primary", width='stretch'):
            st.switch_page("pages/5_Video_Ads.py")

    # Second row of feature cards
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.markdown("### Client Management")
        st.markdown(
            "Manage client accounts, invite them to the portal, "
            "track status, and assign reps."
        )
        if st.button("Manage Clients", type="primary", width='stretch'):
            st.switch_page("pages/8_Clients.py")

    with col6:
        st.markdown("### Contracts")
        st.markdown(
            "Create branded contracts, generate PDFs, send for "
            "e-signature, and track the full lifecycle."
        )
        if st.button("View Contracts", type="primary", width='stretch'):
            st.switch_page("pages/9_Contracts.py")

    with col7:
        st.markdown("### Invoices")
        st.markdown(
            "Create and send invoices, track payments, run AR aging "
            "reports, and sync with QuickBooks."
        )
        if st.button("View Invoices", type="primary", width='stretch'):
            st.switch_page("pages/10_Invoices.py")

    with col8:
        st.markdown("### SMS Messaging")
        st.markdown(
            "Send text messages to clients via Twilio. Use templates, "
            "manage opt-ins, and view message history."
        )
        if st.button("Send Messages", type="primary", width='stretch'):
            st.switch_page("pages/12_Messaging.py")

    st.divider()

    # Quick stats
    st.markdown("### Network Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Screens", "125+")
    c2.metric("Monthly Impressions", "1.9M+")
    c3.metric("Avg Dwell Time", "55+ min")
    c4.metric("Markets", "3 Active")

    # Recent output files
    st.markdown("### Recent Output")
    output_dir = Path(__file__).parent / "output"
    recent_files = []
    for subdir in ["proposals", "reports", "contracts", "emails", "videos", "research"]:
        folder = output_dir / subdir
        if folder.exists():
            for f in sorted(folder.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                # Skip hidden/dot files like .gitkeep
                if f.name.startswith("."):
                    continue
                recent_files.append((f.name, subdir, f))

    if recent_files:
        for fname, category, fpath in recent_files[:10]:
            col_a, col_b, col_c = st.columns([3, 1, 1])
            col_a.text(fname)
            col_b.caption(category)
            with open(fpath, "rb") as f:
                col_c.download_button(
                    "Download",
                    data=f.read(),
                    file_name=fname,
                    key=f"dl_{category}_{fname}",
                )
    else:
        st.info("No files generated yet. Create your first proposal or report above!")


# ── Auth Routing ────────────────────────────────────────────────────────────

if check_team_auth():
    main()
elif check_portal_auth():
    st.switch_page("pages/portal_dashboard.py")
else:
    render_landing_page()
