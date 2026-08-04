#!/usr/bin/env python3
# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Smoke-test every proposal generator end to end, offline.

Runs the real BaseProposal.generate() pipeline for ALL proposal types against a
stub Claude, and asserts each one lands a file on disk. No API key, no network.

This exists because Host Media Kit, Venue Partner, and Multi-Brand Bundle
shipped broken: BaseProposal.generate() built its filename from
input_data.business_name, which those three input dataclasses do not define, so
every one of them crashed on the final save. Nothing caught it because
generate_samples_offline.py hand-builds documents through DocxService and only
ever constructs ProposalInput -- the shared pipeline had no coverage at all.

Run from the project root:
    python scripts/proposal_smoke_test.py

Exits non-zero if any proposal type fails.
"""

import io
import sys
import traceback
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from services.config_service import load_config
from services.docx_service import DocxService
from models.proposal_data import (
    ProposalInput, HostInput, BundleInput, BundleBusiness,
    VenuePartnerInput, ExclusivityInput, RenewalInput, NILPartnerInput,
)
from generators.elite_advertiser import EliteAdvertiserProposal
from generators.host_media_kit import HostMediaKitProposal
from generators.multi_brand_bundle import MultiBrandBundleProposal
from generators.venue_partner import VenuePartnerProposal
from generators.category_exclusivity import CategoryExclusivityProposal
from generators.renewal_upgrade import RenewalUpgradeProposal
from generators.nil_partnership import NILPartnershipProposal
from generators.nil_handout import NILHandout


class StubClaude:
    """Stands in for ClaudeService with deterministic, parseable output.

    Section parsers expect one paragraph followed by "- Title: Body" bullets,
    so the stub returns exactly that shape for every section.
    """

    def build_section_prompt(self, proposal_type, section_key, variables):
        return f"{proposal_type}:{section_key}"

    def generate_section(self, prompt):
        return (
            "This is a stub opening paragraph for the smoke test.\n"
            "- First Point: A short supporting sentence.\n"
            "- Second Point: Another short supporting sentence."
        )

    def generate_email(self, prompt):
        return "Subject: Smoke test\n\nBody line.\n\n-- Team"


# Names deliberately include characters that have broken the filename path
# before: an apostrophe, an ampersand, a slash, and a colon.
CASES = [
    ("Elite Advertiser", EliteAdvertiserProposal, lambda: ProposalInput(
        business_name="Bob's Auto Group", contact_name="Dana",
        industry="Auto Dealer", city="Oxford",
    )),
    ("Host Media Kit", HostMediaKitProposal, lambda: HostInput(
        venue_name="Rafters Bar/Grill", contact_name="Dana",
        venue_category="Bar/Restaurant", city="Oxford",
    )),
    ("Multi-Brand Bundle", MultiBrandBundleProposal, lambda: BundleInput(
        owner_name="Jim Watts", businesses=[
            BundleBusiness(name="Watts Auto", industry="Auto", city="Oxford"),
            BundleBusiness(name="Watts Gym", industry="Fitness", city="Oxford"),
            BundleBusiness(name="Watts Cafe", industry="Restaurant", city="Oxford"),
        ],
    )),
    ("Venue Partner", VenuePartnerProposal, lambda: VenuePartnerInput(
        venue_name="Smith & Sons: Oxford", contact_name="Dana", city="Oxford",
    )),
    ("Category Exclusivity", CategoryExclusivityProposal, lambda: ExclusivityInput(
        business_name="Cannon Cleary McGraw", contact_name="Dana",
        industry="Real Estate", exclusive_category="Real Estate",
    )),
    ("Renewal / Upgrade", RenewalUpgradeProposal, lambda: RenewalInput(
        business_name="Iron & Oak", contact_name="Dana",
    )),
    ("NIL Partnership", NILPartnershipProposal, lambda: NILPartnerInput(
        business_name="Oxford Auto Group", contact_name="Dana",
        industry="Auto Dealer", city="Oxford",
    )),
    ("NIL Handout", NILHandout, lambda: NILPartnerInput(
        business_name="Oxford Auto Group", contact_name="Dana",
        industry="Auto Dealer", city="Oxford",
    )),
]

RESULTS = []


def record(name: str, ok: bool, detail: str = ""):
    RESULTS.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name:22} {detail}")


def fresh_docx(config):
    """A DocxService with the attributes the page normally stashes on it."""
    docx = DocxService(config)
    docx.client_logo_path = None
    docx.page2_photo_paths = []
    docx.page4_photo_paths = []
    docx.page4_captions = []
    return docx


def main():
    print("\n  MCTV Proposal Smoke Test (offline)\n")
    config = load_config()

    for name, generator_class, build_input in CASES:
        try:
            generator = generator_class(config, StubClaude(), fresh_docx(config))
            path, _email = generator.generate(build_input())
            if path and Path(path).exists():
                record(name, True, Path(path).name)
            else:
                record(name, False, "generate() returned no existing file")
        except Exception as exc:
            record(name, False, f"{type(exc).__name__}: {exc}")
            traceback.print_exc()

    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n  {len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        print("  Failed: " + ", ".join(failed) + "\n")
        return 1
    print("  All proposal types generate.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
