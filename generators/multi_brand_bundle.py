"""Multi-Brand Bundle proposal generator.

Generates a proposal for business owners with multiple brands (e.g.,
Good Earth / Hayden) who qualify for the Buy 2 Get 1 Free bundle deal.
Each brand gets its own spotlight section with a dedicated Claude call.
"""

from generators.base_proposal import BaseProposal
from services.config_service import get_team_member, get_all_tiers
from services.docx_service import NAVY, GOLD, GRAY, Pt, WD_ALIGN_PARAGRAPH


class MultiBrandBundleProposal(BaseProposal):
    """Generates a Multi-Brand Bundle proposal with per-brand spotlights."""

    @property
    def proposal_type_key(self) -> str:
        return "multi_brand_bundle"

    def get_sections(self) -> list:
        return [
            ("opportunity", "The Opportunity"),
            ("_brand_spotlights", "Brand Spotlights"),
            ("_bundle_pricing", "Bundle Pricing"),
            ("_market_coverage", "Your Market Coverage"),
            ("bundle_value", "Bundle Value"),
            ("getting_started", "Let's Get Started"),
            ("_team", "Meet Your Team"),
        ]

    def get_prompt_variables(self, data) -> dict:
        rep = get_team_member(self.config, data.sales_rep)
        business_names = [b.name for b in data.businesses]
        business_list = ", ".join(business_names)
        return {
            "owner_name": data.owner_name,
            "business_list": business_list,
            "num_businesses": len(data.businesses),
            "sales_rep": rep["name"],
            "additional_notes": data.additional_notes or "No additional notes.",
        }

    def _build_cover(self, doc, input_data):
        """Build cover page listing all business names in the subtitle."""
        rep = get_team_member(self.config, input_data.sales_rep)
        business_names = [b.name for b in input_data.businesses]
        subtitle = " | ".join(business_names)
        first_name = input_data.businesses[0].name if input_data.businesses else "Bundle"
        self.docx.add_cover_page(
            doc,
            title="Multi-Brand\nBundle",
            subtitle=subtitle,
            prepared_for=f"{input_data.owner_name} \u2014 {first_name} Bundle",
            prepared_by=rep,
        )

    def build_section(self, doc, section_key, data, content):
        if section_key == "opportunity":
            self._build_opportunity(doc, data, content)
        elif section_key == "_brand_spotlights":
            self._build_brand_spotlights(doc, data)
        elif section_key == "_bundle_pricing":
            self._build_bundle_pricing(doc, data)
        elif section_key == "_market_coverage":
            self._build_market_coverage(doc, data)
        elif section_key == "bundle_value":
            self._build_bundle_value(doc, content)
        elif section_key == "getting_started":
            self._build_getting_started(doc, data, content)
        elif section_key == "_team":
            self.docx.add_team_section(doc)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_opportunity(self, doc, data, content):
        """The Opportunity section with network stats."""
        self.docx.add_section_header(doc, "The Opportunity")
        self.docx.add_body_text(doc, content)

        network = self.config["network"]
        self.docx.add_metrics_banner(doc, {
            network["total_screens"]: "Screens Across\nNorth Mississippi",
            network["monthly_impressions"]: "Monthly Impressions",
            f"{len(data.businesses)}": "Brands in\nYour Bundle",
            f"{network['plays_per_hour']}x/Hour": "Ad Plays\nPer Brand",
        })
        doc.add_page_break()

    def _build_brand_spotlights(self, doc, data):
        """Generate a separate Claude-powered spotlight for each brand.

        This section is marked with underscore so the base generate() loop
        skips the Claude call, but we make individual Claude calls here
        for each business in the bundle.
        """
        self.docx.add_section_header(doc, "Your Brands")
        variables = self.get_prompt_variables(data)

        for idx, biz in enumerate(data.businesses):
            self.docx.add_sub_header(doc, biz.name.upper())

            # Build per-brand variables for the brand_spotlight prompt
            brand_vars = {
                **variables,
                "brand_name": biz.name,
                "brand_industry": biz.industry or "local business",
                "brand_city": biz.city or "Oxford",
                "brand_notes": biz.description or "No additional notes.",
            }

            prompt = self.claude.build_section_prompt(
                self.proposal_type_key, "brand_spotlight", brand_vars
            )

            if prompt:
                spotlight_content = self.claude.generate_section(prompt)
                self.docx.add_body_text(doc, spotlight_content)
            else:
                self.docx.add_body_text(
                    doc,
                    f"{biz.name} is a {biz.industry} business in {biz.city} "
                    f"that will benefit from MCTV network exposure."
                )

            # Add contact details if provided
            details = []
            if biz.phone:
                details.append(biz.phone)
            if biz.website:
                details.append(biz.website)
            if details:
                p = doc.add_paragraph()
                run = p.add_run(" | ".join(details))
                run.font.size = Pt(10)
                run.font.color.rgb = GRAY
                run.font.italic = True

            # Add a small spacer between brands (no page break between them)
            if idx < len(data.businesses) - 1:
                doc.add_paragraph()

        doc.add_page_break()

    def _build_bundle_pricing(self, doc, data):
        """Config-driven bundle pricing with Buy 2 Get 1 Free deal."""
        self.docx.add_section_header(doc, "Bundle Pricing")

        pricing = self.config["pricing"]
        bundle_deal = pricing["bundle_deal"]
        bundle_desc = pricing["bundle_discount_description"]
        num_businesses = len(data.businesses)

        self.docx.add_body_text(
            doc,
            f"MCTV's Multi-Brand Bundle makes it simple and cost-effective "
            f"to advertise all {num_businesses} of your businesses on the same network. "
            f"With the {bundle_deal} deal, you get {bundle_desc}."
        )

        # Custom rate display if provided
        if data.custom_monthly_rate and data.custom_monthly_rate > 0:
            self.docx.add_sub_header(doc, "YOUR BUNDLE PACKAGE")

            # Calculate effective per-brand cost
            per_brand = data.custom_monthly_rate / num_businesses if num_businesses else 0

            self.docx.add_metrics_banner(doc, {
                f"${data.custom_monthly_rate:,.0f}/mo": "Total Bundle Rate",
                f"{num_businesses}": "Brands Included",
                f"${per_brand:,.0f}/mo": "Effective Rate\nPer Brand",
                bundle_deal: "Bundle Deal\nApplied",
            })
        else:
            # Show standard tiers with bundle math
            self.docx.add_sub_header(doc, "STANDARD PRICING")
            tiers = get_all_tiers(self.config)
            self.docx.add_pricing_table(doc, tiers)

            self.docx.add_sub_header(doc, f"BUNDLE SAVINGS: {bundle_deal.upper()}")
            self.docx.add_body_text(
                doc,
                f"Select any tier above for each brand. When you bundle "
                f"{num_businesses} businesses, your lowest-priced brand advertises "
                f"for free. One invoice. One partnership. Maximum visibility."
            )

        # Contract terms
        self.docx.add_sub_header(doc, "PARTNERSHIP TERMS")
        self.docx.add_contract_terms(doc, self.config)
        doc.add_page_break()

    def _build_market_coverage(self, doc, data):
        """Config-driven market coverage overview."""
        self.docx.add_section_header(doc, "Your Market Coverage")

        # Collect unique cities from all businesses
        cities = list({biz.city for biz in data.businesses if biz.city})
        city_str = ", ".join(cities) if cities else "North Mississippi"

        self.docx.add_body_text(
            doc,
            f"Your brands span {city_str}. MCTV's network ensures each business "
            f"reaches customers not just in its own neighborhood but across every "
            f"market in North Mississippi."
        )

        # Market details from config
        markets = self.config["markets"]
        for market_name, market_data in markets.items():
            screens = market_data["screens"]
            status = market_data["status"]
            description = market_data.get("description", "")

            if status == "active":
                self.docx.add_sub_header(doc, f"{market_name.upper()} \u2014 {screens} SCREENS")
                self.docx.add_body_text(doc, description)

        # Expanding markets
        expanding = [k for k, v in markets.items() if v["status"] == "expanding"]
        if expanding:
            self.docx.add_sub_header(doc, "EXPANDING MARKETS")
            self.docx.add_body_text(
                doc,
                f"MCTV is actively expanding into {' and '.join(expanding)}. "
                f"Bundle partners get first access to new markets as they launch."
            )

        self.docx.add_venue_categories(doc)
        doc.add_page_break()

    def _build_bundle_value(self, doc, content):
        """Claude-generated bundle value proposition."""
        self.docx.add_section_header(doc, "The Bundle Advantage")
        self.docx.add_body_text(doc, content)
        doc.add_page_break()

    def _build_getting_started(self, doc, data, content):
        """Getting Started section with contact card."""
        self.docx.add_section_header(doc, "Let's Get Started")
        self.docx.add_body_text(doc, content)

        rep = get_team_member(self.config, data.sales_rep)
        self.docx.add_sub_header(doc, "YOUR PARTNERSHIP CONTACT")

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(rep["name"])
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = NAVY

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"{rep['email']}\n{rep['phone']}")
        run.font.size = Pt(11)
        run.font.color.rgb = GRAY

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("MCTV Elite Advertising  |  MCTVofMS.com")
        run.font.size = Pt(10)
        run.font.color.rgb = GOLD

        doc.add_page_break()

    def generate(self, input_data, progress_callback=None) -> tuple:
        """Override generate to add the getting_started Claude call with
        proper variables, since the base class handles most of the flow
        but brand_spotlights need special treatment.

        We rely on the base class flow. The _brand_spotlights section is
        prefixed with underscore, so the base class skips the Claude call.
        The individual Claude calls happen inside _build_brand_spotlights.

        The getting_started section is NOT in prompts.json for multi_brand_bundle,
        so it falls through gracefully if the prompt is missing.
        """
        return super().generate(input_data, progress_callback)
