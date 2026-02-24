"""Dual-mode authentication for MCTV Bot.

Supports two parallel auth paths:
1. Team login: Shared password (APP_PASSWORD) for internal tools
2. Portal login: Supabase Auth (email/password) for client portal

Both modes use st.session_state to track auth state. The two paths
never interfere — a team login doesn't affect portal auth and vice versa.
"""

import streamlit as st
import os
from pathlib import Path


# ── Team Auth (existing pattern — unchanged behavior) ───────────────────────

def check_password() -> bool:
    """Display a login gate if the user is not yet authenticated.

    Returns True if authenticated, False otherwise.
    Call st.stop() after this returns False to prevent page content from rendering.
    """
    # Already logged in this session
    if st.session_state.get("authenticated"):
        return True

    # MCTV Logo
    logo_path = Path(__file__).parent.parent / "assets" / "branding" / "mctv_logo.png"
    if logo_path.exists():
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.image(str(logo_path), use_container_width=True)

    st.markdown(
        """
        <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
            <p style="color: #C5A55A; font-size: 1.1rem; margin: 0;">Indoor Digital Billboard Network</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("#### Team Login")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Log In", type="primary", use_container_width=True):
            correct = os.environ.get("APP_PASSWORD", "mctv2026")
            if password == correct:
                st.session_state["authenticated"] = True
                st.session_state["auth_mode"] = "team"
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")

        st.caption("Contact Creed if you need access.")

    return False


# ── Portal Auth (Supabase-based) ────────────────────────────────────────────

def check_portal_auth() -> bool:
    """Check if a portal user is authenticated via Supabase Auth.

    Returns True if the user has an active portal session, False otherwise.
    Does NOT display a login form — use portal_login page for that.
    """
    return bool(
        st.session_state.get("portal_authenticated")
        and st.session_state.get("portal_user_id")
    )


def portal_login(email: str, password: str) -> dict | None:
    """Authenticate a portal user via Supabase.

    Returns user info dict on success, None on failure.
    On success, also sets all necessary session state.
    """
    from services.supabase_client import sign_in

    result = sign_in(email, password)
    if not result:
        return None

    # Set portal session state
    st.session_state["portal_authenticated"] = True
    st.session_state["auth_mode"] = "portal"
    st.session_state["portal_user_id"] = result.get("user_id", "")
    st.session_state["portal_email"] = result.get("email", "")
    st.session_state["portal_full_name"] = result.get("full_name", "")
    st.session_state["portal_role"] = result.get("role", "advertiser")
    st.session_state["portal_access_token"] = result.get("access_token", "")
    st.session_state["portal_refresh_token"] = result.get("refresh_token", "")

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
    """Redirect to portal login if not authenticated.

    Call this at the top of portal pages. If not authenticated,
    displays a message and stops page rendering.
    """
    if not check_portal_auth():
        st.warning("Please log in to access the client portal.")
        st.page_link("pages/portal_login.py", label="Go to Login", icon="\U0001F512")
        st.stop()
