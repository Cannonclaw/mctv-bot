# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Client portal login — email/password via Supabase Auth."""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_portal_auth, portal_login, portal_logout
from services.supabase_client import is_configured, reset_password

st.set_page_config(
    page_title="Client Portal - MCTV Elite Advertising",
    page_icon="\U0001F4FA",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* MCTV Brand Colors */
    :root { --navy: #1B1F3B; --gold: #C5A55A; }

    /* Hide default sidebar nav for portal pages */
    [data-testid="stSidebar"] { display: none; }

    /* Center the login form */
    .portal-header {
        text-align: center;
        padding: 1rem 0;
    }
    .portal-header h1 {
        color: #1B1F3B;
        font-size: 1.8rem;
        margin-bottom: 0;
    }
    .portal-header p {
        color: #C5A55A;
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Already logged in? Redirect to dashboard ────────────────────────────────

if check_portal_auth():
    st.switch_page("pages/portal_dashboard.py")


# ── Supabase not configured ─────────────────────────────────────────────────

if not is_configured():
    st.error("The client portal is not yet available. Please contact MCTV for access.")
    st.stop()


# ── Login Page ──────────────────────────────────────────────────────────────

# Logo
logo_path = Path(__file__).parent.parent / "assets" / "branding" / "mctv_logo.png"
if logo_path.exists():
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.image(str(logo_path), use_container_width=True)

st.markdown(
    """
    <div class="portal-header">
        <h1>Client Portal</h1>
        <p>View your contracts, invoices, and campaign performance</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Login form
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    # Check for password reset mode
    if st.session_state.get("show_reset_form"):
        st.markdown("#### Reset Password")
        reset_email = st.text_input("Email Address", key="reset_email",
                                    placeholder="your@email.com")

        if st.button("Send Reset Link", type="primary", use_container_width=True):
            if reset_email:
                with st.spinner("Sending reset link..."):
                    success = reset_password(reset_email)
                    if success:
                        st.success("Password reset link sent. Check your email.")
                    else:
                        st.error("Could not send reset link. Please check your email address.")
            else:
                st.error("Please enter your email address.")

        if st.button("Back to Login", use_container_width=True):
            st.session_state["show_reset_form"] = False
            st.rerun()

    else:
        st.markdown("#### Log In")
        email = st.text_input("Email", key="portal_login_email",
                              placeholder="your@email.com")
        password = st.text_input("Password", type="password",
                                 key="portal_login_password")

        if st.button("Log In", type="primary", use_container_width=True):
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Signing in..."):
                    result = portal_login(email, password)
                    if result:
                        st.success(f"Welcome, {result.get('full_name', 'there')}!")
                        st.switch_page("pages/portal_dashboard.py")
                    else:
                        st.error("Invalid email or password. Please try again.")

        if st.button("Forgot Password?", use_container_width=True):
            st.session_state["show_reset_form"] = True
            st.rerun()

        st.divider()
        st.caption("Don't have an account? Contact your MCTV representative to get set up.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; font-size: 0.85rem;">
        <p>MCTV Elite Advertising | Oxford | Starkville | Tupelo</p>
        <p>www.mctvofms.com</p>
        <p style="margin-top: 0.5rem; font-size: 0.75rem;">
            &copy; 2026 MCTV Digital, Inc. All rights reserved.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
