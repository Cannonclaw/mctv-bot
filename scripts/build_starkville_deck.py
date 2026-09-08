#!/usr/bin/env python3
"""Build the Starkville Athletic Club host-partnership deck.

Composes `deck.src.html` (the chassis — MCTV deck CSS per Design.md v1.0) with
`deck.slides.html` (the ten slides) and inlines every asset as a data URI, so the
built file is a single self-contained HTML document with no external requests.
That matters twice over: the artifact CSP blocks external hosts, and the deck has
to survive being emailed around as one file.

    python scripts/build_starkville_deck.py            # build the HTML
    python scripts/build_starkville_deck.py --pdf      # build, then print to PDF

Photo crops are deliberate, not incidental:

* The cover crops `wild-opc.png` to the right of the hand-painted "Oxford Park
  Commission" wall mark. It is the only frame we own of an MCTV screen in a
  recreation facility, but Oxford branding behind a headline that says Starkville
  reads as a copy-paste job, so the lettering is cropped out rather than scrimmed
  over.
* Slide 4 keeps the venue photos uncropped and captions them as Oxford. That page
  is *about* the network being real and photographed in market; pretending those
  rooms are in Starkville is the one thing it must not do.

Copyright (c) MCTV Digital, Inc. Proprietary.
"""
from __future__ import annotations

import argparse
import base64
import io
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required: pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent
DECK = ROOT / "handoffs" / "starkville-athletic-club"
ASSETS = DECK / "assets"
OUT = DECK / "STARKVILLE-Host-Pitch.html"

FONTS = {
    "__FONT_PLAYFAIR__": "PlayfairDisplay.ttf",
    "__FONT_PLAYFAIR_I__": "PlayfairDisplay-Italic.ttf",
    "__FONT_WORKSANS__": "WorkSans.ttf",
    "__FONT_WORKSANS_I__": "WorkSans-Italic.ttf",
}

# token -> (source image, target size, jpeg quality, crop box or None)
# A crop box is applied before the resize, in source pixels.
IMAGES = {
    # Davis Wade at sunset, lifted from page 1 of the Golden Triangle media kit.
    # Already 16:9 at 3000x1688, so it needs no crop — and it is MCTV's own printed
    # cover, which settles the rights question the wild-* frames could not.
    "__COVER__":      ("davis-wade.jpg",        (1920, 1080), 86, None),
    "__PARTNERS__":   ("partner-logos.png",     (2400, 593),  88, None),  # 4.05:1, matches source — must not crop
    "__W_CORNERS__":  ("wild-four-corners.jpg", (760, 1000),  78, None),
    "__W_OPC__":      ("wild-opc.png",          (700, 470),   78, None),
    "__W_DESK__":     ("wild-frontdesk.jpg",    (700, 470),   78, None),
    "__W_COUNTER__":  ("wild-counter.jpg",      (700, 470),   78, None),
    "__W_SHOP__":     ("wild-shirt-shop.jpg",   (700, 470),   78, None),
    "__HS_CREED__":   ("creed_headshot.png",         (220, 220), 84, None),
    "__HS_MM__":      ("mary_michael_headshot.png",  (220, 220), 84, None),
    "__HS_SWAYZE__":  ("swayze_headshot.png",        (220, 220), 84, None),
}


def font_uri(name: str) -> str:
    data = (ASSETS / "fonts" / name).read_bytes()
    return "data:font/ttf;base64," + base64.b64encode(data).decode()


def image_uri(name: str, size: tuple[int, int], quality: int, crop=None) -> str:
    """Cover-fit `name` into `size` and return it as a JPEG data URI."""
    im = Image.open(ASSETS / "img" / name).convert("RGB")
    if crop:
        im = im.crop(crop)
    target = size[0] / size[1]
    ratio = im.width / im.height
    if ratio > target:                      # too wide — trim the sides evenly
        w = int(im.height * target)
        left = (im.width - w) // 2
        im = im.crop((left, 0, left + w, im.height))
    elif ratio < target:                    # too tall — bias the crop upward,
        h = int(im.width / target)          # since screens hang high in frame
        top = int((im.height - h) * 0.28)
        im = im.crop((0, top, im.width, top + h))
    im = im.resize(size, Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build() -> Path:
    slides = (DECK / "deck.slides.html").read_text()
    slides = slides.replace("__MAP_SVG__", (ASSETS / "deck_map.svg").read_text())
    slides = slides.replace("__VISIT_SVG__", (ASSETS / "deck_visit.svg").read_text())

    html = (DECK / "deck.src.html").read_text().replace("__SLIDES__", slides)

    for token, name in FONTS.items():
        html = html.replace(token, font_uri(name))
    for token, (name, size, quality, crop) in IMAGES.items():
        html = html.replace(token, image_uri(name, size, quality, crop))

    leftover = sorted(set(re.findall(r"__[A-Z_]+__", html)))
    if leftover:
        sys.exit(f"unsubstituted tokens remain: {leftover}")

    OUT.write_text(html)
    slide_count = html.count('<section class="page')
    print(f"built {OUT.relative_to(ROOT)} — "
          f"{OUT.stat().st_size / 1024 / 1024:.2f} MB, {slide_count} slides")
    write_artifact_variant(html)
    return OUT


# The deck is laid out on a fixed 1920x1080 canvas, which is right for print and
# wrong for a web page — it would force the viewer to scroll sideways. Every
# dimension in the chassis is a multiple of --u, so re-anchoring that one variable
# to the container's width scales the whole deck with no other change.
ARTIFACT_CSS = """
/* — screen variant: re-anchor --u to the container so the deck scales — */
.deck{container-type:inline-size; max-width:1920px; margin:0 auto; padding:0 0 2vw;}
.deck .page{width:100%; height:auto; aspect-ratio:16/9; margin:0 0 1.6cqw; --u:1cqw;}
@supports not (container-type: inline-size){
  .deck{max-width:none;}
  .deck .page{--u:1vw; margin:0 0 1.6vw;}
}
html,body{background:#DDD8CC; overflow-x:hidden;}
"""


def write_artifact_variant(html: str) -> Path:
    """Emit the same deck as a fragment the Artifact host can wrap and serve."""
    body = html.split("<body>", 1)[1].rsplit("</body>", 1)[0].strip()
    style = html.split("<style>", 1)[1].split("</style>", 1)[0]
    out = ROOT / "handoffs" / "starkville-athletic-club" / "STARKVILLE-Host-Pitch.artifact.html"
    out.write_text(
        "<title>Starkville Athletic Club × MCTV — Host Partnership</title>\n"
        f"<style>{style}{ARTIFACT_CSS}</style>\n"
        f'<div class="deck">\n{body}\n</div>\n'
    )
    print(f"built {out.relative_to(ROOT)} — {out.stat().st_size / 1024 / 1024:.2f} MB (screen)")
    return out


# A 16:9 canvas maps to no standard paper size, so a print run of this deck is
# normally a custom trim — which is a slow, expensive conversation at a copy
# counter. This imposes each slide on plain US Letter landscape inside a white
# margin: no bleed, no trim marks, no custom stock. It is a walk-up colour copy
# job any shop can run while you wait.
#
# Sized in inches rather than by zoom. The canvas is exactly 100u wide, so setting
# --u to a hundredth of the target width rescales the entire slide with no
# transform and no rounding drift — and the margins then centre it honestly.
# 11 - 2(0.4) = 10.2in wide; 8.5 - 2(1.38) = 5.74in tall; 10.2/5.74 = 16:9.
PRINT_CSS = """
@page{size:letter landscape; margin:1.38in 0.4in;}
html,body{background:#fff;}
.page{width:10.2in; height:5.7375in; --u:0.102in;
      margin:0; box-shadow:none; page-break-after:always;}
.page:last-child{page-break-after:auto;}
"""


def to_print_pdf(src: Path) -> None:
    """Impose the deck on US Letter landscape for a walk-up print shop."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("PDF export needs Playwright: pip install playwright")

    html = src.read_text().replace("</style>", PRINT_CSS + "</style>", 1)
    staged = src.with_name("_print_stage.html")
    staged.write_text(html)
    pdf = src.with_name("STARKVILLE-Host-Pitch-PRINT.pdf")
    try:
        with sync_playwright() as p:
            pinned = sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
            launch = {"executable_path": str(pinned[-1])} if pinned else {}
            browser = p.chromium.launch(**launch)
            page = browser.new_page(viewport={"width": 1980, "height": 1200})
            page.goto(staged.as_uri())
            page.wait_for_timeout(2500)
            page.pdf(path=str(pdf), format="Letter", landscape=True,
                     print_background=True, prefer_css_page_size=True)
            browser.close()
    finally:
        staged.unlink(missing_ok=True)
    print(f"wrote {pdf.relative_to(ROOT)} — {pdf.stat().st_size / 1024 / 1024:.2f} MB (US Letter)")


def to_pdf(src: Path) -> None:
    """Print the deck at its native 1920x1080 canvas, one slide per page."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("PDF export needs Playwright: pip install playwright")

    pdf = src.with_suffix(".pdf")
    with sync_playwright() as p:
        # Prefer the pinned Chromium the image ships; fall back to whatever
        # Playwright resolves on a normal workstation.
        pinned = sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
        launch = {"executable_path": str(pinned[-1])} if pinned else {}
        browser = p.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 1980, "height": 1200})
        page.goto(src.as_uri())
        page.wait_for_timeout(2500)         # let the inlined webfonts settle
        page.pdf(path=str(pdf), width="1920px", height="1080px",
                 print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()
    print(f"wrote {pdf.relative_to(ROOT)} — {pdf.stat().st_size / 1024 / 1024:.2f} MB")


# The concept sheet is a different animal from the deck: one page, portrait, and
# meant to be opened cold in an inbox on a phone before anybody has been pitched.
# It shares the brand (colours, Playfair over Work Sans, the wordmark) and nothing
# else — see the note at the top of concept.src.html for why it does not inherit
# the deck's unit grid. The band photo is sized small on purpose: this rides on an
# email, and a 3MB attachment from a stranger does not get opened.
def build_concept(pdf: bool = False) -> Path:
    src = DECK / "concept.src.html"
    html = src.read_text()
    for token, name in FONTS.items():
        if token in html:
            html = html.replace(token, font_uri(name))
    html = html.replace("__BAND__", image_uri("davis-wade.jpg", (1500, 470), 80, None))

    leftover = sorted(set(re.findall(r"__[A-Z_]+__", html)))
    if leftover:
        sys.exit(f"unsubstituted tokens remain in concept sheet: {leftover}")

    out = DECK / "STARKVILLE-Concept-Sheet.html"
    out.write_text(html)
    print(f"built {out.relative_to(ROOT)} — {out.stat().st_size / 1024:.0f} KB")
    if pdf:
        concept_pdf(out)
    return out


def concept_pdf(src: Path) -> Path:
    """Print the concept sheet to a one-page US Letter portrait PDF."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("PDF export needs Playwright: pip install playwright")

    pdf = src.with_suffix(".pdf")
    with sync_playwright() as p:
        pinned = sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
        launch = {"executable_path": str(pinned[-1])} if pinned else {}
        browser = p.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        page.goto(src.as_uri())
        page.wait_for_timeout(2000)
        # The whole point of a concept sheet is that it is one page. Letter minus
        # the 0.5in @page margins leaves 10in, and the sheet renders at the same
        # 7.2in column on screen as it does in print, so this measurement holds.
        # It has already caught one silent spill onto a second page.
        height_in = page.evaluate(
            "() => document.querySelector('.sheet').scrollHeight / 96")
        if height_in > 10.0:
            sys.exit(f"concept sheet is {height_in:.3f}in tall — over the 10in "
                     f"page by {(height_in - 10) * 72:.1f}pt, so it would print "
                     f"on two pages. Trim copy or spacing.")
        print(f"  sheet height {height_in:.3f}in of 10.0in")
        page.pdf(path=str(pdf), format="Letter", print_background=True,
                 prefer_css_page_size=True)
        browser.close()
    print(f"wrote {pdf.relative_to(ROOT)} — {pdf.stat().st_size / 1024:.0f} KB")
    return pdf


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", action="store_true", help="also print the deck to PDF")
    ap.add_argument("--print-package", action="store_true",
                    help="also impose the deck on US Letter landscape for a copy shop")
    ap.add_argument("--concept", action="store_true",
                    help="build the one-page concept sheet instead of the deck")
    args = ap.parse_args()
    if args.concept:
        build_concept(pdf=args.pdf)
        sys.exit(0)
    built = build()
    if args.pdf:
        to_pdf(built)
    if args.print_package:
        to_print_pdf(built)
