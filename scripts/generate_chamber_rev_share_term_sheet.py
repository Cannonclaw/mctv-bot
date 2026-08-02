# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Chamber revenue-share term sheet (one page, designed).

Discussion draft for the Oxford-Lafayette Chamber partnership: rev-share
percentage, sourcing definition, 12-month window, volume kicker, payment
mechanics, and a worked example. Same fixed-canvas pipeline as
generate_chamber_packet_designs.py (fonts vendored, headless Chromium).

Usage:
    python scripts/generate_chamber_rev_share_term_sheet.py
    python scripts/generate_chamber_rev_share_term_sheet.py --rate 199 --base-pct 10 --kicker-pct 15
"""

import argparse
import base64
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.config_service import load_config

PROJECT_ROOT = Path(__file__).parent.parent
FONTS_DIR = PROJECT_ROOT / "assets" / "fonts"
OUTPUT_DIR = PROJECT_ROOT / "output" / "proposals"
CHAMBER_LOGO = PROJECT_ROOT / "assets" / "branding" / "oxford_chamber.png"

NAVY = "#1B1F3B"
GOLD = "#C5A55A"
GOLD_DK = "#A8874A"
INK = "#23273D"
MUTED = "#6C7080"
HAIRLINE = "#E4E2DC"
CREAM = "#F7F5F0"

FONT_FILES = {
    "playfair-700": ("Playfair Display", 700, "normal", "playfair-display-latin-700-normal.woff2"),
    "playfair-800": ("Playfair Display", 800, "normal", "playfair-display-latin-800-normal.woff2"),
    "playfair-400i": ("Playfair Display", 400, "italic", "playfair-display-latin-400-italic.woff2"),
    "inter-400": ("Inter", 400, "normal", "inter-latin-400-normal.woff2"),
    "inter-500": ("Inter", 500, "normal", "inter-latin-500-normal.woff2"),
    "inter-600": ("Inter", 600, "normal", "inter-latin-600-normal.woff2"),
    "inter-700": ("Inter", 700, "normal", "inter-latin-700-normal.woff2"),
}


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def font_css():
    rules = []
    for family, weight, style, filename in FONT_FILES.values():
        data = base64.b64encode((FONTS_DIR / filename).read_bytes()).decode("ascii")
        rules.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"font-style:{style};font-display:block;"
            f"src:url(data:font/woff2;base64,{data}) format('woff2');}}"
        )
    return "\n".join(rules)


def chamber_logo_tag():
    if not CHAMBER_LOGO.exists():
        return ""
    data = base64.b64encode(CHAMBER_LOGO.read_bytes()).decode("ascii")
    return f'<img class="ch-logo" src="data:image/png;base64,{data}" alt="Oxford-Lafayette Chamber of Commerce"/>'


CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #DDDDDD; }
.page-canvas { position: relative; width: 8.5in; height: 11in; background: #FFFFFF;
  overflow: hidden; font-family: 'Inter', sans-serif; color: %(ink)s; margin: 0 auto; }
.inner { position: absolute; left: 0.62in; right: 0.62in; top: 0.5in; }
.masthead { display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 7pt; border-bottom: 1.6pt solid %(navy)s; }
.masthead .brand { font-size: 10pt; font-weight: 700; letter-spacing: 0.22em; color: %(navy)s; }
.masthead .brand .amp { color: %(gold)s; }
.mh-right { display: flex; align-items: center; gap: 9pt; }
.ch-logo { height: 0.36in; width: auto; display: block; max-width: 1.5in; object-fit: contain; }
.prog { font-size: 6.6pt; font-weight: 600; letter-spacing: 0.18em; color: %(muted)s;
  text-transform: uppercase; line-height: 1.35; text-align: right; padding-left: 9pt;
  border-left: 0.6pt solid %(hairline)s; }
.kicker { margin-top: 12pt; font-size: 7.2pt; font-weight: 700; letter-spacing: 0.24em;
  color: %(gold_dk)s; text-transform: uppercase; }
.kicker .draft { color: #B03A2E; }
.headline { font-family: 'Playfair Display', serif; font-weight: 800; font-size: 22pt;
  line-height: 1.08; color: %(navy)s; margin-top: 5pt; }
.lede { margin-top: 6pt; font-size: 8.4pt; line-height: 1.5; color: %(ink)s; max-width: 6.6in; }
.sec { margin-top: 9pt; }
.sec-title { font-size: 8pt; font-weight: 700; letter-spacing: 0.16em; color: %(navy)s;
  text-transform: uppercase; padding-bottom: 4pt; border-bottom: 0.8pt solid %(hairline)s;
  margin-bottom: 7pt; display: flex; align-items: baseline; gap: 6pt; }
.sec-title .no { font-family: 'Playfair Display', serif; font-style: italic; font-weight: 400;
  font-size: 9.5pt; color: %(gold_dk)s; letter-spacing: 0; text-transform: none; }
.terms { display: flex; gap: 16pt; }
.terms .col { flex: 1; }
.t-row { display: flex; gap: 8pt; margin-bottom: 5pt; }
.t-key { flex: none; width: 1.18in; font-size: 7.4pt; font-weight: 700; color: %(navy)s;
  text-transform: uppercase; letter-spacing: 0.06em; padding-top: 0.5pt; }
.t-val { font-size: 8.2pt; line-height: 1.45; color: %(ink)s; }
.t-val b { font-weight: 700; color: %(navy)s; }
.bigpct { display: flex; gap: 12pt; margin: 2pt 0 8pt; }
.pct-card { flex: 1; border: 0.8pt solid %(hairline)s; border-top: 2.2pt solid %(gold)s;
  background: %(cream)s; padding: 7pt 10pt 6pt; }
.pct-card .n { font-family: 'Playfair Display', serif; font-weight: 800; font-size: 19pt;
  color: %(navy)s; }
.pct-card .lbl { font-size: 6.6pt; font-weight: 700; letter-spacing: 0.12em;
  text-transform: uppercase; color: %(gold_dk)s; margin-bottom: 2pt; }
.pct-card .d { font-size: 7.3pt; line-height: 1.4; color: %(ink)s; margin-top: 2pt; }
.excl { background: #FFFFFF; border: 0.8pt solid %(hairline)s; border-left: 2.2pt solid %(navy)s;
  padding: 8pt 11pt; font-size: 8pt; line-height: 1.5; }
.excl b { color: %(navy)s; }
table.example { width: 100%%; border-collapse: collapse; font-size: 8pt; }
table.example th { text-align: left; font-size: 6.8pt; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: %(muted)s; padding: 0 8pt 4pt 0;
  border-bottom: 0.8pt solid %(hairline)s; }
table.example th.r, table.example td.r { text-align: right; padding-right: 0; }
table.example td { padding: 3.5pt 8pt 3.5pt 0; border-bottom: 0.5pt solid %(hairline)s;
  color: %(ink)s; }
table.example tr.hl td { font-weight: 700; color: %(navy)s; background: %(cream)s; }
.two-col { display: flex; gap: 16pt; }
.two-col > div { flex: 1; }
.commit li { font-size: 7.8pt; line-height: 1.45; margin-bottom: 2.5pt; margin-left: 10pt; }
.commit li::marker { color: %(gold)s; }
.sig-band { position: absolute; left: 0; right: 0; bottom: 0; background: %(navy)s;
  color: #FFFFFF; padding: 10pt 0.62in 12pt; }
.sig-note { font-size: 7.6pt; line-height: 1.5; color: rgba(255,255,255,0.85); }
.sig-note b { color: %(gold)s; }
.sig-cols { display: flex; gap: 24pt; margin-top: 10pt; }
.sig-col { flex: 1; }
.sig-line { border-bottom: 0.8pt solid rgba(255,255,255,0.5); height: 16pt; }
.sig-lbl { font-size: 6.4pt; letter-spacing: 0.14em; text-transform: uppercase;
  color: rgba(255,255,255,0.6); margin-top: 3pt; }
""" % {"navy": NAVY, "gold": GOLD, "gold_dk": GOLD_DK, "ink": INK, "muted": MUTED,
       "hairline": HAIRLINE, "cream": CREAM}


def build_html(rate, screens, base_pct, kicker_pct, kicker_threshold, cap, window_months):
    config = load_config()
    share_base = rate * base_pct / 100
    share_kick = rate * kicker_pct / 100

    def row(n_adv, pct):
        gross = rate * n_adv
        chamber = gross * pct / 100
        yearly = chamber * 12
        cls = ' class="hl"' if n_adv == cap else ''
        return (f'<tr{cls}>'
                f'<td>{n_adv} advertisers</td><td>{pct:.0f}%</td>'
                f'<td class="r">${gross:,.0f}/mo</td>'
                f'<td class="r">${chamber:,.0f}/mo &nbsp;&middot;&nbsp; ${yearly:,.0f}/yr</td></tr>')

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{font_css()}\n{CSS}</style></head><body>
<div class="page-canvas"><div class="inner">
  <div class="masthead">
    <div class="brand">MCTV <span class="amp">ELITE</span> ADVERTISING</div>
    <div class="mh-right">{chamber_logo_tag()}
      <div class="prog">CHAMBER PARTNER PROGRAM<br/>REVENUE SHARE &middot; 2026</div>
    </div>
  </div>

  <div class="kicker"><span class="draft">Draft for discussion</span> &middot; Oxford-Lafayette Chamber &times; MCTV Elite Advertising</div>
  <div class="headline">Chamber revenue share &mdash; proposed terms.</div>
  <div class="lede">The Chamber endorses the member program and refers members; MCTV runs the network,
  the campaigns, and the billing. The Chamber earns a share of every deal it sources. One page,
  plain terms &mdash; the partnership agreement will carry the legal language.</div>

  <div class="sec">
    <div class="sec-title"><span class="no">01</span> The share</div>
    <div class="bigpct">
      <div class="pct-card"><div class="lbl">Base</div><div class="n">{base_pct:.0f}%</div>
        <div class="d">of collected revenue on every Chamber-sourced deal, for that advertiser's
        first {window_months} months. ${share_base:,.2f}/mo per advertiser at the ${rate:,.0f} member rate.</div></div>
      <div class="pct-card"><div class="lbl">Volume</div><div class="n">{kicker_pct:.0f}%</div>
        <div class="d">replaces the base rate in any month with {kicker_threshold}+ active
        Chamber-sourced advertisers. ${share_kick:,.2f}/mo per advertiser &mdash; the Chamber's
        upside for selling, not just endorsing.</div></div>
      <div class="pct-card"><div class="lbl">After {window_months} months</div><div class="n">0%</div>
        <div class="d">the share applies to each advertiser's first {window_months} months only.
        Renewals beyond that are serviced and retained by MCTV.</div></div>
    </div>
    <div class="excl"><b>Not shared:</b> advertisers already under contract with MCTV before this
    agreement; advertisers MCTV sources through its own outreach (membership alone does not qualify);
    renewal months beyond the {window_months}-month window; production or creative fees.</div>
  </div>

  <div class="sec">
    <div class="sec-title"><span class="no">02</span> What "Chamber-sourced" means</div>
    <div class="terms"><div class="col">
      <div class="t-row"><div class="t-key">Qualifies</div><div class="t-val">The Chamber makes the
      introduction &mdash; a referral by name to MCTV, a lead from a Chamber mailer or event, or a
      sign-up through the Chamber's link or QR code. Attribution is recorded at signup.</div></div>
      <div class="t-row"><div class="t-key">Does not</div><div class="t-val">A business that happens
      to hold a membership but reached MCTV on its own or through MCTV's outreach.</div></div>
    </div><div class="col">
      <div class="t-row"><div class="t-key">Disputes</div><div class="t-val">Flagged within 30 days
      of first invoice, settled by the signup record. After 30 days, attribution is final.</div></div>
      <div class="t-row"><div class="t-key">Active</div><div class="t-val">An advertiser is active in
      any month MCTV collects the member rate from them. Paused or lapsed accounts don't count
      toward the {kicker_threshold}-advertiser volume threshold.</div></div>
    </div></div>
  </div>

  <div class="sec">
    <div class="sec-title"><span class="no">03</span> What the money looks like</div>
    <table class="example">
      <tr><th>Chamber-sourced advertisers</th><th>Rate</th><th class="r">Program gross</th><th class="r">Chamber share</th></tr>
      {row(10, base_pct)}
      {row(kicker_threshold, kicker_pct)}
      {row(cap, kicker_pct)}
    </table>
  </div>

  <div class="sec two-col">
    <div>
      <div class="sec-title"><span class="no">04</span> MCTV commits to</div>
      <ul class="commit">
        <li>The ${rate:,.0f}/mo member rate on {screens} screens, held for the program's first year.</li>
        <li>Monthly statement of active advertisers, collections, and the share owed.</li>
        <li>Payment by the 15th of the following month, on collected revenue.</li>
        <li>Chamber co-branding on program collateral.</li>
      </ul>
    </div>
    <div>
      <div class="sec-title"><span class="no">05</span> The Chamber commits to</div>
      <ul class="commit">
        <li>Program announcement to the member list, plus presence at member events.</li>
        <li>MCTV as the Chamber's endorsed indoor-screen advertising partner.</li>
        <li>Logo use on program materials (as placed above).</li>
        <li>Program capped at {cap} advertisers &mdash; scarcity is part of the offer.</li>
      </ul>
    </div>
  </div>
</div>

<div class="sig-band">
  <div class="sig-note"><b>This is a discussion draft, not a contract.</b> Term: 12 months from
  signing, renewing annually unless either side gives 60 days' notice; share already earned
  survives termination for the remainder of each advertiser's {window_months}-month window.
  Final language to follow in the partnership agreement.</div>
  <div class="sig-cols">
    <div class="sig-col"><div class="sig-line"></div><div class="sig-lbl">MCTV Elite Advertising &mdash; T. Creed Cannon &middot; Date</div></div>
    <div class="sig-col"><div class="sig-line"></div><div class="sig-lbl">Oxford-Lafayette County Chamber of Commerce &middot; Date</div></div>
  </div>
</div>
</div></body></html>"""
    return html


TRIM_W, TRIM_H = 8.5, 11.0
BLEED = 0.125
MARK_ZONE = 0.25
OUTER = BLEED + MARK_ZONE
MEDIA_W = TRIM_W + 2 * OUTER
MEDIA_H = TRIM_H + 2 * OUTER
MARK_LEN = 0.1875

PRINT_CSS = """
body { background: #FFFFFF; }
.sheet { position: relative; width: %(mw).3fin; height: %(mh).3fin; background: #FFFFFF; }
.sheet .page-canvas { position: absolute; left: %(outer).3fin; top: %(outer).3fin; margin: 0; }
/* navy signature band bleeds off left/right/bottom trim */
.sheet .sig-band { left: -%(bleed).3fin; right: -%(bleed).3fin; bottom: -%(bleed).3fin;
  padding-left: %(padl).3fin; padding-right: %(padl).3fin; padding-bottom: %(padb).3fin; }
.cmark { position: absolute; }
.slug { position: absolute; left: %(outer).3fin; top: %(slugy).3fin;
  font-family: 'Inter', sans-serif; font-size: 5.6pt; letter-spacing: 0.12em;
  color: #444444; text-transform: uppercase; }
@page { size: %(mw).3fin %(mh).3fin; margin: 0; }
""" % {"mw": MEDIA_W, "mh": MEDIA_H, "outer": OUTER, "bleed": BLEED,
       "padl": 0.62 + BLEED, "padb": 14/72 + BLEED, "slugy": OUTER + TRIM_H + BLEED + 0.06}


def crop_marks_html():
    marks = []
    for x_edge, y_edge in ((0, 0), (1, 0), (0, 1), (1, 1)):
        tx = OUTER if x_edge == 0 else OUTER + TRIM_W
        ty = OUTER if y_edge == 0 else OUTER + TRIM_H
        hx = (tx - BLEED - MARK_LEN) if x_edge == 0 else (tx + BLEED)
        marks.append(
            f'<div class="cmark" style="left:{hx:.4f}in;top:{ty:.4f}in;'
            f'width:{MARK_LEN}in;border-top:0.25pt solid #000;"></div>'
        )
        vy = (ty - BLEED - MARK_LEN) if y_edge == 0 else (ty + BLEED)
        marks.append(
            f'<div class="cmark" style="left:{tx:.4f}in;top:{vy:.4f}in;'
            f'height:{MARK_LEN}in;border-left:0.25pt solid #000;"></div>'
        )
    return "".join(marks)


def wrap_for_print(html):
    slug = (f'<div class="slug">MCTV Chamber Rev-Share Term Sheet &nbsp;&middot;&nbsp; '
            f'TRIM {TRIM_W}&Prime; &times; {TRIM_H}&Prime; &nbsp;&middot;&nbsp; BLEED {BLEED}&Prime;'
            f' &nbsp;&middot;&nbsp; CROP MARKS SHOWN &nbsp;&middot;&nbsp; RGB &mdash; CONVERT TO CMYK</div>')
    html = html.replace("</style>", PRINT_CSS + "</style>")
    html = html.replace('<div class="page-canvas">',
                        '<div class="sheet">' + crop_marks_html() + slug + '<div class="page-canvas">')
    html = html.replace("</body>", "</div></body>")
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=float, default=199)
    ap.add_argument("--screens", type=int, default=25)
    ap.add_argument("--base-pct", type=float, default=10)
    ap.add_argument("--kicker-pct", type=float, default=15)
    ap.add_argument("--kicker-threshold", type=int, default=25)
    ap.add_argument("--cap", type=int, default=50)
    ap.add_argument("--window-months", type=int, default=12)
    ap.add_argument("--chromium", default=None)
    args = ap.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html = build_html(args.rate, args.screens, args.base_pct, args.kicker_pct,
                      args.kicker_threshold, args.cap, args.window_months)
    html_path = OUTPUT_DIR / "MCTV_Chamber_Rev_Share_Term_Sheet.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"HTML: {html_path}")

    chromium = args.chromium or shutil.which("chromium") or "/opt/pw-browsers/chromium"
    pdf_path = OUTPUT_DIR / "MCTV_Chamber_Rev_Share_Term_Sheet.pdf"
    subprocess.run([
        chromium, "--headless", "--disable-gpu", "--no-sandbox",
        f"--print-to-pdf={pdf_path}", "--no-pdf-header-footer",
        "--print-to-pdf-no-header", str(html_path),
    ], check=True, capture_output=True)
    print(f"PDF:  {pdf_path}")

    print_html = wrap_for_print(html)
    print_html_path = OUTPUT_DIR / "MCTV_Chamber_Rev_Share_Term_Sheet_PRINT.html"
    print_html_path.write_text(print_html, encoding="utf-8")
    print_pdf_path = OUTPUT_DIR / "MCTV_Chamber_Rev_Share_Term_Sheet_PRINT.pdf"
    subprocess.run([
        chromium, "--headless", "--disable-gpu", "--no-sandbox",
        f"--print-to-pdf={print_pdf_path}", "--no-pdf-header-footer",
        "--print-to-pdf-no-header", str(print_html_path),
    ], check=True, capture_output=True)
    print(f"PDF:  {print_pdf_path} (press)")


if __name__ == "__main__":
    main()
