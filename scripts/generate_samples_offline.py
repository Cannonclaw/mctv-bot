#!/usr/bin/env python3
# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
"""Generate sample proposal PDFs WITHOUT requiring Claude API.

Uses pre-written content for each industry sample. Run from project root:
    python scripts/generate_samples_offline.py

Generates 4 industry sample PDFs in all 4 color schemes -> assets/samples/
IMPORTANT: Sample proposals exclude the pricing section.
"""

import io
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from models.proposal_data import ProposalInput
from services.config_service import load_config, get_team_member, get_all_tiers
from services.docx_service import DocxService, COLOR_SCHEMES


# ── PRE-WRITTEN CONTENT PER INDUSTRY ────────────────────────────────────────

CONTENT = {
    "restaurant": {
        "opportunity_intro": (
            "Oxford's dining scene is thriving, but standing out takes more than a great menu. "
            "Southern Table Kitchen & Bar has the food and the atmosphere. Now it is time "
            "to put your brand in front of the thousands of local consumers who visit MCTV "
            "venues every single day."
        ),
        "opportunity_points": [
            ("Captive Dining Audiences",
             "Your ad plays in barbershops, gyms, and medical offices where customers "
             "sit for 55+ minutes on average. That is 55 minutes of repeated exposure "
             "to your brand and daily specials."),
            ("Peak Hour Targeting",
             "MCTV screens run 12 hours a day, hitting the lunch and dinner crowds "
             "exactly when they are deciding where to eat. Your ad plays 4 times "
             "per hour on every screen in your package."),
            ("Community Credibility",
             "Appearing on screens across Oxford builds trust and familiarity. "
             "When locals see your brand everywhere they go, Southern Table becomes "
             "the obvious choice for their next meal out."),
        ],
        "included_items": [
            ("15-Second Ad Slot",
             "Your custom-designed ad runs on a 15-minute content loop, playing 4 times "
             "per hour, 12 hours a day, 7 days a week across every screen in your package."),
            ("Professional Creative Design",
             "Our team designs your ad at no extra cost. We handle everything from concept "
             "to final production. Quarterly refreshes keep your message seasonal and current."),
            ("NTV360 Analytics Dashboard",
             "Real-time dashboard access showing plays, impressions, venue performance, "
             "and campaign analytics. See exactly where your ads are running and how often."),
            ("Content Ownership",
             "Every ad we create belongs to you. Use it on social media, your website, "
             "or anywhere else. Your investment extends beyond the screens."),
        ],
        "market_text": (
            "Southern Table's ads will play across Oxford's most-visited venues, from "
            "barbershops on the Square to fitness centers near campus. With 75 screens "
            "in Oxford alone, your brand reaches a diverse cross-section of the community "
            "that other local advertising simply cannot match."
        ),
        "why_mctv": [
            ("Unskippable Impressions",
             "Unlike social media ads that get scrolled past or TV spots that get muted, "
             "MCTV ads play on screens in captive environments. Customers cannot skip, "
             "block, or ignore your message."),
            ("Hyper-Local Reach",
             "Every screen is in a local business within your community. Your ad appears "
             "alongside the trusted venues your customers already frequent, building "
             "credibility by association."),
            ("Unbeatable Value",
             "At a CPM of $1-3, MCTV delivers more impressions per dollar than radio, "
             "print, cable TV, or outdoor billboards. Your advertising budget works "
             "harder and reaches farther."),
        ],
        "getting_started": (
            "Getting started is simple. Choose your package, and our team handles "
            "everything from ad design to screen placement. Most campaigns are live "
            "within 5 business days. Your dedicated account representative will guide "
            "you through every step and answer any questions along the way."
        ),
    },
    "salon": {
        "opportunity_intro": (
            "In a market crowded with grooming options, brand recognition is everything. "
            "Blades & Fades has earned a reputation for quality. Indoor digital billboard "
            "advertising puts your brand in front of thousands of potential clients "
            "across Oxford and Starkville every day."
        ),
        "opportunity_points": [
            ("Two-Market Dominance",
             "With locations in both Oxford and Starkville, Blades & Fades can blanket "
             "both college towns simultaneously. Your ad plays in restaurants, gyms, "
             "and offices where your ideal customers spend their time."),
            ("Repeat Exposure Builds Loyalty",
             "The average MCTV venue visitor spends 55+ minutes per visit. Your ad "
             "plays multiple times during each visit, building the kind of familiarity "
             "that turns first-time visitors into regulars."),
            ("Student and Professional Reach",
             "MCTV screens are in venues frequented by both college students and "
             "working professionals, giving Blades & Fades access to the full "
             "spectrum of potential clients in both markets."),
        ],
        "included_items": [
            ("Multi-Screen Ad Placement",
             "Your ad runs across screens in restaurants, medical offices, gyms, and "
             "retail locations. Every screen plays your ad 4 times per hour, all day."),
            ("Branded Creative at No Cost",
             "Our design team creates your ad from scratch. Send us your logo and "
             "any photos, and we will produce a professional, eye-catching ad that "
             "represents your brand perfectly."),
            ("Performance Analytics",
             "Track plays, impressions, and venue data in real time through the "
             "NTV360 dashboard. Know exactly how your campaign is performing."),
            ("Quarterly Content Refreshes",
             "Keep your messaging fresh with complimentary ad updates every quarter. "
             "Promote seasonal specials, new services, or updated branding."),
        ],
        "market_text": (
            "Blades & Fades' ads will play across 105 screens spanning Oxford and "
            "Starkville. From the Square to Cotton District, your brand will be "
            "visible in the venues where your future clients eat, work out, and shop."
        ),
        "why_mctv": [
            ("Built for Local Businesses",
             "MCTV was created specifically for local businesses like Blades & Fades. "
             "No national competition, no algorithmic guessing. Just your ad in front "
             "of your community, all day, every day."),
            ("Zero Waste Advertising",
             "Every impression happens inside a local venue within your service area. "
             "No wasted reach on people 200 miles away. Every play counts."),
            ("Partnership, Not Just Advertising",
             "MCTV is a partner, not just a vendor. We provide creative, analytics, "
             "and strategic support to help Blades & Fades grow."),
        ],
        "getting_started": (
            "Choose your screen package and our team will design your first ad "
            "within 48 hours. We will have your campaign live across both Oxford "
            "and Starkville within one week. Your account representative is available "
            "anytime to help optimize your campaign."
        ),
    },
    "gym": {
        "opportunity_intro": (
            "Starkville's fitness market is competitive, and gym-goers are always "
            "looking for their next challenge. Iron & Oak Fitness has the equipment "
            "and the energy. Indoor digital billboard advertising puts your brand in "
            "front of health-conscious consumers across the entire Starkville market."
        ),
        "opportunity_points": [
            ("Reach Health-Conscious Consumers",
             "Your ad plays in restaurants, offices, and retail locations where "
             "health-minded people spend their time. These are the exact consumers "
             "most likely to try a new gym or fitness class."),
            ("Campus-Adjacent Visibility",
             "With 30 screens near Mississippi State campus, Iron & Oak reaches "
             "students looking for a gym that is more than just a university rec "
             "center. New semester sign-ups start with awareness."),
            ("Year-Round Brand Presence",
             "January resolutions are great, but consistent advertising keeps your "
             "gym top of mind all year. MCTV ads run every day, building the kind "
             "of awareness that drives memberships in every season."),
        ],
        "included_items": [
            ("Targeted Screen Placement",
             "Your ad runs on screens in Starkville's highest-traffic venues. "
             "Restaurants, offices, salons, and retail locations where your future "
             "members are already spending time."),
            ("Custom Video-Quality Ads",
             "Our creative team designs professional, eye-catching ads that showcase "
             "your facility, classes, and brand. No stock photos needed."),
            ("Real-Time Campaign Data",
             "NTV360 analytics show you exactly how many times your ad played, "
             "in which venues, and how many estimated impressions you received."),
            ("Flexible Content Updates",
             "Promote January specials, summer boot camps, or new class schedules. "
             "We update your ad quarterly at no extra cost."),
        ],
        "market_text": (
            "Iron & Oak's ads will play across 30 screens in Starkville, reaching "
            "MSU students, faculty, and local families. Your brand will be visible "
            "in the restaurants, barbershops, and offices where Starkville's most "
            "active residents spend their time."
        ),
        "why_mctv": [
            ("Captive Audience Advertising",
             "People in waiting rooms and restaurants cannot skip your ad. They see "
             "it multiple times during a single visit, building the repetition that "
             "drives action and membership sign-ups."),
            ("Cost-Effective Growth",
             "MCTV delivers more impressions per dollar than any other local "
             "advertising option. At $1-3 CPM, your marketing budget stretches "
             "further than social media, radio, or print."),
            ("Community Integration",
             "Your ad appears alongside Starkville's most trusted local businesses. "
             "This builds credibility and positions Iron & Oak as a community "
             "staple, not just another gym."),
        ],
        "getting_started": (
            "Select your screen package, send us your logo and any gym photos, and "
            "we will have your ad designed and live within one week. Most clients "
            "see their first campaign analytics within 30 days. Your dedicated "
            "representative is here to help every step of the way."
        ),
    },
    "auto": {
        "opportunity_intro": (
            "Every car on the road in Tupelo will eventually need service. Precision "
            "Auto Care has the expertise and the reputation. Indoor digital billboard "
            "advertising ensures that when that check-engine light comes on, your shop "
            "is the first name that comes to mind."
        ),
        "opportunity_points": [
            ("Top-of-Mind When It Matters",
             "Auto repair is not an impulse purchase. People choose the shop they "
             "remember when their car needs work. MCTV's repeated impressions build "
             "the brand familiarity that drives phone calls."),
            ("Reach Every Driver in Tupelo",
             "With 25 screens across Tupelo's most-visited venues, Precision Auto Care "
             "reaches the full driving population. Your ad plays in restaurants, "
             "offices, gyms, and shops all day, every day."),
            ("New Resident Acquisition",
             "Tupelo is growing. People moving to the area need a trusted mechanic. "
             "MCTV puts Precision Auto Care in front of new residents before your "
             "competitors even know they arrived."),
        ],
        "included_items": [
            ("Full-Market Screen Coverage",
             "Your ad runs across all 25 Tupelo screens in diverse venues. "
             "4 plays per hour, 12 hours a day, reaching thousands of local "
             "drivers every single week."),
            ("Professional Ad Design",
             "Our team creates a clean, trustworthy ad that highlights your services, "
             "certifications, and location. We handle design, revisions, and updates."),
            ("Campaign Analytics",
             "NTV360 dashboard gives you real-time data on plays, impressions, and "
             "venue-level performance. See the ROI on every dollar spent."),
            ("Seasonal Promotions",
             "Promote winter tire specials, back-to-school inspections, or oil change "
             "deals. Quarterly content refreshes keep your message timely."),
        ],
        "market_text": (
            "Precision Auto Care's ads will play across 25 screens throughout Tupelo, "
            "from restaurants on Main Street to fitness centers and professional offices. "
            "Your brand reaches the full cross-section of Tupelo's driving community."
        ),
        "why_mctv": [
            ("Trust Through Repetition",
             "Auto repair customers choose shops they recognize and trust. MCTV's "
             "repeated daily impressions build that trust gradually, so when the need "
             "arises, Precision Auto Care is the obvious call."),
            ("Lowest CPM in Local Advertising",
             "At $1-3 per thousand impressions, MCTV costs less than radio, print, "
             "cable, or digital advertising. More reach for less money means faster "
             "return on your marketing investment."),
            ("Local Business, Local Advertising",
             "MCTV screens are only in local venues within your service area. Every "
             "impression reaches someone who could actually walk through your door. "
             "No wasted spend on out-of-market audiences."),
        ],
        "getting_started": (
            "Choose your package and share your logo and shop photos. Our team "
            "designs your ad and gets it live across Tupelo within 5 business days. "
            "We handle everything so you can focus on running your shop."
        ),
    },
}

# ── SAMPLE BUSINESS DATA ────────────────────────────────────────────────────

SAMPLES = [
    {
        "key": "restaurant",
        "filename_base": "MCTV_Sample_Restaurant",
        "data": ProposalInput(
            business_name="Southern Table Kitchen & Bar",
            contact_name="James Mitchell",
            contact_email="james@southerntable.com",
            industry="Restaurant & Bar",
            city="Oxford",
            selected_markets=["Oxford"],
            sales_rep="Swayze Hollingsworth",
        ),
    },
    {
        "key": "salon",
        "filename_base": "MCTV_Sample_Salon",
        "data": ProposalInput(
            business_name="Blades & Fades Barbershop",
            contact_name="Marcus Williams",
            contact_email="marcus@bladesandfades.com",
            industry="Barbershop & Salon",
            city="Oxford",
            selected_markets=["Oxford", "Starkville"],
            sales_rep="Mary Michael Cannon",
        ),
    },
    {
        "key": "gym",
        "filename_base": "MCTV_Sample_Gym",
        "data": ProposalInput(
            business_name="Iron & Oak Fitness",
            contact_name="Sarah Collins",
            contact_email="sarah@ironandoak.com",
            industry="Gym & Fitness",
            city="Starkville",
            selected_markets=["Starkville"],
            sales_rep="Swayze Hollingsworth",
        ),
    },
    {
        "key": "auto",
        "filename_base": "MCTV_Sample_Auto",
        "data": ProposalInput(
            business_name="Precision Auto Care",
            contact_name="David Thompson",
            contact_email="david@precisionauto.com",
            industry="Auto Repair & Service",
            city="Tupelo",
            selected_markets=["Tupelo"],
            sales_rep="Mary Michael Cannon",
        ),
    },
]

SAMPLES_DIR = ROOT / "assets" / "samples"


def build_sample(config: dict, sample: dict, scheme: str = "original") -> Path:
    """Build a single sample proposal .docx (no pricing, no Claude API)."""
    data = sample["data"]
    content = CONTENT[sample["key"]]

    docx = DocxService(config, color_scheme=scheme)
    docx.preparer_name = data.sales_rep
    doc = docx.create_document()

    # ── Cover page ──
    rep = get_team_member(config, data.sales_rep)
    docx.add_cover_page(
        doc,
        title="ADVERTISING PARTNERSHIP\nPROPOSAL",
        subtitle=data.business_name,
        prepared_for=data.contact_name,
        prepared_by=rep,
    )

    # ── The Opportunity ──
    docx.add_section_header(doc, "The Opportunity")
    docx.add_body_text(doc, content["opportunity_intro"])
    for title, desc in content["opportunity_points"]:
        docx.add_selling_point(doc, title, desc)

    network = config["network"]
    docx.add_metrics_banner(doc, {
        network["total_screens"]: "Screens Across\nNorth Mississippi",
        network["monthly_impressions"]: "Monthly Impressions",
        f"{network['avg_dwell_time_minutes']}+ Min": "Avg. Dwell Time\nPer Visit",
        f"{network['plays_per_hour']}x/Hour": "Your Ad Plays\nEvery Day",
    })

    # ── What's Included ──
    docx.add_section_header(doc, "What's Included", new_page=True)
    for title, desc in content["included_items"]:
        docx.add_accent_card(doc, title, desc)

    # ── Market Coverage ──
    docx.add_section_header(doc, "Your Market Coverage", new_page=True)
    docx.add_body_text(doc, content["market_text"])
    venue_text = (
        "Your ads play in: Restaurants & Bars  |  Barbershops & Salons  |  "
        "Medical & Dental  |  Gyms & Fitness  |  Auto & Service Shops  |  "
        "Retail & Boutiques  |  Professional Offices  |  Community Venues"
    )
    docx.add_callout_box(doc, venue_text)

    # ── How MCTV Compares (no pricing, just competitive table) ──
    docx.add_section_header(doc, "How MCTV Compares")
    docx.add_body_text(
        doc,
        "Local businesses have more advertising options than ever. "
        "Here is how MCTV stacks up against the alternatives."
    )
    docx.add_competitive_comparison(doc, monthly_rate=500, screen_count=20,
                                     monthly_impressions=30000)

    # ── Why MCTV ──
    docx.add_section_header(doc, "Why MCTV", new_page=True)
    for title, desc in content["why_mctv"]:
        docx.add_accent_card(doc, title, desc)

    # ── The MCTV Network ──
    docx.add_section_header(doc, "The MCTV Network", new_page=True)
    proof = config.get("social_proof", {})
    headline = proof.get("headline", "")
    if headline:
        docx.add_body_text(doc, headline)
    docx.add_social_proof_section(doc)
    docx.add_sub_header(doc, "WHERE YOUR ADS PLAY")
    docx.add_venue_categories(doc)

    # ── Getting Started ──
    docx.add_section_header(doc, "Getting Started", new_page=True)
    docx.add_body_text(doc, content["getting_started"])

    # ── Team ──
    docx.add_team_section(doc)

    # ── Footer ──
    docx.add_footer(doc)

    # Save
    scheme_suffix = f"_{scheme}" if scheme != "original" else ""
    filename = f"{sample['filename_base']}{scheme_suffix}.docx"
    filepath = SAMPLES_DIR / filename
    doc.save(str(filepath))
    return filepath


def main():
    print()
    print("=" * 60)
    print("  MCTV Sample Proposal Generator (Offline)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    print("  NOTE: Pricing sections are EXCLUDED from all samples.")
    print("        Pricing is never made publicly available.")
    print()

    config = load_config()
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    # Generate each sample in the "original" color scheme
    # (plus optionally all 4 schemes for variety)
    schemes_to_generate = ["original"]  # Add more: ["original", "light", "dark", "pastel"]

    total = len(SAMPLES) * len(schemes_to_generate)
    count = 0

    for scheme in schemes_to_generate:
        scheme_label = COLOR_SCHEMES[scheme]["label"]
        for sample in SAMPLES:
            count += 1
            name = sample["data"].business_name
            print(f"  [{count}/{total}] {name} ({scheme_label})...", end=" ", flush=True)
            try:
                path = build_sample(config, sample, scheme)
                size = path.stat().st_size
                print(f"OK ({size:,} bytes)")
            except Exception as e:
                print(f"FAIL: {e}")

    print()
    print(f"  Samples saved to: {SAMPLES_DIR}")

    # List generated files
    files = sorted(SAMPLES_DIR.glob("*.docx"))
    if files:
        print(f"  {len(files)} files generated:")
        for f in files:
            print(f"    - {f.name} ({f.stat().st_size:,} bytes)")

    print()
    print("  To convert to PDF, run on Render (Docker w/ LibreOffice)")
    print("  or use docx2pdf locally.")
    print()


if __name__ == "__main__":
    main()
