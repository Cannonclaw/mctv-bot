# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Generate sample proposal PDFs for the website Samples page.

Run from project root:
    python scripts/generate_samples.py

Requires ANTHROPIC_API_KEY in .env or environment.
Generates 4 industry sample PDFs → assets/samples/

IMPORTANT: Sample proposals exclude the pricing section.
Pricing is never made publicly available.
"""

import sys
import shutil
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import os
from models.proposal_data import ProposalInput
from generators.elite_advertiser import EliteAdvertiserProposal
from services.claude_service import ClaudeService
from services.config_service import load_config
from services.docx_service import DocxService


# ── SAMPLE-SAFE GENERATOR (no pricing) ───────────────────────────────────────

class SampleProposal(EliteAdvertiserProposal):
    """Elite Advertiser variant that excludes pricing for public samples."""

    def get_sections(self) -> list:
        """Same sections as Elite Advertiser but without pricing."""
        return [
            s for s in super().get_sections()
            if s[0] != "_pricing"
        ]


# ── SAMPLE BUSINESSES ────────────────────────────────────────────────────────

SAMPLES = [
    {
        "filename": "MCTV_Sample_Restaurant.pdf",
        "data": ProposalInput(
            business_name="Southern Table Kitchen & Bar",
            contact_name="James Mitchell",
            contact_email="james@southerntable.com",
            industry="Restaurant & Bar",
            city="Oxford",
            selected_markets=["Oxford"],
            sales_rep="Swayze Hollingsworth",
            additional_notes="Popular farm-to-table restaurant on the Square. Serves lunch and dinner. Looking to increase weekday traffic.",
        ),
    },
    {
        "filename": "MCTV_Sample_Salon.pdf",
        "data": ProposalInput(
            business_name="Blades & Fades Barbershop",
            contact_name="Marcus Williams",
            contact_email="marcus@bladesandfades.com",
            industry="Barbershop & Salon",
            city="Oxford",
            selected_markets=["Oxford", "Starkville"],
            sales_rep="Mary Michael Cannon",
            additional_notes="Two locations. Wants to build brand recognition across both college towns.",
        ),
    },
    {
        "filename": "MCTV_Sample_Gym.pdf",
        "data": ProposalInput(
            business_name="Iron & Oak Fitness",
            contact_name="Sarah Collins",
            contact_email="sarah@ironandoak.com",
            industry="Gym & Fitness",
            city="Starkville",
            selected_markets=["Starkville"],
            sales_rep="Swayze Hollingsworth",
            additional_notes="Boutique gym near MSU campus. Focus on student memberships and January sign-ups.",
        ),
    },
    {
        "filename": "MCTV_Sample_Auto.pdf",
        "data": ProposalInput(
            business_name="Precision Auto Care",
            contact_name="David Thompson",
            contact_email="david@precisionauto.com",
            industry="Auto Repair & Service",
            city="Tupelo",
            selected_markets=["Tupelo"],
            sales_rep="Mary Michael Cannon",
            additional_notes="Full-service auto repair. Wants to reach new customers moving to the area.",
        ),
    },
]

SAMPLES_DIR = ROOT / "assets" / "samples"


def generate_samples():
    """Generate all sample proposal PDFs (no pricing included)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    config = load_config()
    claude = ClaudeService(api_key=api_key)

    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    # Default screen photos for samples
    screens_dir = ROOT / "assets" / "screens"
    default_screens = []
    if screens_dir.exists():
        default_screens = sorted(
            str(p) for p in screens_dir.glob("*")
            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        )

    for i, sample in enumerate(SAMPLES, 1):
        print(f"\n[{i}/{len(SAMPLES)}] Generating: {sample['filename']}")
        print(f"    Business: {sample['data'].business_name}")
        print(f"    Industry: {sample['data'].industry}")
        print(f"    NOTE: Pricing section excluded from samples")

        docx = DocxService(config, color_scheme="original")

        # Add default screen photos
        if default_screens:
            docx.extra_photo_paths = list(default_screens)

        # Use SampleProposal (no pricing) instead of EliteAdvertiserProposal
        generator = SampleProposal(config, claude, docx)

        def progress(section_title, step, total):
            print(f"    [{step}/{total}] {section_title}")

        proposal_path, email_path = generator.generate(
            sample["data"], progress_callback=progress
        )

        # The generator outputs .docx — we need to convert to PDF
        # On Windows, try docx2pdf; on Docker/Linux, use LibreOffice
        docx_path = Path(proposal_path)

        try:
            from services.docx_service import DocxService as DS
            pdf_path = DS.convert_to_pdf(str(docx_path))
            if pdf_path and Path(pdf_path).exists():
                dest = SAMPLES_DIR / sample["filename"]
                shutil.copy2(pdf_path, dest)
                print(f"    PDF saved: {dest}")
            else:
                # Fallback: just copy the .docx and note it
                dest = SAMPLES_DIR / sample["filename"].replace(".pdf", ".docx")
                shutil.copy2(docx_path, dest)
                print(f"    PDF conversion failed. DOCX saved: {dest}")
                print(f"    Convert manually or run on Docker for LibreOffice.")
        except Exception as e:
            # Fallback: copy .docx
            dest = SAMPLES_DIR / sample["filename"].replace(".pdf", ".docx")
            shutil.copy2(docx_path, dest)
            print(f"    PDF conversion error: {e}")
            print(f"    DOCX saved: {dest}")

    print(f"\nDone! Samples saved to: {SAMPLES_DIR}")
    print("Pricing is NOT included in any sample PDFs.")


if __name__ == "__main__":
    generate_samples()
