#!/usr/bin/env python3
# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Generate the Starkville Athletic Club leave-behind PDF.

Client-facing companion to handoffs/starkville-athletic-club/PITCH-BRIEF.md.
Built for Joe Underwood (owner) ahead of the 2026-08-12 meeting.

Offline by design — hand-written copy, no Claude API call, same pattern as
scripts/generate_samples_offline.py. Run from the project root:

    python scripts/generate_sac_pitch.py

Output lands in output/proposals/ (gitignored). This document CONTAINS PRICING
and is client-specific: it must never be published to the Samples page or any
public route.

Every figure below is sourced from data/network_dashboard.json (NTV360 measured),
static/rates.html (v2.0 rate model), or config/config.json. See section 10 of the
pitch brief for the full source table.
"""

import io
import sys
from pathlib import Path
from datetime import datetime

# Force UTF-8 on Windows terminals (MEMORY.md lesson #22)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from services.config_service import load_config, get_team_member
from services.docx_service import DocxService
from services.pdf_service import convert_docx_to_pdf

OUTPUT_DIR = ROOT / "output" / "proposals"

CLIENT = "Starkville Athletic Club"
CONTACT = "Joe Underwood"
SALES_REP = "T. Creed Cannon"
HOST_SCREENS = 5

# ── Measured figures (data/network_dashboard.json, refreshed 2026-02-24) ─────
SV_VENUES = 25
SV_SCREENS = 31
SV_IMPRESSIONS = 491_448
SV_DWELL = 51.8
SV_TRAFFIC = 104_465

# Network-measured gym averages across Built Different Fitness, Rebel Body
# Fitness, and CrossFit Tupelo — the three fitness venues on the network.
GYM_TRAFFIC = 4_786
GYM_DWELL = 57.1
GYM_IMPR_PER_SCREEN = 18_221

# ── The $199 block: Starkville's longest-dwell rooms ─────────────────────────
BLOCK = [
    ("Skate Odyssey", "Family Recreation", "1", "94.6 min"),
    ("BJ's Family Pharmacy", "Pharmacy", "1", "64.0 min"),
    ("Two Brothers Smoked Meats", "Restaurant", "3", "56.7 min"),
    ("Mississippi Ice Daiquiri Shop", "Bar & Restaurant", "1", "56.7 min"),
    ("Hobie's Tiki Dawgs & Daqs", "Bar & Restaurant", "1", "56.7 min"),
    ("Umi Japanese Steakhouse", "Restaurant", "1", "56.7 min"),
    ("The Breakfast Club", "Restaurant", "1", "56.7 min"),
    ("Arepas Coffee & Bar", "Coffee & Bar", "1", "56.7 min"),
]
BLOCK_SCREENS = 10
BLOCK_IMPRESSIONS = 146_844  # conservative rates.html v2.0 model


def build(config: dict, scheme: str = "original") -> Path:
    """Build the Starkville Athletic Club leave-behind .docx."""
    docx = DocxService(config, color_scheme=scheme)
    docx.preparer_name = SALES_REP
    doc = docx.create_document()
    rep = get_team_member(config, SALES_REP)

    pricing = config["pricing"]
    network = config["network"]
    inside_plays = pricing["host_free_inside_plays_per_hour"]
    outside_plays = pricing["host_outside_plays_per_hour"]
    free_outside = pricing["host_free_outside_screens"]
    hours, days = network["hours_per_day"], network["days_per_month"]

    inside_monthly = inside_plays * hours * days * HOST_SCREENS
    outside_monthly = outside_plays * hours * days * free_outside
    total_plays = inside_monthly + outside_monthly

    # ── Cover ────────────────────────────────────────────────────────────────
    docx.add_cover_page(
        doc,
        title="Host\nPartnership",
        subtitle=CLIENT,
        prepared_for=CONTACT,
        prepared_by=rep,
    )

    # ── The Opportunity ──────────────────────────────────────────────────────
    docx.add_section_header(doc, "The Opportunity")
    docx.add_body_text(
        doc,
        f"Joe, thank you for reaching out. Here is what we would like to build with "
        f"{CLIENT}.\n\n"
        f"MCTV runs the largest indoor digital billboard network in North Mississippi. "
        f"In Starkville that is {SV_VENUES} local businesses and {SV_SCREENS} screens — "
        f"restaurants, clinics, pharmacies, salons, and shops where people sit still. "
        f"We would like to add your club to it, at no cost to you."
    )

    docx.add_selling_point(
        doc, "There is not one gym on a Starkville screen",
        "Every fitness business on our network today is in Oxford or Tupelo. The category "
        "is wide open here, and you are the first gym owner we have talked to about it.",
    )
    docx.add_selling_point(
        doc, "Gyms are the best rooms we have",
        f"Across our network, fitness venues average {GYM_DWELL} minutes of dwell time and "
        f"{GYM_TRAFFIC:,} visits a month. Your members come back several times a week and "
        f"stay the better part of an hour. Almost nothing else on the network does that.",
    )
    docx.add_selling_point(
        doc, "Nobody scrolls past it",
        "These ads cannot be skipped, blocked, or muted. They play on a screen in a room "
        "where somebody is already waiting.",
    )

    docx.add_metrics_banner(doc, {
        f"{SV_VENUES}": "Starkville\nVenues",
        f"{SV_SCREENS}": "Starkville\nScreens",
        f"{SV_IMPRESSIONS/1000:,.0f}K": "Monthly\nImpressions",
        f"{SV_DWELL:.0f} Min": "Average Dwell\nPer Visit",
    })

    # ── Your Free Host Package ───────────────────────────────────────────────
    docx.add_section_header(doc, "Your Free Host Package", new_page=True)
    docx.add_body_text(
        doc,
        f"We install {HOST_SCREENS} screens at {CLIENT} at no cost to you. Not the "
        f"hardware, not the installation, not the content, not the management. We handle "
        f"all of it, and it stays free for as long as you host."
    )

    docx.add_accent_card(
        doc, "At your club",
        f"Your own ad plays {inside_plays} times per hour on all {HOST_SCREENS} screens — "
        f"{inside_monthly:,} plays a month in front of your members. Promote personal "
        f"training, class schedules, guest passes, or whatever you are pushing that month. "
        f"We update it for you.",
    )
    docx.add_accent_card(
        doc, "Across Starkville",
        f"You also get free advertising on {free_outside} additional screens around town at "
        f"{outside_plays} plays per hour — {outside_monthly:,} plays a month reaching people "
        f"who have never walked into your club. That piece alone is a $350 per month package "
        f"at our published rates.",
    )
    docx.add_accent_card(
        doc, "Content included, and it is yours",
        "Our team designs your ads at no charge and refreshes them quarterly. Everything we "
        "make for you belongs to you — use it on social, your website, print, anywhere you "
        "want, at no additional cost.",
    )

    docx.add_metrics_banner(doc, {
        "$0": "Your Monthly\nCost",
        f"{HOST_SCREENS}": "Screens at\nYour Club",
        f"{free_outside}": "Free Screens\nAround Starkville",
        f"{total_plays:,}": "Ad Plays\nPer Month",
    })
    docx.add_callout_box(
        doc,
        f"{total_plays:,} ad plays every month, at no cost to you, for as long as you host."
    )

    # ── Expanding Your Reach ─────────────────────────────────────────────────
    docx.add_section_header(doc, "Expanding Your Reach", new_page=True)
    docx.add_body_text(
        doc,
        "The host package above is free and stays free. If you want to reach further into "
        "Starkville than the ten screens it includes, here is what that looks like. Both "
        "options are host-partner rates, well under our published pricing."
    )

    docx.add_sub_header(doc, "STARKVILLE HOST RATE — $199/MONTH")
    docx.add_body_text(
        doc,
        f"Your ad runs across a {BLOCK_SCREENS}-screen block of Starkville's longest-dwell "
        f"venues — roughly {BLOCK_IMPRESSIONS:,} impressions a month. Our published rate "
        f"for ten screens is $350. As a host partner, yours is $199."
    )
    docx.add_data_table(
        doc,
        ["Venue", "Type", "Screens", "Avg. Dwell"],
        [[n, t, s, d] for n, t, s, d in BLOCK],
    )

    docx.add_sub_header(doc, "FULL STARKVILLE TERRITORY — $599/MONTH")
    docx.add_body_text(
        doc,
        f"Every screen we have in Starkville — all {SV_VENUES} venues and {SV_SCREENS} "
        f"screens, about {SV_IMPRESSIONS:,} impressions a month. This is the option if you "
        f"want your club in front of essentially everyone in town who eats out, fills a "
        f"prescription, or gets their hair cut."
    )

    docx.add_sub_header(doc, "PARTNERSHIP TERMS")
    docx.add_contract_terms(doc, config)

    # ── Category Exclusivity ─────────────────────────────────────────────────
    docx.add_section_header(doc, "Fitness Category Exclusivity", new_page=True)
    docx.add_body_text(
        doc,
        "Right now there is not a single gym on a Starkville screen. That will not stay "
        "true — we are opening a run of Starkville partnerships this fall. Category "
        "exclusivity is how you make sure the gym on those screens is yours."
    )

    docx.add_accent_card(
        doc, "What it locks",
        "For as long as your agreement runs, MCTV will not display advertising from any "
        "competing gym, fitness studio, health club, or personal training facility on any "
        "Starkville screen. In writing, in the contract.",
    )
    docx.add_accent_card(
        doc, "What it does not cover",
        "Supplement and nutrition retail, med-spas, wellness clinics, and physical therapy "
        "are outside the category. Two of them — 39759 Nutrition and Revive Wellness "
        "Clinic — are existing host venues in Starkville and will keep running their own "
        "ads. We would rather tell you that now than have it be a surprise later.",
    )
    docx.add_accent_card(
        doc, "If we ever slip",
        "If competing content reaches a covered screen, we remove it within 24 hours of "
        "you telling us, and you are credited for the period it ran.",
    )
    docx.add_callout_box(
        doc,
        "Fitness category exclusivity across Starkville: $200 per month, added to any "
        "advertising package above. Twelve-month minimum term."
    )

    # ── MSU Season Sponsorship ───────────────────────────────────────────────
    sponsorships = config.get("sponsorship_packages", [])
    msu = next((s for s in sponsorships if s.get("key") == "msstate_football"), None)
    if msu:
        docx.add_section_header(doc, "Mississippi State Season Sponsorship")
        docx.add_body_text(
            doc,
            f"One more thing worth knowing. We do not currently have a sponsor tied to "
            f"Mississippi State athletics, and the season starts next month.\n\n"
            f"{msu['description']}"
        )
        docx.add_callout_box(
            doc,
            f"{msu['name']} — {msu['screens']} Starkville screens, "
            f"{msu['term_months']} months (September through bowl season). "
            f"List rate ${msu['monthly_rate']:,}/month. "
            f"Offered to you as a founding host partner at $599/month."
        )

    # ── How MCTV Compares ────────────────────────────────────────────────────
    docx.add_section_header(doc, "How MCTV Compares", new_page=True)
    docx.add_body_text(
        doc,
        "Here is the $199 Starkville host rate measured against what else you could buy "
        "with the same money. CPM is cost per thousand people reached — the standard way "
        "to compare advertising across very different channels."
    )
    docx.add_competitive_comparison(
        doc, monthly_rate=199, screen_count=BLOCK_SCREENS,
        monthly_impressions=BLOCK_IMPRESSIONS,
    )

    # ── The MCTV Network ─────────────────────────────────────────────────────
    docx.add_section_header(doc, "The MCTV Network", new_page=True)
    docx.add_social_proof_section(doc)
    docx.add_sub_header(doc, "WHERE YOUR ADS PLAY")
    docx.add_venue_categories(doc)

    # ── Getting Started ──────────────────────────────────────────────────────
    docx.add_section_header(doc, "Getting Started")
    docx.add_body_text(
        doc,
        "1. Walk the club. We come out, look at your space, and agree on where the "
        f"{HOST_SCREENS} screens go. Usually the front desk, the cardio floor, and the "
        "areas where members wait.\n"
        "2. Sign the hosting agreement. One page of real terms, no cost to you.\n"
        "3. We install. Typically within two weeks of signing.\n"
        "4. We build your content. You approve it before anything goes live.\n"
        "5. You get a traction report every month — plays, venues, impressions, and cost "
        "per thousand, straight from our NTV360 dashboard. No guessing whether it worked."
    )
    docx.add_callout_box(
        doc,
        f"{rep['name']}  |  {rep['email']}  |  {rep['phone']}  |  "
        f"MCTV Elite Advertising  |  MCTVofMS.com"
    )

    # ── Team + footer ────────────────────────────────────────────────────────
    docx.add_team_section(
        doc,
        closing_text="We would be glad to have Starkville Athletic Club on the network.",
    )
    docx.add_footer(doc)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    path = OUTPUT_DIR / f"MCTV_Starkville_Athletic_Club_{stamp}.docx"
    doc.save(str(path))
    return path


def main():
    print()
    print("=" * 62)
    print("  Starkville Athletic Club — Host Partnership Leave-Behind")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)
    print()
    print("  CLIENT-SPECIFIC — contains pricing. Never publish this document.")
    print()

    config = load_config()
    docx_path = build(config)
    print(f"  DOCX  {docx_path.name}  ({docx_path.stat().st_size:,} bytes)")

    pdf_path = convert_docx_to_pdf(docx_path)
    if pdf_path and pdf_path.exists():
        print(f"  PDF   {pdf_path.name}  ({pdf_path.stat().st_size:,} bytes)")
    else:
        print("  PDF   conversion unavailable — install LibreOffice or convert manually")

    print()
    print(f"  Saved to: {OUTPUT_DIR}")
    print()


if __name__ == "__main__":
    main()
