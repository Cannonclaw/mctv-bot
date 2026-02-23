"""Prospect Research — competitive intelligence briefs for sales calls."""

import streamlit as st
import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

st.set_page_config(
    page_title="Prospect Research - MCTV Bot",
    page_icon="\U0001F50D",
    layout="wide",
)

from services.auth import check_password

if not check_password():
    st.stop()

from services.config_service import load_config, get_team_names, get_market_names
from services.claude_service import ClaudeService

config = load_config()
team_names = get_team_names(config)
market_names = get_market_names(config)

st.markdown("## Prospect Research")
st.caption(
    "Generate a competitive intelligence brief before your sales call. "
    "Paste a prospect's info and get tailored talking points in seconds."
)

st.divider()


# ── DISPLAY HELPER ────────────────────────────────────────────────────────────


def _display_brief(brief: str, business_name: str):
    """Parse the research brief into sections and display with expanders."""
    section_patterns = [
        (r"SECTION\s*1\s*[-:–]\s*PROSPECT SNAPSHOT", "Prospect Snapshot", "\U0001F3E2"),
        (r"SECTION\s*2\s*[-:–]\s*ONLINE PRESENCE", "Online Presence Assessment", "\U0001F310"),
        (r"SECTION\s*3\s*[-:–]\s*LOCAL ADVERTISING", "Local Advertising Landscape", "\U0001F4CD"),
        (r"SECTION\s*4\s*[-:–]\s*WHY MCTV", f"Why MCTV Makes Sense for {business_name}", "\U0001F4FA"),
        (r"SECTION\s*5\s*[-:–]\s*SALES TALKING POINTS", "Sales Talking Points", "\U0001F4AC"),
        (r"SECTION\s*6\s*[-:–]\s*OBJECTION RESPONSES", "Objection Responses", "\U0001F6E1\uFE0F"),
        (r"SECTION\s*7\s*[-:–]\s*RECOMMENDED APPROACH", "Recommended Approach", "\U0001F3AF"),
    ]

    # Find section boundaries
    sections_found = []
    for pattern, title, icon in section_patterns:
        match = re.search(pattern, brief, re.IGNORECASE)
        if match:
            sections_found.append((match.start(), match.end(), title, icon))

    if len(sections_found) >= 3:
        sections_found.sort(key=lambda x: x[0])

        for i, (start, header_end, title, icon) in enumerate(sections_found):
            if i + 1 < len(sections_found):
                content = brief[header_end : sections_found[i + 1][0]].strip()
            else:
                content = brief[header_end:].strip()

            # Key sections expanded by default
            expanded = title in [
                "Sales Talking Points",
                "Objection Responses",
                "Recommended Approach",
            ] or "Why MCTV" in title

            with st.expander(f"{icon} {title}", expanded=expanded):
                st.markdown(content)
    else:
        # Fallback — show as raw text
        with st.expander("Research Brief", expanded=True):
            st.text(brief)


# ── INPUT FORM ────────────────────────────────────────────────────────────────

col1, col2 = st.columns(2)

with col1:
    business_name = st.text_input(
        "Business Name *",
        placeholder="Bottletree Bakery",
        help="The prospect's business name.",
    )
    industry = st.text_input(
        "Industry *",
        placeholder="Bakery / Coffee Shop",
        help="What type of business is this?",
    )
    city = st.selectbox(
        "City",
        market_names + ["Other"],
        help="Where is this business located?",
    )
    if city == "Other":
        city = st.text_input("City Name", placeholder="Grenada")

with col2:
    website_url = st.text_input(
        "Website URL (optional but recommended)",
        placeholder="https://www.bottletreebakery.com",
        help="We'll scan their website for intel. Leave blank if unknown.",
    )
    sales_rep = st.selectbox("Sales Rep", team_names, index=1)
    additional_notes = st.text_area(
        "Additional Context (optional)",
        placeholder=(
            "Met the owner at Chamber event. They mentioned radio ads aren't working. "
            "They have 2 locations. Competitor across the street already advertises with us."
        ),
        height=100,
        help="Anything you already know — the more context, the better the brief.",
    )

st.divider()


# ── GENERATE BUTTON ───────────────────────────────────────────────────────────

if st.button(
    "\U0001F50D Generate Research Brief",
    type="primary",
    use_container_width=True,
):
    if not business_name or not industry:
        st.error("Please fill in at least Business Name and Industry.")
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key or api_key == "your-api-key-here":
            st.error(
                "ANTHROPIC_API_KEY not configured. Set it in Settings or .env file."
            )
        else:
            model = config.get("proposal_settings", {}).get(
                "model", "claude-sonnet-4-5-20250929"
            )
            claude = ClaudeService(api_key=api_key, model=model)

            # ── Step 1: Scrape website ────────────────────────────────
            website_data = (
                "No website provided — analysis based on industry and city only."
            )
            scraped_images = []

            if website_url:
                progress = st.progress(0, text="Scanning prospect website...")
                from services.web_scraper import (
                    scrape_website_text,
                    scrape_website_images,
                )

                site_info = scrape_website_text(website_url)
                if site_info:
                    parts = []
                    if site_info.get("title"):
                        parts.append(f"Page Title: {site_info['title']}")
                    if site_info.get("description"):
                        parts.append(
                            f"Meta Description: {site_info['description']}"
                        )
                    if site_info.get("phone"):
                        parts.append(f"Phone Found: {site_info['phone']}")
                    if site_info.get("email"):
                        parts.append(f"Email Found: {site_info['email']}")
                    if site_info.get("address"):
                        parts.append(f"Address Found: {site_info['address']}")
                    if site_info.get("social_links"):
                        parts.append(
                            f"Social Profiles: {', '.join(site_info['social_links'][:5])}"
                        )
                    if site_info.get("headings"):
                        parts.append(
                            f"Key Headings: {' | '.join(site_info['headings'][:10])}"
                        )
                    if site_info.get("body_text"):
                        body = site_info["body_text"][:4000]
                        parts.append(f"Page Content (excerpt): {body}")
                    website_data = "\n".join(parts)
                    progress.progress(
                        0.3, text="Website scanned. Checking for images..."
                    )
                else:
                    progress.progress(
                        0.3,
                        text="Could not scrape website. Proceeding with industry analysis...",
                    )
                    website_data = (
                        f"Website ({website_url}) could not be scraped — "
                        "analysis based on industry and city only."
                    )

                scraped_images = scrape_website_images(website_url, max_images=6)
                progress.progress(0.5, text="Generating competitive brief...")
            else:
                progress = st.progress(
                    0.5, text="Generating competitive brief..."
                )

            # ── Step 2: Build prompt and call Claude ──────────────────
            prompt = claude.build_section_prompt(
                "prospect_research",
                "competitive_brief",
                {
                    "business_name": business_name,
                    "industry": industry,
                    "city": city,
                    "website_url": website_url or "Not provided",
                    "website_data": website_data,
                    "additional_notes": additional_notes
                    or "No additional context provided.",
                },
            )

            try:
                brief = claude.generate_section(prompt, max_tokens=3000)
                progress.progress(1.0, text="Complete!")

                st.success(f"Research brief generated for {business_name}!")
                st.caption(f"API Usage: {claude.usage_summary}")

                # ── Store in session state ────────────────────────────
                st.session_state["research_brief"] = brief
                st.session_state["research_data"] = {
                    "business_name": business_name,
                    "industry": industry,
                    "city": city,
                    "website_url": website_url,
                    "sales_rep": sales_rep,
                    "additional_notes": additional_notes,
                    "generated_at": datetime.now().isoformat(),
                }

                # ── Show scraped images ───────────────────────────────
                if scraped_images:
                    with st.expander(
                        f"Website Images ({len(scraped_images)} found)",
                        expanded=False,
                    ):
                        img_cols = st.columns(min(len(scraped_images), 4))
                        for i, img in enumerate(scraped_images):
                            with img_cols[i % 4]:
                                try:
                                    st.image(
                                        img["url"],
                                        caption=img.get(
                                            "alt", img["filename"]
                                        )[:30],
                                        use_container_width=True,
                                    )
                                except Exception:
                                    st.caption(
                                        f"Could not load: {img['filename']}"
                                    )

                # ── Display parsed brief ──────────────────────────────
                _display_brief(brief, business_name)

                # ── Export options ─────────────────────────────────────
                st.divider()
                st.markdown("#### Export & Actions")
                exp_col1, exp_col2, exp_col3 = st.columns(3)

                safe_name = business_name.replace(" ", "_").replace("'", "")
                date_str = datetime.now().strftime("%Y-%m-%d")

                # Download as .txt
                with exp_col1:
                    header = f"MCTV PROSPECT RESEARCH BRIEF\n{'=' * 40}\n"
                    header += f"Business: {business_name}\n"
                    header += f"Industry: {industry}\n"
                    header += f"City: {city}\n"
                    header += f"Website: {website_url or 'N/A'}\n"
                    header += f"Generated: {datetime.now().strftime('%B %d, %Y')}\n"
                    header += f"Rep: {sales_rep}\n"
                    header += f"{'=' * 40}\n\n"
                    full_export = header + brief

                    st.download_button(
                        "Download Brief (.txt)",
                        data=full_export,
                        file_name=f"MCTV_Research_{safe_name}_{date_str}.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )

                # Use in Proposal
                with exp_col2:
                    if st.button(
                        "Use in Proposal \u2192",
                        use_container_width=True,
                        help="Pre-fill the proposal form with this research data",
                    ):
                        st.session_state["prefill_proposal"] = {
                            "business_name": business_name,
                            "industry": industry,
                            "city": city,
                            "contact_email": "",
                            "sales_rep": sales_rep,
                            "additional_notes": (
                                f"RESEARCH CONTEXT: {additional_notes}\n\n"
                                f"KEY INSIGHTS FROM BRIEF:\n{brief[:500]}"
                            ),
                            "website_url": website_url,
                        }
                        st.switch_page("pages/1_Proposals.py")

                # Download as JSON
                with exp_col3:
                    research_json = json.dumps(
                        {
                            "business_name": business_name,
                            "industry": industry,
                            "city": city,
                            "website_url": website_url,
                            "sales_rep": sales_rep,
                            "additional_notes": additional_notes,
                            "brief": brief,
                            "generated_at": datetime.now().isoformat(),
                        },
                        indent=2,
                    )
                    st.download_button(
                        "Download JSON",
                        data=research_json,
                        file_name=f"MCTV_Research_{safe_name}_{date_str}.json",
                        mime="application/json",
                        use_container_width=True,
                    )

            except Exception as e:
                progress.empty()
                st.error(f"Error generating brief: {str(e)}")
                st.exception(e)


# ── SHOW PREVIOUS BRIEF ──────────────────────────────────────────────────────

if (
    "research_brief" in st.session_state
    and "research_data" in st.session_state
):
    data = st.session_state["research_data"]
    st.divider()
    st.markdown(f"### Previous Research: {data['business_name']}")
    st.caption(
        f"Generated {data.get('generated_at', 'earlier')[:16]} | "
        f"Industry: {data['industry']} | City: {data['city']}"
    )
    _display_brief(st.session_state["research_brief"], data["business_name"])
