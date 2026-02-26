# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Multi-Brand Bundle proposal generator — scannable, visual v20 layout.

Generates a proposal for business owners with multiple brands (e.g.,
Good Earth / Hayden) who qualify for the Buy 2 Get 1 Free bundle deal.
Each brand gets its own spotlight section with a dedicated Claude call.
"""

import re

from generators.base_proposal import BaseProposal
from services.config_service import (
    get_team_member, get_all_tiers,
    get_tier_impressions, calculate_cpm, get_network_impressions,
    CPM_BENCHMARK_TEXT,
)


class MultiBrandBundleProposal(BaseProposal):
    """Generates a Multi-Brand Bundle proposal with per-brand spotlights."""

    # Intentional photo placement — no scattered behavior.
    PHOTO_DISTRIBUTION = {
        "opportunity":     {"source": "page2", "max": 4},
        "_market_coverage": {"source": "page4", "max": 6, "cols": 2,
                             "title": "Our Screens in Your Community"},
    }

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
            ("_competitive", "How MCTV Compares"),
            ("why_mctv", "Why MCTV"),
            ("_social_proof", "The MCTV Network"),
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
            self._build_bundle_value(doc, data, content)
        elif section_key == "_competitive":
            self._build_competitive(doc, data)
        elif section_key == "why_mctv":
            self._build_why_mctv(doc, content)
        elif section_key == "_social_proof":
            self._build_social_proof(doc)
        elif section_key == "getting_started":
            self._build_getting_started(doc, data, content)
        elif section_key == "_team":
            self.docx.add_team_section(doc)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    # -- THE OPPORTUNITY (paragraph + callout bullets + stats banner) --

    def _build_opportunity(self, doc, data, content):
        """The Opportunity section with network stats."""
        self.docx.add_section_header(doc, "The Opportunity")

        # Claude returns: 1 paragraph then 3 dash-bullet reasons
        # Split on the first dash to separate paragraph from bullets
        parts = re.split(r'\n\s*-\s*', content, maxsplit=1)
        if len(parts) == 2:
            self.docx.add_body_text(doc, parts[0].strip())
            bullets = re.split(r'\n\s*-\s*', parts[1])
            clean_bullets = "\n".join(f"- {b.strip()}" for b in bullets if b.strip())
            self.docx.add_callout_box(doc, clean_bullets)
        else:
            self.docx.add_body_text(doc, content)

        network = self.config["network"]
        self.docx.add_metrics_banner(doc, {
            network["total_screens"]: "Screens Across\nNorth Mississippi",
            network["monthly_impressions"]: "Monthly Impressions",
            f"{len(data.businesses)}": "Brands in\nYour Bundle",
            f"{network['plays_per_hour']}x/Hour": "Ad Plays\nPer Brand",
        })

    # -- BRAND SPOTLIGHTS (per-brand Claude calls with bullet rendering) --

    def _build_brand_spotlights(self, doc, data):
        """Generate a separate Claude-powered spotlight for each brand.

        This section is marked with underscore so the base generate() loop
        skips the Claude call, but we make individual Claude calls here
        for each business in the bundle.
        """
        self.docx.add_section_header(doc, "Your Brands", new_page=True)
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
                if spotlight_content:
                    self.docx.add_bullet_list(doc, spotlight_content)
                else:
                    self.docx.add_body_text(
                        doc,
                        f"{biz.name} is a {biz.industry or 'local'} business in "
                        f"{biz.city or 'your area'} that will benefit from MCTV "
                        f"network exposure."
                    )
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
                self.docx.add_callout_box(doc, " | ".join(details))

            # Thin gold divider between brands (not after the last one)
            if idx < len(data.businesses) - 1:
                self.docx.add_section_divider(doc)

    # -- BUNDLE PRICING (own page: table + contract terms) --

    def _build_bundle_pricing(self, doc, data):
        """Config-driven bundle pricing with Buy 2 Get 1 Free deal."""
        self.docx.add_section_header(doc, "Bundle Pricing", new_page=True)

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

            # Bundle CPM — total rate vs total network impressions shared across brands
            total_impressions = get_network_impressions(self.config)
            bundle_cpm = calculate_cpm(data.custom_monthly_rate, total_impressions)

            metrics = {
                f"${data.custom_monthly_rate:,.0f}/mo": "Total Bundle Rate",
                f"{num_businesses}": "Brands Included",
                f"${per_brand:,.0f}/mo": "Effective Rate\nPer Brand",
            }
            if bundle_cpm > 0:
                metrics[f"${bundle_cpm:.2f}"] = "Bundle CPM"
            else:
                metrics[bundle_deal] = "Bundle Deal\nApplied"

            self.docx.add_metrics_banner(doc, metrics)

            if bundle_cpm > 0:
                per_brand_impressions = total_impressions / num_businesses
                per_brand_cpm = calculate_cpm(per_brand, per_brand_impressions)
                self.docx.add_callout_box(
                    doc,
                    f"Bundle CPM: ${bundle_cpm:.2f} per 1,000 impressions across "
                    f"all {num_businesses} brands \u2014 effectively "
                    f"${per_brand_cpm:.2f} per brand.\n"
                    f"{CPM_BENCHMARK_TEXT}"
                )
        else:
            # Show standard tiers with bundle math
            self.docx.add_sub_header(doc, "STANDARD PRICING")
            tiers = get_all_tiers(self.config)
            self.docx.add_pricing_table(doc, tiers)

            # CPM comparison across tiers
            cpm_parts = []
            for tier in tiers:
                tier_imp = get_tier_impressions(self.config, tier["screens"])
                tier_cpm = calculate_cpm(tier["monthly_rate"], tier_imp)
                if tier_cpm > 0:
                    cpm_parts.append(f"{tier['name']}: ${tier_cpm:.2f}")
            if cpm_parts:
                self.docx.add_callout_box(
                    doc,
                    f"CPM Per Brand:  {'  |  '.join(cpm_parts)}\n"
                    f"With {bundle_deal}, your effective per-brand CPM drops even lower.\n"
                    f"{CPM_BENCHMARK_TEXT}"
                )

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

    # -- MARKET COVERAGE (compact: short text + inline venue callout) --

    def _build_market_coverage(self, doc, data):
        """Config-driven market coverage overview."""
        self.docx.add_section_header(doc, "Your Market Coverage", new_page=True)

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

        # Compact venue list as a callout box instead of a grid
        venue_text = (
            "Your ads play in: Restaurants & Bars  |  Barbershops & Salons  |  "
            "Medical & Dental  |  Gyms & Fitness  |  Auto & Service Shops  |  "
            "Retail & Boutiques  |  Professional Offices  |  Community Venues"
        )
        self.docx.add_callout_box(doc, venue_text)

    # -- BUNDLE VALUE (accent cards + metrics banner) --

    def _build_bundle_value(self, doc, data, content):
        """Claude-generated bundle value proposition with accent cards."""
        self.docx.add_section_header(doc, "The Bundle Advantage", new_page=True)

        pricing = self.config["pricing"]
        bundle_deal = pricing["bundle_deal"]
        num_businesses = len(data.businesses)
        network = self.config["network"]

        # Calculate monthly savings (lowest tier rate = the free brand)
        total_screens = int(network["total_screens"])
        if data.custom_monthly_rate and data.custom_monthly_rate > 0:
            per_brand = data.custom_monthly_rate / num_businesses if num_businesses else 0
            monthly_savings = f"${per_brand:,.0f}"
        else:
            tiers = get_all_tiers(self.config)
            lowest_rate = min(t["monthly_rate"] for t in tiers) if tiers else 0
            monthly_savings = f"${lowest_rate:,.0f}"

        self.docx.add_metrics_banner(doc, {
            bundle_deal: "Bundle Deal",
            f"{num_businesses}": "Brands in\nYour Bundle",
            f"{total_screens}": "Total Screens",
            f"{monthly_savings}/mo": "Monthly Savings\n(Free Brand)",
        })

        for line in content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            match = re.match(r'^-\s+(.+?)(?::|--)\s+(.+)$', line)
            if match:
                self.docx.add_accent_card(doc, match.group(1).strip(), match.group(2).strip())
            else:
                clean = line.lstrip('- ').strip()
                if clean:
                    self.docx.add_body_text(doc, clean)

    # -- COMPETITIVE COMPARISON (MCTV vs other media channels) --

    def _build_competitive(self, doc, data):
        self.docx.add_section_header(doc, "How MCTV Compares")

        self.docx.add_body_text(
            doc,
            "Local businesses have more advertising options than ever. "
            "Here is how MCTV stacks up against the alternatives."
        )

        total_screens = int(self.config["network"]["total_screens"])

        if data.custom_monthly_rate and data.custom_monthly_rate > 0:
            rate = data.custom_monthly_rate
            screens = total_screens
        else:
            tiers = get_all_tiers(self.config)
            mid = tiers[len(tiers) // 2] if tiers else tiers[0]
            rate = mid["monthly_rate"]
            screens = mid["screens"]

        impressions = get_tier_impressions(self.config, screens)
        self.docx.add_competitive_comparison(doc, rate, screens, impressions)
        self.docx.add_roi_projection(
            doc, rate, screens, impressions,
            business_name=data.owner_name + "'s businesses",
        )

    # -- WHY MCTV (accent cards) --

    def _build_why_mctv(self, doc, content):
        self.docx.add_section_header(doc, "Why MCTV", new_page=True)

        for line in content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            match = re.match(r'^-\s+(.+?)(?::|--)\s+(.+)$', line)
            if match:
                self.docx.add_accent_card(doc, match.group(1).strip(), match.group(2).strip())
            else:
                clean = line.lstrip('- ').strip()
                if clean:
                    self.docx.add_body_text(doc, clean)

    # -- SOCIAL PROOF (network stats + venue categories) --

    def _build_social_proof(self, doc):
        self.docx.add_section_header(doc, "The MCTV Network", new_page=True)

        proof = self.config.get("social_proof", {})
        headline = proof.get("headline", "")
        if headline:
            self.docx.add_body_text(doc, headline)

        self.docx.add_social_proof_section(doc)

        self.docx.add_sub_header(doc, "WHERE YOUR ADS PLAY")
        self.docx.add_venue_categories(doc)

    # -- GETTING STARTED (compact callout contact card) --

    def _build_getting_started(self, doc, data, content):
        """Getting Started section with contact card."""
        self.docx.add_section_header(doc, "Let's Get Started", new_page=True)
        self.docx.add_body_text(doc, content)

        rep = get_team_member(self.config, data.sales_rep)
        contact_text = f"{rep['name']}  |  {rep['email']}  |  {rep['phone']}  |  MCTV Elite Advertising  |  MCTVofMS.com"
        self.docx.add_callout_box(doc, contact_text)

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
