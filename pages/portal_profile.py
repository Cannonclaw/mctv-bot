# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Client portal profile — edit contact info and change password."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import require_portal_auth, get_portal_user, portal_logout
from services.portal_service import get_client_by_user_id, update_client
from services.supabase_client import reset_password

st.set_page_config(
    page_title="My Profile - MCTV Client Portal",
    page_icon="\U0001F464",
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

st.markdown("## My Profile")
st.caption(f"{client.get('business_name', '')} | Account Settings")
st.divider()

# ── Contact Info ────────────────────────────────────────────────────────────

st.markdown("### Contact Information")

with st.form("profile_form"):
    pc1, pc2 = st.columns(2)

    with pc1:
        contact_name = st.text_input("Contact Name",
                                     value=client.get("contact_name", ""))
        contact_email = st.text_input("Email",
                                      value=client.get("contact_email", ""),
                                      disabled=True,
                                      help="Contact your MCTV rep to change your email")

    with pc2:
        contact_phone = st.text_input("Phone",
                                      value=client.get("contact_phone", ""))
        city = st.text_input("City",
                             value=client.get("city", ""))

    if st.form_submit_button("Save Changes", type="primary", use_container_width=True):
        update_data = {
            "contact_name": contact_name,
            "contact_phone": contact_phone,
            "city": city,
        }
        result = update_client(client_id, update_data)
        if result:
            st.success("Profile updated.")
            st.rerun()
        else:
            st.error("Failed to update profile.")

# ── Account Details ─────────────────────────────────────────────────────────

st.divider()
st.markdown("### Account Details")

ac1, ac2 = st.columns(2)
with ac1:
    st.text(f"Business: {client.get('business_name', '')}")
    st.text(f"Account Type: {client.get('client_type', 'advertiser').title()}")
    st.text(f"Status: {client.get('status', 'onboarding').title()}")

with ac2:
    st.text(f"Assigned Rep: {client.get('assigned_rep', 'MCTV Team')}")
    st.text(f"Portal Email: {user.get('email', '')}")
    created = client.get("created_at", "")[:10] if client.get("created_at") else "N/A"
    st.text(f"Member Since: {created}")

# ── Password Reset ──────────────────────────────────────────────────────────

st.divider()
st.markdown("### Change Password")
st.caption("We'll send a password reset link to your email address.")

if st.button("Send Password Reset Email", use_container_width=True):
    email = user.get("email", "")
    if email:
        with st.spinner("Sending reset link..."):
            success = reset_password(email)
            if success:
                st.success(f"Password reset link sent to {email}. Check your inbox.")
            else:
                st.error("Could not send reset link. Please try again later.")
    else:
        st.error("No email address on file.")

# ── Support ─────────────────────────────────────────────────────────────────

st.divider()
st.markdown("### Need Help?")
st.markdown(
    "Contact your MCTV representative directly, or reach us at:\n"
    "- **Creed Cannon** — creed@mctvofms.com | (601) 201-8202\n"
    "- **Mary Michael Cannon** — mmc@mctvofms.com | (662) 801-5677\n"
    "- **Swayze Hollingsworth** — swayze@mctvofms.com | (662) 907-0404"
)
