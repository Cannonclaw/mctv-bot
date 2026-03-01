# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Public client intake form — no password required."""

import streamlit as st
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.leads_service import save_lead, send_notification_email
from services.config_service import load_config, get_market_names

st.set_page_config(
    page_title="Advertise With MCTV",
    page_icon="\U0001F4FA",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Hide sidebar and Streamlit chrome for a clean client-facing look
# Also inject SEO meta tags, Open Graph, and JSON-LD structured data
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>

<!-- SEO Meta Tags -->
<meta name="description" content="Get your brand in front of thousands. MCTV Elite Advertising places your ads on 125+ indoor digital billboard screens across Oxford, Starkville, and Tupelo, Mississippi. Request your free custom proposal.">
<meta name="keywords" content="indoor digital billboard advertising, MCTV, North Mississippi, Oxford MS, Starkville MS, Tupelo MS, local advertising, digital signage">
<meta name="author" content="MCTV Elite Advertising">
<link rel="canonical" href="https://bot.mctvofms.com/Intake">

<!-- Open Graph Tags -->
<meta property="og:title" content="Advertise With MCTV | Indoor Digital Billboards in North Mississippi">
<meta property="og:description" content="125+ indoor digital billboard screens across Oxford, Starkville, and Tupelo. 1.9M+ monthly impressions. Request your free custom advertising proposal.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://bot.mctvofms.com/Intake">
<meta property="og:site_name" content="MCTV Elite Advertising">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Advertise With MCTV | Indoor Digital Billboards in North Mississippi">
<meta name="twitter:description" content="125+ screens. 1.9M+ impressions. Your ad plays 4x per hour and can't be skipped. Get your free custom proposal.">

<!-- JSON-LD Structured Data: Organization + LocalBusiness -->
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "MCTV Elite Advertising",
    "description": "North Mississippi's premier indoor digital billboard network. 125+ screens in Oxford, Starkville, and Tupelo reaching 1.9M+ monthly impressions.",
    "url": "https://mctvofms.com",
    "telephone": "+16012018202",
    "email": "creed@mctvofms.com",
    "areaServed": [
        {"@type": "City", "name": "Oxford", "addressRegion": "MS"},
        {"@type": "City", "name": "Starkville", "addressRegion": "MS"},
        {"@type": "City", "name": "Tupelo", "addressRegion": "MS"}
    ],
    "serviceType": "Indoor Digital Billboard Advertising",
    "numberOfEmployees": {"@type": "QuantitativeValue", "value": 3},
    "foundingLocation": {"@type": "Place", "name": "Oxford, Mississippi"},
    "slogan": "North Mississippi's Indoor Digital Billboard Network",
    "knowsAbout": ["Indoor advertising", "Digital billboards", "Local business marketing", "Digital signage"]
}
</script>
""", unsafe_allow_html=True)


# ── BRANDED HEADER ───────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="text-align: center; padding: 1.5rem 0 0.5rem 0;">
        <h1 style="color: #1B1F3B; font-size: 2.2rem; margin-bottom: 0;">MCTV Elite Advertising</h1>
        <p style="color: #C5A55A; font-size: 1.1rem; margin-top: 0.25rem;">Indoor Digital Billboard Network</p>
        <p style="color: #666; font-size: 0.95rem;">Oxford &bull; Starkville &bull; Tupelo &bull; North Mississippi</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()


# ── CHECK IF ALREADY SUBMITTED ───────────────────────────────────────────────

if st.session_state.get("intake_submitted"):
    st.markdown(
        """
        <div style="text-align: center; padding: 3rem 0;">
            <h2 style="color: #1B1F3B;">Thank You!</h2>
            <p style="color: #666; font-size: 1.1rem;">
                Your information has been received. A member of our team will
                reach out to you within 24 hours to discuss how MCTV can help
                grow your business.
            </p>
            <p style="color: #C5A55A; font-size: 1rem; margin-top: 2rem;">
                In the meantime, feel free to visit
                <a href="https://www.mctvofms.com" target="_blank" style="color: #C5A55A;">mctvofms.com</a>
                to learn more about our network.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ── INTRO TEXT ───────────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="text-align: center; padding: 0 0 1rem 0;">
        <h3 style="color: #1B1F3B;">Get Your Brand in Front of Thousands</h3>
        <p style="color: #555; font-size: 0.95rem; max-width: 600px; margin: 0 auto;">
            125+ screens across North Mississippi. 1.9 million monthly impressions.
            55+ minute average dwell time. Fill out the form below and our team
            will put together a custom advertising plan for your business.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()


# ── INTAKE FORM ──────────────────────────────────────────────────────────────

st.markdown("#### Tell Us About Your Business")

col1, col2 = st.columns(2)
with col1:
    business_name = st.text_input("Business Name *", placeholder="Your Business Name")
    contact_name = st.text_input("Your Name *", placeholder="First and Last Name")
    contact_email = st.text_input("Email Address *", placeholder="you@yourbusiness.com")
with col2:
    contact_phone = st.text_input("Phone Number *", placeholder="(555) 555-5555")
    industry = st.text_input("Industry *", placeholder="Restaurant, Salon, Law Firm, etc.")
    _cfg = load_config()
    city = st.selectbox("City", get_market_names(_cfg, active_only=False) + ["Other"])

if city == "Other":
    city = st.text_input("Your City", placeholder="City, State")

st.divider()

st.markdown("#### What Are You Looking For?")

interest_level = st.radio(
    "How interested are you in advertising with MCTV?",
    [
        "Just exploring — tell me more",
        "Interested — I'd like to see a proposal",
        "Ready to go — let's get started",
    ],
    index=0,
)

goals = st.text_area(
    "What are your advertising goals? (optional)",
    placeholder="Examples: Increase foot traffic, build brand awareness, promote a grand opening, "
                "reach college students, advertise a new service...",
    height=100,
)

how_heard = st.selectbox(
    "How did you hear about MCTV?",
    [
        "Select one...",
        "Saw a screen in a local business",
        "Referral from another business",
        "Social media",
        "Website",
        "Someone from MCTV reached out",
        "Other",
    ],
)

st.divider()

st.markdown("#### Upload Your Logo (optional)")
st.caption("If you have your business logo handy, upload it here and we'll include it in your custom proposal.")

client_logo = st.file_uploader(
    "Business Logo",
    type=["png", "jpg", "jpeg", "webp"],
    label_visibility="collapsed",
)
if client_logo:
    st.image(client_logo, width=200)

additional_notes = st.text_area(
    "Anything else you'd like us to know? (optional)",
    placeholder="Multiple locations, seasonal promotions, budget range, etc.",
    height=80,
)

st.divider()


# ── SUBMIT ───────────────────────────────────────────────────────────────────

if st.button("Submit", type="primary", width='stretch'):
    # Validate required fields
    missing = []
    if not business_name:
        missing.append("Business Name")
    if not contact_name:
        missing.append("Your Name")
    if not contact_email:
        missing.append("Email Address")
    if not contact_phone:
        missing.append("Phone Number")
    if not industry:
        missing.append("Industry")
    if how_heard == "Select one...":
        missing.append("How did you hear about MCTV")

    # Validate phone number format
    import re
    phone_digits = re.sub(r'\D', '', contact_phone) if contact_phone else ""
    phone_invalid = contact_phone and len(phone_digits) < 10

    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
    elif phone_invalid:
        st.error("Please enter a valid phone number (at least 10 digits).")
    else:
        # Save the logo to a permanent location if uploaded
        logo_filename = None
        if client_logo:
            from pathlib import Path
            logos_dir = Path(__file__).parent.parent / "data" / "logos"
            logos_dir.mkdir(parents=True, exist_ok=True)
            suffix = Path(client_logo.name).suffix
            safe_biz = business_name.replace(" ", "_").replace("'", "")
            logo_filename = f"{safe_biz}{suffix}"
            with open(logos_dir / logo_filename, "wb") as f:
                f.write(client_logo.getbuffer())

        # Build lead data
        lead = {
            "business_name": business_name,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "industry": industry,
            "city": city,
            "interest_level": interest_level,
            "goals": goals,
            "how_heard": how_heard if how_heard != "Select one..." else "",
            "additional_notes": additional_notes,
            "logo_file": logo_filename,
        }

        # Save and notify
        lead_id = save_lead(lead)
        email_ok = send_notification_email(lead)

        st.session_state["intake_submitted"] = True
        st.rerun()


# ── FOOTER ───────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="text-align: center; padding: 2rem 0 1rem 0; color: #999; font-size: 0.8rem;">
        MCTV Elite Advertising &bull; Oxford &bull; Starkville &bull; Tupelo<br>
        <a href="https://www.mctvofms.com" target="_blank" style="color: #C5A55A;">mctvofms.com</a>
    </div>
    """,
    unsafe_allow_html=True,
)
