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

ATTACHMENTS = [
    (DECK / "STARKVILLE-Host-Pitch.pdf",
     "1-DECK-Starkville-Athletic-Club.pdf"),
    (OUT / "SAC-1-Host-Agreement-FREE.pdf",
     "2-AGREEMENT-Host-FREE.pdf"),
    (OUT / "SAC-2-Advertising-199.pdf",
     "3-AGREEMENT-Advertising-199.pdf"),
    (OUT / "SAC-3-Block-plus-Exclusivity-399.pdf",
     "4-AGREEMENT-Block-plus-Exclusivity-399.pdf"),
]

BODY = """Starkville Athletic Club - Joe Underwood - 100 Eckford Drive
Wednesday 12 August 2026, 10:30 AM

Attached, in the order you would use them:

  1. DECK - 15 pages. Cover, the offer, what changed since March 2025, the
     network and the map, partners, where the ad runs, screens in the wild,
     the lobby board, the economics, the dwell math, the traction report,
     exclusivity, the ladder, the wider network, next steps.

  2. HOST AGREEMENT - $0/mo. Five screens at the club, ten free around
     Starkville, 12 months, auto-renews. Hardware, install, creative and
     quarterly refreshes included. No minimum and no obligation to buy
     advertising. Either party can end it on 30 days notice and we remove the
     hardware at our cost.

  3. ADVERTISING - $199/mo, 6 months. Ten-screen block of the longest-dwell
     venues in town. Published rate for ten screens is $350.

  4. BLOCK + FITNESS EXCLUSIVITY - $399/mo, 12 months. That is the $199 block
     plus the $200 exclusivity premium on one page. It replaces number 3
     rather than adding to it - sign 2 and 4, or 2 and 3, never all three.
     Covered category is gyms, fitness studios, health clubs and personal
     training. Not covered: supplement and nutrition retail, med-spa, wellness
     clinics, physical therapy.

Full territory is $599/mo for all 25 venues and 31 screens. No page drawn for
it - say the word and I will have one.

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
