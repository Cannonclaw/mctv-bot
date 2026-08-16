#!/usr/bin/env python3
"""Self-addressed .eml carrying the Starkville deck and all three agreements.

Creed wanted one message from himself to himself so it lands in Outlook and
syncs to the tablet he will have open in the meeting. Send it to yourself and it
appears on every device; that is the whole mechanism, which is why this one is
stamped X-Unsent like the others — it opens as a draft with Send waiting.

    python scripts/build_sac_self_eml.py

PDFs only, deliberately. The Word originals are in the message to Swayze; on a
tablet they are dead weight and they slow the attachment list down.

The body is written to be safe on a screen somebody else can see. This message
will be open on a tablet in front of the prospect, so it carries no walk-away
floors, no "hold this one back", and nothing about how to work the room — all of
that lives in PITCH-BRIEF.md, which stays on the laptop. What is here is an
index and two questions.

Copyright (c) MCTV Digital, Inc. Proprietary.
"""
from __future__ import annotations

import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECK = ROOT / "handoffs" / "starkville-athletic-club"
OUT = DECK / "contracts"
ME = "T. Creed Cannon <creed@mctvofms.com>"

# The form leads. It is the page that gets a pen on it; the long-form agreements
# behind it are backup. The $399 block-plus-exclusivity contract is deliberately
# not here — it is not one of the five options on the form, and a fourth price
# floating around on a tablet in front of the client is the exact confusion this
# message exists to avoid. It is still on disk if it is wanted.
ATTACHMENTS = [
    (OUT / "SAC-Agreement-Payment-Form.pdf",
     "1-SIGN-THIS-Agreement-and-Payment-Form.pdf"),
    (DECK / "STARKVILLE-Host-Pitch.pdf",
     "2-DECK-Starkville-Athletic-Club.pdf"),
    (OUT / "SAC-1-Host-Agreement-FREE.pdf",
     "3-LONGFORM-Host-FREE.pdf"),
    (OUT / "SAC-2-Advertising-199.pdf",
     "4-LONGFORM-Advertising-199.pdf"),
]

BODY = """Starkville Athletic Club - Joe Underwood - 100 Eckford Drive
Wednesday 12 August 2026

  1. AGREEMENT + PAYMENT FORM - one page, tick one box and sign. This is the
     one that gets completed. Five options on it:

        Hosting only, no advertising ............ $0/mo    no term
        Starkville host rate, ten-screen block .. $199/mo  6 months
        Full Starkville market, 31 screens ...... $599/mo  12 months
        Full Starkville + fitness exclusivity ... $700/mo  12 months
        Golden Triangle + exclusivity + season .. $999/mo  12 months

     Hosting is free on every line, including the paid ones. Payment block on
     the same page - ACH no fee, card plus 3.5%. Prepay six and the seventh is
     free; prepay twelve and the thirteenth and fourteenth are free.

  2. DECK - 15 pages, the one we walked through.

  3. LONG-FORM HOST AGREEMENT - $0/mo. Five screens at the club, ten free
     around Starkville, 12 months, auto-renews. Hardware, install, creative and
     quarterly refreshes included. No minimum, no obligation to buy advertising.
     Either party ends it on 30 days notice and we pull the hardware at our cost.

  4. LONG-FORM ADVERTISING - $199/mo, 6 months, ten-screen block. Published
     rate for ten screens is $350.

Exclusivity covers gyms, fitness studios, health clubs and personal training.
Not supplement or nutrition retail, med-spa, wellness clinics or physical
therapy - 39759 Nutrition and Revive Wellness are existing hosts and stay.

Golden Triangle is 35 screens: Starkville 31, Columbus 3, West Point 1.

Two things to get from Joe:

  - The real class schedule. The board times in the deck are placeholders.
  - The actual staffed hours, against the 24-hour key card access.
"""


def main() -> None:
    missing = [str(p) for p, _ in ATTACHMENTS if not p.exists()]
    if missing:
        sys.exit("missing attachments:\n  " + "\n  ".join(missing))

    msg = EmailMessage()
    msg["From"] = ME
    msg["To"] = ME
    msg["Subject"] = "Starkville Athletic Club - deck + agreements - 12 Aug 2026"
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="mctvofms.com")
    msg["X-Unsent"] = "1"
    msg.set_content(BODY)

    for path, name in ATTACHMENTS:
        msg.add_attachment(path.read_bytes(), maintype="application",
                           subtype="pdf", filename=name)

    out = OUT / "Starkville-Athletic-Club-DECK-and-AGREEMENTS.eml"
    out.write_bytes(bytes(msg))
    print(f"wrote {out.relative_to(ROOT)} - "
          f"{out.stat().st_size / 1024 / 1024:.2f} MB, {len(ATTACHMENTS)} attachments")
    for _p, name in ATTACHMENTS:
        print(f"    {name}")


if __name__ == "__main__":
    main()
