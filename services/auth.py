"""Simple shared password authentication for MCTV Bot."""

import streamlit as st
import os
from pathlib import Path


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
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")

        st.caption("Contact Creed if you need access.")

    return False
