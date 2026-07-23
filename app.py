# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""MCTV Elite Advertising Bot - Main Streamlit Application.

Single entry point with a unified landing page offering three login paths:
1. Team Member — shared password for internal tools
2. Host Venue — Supabase email/password or magic link for venue partners
3. Advertiser — Supabase email/password or magic link for advertisers
"""

import logging
import mimetypes

# Configure logging so notification_service, contract_service etc. output
# goes to Render's stdout log stream.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Fix 1: Windows maps .js → text/plain in the registry. Starlette's
# FileResponse calls mimetypes.guess_type() so we fix it globally.
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")

import streamlit as st

# Fix 2 + 3: Streamlit internal-module patches for .js MIME types and PWA
# service-worker scope. These reach into Streamlit's private innards and
# the module paths shift between versions, so we wrap each patch in its
# own try/except — none of them are critical, and we'd rather have the app
# boot than enforce a fix Streamlit may have already applied upstream.
def _apply_streamlit_patches():
    try:
        import streamlit.web.server.app_static_file_handler as _asfh
    except ImportError:
        logging.warning("streamlit.web.server.app_static_file_handler missing — "
                        "skipping .js MIME + PWA Tornado patches")
        _asfh = None

    try:
        import streamlit.web.server.starlette.starlette_routes as _star_routes
    except ImportError:
        logging.warning("streamlit.web.server.starlette.starlette_routes missing — "
                        "skipping PWA Starlette patches")
        _star_routes = None

    # .js + .html extension whitelist. .html is here so the public rate
    # calculator stays reachable at /app/static/rates.html even if the
    # /rates route in server_routes.py stops matching a future Streamlit.
    # Only files we ship in static/ are servable, none of them user-supplied.
    if _asfh is not None and hasattr(_asfh, "SAFE_APP_STATIC_FILE_EXTENSIONS"):
        try:
            safe_exts = _asfh.SAFE_APP_STATIC_FILE_EXTENSIONS + (".js", ".html")
            _asfh.SAFE_APP_STATIC_FILE_EXTENSIONS = safe_exts
            if _star_routes is not None and hasattr(_star_routes,
                                                     "SAFE_APP_STATIC_FILE_EXTENSIONS"):
                _star_routes.SAFE_APP_STATIC_FILE_EXTENSIONS = safe_exts
        except Exception as _e:
            logging.warning("Could not patch SAFE_APP_STATIC_FILE_EXTENSIONS: %s", _e)

    # Tornado: Service-Worker-Allowed header
    if _asfh is not None and hasattr(_asfh, "AppStaticFileHandler"):
        try:
            _orig_set_extra = _asfh.AppStaticFileHandler.set_extra_headers

            def _sw_extra_headers(self, path):
                _orig_set_extra(self, path)
                if path.endswith("service-worker.js"):
                    self.set_header("Service-Worker-Allowed", "/")

            _asfh.AppStaticFileHandler.set_extra_headers = _sw_extra_headers
        except Exception as _e:
            logging.warning("Could not patch Tornado AppStaticFileHandler: %s", _e)

    # Starlette: Service-Worker-Allowed header via wrapped route endpoint
    if _star_routes is not None and hasattr(_star_routes,
                                              "create_app_static_serving_routes"):
        try:
            _orig_starlette_static = _star_routes.create_app_static_serving_routes

            def _patched_starlette_static(main_script_path, base_url=None):
                from starlette.routing import Route as _Route
                routes = _orig_starlette_static(main_script_path, base_url)
                patched = []
                for r in routes:
                    if hasattr(r, "methods") and r.methods and "GET" in r.methods:
                        _orig_ep = r.endpoint

                        async def _wrapped(request, _ep=_orig_ep):
                            resp = await _ep(request)
                            if request.path_params.get("path", "").endswith("service-worker.js"):
                                resp.headers["Service-Worker-Allowed"] = "/"
                            return resp

                        patched.append(_Route(r.path, _wrapped, methods=list(r.methods)))
                    else:
                        patched.append(r)
                return patched

            _star_routes.create_app_static_serving_routes = _patched_starlette_static
        except Exception as _e:
            logging.warning("Could not patch Starlette static routes: %s", _e)


_apply_streamlit_patches()

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

# PWA support (manifest, service worker, mobile CSS)
from services.pwa import inject_pwa, inject_install_banner
inject_pwa()
inject_install_banner()

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
    from services.team_ui import render_team_sidebar

    render_team_sidebar()

    # ── HERO ──────────────────────────────────────────────────────────────
    user_name = st.session_state.get("team_user", "")
    greet = f"Welcome back{', ' + user_name.split()[0] if user_name else ''}."
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1B1F3B 0%, #2a2f55 100%);
                color: white; padding: 1.8rem 2rem; border-radius: 14px;
                margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(27,31,59,0.15);">
        <p style="color:#C5A55A; font-size:0.78rem; letter-spacing:0.18em; margin:0;
                  text-transform:uppercase; font-weight:600;">MCTV ELITE ADVERTISING</p>
        <h1 style="color:#fff; margin:0.4rem 0 0.3rem; font-size:1.9rem; font-weight:700;
                   letter-spacing:-0.01em;">{greet}</h1>
        <p style="color:#d8d8d8; margin:0; font-size:1.02rem;">
            North Mississippi's indoor digital billboard network — 125+ screens,
            1.9M+ monthly impressions, captive audiences across Oxford, Starkville, and Tupelo.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── TODAY'S BRIEFING ───────────────────────────────────────────────────
    try:
        from services.briefing_service import generate_briefing as _gen_briefing
        if "home_alerts" not in st.session_state:
            _brief = _gen_briefing()
            st.session_state.home_alerts = _brief.get("alerts", [])
            st.session_state.home_summary = _brief.get("executive_summary", {})

        _summary = st.session_state.get("home_summary", {})
        _alerts = st.session_state.get("home_alerts", [])

        if _summary:
            st.markdown("##### \U0001F4CA  At a glance")
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("MRR",
                      f"${_summary.get('monthly_recurring_revenue', 0):,.0f}")
            k2.metric("Active Clients",
                      _summary.get("active_clients", 0))
            k3.metric("Pending Sig",
                      _summary.get("contracts_awaiting_signature", 0))
            k4.metric("Overdue AR",
                      f"${_summary.get('overdue_amount', 0):,.0f}")
            k5.metric("Hot Leads",
                      _summary.get("hot_leads", 0))

        if _alerts:
            st.markdown("##### \u26A0\uFE0F  Today's focus")
            for _a in _alerts[:3]:
                st.warning(_a)
            if len(_alerts) > 3:
                if st.button(f"View all {len(_alerts)} alerts \u2192",
                             key="goto_briefing"):
                    st.switch_page("pages/13_Briefing.py")
    except Exception:
        pass

    st.markdown("&nbsp;", unsafe_allow_html=True)

    # ── PRIMARY ACTIONS ─────────────────────────────────────────────────
    st.markdown("##### \U0001F680  Move a deal forward")
    p1, p2, p3, p4 = st.columns(4)

    def _action_card(col, emoji, title, blurb, target, btn_text, btn_key):
        with col:
            st.markdown(
                f"""<div style="background:#fff; border:1px solid #ececec;
                       border-radius:12px; padding:1.2rem; height: 175px;
                       box-shadow:0 1px 3px rgba(27,31,59,0.04);">
                <div style="font-size:1.6rem; margin-bottom:0.4rem;">{emoji}</div>
                <h4 style="color:#1B1F3B; margin:0 0 0.3rem; font-size:1.05rem;
                           font-weight:700;">{title}</h4>
                <p style="color:#6b7280; font-size:0.86rem; margin:0;
                          line-height:1.4;">{blurb}</p>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button(btn_text, key=btn_key, type="primary",
                         width="stretch"):
                st.switch_page(target)

    _action_card(p1, "\U0001F4CA", "Build a Plan",
                  "Pick venues on the map, see live impressions and CPM.",
                  "pages/16_Simulator.py", "Open Simulator", "act_sim")
    _action_card(p2, "\U0001F4DD", "New Proposal",
                  "Generate a polished proposal PDF in under 60 seconds.",
                  "pages/1_Proposals.py", "Create Proposal", "act_prop")
    _action_card(p3, "\U0001F3A4", "Voice to Proposal",
                  "Paste call notes — Claude pre-fills a scenario for you.",
                  "pages/17_VoiceToProposal.py", "Open", "act_v2p")
    _action_card(p4, "\U0001F3AF", "Prospector",
                  "Hunt cold leads in Oxford, Starkville, and Tupelo.",
                  "pages/15_Prospector.py", "Find Leads", "act_pro")

    st.markdown("&nbsp;", unsafe_allow_html=True)

    # ── PIPELINE + CLIENT WORK ───────────────────────────────────────────
    p5, p6, p7, p8 = st.columns(4)
    _action_card(p5, "\U0001F4B0", "Sales Pipeline",
                  "Move deals through 9 stages. See revenue forecast.",
                  "pages/14_Pipeline.py", "View Pipeline", "act_pipe")
    _action_card(p6, "\U0001F4C3", "Contracts",
                  "Send for e-signature, manage renewals and onboarding.",
                  "pages/9_Contracts.py", "View Contracts", "act_contracts")
    _action_card(p7, "\U0001F4B5", "Invoices",
                  "Send Pay Now links via QuickBooks. Track AR.",
                  "pages/10_Invoices.py", "View Invoices", "act_invoices")
    _action_card(p8, "\U0001F4B2", "Rep Dashboard",
                  "Your MRR, commission accrual, and stalled deals.",
                  "pages/21_RepDashboard.py", "Your Numbers", "act_rep")

    st.markdown("&nbsp;", unsafe_allow_html=True)

    # ── NETWORK SNAPSHOT ─────────────────────────────────────────────────
    st.markdown("##### \U0001F4FA  Network Snapshot")
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("Total Screens", "125+")
    n2.metric("Monthly Impressions", "1.9M+")
    n3.metric("Avg Dwell Time", "55+ min")
    n4.metric("Markets", "3 Active")

    # ── RECENT OUTPUT (compact list) ─────────────────────────────────────
    output_dir = Path(__file__).parent / "output"
    recent_files = []
    for subdir in ["proposals", "reports", "contracts", "emails", "videos", "research", "case_studies"]:
        folder = output_dir / subdir
        if folder.exists():
            for f in sorted(folder.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                if f.name.startswith("."):
                    continue
                recent_files.append((f.name, subdir, f))

    if recent_files:
        st.markdown("##### \U0001F4C2  Recent Output")
        for fname, category, fpath in recent_files[:8]:
            col_a, col_b, col_c = st.columns([4, 1, 1])
            col_a.text(fname)
            col_b.markdown(
                f'<span style="color:#C5A55A; font-size:0.78rem; '
                f'text-transform:uppercase; letter-spacing:0.06em; '
                f'font-weight:600;">{category}</span>',
                unsafe_allow_html=True,
            )
            with open(fpath, "rb") as f:
                col_c.download_button(
                    "\u2B07\uFE0F",
                    data=f.read(),
                    file_name=fname,
                    key=f"dl_{category}_{fname}",
                )


# ── Auth Routing ────────────────────────────────────────────────────────────

if check_team_auth():
    main()
elif check_portal_auth():
    st.switch_page("pages/portal_dashboard.py")
else:
    render_landing_page()
