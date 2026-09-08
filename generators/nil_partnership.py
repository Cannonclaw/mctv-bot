# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""NIL / athlete partnership proposal generator.

Sells local businesses on advertising that features a collective athlete.
Section copy comes from generators/nil_sections.py so this proposal, the
one-page handout, and the Elite Advertiser NIL page stay in sync.
"""

from generators.base_proposal import BaseProposal
from generators import nil_sections as nil
from services.config_service import get_team_member, get_pricing_tier


class NILPartnershipProposal(BaseProposal):
    """Generates the full athlete partnership proposal."""

    PHOTO_DISTRIBUTION = {
        "opportunity": {"source": "page2", "max": 4},
        "_receipts":   {"source": "page4", "max": 6, "cols": 3,
                        "title": "Our Screens in Your Community"},
    }

    @property
    def proposal_type_key(self) -> str:
        return "nil_partnership"

    def get_sections(self) -> list:
        return [
            ("opportunity", "The Opportunity"),
            ("_how_it_works", "How It Works"),
            ("_why_different", "Why This One Is Different"),
            ("_athlete_voices", "In Their Words"),
            ("_packages", "Packages"),
            ("_receipts", "The Receipts"),
            ("_compliance", "How This Stays Clean"),
            ("getting_started", "Getting Started"),
            ("_team", "Meet Your Team"),
        ]

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _collective(self, data) -> str:
        return nil.collective_name(self.config, getattr(data, "collective_name", ""))

    def _media_basis(self, data) -> tuple:
        """(monthly_rate, screens) to drive the CPM / ROI math.

        For a bundled package the athlete fee is baked into one price, so the
        package rate is what the client actually pays. For the add-on and
        contribution structures the media buy is priced off the standard rate
        card, so that tier is the honest basis for a media comparison.
        """
        structure = nil.normalize_structure(data.nil_structure)
        if structure == "bundled":
            packages = nil.nil_config(self.config).get("packages", {}).get("bundled", [])
            if packages:
                idx = min(max(data.nil_tier, 0), len(packages) - 1)
                pkg = packages[idx]
                return float(pkg.get("monthly_rate", 0)), int(pkg.get("screens", 0))
            return 0.0, 0

        tier = get_pricing_tier(self.config, data.base_tier)
        return float(tier["monthly_rate"]), int(tier["screens"])

    # ── Pipeline hooks ───────────────────────────────────────────────────────

    def _build_cover(self, doc, input_data):
        rep = get_team_member(self.config, input_data.sales_rep)
        self.docx.preparer_name = rep["name"]
        self.docx.add_cover_page(
            doc,
            title="ATHLETE\nPARTNERSHIP",
            subtitle=input_data.business_name,
            prepared_for=input_data.contact_name,
            prepared_by=rep,
            client_logo_path=getattr(self.docx, "client_logo_path", None),
        )

    def get_prompt_variables(self, data) -> dict:
        rep = get_team_member(self.config, data.sales_rep)
        market_details = []
        for market_name in data.selected_markets:
            screens = self.config["markets"].get(market_name, {}).get("screens", 0)
            market_details.append(f"{market_name} ({screens} screens)")

        return {
            "business_name": data.business_name,
            "contact_name": data.contact_name,
            "contact_email": data.contact_email,
            "industry": data.industry or "local business",
            "city": data.city,
            "selected_markets": ", ".join(market_details),
            "collective_name": self._collective(data),
            "athlete_count": data.athlete_count,
            "sales_rep": rep["name"],
            "additional_notes": data.additional_notes or "No additional notes.",
        }

    def build_section(self, doc, section_key, data, content):
        if section_key == "opportunity":
            self._build_opportunity(doc, data, content)
        elif section_key == "_how_it_works":
            nil.render_how_it_works(doc=doc, docx=self.docx, config=self.config,
                                    structure=data.nil_structure,
                                    header="How It Works", new_page=True)
        elif section_key == "_why_different":
            self.docx.add_section_header(doc, "Why This One Is Different")
            nil.render_value_props(self.docx, doc, self.config)
        elif section_key == "_athlete_voices":
            nil.render_athlete_voices(self.docx, doc, self.config, new_page=True)
        elif section_key == "_packages":
            nil.render_packages(self.docx, doc, self.config, data.nil_structure,
                                header="Packages", new_page=True)
            self._build_exclusivity_note(doc, data)
            self.docx.add_sub_header(doc, "PARTNERSHIP TERMS")
            self.docx.add_contract_terms(doc, self.config)
        elif section_key == "_receipts":
            rate, screens = self._media_basis(data)
            nil.render_receipts(self.docx, doc, self.config, rate, screens,
                                business_name=data.business_name,
                                header="The Receipts", new_page=True)
        elif section_key == "_compliance":
            nil.render_compliance(self.docx, doc, self.config, data.tax_language,
                                  header="How This Stays Clean", new_page=True)
        elif section_key == "getting_started":
            self._build_getting_started(doc, data, content)
        elif section_key == "_team":
            self.docx.add_team_section(doc)

    # ── THE OPPORTUNITY ──────────────────────────────────────────────────────

    def _build_opportunity(self, doc, data, content):
        self.docx.add_section_header(doc, "The Opportunity")

        # Claude returns one paragraph then dash-bullet reasons.
        import re
        parts = re.split(r'\n\s*-\s*', content, maxsplit=1)
        if len(parts) == 2:
            self.docx.add_body_text(doc, parts[0].strip())
            for bullet in re.split(r'\n\s*-\s*', parts[1]):
                bullet = bullet.strip()
                if not bullet:
                    continue
                match = re.match(r'^(.+?)(?::|--)\s+(.+)$', bullet)
                if match:
                    self.docx.add_selling_point(doc, match.group(1).strip(),
                                                match.group(2).strip())
                else:
                    self.docx.add_selling_point(doc, bullet, "")
        elif content:
            self.docx.add_body_text(doc, content)

        nil.render_intro(self.docx, doc, self.config, self._collective(data))

        # "headline" mode leads with the tax framing, so it runs here on page
        # one as well as in the compliance section.
        if nil.normalize_tax(data.tax_language) == "headline":
            nil.render_tax_block(self.docx, doc, self.config, "headline",
                                 with_disclaimer=False)

    # ── EXCLUSIVITY UPSELL ───────────────────────────────────────────────────

    def _build_exclusivity_note(self, doc, data):
        """Category lockout note, when the deal includes it."""
        if not data.category_exclusive:
            return
        category = data.exclusive_category or data.industry or "your category"
        self.docx.add_sub_header(doc, "CATEGORY EXCLUSIVITY")
        self.docx.add_callout_box(
            doc,
            f"{data.business_name} is the only {category} business in the athlete "
            f"rotation across {', '.join(data.selected_markets)}. Your competitor "
            f"cannot buy the same athlete on the same screens for the length of "
            f"this partnership."
        )

    # ── GETTING STARTED ──────────────────────────────────────────────────────

    def _build_getting_started(self, doc, data, content):
        self.docx.add_section_header(doc, "Getting Started", new_page=True)
        if content:
            self.docx.add_body_text(doc, content)

        rep = get_team_member(self.config, data.sales_rep)
        self.docx.add_sub_header(doc, "YOUR PARTNERSHIP CONTACT")
        self.docx.add_callout_box(
            doc,
            f"{rep['name']}  |  {rep['email']}  |  {rep['phone']}  |  "
            f"MCTV Elite Advertising  |  MCTVofMS.com"
        )
