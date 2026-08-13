# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Assemble the Huntington Bank Arena outreach email as a reviewable .eml draft.

    python handoffs/huntington-bank-arena/build_email.py

Writes output/emails/Huntington_Bank_Arena_Alli_Shackelford.eml with the host
media kit attached. Open it in Outlook, review, then Send. Nothing is sent from
here — the .eml is a draft artifact, not a transmission.

Run build_deck.py first; this attaches the PDF it produces.
"""

import pathlib
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PDF = ROOT / "output" / "proposals" / "MCTV_Host_Media_Kit_Huntington_Bank_Arena.pdf"
OUT = ROOT / "output" / "emails" / "Huntington_Bank_Arena_Alli_Shackelford.eml"

FROM = "T. CREED CANNON <CREED@MCTVOFMS.COM>"
TO = "Alli Shackelford <alli@hbarena.com>"
SUBJECT = "MCTV | Huntington Bank Arena — Host Partnership Overview"

SIG_LINES = ["T. Creed Cannon", "Managing Partner", "MCTV Digital, Inc",
             "601-201-8202", "www.mctvofms.com"]

BULLETS = [
    ("The structure is the same one the Tupelo Airport Authority board approved in March. "
     "Their screens went live in April and run across the lobby, ticket counter, baggage claim "
     "and the sterile corridor. Happy to put you in touch with Dylan over there if you'd like "
     "an unfiltered opinion."),
    ("Page 6 is a starting map for screen placement, not a final one. We'd want to walk the "
     "building with you and set the count and the positions together."),
    ("Page 9 covers the piece I think matters most for you — your event calendar running "
     "across all 125+ of our screens in Tupelo, Oxford and the Golden Triangle, at no charge. "
     "That is reach you would otherwise be buying."),
    ("The revenue figures on page 8 are illustrative. Once we have walked the facility we will "
     "model it properly against your actual traffic."),
]

OPENING = [
    ("Thank you for your time today — we really enjoyed getting to see the building and "
     "hear where you are wanting to take it."),
    ("As promised, I have attached a host media kit put together specifically for the Arena and "
     "Conference Center. It walks through what we discussed: we install and own the screens, we "
     "sell and service the advertising that runs on them, and the Arena takes a share of "
     "everything sold — with no capital cost to you at any point."),
    "A few things worth flagging as you look through it:",
]

CLOSING = [
    ("If it looks like a fit, the next step is just a walkthrough at your convenience — "
     "about an hour — and we will bring a draft agreement and our certificate of insurance "
     "with us."),
    "Thanks again, and I look forward to hearing what you think.",
]


def plain_text():
    parts = ["Alli,", ""]
    for p in OPENING:
        parts += [p, ""]
    for b in BULLETS:
        parts += ["  -  " + b, ""]
    for p in CLOSING:
        parts += [p, ""]
    parts += ["Best Regards,", ""] + SIG_LINES
    return "\n".join(parts)


def html_body():
    p = "".join(f"<p>{t}</p>" for t in OPENING)
    li = "".join(f"<li>{b}</li>" for b in BULLETS)
    c = "".join(f"<p>{t}</p>" for t in CLOSING)
    sig = "<br>".join(SIG_LINES)
    return f"""<html><body style="font-family:Aptos,Calibri,sans-serif;font-size:12pt;color:#000">
<p>Alli,</p>
{p}
<ul>{li}</ul>
{c}
<p>Best Regards,</p>
<p>{sig}</p>
</body></html>"""


def main():
    if not PDF.exists():
        sys.exit(f"missing {PDF} — run build_deck.py first")

    msg = EmailMessage()
    msg["From"] = FROM
    msg["To"] = TO
    msg["Subject"] = SUBJECT
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="mctvofms.com")
    msg["X-Unsent"] = "1"  # Outlook opens it as an editable draft, not a received item

    msg.set_content(plain_text())
    msg.add_alternative(html_body(), subtype="html")
    msg.add_attachment(PDF.read_bytes(), maintype="application", subtype="pdf",
                       filename=PDF.name)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(msg.as_bytes())
    print(f"wrote {OUT}  ({OUT.stat().st_size // 1024} KB)")
    print(f"  attached: {PDF.name}")


if __name__ == "__main__":
    main()
