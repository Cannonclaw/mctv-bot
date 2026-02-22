"""Abstract base class for all proposal generators."""

from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from services.claude_service import ClaudeService
from services.docx_service import DocxService
from services.config_service import get_team_member


# Sections after which to insert uploaded photos
VENUE_PHOTO_SECTIONS = {"market_coverage", "_market_coverage"}
AD_EXAMPLE_SECTIONS = {"whats_included", "_whats_included"}
EXTRA_PHOTO_SECTIONS = {"_team"}  # extra photos go right before team


class BaseProposal(ABC):
    """Base class that all proposal generators inherit from."""

    def __init__(self, config: dict, claude: ClaudeService, docx: DocxService):
        self.config = config
        self.claude = claude
        self.docx = docx

    @abstractmethod
    def get_sections(self) -> list:
        """Return ordered list of (section_key, section_title) tuples."""
        pass

    @abstractmethod
    def build_section(self, doc, section_key: str, input_data, content: str):
        """Add a formatted section to the Word document."""
        pass

    @abstractmethod
    def get_prompt_variables(self, input_data) -> dict:
        """Extract template variables from the input data."""
        pass

    @property
    @abstractmethod
    def proposal_type_key(self) -> str:
        """The key in prompts.json for this proposal type."""
        pass

    def generate(self, input_data, progress_callback=None) -> tuple:
        """Full generation pipeline.

        Returns (proposal_path, email_path) tuple.
        """
        doc = self.docx.create_document()
        variables = self.get_prompt_variables(input_data)
        sections = self.get_sections()
        total = len(sections)

        # Get uploaded photos from the docx service
        venue_photos = getattr(self.docx, "venue_photo_paths", [])
        ad_examples = getattr(self.docx, "ad_example_paths", [])
        extra_photos = getattr(self.docx, "extra_photo_paths", [])

        # Build cover page first
        self._build_cover(doc, input_data)

        # Generate each section
        for idx, (section_key, section_title) in enumerate(sections):
            if progress_callback:
                progress_callback(section_title, idx + 1, total)

            # Insert extra photos BEFORE team section
            if section_key in EXTRA_PHOTO_SECTIONS and extra_photos:
                self.docx.add_photos_grid(doc, extra_photos, title="Gallery")

            # Some sections don't need Claude (pricing, team, etc.)
            if section_key.startswith("_"):
                self.build_section(doc, section_key, input_data, "")
            else:
                # Build prompt and call Claude
                prompt = self.claude.build_section_prompt(
                    self.proposal_type_key, section_key, variables
                )

                if prompt:
                    content = self.claude.generate_section(prompt)
                else:
                    content = ""

                self.build_section(doc, section_key, input_data, content)

            # Insert venue photos AFTER market coverage section
            if section_key in VENUE_PHOTO_SECTIONS and venue_photos:
                self.docx.add_photos_grid(doc, venue_photos, title="Our Screens in Action")

            # Insert ad examples AFTER whats_included section
            if section_key in AD_EXAMPLE_SECTIONS and ad_examples:
                self.docx.add_photos_grid(doc, ad_examples, title="Ad Creative Examples")

        # Add footer
        self.docx.add_footer(doc)

        # Save proposal
        safe_name = input_data.business_name.replace(" ", "_").replace("'", "")
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"MCTV_Proposal_{safe_name}_{date_str}.docx"
        proposal_path = self.docx.save_proposal(doc, filename)

        # Generate cover email
        email_path = None
        if self.config["proposal_settings"]["include_cover_email"]:
            email_prompt = self.claude.build_section_prompt(
                self.proposal_type_key, "cover_email", variables
            )
            if email_prompt:
                email_content = self.claude.generate_email(email_prompt)
                email_filename = f"MCTV_Email_{safe_name}_{date_str}.txt"
                email_path = self.docx.save_email(email_content, email_filename)

        return proposal_path, email_path

    def _build_cover(self, doc, input_data):
        """Build the cover page from input data."""
        rep = get_team_member(self.config, input_data.sales_rep)
        # Get client logo path if set on the docx service
        client_logo = getattr(self.docx, "client_logo_path", None)
        self.docx.add_cover_page(
            doc,
            title="Advertising\nPartnership",
            subtitle="PROPOSAL",
            prepared_for=f"{input_data.contact_name} \u2014 {input_data.business_name}",
            prepared_by=rep,
            client_logo_path=client_logo,
        )
