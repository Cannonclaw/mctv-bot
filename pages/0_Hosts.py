# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Public Host Application Form.

Prospective venues fill this out to apply to host MCTV screens. Submissions
land directly in the Host Acquisition Pipeline (pipeline_opportunities,
deal_type='host', stage='identified').
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.config_service import load_config, get_market_names
from services.supabase_client import insert_row

st.set_page_config(
    page_title="Host MCTV Screens at Your Venue",
    page_icon="\U0001F4FA",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { max-width: 720px; padding-top: 1.5rem; }
</style>

<!-- iframe auto-resize for WordPress embedding -->
<script>
(function() {
    if (window.parent === window) return;
    var lastHeight = 0;
    function sendHeight() {
        var h = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
        if (h !== lastHeight) {
            lastHeight = h;
            window.parent.postMessage({type: 'streamlit:height', height: h}, '*');
        }
    }
    sendHeight();
    window.addEventListener('load', sendHeight);
    window.addEventListener('resize', sendHeight);
    setInterval(sendHeight, 1000);
    if (window.MutationObserver) {
        new MutationObserver(sendHeight).observe(document.body,
            {childList: true, subtree: true, attributes: true});
    }
})();
</script>
""", unsafe_allow_html=True)


# ── Branded header ───────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center; padding:1.2rem 0 0.5rem;">
    <h1 style="color:#1B1F3B; font-size:2.0rem; margin-bottom:0;">Host MCTV at Your Venue</h1>
    <p style="color:#C5A55A; font-size:1.05rem; margin-top:0.2rem;">
        Free screens, free advertising, captive audience.
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()


# ── Already submitted? ───────────────────────────────────────────────────────

if st.session_state.get("host_app_submitted"):
    st.markdown("""
    <div style="text-align:center; padding:2.5rem 0;">
        <h2 style="color:#1B1F3B;">Thanks — we got your application.</h2>
        <p style="color:#666; font-size:1.05rem;">
            A member of our team will reach out within 2 business days to walk
            through next steps. We typically install screens within 30 days
            of an approved partnership.
        </p>
        <p style="color:#C5A55A; font-size:1rem; margin-top:1.5rem;">
            <a href="https://www.mctvofms.com" target="_blank" style="color:#C5A55A;">mctvofms.com</a>
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Why host (sales copy) ────────────────────────────────────────────────────

st.markdown("""
**Why MCTV hosts love the deal:**

- **Free screens.** We supply, install, and maintain everything.
- **Free advertising for your business.** Run your own ads in the rotation.
- **No content to manage.** We handle creative, scheduling, and updates.
- **Make your venue more vibrant.** Premium screens elevate the customer
  experience.

We're looking for venues with steady foot traffic across Oxford, Starkville,
Tupelo, and growing markets. Restaurants, salons, gyms, medical offices,
retail, and entertainment venues all work.
""")

st.divider()
st.markdown("#### Tell us about your venue")


# ── Form ─────────────────────────────────────────────────────────────────────

col1, col2 = st.columns(2)
with col1:
    business_name = st.text_input("Venue / Business Name *", placeholder="The Local Pour")
    contact_name = st.text_input("Your Name *", placeholder="First and Last")
    contact_email = st.text_input("Email Address *", placeholder="you@yourvenue.com")
with col2:
    contact_phone = st.text_input("Phone *", placeholder="(555) 555-5555")
    industry = st.text_input(
        "Venue Type *",
        placeholder="Restaurant, Bar, Salon, Gym, Medical, Retail...",
    )
    cfg = load_config()
    market = st.selectbox(
        "Market",
        get_market_names(cfg, active_only=False) + ["Other"],
        index=0,
    )

if market == "Other":
    market = st.text_input("Your City *", placeholder="City, State")

street_address = st.text_input(
    "Street Address",
    placeholder="123 Main St, Oxford, MS 38655",
)

st.markdown("#### About the foot traffic")

ft_col1, ft_col2 = st.columns(2)
visitors = ft_col1.selectbox(
    "Approx. weekly visitors",
    ["Under 200", "200-500", "500-1,000", "1,000-3,000", "3,000-10,000", "Over 10,000"],
    index=2,
)
dwell = ft_col2.selectbox(
    "Average customer dwell time",
    ["Under 5 min", "5-15 min", "15-30 min", "30-60 min", "Over an hour"],
    index=2,
)

screen_pref = st.radio(
    "How many screens could you fit?",
    ["1 screen", "2 screens", "3+ screens", "Not sure — let's discuss"],
    index=3,
    horizontal=True,
)

decision = st.radio(
    "Are you the decision-maker?",
    ["Yes — I can sign a hosting agreement",
     "I'm an owner but partner needs to approve",
     "I work here — I'd want to introduce you to the owner"],
    index=0,
)

notes = st.text_area(
    "Anything else? (peak hours, events, demographics, screens you've seen at other venues)",
    height=100,
    placeholder="Optional but helpful — paints a clearer picture for our team.",
)

st.divider()


# ── SMS consent (TCPA / A2P) ─────────────────────────────────────────────────
SMS_CONSENT_LABEL = (
    "I agree to receive SMS messages from MCTV Digital regarding my hosting "
    "inquiry. Message and data rates may apply. Message frequency varies. "
    "Reply STOP to opt out, HELP for help."
)
sms_consent = st.checkbox(SMS_CONSENT_LABEL + " *", key="host_sms_consent")
st.caption(
    "Required to text you about your inquiry. View our "
    "[SMS Terms](https://mctvofms.com/sms-terms/) and "
    "[Privacy Policy](https://mctvofms.com/privacy-policy/)."
)

st.divider()


# ── Submit ───────────────────────────────────────────────────────────────────

if st.button("Submit Application", type="primary", width='stretch'):
    missing = []
    if not business_name: missing.append("Venue Name")
    if not contact_name:  missing.append("Your Name")
    if not contact_email: missing.append("Email")
    if not contact_phone: missing.append("Phone")
    if not industry:      missing.append("Venue Type")
    if not market:        missing.append("City")

    import re as _re
    phone_digits = _re.sub(r"\D", "", contact_phone) if contact_phone else ""
    phone_invalid = contact_phone and len(phone_digits) < 10

    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
    elif phone_invalid:
        st.error("Please enter a valid phone number (at least 10 digits).")
    elif not sms_consent:
        st.error("Please check the SMS consent box to continue.")
    else:
        notes_full = notes
        if street_address:
            notes_full = f"Address: {street_address}\n\n{notes_full}".strip()
        notes_full += (
            f"\n\nFoot traffic: {visitors}, dwell time: {dwell}, "
            f"screen preference: {screen_pref}, decision-maker: {decision}"
        )

        client_ip = ""
        try:
            headers = getattr(st.context, "headers", {}) or {}
            client_ip = (
                headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or headers.get("X-Real-Ip", "")
                or ""
            )
        except Exception:
            pass

        opp = insert_row("pipeline_opportunities", {
            "deal_type": "host",
            "business_name": business_name,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "city": market,
            "industry": industry,
            "stage": "identified",
            "source": "intake_form",
            "assigned_rep": "Mary Michael",
            "notes": notes_full,
            "probability": 25,
        })

        # Record SMS consent
        try:
            from services.sms_service import set_consent
            set_consent(contact_phone, opted_in=True, name=contact_name)
        except Exception as _e:
            print(f"[hosts intake] set_consent failed: {_e}")

        # Notify the team
        try:
            from services.notification_service import _send_email
            import os as _os
            to_emails = [s.strip() for s in
                          (_os.environ.get("NOTIFY_EMAILS", "") or "").split(",")
                          if s.strip()]
            if to_emails:
                subject = f"New host application: {business_name} ({market})"
                body = (
                    f"A new venue applied to host MCTV screens.\n\n"
                    f"Business: {business_name}\n"
                    f"Contact:  {contact_name}\n"
                    f"Email:    {contact_email}\n"
                    f"Phone:    {contact_phone}\n"
                    f"Market:   {market}\n"
                    f"Type:     {industry}\n"
                    f"Address:  {street_address or '(not provided)'}\n\n"
                    f"Foot traffic: {visitors}\n"
                    f"Dwell time:   {dwell}\n"
                    f"Screen pref:  {screen_pref}\n"
                    f"Decision:     {decision}\n\n"
                    f"Notes:\n{notes or '(none)'}\n\n"
                    f"Lead landed in the Host Pipeline at stage 'identified'."
                )
                for e in to_emails:
                    try:
                        _send_email(e, subject, body)
                    except Exception as _e:
                        print(f"[hosts intake] email to {e} failed: {_e}")
        except Exception as _e:
            print(f"[hosts intake] team notify failed: {_e}")

        st.session_state["host_app_submitted"] = True
        st.rerun()


st.markdown(
    '<div style="text-align:center; padding:2rem 0 1rem; color:#999; font-size:0.85rem;">'
    'MCTV Elite Advertising · Oxford · Starkville · Tupelo<br>'
    '<a href="https://www.mctvofms.com" target="_blank" style="color:#C5A55A;">mctvofms.com</a>'
    '</div>',
    unsafe_allow_html=True,
)
