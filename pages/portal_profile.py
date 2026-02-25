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

from services.auth import require_portal_auth, get_portal_user
from services.portal_service import update_client
from services.supabase_client import reset_password
from services.portal_ui import inject_portal_css, render_portal_sidebar, render_portal_footer, load_portal_client

st.set_page_config(
    page_title="My Profile - MCTV Client Portal",
    page_icon="\U0001F464",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_portal_css()
require_portal_auth()

user = get_portal_user()
render_portal_sidebar(user)
client = load_portal_client(user)

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
        try:
            result = update_client(client_id, update_data)
            if result:
                st.success("Profile updated.")
                st.rerun()
            else:
                st.error("Failed to update profile. Please try again.")
        except Exception as e:
            st.error(f"Error updating profile: {e}")

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

if st.button("Send Password Reset Email", type="primary", use_container_width=True):
    email = user.get("email", "")
    if email:
        with st.spinner("Sending reset link..."):
            try:
                success = reset_password(email)
                if success:
                    st.success(f"Password reset link sent to {email}. Check your inbox.")
                else:
                    st.error("Could not send reset link. Please try again later.")
            except Exception:
                st.error("An error occurred. Please try again later.")
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

render_portal_footer()
