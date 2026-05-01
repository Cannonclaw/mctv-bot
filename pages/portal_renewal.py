# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Public, token-gated one-click renewal page.

Loaded via ``?token=<uuid>``. Shows the client a summary of their current
contract + recent traction + a single button to renew. Accepting kicks off
the standard contract draft -> sign workflow.
"""

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.contract_service import (
    accept_renewal_offer,
    find_contract_by_renewal_token,
)
from services.portal_service import get_client

st.set_page_config(
    page_title="Renew Your MCTV Contract",
    page_icon="\U0001F4FA",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    #MainMenu, footer { visibility: hidden; }
    .block-container { max-width: 800px; padding-top: 2rem; }
    .renewal-hero {
        background: #1B1F3B; color: white; padding: 2rem; border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .renewal-hero h1 { color: #C5A55A; margin: 0; font-size: 1.6rem; }
</style>
""", unsafe_allow_html=True)


# ── Token gate ───────────────────────────────────────────────────────────────

token = st.query_params.get("token", "").strip()
if not token:
    st.error("This link is missing or invalid.")
    st.stop()

contract = find_contract_by_renewal_token(token)
if not contract:
    st.error("This renewal link has expired or was never valid. Please contact your MCTV representative.")
    st.stop()

client = get_client(contract.get("client_id", "")) or {}
biz = client.get("business_name", "your business")


# ── Already accepted? ────────────────────────────────────────────────────────

if contract.get("renewal_accepted_at"):
    st.markdown(f"""
    <div class="renewal-hero">
        <h1>Renewal Already in Motion</h1>
        <p style="color:#e8e8e8; margin:0.4rem 0 0;">
            Thanks, {biz}! Your renewal was accepted on
            {contract['renewal_accepted_at'][:10]}. Your MCTV rep is preparing
            the paperwork and will be in touch shortly.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Hero ─────────────────────────────────────────────────────────────────────

end_date = contract.get("end_date", "")
days_left = ""
if end_date:
    try:
        delta = (datetime.fromisoformat(end_date).date() - datetime.now().date()).days
        days_left = f"{delta} days remaining"
    except Exception:
        pass

st.markdown(f"""
<div class="renewal-hero">
    <p style="color:#C5A55A; font-size:0.85rem; letter-spacing:2px; margin:0;">MCTV ELITE ADVERTISING</p>
    <h1>Renew with MCTV, {biz}</h1>
    <p style="color:#e8e8e8; margin:0.4rem 0 0;">
        Your contract ends {end_date or 'soon'}{' — ' + days_left if days_left else ''}.
        Keep your ads running with one click.
    </p>
</div>
""", unsafe_allow_html=True)


# ── Current contract summary ─────────────────────────────────────────────────

st.markdown("### Your Current Plan")
m1, m2, m3 = st.columns(3)
m1.metric("Tier", contract.get("tier_name", "Custom"))
m2.metric("Screens", contract.get("screen_count", 0))
m3.metric("Monthly Rate", f"${float(contract.get('monthly_rate', 0) or 0):,.0f}")

markets = contract.get("markets") or []
if markets:
    st.caption(f"Markets: {', '.join(markets)}")


# ── Term selector ────────────────────────────────────────────────────────────

st.markdown("### Choose Your Renewal Term")
default_term = int(contract.get("term_months", 12) or 12)
term = st.radio(
    "Term length",
    options=[6, 12],
    index=1 if default_term >= 12 else 0,
    horizontal=True,
    format_func=lambda m: f"{m} months" + (" (recommended)" if m == 12 else ""),
)

if term == 12:
    st.success(
        "Lock in 12 months and we'll prepay-bonus you a 13th month free if "
        "you choose to pay upfront. Talk to your rep about details."
    )

st.divider()


# ── Accept ───────────────────────────────────────────────────────────────────

st.markdown("### Renew My Contract")
st.caption(
    "Clicking below creates a new draft contract with the same terms, starting "
    "the day after your current contract ends. Your MCTV rep will email it to "
    "you for signature within 1 business day."
)

if st.button("Renew for " + str(term) + " months", type="primary", width="stretch"):
    with st.spinner("Locking in your renewal..."):
        new_draft = accept_renewal_offer(token, term_months=term)
    if not new_draft:
        st.error("Something went wrong. Please contact your MCTV representative.")
    else:
        st.success(
            "Renewal accepted! Your MCTV rep has been notified and will send "
            "the new contract to you for signature within 1 business day."
        )
        st.balloons()
        st.markdown(f"**New start date:** {new_draft.get('start_date', '')}")
        st.markdown(f"**Term:** {new_draft.get('term_months', term)} months")

st.markdown(
    '<div style="text-align:center; color:#888; font-size:0.85rem; padding:2rem 0 0;">'
    '<p>MCTV Elite Advertising | Oxford | Starkville | Tupelo</p>'
    '<p>www.mctvofms.com | &copy; 2026 MCTV Digital, Inc.</p>'
    '</div>',
    unsafe_allow_html=True,
)
