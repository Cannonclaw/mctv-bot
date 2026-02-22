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
            st.success("API Key: Connected")
        else:
            st.warning("API Key: Not configured")
            st.caption("Set your key in Settings or .env file")

        st.divider()
        st.markdown("**Navigation**")
        st.page_link("app.py", label="Home", icon="\U0001F3E0")
        st.page_link("pages/1_Proposals.py", label="Proposal Generator", icon="\U0001F4DD")
        st.page_link("pages/2_Reports.py", label="Traction Reports", icon="\U0001F4CA")
        st.page_link("pages/3_Settings.py", label="Settings", icon="\u2699\uFE0F")

        st.divider()
        st.caption("MCTV Elite Advertising")
        st.caption("Oxford | Starkville | Tupelo")
        st.caption("www.mctvofms.com")

    # Main content - Home page
    st.markdown('<p class="main-header">MCTV Elite Advertising Bot</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Generate proposals and traction reports in seconds</p>', unsafe_allow_html=True)

    st.divider()

    # Feature cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Proposal Generator")
        st.markdown(
            "Create polished advertising proposals tailored to each client. "
            "6 proposal types including Elite Advertiser, Host Media Kit, "
            "Multi-Brand Bundle, and more."
        )
        if st.button("Create Proposal", type="primary", use_container_width=True):
            st.switch_page("pages/1_Proposals.py")

    with col2:
        st.markdown("### Traction Reports")
        st.markdown(
            "Generate professional traction and ad performance reports "
            "from NTV360 data. Upload Excel exports or enter data manually."
        )
        if st.button("Create Report", type="primary", use_container_width=True):
            st.switch_page("pages/2_Reports.py")

    with col3:
        st.markdown("### Settings")
        st.markdown(
            "Configure your API key, update pricing, edit team info, "
            "and manage network data. All changes save instantly."
        )
        if st.button("Open Settings", use_container_width=True):
            st.switch_page("pages/3_Settings.py")

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
    for subdir in ["proposals", "reports", "emails"]:
        folder = output_dir / subdir
        if folder.exists():
            for f in sorted(folder.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
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
                    key=f"dl_{fname}",
                )
    else:
        st.info("No files generated yet. Create your first proposal or report above!")


if __name__ == "__main__":
    main()
