#!/usr/bin/env python3
"""Print instructions for the agreement form, as an .eml to Swayze.

The instructions live in the body rather than as an attached markdown file,
because whoever is standing at the counter is reading this on a phone and should
not have to open anything to answer "what stock?".

    python scripts/build_sac_print_eml.py

Copyright (c) MCTV Digital, Inc. Proprietary.
"""
from __future__ import annotations

import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "handoffs" / "starkville-athletic-club" / "contracts"
FORM = OUT / "SAC-Agreement-Payment-Form.pdf"

BODY = """Swayze,

Attached is the Starkville Athletic Club agreement and payment form. One page.
Copy Cow at 306 University Drive is the closest and they are one of our own host
venues - worth mentioning at the counter.

The ask, in one line:

  "One page, letter, portrait, full colour, actual size, on your heaviest
   UNCOATED stock. Six copies. No coating, no finishing."

THE ONE THING THAT MATTERS

Uncoated. Not gloss, not silk, not "premium."

Ask a print counter for good paper and they reach for coated gloss, because that
is what looks expensive on a flyer. A pen skates on gloss. Joe is going to write
his bank routing number and sign his name on this page. On a coated sheet a
ballpoint skips and gel ink smears under his hand.

Say the word uncoated out loud. If they show you a sample, drag a pen across it
before you agree to it.

SPECS

  Pages ........ 1
  Size ......... US Letter, 8.5 x 11
  Orientation .. Portrait
  Colour ....... Full colour
  Stock ........ UNCOATED, 28-32 lb bond / 70-80 lb text. 100 lb uncoated text
                 if they have it.
  Shade ........ Bright white or natural white. Not cream - it fights the cream
                 panels already on the form.
  Scaling ...... Actual size / 100%. Not "fit to page."
  Sides ........ Single-sided
  Finishing .... None. No staple, no fold, no lamination.
  Copies ....... 6

Six because he will change his mind about which box to tick at least once, and a
crossed-out checkbox on a payment authorization looks sloppy. Blanks are cheap,
driving back is not.

AVOID

  - "Fit to page." The form is drawn to the sheet with its own margins. Shrink it
    and the fields land in the wrong place for a pen.
  - Cardstock. 80 lb cover or heavier is stiff to write on without a hard surface
    under it. Text weight, not cover weight.
  - Any coating or protective finish. It is a form. It gets written on.
  - Printing it pre-filled. Print it blank. Every field gets completed by hand in
    front of him, including the package box and the amount authorized.

IF SOMETHING IS NOT AVAILABLE

  - No heavy uncoated: take standard 24 lb uncoated over any coated stock at any
    weight. Writability beats heft on this page.
  - Colour printer down: greyscale is fine here, unlike the deck. The form is
    legible and legally complete in black and white.
  - Shop backed up: it is one page. Ask for the self-serve machine - colour,
    letter, actual size, uncoated tray.

ONCE IT IS SIGNED

The completed page carries bank account and card details. Do not leave it face-up
on a counter or a passenger seat, do not photograph it and text it to anybody, and
if a copy has to move by email it goes encrypted. Hand it to accounting directly
and the paper goes in the file. That is why the footer says Confidential.

Creed
"""


def main() -> None:
    if not FORM.exists():
        sys.exit(f"form PDF missing: {FORM}")

    msg = EmailMessage()
    msg["From"] = "T. Creed Cannon <creed@mctvofms.com>"
    msg["To"] = "Swayze Hollingsworth <swayze@mctvofms.com>"
    msg["Subject"] = "Starkville Athletic Club agreement - print instructions"
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="mctvofms.com")
    msg["X-Unsent"] = "1"
    msg.set_content(BODY)
    msg.add_attachment(FORM.read_bytes(), maintype="application", subtype="pdf",
                       filename="SAC-Agreement-and-Payment-Form-PRINT-THIS.pdf")

    out = OUT / "Print-Instructions-to-Swayze.eml"
    out.write_bytes(bytes(msg))
    print(f"wrote {out.relative_to(ROOT)} - {out.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
