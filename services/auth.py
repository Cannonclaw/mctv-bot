"""Simple shared password authentication for MCTV Bot."""

import streamlit as st
import os


def check_password() -> bool:
    """Display a login gate if the user is not yet authenticated.

    Returns True if authenticated, False otherwise.
    Call st.stop() after this returns False to prevent page content from rendering.
    """
    # Already logged in this session
    if st.session_state.get("authenticated"):
        return True

    # Login form
    st.markdown(
        """
        <div style="text-align: center; padding: 2rem 0;">
            <h1 style="color: #1B1F3B; font-size: 2.5rem;">MCTV Elite Advertising</h1>
            <p style="color: #C5A55A; font-size: 1.1rem;">Indoor Digital Billboard Network</p>
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
