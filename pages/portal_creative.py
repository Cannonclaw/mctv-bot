# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Client portal creative requests — submit photos/logos and request new creative."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import require_portal_auth, get_portal_user, portal_logout
from services.portal_service import get_client_by_user_id
from services.supabase_client import query_table, insert_row
from services.storage_service import upload_file, BUCKET_CREATIVE_UPLOADS
from services.notification_service import notify_creative_submitted

st.set_page_config(
    page_title="Creative Requests - MCTV Client Portal",
    page_icon="\U0001F3A8",
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
bname = client.get("business_name", "")

st.markdown("## Creative Requests")
st.caption(f"{bname} | Submit photos, logos, and creative requests")
st.divider()

# ── Tabs ────────────────────────────────────────────────────────────────────

tab_requests, tab_new = st.tabs(["My Requests", "Submit New Request"])

# ── Tab: Existing Requests ──────────────────────────────────────────────────

with tab_requests:
    requests = query_table("creative_requests", filters={"client_id": client_id},
                           order="-created_at")

    if not requests:
        st.info(
            "No creative requests yet. Use the 'Submit New Request' tab to send us "
            "photos, logos, or request new ad creative."
        )
    else:
        for req in requests:
            rid = req.get("id", "")
            req_title = req.get("title", "Request")
            req_type = req.get("request_type", "general").replace("_", " ").title()
            req_status = req.get("status", "pending")
            created = req.get("created_at", "")[:16] if req.get("created_at") else ""

            status_emoji = {
                "pending": "\U0001F7E1",
                "in_progress": "\U0001F535",
                "review": "\U0001F7E0",
                "approved": "\u2705",
                "live": "\U0001F7E2",
                "rejected": "\U0001F534",
            }.get(req_status, "\u26AA")

            with st.expander(
                f"{status_emoji} **{req_title}** — {req_type} | {req_status.replace('_', ' ').title()}",
                expanded=(req_status in ("pending", "in_progress")),
            ):
                st.text(f"Type: {req_type}")
                st.text(f"Status: {req_status.replace('_', ' ').title()}")
                st.text(f"Submitted: {created}")

                if req.get("description"):
                    st.markdown("**Description:**")
                    st.text(req.get("description"))

                # Show attached files
                files = query_table("creative_files", filters={"request_id": rid})
                if files:
                    st.markdown(f"**Attached Files:** {len(files)}")
                    for f in files:
                        st.caption(f"  {f.get('file_name', 'file')} ({f.get('file_type', '')})")

# ── Tab: New Request ────────────────────────────────────────────────────────

with tab_new:
    st.markdown("### Submit a Creative Request")
    st.caption(
        "Send us your photos, logos, or request new ad creative. "
        "Our team will handle everything from here."
    )

    with st.form("creative_request_form"):
        req_title = st.text_input("Request Title *", placeholder="e.g., New spring menu photos")

        req_type = st.selectbox(
            "Request Type *",
            ["New Ad Creative", "Update Existing Ad", "Logo Upload", "Photo Upload", "General Request"],
        )
        type_map = {
            "New Ad Creative": "new_ad",
            "Update Existing Ad": "update_ad",
            "Logo Upload": "logo_upload",
            "Photo Upload": "photo_upload",
            "General Request": "general",
        }

        description = st.text_area(
            "Description",
            placeholder="Tell us what you need. The more detail, the better we can help.",
            height=120,
        )

        uploaded_files = st.file_uploader(
            "Upload Files",
            type=["png", "jpg", "jpeg", "gif", "pdf", "ai", "psd", "svg"],
            accept_multiple_files=True,
            help="Upload photos, logos, or design files (max 20MB each)",
        )

        submitted = st.form_submit_button("Submit Request", type="primary",
                                          use_container_width=True)

        if submitted:
            if not req_title:
                st.error("Please enter a title for your request.")
            else:
                with st.spinner("Submitting your request..."):
                    # Create the request record
                    req_data = {
                        "client_id": client_id,
                        "submitted_by": user.get("user_id", ""),
                        "request_type": type_map.get(req_type, "general"),
                        "title": req_title,
                        "description": description,
                        "status": "pending",
                        "priority": "normal",
                    }
                    result = insert_row("creative_requests", req_data)

                    if result:
                        request_id = result.get("id", "")

                        # Upload attached files
                        file_count = 0
                        for uploaded_file in (uploaded_files or []):
                            file_bytes = uploaded_file.read()
                            storage_path = f"{client_id}/{request_id}/{uploaded_file.name}"

                            uploaded = upload_file(
                                BUCKET_CREATIVE_UPLOADS,
                                storage_path,
                                file_bytes,
                                uploaded_file.type,
                            )

                            if uploaded:
                                # Record file in creative_files table
                                insert_row("creative_files", {
                                    "request_id": request_id,
                                    "file_name": uploaded_file.name,
                                    "file_type": uploaded_file.type,
                                    "file_size": len(file_bytes),
                                    "storage_path": storage_path,
                                    "uploaded_by": user.get("user_id", ""),
                                })
                                file_count += 1

                        # Notify MCTV team
                        notify_creative_submitted(
                            business_name=bname,
                            request_title=req_title,
                            request_type=req_type,
                        )

                        file_msg = f" with {file_count} file(s)" if file_count else ""
                        st.success(f"Request submitted{file_msg}! Our team will get started on this.")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Failed to submit request. Please try again.")
