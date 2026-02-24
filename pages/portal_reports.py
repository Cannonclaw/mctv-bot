"""Client portal reports — view shared traction reports."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import require_portal_auth, get_portal_user, portal_logout
from services.portal_service import get_client_by_user_id
from services.supabase_client import query_table
from services.storage_service import get_signed_url, BUCKET_REPORTS

st.set_page_config(
    page_title="Reports - MCTV Client Portal",
    page_icon="\U0001F4CA",
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

st.markdown("## Campaign Reports")
st.caption(f"{client.get('business_name', '')} | Performance & Traction Reports")
st.divider()

# ── Fetch reports ───────────────────────────────────────────────────────────

reports = query_table("client_reports", filters={"client_id": client_id},
                      order="-created_at")

if not reports:
    st.info(
        "No reports available yet. Your MCTV team will share traction reports here "
        "as your campaign runs. Reports typically include play counts, impressions, "
        "venue breakdowns, and insights."
    )
    st.stop()

for report in reports:
    rid = report.get("id", "")
    title = report.get("title", "Report")
    rtype = report.get("report_type", "traction").title()
    period = report.get("campaign_period", "")
    plays = report.get("total_plays")
    impressions = report.get("total_impressions")
    venues = report.get("total_venues")
    created = report.get("created_at", "")[:10] if report.get("created_at") else ""

    with st.expander(f"\U0001F4CA **{title}** — {period or created}", expanded=True):
        # Key metrics
        if plays or impressions or venues:
            mc1, mc2, mc3 = st.columns(3)
            if plays:
                mc1.metric("Total Plays", f"{plays:,}")
            if impressions:
                mc2.metric("Est. Impressions", f"{impressions:,}")
            if venues:
                mc3.metric("Venues", venues)

        st.text(f"Report Type: {rtype}")
        st.text(f"Period: {period or 'N/A'}")
        st.text(f"Shared: {created}")

        if report.get("highlights"):
            st.markdown("**Highlights:**")
            st.text(report.get("highlights"))

        # Download link
        doc_url = report.get("document_url", "")
        if doc_url:
            local_path = Path(doc_url) if doc_url else None
            if local_path and local_path.exists():
                with open(local_path, "rb") as f:
                    st.download_button(
                        "Download Full Report",
                        data=f.read(),
                        file_name=local_path.name,
                        key=f"dl_report_{rid}",
                        type="primary",
                    )
            else:
                url = get_signed_url(BUCKET_REPORTS, doc_url)
                if url:
                    st.markdown(f"[Download Full Report]({url})")
