# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""One-page NIL / athlete partnership handout.

The leave-behind you hand across a table. It overrides generate() rather than
using the BaseProposal pipeline so it makes ZERO Claude API calls -- it renders
instantly and identically every time, which is what a printed handout needs.
"""

from datetime import datetime

from generators.base_proposal import BaseProposal
from generators import nil_sections as nil
from services.config_service import get_team_member


class NILHandout(BaseProposal):
    """Generates the 1-2 page athlete partnership handout."""

    @property
    def proposal_type_key(self) -> str:
        return "nil_partnership"

    def get_sections(self) -> list:
        # Everything is rendered directly in generate(); no Claude sections.
        return []

    def get_prompt_variables(self, data) -> dict:
        return {}

    def build_section(self, doc, section_key, data, content):
        pass

    def generate(self, input_data, progress_callback=None) -> tuple:
        """Build and save the handout.

        Returns (handout_path, None) to match the BaseProposal contract.
        """
        config = self.config
        collective = nil.collective_name(
            config, getattr(input_data, "collective_name", "")
        )
        structure = nil.normalize_structure(input_data.nil_structure)
        tax_language = nil.normalize_tax(input_data.tax_language)

        if progress_callback:
            progress_callback("Building handout", 1, 1)

        doc = self.docx.create_document()

        # ── Masthead ──
        self.docx.add_section_header(doc, f"Advertise With {collective}")
        nil.render_intro(self.docx, doc, config, collective)

        network = config["network"]
        self.docx.add_metrics_banner(doc, {
            network["total_screens"]: "Screens Across\nNorth Mississippi",
            network["monthly_impressions"]: "Monthly Impressions",
            f"{network['avg_dwell_time_minutes']}+ Min": "Avg. Dwell Time\nPer Visit",
            f"{network['plays_per_hour']}x/Hour": "Your Ad Plays\nEvery Hour",
        })

        # ── The mechanic ──
        nil.render_how_it_works(self.docx, doc, config, structure,
                                header="How It Works")

        # ── Athlete voices (consent-gated, capped for length) ──
        nil.render_athlete_voices(self.docx, doc, config, limit=2,
                                  header="In Their Words")

        # ── Packages (CPM table suppressed to keep this short) ──
        nil.render_packages(self.docx, doc, config, structure,
                            header="Packages", new_page=True, show_cpm=False)

        # ── Compliance + tax framing ──
        nil.render_compliance(self.docx, doc, config, tax_language,
                              header="How This Stays Clean")

        # ── Contact ──
        rep = get_team_member(config, input_data.sales_rep)
        self.docx.add_sub_header(doc, "TALK TO US")
        self.docx.add_callout_box(
            doc,
            f"{rep['name']}  |  {rep['email']}  |  {rep['phone']}  |  "
            f"MCTV Elite Advertising  |  MCTVofMS.com"
        )

        self.docx.add_footer(doc)

        safe_name = input_data.business_name.replace(" ", "_").replace("'", "")
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"MCTV_NIL_Handout_{safe_name}_{date_str}.docx"
        return self.docx.save_proposal(doc, filename), None
