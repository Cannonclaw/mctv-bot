# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Dual-mode authentication for MCTV Bot.

Supports two parallel auth paths:
1. Team login: Shared password (APP_PASSWORD) for internal tools
2. Portal login: Supabase Auth (email/password OR magic link) for client portal

Both modes use st.session_state to track auth state. The two paths
never interfere — a team login doesn't affect portal auth and vice versa.

Magic link (passwordless) flow:
1. User enters email on portal_login page and clicks "Send Magic Link"
2. Supabase sends an email with a link containing ?token_hash=xxx&type=magiclink
3. User clicks the link, which redirects back to portal_login with those query params
4. portal_login detects the params and calls portal_magic_link_callback()
5. This exchanges the token_hash for a session via supabase_client.verify_otp()
6. On success, session state is set and user is redirected to the dashboard

Password reset flow:
1. User clicks "Forgot Password?" on portal_login (or "Change Password" on profile)
2. Supabase sends a reset link with ?token_hash=xxx&type=recovery
3. User clicks it, redirects to portal_login which detects type=recovery
4. The token is exchanged for a session, and the user sees a "Set New Password" form
"""

import streamlit as st
import os
import time
from pathlib import Path


# ── Login Rate Limiting ────────────────────────────────────────────────────
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_LOCKOUT_SECONDS = 300  # 5 minutes


def _check_rate_limit(key: str) -> bool:
    """Return True if the login attempt is allowed, False if locked out."""
    attempts = st.session_state.get(f"_login_attempts_{key}", 0)
    lockout_until = st.session_state.get(f"_login_lockout_{key}", 0)

    if lockout_until and time.time() < lockout_until:
        return False

    if lockout_until and time.time() >= lockout_until:
        st.session_state[f"_login_attempts_{key}"] = 0
        st.session_state[f"_login_lockout_{key}"] = 0

    return True


def _record_failed_login(key: str):
    """Record a failed login attempt and lock out if threshold reached."""
    attempts = st.session_state.get(f"_login_attempts_{key}", 0) + 1
    st.session_state[f"_login_attempts_{key}"] = attempts

    if attempts >= _LOGIN_MAX_ATTEMPTS:
        st.session_state[f"_login_lockout_{key}"] = time.time() + _LOGIN_LOCKOUT_SECONDS


def _reset_login_attempts(key: str):
    """Reset login attempt counter after successful login."""
    st.session_state.pop(f"_login_attempts_{key}", None)
    st.session_state.pop(f"_login_lockout_{key}", None)


# ── Portal Access Control ───────────────────────────────────────────────────
# Only these emails can log into the portal. Add client emails here when ready
# to open access. This acts as a whitelist on top of Supabase Auth.

def _get_allowed_portal_emails() -> set:
    """Return the set of emails allowed to access the portal.

    Reads from PORTAL_ALLOWED_EMAILS env var (comma-separated) if set,
    otherwise defaults to the MCTV team.
    """
    env_val = os.environ.get("PORTAL_ALLOWED_EMAILS", "")
    if env_val.strip():
        return {e.strip().lower() for e in env_val.split(",") if e.strip()}
    # Default: team only
    return {
        "creed@mctvofms.com",
        "mmc@mctvofms.com",
        "swayze@mctvofms.com",
    }


# ── Team Auth ───────────────────────────────────────────────────────────────

def check_team_auth() -> bool:
    """Check if a team user is authenticated. No UI rendering."""
    return bool(st.session_state.get("authenticated"))


def render_team_login_form():
    """Render the team password login form (no branding — caller handles that)."""
    st.markdown("#### Team Member Login")
    st.caption("Enter the shared team password to access internal tools.")

    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Log In", type="primary", width='stretch'):
        if not _check_rate_limit("team"):
            st.error("Too many failed attempts. Please wait 5 minutes before trying again.")
        else:
            correct = os.environ.get("APP_PASSWORD")
            if not correct:
                st.error("Team login is not configured. Contact an administrator.")
            elif password == correct:
                _reset_login_attempts("team")
                st.session_state["authenticated"] = True
                st.session_state["auth_mode"] = "team"
                st.rerun()
            else:
                _record_failed_login("team")
                st.error("Incorrect password. Please try again.")

    st.caption("Contact Creed if you need access.")


def team_logout():
    """Clear team session state."""
    st.session_state["authenticated"] = False
    st.session_state["auth_mode"] = None
    st.session_state.pop("login_mode", None)


def check_password() -> bool:
    """Legacy wrapper — keeps existing team page calls working unchanged.

    Shows login form if not authenticated, returns True/False.
    """
    if check_team_auth():
        return True

    # Show branding + login form for pages that call check_password() directly
    logo_path = Path(__file__).parent.parent / "assets" / "branding" / "mctv_logo.png"
    if logo_path.exists():
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.image(str(logo_path), width='stretch')

    st.markdown(
        '<div style="text-align: center; padding: 0.5rem 0 1rem 0;">'
        '<p style="color: #C5A55A; font-size: 1.1rem; margin: 0;">Indoor Digital Billboard Network</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        render_team_login_form()

    return False


# ── Portal Auth (Supabase-based) ────────────────────────────────────────────

def check_portal_auth() -> bool:
    """Check if a portal user is authenticated via Supabase Auth.

    Returns True if the user has an active portal session, False otherwise.
    Attempts to refresh the session if the token is nearing expiry.
    Does NOT display a login form — use portal_login page for that.
    """
    if not (st.session_state.get("portal_authenticated")
            and st.session_state.get("portal_user_id")):
        return False

    # Attempt token refresh if we have a refresh token
    _try_refresh_token()
    return True


def _try_refresh_token():
    """Silently refresh the Supabase access token if possible.

    Called on each auth check to keep the session alive.
    """
    refresh_token = st.session_state.get("portal_refresh_token", "")
    if not refresh_token:
        return

    # Only refresh once per 45 minutes (tokens last ~60 min)
    last_refresh = st.session_state.get("_last_token_refresh", 0)
    if time.time() - last_refresh < 2700:
        return

    try:
        from services.supabase_client import refresh_session
        result = refresh_session(refresh_token)
        if result:
            st.session_state["portal_access_token"] = result.get("access_token", "")
            st.session_state["portal_refresh_token"] = result.get("refresh_token", refresh_token)
            st.session_state["_last_token_refresh"] = time.time()
    except Exception as e:
        print(f"[auth] Token refresh failed (non-blocking): {e}")


def _set_portal_session(result: dict):
    """Set all portal session state from a successful auth result.

    Shared by portal_login (password) and portal_magic_link_callback (OTP).
    """
    st.session_state["portal_authenticated"] = True
    st.session_state["auth_mode"] = "portal"
    st.session_state["portal_user_id"] = result.get("user_id", "")
    st.session_state["portal_email"] = result.get("email", "")
    st.session_state["portal_full_name"] = result.get("full_name", "")
    st.session_state["portal_role"] = result.get("role", "advertiser")
    st.session_state["portal_access_token"] = result.get("access_token", "")
    st.session_state["portal_refresh_token"] = result.get("refresh_token", "")


def portal_login(email: str, password: str) -> dict | None:
    """Authenticate a portal user via Supabase email/password.

    Returns user info dict on success, None on failure.
    On success, also sets all necessary session state.
    Enforces the portal email allowlist.
    """
    # Check allowlist BEFORE hitting Supabase
    allowed = _get_allowed_portal_emails()
    if email.strip().lower() not in allowed:
        return None

    from services.supabase_client import sign_in

    result = sign_in(email, password)
    if not result:
        return None

    _set_portal_session(result)
    return result


def send_portal_magic_link(email: str) -> bool:
    """Send a magic link email to the given portal user.

    Checks the allowlist before sending. Returns True if the email was sent.
    """
    allowed = _get_allowed_portal_emails()
    if email.strip().lower() not in allowed:
        return False

    from services.supabase_client import send_magic_link
    return send_magic_link(email)


def portal_magic_link_callback(token_hash: str, otp_type: str = "magiclink") -> dict | None:
    """Handle the magic link or recovery callback from Supabase.

    Called when portal_login detects ?token_hash=xxx&type=magiclink (or recovery)
    in the URL query params. Exchanges the token for a session and sets state.

    Args:
        token_hash: The token_hash from the redirect URL query params.
        otp_type: "magiclink" for magic links, "recovery" for password resets.

    Returns user info dict on success, None on failure.
    """
    from services.supabase_client import verify_otp

    result = verify_otp(token_hash, otp_type)
    if not result:
        return None

    # Check allowlist
    email = result.get("email", "")
    allowed = _get_allowed_portal_emails()
    if email.strip().lower() not in allowed:
        # User authenticated but is not on the allowlist — sign them out
        from services.supabase_client import sign_out
        sign_out(result.get("access_token", ""))
        return None

    _set_portal_session(result)
    return result


def portal_logout():
    """Clear portal session state and sign out of Supabase."""
    from services.supabase_client import sign_out

    token = st.session_state.get("portal_access_token", "")
    if token:
        sign_out(token)

    # Clear all portal session keys
    for key in list(st.session_state.keys()):
        if key.startswith("portal_"):
            del st.session_state[key]

    st.session_state["auth_mode"] = None
    st.session_state.pop("login_mode", None)


def get_portal_user() -> dict:
    """Get the current portal user's info from session state.

    Returns dict with user_id, email, full_name, role.
    Returns empty dict if not authenticated.
    """
    if not check_portal_auth():
        return {}

    return {
        "user_id": st.session_state.get("portal_user_id", ""),
        "email": st.session_state.get("portal_email", ""),
        "full_name": st.session_state.get("portal_full_name", ""),
        "role": st.session_state.get("portal_role", "advertiser"),
    }


def get_portal_role() -> str:
    """Get the current portal user's role. Returns empty string if not logged in."""
    return st.session_state.get("portal_role", "")


def is_portal_advertiser() -> bool:
    """Check if current portal user is an advertiser."""
    return get_portal_role() == "advertiser"


def is_portal_host() -> bool:
    """Check if current portal user is a venue host."""
    return get_portal_role() == "host"


def require_portal_auth():
    """Redirect to landing page if not authenticated.

    Call this at the top of portal pages. If not authenticated,
    displays a message and stops page rendering.
    """
    if not check_portal_auth():
        st.warning("Please log in to access the client portal.")
        st.page_link("app.py", label="Go to Login", icon="\U0001F512")
        st.stop()


# ── Shared Portal Login Form ───────────────────────────────────────────────

def render_portal_login_form(context_title: str = "Client Portal",
                             context_subtitle: str = "View your contracts, invoices, and campaign performance"):
    """Render the Supabase email/password + magic link login form.

    Used by both app.py landing page and portal_login.py callback page.
    """
    from services.supabase_client import is_configured, reset_password

    if not is_configured():
        st.error("The client portal is not yet available. Please contact MCTV for access.")
        return

    # Recovery mode: Set New Password form
    if st.session_state.get("_recovery_mode"):
        from services.supabase_client import update_user_password

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
                    st.session_state.pop("_recovery_mode", None)
                    st.session_state.pop("_recovery_access_token", None)
                    st.success("Password updated! You can now log in with your new password.")
                    portal_logout()
                    st.rerun()
                else:
                    st.error("Failed to update password. The link may have expired.")

        if st.button("Cancel", width='stretch'):
            st.session_state.pop("_recovery_mode", None)
            st.session_state.pop("_recovery_access_token", None)
            portal_logout()
            st.rerun()
        return

    # Password reset request form
    if st.session_state.get("show_reset_form"):
        st.markdown("#### Reset Password")
        reset_email = st.text_input("Email Address", key="reset_email",
                                    placeholder="your@email.com")

        if st.button("Send Reset Link", type="primary", width='stretch'):
            if reset_email:
                # Check allowlist before sending reset email
                allowed = _get_allowed_portal_emails()
                if reset_email.strip().lower() not in allowed:
                    st.error("Could not send reset link. Please check your email address.")
                else:
                    with st.spinner("Sending reset link..."):
                        success = reset_password(reset_email)
                        if success:
                            st.success("Password reset link sent! Check your email.")
                        else:
                            st.error("Could not send reset link. Please check your email address.")
            else:
                st.error("Please enter your email address.")

        if st.button("Back to Login", width='stretch'):
            st.session_state["show_reset_form"] = False
            st.rerun()
        return

    # Main login form (password + magic link toggle)
    st.markdown("#### Log In")

    use_magic_link = st.toggle("Use email link instead of password",
                               key="use_magic_link",
                               help="We'll send a sign-in link to your email.")

    email = st.text_input("Email", key="portal_login_email",
                          placeholder="your@email.com")

    if use_magic_link:
        if st.button("Send Sign-In Link", type="primary", width='stretch'):
            if not email:
                st.error("Please enter your email address.")
            else:
                with st.spinner("Sending sign-in link..."):
                    success = send_portal_magic_link(email)
                if success:
                    st.success("Sign-in link sent! Check your email.")
                    st.info("Didn't get the email? Check your spam folder.")
                else:
                    st.error("Could not send sign-in link. Contact your MCTV representative.")
    else:
        password = st.text_input("Password", type="password",
                                 key="portal_login_password")

        if st.button("Log In", type="primary", width='stretch'):
            if not _check_rate_limit("portal"):
                st.error("Too many failed attempts. Please wait 5 minutes before trying again.")
            elif not email or not password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Signing in..."):
                    result = portal_login(email, password)
                    if result:
                        _reset_login_attempts("portal")
                        st.success(f"Welcome, {result.get('full_name', 'there')}!")
                        st.switch_page("pages/portal_dashboard.py")
                    else:
                        _record_failed_login("portal")
                        st.error("Invalid email or password. Please try again.")

    if st.button("Forgot Password?", width='stretch'):
        st.session_state["show_reset_form"] = True
        st.rerun()

    st.divider()
    st.caption("Don't have an account? Contact your MCTV representative to get set up.")
