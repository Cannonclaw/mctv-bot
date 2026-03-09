# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Client portal contract page — view, download, and e-sign contracts."""

import logging
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import require_portal_auth, get_portal_user
from services.contract_service import (
    get_contracts_for_client, record_contract_view,
    sign_contract, get_contract_download_url, update_contract,
)
from services.portal_ui import inject_portal_css, render_portal_sidebar, render_portal_footer, load_portal_client

st.set_page_config(
    page_title="My Contract - MCTV Client Portal",
    page_icon="\U0001F4DD",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Signature box CSS (page-specific)
st.markdown("""
<style>
    .signature-box {
        border: 2px solid #C5A55A;
        border-radius: 8px;
        padding: 1.5rem;
        background-color: #FAFAF5;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

inject_portal_css()
require_portal_auth()

user = get_portal_user()
render_portal_sidebar(user)
client = load_portal_client(user)

client_id = client.get("id", "")

try:
    contracts = get_contracts_for_client(client_id)
except Exception:
    st.error("Unable to load your contracts. Please try again later.")
    contracts = []

st.markdown("## My Contract")
st.caption(f"{client.get('business_name', '')} | Advertising Partnership")
st.divider()

if not contracts:
    st.info(
        "No contracts on file yet. Your MCTV representative will prepare your "
        "advertising agreement and you'll be able to review and sign it right here."
    )
    render_portal_footer()
    st.stop()


# ── Display each contract ──────────────────────────────────────────────────

for contract in contracts:
    cid = contract.get("id", "")
    title = contract.get("title", "Contract")
    cstatus = contract.get("status", "draft")
    tier = contract.get("tier_name", "")
    try:
        rate = float(contract.get("monthly_rate", 0))
    except (TypeError, ValueError):
        rate = 0.0
    screens = contract.get("screen_count", 0)
    term = contract.get("term_months", 0)
    markets = contract.get("markets", [])

    status_display = {
        "draft": ("Preparing", "\u270F\uFE0F"),
        "sent": ("Ready to Sign", "\U0001F4E8"),
        "viewed": ("Ready to Sign", "\U0001F4E8"),
        "signed": ("Signed", "\u2705"),
        "active": ("Active", "\U0001F7E2"),
        "expired": ("Expired", "\u23F0"),
        "cancelled": ("Cancelled", "\U0001F534"),
    }
    status_label, status_icon = status_display.get(cstatus, ("Unknown", "\u26AA"))

    st.markdown(f"### {status_icon} {title}")
    st.markdown(f"**Status: {status_label}**")

    det_col1, det_col2, det_col3 = st.columns(3)

    with det_col1:
        st.markdown("**Package**")
        st.text(f"Tier: {tier or 'Custom'}")
        st.text(f"Screens: {screens}")
        st.text(f"Monthly Rate: ${rate:,.2f}")

    with det_col2:
        st.markdown("**Term**")
        st.text(f"Length: {term} months")
        st.text(f"Start: {contract.get('start_date', 'TBD')}")
        st.text(f"End: {contract.get('end_date', 'TBD')}")
        st.text(f"Auto-Renew: {'Yes' if contract.get('auto_renew') else 'No'}")

    with det_col3:
        st.markdown("**Markets**")
        for market in (markets or ["Oxford"]):
            st.text(f"  {market}")

    # ── Download button ─────────────────────────────────────────────
    if contract.get("document_url"):
        st.divider()
        doc_url = contract.get("document_url", "")

        is_local_path = doc_url.startswith("/") or doc_url.startswith("C:") or doc_url.startswith("output")
        local_path = Path(doc_url) if is_local_path else None

        # Path traversal protection: ensure local path resolves inside output/
        if local_path:
            try:
                resolved = local_path.resolve()
                output_root = Path(__file__).parent.parent / "output"
                if not str(resolved).startswith(str(output_root.resolve())):
                    local_path = None
            except Exception:
                local_path = None

        if local_path and local_path.exists():
            with open(local_path, "rb") as f:
                st.download_button(
                    "Download Contract Document",
                    data=f.read(),
                    file_name=local_path.name,
                    key=f"dl_contract_{cid}",
                    type="primary",
                )
        else:
            try:
                download_url = get_contract_download_url(cid, client_id=client_id)
            except Exception:
                download_url = None

            if download_url:
                st.link_button(
                    "Download Contract Document",
                    url=download_url,
                    type="primary",
                )
            elif doc_url:
                st.caption("Contract document is being processed. Please check back shortly.")

    # ── Mark as viewed ──────────────────────────────────────────────
    if cstatus == "sent":
        try:
            record_contract_view(cid, client_id=client_id)
        except Exception as e:
            logger.warning("Failed to record contract view for %s: %s", cid, e)

    # ── TIER SELECTION (multi-option contracts) ─────────────────────
    tier_opts = contract.get("tier_options")
    chosen_tier = contract.get("selected_tier", "")
    needs_tier_selection = (
        tier_opts and isinstance(tier_opts, list) and len(tier_opts) >= 2
        and not chosen_tier
        and cstatus in ("sent", "viewed")
    )

    if needs_tier_selection:
        st.divider()
        st.markdown("### Select Your Package")
        st.markdown(
            "Your MCTV representative has prepared multiple package options "
            "for you. Please select the one that best fits your needs before signing."
        )

        tier_labels = []
        for i, opt in enumerate(tier_opts):
            name = opt.get("name", f"Option {i + 1}")
            scr = opt.get("screens", 0)
            rt = float(opt.get("rate", 0))
            tier_labels.append(f"{name} — {scr} Screens — ${rt:,.0f}/mo")

        tier_choice = st.radio(
            "Choose your package:",
            tier_labels,
            index=1 if len(tier_labels) > 2 else 0,
            key=f"tier_select_{cid}",
        )

        if st.button("Confirm Package Selection", key=f"confirm_tier_{cid}",
                      type="primary", use_container_width=True):
            # Extract the selected tier name
            idx = tier_labels.index(tier_choice)
            selected_opt = tier_opts[idx]
            sel_name = selected_opt.get("name", "")
            sel_screens = selected_opt.get("screens", 0)
            sel_rate = float(selected_opt.get("rate", 0))
            update_contract(cid, {
                "selected_tier": sel_name,
                "tier_name": sel_name,
                "screen_count": sel_screens,
                "monthly_rate": sel_rate,
            })
            st.success(f"Package **{sel_name}** selected! You can now sign below.")
            st.rerun()

    # ── SIGNATURE SECTION ───────────────────────────────────────────
    # Clear stale confirmation state so users must re-confirm each visit
    _confirm_key = f"sign_confirmed_{cid}"
    if _confirm_key not in st.session_state:
        pass  # fresh visit, nothing to clear
    elif st.session_state.get(f"_sign_page_loaded_{cid}") is None:
        # First render this session — reset confirmation
        st.session_state[_confirm_key] = False
    st.session_state[f"_sign_page_loaded_{cid}"] = True

    if cstatus in ("sent", "viewed") and not needs_tier_selection:
        st.divider()
        st.markdown("### Sign Your Contract")

        st.markdown(
            """
            <div class="signature-box">
                <p style="font-size: 1rem; color: #333;">
                    By typing your full name below and clicking "I Agree & Sign",
                    you acknowledge that you have read and agree to all terms and
                    conditions in this advertising agreement.
                </p>
                <p style="font-size: 0.85rem; color: #666;">
                    Your electronic signature is legally binding under the Mississippi
                    Uniform Electronic Transactions Act. We will record your name,
                    the date/time, and your IP address for our records.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sign_col1, sign_col2 = st.columns([2, 1])

        with sign_col1:
            typed_name = st.text_input(
                "Type your full legal name to sign",
                key=f"sign_name_{cid}",
                placeholder="e.g., John A. Smith",
            )

        with sign_col2:
            st.markdown(f"**Date:** {datetime.now().strftime('%B %d, %Y')}")
            st.markdown(f"**Signing as:** {user.get('full_name', '')}")

        # Name validation warning
        user_full_name = user.get("full_name", "").strip()
        name_mismatch = (typed_name and user_full_name
                         and typed_name.strip().lower() != user_full_name.lower())
        if name_mismatch:
            st.warning(
                f"The name you typed does not match your account name "
                f"(**{user_full_name}**). Please ensure you are typing your full legal name."
            )

        agree = st.checkbox(
            "I have read the full contract and agree to all terms and conditions",
            key=f"sign_agree_{cid}",
        )

        # Two-step confirmation
        confirm_key = f"sign_confirmed_{cid}"
        if st.session_state.get(confirm_key):
            st.info("Click **Confirm Signature** below to finalize. This is legally binding.")

        if not st.session_state.get(confirm_key):
            if st.button("I Agree & Sign", key=f"sign_btn_{cid}", type="primary",
                          width='stretch', disabled=not (typed_name and agree)):
                if not typed_name:
                    st.error("Please type your full name to sign.")
                elif not agree:
                    st.error("Please check the agreement box to proceed.")
                else:
                    st.session_state[confirm_key] = True
                    st.rerun()
        else:
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                do_sign = st.button("Confirm Signature", key=f"confirm_sign_{cid}",
                                    type="primary", width='stretch')
            with col_cancel:
                if st.button("Cancel", key=f"cancel_sign_{cid}", width='stretch'):
                    st.session_state[confirm_key] = False
                    st.rerun()

            if do_sign:
                with st.spinner("Recording your signature..."):
                    try:
                        # Capture client IP from request headers
                        client_ip = ""
                        try:
                            headers = st.context.headers
                            client_ip = (headers.get("X-Forwarded-For", "").split(",")[0].strip()
                                         or headers.get("X-Real-Ip", "")
                                         or headers.get("Remote-Addr", ""))
                        except Exception:
                            pass

                        result = sign_contract(
                            contract_id=cid,
                            signed_by=typed_name,
                            ip_address=client_ip,
                            user_agent="MCTV Client Portal (Streamlit)",
                            user_id=user.get("user_id", ""),
                            client_id=client_id,
                        )
                        if result:
                            st.session_state[confirm_key] = False
                            st.success("Contract signed successfully! Thank you.")
                            st.balloons()
                            st.info(
                                "Your MCTV team has been notified. You'll receive a "
                                "confirmation email shortly."
                            )
                            st.rerun()
                        else:
                            st.session_state[confirm_key] = False
                            st.error(
                                "Something went wrong recording your signature. "
                                "Please try again or contact your MCTV representative."
                            )
                    except Exception as e:
                        st.session_state[confirm_key] = False
                        print(f"[portal_contract] Sign error: {e}")
                        st.error("Something went wrong. Please try again or contact MCTV.")

    elif cstatus in ("signed", "active"):
        st.divider()
        st.success("This contract has been signed and is on file.")
        if contract.get("signed_by"):
            st.text(f"Signed by: {contract.get('signed_by')}")
            signed_at = contract.get("signed_at", "")
            if signed_at:
                st.text(f"Signed on: {signed_at[:16]}")

    elif cstatus == "draft":
        st.divider()
        st.info("This contract is being prepared by your MCTV representative. You'll be notified when it's ready to sign.")

    st.divider()

render_portal_footer()
