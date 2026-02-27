# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Portal login — callback handler for magic links and password resets.

The main login UI now lives on the unified landing page (app.py).
This page handles Supabase auth redirects that arrive with query params:
  ?token_hash=xxx&type=magiclink   — passwordless login callback
  ?token_hash=xxx&type=recovery    — password reset callback

Normal visits (no callback) are redirected to app.py.

Supabase Dashboard requirements (Auth > URL Configuration):
- Site URL: https://bot.mctvofms.com
- Redirect URLs: https://bot.mctvofms.com/portal_login
  (also add http://localhost:8501/portal_login for local dev)
"""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import (
    check_portal_auth, portal_magic_link_callback,
)

st.set_page_config(
    page_title="Client Portal - MCTV Elite Advertising",
    page_icon="\U0001F4FA",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Hide sidebar
st.markdown('<style>[data-testid="stSidebar"]{display:none;}</style>', unsafe_allow_html=True)


# ── Magic Link / Recovery Callback Handler ─────────────────────────────────

_token_hash = st.query_params.get("token_hash", "")
_auth_type = st.query_params.get("type", "")

if _token_hash and _auth_type in ("magiclink", "recovery"):
    # Clear params immediately so they don't fire again on refresh
    st.query_params.clear()

    if _auth_type == "recovery":
        with st.spinner("Verifying reset link..."):
            result = portal_magic_link_callback(_token_hash, otp_type="recovery")

        if result:
            st.session_state["_recovery_mode"] = True
            st.session_state["_recovery_access_token"] = result.get("access_token", "")
            # Send to landing page which will show the password reset form
            st.session_state["login_mode"] = "portal_advertiser"
            st.switch_page("app.py")
        else:
            st.error("This reset link has expired or is invalid. Please request a new one.")
            st.stop()
    else:
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


# ── Already authenticated? Go to dashboard ─────────────────────────────────

if check_portal_auth() and not st.session_state.get("_recovery_mode"):
    st.switch_page("pages/portal_dashboard.py")


# ── Normal visit (no callback) — redirect to unified landing page ──────────

st.switch_page("app.py")
