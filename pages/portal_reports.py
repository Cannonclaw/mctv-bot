# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Client portal reports — view shared traction reports."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import require_portal_auth, get_portal_user
from services.supabase_client import query_table
from services.storage_service import get_signed_url, BUCKET_REPORTS
from services.portal_ui import inject_portal_css, render_portal_sidebar, render_portal_footer, load_portal_client

st.set_page_config(
    page_title="Reports - MCTV Client Portal",
    page_icon="\U0001F4CA",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_portal_css()
require_portal_auth()

user = get_portal_user()
render_portal_sidebar(user)
client = load_portal_client(user)

client_id = client.get("id", "")

st.markdown("## Campaign Reports")
st.caption(f"{client.get('business_name', '')} | Performance & Traction Reports")
st.divider()

# ── Fetch reports ───────────────────────────────────────────────────────────

try:
    reports = query_table("client_reports", filters={"client_id": client_id},
                          order="-created_at")
except Exception:
    st.error("Unable to load your reports. Please try again later.")
    reports = []

if not reports:
    st.info(
        "No reports available yet. Your MCTV team will share traction reports here "
        "as your campaign runs. Reports typically include play counts, impressions, "
        "venue breakdowns, and insights."
    )
    render_portal_footer()
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

        doc_url = report.get("document_url", "")
        if doc_url:
            local_path = Path(doc_url) if doc_url else None

            # Path traversal protection: ensure local path resolves inside output/
            if local_path:
                try:
                    resolved = local_path.resolve()
                    output_root = Path(__file__).parent.parent / "output"
                    if not str(resolved).startswith(str(output_root.resolve())):
                        local_path = None
                except Exception:
                    local_path = None

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
                try:
                    url = get_signed_url(BUCKET_REPORTS, doc_url)
                except Exception:
                    url = None

                if url:
                    st.link_button(
                        "Download Full Report",
                        url=url,
                        type="primary",
                    )

render_portal_footer()
