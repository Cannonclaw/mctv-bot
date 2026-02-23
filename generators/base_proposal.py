"""Abstract base class for all proposal generators."""

from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from services.claude_service import ClaudeService
from services.docx_service import DocxService
from services.config_service import get_team_member


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

        # Get intentionally-placed photos from the docx service.
        # page2 = The Opportunity (max 2 hero photos)
        # page4 = Market Coverage (max 6 grid photos)
        page2_photos = getattr(self.docx, "page2_photo_paths", [])
        page4_photos = getattr(self.docx, "page4_photo_paths", [])

        # Build photo pools keyed by source name (matches PHOTO_DISTRIBUTION)
        photo_pools = {
            "page2": list(page2_photos),
            "page4": list(page4_photos),
            # Legacy "extra" source maps to page2 + page4 combined
            "extra": list(page2_photos) + list(page4_photos),
        }

        # Check if this generator defines per-section photo distribution
        photo_dist = getattr(self, 'PHOTO_DISTRIBUTION', None)

        # Build cover page first
        self._build_cover(doc, input_data)

        # Generate each section
        for idx, (section_key, section_title) in enumerate(sections):
            if progress_callback:
                progress_callback(section_title, idx + 1, total)

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

            # Intentional photo placement — each photo has a specific page.
            # No "scattered throughout" behavior. Every photo is explicitly
            # assigned to a section via PHOTO_DISTRIBUTION.
            if photo_dist and section_key in photo_dist:
                slot = photo_dist[section_key]
                source = slot.get("source", "extra")
                pool = photo_pools.get(source, [])
                if pool:
                    count = min(slot.get("max", 2), len(pool))
                    batch = pool[:count]
                    del pool[:count]
                    title = slot.get("title")
                    grid_cols = slot.get("cols", 2)
                    if title:
                        self.docx.add_photos_grid(doc, batch, title=title,
                                                  cols=grid_cols)
                    else:
                        self.docx.add_inline_photos(doc, batch, cols=grid_cols)

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
        # Store the preparer name on docx service so add_team_section()
        # can reorder the team array to show the preparer first.
        self.docx.preparer_name = rep["name"]
        # Get client logo path if set on the docx service
        client_logo = getattr(self.docx, "client_logo_path", None)
        self.docx.add_cover_page(
            doc,
            title="ADVERTISING PARTNERSHIP\nPROPOSAL",
            subtitle=input_data.business_name,
            prepared_for=input_data.contact_name,
            prepared_by=rep,
            client_logo_path=client_logo,
        )
