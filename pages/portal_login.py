# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Client portal login — email/password + magic link (passwordless) via Supabase Auth.

Auth flows supported:
1. Password login: email + password, exchanged for tokens via sign_in().
2. Magic link (OTP): email only, Supabase sends a login link. When clicked,
   redirects back here with ?token_hash=xxx&type=magiclink, exchanged via verify_otp().
3. Password reset: "Forgot Password?" sends a reset link. When clicked,
   redirects back here with ?token_hash=xxx&type=recovery. The token is exchanged
   for a session and the user sees a "Set New Password" form.

Supabase Dashboard requirements (Auth > URL Configuration):
- Site URL: https://mctv-bot.onrender.com
- Redirect URLs: https://mctv-bot.onrender.com/portal_login
  (also add http://localhost:8501/portal_login for local dev)
"""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import (
    check_portal_auth, portal_login, portal_logout,
    send_portal_magic_link, portal_magic_link_callback,
)
from services.supabase_client import is_configured, reset_password, update_user_password

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


# ── Magic Link / Recovery Callback Handler ─────────────────────────────────
# When Supabase redirects back after the user clicks a magic link or password
# reset link, the URL contains ?token_hash=xxx&type=magiclink (or type=recovery).
# We must handle this BEFORE rendering anything else, similar to the QuickBooks
# OAuth callback in 3_Settings.py.

_token_hash = st.query_params.get("token_hash", "")
_auth_type = st.query_params.get("type", "")

if _token_hash and _auth_type in ("magiclink", "recovery"):
    # Clear the query params immediately so they don't fire again on refresh
    st.query_params.clear()

    if _auth_type == "recovery":
        # Password reset flow: exchange the token for a session, then show
        # a "Set New Password" form. We store the session in state temporarily.
        with st.spinner("Verifying reset link..."):
            result = portal_magic_link_callback(_token_hash, otp_type="recovery")

        if result:
            # User is now authenticated via the recovery token. Show the
            # password change form instead of redirecting to the dashboard.
            st.session_state["_recovery_mode"] = True
            st.session_state["_recovery_access_token"] = result.get("access_token", "")
        else:
            st.error(
                "This reset link has expired or is invalid. "
                "Please request a new one."
            )
            st.stop()

    else:
        # Magic link login flow: exchange token_hash for a full session
        with st.spinner("Signing you in..."):
            result = portal_magic_link_callback(_token_hash, otp_type="magiclink")

        if result:
            st.success(f"Welcome, {result.get('full_name', 'there')}!")
            st.switch_page("pages/portal_dashboard.py")
        else:
            st.error(
                "This magic link has expired or your email is not authorized. "
                "Please try again or contact your MCTV representative."
            )
            st.stop()


# ── Already logged in? Redirect to dashboard ────────────────────────────────
# (Skip this check if we're in recovery mode — the user needs to set a password)

if check_portal_auth() and not st.session_state.get("_recovery_mode"):
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
        st.image(str(logo_path), width='stretch')

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

    # ── Recovery mode: Set New Password form ───────────────────────────────
    if st.session_state.get("_recovery_mode"):
        st.markdown("#### Set New Password")
        st.info("Your identity has been verified. Enter a new password below.")

        new_pw = st.text_input("New Password", type="password", key="recovery_new_pw")
        confirm_pw = st.text_input("Confirm Password", type="password", key="recovery_confirm_pw")

        if st.button("Update Password", type="primary", width='stretch'):
            if not new_pw or not confirm_pw:
                st.error("Please fill in both fields.")
            elif new_pw != confirm_pw:
                st.error("Passwords do not match.")
            elif len(new_pw) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                token = st.session_state.get("_recovery_access_token", "")
                with st.spinner("Updating password..."):
                    success = update_user_password(token, new_pw)
                if success:
                    # Clear recovery state
                    st.session_state.pop("_recovery_mode", None)
                    st.session_state.pop("_recovery_access_token", None)
                    st.success("Password updated! You can now log in with your new password.")
                    # Log them out so they re-authenticate with the new password
                    portal_logout()
                    st.rerun()
                else:
                    st.error("Failed to update password. The link may have expired. Please try again.")

        if st.button("Cancel", width='stretch'):
            st.session_state.pop("_recovery_mode", None)
            st.session_state.pop("_recovery_access_token", None)
            portal_logout()
            st.rerun()

    # ── Password reset request form ────────────────────────────────────────
    elif st.session_state.get("show_reset_form"):
        st.markdown("#### Reset Password")
        reset_email = st.text_input("Email Address", key="reset_email",
                                    placeholder="your@email.com")

        if st.button("Send Reset Link", type="primary", width='stretch'):
            if reset_email:
                with st.spinner("Sending reset link..."):
                    success = reset_password(reset_email)
                    if success:
                        st.success(
                            "Password reset link sent! Check your email and "
                            "click the link to set a new password."
                        )
                    else:
                        st.error("Could not send reset link. Please check your email address.")
            else:
                st.error("Please enter your email address.")

        if st.button("Back to Login", width='stretch'):
            st.session_state["show_reset_form"] = False
            st.rerun()

    # ── Main login form (password + magic link toggle) ─────────────────────
    else:
        st.markdown("#### Log In")

        # Login method toggle: password vs. magic link
        use_magic_link = st.toggle("Use email link instead of password",
                                   key="use_magic_link",
                                   help="We'll send a sign-in link to your email. No password needed.")

        email = st.text_input("Email", key="portal_login_email",
                              placeholder="your@email.com")

        if use_magic_link:
            # ── Magic link mode ────────────────────────────────────────────
            if st.button("Send Sign-In Link", type="primary", width='stretch'):
                if not email:
                    st.error("Please enter your email address.")
                else:
                    with st.spinner("Sending sign-in link..."):
                        success = send_portal_magic_link(email)
                    if success:
                        st.success(
                            "Sign-in link sent! Check your email and click the "
                            "link to log in. You can close this tab."
                        )
                        st.info(
                            "Didn't get the email? Check your spam folder, "
                            "or try again in a minute."
                        )
                    else:
                        st.error(
                            "Could not send sign-in link. Your email may not be "
                            "authorized for portal access. Contact your MCTV representative."
                        )
        else:
            # ── Password mode ──────────────────────────────────────────────
            password = st.text_input("Password", type="password",
                                     key="portal_login_password")

            if st.button("Log In", type="primary", width='stretch'):
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

        if st.button("Forgot Password?", width='stretch'):
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
