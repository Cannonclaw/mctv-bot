# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Extract copy.md from the built deck so the copy deck can never drift from it.

    python handoffs/huntington-bank-arena/build_copydeck.py

Run after build_deck.py. copy.md is generated — edit build_deck.py, not copy.md.
"""

import html
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
DECK = HERE / "deck.html"
OUT = HERE / "copy.md"

TITLES = [
    "Cover", "What we're proposing", "Proof — Tupelo Regional", "Seen in the wild",
    "The network & the value", "The company you'd keep", "Where your screens would go",
    "Not a wall of ads", "What it costs you: nothing", "Sixty / forty",
    "Your calendar, on every screen we own", "Who we are", "Owner-operated, and local",
    "How this actually happens", "Thank you",
]

BLOCK_END = re.compile(r"</(p|div|h1|h2|h3|li|td|th|tr|section|table|ul|a|span)>")
SENT = "\x00"  # block boundary marker, survives the tag strip


def blocks(chunk):
    chunk = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", chunk, flags=re.S)
    chunk = re.sub(r"<br\s*/?>", SENT, chunk)
    chunk = BLOCK_END.sub(SENT, chunk)
    chunk = re.sub(r"<[^>]+>", " ", chunk)
    chunk = html.unescape(chunk)
    # Collapse the source file's own line wrapping before splitting on real blocks,
    # otherwise every wrapped sentence arrives as two fragments.
    chunk = chunk.replace("\n", " ").replace("\r", " ")
    parts = (re.sub(r"\s+", " ", p).strip() for p in chunk.split(SENT))
    return [p for p in parts if p]


def main():
    if not DECK.exists():
        sys.exit(f"missing {DECK} — run build_deck.py first")
    body = DECK.read_text().split("<body>", 1)[1].replace("</body></html>", "")
    slides = ['<section class="slide' + s
              for s in body.split('<section class="slide') if s.strip()]

    out = [
        "# Copy deck — Huntington Bank Arena host media kit",
        "",
        "Generated from `deck.html` by `build_copydeck.py`; do not hand-edit.",
        "Every string below is final copy, approved for send. Layout may change in redesign;",
        "wording may not, except where `DESIGN-BRIEF.md` explicitly allows it.",
        "",
    ]
    for i, s in enumerate(slides, 1):
        tone = "navy" if "slide navy" in s.split(">")[0] else "cream"
        title = TITLES[i - 1] if i <= len(TITLES) else f"Page {i}"
        out += [f"## Page {i:02d} — {title}  ·  _{tone} spread_", ""]
        out += [f"- {line}" for line in blocks(s)]
        out.append("")

    OUT.write_text("\n".join(out))
    print(f"wrote {OUT}  ({len(slides)} pages)")


if __name__ == "__main__":
    main()
