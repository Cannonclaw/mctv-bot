# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Designed (print-quality) Chamber packet documents.

Builds the Chamber deal one-sheet and the Oxford location sheet as
fixed-canvas HTML (US Letter) with embedded fonts, then prints them to
PDF with headless Chromium. These are the packet-ready versions — the
DocxService generators (generate_chamber_one_sheet.py /
generate_chamber_location_sheet.py) remain for editable Word output.

All figures derive from config/config.json, data/network_dashboard.json,
and data/oxford_chamber_members.json.

Usage:
    python scripts/generate_chamber_packet_designs.py
    python scripts/generate_chamber_packet_designs.py --rate 199 --screens 25
    python scripts/generate_chamber_packet_designs.py --chromium /usr/bin/chromium
"""

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.config_service import load_config, get_tier_impressions, calculate_cpm

PROJECT_ROOT = Path(__file__).parent.parent
FONTS_DIR = PROJECT_ROOT / "assets" / "fonts"
OUTPUT_DIR = PROJECT_ROOT / "output" / "proposals"
DASHBOARD_PATH = PROJECT_ROOT / "data" / "network_dashboard.json"
MEMBERS_PATH = PROJECT_ROOT / "data" / "oxford_chamber_members.json"

NAVY = "#1B1F3B"
GOLD = "#C5A55A"
INK = "#23273D"
MUTED = "#6C7080"
HAIRLINE = "#E4E2DC"
PAPER = "#FFFFFF"
CREAM = "#F7F5F0"
BAR_NAVY = "#565C7E"

FONT_FILES = {
    "playfair-700": ("Playfair Display", 700, "normal", "playfair-display-latin-700-normal.woff2"),
    "playfair-800": ("Playfair Display", 800, "normal", "playfair-display-latin-800-normal.woff2"),
    "playfair-400i": ("Playfair Display", 400, "italic", "playfair-display-latin-400-italic.woff2"),
    "inter-400": ("Inter", 400, "normal", "inter-latin-400-normal.woff2"),
    "inter-500": ("Inter", 500, "normal", "inter-latin-500-normal.woff2"),
    "inter-600": ("Inter", 600, "normal", "inter-latin-600-normal.woff2"),
    "inter-700": ("Inter", 700, "normal", "inter-latin-700-normal.woff2"),
}

# Short display names / category cleanups shared with the DOCX location sheet
NAME_SHORTEN = {
    "Oxford-Lafayette County Chamber of Commerce": "Oxford-Lafayette County Chamber",
    "RedMed Urgent Clinic of Oxford - Jackson Ave": "RedMed Urgent Clinic",
    "Right Track Medical Group - Oxford": "Right Track Medical Group",
    "Uno Mas Tacos y Tequila Jackson Ave": "Uno Mas Tacos y Tequila",
    "The Velvet Ditch - Sports bar & Seafood": "The Velvet Ditch",
    "Internal Medicine Associates of Oxford": "Internal Medicine Associates",
    "4 Corner's Chevron (Chicken On A Stick)": "4 Corner's Chevron",
    "Little Bambini Children's Boutique": "Little Bambini",
    "Cannon Chevrolet Buick Cadillac of Oxford": "Cannon Chevrolet Buick Cadillac",
    "Mississippi Asthma & Allergy Clinic, P.A.": "MS Asthma & Allergy Clinic",
    "Booth's Barbeque and Yard": "Booth's Barbeque & Yard",
    "Rafters Music and Food": "Rafters Music & Food",
    "MARATHON South Lamar": "Marathon South Lamar",
    "Texaco lamar express": "Texaco Lamar Express",
}
CATEGORY_OVERRIDES = {
    "Cannon Chevrolet Buick Cadillac of Oxford": "Auto Dealer",
    "Cannon Collision Center": "Collision Center",
    "Rebel Yell Rooftop Bar": "Rooftop Bar",
}


def esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def font_css() -> str:
    rules = []
    for family, weight, style, filename in FONT_FILES.values():
        data = base64.b64encode((FONTS_DIR / filename).read_bytes()).decode("ascii")
        rules.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"font-style:{style};font-display:block;"
            f"src:url(data:font/woff2;base64,{data}) format('woff2');}}"
        )
    return "\n".join(rules)


def parse_cpm_range(est_cpm: str) -> tuple:
    numbers = [float(n) for n in re.findall(r"[\d.]+", est_cpm)]
    if not numbers:
        return (0.0, 0.0)
    return (numbers[0], numbers[-1])


def money(n: float) -> str:
    return f"${n:,.0f}"


def find_benchmark(config: dict, medium: str) -> dict:
    for b in config.get("industry_benchmarks", {}).get("media_comparison", []):
        if b["medium"] == medium:
            return b
    return {}


# ── Print geometry (US Letter) ────────────────────────────────────────────
TRIM_W, TRIM_H = 8.5, 11.0      # finished size, inches
BLEED = 0.125                    # art extends this far past trim
MARK_ZONE = 0.25                 # room outside the bleed for crop marks
OUTER = BLEED + MARK_ZONE        # trim box offset inside the media box
MEDIA_W = TRIM_W + 2 * OUTER
MEDIA_H = TRIM_H + 2 * OUTER
MARK_LEN = 0.1875                # crop mark length
SIDE_MARGIN = 0.62               # content margin inside trim


def crop_marks_html() -> str:
    """Eight hairline crop marks, offset from trim by the bleed amount."""
    marks = []
    for x_edge, y_edge in ((0, 0), (1, 0), (0, 1), (1, 1)):
        tx = OUTER if x_edge == 0 else OUTER + TRIM_W   # trim line, x
        ty = OUTER if y_edge == 0 else OUTER + TRIM_H   # trim line, y
        # Horizontal mark: sits on the trim's y, runs outward from the bleed edge
        hx = (tx - BLEED - MARK_LEN) if x_edge == 0 else (tx + BLEED)
        marks.append(
            f'<div class="cmark" style="left:{hx:.4f}in;top:{ty:.4f}in;'
            f'width:{MARK_LEN}in;border-top:0.25pt solid #000;"></div>'
        )
        # Vertical mark: sits on the trim's x, runs outward from the bleed edge
        vy = (ty - BLEED - MARK_LEN) if y_edge == 0 else (ty + BLEED)
        marks.append(
            f'<div class="cmark" style="left:{tx:.4f}in;top:{vy:.4f}in;'
            f'height:{MARK_LEN}in;border-left:0.25pt solid #000;"></div>'
        )
    return "".join(marks)


def slug_html(label: str) -> str:
    return (
        f'<div class="slug">{esc(label)} &nbsp;·&nbsp; TRIM {TRIM_W}&Prime; &times; {TRIM_H}&Prime;'
        f' &nbsp;·&nbsp; BLEED {BLEED}&Prime; &nbsp;·&nbsp; CROP MARKS SHOWN &nbsp;·&nbsp; RGB &mdash; CONVERT TO CMYK</div>'
    )


BASE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #DDDDDD; }
.page-canvas {
  position: relative; width: 8.5in; height: 11in;
  background: %(paper)s; overflow: hidden;
  font-family: 'Inter', sans-serif; color: %(ink)s;
  margin: 0 auto;
}
.inner { position: absolute; left: 0.62in; right: 0.62in; top: 0.5in; }
.masthead { display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 7pt; border-bottom: 1.6pt solid %(navy)s; }
.masthead .brand { font-size: 10pt; font-weight: 700; letter-spacing: 0.22em;
  color: %(navy)s; }
.masthead .brand .amp { color: %(gold)s; }
.masthead .prog { font-size: 6.6pt; font-weight: 600; letter-spacing: 0.18em;
  color: %(muted)s; text-transform: uppercase; line-height: 1.35; text-align: right; }
.masthead .mh-right { display: flex; align-items: center; gap: 9pt; }
/* 0.36in = 108px artwork at exactly 300ppi; raising this drops below press minimum */
.masthead .mh-right .ch-logo { height: 0.36in; width: auto; display: block;
  max-width: 1.5in; object-fit: contain; }
.masthead .mh-right .prog { padding-left: 9pt;
  border-left: 0.6pt solid %(hairline)s; }
.kicker { margin-top: 11pt; font-size: 7.2pt; font-weight: 700;
  letter-spacing: 0.24em; color: %(gold_dk)s; text-transform: uppercase; }
.headline { font-family: 'Playfair Display', serif; font-weight: 800;
  color: %(navy)s; margin-top: 7pt; }
.deck { font-size: 9.2pt; line-height: 1.55; color: %(muted)s; font-weight: 400; }
.statband { display: flex; margin-top: 13pt; border-top: 2.2pt solid %(gold)s;
  border-bottom: 0.6pt solid %(hairline)s; background: %(cream)s; }
.stat { flex: 1; padding: 10pt 4pt 9pt; text-align: center; }
.stat + .stat { border-left: 0.6pt solid %(hairline)s; }
.stat .num { font-family: 'Playfair Display', serif; font-weight: 700;
  font-size: 21pt; color: %(navy)s; }
.stat .num .unit { font-size: 12pt; }
.stat .lbl { margin-top: 4pt; font-size: 6.4pt; font-weight: 600;
  letter-spacing: 0.14em; color: %(muted)s; text-transform: uppercase; }
.sec-title { display: flex; align-items: baseline; gap: 7pt;
  font-size: 8.6pt; font-weight: 700; letter-spacing: 0.16em;
  color: %(navy)s; text-transform: uppercase; }
.sec-title::after { content: ""; flex: 1; border-top: 0.6pt solid %(hairline)s;
  transform: translateY(-2pt); }
.sec-sub { font-size: 7.6pt; color: %(muted)s; margin-top: 3pt; }
.footband { position: absolute; left: 0; right: 0; bottom: 0;
  background: %(navy)s; color: #FFFFFF; }
.footband .fb-inner { padding: 13pt 0.62in 12pt; }
.contact { display: flex; justify-content: space-between; align-items: center;
  font-size: 6.8pt; letter-spacing: 0.12em; text-transform: uppercase;
  color: rgba(255,255,255,0.72); }
.contact b { color: %(gold)s; font-weight: 600; }
.grove { display: flex; align-items: center; gap: 12pt; margin-top: 9pt;
  padding-top: 8pt; border-top: 0.6pt solid rgba(255,255,255,0.18); }
.grove img { width: 0.95in; height: auto; flex: none; display: block; }
.grove .g-txt { font-size: 7.3pt; line-height: 1.4; color: rgba(255,255,255,0.82); }
.grove .g-txt b { color: %(gold)s; font-weight: 600; }
/* team — compact strip on the navy band */
.team-strip { display: flex; gap: 13pt; margin-top: 9pt; padding-top: 9pt;
  border-top: 0.6pt solid rgba(255,255,255,0.18); }
.tm { display: flex; align-items: center; gap: 6pt; flex: 1; }
.tm img { width: 0.36in; height: 0.36in; border-radius: 50%%; object-fit: cover;
  border: 0.8pt solid %(gold)s; flex: none; display: block; }
.tm .t-name { font-size: 7.2pt; font-weight: 700; color: #FFFFFF; }
.tm .t-title { font-size: 5.6pt; letter-spacing: 0.09em; text-transform: uppercase;
  color: rgba(255,255,255,0.60); margin-top: 0.5pt; }
.tm .t-c { font-size: 6.1pt; color: rgba(255,255,255,0.82); margin-top: 2pt; }
/* team — larger block on light background */
.team-full { display: flex; gap: 20pt; margin-top: 10pt; }
.tf { flex: 1; }
.tf img { width: 0.62in; height: 0.62in; border-radius: 50%%; object-fit: cover;
  border: 1pt solid %(gold)s; display: block; margin-bottom: 5pt; }
.tf .f-name { font-size: 8.6pt; font-weight: 700; color: %(navy)s; }
.tf .f-title { font-size: 6.2pt; letter-spacing: 0.1em; text-transform: uppercase;
  color: %(muted)s; margin-top: 1.5pt; }
.tf .f-c { font-size: 7.4pt; line-height: 1.5; color: %(ink)s; margin-top: 4pt; }
/* Print-ready wrapper: media box carries bleed + crop-mark zone */
.sheet { position: relative; width: %(media_w).4fin; height: %(media_h).4fin;
  background: %(paper)s; margin: 0 auto; }
.sheet .page-canvas { position: absolute; left: %(outer).4fin; top: %(outer).4fin;
  overflow: visible; margin: 0; }
.cmark { position: absolute; }
.slug { position: absolute; left: %(slug_x).4fin; bottom: 0.055in;
  font-family: 'Inter', sans-serif; font-size: 4.6pt; letter-spacing: 0.08em;
  color: #000000; white-space: nowrap; }
""" % {
    "paper": PAPER, "ink": INK, "navy": NAVY, "gold": GOLD, "muted": MUTED,
    "hairline": HAIRLINE, "cream": CREAM, "gold_dk": "#A8873F",
    "media_w": MEDIA_W, "media_h": MEDIA_H, "outer": OUTER,
    "slug_x": OUTER + 1.0,
}

# In print mode the navy footer band must run off the trimmed edge.
BLEED_CSS = """
.sheet .footband { left: -%(bleed).4fin; right: -%(bleed).4fin; bottom: -%(bleed).4fin; }
.sheet .footband .fb-inner { padding-left: %(pad).4fin; padding-right: %(pad).4fin;
  padding-bottom: calc(14pt + %(bleed).4fin); }
""" % {"bleed": BLEED, "pad": SIDE_MARGIN + BLEED}


def grove_block_html() -> str:
    """Grove Collective lockup + NIL availability line for the navy footer band."""
    logo = PROJECT_ROOT / "assets" / "branding" / "grove_collective_white.png"
    data = base64.b64encode(logo.read_bytes()).decode("ascii")
    return (
        '<div class="grove">'
        f'<img src="data:image/png;base64,{data}" alt="The Grove Collective"/>'
        '<div class="g-txt"><b>Official partner of The Grove Collective.</b><br/>'
        'NIL revenue share and sponsorship packages available upon request.</div>'
        "</div>"
    )


def _photo_data_uri(rel_path: str) -> str:
    path = PROJECT_ROOT / rel_path
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def team_strip_html(config: dict) -> str:
    """Compact team row with headshots + direct contacts, for the navy band."""
    cards = []
    for m in config.get("team", []):
        img = _photo_data_uri(m.get("photo", ""))
        photo = f'<img src="{img}" alt="{esc(m["name"])}"/>' if img else ""
        cards.append(
            f'<div class="tm">{photo}<div><div class="t-name">{esc(m["name"])}</div>'
            f'<div class="t-title">{esc(m["title"])}</div>'
            f'<div class="t-c">{esc(m["phone"])} &nbsp;·&nbsp; {esc(m["email"])}</div>'
            "</div></div>"
        )
    return f'<div class="team-strip">{"".join(cards)}</div>'


def team_block_html(config: dict) -> str:
    """Larger team block for a light background."""
    cards = []
    for m in config.get("team", []):
        img = _photo_data_uri(m.get("photo", ""))
        photo = f'<img src="{img}" alt="{esc(m["name"])}"/>' if img else ""
        cards.append(
            f'<div class="tf">{photo}<div class="f-name">{esc(m["name"])}</div>'
            f'<div class="f-title">{esc(m["title"])}</div>'
            f'<div class="f-c">{esc(m["phone"])}<br/>{esc(m["email"])}</div></div>'
        )
    return f'<div class="team-full">{"".join(cards)}</div>'


def wrap_for_print(canvas_html: str, label: str) -> str:
    """Wrap a trim-size canvas in a media box with crop marks and a slug line."""
    return (
        f'<div class="sheet">{crop_marks_html()}{canvas_html}{slug_html(label)}</div>'
    )


# Oxford-Lafayette County Chamber mark. Drop the supplied artwork here as a
# full-colour or dark logo on a transparent background; it co-brands the
# masthead. If the file is absent the masthead falls back to text only, so the
# packet still builds.
CHAMBER_LOGO = PROJECT_ROOT / "assets" / "branding" / "oxford_chamber.png"


def chamber_logo_html() -> str:
    if not CHAMBER_LOGO.exists():
        return ""
    data = base64.b64encode(CHAMBER_LOGO.read_bytes()).decode("ascii")
    return (
        f'<img class="ch-logo" src="data:image/png;base64,{data}" '
        'alt="Oxford-Lafayette County Chamber of Commerce"/>'
    )


def masthead_html() -> str:
    logo = chamber_logo_html()
    right = (
        f'<div class="mh-right">{logo}'
        '<div class="prog">Chamber Partner<br/>Program &middot; 2026</div></div>'
        if logo else
        '<div class="prog">Chamber Partner Program &middot; 2026</div>'
    )
    return (
        '<div class="masthead">'
        '<div class="brand">MCTV <span class="amp">ELITE</span> ADVERTISING</div>'
        f'{right}'
        "</div>"
    )


def build_one_sheet_html(config: dict, rate: float, screens: int,
                         print_ready: bool = False) -> str:
    network = config["network"]
    plays_hr = network["plays_per_hour"]
    hours = network["hours_per_day"]
    days = network["days_per_month"]
    monthly_plays = plays_hr * hours * days * screens
    imps = get_tier_impressions(config, screens)
    cpm = calculate_cpm(rate, imps)
    daily_cost = rate / days
    per_screen = rate / screens
    per_dollar = imps / rate
    dwell = network["avg_dwell_time_minutes"]

    tiers = config["pricing"]["elite_tiers"]
    anchor = min(tiers, key=lambda t: abs(t["screens"] - screens))
    savings_pct = round((1 - rate / (anchor["cost_per_screen"] * screens)) * 100)

    # Cost of this deal's audience at each channel's typical CPM
    channels = []
    for b in config["industry_benchmarks"]["media_comparison"]:
        if b["medium"] == "MCTV Indoor":
            continue
        lo, hi = parse_cpm_range(b["est_cpm"])
        cost_lo, cost_hi = imps / 1000 * lo, imps / 1000 * hi
        channels.append({
            "name": b["medium"], "lo": lo, "hi": hi,
            "cost_lo": cost_lo, "cost_hi": cost_hi,
            "mid": (cost_lo + cost_hi) / 2,
        })
    channels.sort(key=lambda c: -c["mid"])
    max_mid = max(c["mid"] for c in channels)

    bar_rows = []
    for c in channels:
        pct = max(c["mid"] / max_mid * 100, 1.5)
        bar_rows.append(
            f'<div class="brow"><div class="bname">{esc(c["name"])}</div>'
            f'<div class="btrack"><div class="bfill" style="width:{pct:.1f}%"></div></div>'
            f'<div class="bval">{money(c["cost_lo"])}&ndash;{money(c["cost_hi"])}</div></div>'
        )
    mctv_pct = max(rate / max_mid * 100, 1.2)
    bar_rows.append(
        f'<div class="brow mctv"><div class="bname">MCTV Chamber Deal</div>'
        f'<div class="btrack"><div class="bfill gold" style="width:{mctv_pct:.1f}%"></div></div>'
        f'<div class="bval">{money(rate)}</div></div>'
    )

    print_b = find_benchmark(config, "Print / Newspaper")
    out_b = find_benchmark(config, "Outdoor Billboard")
    p_lo, p_hi = parse_cpm_range(print_b.get("est_cpm", "$20 - $40"))
    o_lo, o_hi = parse_cpm_range(out_b.get("est_cpm", "$3 - $8"))
    print_buys = (rate / p_hi * 1000, rate / p_lo * 1000)
    out_buys = (rate / o_hi * 1000, rate / o_lo * 1000)
    out_min = out_b.get("monthly_cost", "$1,500 - $4,000").split(" - ")[0]

    css = f"""
.headline {{ font-size: 27pt; line-height: 1.06; }}
.headline .gold {{ color: {GOLD}; }}
.deck {{ margin-top: 6pt; max-width: 5.9in; }}
.chart {{ margin-top: 8pt; }}
.brow {{ display: flex; align-items: center; gap: 8pt; margin-top: 4.4pt; }}
.bname {{ width: 1.28in; font-size: 7.6pt; font-weight: 500; color: {INK};
  text-align: right; flex: none; }}
.btrack {{ flex: 1; }}
.bfill {{ height: 8.5pt; background: {BAR_NAVY};
  border-radius: 0 3pt 3pt 0; }}
.bfill.gold {{ background: {GOLD}; }}
.bval {{ width: 1.18in; flex: none; font-size: 7.3pt; font-weight: 600;
  color: {MUTED}; font-variant-numeric: tabular-nums; }}
.brow.mctv .bname, .brow.mctv .bval {{ font-weight: 700; color: {NAVY}; }}
.trio {{ display: flex; gap: 10pt; margin-top: 8pt; }}
.tcard {{ flex: 1; border: 0.6pt solid {HAIRLINE}; border-top: 2.2pt solid {BAR_NAVY};
  padding: 8pt 10pt 9pt; background: {PAPER}; }}
.tcard.gold {{ border-top-color: {GOLD}; background: {CREAM}; }}
.tcard .t-med {{ font-size: 6.6pt; font-weight: 700; letter-spacing: 0.16em;
  text-transform: uppercase; color: {MUTED}; }}
.tcard .t-num {{ font-family: 'Playfair Display', serif; font-weight: 700;
  font-size: 16.5pt; color: {NAVY}; margin-top: 5pt; }}
.tcard .t-note {{ font-size: 7.2pt; color: {MUTED}; line-height: 1.45; margin-top: 4pt; }}
.obs {{ display: flex; gap: 14pt; margin-top: 7pt; }}
.ob {{ flex: 1; }}
.ob .o-num {{ font-family: 'Playfair Display', serif; font-style: italic;
  font-weight: 400; font-size: 13pt; color: {GOLD}; }}
.ob .o-title {{ font-size: 8.2pt; font-weight: 700; color: {NAVY}; margin-top: 2pt; }}
.ob .o-body {{ font-size: 7.4pt; line-height: 1.5; color: {MUTED}; margin-top: 3pt; }}
.footband .fb-line {{ font-family: 'Playfair Display', serif; font-weight: 700;
  font-size: 11.8pt; line-height: 1.32; color: #FFFFFF; }}
.footband .fb-line b {{ color: {GOLD}; font-weight: 700; }}
.footband .fb-sub {{ margin-top: 6pt; font-size: 7.4pt; color: rgba(255,255,255,0.66); }}
.footband .contact {{ margin-top: 11pt; padding-top: 9pt;
  border-top: 0.6pt solid rgba(255,255,255,0.18); }}
"""

    body = f"""
<div class="flyer page-canvas" data-canvas-width="816" data-canvas-height="1056">
  <div class="inner">
    {masthead_html()}
    <div class="kicker">Exclusive for Oxford-Lafayette Chamber Members</div>
    <h1 class="headline">{screens} screens.<br/><span class="gold">{money(rate)}</span> a month.</h1>
    <p class="deck">The Chamber member rate puts your business on {screens} MCTV indoor
    billboard screens in the restaurants, gyms, salons, and waiting rooms where Oxford
    already spends its day &mdash; for less than most businesses spend on a single print ad.</p>

    <div class="statband">
      <div class="stat"><div class="num">{screens}</div><div class="lbl">Screens in Local Venues</div></div>
      <div class="stat"><div class="num">{monthly_plays:,}</div><div class="lbl">Ad Plays Every Month</div></div>
      <div class="stat"><div class="num">{imps / 1000:,.0f}<span class="unit">K</span></div><div class="lbl">Monthly Impressions</div></div>
      <div class="stat"><div class="num">${cpm:.2f}</div><div class="lbl">Cost per 1,000 Impressions</div></div>
    </div>

    <div style="margin-top: 12pt;">
      <div class="sec-title">The price of this audience, channel by channel</div>
      <div class="sec-sub">Monthly cost to buy {imps:,.0f} impressions at each channel&rsquo;s typical CPM
      (industry benchmarks; bars show the midpoint).</div>
      <div class="chart">{"".join(bar_rows)}</div>
    </div>

    <div style="margin-top: 11pt;">
      <div class="sec-title">What the same {money(rate)} buys</div>
      <div class="trio">
        <div class="tcard"><div class="t-med">Print / Newspaper</div>
          <div class="t-num">~{print_buys[0] / 1000:,.0f}&ndash;{print_buys[1] / 1000:,.0f}K</div>
          <div class="t-note">impressions &mdash; one ad, one page, one run, easy to flip past.</div></div>
        <div class="tcard"><div class="t-med">Outdoor Billboard</div>
          <div class="t-num">~{out_buys[0] / 1000:,.0f}&ndash;{out_buys[1] / 1000:,.0f}K</div>
          <div class="t-note">impressions &mdash; and one board alone rents from {out_min}/mo,
          seen for seconds at 60 mph.</div></div>
        <div class="tcard gold"><div class="t-med">MCTV Chamber Deal</div>
          <div class="t-num">{imps:,.0f}</div>
          <div class="t-note">impressions across {screens} venues where customers sit
          for {dwell} minutes at a time.</div></div>
      </div>
    </div>

    <div style="margin-top: 11pt;">
      <div class="sec-title">Worth knowing</div>
      <div class="obs">
        <div class="ob"><div class="o-num">01</div>
          <div class="o-title">{savings_pct}% below our published rates</div>
          <div class="o-body">Standard is ${anchor["cost_per_screen"]:.0f} a screen. Members pay
          ${per_screen:.2f} &mdash; a bigger network than our
          {money(config["pricing"]["elite_tiers"][1]["monthly_rate"])} tier.</div></div>
        <div class="ob"><div class="o-num">02</div>
          <div class="o-title">A {dwell}-minute audience</div>
          <div class="o-body">{plays_hr}&times; an hour, {hours} hours a day, in rooms people
          sit in &mdash; not a 60 mph glance.</div></div>
        <div class="ob"><div class="o-num">03</div>
          <div class="o-title">It can&rsquo;t be skipped</div>
          <div class="o-body">No scroll, no channel change, no recycling bin. Every
          play counted in NTV360.</div></div>
      </div>
    </div>
  </div>

  <div class="footband"><div class="fb-inner">
    <div class="fb-line">The bottom line: <b>${daily_cost:.2f} a day</b> puts your business in
    {screens} rooms, {monthly_plays:,} times a month. Every dollar buys
    <b>~{per_dollar:,.0f} impressions</b> &mdash; print buys ~{1000 / p_hi:,.0f}&ndash;{1000 / p_lo:,.0f}. <span style="color:rgba(255,255,255,0.62);">Chamber members only &mdash; screens are limited.</span></div>
    {grove_block_html()}
    {team_strip_html(config)}
    <div class="contact" style="margin-top:9pt;padding-top:8pt;border-top:0.6pt solid rgba(255,255,255,0.18);">
    <span><b>MCTV Elite Advertising</b> &nbsp;&middot;&nbsp; {esc(config["company"]["tagline"])}</span>
    <span>{esc(config["company"]["website"])}</span></div>
  </div></div>
</div>
"""

    if print_ready:
        body = wrap_for_print(body, "MCTV Chamber Deal One-Sheet")

    page_w, page_h = (MEDIA_W, MEDIA_H) if print_ready else (TRIM_W, TRIM_H)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<title>MCTV Chamber Deal One-Sheet</title>
<meta name="hz:slide-selector" content=".flyer"/>
<meta name="hz:canvas-width" content="816"/>
<meta name="hz:canvas-height" content="1056"/>
<style>
{font_css()}
{BASE_CSS}
{css}
{BLEED_CSS if print_ready else ""}
@page {{ size: {page_w}in {page_h}in; margin: 0; }}
@media print {{ body {{ background: none; }}
  .page-canvas, .sheet {{ margin: 0; }} }}
</style></head><body>{body}</body></html>"""


def load_oxford_venues() -> list:
    data = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    venues = [v for v in data["venues"].values() if "Oxford MS" in v.get("address", "")]
    venues.sort(key=lambda v: v["host_name"].lower())
    return venues


def street_address(full: str) -> str:
    addr = re.sub(r",?\s*Oxford\s+MS\s*\d*\s*$", "", full).strip().rstrip(",")
    return re.sub(r"\s*(,?\s*(Suite|Ste\.?|UNIT|Unit)\s*\S+|#\S+)\s*$", "", addr).strip()


def venue_entry_html(v: dict) -> str:
    name = NAME_SHORTEN.get(v["host_name"], v["host_name"])
    cat = CATEGORY_OVERRIDES.get(v["host_name"], v.get("category", ""))
    screens = v.get("license_count", 1)
    imps = v.get("impressions") or 0
    chip = f'<span class="chip">{screens}&times;</span>' if screens > 1 else ""
    return (
        f'<div class="venue"><div class="v-name">{esc(name)}{chip}</div>'
        f'<div class="v-meta">{esc(cat)} &middot; {esc(street_address(v.get("address", "")))}'
        f' &middot; {imps / 1000:,.1f}K imps/mo</div></div>'
    )


def build_location_sheet_html(config: dict, rate: float, screens_deal: int,
                              print_ready: bool = False) -> str:
    venues = load_oxford_venues()
    membership = json.loads(MEMBERS_PATH.read_text(encoding="utf-8"))
    status = membership.get("members", {})
    checked = membership.get("checked_at", "")

    members = [v for v in venues if status.get(v["host_name"], {}).get("member") is True]
    others = [v for v in venues if status.get(v["host_name"], {}).get("member") is not True]
    total_screens = sum(v.get("license_count", 1) for v in venues)
    total_imps = sum(v.get("impressions") or 0 for v in venues)
    member_screens = sum(v.get("license_count", 1) for v in members)
    network = config["network"]

    css = f"""
.page-canvas + .page-canvas {{ margin-top: 24px; }}
.headline {{ font-size: 24pt; line-height: 1.1; }}
.deck {{ margin-top: 7pt; max-width: 6.2in; }}
.deck b {{ color: {NAVY}; font-weight: 600; }}
.cols {{ column-count: 2; column-gap: 26pt; margin-top: 9pt; }}
.venue {{ break-inside: avoid; padding: 4.6pt 0 4.2pt; border-bottom: 0.5pt solid {HAIRLINE}; }}
.v-name {{ font-size: 8pt; font-weight: 600; color: {INK}; }}
.chip {{ display: inline-block; margin-left: 5pt; padding: 0.5pt 4pt;
  font-size: 6.2pt; font-weight: 700; color: {NAVY};
  background: {CREAM}; border: 0.5pt solid {GOLD}; border-radius: 6pt;
  vertical-align: 1pt; }}
.v-meta {{ font-size: 6.8pt; color: {MUTED}; margin-top: 1.6pt; }}
.dia-mark {{ display: inline-block; width: 5pt; height: 5pt;
  background: {GOLD}; transform: rotate(45deg); margin-right: 2pt; }}
.count {{ font-family: 'Playfair Display', serif; font-style: italic;
  font-weight: 400; font-size: 11pt; color: {GOLD}; text-transform: none;
  letter-spacing: 0; }}
.rot {{ display: flex; gap: 10pt; margin-top: 10pt; }}
.rcard {{ flex: 1; border: 0.6pt solid {HAIRLINE}; border-top: 2.2pt solid {GOLD};
  background: {CREAM}; padding: 10pt 11pt 11pt; }}
.rcard .r-num {{ font-family: 'Playfair Display', serif; font-weight: 700;
  font-size: 16pt; color: {NAVY}; }}
.rcard .r-note {{ font-size: 7.2pt; color: {MUTED}; line-height: 1.45; margin-top: 3pt; }}
.srcnote {{ margin-top: 12pt; font-size: 6.6pt; line-height: 1.5; color: {MUTED};
  font-style: italic; }}
.incl {{ display: grid; grid-template-columns: 1fr 1fr; gap: 9pt 22pt;
  margin-top: 10pt; }}
.incl .ip {{ display: flex; gap: 7pt; align-items: baseline;
  padding-bottom: 8pt; border-bottom: 0.5pt solid {HAIRLINE}; }}
.incl .ip .dia {{ width: 4.4pt; height: 4.4pt; background: {GOLD};
  transform: rotate(45deg); flex: none; margin-top: 3pt; }}
.incl .ip .it {{ font-size: 8pt; line-height: 1.5; color: {INK}; font-weight: 500; }}
.footband .fb-line {{ font-family: 'Playfair Display', serif; font-weight: 700;
  font-size: 12.2pt; line-height: 1.35; color: #FFFFFF; }}
.footband .fb-line b {{ color: {GOLD}; }}
.footband .contact {{ margin-top: 10pt; padding-top: 9pt;
  border-top: 0.6pt solid rgba(255,255,255,0.18); }}
"""

    member_entries = "".join(venue_entry_html(v) for v in members)
    other_entries = "".join(venue_entry_html(v) for v in others)
    trust_html = "".join(
        f'<div class="ip"><span class="dia"></span>'
        f'<span class="it">{esc(point)}</span></div>'
        for point in config.get("social_proof", {}).get("trust_points", [])
    )

    page1 = f"""
<div class="page page-canvas" data-canvas-width="816" data-canvas-height="1056">
  <div class="inner">
    {masthead_html()}
    <div class="kicker">Oxford Location Sheet &middot; Chamber Packet</div>
    <h1 class="headline">Where your ad plays in Oxford.</h1>
    <p class="deck">MCTV runs <b>{total_screens} screens across {len(venues)} Oxford venues</b> &mdash;
    and <b>{len(members)} of those venues are active Oxford-Lafayette County Chamber members</b>,
    from the Square to Jackson Avenue, including the Chamber&rsquo;s own lobby. Advertise here
    and your dollars circulate inside the member network.</p>

    <div class="statband">
      <div class="stat"><div class="num">{len(venues)}</div><div class="lbl">Oxford Venues</div></div>
      <div class="stat"><div class="num">{total_screens}</div><div class="lbl">Screens Running Today</div></div>
      <div class="stat"><div class="num">{total_imps / 1000:,.0f}<span class="unit">K</span></div><div class="lbl">Est. Monthly Impressions</div></div>
      <div class="stat"><div class="num">{len(members)}</div><div class="lbl">Chamber Member Venues</div></div>
    </div>

    <div style="margin-top: 11pt;">
      <div class="sec-title"><span class="dia-mark"></span> Chamber member venues
        <span class="count">{len(members)} venues &middot; {member_screens} screens</span></div>
      <div class="cols">{member_entries}</div>
    </div>
  </div>
</div>
"""

    page2 = f"""
<div class="page page-canvas" data-canvas-width="816" data-canvas-height="1056">
  <div class="inner">
    {masthead_html()}
    <div style="margin-top: 20pt;">
      <div class="sec-title">The rest of the Oxford network
        <span class="count">{len(others)} venues</span></div>
      <div class="sec-sub">Your rotation doesn&rsquo;t stop at member venues &mdash; the Chamber
      deal plays across every Oxford location below as well.</div>
      <div class="cols">{other_entries}</div>
    </div>

    <div style="margin-top: 16pt;">
      <div class="sec-title">How the rotation works</div>
      <div class="rot">
        <div class="rcard"><div class="r-num">{network["plays_per_hour"]}&times; / hour</div>
          <div class="r-note">Your ad plays every {60 // network["plays_per_hour"]} minutes on
          every screen, {network["hours_per_day"]} hours a day.</div></div>
        <div class="rcard"><div class="r-num">{network["avg_dwell_time_minutes"]} min</div>
          <div class="r-note">Average customer visit &mdash; long enough to see your ad
          several times per stop.</div></div>
        <div class="rcard"><div class="r-num">{money(rate)} / mo</div>
          <div class="r-note">The Chamber member rate for {screens_deal} screens across
          this network. Verified plays in NTV360.</div></div>
      </div>
    </div>

    <div style="margin-top: 16pt;">
      <div class="sec-title">Included with every Chamber deal</div>
      <div class="incl">{trust_html}</div>
    </div>

    <div style="margin-top: 15pt;">
      <div class="sec-title">Your MCTV team</div>
      {team_block_html(config)}
      <div class="srcnote">Chamber membership cross-checked against the Oxford-Lafayette County
      Chamber of Commerce online directory (business.oxfordms.com){f" on {checked}" if checked else ""}.
      Impressions estimated from NTV360 venue traffic. Screen counts as of the latest network sync.</div>
    </div>
  </div>

  <div class="footband"><div class="fb-inner">
    <div class="fb-line">One flat rate. <b>{len(venues)} rooms</b> across Oxford &mdash;
    <b>{len(members)} of them fellow Chamber members.</b></div>
    {grove_block_html()}
    <div class="contact"><span><b>MCTV Elite Advertising</b> &nbsp;&middot;&nbsp; {esc(config["company"]["tagline"])}</span>
    <span>{esc(config["company"]["website"])}</span></div>
  </div></div>
</div>
"""

    if print_ready:
        page1 = wrap_for_print(page1, "MCTV Oxford Location Sheet &mdash; Page 1 (front)")
        page2 = wrap_for_print(page2, "MCTV Oxford Location Sheet &mdash; Page 2 (back)")

    page_w, page_h = (MEDIA_W, MEDIA_H) if print_ready else (TRIM_W, TRIM_H)
    break_sel = ".sheet" if print_ready else ".page-canvas"

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<title>MCTV Oxford Location Sheet</title>
<meta name="hz:slide-selector" content=".page"/>
<meta name="hz:canvas-width" content="816"/>
<meta name="hz:canvas-height" content="1056"/>
<style>
{font_css()}
{BASE_CSS}
{css}
{BLEED_CSS if print_ready else ""}
@page {{ size: {page_w}in {page_h}in; margin: 0; }}
@media print {{ body {{ background: none; }}
  .page-canvas, .sheet {{ margin: 0; }}
  {break_sel} {{ page-break-after: always; }}
  {break_sel}:last-child {{ page-break-after: auto; }}
  .page-canvas + .page-canvas {{ margin-top: 0; }} }}
</style></head><body>{page1}{page2}</body></html>"""


PRINT_INSTRUCTIONS = """MCTV ELITE ADVERTISING - CHAMBER PACKET
PRINT SPECIFICATION / RELEASE NOTES
================================================================

CONTACT
  T. Creed Cannon, Managing Partner
  MCTV Digital, Inc.  |  601-201-8202  |  www.mctvofms.com
  Please confirm receipt and send a proof before running.

FILES SUPPLIED (press-ready PDF)
  1. MCTV_Chamber_Deal_One_Sheet_PRINT.pdf
       1 page  |  print SINGLE-SIDED (4/0)
  2. MCTV_Chamber_Oxford_Location_Sheet_PRINT.pdf
       2 pages |  print DOUBLE-SIDED (4/4), head-to-head
       Page 1 = front, Page 2 = back. Both pages are one sheet of paper.

  These two pieces are inserted into the same Chamber presentation packet,
  so please keep stock and finish identical between them.

SIZE & GEOMETRY
  Finished / trim size .... {trim_w}" x {trim_h}" (US Letter), portrait
  Document size ........... {media_w}" x {media_h}"
  Bleed ................... {bleed}" on all four sides
  Crop marks .............. included, hairline, offset {bleed}" from trim
  Safety / live area ...... all live copy sits at least 0.4" inside trim

  The dark navy band at the foot of the page is a full-bleed element -
  it intentionally runs off the left, right, and bottom trim edges.

  A small slug line sits at the bottom of each page outside the trim
  (file name, trim, bleed). It trims off and must NOT appear on the
  finished piece. If your workflow prefers files without the slug or
  marks, let us know and we will re-export.

COLOR
  Two sets are supplied. Use whichever suits your workflow:

    *_PRINT_CMYK.pdf  DeviceCMYK, already separated. Converted from the
                      RGB masters through a SWOP-like profile. All images
                      are CMYK; no RGB remains.
    *_PRINT.pdf       the RGB masters. If you would rather separate these
                      yourself against your own press profile, please do
                      - your profile beats ours. Ignore the CMYK set.

  Achieved separation in the CMYK files, for reference:
    MCTV Navy ....... {navy}   C90 M85 Y47 K55, 276% total ink
    MCTV Gold ....... {gold}   warm antique gold, not yellow/brassy
    Warm cream ...... {cream}   very light panel tint - please confirm
                                 it holds and does not blow out to white
  Peak coverage anywhere on the page is 302% and only over a couple of
  stray pixels; everything else sits at or under 276%. The hex values
  remain authoritative - match them on a calibrated proof. The navy must
  not read washed out or purple.

  Note on small type: body copy is {ink}, a very dark navy rather than
  pure black, so it separates as a rich 4-color dark rather than 100% K.
  That is deliberate - forcing near-blacks to K-only also flattened the
  brand navy to solid black. If you would prefer 100% K on text at 8pt
  and below, apply your own black generation, or take the RGB masters
  and separate to taste.

  The navy covers a large solid area. Please watch for banding and
  mottling in the footer band.

FONTS
  Fully embedded subsets, no substitutions required:
    Playfair Display (headlines, figures)
    Inter (body, labels)
  Both are SIL Open Font License; embedding and printing are permitted.
  No fonts need to be supplied separately. Nothing is outlined - if your
  RIP prefers outlines, tell us and we will re-export with type converted.

IMAGES & LOGOS
  All artwork is embedded in the PDF. No linked files.
  The Grove Collective logo is placed at approximately 2,300 ppi at final
  size (well above the 300 ppi minimum) and carries an alpha channel.
  Vector EPS/AI of that logo is available on request if your prepress
  department would rather place vector art.

STOCK & FINISHING (recommendation - confirm before running)
  Stock ......... 100 lb gloss or silk text, or 80 lb silk cover for a
                  heavier leave-behind. We are open to your house stock.
  Coating ....... optional gloss or satin aqueous
  Finishing ..... flat, trim only. No folds, scores, drilling, or binding.
  Quantity ...... _____________ (to be confirmed)

PROOFING
  Please provide a hard-copy contract proof (or a PDF proof plus a press
  check) before the full run. We specifically want to see:
    - the navy footer band for evenness and correct depth
    - the gold accents for warmth
    - small reversed white type in the footer band for fill-in
    - the Grove Collective logo for clean edges against the navy

Questions on any of the above - call Creed at 601-201-8202.
"""


def write_print_instructions() -> Path:
    text = PRINT_INSTRUCTIONS.format(
        trim_w=TRIM_W, trim_h=TRIM_H, media_w=MEDIA_W, media_h=MEDIA_H,
        bleed=BLEED, navy=NAVY, gold=GOLD, cream=CREAM, ink=INK,
    )
    path = OUTPUT_DIR / "MCTV_Chamber_Packet_PRINT_INSTRUCTIONS.txt"
    path.write_text(text, encoding="utf-8")
    return path


def find_chromium(explicit: str = None) -> str:
    candidates = [explicit, "/opt/pw-browsers/chromium",
                  shutil.which("chromium"), shutil.which("chromium-browser"),
                  shutil.which("google-chrome")]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise SystemExit("Chromium not found — pass --chromium /path/to/chromium")


def render_pdf(chromium: str, html_path: Path, pdf_path: Path):
    subprocess.run(
        [chromium, "--headless", "--disable-gpu", "--no-sandbox",
         "--no-pdf-header-footer", "--disable-dev-shm-usage",
         f"--print-to-pdf={pdf_path}", str(html_path)],
        check=True, capture_output=True, timeout=120,
    )


def main():
    parser = argparse.ArgumentParser(description="Generate designed Chamber packet documents")
    parser.add_argument("--rate", type=float, default=199.0)
    parser.add_argument("--screens", type=int, default=25)
    parser.add_argument("--chromium", default=None, help="Path to Chromium binary")
    parser.add_argument("--html-only", action="store_true", help="Skip PDF rendering")
    parser.add_argument("--no-print-ready", action="store_true",
                        help="Skip the bleed/crop-mark press versions")
    args = parser.parse_args()

    config = load_config()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    docs = {
        "MCTV_Chamber_Deal_One_Sheet_Design":
            build_one_sheet_html(config, args.rate, args.screens),
        "MCTV_Chamber_Oxford_Location_Sheet_Design":
            build_location_sheet_html(config, args.rate, args.screens),
    }
    if not args.no_print_ready:
        docs.update({
            "MCTV_Chamber_Deal_One_Sheet_PRINT":
                build_one_sheet_html(config, args.rate, args.screens, print_ready=True),
            "MCTV_Chamber_Oxford_Location_Sheet_PRINT":
                build_location_sheet_html(config, args.rate, args.screens, print_ready=True),
        })

    chromium = None if args.html_only else find_chromium(args.chromium)
    for name, html in docs.items():
        html_path = OUTPUT_DIR / f"{name}.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"HTML: {html_path}")
        if chromium:
            pdf_path = OUTPUT_DIR / f"{name}.pdf"
            render_pdf(chromium, html_path, pdf_path)
            print(f"PDF:  {pdf_path}")

    if not args.no_print_ready:
        print(f"SPEC: {write_print_instructions()}")


if __name__ == "__main__":
    main()
