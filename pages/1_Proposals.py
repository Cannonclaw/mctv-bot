# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Proposal Generator page - creates all 6 proposal types."""

import streamlit as st
import os
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.config_service import load_config, get_team_names, get_market_names, get_all_tiers
from services.claude_service import ClaudeService
from services.docx_service import DocxService
from models.proposal_data import (
    ProposalInput, HostInput, BundleInput, BundleBusiness,
    VenuePartnerInput, ExclusivityInput, RenewalInput,
)
from generators.elite_advertiser import EliteAdvertiserProposal
from generators.host_media_kit import HostMediaKitProposal
from generators.multi_brand_bundle import MultiBrandBundleProposal
from generators.venue_partner import VenuePartnerProposal
from generators.category_exclusivity import CategoryExclusivityProposal
from generators.renewal_upgrade import RenewalUpgradeProposal

st.set_page_config(page_title="Proposal Generator - MCTV Bot", page_icon="\U0001F4DD", layout="wide")

from services.auth import check_password
if not check_password():
    st.stop()

# ── PRE-FILL FROM RESEARCH (if coming from Research page) ────────────────────
_prefill = st.session_state.pop("prefill_proposal", None)

st.markdown("## Proposal Generator")
st.caption("Select a proposal type and fill in the details to generate a polished Word document + PDF.")

if _prefill:
    st.info(f"Pre-filled from research on **{_prefill.get('business_name', '')}**. Review and adjust below.")


# ── HELPER: save uploaded logo to temp file ────────────────────────────────

def _save_uploaded_file(uploaded_file) -> str | None:
    """Save a single uploaded file to a temp file and return the path."""
    if uploaded_file is None:
        return None
    suffix = Path(uploaded_file.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.close()
    return tmp.name


def _save_uploaded_files(uploaded_files) -> list[str]:
    """Save multiple uploaded files and return list of paths."""
    paths = []
    for f in (uploaded_files or []):
        path = _save_uploaded_file(f)
        if path:
            paths.append(path)
    return paths


# ── GENERATION ENGINE (must be defined before forms call it) ──────────────────

def _generate_proposal(generator_class, data, client_logo_path=None,
                       page2_photo_paths=None, page4_photo_paths=None,
                       color_scheme="original"):
    """Run the proposal generation pipeline with progress UI.

    Args:
        generator_class: The proposal generator class.
        data: Proposal input data.
        client_logo_path: Path to the client logo image.
        page2_photo_paths: Photos for The Opportunity (page 2), max 4.
        page4_photo_paths: Photos for Market Coverage (page 4), max 6.
        color_scheme: Color scheme key.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your-api-key-here":
        st.error(
            "ANTHROPIC_API_KEY not configured. "
            "Please set it in Settings or in the .env file."
        )
        return

    config = load_config()
    model = config["proposal_settings"].get("model", "claude-sonnet-4-5-20250929")

    claude = ClaudeService(api_key=api_key, model=model)
    docx_svc = DocxService(config, color_scheme=color_scheme)

    # Store photo paths on the docx service — intentional placement only.
    # page2 = The Opportunity hero photos (max 4)
    # page4 = Market Coverage grid photos (max 6)
    docx_svc.client_logo_path = client_logo_path
    docx_svc.page2_photo_paths = (page2_photo_paths or [])[:4]   # cap at 4
    docx_svc.page4_photo_paths = (page4_photo_paths or [])[:6]   # cap at 6

    # Legacy attributes (for backwards compat with other generator types)
    docx_svc.venue_photo_paths = []
    docx_svc.ad_example_paths = []
    docx_svc.extra_photo_paths = docx_svc.page2_photo_paths + docx_svc.page4_photo_paths

    # Auto-include default community screen photos when NO user photos
    # were uploaded or scraped. These fill Market Coverage (page 4).
    if not docx_svc.page2_photo_paths and not docx_svc.page4_photo_paths:
        screens_dir = Path(__file__).parent.parent / "assets" / "screens"
        if screens_dir.exists():
            default_screens = []
            # Try market-specific subdirectories first
            selected = getattr(data, "selected_markets", [])
            if selected:
                for market_name in selected:
                    market_dir = screens_dir / market_name
                    if market_dir.exists():
                        default_screens.extend(sorted(
                            str(p) for p in market_dir.glob("*")
                            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
                        ))
            # Fallback: root screens/ directory
            if not default_screens:
                default_screens = sorted(
                    str(p) for p in screens_dir.glob("*")
                    if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
                )
            if default_screens:
                # First 2 go to page 2, rest to page 4
                docx_svc.page2_photo_paths = default_screens[:2]
                docx_svc.page4_photo_paths = default_screens[2:8]
                docx_svc.extra_photo_paths = default_screens[:8]

    generator = generator_class(config, claude, docx_svc)

    progress_bar = st.progress(0, text="Starting generation...")
    status_text = st.empty()

    def on_progress(section_name, current, total):
        pct = current / total
        progress_bar.progress(pct, text=f"Generating: {section_name} ({current}/{total})")
        status_text.caption(f"Section {current} of {total}: {section_name}")

    try:
        proposal_path, email_path = generator.generate(data, progress_callback=on_progress)
        progress_bar.progress(1.0, text="Complete!")
        status_text.empty()

        st.success("Proposal generated successfully!")
        st.caption(f"API Usage: {claude.usage_summary}")

        # Download buttons - Word, PDF, and Email
        pdf_path = DocxService.get_pdf_path(proposal_path)
        num_cols = 2 + (1 if pdf_path else 0)
        cols = st.columns(num_cols)

        with open(proposal_path, "rb") as f:
            cols[0].download_button(
                "Download Word (.docx)",
                data=f.read(),
                file_name=proposal_path.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width='stretch',
            )

        if pdf_path:
            with open(pdf_path, "rb") as f:
                cols[1].download_button(
                    "Download PDF",
                    data=f.read(),
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    type="primary",
                    width='stretch',
                )
            email_col = cols[2]
        else:
            st.info("PDF conversion unavailable (install Microsoft Word for auto-PDF). Word file is ready above.")
            email_col = cols[1]

        if email_path and email_path.exists():
            with open(email_path, "r", encoding="utf-8") as f:
                email_content = f.read()
            email_col.download_button(
                "Download Cover Email (.txt)",
                data=email_content,
                file_name=email_path.name,
                mime="text/plain",
                width='stretch',
            )

            with st.expander("Preview Cover Email"):
                st.text(email_content)

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Error generating proposal: {str(e)}")
        st.exception(e)

    finally:
        # Clear scraped photo session state so stale paths don't persist
        st.session_state.pop("scraped_page2_paths", None)
        st.session_state.pop("scraped_page4_paths", None)
        st.session_state.pop("scraped_logo_path", None)
        st.session_state.pop("scraped_images", None)

        # Clean up all temp files
        all_temps = [client_logo_path] + (page2_photo_paths or []) + (page4_photo_paths or [])
        for tmp in all_temps:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass


config = load_config()
team_names = get_team_names(config)
market_names = get_market_names(config)
all_markets = get_market_names(config, active_only=False)

# Proposal type selector
proposal_type = st.selectbox(
    "Proposal Type",
    [
        "Elite Advertiser",
        "Host Media Kit",
        "Multi-Brand Bundle",
        "Venue Partner / Revenue Share",
        "Category Exclusivity",
        "Renewal / Upgrade",
    ],
    help="Choose the type of proposal to generate.",
)

st.divider()

# ── COLOR SCHEME ──────────────────────────────────────────────────────────────
from services.docx_service import COLOR_SCHEMES

st.markdown("#### Color Scheme")
scheme_options = {k: v["label"] for k, v in COLOR_SCHEMES.items()}
color_scheme = st.radio(
    "Choose a color palette for the proposal",
    options=list(scheme_options.keys()),
    format_func=lambda k: scheme_options[k],
    horizontal=True,
    index=0,
    help="Changes the cover page, headers, accents, and borders throughout the proposal.",
)

st.divider()

# ── PHOTOS & IMAGES (shared across all forms) ────────────────────────────────
st.markdown("#### Photos & Images (optional)")
st.caption(
    "Photos are placed on **The Opportunity** (page 2, up to 2 photos) and "
    "**Market Coverage** (page 4, up to 6 photos). Recommended: **8 total**."
)

# Website image scraper
client_website = st.text_input(
    "Client Website URL — auto-pull images from their site",
    placeholder="https://www.oxfordfloral.com",
    help="Enter the client's website and we'll find their logo and photos automatically.",
)

if client_website and st.button("🔍 Scan Website for Images", key="scan_btn"):
    with st.spinner("Scanning website for images..."):
        from services.web_scraper import scrape_website_images, download_image
        images = scrape_website_images(client_website)
        if images:
            st.success(f"Found {len(images)} images!")
            st.session_state["scraped_images"] = images
        else:
            st.warning("No images found on that website. Try uploading manually below.")

# Show scraped images for OPT-IN selection
# KEY BEHAVIOR: All scraped photos default to UNSELECTED — the user decides.
# Exception: logos auto-select if detected with high confidence.
if st.session_state.get("scraped_images"):
    st.markdown("**Scraped images — select which to include:**")
    st.caption("Images default to *Skip*. Select a placement for each photo you want to use.")
    # Placement options: Skip (default for non-logo), Logo, or a proposal page
    _PLACEMENT_OPTIONS = ["Skip", "Client Logo", "The Opportunity (page 2)", "Market Coverage (page 4)"]
    # Only logos auto-select; everything else defaults to Skip
    _cat_to_default = {"logo": "Client Logo"}

    img_cols = st.columns(4)
    for i, img_info in enumerate(st.session_state["scraped_images"]):
        category = img_info.get("category", "product")
        default_placement = _cat_to_default.get(category, "Skip")
        default_idx = _PLACEMENT_OPTIONS.index(default_placement)
        with img_cols[i % 4]:
            st.image(img_info["url"], caption=img_info.get("alt", img_info["filename"])[:30], width='stretch')
            st.selectbox("Placement", _PLACEMENT_OPTIONS, index=default_idx,
                         key=f"scrape_slot_{i}")

    if st.button("📥 Download Selected Images"):
        from services.web_scraper import download_image
        # Collect user selections
        slot_assignments = {}
        for i, img_info in enumerate(st.session_state["scraped_images"]):
            slot = st.session_state.get(f"scrape_slot_{i}", "Skip")
            if slot != "Skip":
                slot_assignments[img_info["url"]] = slot

        if not slot_assignments:
            st.warning("No images selected. Check the placement dropdowns above.")
        else:
            with st.spinner(f"Downloading {len(slot_assignments)} images..."):
                routed = {"Client Logo": [], "The Opportunity (page 2)": [], "Market Coverage (page 4)": []}
                for url, slot in slot_assignments.items():
                    path = download_image(url)
                    if path:
                        routed[slot].append(path)
                total = sum(len(v) for v in routed.values())
                if total:
                    st.session_state["scraped_logo_path"] = routed["Client Logo"][0] if routed["Client Logo"] else None
                    st.session_state["scraped_page2_paths"] = routed["The Opportunity (page 2)"]
                    st.session_state["scraped_page4_paths"] = routed["Market Coverage (page 4)"]
                    summary_parts = []
                    if routed["Client Logo"]:
                        summary_parts.append("1 logo")
                    pg2 = len(routed["The Opportunity (page 2)"])
                    pg4 = len(routed["Market Coverage (page 4)"])
                    if pg2:
                        summary_parts.append(f"{pg2} for page 2")
                    if pg4:
                        summary_parts.append(f"{pg4} for page 4")
                    st.success(f"Downloaded {total} images: {', '.join(summary_parts)}")
                else:
                    st.warning("Could not download any images. Try uploading manually.")

scraped_logo_path = st.session_state.get("scraped_logo_path", None)
scraped_page2_paths = st.session_state.get("scraped_page2_paths", [])
scraped_page4_paths = st.session_state.get("scraped_page4_paths", [])

st.divider()

# ── Client Logo Upload ──
client_logo_file = st.file_uploader(
    "Client Logo — appears on the cover page",
    type=["png", "jpg", "jpeg", "webp"],
    key="client_logo",
    help="The client's logo will be placed on the proposal cover page.",
)
if client_logo_file:
    st.image(client_logo_file, width=150, caption="Logo preview")

# ── Photo Uploads with Placement Control ──
st.markdown("##### Proposal Photos")
st.caption(
    "Upload photos and assign each to a page. "
    "Page 2 (The Opportunity) holds up to 4 photos (1=centered, 2=side-by-side, 3=2+1, 4=2×2 grid). "
    "Page 4 (Market Coverage) holds up to 6 in a 2×3 grid."
)

page2_photos = st.file_uploader(
    "The Opportunity photos (page 2) — up to 4 hero showcase photos",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
    key="page2_photos",
    help="These appear on page 2 as the hero showcase of the client's work. 1=centered, 2=side-by-side, 3=2+1, 4=2×2 grid.",
)
if page2_photos:
    cols = st.columns(min(len(page2_photos), 4))
    for i, photo in enumerate(page2_photos):
        cols[i % 4].image(photo, caption=photo.name, width='stretch')
    if len(page2_photos) > 4:
        st.warning(f"Page 2 supports up to 4 photos. Only the first 4 of {len(page2_photos)} will be used.")

page4_photos = st.file_uploader(
    "Market Coverage photos (page 4) — up to 6 in a grid",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
    key="page4_photos",
    help="Product photos, venue shots, or client work shown in a 2×3 grid on page 4.",
)
if page4_photos:
    cols = st.columns(min(len(page4_photos), 4))
    for i, photo in enumerate(page4_photos):
        cols[i % 4].image(photo, caption=photo.name, width='stretch')
    if len(page4_photos) > 6:
        st.warning(f"Page 4 supports up to 6 photos. Only the first 6 of {len(page4_photos)} will be used.")

# Show total photo count feedback
_total_pg2 = len(page2_photos or []) + len(scraped_page2_paths)
_total_pg4 = len(page4_photos or []) + len(scraped_page4_paths)
_total_photos = _total_pg2 + _total_pg4
if _total_photos > 0:
    st.caption(f"📸 **{_total_photos} photos** selected: {min(_total_pg2, 4)} on page 2, {min(_total_pg4, 6)} on page 4")
    if _total_photos > 10:
        st.warning(f"Maximum 10 photos recommended. {_total_photos - 10} may be excluded.")

st.divider()


# ── ELITE ADVERTISER FORM ────────────────────────────────────────────────────
if proposal_type == "Elite Advertiser":
    st.markdown("### Elite Advertiser Proposal")
    st.caption("The flagship 5-6 page proposal — scannable, visual, punchy")

    col1, col2 = st.columns(2)
    with col1:
        business_name = st.text_input("Business Name *",
            value=_prefill.get("business_name", "") if _prefill else "",
            placeholder="McGlawn Homes, Inc.")
        contact_name = st.text_input("Contact Name *", placeholder="Josh McGlawn")
        contact_email = st.text_input("Contact Email", placeholder="josh@mcglawnhomes.com")
        industry = st.text_input("Industry *",
            value=_prefill.get("industry", "") if _prefill else "",
            placeholder="Custom Home Building / Construction")
    with col2:
        _pf_city = _prefill.get("city", market_names[0]) if _prefill else market_names[0]
        _city_idx = market_names.index(_pf_city) if _pf_city in market_names else 0
        city = st.selectbox("Primary City", market_names, index=_city_idx)
        selected_markets = st.multiselect("Markets to Include", market_names, default=[market_names[0]])
        _pf_rep = _prefill.get("sales_rep", team_names[1]) if _prefill else team_names[1]
        _rep_idx = team_names.index(_pf_rep) if _pf_rep in team_names else 1
        sales_rep = st.selectbox("Sales Rep", team_names, index=_rep_idx)

    st.markdown("#### Pricing")
    custom_pricing = st.toggle("Use Custom Pricing", value=False,
                                help="Enable to set a custom rate instead of standard tiers")
    if custom_pricing:
        cp1, cp2 = st.columns(2)
        custom_screens = cp1.number_input("Number of Screens", min_value=1, value=20)
        custom_rate = cp2.number_input("Monthly Rate ($)", min_value=0.0, value=500.0, step=50.0)
    else:
        custom_screens = 0
        custom_rate = 0.0
        st.info("Standard 4-tier pricing will be shown: $350/10 screens, $500/20, $800/40, $1,300/75+")

    additional_notes = st.text_area(
        "Additional Notes (optional)",
        value=_prefill.get("additional_notes", "") if _prefill else "",
        placeholder="Any specific details about the business, their goals, competitors, etc. "
                    "This context helps Claude write more tailored content.",
        height=100,
    )

    if st.button("Generate Proposal", type="primary", width='stretch'):
        if not business_name or not contact_name or not industry:
            st.error("Please fill in all required fields (marked with *).")
        else:
            logo_path = _save_uploaded_file(client_logo_file) or scraped_logo_path
            pg2_paths = _save_uploaded_files(page2_photos)[:4] + scraped_page2_paths
            pg4_paths = _save_uploaded_files(page4_photos)[:6] + scraped_page4_paths
            data = ProposalInput(
                business_name=business_name,
                contact_name=contact_name,
                contact_email=contact_email,
                industry=industry,
                city=city,
                selected_markets=selected_markets,
                custom_pricing=custom_pricing,
                custom_screen_count=custom_screens,
                custom_monthly_rate=custom_rate,
                sales_rep=sales_rep,
                additional_notes=additional_notes,
            )
            _generate_proposal(EliteAdvertiserProposal, data,
                               client_logo_path=logo_path,
                               page2_photo_paths=pg2_paths,
                               page4_photo_paths=pg4_paths,
                               color_scheme=color_scheme)


# ── HOST MEDIA KIT FORM ──────────────────────────────────────────────────────
elif proposal_type == "Host Media Kit":
    st.markdown("### Host Media Kit Proposal")
    st.caption("For venue partners who host MCTV screens (Hotel Tupelo / Stouts / Tico's style)")

    col1, col2 = st.columns(2)
    with col1:
        venue_name = st.text_input("Venue Name *", placeholder="Hotel Tupelo")
        contact_name = st.text_input("Contact Name *", placeholder="John Smith")
        contact_email = st.text_input("Contact Email", placeholder="john@hoteltupelo.com")
        venue_category = st.selectbox("Venue Category", config["venue_categories"])
    with col2:
        venue_address = st.text_input("Venue Address", placeholder="123 Main St, Tupelo, MS")
        city = st.selectbox("City", market_names)
        proposed_screens = st.number_input("Proposed Screen Count", min_value=1, value=1)
        free_outside = st.number_input("Free Outside Screens", min_value=5, value=10, step=5)
        sales_rep = st.selectbox("Sales Rep", team_names, index=0)

    additional_notes = st.text_area("Additional Notes", height=80)

    if st.button("Generate Proposal", type="primary", width='stretch'):
        if not venue_name or not contact_name:
            st.error("Please fill in all required fields.")
        else:
            logo_path = _save_uploaded_file(client_logo_file) or scraped_logo_path
            pg2_paths = _save_uploaded_files(page2_photos)[:4] + scraped_page2_paths
            pg4_paths = _save_uploaded_files(page4_photos)[:6] + scraped_page4_paths
            data = HostInput(
                venue_name=venue_name,
                contact_name=contact_name,
                contact_email=contact_email,
                venue_category=venue_category,
                venue_address=venue_address,
                city=city,
                proposed_screen_count=proposed_screens,
                free_outside_screens=free_outside,
                sales_rep=sales_rep,
                additional_notes=additional_notes,
            )
            _generate_proposal(HostMediaKitProposal, data,
                               client_logo_path=logo_path,
                               page2_photo_paths=pg2_paths,
                               page4_photo_paths=pg4_paths,
                               color_scheme=color_scheme)


# ── MULTI-BRAND BUNDLE FORM ──────────────────────────────────────────────────
elif proposal_type == "Multi-Brand Bundle":
    st.markdown("### Multi-Brand Bundle Proposal")
    st.caption("For owners with multiple businesses (Good Earth / Hayden style)")

    col1, col2 = st.columns(2)
    with col1:
        owner_name = st.text_input("Owner Name *", placeholder="Hayden Alexander")
        owner_email = st.text_input("Owner Email", placeholder="hayden@goodearth.com")
    with col2:
        sales_rep = st.selectbox("Sales Rep", team_names, index=1)
        custom_rate = st.number_input("Custom Monthly Rate ($)", min_value=0.0, value=1000.0, step=50.0,
                                       help="Set to 0 to use standard tier pricing")

    st.markdown("#### Businesses in Bundle")
    num_businesses = st.number_input("Number of Businesses", min_value=2, max_value=6, value=3)

    businesses = []
    for i in range(num_businesses):
        with st.expander(f"Business {i + 1}", expanded=(i == 0)):
            bc1, bc2 = st.columns(2)
            bname = bc1.text_input(f"Business Name", key=f"bname_{i}", placeholder=f"Business {i+1}")
            bindustry = bc2.text_input(f"Industry", key=f"bind_{i}", placeholder="Landscaping")
            bcity = bc1.selectbox(f"City", market_names, key=f"bcity_{i}")
            bdesc = bc2.text_input(f"Description (optional)", key=f"bdesc_{i}")
            bphone = bc1.text_input(f"Phone (optional)", key=f"bphone_{i}")
            bwebsite = bc2.text_input(f"Website (optional)", key=f"bweb_{i}")
            businesses.append(BundleBusiness(
                name=bname, industry=bindustry, city=bcity,
                description=bdesc, phone=bphone, website=bwebsite,
            ))

    additional_notes = st.text_area("Additional Notes", height=80)

    if st.button("Generate Proposal", type="primary", width='stretch'):
        if not owner_name or not businesses[0].name:
            st.error("Please fill in the owner name and at least the first business.")
        else:
            logo_path = _save_uploaded_file(client_logo_file) or scraped_logo_path
            pg2_paths = _save_uploaded_files(page2_photos)[:4] + scraped_page2_paths
            pg4_paths = _save_uploaded_files(page4_photos)[:6] + scraped_page4_paths
            data = BundleInput(
                owner_name=owner_name,
                owner_email=owner_email,
                businesses=businesses,
                custom_monthly_rate=custom_rate,
                sales_rep=sales_rep,
                additional_notes=additional_notes,
            )
            _generate_proposal(MultiBrandBundleProposal, data,
                               client_logo_path=logo_path,
                               page2_photo_paths=pg2_paths,
                               page4_photo_paths=pg4_paths,
                               color_scheme=color_scheme)


# ── VENUE PARTNER / REVENUE SHARE FORM ───────────────────────────────────────
elif proposal_type == "Venue Partner / Revenue Share":
    st.markdown("### Venue Partner / Revenue Share Proposal")
    st.caption("For large venues with revenue sharing (Tupelo Airport style)")

    col1, col2 = st.columns(2)
    with col1:
        venue_name = st.text_input("Venue Name *", placeholder="Tupelo Regional Airport")
        contact_name = st.text_input("Contact Name *", placeholder="Dylan Meador")
        contact_email = st.text_input("Contact Email")
        venue_type = st.text_input("Venue Type *", placeholder="Airport / Arena / Hotel")
    with col2:
        venue_address = st.text_input("Venue Address")
        city = st.selectbox("City", all_markets)
        proposed_screens = st.number_input("Proposed Screens", min_value=1, value=5)
        monthly_traffic = st.number_input("Est. Monthly Traffic", min_value=0, value=10000, step=1000)

    st.markdown("#### Revenue Model")
    rc1, rc2, rc3 = st.columns(3)
    revenue_split = rc1.number_input("Venue Revenue Share %", min_value=5.0, max_value=50.0, value=15.0, step=5.0)
    premium_rate = rc2.number_input("Premium Slot Rate $/mo", min_value=0.0, value=1750.0, step=250.0)
    standard_rate = rc3.number_input("Standard Slot Rate $/mo", min_value=0.0, value=1000.0, step=100.0)

    sales_rep = st.selectbox("Sales Rep", team_names, index=0)
    additional_notes = st.text_area("Additional Notes", height=80)

    if st.button("Generate Proposal", type="primary", width='stretch'):
        if not venue_name or not contact_name:
            st.error("Please fill in all required fields.")
        else:
            logo_path = _save_uploaded_file(client_logo_file) or scraped_logo_path
            pg2_paths = _save_uploaded_files(page2_photos)[:4] + scraped_page2_paths
            pg4_paths = _save_uploaded_files(page4_photos)[:6] + scraped_page4_paths
            data = VenuePartnerInput(
                venue_name=venue_name,
                contact_name=contact_name,
                contact_email=contact_email,
                venue_type=venue_type,
                venue_address=venue_address,
                city=city,
                proposed_screen_count=proposed_screens,
                estimated_monthly_traffic=monthly_traffic,
                revenue_split_pct=revenue_split,
                premium_slot_rate=premium_rate,
                standard_slot_rate=standard_rate,
                sales_rep=sales_rep,
                additional_notes=additional_notes,
            )
            _generate_proposal(VenuePartnerProposal, data,
                               client_logo_path=logo_path,
                               page2_photo_paths=pg2_paths,
                               page4_photo_paths=pg4_paths,
                               color_scheme=color_scheme)


# ── CATEGORY EXCLUSIVITY FORM ────────────────────────────────────────────────
elif proposal_type == "Category Exclusivity":
    st.markdown("### Category Exclusivity Proposal")
    st.caption("Premium pricing for exclusive category ownership (Cannon Cleary McGraw style)")

    col1, col2 = st.columns(2)
    with col1:
        business_name = st.text_input("Business Name *", placeholder="Cannon Cleary McGraw")
        contact_name = st.text_input("Contact Name *")
        contact_email = st.text_input("Contact Email")
        industry = st.text_input("Industry *", placeholder="Real Estate Brokerage")
    with col2:
        exclusive_category = st.text_input("Exclusive Category *",
                                            placeholder="Real Estate / Law Firm / Bank",
                                            help="The category they'll be the ONLY advertiser in")
        city = st.selectbox("Primary City", market_names)
        selected_markets = st.multiselect("Exclusive Markets", market_names, default=[market_names[0]])
        monthly_rate = st.number_input("Monthly Rate ($)", min_value=0.0, value=2000.0, step=100.0,
                                        help="Set to 0 to show standard tiers with exclusivity note")

    sales_rep = st.selectbox("Sales Rep", team_names)
    additional_notes = st.text_area("Additional Notes", height=80)

    if st.button("Generate Proposal", type="primary", width='stretch'):
        if not business_name or not contact_name or not exclusive_category:
            st.error("Please fill in all required fields.")
        else:
            logo_path = _save_uploaded_file(client_logo_file) or scraped_logo_path
            pg2_paths = _save_uploaded_files(page2_photos)[:4] + scraped_page2_paths
            pg4_paths = _save_uploaded_files(page4_photos)[:6] + scraped_page4_paths
            data = ExclusivityInput(
                business_name=business_name,
                contact_name=contact_name,
                contact_email=contact_email,
                industry=industry,
                exclusive_category=exclusive_category,
                city=city,
                selected_markets=selected_markets,
                monthly_rate=monthly_rate,
                sales_rep=sales_rep,
                additional_notes=additional_notes,
            )
            _generate_proposal(CategoryExclusivityProposal, data,
                               client_logo_path=logo_path,
                               page2_photo_paths=pg2_paths,
                               page4_photo_paths=pg4_paths,
                               color_scheme=color_scheme)


# ── RENEWAL / UPGRADE FORM ───────────────────────────────────────────────────
elif proposal_type == "Renewal / Upgrade":
    st.markdown("### Renewal / Upgrade Proposal")
    st.caption("For existing clients with traction data")

    col1, col2 = st.columns(2)
    with col1:
        business_name = st.text_input("Business Name *")
        contact_name = st.text_input("Contact Name *")
        contact_email = st.text_input("Contact Email")
        current_tier = st.text_input("Current Package", placeholder="20 Screens / $500/mo")
    with col2:
        months = st.number_input("Months as Client", min_value=1, value=6)
        total_plays = st.number_input("Total Ad Plays", min_value=0, value=100000, step=10000)
        total_venues = st.number_input("Total Venues", min_value=0, value=20)
        total_impressions = st.number_input("Total Impressions", min_value=0.0, value=500000.0, step=50000.0)

    suggested_tier = st.text_input("Suggested Upgrade", placeholder="40 Screens / $800/mo")
    sales_rep = st.selectbox("Sales Rep", team_names, index=1)
    additional_notes = st.text_area("Additional Notes", height=80)

    if st.button("Generate Proposal", type="primary", width='stretch'):
        if not business_name or not contact_name:
            st.error("Please fill in all required fields.")
        else:
            logo_path = _save_uploaded_file(client_logo_file) or scraped_logo_path
            pg2_paths = _save_uploaded_files(page2_photos)[:4] + scraped_page2_paths
            pg4_paths = _save_uploaded_files(page4_photos)[:6] + scraped_page4_paths
            data = RenewalInput(
                business_name=business_name,
                contact_name=contact_name,
                contact_email=contact_email,
                current_tier=current_tier,
                months_as_client=months,
                total_plays=total_plays,
                total_venues=total_venues,
                total_impressions=total_impressions,
                suggested_upgrade_tier=suggested_tier,
                sales_rep=sales_rep,
                additional_notes=additional_notes,
            )
            _generate_proposal(RenewalUpgradeProposal, data,
                               client_logo_path=logo_path,
                               page2_photo_paths=pg2_paths,
                               page4_photo_paths=pg4_paths,
                               color_scheme=color_scheme)
