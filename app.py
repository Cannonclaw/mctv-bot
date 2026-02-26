# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""MCTV Elite Advertising Bot - Main Streamlit Application."""

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


# ── Password Gate ────────────────────────────────────────────────────────────
from services.auth import check_password
if not check_password():
    st.stop()


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
        st.caption("MCTV Elite Advertising")
        st.caption("Oxford | Starkville | Tupelo")
        st.caption("www.mctvofms.com")
        st.caption("© 2026 MCTV Digital, Inc.")

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


if __name__ == "__main__":
    main()
