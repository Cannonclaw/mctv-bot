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
                       page4_captions=None, color_scheme="original"):
    """Run the proposal generation pipeline with progress UI.

    Args:
        generator_class: The proposal generator class.
        data: Proposal input data.
        client_logo_path: Path to the client logo image.
        page2_photo_paths: Photos for The Opportunity (page 2), max 4.
        page4_photo_paths: Photos for Market Coverage (page 4), max 6.
        page4_captions: Optional captions for page 4 photos (same order).
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
    docx_svc.page4_captions = (page4_captions or [])[:6]         # match page4

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
        st.session_state.pop("scraped_page4_captions", None)
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
        "Sponsorship Package",
    ],
    help="Choose the type of proposal to generate.",
)


# ── SPONSORSHIP PRESET (Elite Advertiser variant) ────────────────────────────
# A "Sponsorship Package" is a preset-driven Elite Advertiser proposal aimed
# at event/seasonal saturation deals (Ole Miss Football, holiday shopping, etc).
# Picking a preset pre-fills selected_markets, screen count, monthly rate, and
# notes so the rep gets a proposal in seconds.

if proposal_type == "Sponsorship Package":
    packages = config.get("sponsorship_packages", []) or []
    st.markdown("#### Pick a sponsorship preset")
    st.caption("Each preset bundles markets + screens + a seasonal narrative. "
               "After picking, fill in the prospect details below and generate "
               "an Elite Advertiser proposal with the package built in.")

    if not packages:
        st.warning("No sponsorship packages defined. Add some in config.json under `sponsorship_packages`.")
        st.stop()

    pkg_keys = [p["key"] for p in packages]
    pkg_lookup = {p["key"]: p for p in packages}
    chosen_key = st.selectbox(
        "Preset",
        pkg_keys,
        format_func=lambda k: pkg_lookup[k]["name"],
    )
    chosen = pkg_lookup[chosen_key]

    pcol1, pcol2 = st.columns([2, 1])
    with pcol1:
        st.markdown(f"**{chosen['name']}**")
        st.caption(chosen.get("tagline", ""))
        st.markdown(chosen.get("description", ""))
        st.markdown(f"**Best for:** {', '.join(chosen.get('best_for', []))}")
    with pcol2:
        st.metric("Markets", ", ".join(chosen.get("markets", [])))
        st.metric("Screens", chosen.get("screens", 0))
        st.metric("Monthly rate", f"${float(chosen.get('monthly_rate', 0)):,.0f}")
        st.metric("Term", f"{chosen.get('term_months', 1)} mo")

    st.session_state["sponsorship_preset"] = chosen
    st.info(
        "Now scroll to the Elite Advertiser form below — markets, monthly rate, "
        "and notes will be pre-populated from this preset. Just add the prospect "
        "info and click Generate."
    )
    # Behind the scenes the generator uses the Elite Advertiser flow.
    proposal_type = "Elite Advertiser"

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

if client_website and st.button("\U0001f50d Scan Website for Images", key="scan_btn"):
    with st.spinner("Scanning website for images..."):
        from services.web_scraper import scrape_website_images, auto_assign_photos, download_image
        images = scrape_website_images(client_website)
        if images:
            # Run auto-assignment engine to set smart defaults
            images = auto_assign_photos(images)
            st.session_state["scraped_images"] = images
            auto_count = sum(1 for img in images if img.get("auto_assigned"))
            st.success(f"Found {len(images)} images! \U0001f916 Auto-assigned {auto_count} to optimal slots.")
        else:
            st.warning("No images found on that website. Try uploading manually below.")

# Show scraped images for OPT-IN selection
# KEY BEHAVIOR: All scraped photos default to UNSELECTED — the user decides.
# Exception: logos auto-select if detected with high confidence.
if st.session_state.get("scraped_images"):
    st.markdown("**Scraped images — select which to include:**")
    st.caption("Images ranked by quality & relevance. \U0001f916 = auto-assigned to best slot.")

    # Sort images: auto-assigned first, then by confidence (best images at top)
    _RANK_BONUS = {"logo": 0.20, "venue": 0.15, "product": 0.10, "food": 0.10, "team": 0.05, "promo": -0.20}
    def _img_rank(img):
        auto = 1.0 if img.get("auto_assigned") else 0.0
        conf = img.get("confidence", 0.0)
        bonus = _RANK_BONUS.get(img.get("category", "product"), 0.0)
        return -(auto + conf + bonus)
    st.session_state["scraped_images"] = sorted(
        st.session_state["scraped_images"], key=_img_rank,
    )

    _PLACEMENT_OPTIONS = ["Skip", "Client Logo", "The Opportunity (page 2)", "Market Coverage (page 4)"]
    _cat_badge = {
        "logo": "\U0001f3f7\ufe0f Logo",
        "product": "\U0001f4f7 Photo",
        "venue": "\U0001f3e2 Venue",
        "team": "\U0001f465 Team",
        "food": "\U0001f37d\ufe0f Food",
        "promo": "\U0001f4e2 Promo",
        "ad_example": "\U0001f4e2 Promo",  # legacy compat
    }

    # Bulk action buttons
    bulk_cols = st.columns(4)
    if bulk_cols[0].button("All → Page 2", key="bulk_pg2"):
        for i in range(len(st.session_state["scraped_images"])):
            st.session_state[f"scrape_slot_{i}"] = "The Opportunity (page 2)"
        st.rerun()
    if bulk_cols[1].button("All → Page 4", key="bulk_pg4"):
        for i in range(len(st.session_state["scraped_images"])):
            st.session_state[f"scrape_slot_{i}"] = "Market Coverage (page 4)"
        st.rerun()
    if bulk_cols[2].button("Skip All", key="bulk_skip"):
        for i in range(len(st.session_state["scraped_images"])):
            st.session_state[f"scrape_slot_{i}"] = "Skip"
        st.rerun()

    # ── Photo Counter Bar ───────────────────────────────────────────────
    _logo_n = 0
    _pg2_n = 0
    _pg4_n = 0
    _skip_n = 0
    for i in range(len(st.session_state["scraped_images"])):
        slot = st.session_state.get(f"scrape_slot_{i}", "Skip")
        if slot == "Client Logo":
            _logo_n += 1
        elif slot == "The Opportunity (page 2)":
            _pg2_n += 1
        elif slot == "Market Coverage (page 4)":
            _pg4_n += 1
        else:
            _skip_n += 1

    _logo_icon = "\u2705" if _logo_n == 1 else ("\u26a0\ufe0f" if _logo_n > 1 else "\u2014")
    _pg2_color = "red" if _pg2_n > 4 else ("green" if _pg2_n > 0 else "gray")
    _pg4_color = "red" if _pg4_n > 6 else ("green" if _pg4_n > 0 else "gray")
    st.markdown(
        f"\U0001f3f7\ufe0f **Logo:** {_logo_icon}"
        f"&emsp;|&emsp;\U0001f4c4 **Page 2:** "
        f"<span style='color:{_pg2_color}'>{_pg2_n}/4</span>"
        f"&emsp;|&emsp;\U0001f4f8 **Page 4:** "
        f"<span style='color:{_pg4_color}'>{_pg4_n}/6</span>"
        f"&emsp;|&emsp;\u23ed\ufe0f **Skipped:** {_skip_n}",
        unsafe_allow_html=True,
    )
    if _pg2_n > 4:
        st.warning(f"Page 2 supports max **4** photos. {_pg2_n - 4} extra will auto-overflow to Page 4 on download.")
    if _pg4_n > 6:
        st.warning(f"Page 4 supports max **6** photos. {_pg4_n - 6} extra will be excluded on download.")
    if _logo_n > 1:
        st.warning("Multiple images assigned to Logo. Only the first will be used.")

    img_cols = st.columns(4)
    for i, img_info in enumerate(st.session_state["scraped_images"]):
        category = img_info.get("category", "product")
        # Use auto-assignment default if available, else Skip
        default_placement = img_info.get("default_placement", "Skip")
        default_idx = _PLACEMENT_OPTIONS.index(default_placement) if default_placement in _PLACEMENT_OPTIONS else 0
        with img_cols[i % 4]:
            st.image(img_info["url"], caption=img_info.get("alt", img_info["filename"])[:30], width='stretch')
            badge = _cat_badge.get(category, "\U0001f4f7 Photo")
            conf = img_info.get("confidence", 0)
            conf_pct = f"{int(conf * 100)}%" if conf else ""
            auto_tag = " \U0001f916" if img_info.get("auto_assigned") else ""
            st.caption(f"{badge} {conf_pct}{auto_tag} · `{img_info['filename'][:25]}`")
            st.selectbox("Placement", _PLACEMENT_OPTIONS, index=default_idx,
                         key=f"scrape_slot_{i}")
            st.text_input("Caption", key=f"scrape_caption_{i}",
                          max_chars=60, placeholder="Caption (page 4 only)",
                          label_visibility="collapsed")

    # ── Photo Order Preview ───────────────────────────────────────────
    with st.expander("Preview photo order by page"):
        _order_pg2 = []
        _order_pg4 = []
        _order_logo = []
        for i, img_info in enumerate(st.session_state["scraped_images"]):
            slot = st.session_state.get(f"scrape_slot_{i}", "Skip")
            name = img_info.get("filename", f"image_{i}")[:25]
            if slot == "Client Logo":
                _order_logo.append(name)
            elif slot == "The Opportunity (page 2)":
                _order_pg2.append(name)
            elif slot == "Market Coverage (page 4)":
                _order_pg4.append(name)
        if _order_logo:
            st.markdown(f"**Logo:** {_order_logo[0]}")
        if _order_pg2:
            st.markdown("**Page 2 (The Opportunity):** " + " \u2192 ".join(
                f"{n+1}. `{f}`" for n, f in enumerate(_order_pg2)
            ))
        if _order_pg4:
            st.markdown("**Page 4 (Market Coverage):** " + " \u2192 ".join(
                f"{n+1}. `{f}`" for n, f in enumerate(_order_pg4)
            ))
        if not (_order_logo or _order_pg2 or _order_pg4):
            st.caption("No images assigned yet.")
        st.caption("*Photos are placed in the order shown. Re-assign placements above to change order.*")

    if st.button("\U0001f4e5 Download Selected Images"):
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
                pg4_captions_list = []
                for url, slot in slot_assignments.items():
                    path = download_image(url)
                    if path:
                        routed[slot].append(path)
                        if slot == "Market Coverage (page 4)":
                            # Find matching caption from session state
                            cap = ""
                            for j, img_info in enumerate(st.session_state["scraped_images"]):
                                if img_info["url"] == url:
                                    cap = st.session_state.get(f"scrape_caption_{j}", "")
                                    break
                            pg4_captions_list.append(cap)
                # Overflow: Page 2 excess → Page 4, Page 4 excess → excluded
                pg2_list = routed["The Opportunity (page 2)"]
                pg4_list = routed["Market Coverage (page 4)"]
                if len(pg2_list) > 4:
                    overflow = pg2_list[4:]
                    routed["The Opportunity (page 2)"] = pg2_list[:4]
                    pg4_list = overflow + pg4_list  # overflow gets priority
                overflow_excluded = 0
                if len(pg4_list) > 6:
                    overflow_excluded = len(pg4_list) - 6
                    pg4_list = pg4_list[:6]
                routed["Market Coverage (page 4)"] = pg4_list
                total = sum(len(v) for v in routed.values())
                if total:
                    st.session_state["scraped_logo_path"] = routed["Client Logo"][0] if routed["Client Logo"] else None
                    st.session_state["scraped_page2_paths"] = routed["The Opportunity (page 2)"]
                    st.session_state["scraped_page4_paths"] = routed["Market Coverage (page 4)"]
                    st.session_state["scraped_page4_captions"] = pg4_captions_list
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
                    if overflow_excluded > 0:
                        st.info(f"{overflow_excluded} image(s) excluded due to page limits.")
                    # Quality badges — show resolution for downloaded images
                    from services.web_scraper import score_image_quality
                    all_downloaded = (
                        routed["Client Logo"]
                        + routed["The Opportunity (page 2)"]
                        + routed["Market Coverage (page 4)"]
                    )
                    badge_parts = []
                    low_count = 0
                    for dl_path in all_downloaded:
                        q = score_image_quality(dl_path)
                        fname = Path(dl_path).name[:20]
                        badge_parts.append(f"`{fname}` {q['quality_label']}")
                        if q["quality_tier"] == "low":
                            low_count += 1
                    if badge_parts:
                        st.caption("**Resolution:** " + " · ".join(badge_parts))
                    if low_count:
                        st.warning(
                            f"{low_count} image(s) are low resolution and may "
                            "appear blurry in the proposal."
                        )
                else:
                    st.warning("Could not download any images. Try uploading manually.")

scraped_logo_path = st.session_state.get("scraped_logo_path", None)
scraped_page2_paths = st.session_state.get("scraped_page2_paths", [])
scraped_page4_paths = st.session_state.get("scraped_page4_paths", [])
scraped_page4_captions = st.session_state.get("scraped_page4_captions", [])

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

    # Sponsorship preset overrides defaults if one was selected above
    _sponsor = st.session_state.get("sponsorship_preset")

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
        if _sponsor and _sponsor.get("markets"):
            default_city = _sponsor["markets"][0]
            default_markets = list(_sponsor["markets"])
        else:
            default_city = _prefill.get("city", market_names[0]) if _prefill else market_names[0]
            default_markets = [market_names[0]]
        _city_idx = market_names.index(default_city) if default_city in market_names else 0
        city = st.selectbox("Primary City", market_names, index=_city_idx)
        selected_markets = st.multiselect("Markets to Include", market_names, default=default_markets)
        _pf_rep = _prefill.get("sales_rep", team_names[1]) if _prefill else team_names[1]
        _rep_idx = team_names.index(_pf_rep) if _pf_rep in team_names else 1
        sales_rep = st.selectbox("Sales Rep", team_names, index=_rep_idx)

    st.markdown("#### Pricing")
    # Sponsorship presets always use custom pricing (the preset rate)
    default_custom = bool(_sponsor)
    custom_pricing = st.toggle("Use Custom Pricing", value=default_custom,
                                help="Enable to set a custom rate instead of standard tiers")
    if custom_pricing:
        default_screens = int(_sponsor["screens"]) if _sponsor else 20
        default_rate = float(_sponsor["monthly_rate"]) if _sponsor else 500.0
        cp1, cp2 = st.columns(2)
        custom_screens = cp1.number_input("Number of Screens", min_value=1, value=default_screens)
        custom_rate = cp2.number_input("Monthly Rate ($)", min_value=0.0, value=default_rate, step=50.0)
    else:
        custom_screens = 0
        custom_rate = 0.0
        st.info("Standard 4-tier pricing will be shown: $350/10 screens, $500/20, $800/40, $1,300/75+")

    # Pre-fill notes with sponsorship narrative when a preset is in use
    default_notes = ""
    if _sponsor:
        default_notes = (
            f"Sponsorship Package: {_sponsor.get('name', '')}\n"
            f"{_sponsor.get('description', '')}\n\n"
            f"Term: {_sponsor.get('term_months', 1)} month(s). "
            f"Best for: {', '.join(_sponsor.get('best_for', []))}."
        )
    elif _prefill:
        default_notes = _prefill.get("additional_notes", "")

    additional_notes = st.text_area(
        "Additional Notes (optional)",
        value=default_notes,
        placeholder="Any specific details about the business, their goals, competitors, etc. "
                    "This context helps Claude write more tailored content.",
        height=120,
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
                               page4_captions=scraped_page4_captions,
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
                               page4_captions=scraped_page4_captions,
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
                               page4_captions=scraped_page4_captions,
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
                               page4_captions=scraped_page4_captions,
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

    # Live exclusivity conflict check — warn the rep before they pitch a
    # category that's already locked up for someone else in these markets.
    if exclusive_category and selected_markets:
        try:
            from services.exclusivity_service import find_conflicts, format_conflict_message
            conflicts = find_conflicts(exclusive_category, selected_markets)
            if conflicts:
                st.error(
                    "**\u26A0\uFE0F Exclusivity Conflict Detected**\n\n"
                    + format_conflict_message(conflicts)
                    + "\n\nGenerating this proposal anyway is OK if you've "
                    "already cleared it with the existing client, but the "
                    "default move is to pick a different category or different "
                    "markets."
                )
            else:
                st.success(
                    f"\u2705 No exclusivity conflicts for '{exclusive_category}' "
                    f"in {', '.join(selected_markets)}."
                )
        except Exception as _e:
            st.caption(f"Exclusivity check unavailable: {_e}")

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
                               page4_captions=scraped_page4_captions,
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
                               page4_captions=scraped_page4_captions,
                               color_scheme=color_scheme)
