# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Public, token-gated NPS survey page.

Reached via ``?token=<uuid>`` in the email. No login. Submits once and
shows a thank-you. Also surfaces the new shareable survey URL only — never
links back to the wider portal so a recipient who doesn't have an account
isn't pushed to log in.
"""

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.nps_service import find_survey_by_token, submit_response
from services.portal_service import get_client

st.set_page_config(
    page_title="Quick MCTV Check-In",
    page_icon="\U0001F4DD",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    #MainMenu, footer { visibility: hidden; }
    .block-container { max-width: 720px; padding-top: 2rem; }
    .nps-hero {
        background: #1B1F3B; color: white; padding: 1.6rem; border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .nps-hero h1 { color: #C5A55A; margin: 0; font-size: 1.4rem; }
    .nps-hero p { color: #e8e8e8; margin: 0.4rem 0 0; }
</style>
""", unsafe_allow_html=True)


# ── Token gate ───────────────────────────────────────────────────────────────

token = st.query_params.get("token", "").strip()
if not token:
    st.error("This survey link is missing or invalid.")
    st.stop()

survey = find_survey_by_token(token)
if not survey:
    st.error("This survey link has expired or was never valid. Thanks for clicking — no further action needed.")
    st.stop()

client = get_client(survey.get("client_id", "")) or {}
business = client.get("business_name", "your business")

milestone_label = {
    "30d": "first 30 days",
    "90d": "first 90 days",
    "180d": "first 6 months",
}.get(survey.get("milestone"), "")


# ── Already responded? ───────────────────────────────────────────────────────

if survey.get("responded_at"):
    st.markdown(f"""
    <div class="nps-hero">
        <h1>Thanks again!</h1>
        <p>We already have your answer — no need to submit twice.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Hero ─────────────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="nps-hero">
    <p style="color:#C5A55A; font-size:0.85rem; letter-spacing:2px; margin:0;">MCTV ELITE ADVERTISING</p>
    <h1>Quick check-in for {business}</h1>
    <p>You've been with MCTV for your {milestone_label}. Two minutes of feedback
    helps us run a better network.</p>
</div>
""", unsafe_allow_html=True)


# ── Form ─────────────────────────────────────────────────────────────────────

st.markdown("**On a scale of 0 to 10, how likely are you to recommend MCTV to "
             "another business owner?**")
score = st.slider("0 = not at all  ·  10 = absolutely",
                   min_value=0, max_value=10, value=8, key="nps_score")

st.markdown(" ")  # spacing
what_working = st.text_area(
    "What's working well?",
    placeholder="Specific results, venues, screens, our team — anything that's clicking.",
    height=110,
)
what_not_working = st.text_area(
    "What could be better?",
    placeholder="No filter — what would make MCTV more valuable to you?",
    height=110,
)
open_to_referrals = st.checkbox(
    "I'd be happy to refer another business owner to MCTV.",
)

st.markdown(" ")
if st.button("Submit feedback", type="primary", width="stretch"):
    with st.spinner("Saving..."):
        result = submit_response(
            token=token,
            score=score,
            what_working=what_working,
            what_not_working=what_not_working,
            open_to_referrals=open_to_referrals,
        )
    if not result:
        st.error("Something went wrong. Please email creed@mctvofms.com — we still want your feedback.")
    else:
        st.success("Got it — thanks for taking the time. We read every response.")
        st.balloons()
        st.markdown(
            "If you marked yourself open to referrals, your MCTV rep will follow "
            "up with a referral link you can share with other businesses."
        )

st.markdown(
    '<div style="text-align:center; color:#888; font-size:0.85rem; padding:2rem 0 0;">'
    'MCTV Elite Advertising · Oxford · Starkville · Tupelo<br>'
    '&copy; 2026 MCTV Digital, Inc.'
    '</div>',
    unsafe_allow_html=True,
)
