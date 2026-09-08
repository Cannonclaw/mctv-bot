# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Shared NIL / athlete partnership section renderers.

Three documents show NIL content: the full NIL Partnership proposal, the
one-page handout, and the optional page inside the Elite Advertiser proposal.
They all render from here so the copy and the compliance language cannot
drift apart.

Two independent knobs drive every renderer:

  structure     "bundled" | "addon" | "contribution"  -- how the money is packaged
  tax_language  "plain" | "headline" | "omit"         -- how much tax framing prints

All copy lives in config["nil"] so it is editable without touching code.
"""

from services.config_service import (
    get_all_tiers, get_tier_impressions, calculate_cpm, CPM_BENCHMARK_TEXT,
)

STRUCTURES = ("bundled", "addon", "contribution")
TAX_MODES = ("plain", "headline", "omit")

DEFAULT_STRUCTURE = "bundled"
DEFAULT_TAX = "plain"


# ── Accessors / normalizers ──────────────────────────────────────────────────

def nil_config(config: dict) -> dict:
    """The config["nil"] block, or an empty dict if it isn't configured."""
    return config.get("nil", {}) or {}


def normalize_structure(value: str) -> str:
    """Coerce an unknown structure key to the safest default."""
    return value if value in STRUCTURES else DEFAULT_STRUCTURE


def normalize_tax(value: str) -> str:
    """Coerce an unknown tax key to the safest default."""
    return value if value in TAX_MODES else DEFAULT_TAX


def collective_name(config: dict, override: str = "") -> str:
    """Collective name, preferring a per-proposal override."""
    if override:
        return override
    return nil_config(config).get("collective", {}).get("name", "the collective")


def consented_voices(config: dict) -> list:
    """Athlete testimonials cleared for print.

    The consent gate is deliberately structural: a quote without a signed
    release on file cannot reach a generated document, no matter what the
    rest of the config says.
    """
    voices = nil_config(config).get("athlete_voices", []) or []
    return [v for v in voices if v.get("consent_on_file") is True]


def _attribution(voice: dict) -> str:
    """Build the 'Name, Sport' byline for a testimonial card."""
    parts = [voice.get("name", "").strip()]
    detail = " — ".join(
        p for p in (voice.get("sport", "").strip(), voice.get("school", "").strip()) if p
    )
    if detail:
        parts.append(detail)
    return ", ".join(p for p in parts if p)


# ── Section renderers ────────────────────────────────────────────────────────

def render_intro(docx, doc, config, collective: str):
    """Collective blurb + the 'here is the objection' paragraph.

    Naming the pay-for-play objection outright converts better with this
    buyer than an all-positive page, which reads as naive to anyone who has
    followed college sports for the last few years.
    """
    cfg = nil_config(config)
    blurb = cfg.get("collective", {}).get("blurb", "")
    if blurb:
        try:
            blurb = blurb.format(collective=collective)
        except (KeyError, IndexError):
            pass  # stray braces in hand-edited config — print it as written
        docx.add_body_text(doc, blurb)

    objection = cfg.get("objection", "")
    if objection:
        docx.add_callout_box(doc, objection)


def render_value_props(docx, doc, config):
    """The four 'why this one is different' accent cards."""
    for prop in nil_config(config).get("value_props", []) or []:
        title = prop.get("title", "").strip()
        body = prop.get("body", "").strip()
        if title:
            docx.add_accent_card(doc, title, body)


def render_how_it_works(docx, doc, config, structure: str, header: str = "How It Works",
                        new_page: bool = False):
    """Numbered mechanic for the selected structure."""
    structure = normalize_structure(structure)
    steps = nil_config(config).get("how_it_works", {}).get(structure, []) or []
    if not steps:
        return False

    if header:
        docx.add_section_header(doc, header, new_page=new_page)

    for step in steps:
        # Config stores each step as "Title: Body" so it renders as a
        # scannable selling point rather than a wall of text.
        title, _, body = step.partition(":")
        docx.add_selling_point(doc, title.strip(), body.strip())
    return True


def render_athlete_voices(docx, doc, config, limit: int = None,
                          header: str = "In Their Words", new_page: bool = False):
    """Consent-gated athlete testimonials. Returns True if anything rendered.

    Renders nothing at all (including the header) when no athlete has a
    release on file, so an unreleased quote can never ship by accident.
    """
    voices = consented_voices(config)
    if limit is not None:
        voices = voices[:limit]
    if not voices:
        return False

    if header:
        docx.add_section_header(doc, header, new_page=new_page)

    for voice in voices:
        quote = voice.get("quote", "").strip()
        if not quote:
            continue
        docx.add_accent_card(doc, _attribution(voice), f"“{quote}”")
    return True


def render_packages(docx, doc, config, structure: str, header: str = "Packages",
                    new_page: bool = False, show_cpm: bool = True):
    """Pricing, laid out per structure.

    bundled       one athlete-featured table, single price per package.
    addon         standard MCTV rate card, then priced athlete tiers on top.
    contribution  standard MCTV rate card, then an open support amount.
    """
    structure = normalize_structure(structure)
    cfg = nil_config(config)
    packages = cfg.get("packages", {})

    if header:
        docx.add_section_header(doc, header, new_page=new_page)

    if structure == "bundled":
        rows = [
            [
                p.get("name", ""),
                f"${p.get('monthly_rate', 0):,.0f}/mo",
                f"{p.get('screens', 0)}",
                f"{p.get('athletes', 0)}",
                p.get("includes", ""),
            ]
            for p in packages.get("bundled", []) or []
        ]
        if rows:
            docx.add_data_table(
                doc,
                ["Package", "Monthly", "Screens", "Athletes", "What's Included"],
                rows,
            )
        docx.add_callout_box(
            doc,
            "One price covers the media and the athlete. Every package includes "
            "the creative, the proof-of-play reporting, and the signed deal memo."
        )
        return

    # Both "addon" and "contribution" start from the standard rate card, so the
    # media half of the spend is priced exactly like any other MCTV campaign.
    docx.add_sub_header(doc, "YOUR MCTV ADVERTISING")
    tiers = get_all_tiers(config)
    docx.add_pricing_table(doc, tiers, recommended_idx=1 if len(tiers) > 1 else None)

    if show_cpm:
        cpm_parts = []
        for tier in tiers:
            tier_imp = get_tier_impressions(config, tier["screens"])
            tier_cpm = calculate_cpm(tier["monthly_rate"], tier_imp)
            if tier_cpm > 0:
                cpm_parts.append(f"{tier['name']}: ${tier_cpm:.2f}")
        if cpm_parts:
            docx.add_callout_box(
                doc,
                f"Your CPM (Cost Per 1,000 Impressions):  "
                f"{'  |  '.join(cpm_parts)}\n{CPM_BENCHMARK_TEXT}"
            )

    if structure == "addon":
        docx.add_sub_header(doc, "ATHLETE TIERS")
        rows = [
            [
                p.get("name", ""),
                f"${p.get('monthly_rate', 0):,.0f}/mo",
                f"{p.get('athletes', 0)}",
                p.get("includes", ""),
            ]
            for p in packages.get("addon", []) or []
        ]
        if rows:
            docx.add_data_table(
                doc, ["Tier", "Monthly", "Athletes", "What's Included"], rows,
            )
        docx.add_callout_box(
            doc,
            "Pick the tier that fits. Each one is a set price for a set amount "
            "of athlete work, so you know exactly what you are buying."
        )
        return

    # contribution
    contrib = packages.get("contribution", {}) or {}
    docx.add_sub_header(doc, "SUPPORTING THE COLLECTIVE")
    note = contrib.get("note", "")
    if note:
        docx.add_body_text(doc, note)
    levels = contrib.get("suggested_levels", []) or []
    if levels:
        docx.add_callout_box(
            doc,
            "Common support levels:  "
            + "  |  ".join(f"${lvl:,.0f}/mo" for lvl in levels)
            + "  |  Or name your own."
        )


def render_receipts(docx, doc, config, monthly_rate: float, screens: int,
                    business_name: str = "", header: str = "The Receipts",
                    new_page: bool = False):
    """Network metrics, media comparison, and the ROI/CPM projection.

    This is the section that turns the pitch into documentation: it is the
    same proof-of-value math the rest of the product line already uses.
    """
    if header:
        docx.add_section_header(doc, header, new_page=new_page)

    network = config["network"]
    docx.add_metrics_banner(doc, {
        network["total_screens"]: "Screens Across\nNorth Mississippi",
        network["monthly_impressions"]: "Monthly Impressions",
        f"{network['avg_dwell_time_minutes']}+ Min": "Avg. Dwell Time\nPer Visit",
        f"{network['plays_per_hour']}x/Hour": "Your Ad Plays\nEvery Hour",
    })

    if monthly_rate > 0 and screens > 0:
        impressions = get_tier_impressions(config, screens)
        docx.add_competitive_comparison(doc, monthly_rate, screens, impressions)
        docx.add_roi_projection(
            doc, monthly_rate, screens, impressions, business_name=business_name,
        )


def render_tax_block(docx, doc, config, tax_language: str, with_disclaimer: bool = True):
    """The tax paragraph. Returns True if anything printed.

    Under "omit" nothing prints at all -- not the paragraph and not the
    disclaimer -- so the document carries no tax framing whatsoever.
    """
    tax_language = normalize_tax(tax_language)
    if tax_language == "omit":
        return False

    cfg = nil_config(config)
    text = cfg.get("tax_language", {}).get(tax_language, "")
    if not text:
        return False

    docx.add_callout_box(doc, text)
    if with_disclaimer:
        disclaimer = cfg.get("disclaimer", "")
        if disclaimer:
            docx.add_body_text(doc, disclaimer)
    return True


def render_compliance(docx, doc, config, tax_language: str,
                      header: str = "How This Stays Clean",
                      new_page: bool = False):
    """Compliance bullets plus the tax block.

    The compliance points print regardless of the tax setting -- they are what
    makes the deal survive NIL Go review, which matters to the client whether
    or not their accountant ever sees the document.
    """
    points = nil_config(config).get("compliance_points", []) or []
    show_tax = normalize_tax(tax_language) != "omit"
    if not points and not show_tax:
        return False

    if header:
        docx.add_section_header(doc, header, new_page=new_page)

    if points:
        # Config stores each point as "Title: Body", which is the format
        # add_bullet_list() parses into bold-title bullets.
        docx.add_bullet_list(doc, "\n".join(f"- {p}" for p in points))

    render_tax_block(docx, doc, config, tax_language)
    return True
