# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Shared team-side UI: branded sidebar, CSS, and page-header helper.

Use this module on every internal team page so the look stays consistent
and the navigation doesn't shift between pages. Three calls per page:

    from services.team_ui import inject_team_css, render_team_sidebar, render_page_header
    inject_team_css()
    render_team_sidebar()
    render_page_header("\U0001F4DD", "Proposals", "Generate polished proposals in seconds.")

(Or just call ``render_team_sidebar()`` — it injects the CSS automatically.)
"""

import streamlit as st
from pathlib import Path

LOGO_PATH = Path(__file__).parent.parent / "assets" / "branding" / "mctv_logo_white.png"

# ── Sidebar navigation, grouped by purpose ───────────────────────────────────
# Each item: (page_path, label, icon_emoji)
NAV_SECTIONS = [
    ("Home", [
        ("app.py", "Dashboard", "\U0001F3E0"),  # 🏠
    ]),
    ("Grow Revenue", [
        ("pages/1_Proposals.py",       "Proposals",            "\U0001F4DD"),  # 📝
        ("pages/25_Rate_Card.py",      "Rate Card",            "\U0001F3F7\uFE0F"),  # 🏷️
        ("pages/16_Simulator.py",      "Audience Simulator",   "\U0001F4CA"),  # 📊
        ("pages/17_VoiceToProposal.py","Voice to Proposal",    "\U0001F3A4"),  # 🎤
        ("pages/19_SalesCoach.py",     "Sales Coach",          "\U0001F3C6"),  # 🏆
        ("pages/6_Samples.py",         "Sample Gallery",       "\U0001F4C2"),  # 📂
    ]),
    ("Pipeline", [
        ("pages/14_Pipeline.py",       "Sales Pipeline",       "\U0001F4B0"),  # 💰
        ("pages/15_Prospector.py",     "Prospector",           "\U0001F3AF"),  # 🎯
        ("pages/4_Leads.py",           "Leads",                "\U0001F4CB"),  # 📋
        ("pages/20_HostPipeline.py",   "Host Pipeline",        "\U0001F3E2"),  # 🏢
    ]),
    ("Client Work", [
        ("pages/8_Clients.py",         "Clients",              "\U0001F465"),  # 👥
        ("pages/9_Contracts.py",       "Contracts",            "\U0001F4C3"),  # 📃
        ("pages/10_Invoices.py",       "Invoices",             "\U0001F4B5"),  # 💵
        ("pages/11_Creative.py",       "Creative Requests",    "\U0001F3A8"),  # 🎨
    ]),
    ("Operations", [
        ("pages/2_Reports.py",         "Traction Reports",     "\U0001F4C8"),  # 📈
        ("pages/13_Briefing.py",       "Daily Briefing",       "\U0001F4D1"),  # 📑
        ("pages/18_ScreenHealth.py",   "Screen Health",        "\U0001F6A8"),  # 🚨
        ("pages/24_Loop_Inventory.py","Loop Inventory",       "\U0001F4FA"),  # 📺
        ("pages/21_RepDashboard.py",   "Rep Dashboard",        "\U0001F4B2"),  # 💲
    ]),
    ("Tools", [
        ("pages/7_Research.py",        "Prospect Research",    "\U0001F50D"),  # 🔍
        ("pages/5_Video_Ads.py",       "Video Ads",            "\U0001F3AC"),  # 🎬
        ("pages/12_Messaging.py",      "SMS Messaging",        "\U0001F4F1"),  # 📱
    ]),
    ("Admin", [
        ("pages/3_Settings.py",        "Settings",             "\u2699\uFE0F"),  # ⚙️
    ]),
]

# ── Branded CSS — applied globally on every team page ───────────────────────
TEAM_CSS = """
<style>
    /* Hide Streamlit's auto-generated page nav (we render our own) */
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stSidebarNavSeparator"] { display: none !important; }

    /* ── Sidebar shell ─────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #1B1F3B 100%) !important;
        border-right: 1px solid #2a2f55;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0.5rem;
    }

    /* Sidebar text colors */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] li,
    [data-testid="stSidebar"] label {
        color: #e8e8e8 !important;
    }
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #888 !important;
    }

    /* Section labels */
    .mctv-nav-section {
        color: #C5A55A !important;
        font-size: 0.68rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.14em !important;
        text-transform: uppercase !important;
        padding: 1rem 1rem 0.3rem !important;
        margin: 0 !important;
        opacity: 0.9;
    }

    /* Page links — sleek nav items */
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"],
    [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
        background: transparent !important;
        padding: 0.5rem 1rem !important;
        border-radius: 8px !important;
        margin: 0.1rem 0.5rem !important;
        transition: all 0.15s ease !important;
        border-left: 3px solid transparent !important;
    }
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
        background: rgba(197, 165, 90, 0.12) !important;
        border-left: 3px solid #C5A55A !important;
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] span,
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {
        color: #d8d8d8 !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover span,
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover p {
        color: #ffffff !important;
    }

    /* Sidebar logo block */
    .mctv-logo-wrap {
        text-align: center;
        padding: 0.6rem 1rem 0.3rem;
    }
    .mctv-tagline {
        text-align: center;
        color: #C5A55A !important;
        font-size: 0.7rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin: -0.4rem 0 0.5rem !important;
        opacity: 0.85;
    }

    /* Sidebar buttons (logout) */
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255, 255, 255, 0.06) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: #e8e8e8 !important;
        font-weight: 500 !important;
        transition: all 0.15s !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(197, 165, 90, 0.15) !important;
        border-color: #C5A55A !important;
        color: #ffffff !important;
    }

    /* Subtle divider */
    [data-testid="stSidebar"] hr {
        border: 0;
        height: 1px;
        background: rgba(197, 165, 90, 0.2);
        margin: 0.8rem 1rem;
    }

    /* ── Main content polish ──────────────────────────────────── */
    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1400px;
    }

    .main h1, .main h2 {
        color: #1B1F3B;
        font-weight: 700;
        letter-spacing: -0.01em;
    }
    .main h3 {
        color: #1B1F3B;
        font-weight: 600;
    }

    /* Metric tiles — sleeker, branded */
    [data-testid="stMetric"] {
        background: linear-gradient(180deg, #ffffff 0%, #fafaf5 100%);
        border: 1px solid #ececec;
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        box-shadow: 0 1px 3px rgba(27, 31, 59, 0.04);
    }
    [data-testid="stMetricValue"] {
        color: #1B1F3B !important;
        font-weight: 700 !important;
        font-size: 1.7rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: #6b7280 !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.07em !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.78rem !important;
    }

    /* Primary buttons — gold + dark text */
    .stButton > button[kind="primary"] {
        background: #C5A55A !important;
        border: 1px solid #C5A55A !important;
        color: #1B1F3B !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em;
        transition: all 0.15s ease;
        box-shadow: 0 1px 2px rgba(197, 165, 90, 0.25);
    }
    .stButton > button[kind="primary"]:hover {
        background: #b5944a !important;
        border-color: #b5944a !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(197, 165, 90, 0.3);
    }

    /* Secondary buttons — clean outlined */
    .stButton > button:not([kind="primary"]) {
        background: #ffffff;
        border: 1px solid #d4d4d8;
        color: #1B1F3B;
        font-weight: 500;
        transition: all 0.15s ease;
    }
    .stButton > button:not([kind="primary"]):hover {
        border-color: #1B1F3B;
        background: #fafafa;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 1px solid #e5e7eb;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        color: #C5A55A !important;
        font-weight: 600 !important;
    }

    /* Dataframes — softer borders */
    .stDataFrame {
        border: 1px solid #ececec !important;
        border-radius: 8px !important;
    }

    /* Dividers */
    .main hr {
        border: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, #e5e7eb, transparent);
        margin: 1.2rem 0;
    }

    /* Hide Streamlit chrome */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
"""


def inject_team_css():
    """Apply branded CSS globally. Idempotent (Streamlit re-renders are fine)."""
    st.markdown(TEAM_CSS, unsafe_allow_html=True)


def render_team_sidebar():
    """Render the branded sidebar on every team page.

    Also injects the CSS, so calling just this is enough on most pages.
    """
    inject_team_css()

    with st.sidebar:
        # Logo
        if LOGO_PATH.exists():
            st.markdown('<div class="mctv-logo-wrap">', unsafe_allow_html=True)
            st.image(str(LOGO_PATH), width="stretch")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="mctv-tagline">Indoor Digital Billboards</p>',
            unsafe_allow_html=True,
        )

        # Grouped nav
        for section_name, items in NAV_SECTIONS:
            st.markdown(
                f'<p class="mctv-nav-section">{section_name}</p>',
                unsafe_allow_html=True,
            )
            for path, label, icon in items:
                try:
                    st.page_link(path, label=label, icon=icon)
                except Exception:
                    # If a page is missing for some reason, skip silently
                    pass

        st.markdown("---")

        # Client portal access
        try:
            st.page_link("pages/portal_login.py", label="Client Portal",
                          icon="\U0001F310")
        except Exception:
            pass

        if st.button("Log Out", width="stretch", key="team_logout_btn"):
            try:
                from services.auth import team_logout
                team_logout()
            except Exception:
                pass
            st.rerun()

        st.caption("MCTV Elite Advertising")
        st.caption("Oxford · Starkville · Tupelo")
        st.caption("\u00A9 2026 MCTV Digital, Inc.")


def render_page_header(emoji: str, title: str, subtitle: str = ""):
    """Consistent page header pattern. Use after render_team_sidebar()."""
    sub_html = (
        f'<p style="color:#6b7280; margin: 0.35rem 0 0; font-size: 1rem;">{subtitle}</p>'
        if subtitle else ""
    )
    st.markdown(
        f'<div style="padding: 0.5rem 0 1.2rem; border-bottom: 2px solid #f3f4f6; '
        f'margin-bottom: 1.2rem;">'
        f'<h1 style="color: #1B1F3B; margin: 0; font-size: 1.85rem; font-weight: 700; '
        f'letter-spacing: -0.01em;">'
        f'<span style="margin-right: 0.4rem;">{emoji}</span>{title}'
        f'</h1>{sub_html}</div>',
        unsafe_allow_html=True,
    )
