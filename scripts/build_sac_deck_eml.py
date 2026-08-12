#!/usr/bin/env python3
"""Wrap the Starkville deck PDF in ready-to-send .eml drafts.

Two versions, because "send her the deck" reads two ways and the body copy is
not interchangeable between them:

    Deck-to-Swayze.eml   internal, Creed -> Swayze Hollingsworth
    Deck-to-Club.eml     client-facing, Creed -> the club's inbox, written for Joe

Both carry STARKVILLE-Host-Pitch.pdf (the native 1920x1080 screen version, not
the US Letter print imposition — that one is for the copy counter and looks
wrong on a screen). Both are stamped X-Unsent so Outlook opens them as
composable drafts; nothing sends until a human clicks send.

    python scripts/build_sac_deck_eml.py

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
PDF = DECK / "STARKVILLE-Host-Pitch.pdf"
FROM = "T. Creed Cannon <creed@mctvofms.com>"

INTERNAL_BODY = """Swayze,

Full deck for Starkville Athletic Club, attached. Fifteen slides, same one I am
walking Joe Underwood through.

Worth knowing before you use any of it on the next Starkville call:

  - Slide 05 names Rebel Body Fitness. The partner wall has its logo on it, so
    the caption says out loud that the one gym on the network is in Oxford and
    there is not one on a Starkville screen. Do not go back to "not one of them
    is a gym" - the wall contradicts it in plain sight.

  - Slide 13's season card is "Football season", not "Mississippi State". We do
    not hold any MSU athletics rights and should not print anything that reads
    like we do.

  - The board times on slide 08 are placeholders. Class names are real, the
    schedule is not, and the slide says so.

Numbers are all measured off the NTV360 dashboard except the network headline
figures, which match the published media kit.

Creed
"""

CLIENT_BODY = """Joe,

Here is the full deck, as promised - fifteen pages, attached.

The short version has not changed: five screens in the club at no cost to you,
a live schedule board in the lobby, and your ad on ten more screens around
Starkville. Nothing on the hosting side carries a bill or an obligation to buy
advertising.

Two things I would still like from you when you have a minute. Your real class
schedule, so we can load it into the board and you can see it running with your
own classes on it rather than my placeholders. And your hours - I did not want
to guess at them in writing.

Anything in here you want walked through again, call me.

Creed Cannon
MCTV Elite Advertising
601-201-8202 - creed@mctvofms.com - mctvofms.com
"""

MESSAGES = [
    dict(
        out="Deck-to-Swayze.eml",
        to="Swayze Hollingsworth <swayze@mctvofms.com>",
        subject="Starkville Athletic Club - the deck",
        body=INTERNAL_BODY,
        attach_as="Starkville-Athletic-Club-MCTV-Host-Partnership.pdf",
    ),
    dict(
        out="Deck-to-Club.eml",
        to="Starkville Athletic Club <admin@starkvilleathleticclub.com>",
        subject="Starkville Athletic Club x MCTV - the full deck",
        body=CLIENT_BODY,
        attach_as="Starkville-Athletic-Club-MCTV-Host-Partnership.pdf",
    ),
]


def main() -> None:
    if not PDF.exists():
        sys.exit(f"deck PDF missing: {PDF}\n"
                 f"run: python scripts/build_starkville_deck.py --pdf")
    payload = PDF.read_bytes()
    OUT.mkdir(parents=True, exist_ok=True)

    for spec in MESSAGES:
        msg = EmailMessage()
        msg["From"] = FROM
        msg["To"] = spec["to"]
        msg["Subject"] = spec["subject"]
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="mctvofms.com")
        msg["X-Unsent"] = "1"
        msg.set_content(spec["body"])
        msg.add_attachment(payload, maintype="application", subtype="pdf",
                           filename=spec["attach_as"])
        path = OUT / spec["out"]
        path.write_bytes(bytes(msg))
        print(f"wrote {path.relative_to(ROOT)} - "
              f"{path.stat().st_size / 1024 / 1024:.2f} MB -> {spec['to']}")


if __name__ == "__main__":
    main()
