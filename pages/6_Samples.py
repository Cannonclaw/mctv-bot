# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Public sample proposals page — no password required.

Visitors (and WordPress iframe embeds) can browse pre-generated sample
proposals to see what MCTV advertising proposals look like.
"""

import streamlit as st
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

st.set_page_config(
    page_title="MCTV Sample Proposals",
    page_icon="\U0001F4FA",
    layout="centered",
    initial_sidebar_state="collapsed",
)


from services.team_ui import render_team_sidebar
render_team_sidebar()
# Hide sidebar and Streamlit chrome for a clean public look
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
<meta name="description" content="See what an MCTV advertising proposal looks like. Download sample proposals for restaurants, salons, gyms, and auto shops. Indoor digital billboard advertising across North Mississippi.">
<meta name="keywords" content="MCTV sample proposals, indoor billboard advertising examples, digital billboard proposal, North Mississippi advertising, Oxford MS, Starkville MS, Tupelo MS">
<meta name="author" content="MCTV Elite Advertising">
<link rel="canonical" href="https://bot.mctvofms.com/Samples">

<!-- Open Graph Tags -->
<meta property="og:title" content="Sample Proposals | MCTV Elite Advertising">
<meta property="og:description" content="Download sample advertising proposals for restaurants, salons, gyms, and auto shops. See how MCTV's 125+ indoor digital billboard screens can grow your business.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://bot.mctvofms.com/Samples">
<meta property="og:site_name" content="MCTV Elite Advertising">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Sample Proposals | MCTV Elite Advertising">
<meta name="twitter:description" content="See what your custom indoor digital billboard advertising proposal looks like. Download free samples for your industry.">

<!-- JSON-LD Structured Data -->
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "WebPage",
    "name": "MCTV Sample Advertising Proposals",
    "description": "Download sample indoor digital billboard advertising proposals for restaurants, salons, gyms, and auto shops across North Mississippi.",
    "url": "https://bot.mctvofms.com/Samples",
    "publisher": {
        "@type": "Organization",
        "name": "MCTV Elite Advertising",
        "url": "https://mctvofms.com"
    },
    "about": {
        "@type": "Service",
        "name": "Indoor Digital Billboard Advertising",
        "provider": {"@type": "Organization", "name": "MCTV Elite Advertising"},
        "areaServed": ["Oxford, MS", "Starkville, MS", "Tupelo, MS"],
        "description": "125+ indoor digital billboard screens across North Mississippi with 1.9M+ monthly impressions."
    }
}
</script>
""", unsafe_allow_html=True)


# ── BRANDED HEADER ───────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="text-align: center; padding: 1.5rem 0 0.5rem 0;">
        <h1 style="color: #1B1F3B; font-size: 2.2rem; margin-bottom: 0;">Sample Proposals</h1>
        <p style="color: #C5A55A; font-size: 1.1rem; margin-top: 0.25rem;">
            See What Your Custom Advertising Proposal Looks Like
        </p>
        <p style="color: #666; font-size: 0.95rem;">
            Every MCTV proposal is AI-generated, personalized to your business, and ready in minutes.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()


# ── SAMPLE PROPOSALS ─────────────────────────────────────────────────────────

SAMPLES_DIR = Path(__file__).parent.parent / "assets" / "samples"

# Industry samples with descriptions
SAMPLE_INDUSTRIES = [
    {
        "name": "Restaurant & Bar",
        "icon": "\U0001F37D\uFE0F",
        "file": "MCTV_Sample_Restaurant.pdf",
        "description": (
            "See how a local restaurant can reach thousands of diners, gym-goers, "
            "and shoppers across North Mississippi with indoor digital billboard ads."
        ),
    },
    {
        "name": "Barbershop & Salon",
        "icon": "\u2702\uFE0F",
        "file": "MCTV_Sample_Salon.pdf",
        "description": (
            "A custom proposal showing how beauty and grooming businesses build "
            "brand awareness with MCTV's network of 125+ screens."
        ),
    },
    {
        "name": "Fitness & Gym",
        "icon": "\U0001F4AA",
        "file": "MCTV_Sample_Gym.pdf",
        "description": (
            "Gyms and fitness studios reach health-conscious consumers across "
            "restaurants, offices, and retail locations all day long."
        ),
    },
    {
        "name": "Auto & Service Shop",
        "icon": "\U0001F697",
        "file": "MCTV_Sample_Auto.pdf",
        "description": (
            "Auto shops and service businesses stay top of mind with repeat "
            "impressions across the entire MCTV network."
        ),
    },
]

found_any = False

for sample in SAMPLE_INDUSTRIES:
    pdf_path = SAMPLES_DIR / sample["file"]
    if pdf_path.exists():
        found_any = True
        st.markdown(f"### {sample['icon']} {sample['name']}")
        st.markdown(f"<p style='color: #555;'>{sample['description']}</p>", unsafe_allow_html=True)
        with open(pdf_path, "rb") as f:
            st.download_button(
                f"Download {sample['name']} Sample",
                data=f.read(),
                file_name=sample["file"],
                mime="application/pdf",
                key=f"sample_{sample['file']}",
                width='stretch',
            )
        st.divider()

if not found_any:
    st.info(
        "Sample proposals are being prepared. Check back soon, or "
        "[contact us](https://www.mctvofms.com) to get a custom proposal "
        "tailored to your business!"
    )

    # Show what a proposal includes instead
    st.markdown("### What's Inside Every MCTV Proposal")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        - **Custom Cover Page** with your business name and logo
        - **The Opportunity** — why indoor digital advertising works for your industry
        - **What's Included** — everything you get as an MCTV partner
        """)
    with col2:
        st.markdown("""
        - **Market Coverage** — 125+ screens across North Mississippi
        - **Why MCTV** — what sets us apart from other advertising
        - **Meet Your Team** — your dedicated MCTV contacts
        """)


# ── CTA ──────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="text-align: center; padding: 2rem 0 1rem 0; background-color: #F5F5F5; border-radius: 8px; margin-top: 1rem;">
        <h3 style="color: #1B1F3B;">Ready for Your Custom Proposal?</h3>
        <p style="color: #555; max-width: 500px; margin: 0 auto 1rem auto;">
            Fill out our quick intake form and our team will generate a personalized
            advertising proposal for your business — usually within 24 hours.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Link to intake form
intake_url = "https://bot.mctvofms.com/Intake"
col_a, col_b, col_c = st.columns([1, 2, 1])
with col_b:
    st.link_button(
        "Get Your Free Proposal",
        intake_url,
        type="primary",
        width='stretch',
    )


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
