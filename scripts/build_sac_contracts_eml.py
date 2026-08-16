#!/usr/bin/env python3
"""Build the three Starkville Athletic Club contracts and wrap them in an .eml.

Creed asked, from the road half an hour out from the meeting, for the contracts
printed and dropped into an Outlook message to Swayze. This produces all three
rungs of the offer ladder as PDFs (print-ready) with the Word originals
alongside, and packages them into a single .eml he can double-click.

    python scripts/build_sac_contracts_eml.py

Rungs, per handoffs/starkville-athletic-club/PITCH-BRIEF.md section 4:

    0  Venue Hosting Agreement       $0/mo    5 screens at the club
    1  Host Advertising Agreement    $199/mo  10-screen Starkville block
    3  Category Exclusivity          +$200/mo fitness lockout, 12-month term

Rung 2 (full territory, $599) is deliberately not generated — Creed asked for
1, 2 and 3 of the options put to him, which were host, host+advertising and
host+exclusivity. The $199 block is the brief's recommended advertising rung;
if he closes the $599 territory instead, rerun with TERRITORY = True.

Copyright (c) MCTV Digital, Inc. Proprietary.
"""
from __future__ import annotations

import sys
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generators.contract_generator import ContractGenerator  # noqa: E402

OUT = ROOT / "handoffs" / "starkville-athletic-club" / "contracts"
CLIENT = "Joe Underwood"
BUSINESS = "Starkville Athletic Club"
REP = "T. Creed Cannon"
START = datetime.now().strftime("%Y-%m-%d")
TERRITORY = False  # flip to True if he takes the $599 full territory instead

# The exclusivity boundary from PITCH-BRIEF section 4. This has to be written down
# rather than left as "fitness and wellness" — two businesses inside that looser
# phrase are already Starkville hosts running their own ads, so a loose wording
# puts us in breach the day we sign.
EXCLUSIVITY_NOTE = (
    "Monthly rate of $399 comprises the $199 ten-screen Starkville host block plus "
    "the $200 category exclusivity premium, and replaces the separate Host "
    "Advertising Agreement rather than adding to it. Exclusivity applies across all "
    "31 MCTV screens in Starkville, not only the ten carrying Advertiser's spot. "
    "Covered category: gyms, fitness studios, health clubs, and personal training "
    "facilities. Not covered: supplement and nutrition retail, med-spa, wellness "
    "clinics, and physical therapy. Advertiser acknowledges 39759 Nutrition and "
    "Revive Wellness Clinic - Starkville as existing MCTV host venues falling "
    "outside the covered category."
)

HOST_NOTE = (
    "Host partnership is provided at no cost for the life of the agreement: "
    "hardware, installation, mounting, maintenance, ad creative and quarterly "
    "refreshes are all included. Venue Host receives 8 plays per hour on each of "
    "the 5 screens installed at the club, plus 4 plays per hour across 10 "
    "additional MCTV screens in other Starkville venues, at no charge. "
    "No minimum purchase and no obligation to buy advertising. Either party may "
    "terminate with 30 days written notice per Section 4, and MCTV removes all "
    "hardware at its own cost."
)

ADVERTISING_NOTE = (
    "Host-partner rate. Covers a defined ten-screen block of Starkville's "
    "longest-dwell venues, and is held separately from the free host placements "
    "under the Venue Hosting Agreement. Published rate for ten screens is $350/mo. "
    "Prepay six months and the seventh is free; prepay twelve and the thirteenth "
    "and fourteenth are free."
)

CONTRACTS = [
    dict(
        key="1-Host-Agreement-FREE",
        contract_type="host",
        tier_name="Host Partnership - 5 Screens",
        screen_count=5,
        monthly_rate=0.0,
        term_months=12,
        auto_renew=True,
        notes=HOST_NOTE,
    ),
    dict(
        key="2-Advertising-199",
        contract_type="host_advertising",
        tier_name=("Full Starkville Territory - 31 Screens" if TERRITORY
                   else "Starkville Host Rate - 10 Screens"),
        screen_count=31 if TERRITORY else 10,
        monthly_rate=599.0 if TERRITORY else 199.0,
        term_months=6,
        auto_renew=True,
        notes=ADVERTISING_NOTE,
    ),
    dict(
        key="3-Block-plus-Exclusivity-399",
        contract_type="category_exclusivity",
        tier_name="Ten-Screen Block + Fitness Exclusivity - Starkville",
        # $399, not $200. The template prints this field as "Monthly Rate (incl.
        # exclusivity premium)", so feeding it the bare +$200 premium produces a
        # contract stating the monthly rate is $200 — which, sitting next to a
        # separate $199 agreement, leaves three defensible readings of what Joe
        # actually owes. This rung replaces the advertising agreement rather than
        # stacking on it: $199 block + $200 premium = $399, for twelve months.
        screen_count=10,
        monthly_rate=399.0,
        term_months=12,
        auto_renew=True,
        exclusive_category="Gyms, fitness studios, health clubs, and personal training facilities",
        notes=EXCLUSIVITY_NOTE,
    ),
]


def build() -> list[tuple[str, Path, Path | None]]:
    OUT.mkdir(parents=True, exist_ok=True)
    gen = ContractGenerator()
    built = []
    for spec in CONTRACTS:
        key = spec.pop("key")
        docx, pdf, _ = gen.generate(
            client_name=CLIENT,
            business_name=BUSINESS,
            markets=["Starkville"],
            start_date=START,
            prepared_by=REP,
            **spec,
        )
        label = ContractGenerator.CONTRACT_LABELS[spec["contract_type"]]
        print(f"  {label:34} {'PDF' if pdf else 'DOCX only':9} {Path(docx).name}")
        built.append((key, Path(docx), Path(pdf) if pdf else None))
    return built


BODY = """Swayze,

Contracts for Starkville Athletic Club, ready to print. Joe Underwood, 100 Eckford
Drive. All three rungs so I can sign whichever one he takes without driving back.

  1. Venue Hosting Agreement - $0/mo, 5 screens at the club plus 10 free around
     town. This is the one that gets signed today if anything does.

  2. Host Advertising Agreement - $199/mo for the ten-screen block. Only if he
     asks to reach past the free screens.

  3. Block + Fitness Exclusivity - $399/mo, 12 months. That is the $199 block
     plus the $200 premium on one page; it replaces number 2 rather than stacking
     on it, so he signs 1 and 3, never 1, 2 and 3. Hold it back - it is the close,
     not the opener. The covered category is written into the notes so we are not
     in breach over 39759 Nutrition or Revive Wellness.

Nothing here is signed and nothing is committed. If he wants the full territory
instead of the block it is $599 and I will need a new page - the floor is $499
with a twelve-month prepay.

Creed
"""


def main() -> None:
    print("Generating contracts...")
    built = build()

    msg = EmailMessage()
    msg["From"] = "T. Creed Cannon <creed@mctvofms.com>"
    msg["To"] = "Swayze Hollingsworth <swayze@mctvofms.com>"
    msg["Subject"] = "Starkville Athletic Club - contracts to print"
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="mctvofms.com")
    msg["X-Unsent"] = "1"  # opens as a composable draft in Outlook, not a sent item
    msg.set_content(BODY)

    attached = 0
    for _key, docx, pdf in built:
        for path, subtype in ((pdf, "pdf"), (docx, "docx")):
            if not path or not path.exists():
                continue
            maintype, sub = (
                ("application", "pdf") if subtype == "pdf"
                else ("application",
                      "vnd.openxmlformats-officedocument.wordprocessingml.document")
            )
            # The generator names files by timestamp, which is fine on disk and
            # useless in an attachment list when you are picking one to print at
            # a counter. Rename on the way into the message.
            nice = f"SAC-{_key}{path.suffix}"
            msg.add_attachment(path.read_bytes(), maintype=maintype,
                               subtype=sub, filename=nice)
            attached += 1

    eml = OUT / "Starkville-Athletic-Club-Contracts.eml"
    eml.write_bytes(bytes(msg))
    size = eml.stat().st_size / 1024 / 1024
    print(f"\nwrote {eml.relative_to(ROOT)} - {size:.2f} MB, {attached} attachments")


if __name__ == "__main__":
    main()
