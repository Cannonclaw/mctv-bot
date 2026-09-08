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
from dotenv import load_dotenv

# Ensure .env is loaded — auth.py may be imported before app.py's load_dotenv runs
load_dotenv(Path(__file__).parent.parent / ".env", override=False)


# ── Login Rate Limiting ────────────────────────────────────────────────────
# Attempts are recorded server-side in portal_login_attempts (migration 024) so
# the limit survives a new tab or a cleared cookie jar. The session_state
# counters are kept as a second layer and as the fallback when the DB is
# unreachable — a database hiccup must not lock everyone out of the app.
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_LOCKOUT_SECONDS = 300  # 5 minutes


def get_client_ip() -> str:
    """Best-effort client IP from the proxy headers Render sets.

    Shared by the auth paths and the portal audit log so every record is
    attributable. Returns "" when headers are unavailable.
    """
    try:
        headers = getattr(st.context, "headers", {}) or {}
        return (
            headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or headers.get("X-Real-Ip", "")
            or headers.get("Remote-Addr", "")
            or ""
        )
    except Exception:
        return ""


# Credential checks are limited by *consecutive failures* — a correct password
# clears the streak. Send actions (magic link, password reset) are limited by
# *total volume*, since every send is a real outbound email whether or not the
# address was valid.
_VOLUME_LIMITED_KINDS = ("magic_link", "reset")


def log_portal_event(action: str, entity_type: str = "", entity_id: str = "",
                     details: dict | None = None):
    """Write a portal audit record for the current session.

    Fills in the acting user, their client, and the originating IP from session
    state so call sites only supply the action. Never raises — an audit write
    failing must not break the page the user is on.
    """
    try:
        from services.portal_service import log_activity

        log_activity(
            client_id=st.session_state.get("_portal_client_id", "") or "",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=st.session_state.get("portal_user_id", "") or "",
            details=details,
            ip_address=get_client_ip(),
        )
    except Exception as e:
        print(f"[auth] Audit log write failed (non-blocking): {e}")


def _db_attempt_count(key: str, kind: str) -> int | None:
    """Count attempts for ``key`` inside the lockout window.

    For volume-limited kinds this counts every attempt; otherwise it counts the
    current run of failures. Returns None if the attempt log is unavailable, so
    callers fall back to the in-session counter rather than failing closed.
    """
    try:
        from services.supabase_client import query_table

        rows = query_table(
            "portal_login_attempts",
            select="succeeded,created_at",
            filters={"attempt_key": key.strip().lower(), "kind": kind},
            order="-created_at",
            limit=_LOGIN_MAX_ATTEMPTS,
        )
    except Exception as e:
        print(f"[auth] Rate-limit lookup unavailable: {e}")
        return None

    if rows is None:
        return None

    from datetime import datetime as _dt

    count_all = kind in _VOLUME_LIMITED_KINDS
    cutoff = time.time() - _LOGIN_LOCKOUT_SECONDS
    count = 0
    for row in rows:
        # For credential checks, a success inside the window clears the streak.
        if not count_all and row.get("succeeded"):
            break
        try:
            when = _dt.fromisoformat(
                str(row.get("created_at", "")).replace("Z", "+00:00")
            ).timestamp()
        except Exception:
            continue
        if when >= cutoff:
            count += 1

    return count


def _record_attempt(key: str, kind: str, succeeded: bool):
    """Append an auth attempt to the server-side log. Never raises."""
    try:
        from services.supabase_client import insert_row

        insert_row("portal_login_attempts", {
            "attempt_key": key.strip().lower(),
            "kind": kind,
            "succeeded": succeeded,
            "ip_address": get_client_ip(),
        })
    except Exception as e:
        print(f"[auth] Could not record login attempt: {e}")


def _check_rate_limit(key: str, kind: str = "password") -> bool:
    """Return True if the login attempt is allowed, False if locked out."""
    db_attempts = _db_attempt_count(key, kind)
    if db_attempts is not None and db_attempts >= _LOGIN_MAX_ATTEMPTS:
        return False

    lockout_until = st.session_state.get(f"_login_lockout_{key}", 0)

    if lockout_until and time.time() < lockout_until:
        return False

    if lockout_until and time.time() >= lockout_until:
        st.session_state[f"_login_attempts_{key}"] = 0
        st.session_state[f"_login_lockout_{key}"] = 0

    return True


def _record_failed_login(key: str, kind: str = "password"):
    """Record a failed login attempt and lock out if threshold reached."""
    attempts = st.session_state.get(f"_login_attempts_{key}", 0) + 1
    st.session_state[f"_login_attempts_{key}"] = attempts

    if attempts >= _LOGIN_MAX_ATTEMPTS:
        st.session_state[f"_login_lockout_{key}"] = time.time() + _LOGIN_LOCKOUT_SECONDS

    _record_attempt(key, kind, succeeded=False)


def _reset_login_attempts(key: str, kind: str = "password"):
    """Reset login attempt counter after successful login."""
    st.session_state.pop(f"_login_attempts_{key}", None)
    st.session_state.pop(f"_login_lockout_{key}", None)
    _record_attempt(key, kind, succeeded=True)


# ── Portal Access Control ───────────────────────────────────────────────────
# Only these emails can log into the portal. Add client emails here when ready
# to open access. This acts as a whitelist on top of Supabase Auth.

def _get_allowed_portal_emails() -> set:
    """Return the set of emails allowed to access the portal.

    The MCTV team is always allowed. PORTAL_ALLOWED_EMAILS (comma-separated)
    *adds* to that set — it does not replace it, or setting the env var would
    silently lock the team out of their own portal. On top of that, every client
    that has been invited to the portal (i.e. has a portal_user_id) is allowed —
    otherwise a created advertiser/host account can never log in even though
    its Supabase Auth user exists and its temp password was emailed.
    """
    emails = {
        "creed@mctvofms.com",
        "mmc@mctvofms.com",
        "swayze@mctvofms.com",
    }

    env_val = os.environ.get("PORTAL_ALLOWED_EMAILS", "")
    if env_val.strip():
        emails |= {e.strip().lower() for e in env_val.split(",") if e.strip()}

    # Add every client that has an active portal account.
    try:
        from services.supabase_client import query_table

        rows = query_table("clients", select="contact_email,portal_user_id") or []
        for row in rows:
            if row.get("portal_user_id") and row.get("contact_email"):
                emails.add(row["contact_email"].strip().lower())
    except Exception as e:  # fail safe — never lock out the team on a DB hiccup
        print(f"[auth] Could not load portal client emails: {e}")

    return emails


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
        # Shared password, so the limit is keyed by source IP.
        rate_key = f"team:{get_client_ip() or 'unknown'}"
        if not _check_rate_limit(rate_key, kind="team"):
            st.error("Too many failed attempts. Please wait 5 minutes before trying again.")
        else:
            correct = os.environ.get("APP_PASSWORD")
            if not correct:
                st.error("Team login is not configured. Contact an administrator.")
            elif password == correct:
                _reset_login_attempts(rate_key, kind="team")
                st.session_state["authenticated"] = True
                st.session_state["auth_mode"] = "team"
                st.rerun()
            else:
                _record_failed_login(rate_key, kind="team")
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

    # A revoked or expired grant must end a *live* session, not just block the
    # next login. Checked here because every portal page reaches this function.
    if _portal_access_expired():
        portal_logout()
        return False

    # Attempt token refresh if we have a refresh token
    _try_refresh_token()
    return True


_ACCESS_CHECK_INTERVAL = 60  # seconds — this runs on every Streamlit rerun


def _portal_access_expired() -> bool:
    """True if this account's portal_access_expires_at has passed.

    Result is cached for ``_ACCESS_CHECK_INTERVAL`` so a DB round trip doesn't
    happen on every rerun. Fails open on lookup errors — an outage should not
    log real clients out.
    """
    from datetime import datetime as _dt

    last_check = st.session_state.get("_access_check_at", 0)
    if time.time() - last_check < _ACCESS_CHECK_INTERVAL:
        return bool(st.session_state.get("_access_expired", False))

    st.session_state["_access_check_at"] = time.time()

    user_id = st.session_state.get("portal_user_id", "")
    if not user_id:
        return False

    try:
        from services.supabase_client import query_table

        rows = query_table(
            "clients",
            select="portal_access_expires_at",
            filters={"portal_user_id": user_id},
        ) or []
    except Exception as e:
        print(f"[auth] Access-expiry lookup failed (non-blocking): {e}")
        st.session_state["_access_expired"] = False
        return False

    expired = False
    for row in rows:
        raw = row.get("portal_access_expires_at")
        if not raw:
            continue
        try:
            when = _dt.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            continue
        if when.timestamp() <= time.time():
            expired = True
            break

    st.session_state["_access_expired"] = expired
    return expired


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
    log_portal_event("portal_login", details={"method": "password"})
    return result


def send_portal_magic_link(email: str) -> bool:
    """Send a magic link email to the given portal user.

    Checks the allowlist and the send rate limit before sending.
    Returns True if the email was sent.
    """
    allowed = _get_allowed_portal_emails()
    if email.strip().lower() not in allowed:
        return False

    # Without this, the send endpoint is an unmetered outbound email trigger.
    if not _check_rate_limit(email, kind="magic_link"):
        return False

    from services.supabase_client import send_magic_link

    sent = send_magic_link(email)
    _record_attempt(email, "magic_link", succeeded=sent)
    return sent


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
    log_portal_event("portal_login", details={"method": otp_type})
    return result


def portal_logout():
    """Clear portal session state and sign out of Supabase."""
    from services.supabase_client import sign_out
    from services.partner_access import clear_access

    # Log before the session keys are cleared — afterwards there is no identity.
    log_portal_event("portal_logout")

    token = st.session_state.get("portal_access_token", "")
    if token:
        sign_out(token)

    # Clear all portal session keys
    for key in list(st.session_state.keys()):
        if key.startswith("portal_"):
            del st.session_state[key]

    clear_access()
    st.session_state.pop("_portal_client_id", None)
    st.session_state.pop("_access_check_at", None)
    st.session_state.pop("_access_expired", None)
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


def is_portal_partner() -> bool:
    """Check if current portal user holds read-only partner evaluation access."""
    return get_portal_role() == "partner"


def require_portal_auth(allowed_roles: tuple[str, ...] | None = None):
    """Stop the page unless a portal user is authenticated.

    Call this at the top of portal pages. If not authenticated, displays a
    message and stops page rendering.

    Args:
        allowed_roles: Optional tuple of roles permitted on this page. When
            given, a logged-in user whose role is not listed is stopped. Use it
            to keep read-only partner accounts off pages that only make sense
            for a real client.
    """
    if not check_portal_auth():
        st.warning("Please log in to access the client portal.")
        st.page_link("app.py", label="Go to Login", icon="\U0001F512")
        st.stop()

    if allowed_roles and get_portal_role() not in allowed_roles:
        st.warning("This page isn't available for your account.")
        st.page_link("pages/portal_dashboard.py", label="Back to Dashboard", icon="\U0001F3E0")
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
                elif not _check_rate_limit(reset_email, kind="reset"):
                    st.error("Too many reset requests. Please wait a few minutes and try again.")
                else:
                    with st.spinner("Sending reset link..."):
                        success = reset_password(reset_email)
                        _record_attempt(reset_email, "reset", succeeded=success)
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
            # Keyed by email so one attacker can't lock out the whole portal.
            rate_key = (email or "").strip().lower() or "portal"
            if not email or not password:
                st.error("Please enter both email and password.")
            elif not _check_rate_limit(rate_key, kind="password"):
                st.error("Too many failed attempts. Please wait 5 minutes before trying again.")
            else:
                with st.spinner("Signing in..."):
                    result = portal_login(email, password)
                    if result:
                        _reset_login_attempts(rate_key, kind="password")
                        st.success(f"Welcome, {result.get('full_name', 'there')}!")
                        st.switch_page("pages/portal_dashboard.py")
                    else:
                        _record_failed_login(rate_key, kind="password")
                        st.error("Invalid email or password. Please try again.")

    if st.button("Forgot Password?", width='stretch'):
        st.session_state["show_reset_form"] = True
        st.rerun()

    st.divider()
    st.caption("Don't have an account? Contact your MCTV representative to get set up.")
