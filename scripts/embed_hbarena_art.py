# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Drop the arena's real tour art into the Huntington Bank Arena mockup.

The mockup ships with gradients standing in for artwork, because the art lives
on Ticketmaster's CDN and the build container cannot reach it. Once you have
the files — the promoter sends them to the arena, and the arena's own emails
carry them — this puts them on the slides:

    handoffs/hbarena-arena/art/blackberry-smoke.jpg
    handoffs/hbarena-arena/art/disney-on-ice.jpg
    handoffs/hbarena-arena/art/anthony-hamilton.jpg
    handoffs/hbarena-arena/art/labor-day.jpg

    python scripts/embed_hbarena_art.py

Any of the four may be missing; a slide with no file keeps its gradient. Run it
again after replacing a file and it re-embeds — it is idempotent, because it
rewrites the same `--art` declaration rather than appending a new one.

The page has to stay self-contained (it is served as one static file, and the
artifact viewer blocks off-site images outright), so each image is resized,
re-encoded as JPEG and inlined as a data URI. 1600px wide is plenty: the slide
is 1920 at most on a lobby screen, and the scrim covers the left half anyway.

Where to find the art, in order of preference:
  1. Ask Alli — it is ask #2 in the follow-up email, and the promoter has
     already sent it to her in print resolution.
  2. Pull it out of the arena's own announcement emails. The July 28
     "JUST ANNOUNCED: BLACKBERRY SMOKE" send embeds these:
       https://assets.engagement.ticketmaster.com/images/properties/150/images/6a68aec62b104.png  (hero)
       https://assets.engagement.ticketmaster.com/images/properties/150/images/6a4d4f56ee46f.png  (secondary)
       https://assets.engagement.ticketmaster.com/images/properties/150/images/6a3ec7dd0d197.png  (arena logo)
     Open the email in a browser and save the images, or curl them from a
     machine whose network policy allows that host.

Using the promoter's art in a mockup we show back to the arena is the point —
it is their campaign, rendered on our screens. Do not put it on a live screen
until the arena says the placement is approved.
"""

import base64
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PAGE = ROOT / "static" / "hbarena_mockup.html"
ART_DIR = ROOT / "handoffs" / "hbarena-arena" / "art"

# slide css class -> basename of its art file (any common extension)
SLIDES = {
    "art-bbs": "blackberry-smoke",
    "art-ice": "disney-on-ice",
    "art-ah": "anthony-hamilton",
    "art-sale": "labor-day",
}

EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
MAX_WIDTH = 1600
JPEG_QUALITY = 82


def find_art(stem: str) -> Path | None:
    for ext in EXTENSIONS:
        candidate = ART_DIR / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def data_uri(path: Path) -> str:
    from PIL import Image

    im = Image.open(path)
    # Flatten transparency onto black — the slides are dark, and a transparent
    # PNG re-encoded to JPEG would otherwise composite onto white.
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, (8, 10, 16))
        flat.paste(im, mask=im.split()[-1])
        im = flat
    else:
        im = im.convert("RGB")
    if im.width > MAX_WIDTH:
        im.thumbnail((MAX_WIDTH, MAX_WIDTH * 4), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    encoded = base64.b64encode(buf.getvalue()).decode()
    return f"url(data:image/jpeg;base64,{encoded})", im.size, len(encoded)


def main() -> int:
    if not PAGE.exists():
        print(f"missing {PAGE}", file=sys.stderr)
        return 1
    ART_DIR.mkdir(parents=True, exist_ok=True)

    html = PAGE.read_text()
    embedded = 0

    for css_class, stem in SLIDES.items():
        art = find_art(stem)
        if art is None:
            print(f"  {css_class:9s} no art file — keeping the gradient")
            continue

        uri, size, nbytes = data_uri(art)
        # The rule is `.art-bbs{background: ...}` — add or replace an --art
        # custom property inside that same block.
        pattern = re.compile(r"(\." + re.escape(css_class) + r"\{background:)(.*?)(\})", re.S)
        match = pattern.search(html)
        if not match:
            print(f"  {css_class:9s} no CSS block found — skipped", file=sys.stderr)
            continue
        body = re.sub(r";?\s*--art:\s*url\(data:[^)]*\)", "", match.group(2))
        html = html[: match.start()] + match.group(1) + body.rstrip().rstrip(";") \
            + f";\n    --art:{uri}" + match.group(3) + html[match.end():]

        # The slide needs the art layer element too; add it once.
        marker = f'<div class="screen {css_class}">'
        if marker in html and f'{marker}\n          <div class="art"></div>' not in html:
            html = html.replace(marker, f'{marker}\n          <div class="art"></div>')

        print(f"  {css_class:9s} {art.name} -> {size[0]}x{size[1]}, {nbytes/1024:.0f}KB inline")
        embedded += 1

    PAGE.write_text(html)
    print(f"\n{embedded} slide(s) carry real art. Page is {PAGE.stat().st_size/1024:.0f}KB.")
    if embedded:
        print("Re-publish the artifact and re-run scripts/route_check.py before sending.")
    else:
        print(f"Put the files in {ART_DIR.relative_to(ROOT)}/ and run this again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
