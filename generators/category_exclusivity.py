# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Category Exclusivity proposal generator — scannable, visual v20 layout."""

from generators.base_proposal import BaseProposal
from services.config_service import (
    get_team_member, get_pricing_tier, get_all_tiers,
    get_tier_impressions, calculate_cpm, CPM_BENCHMARK_TEXT,
    get_hours_per_day, get_days_per_month,
)


class CategoryExclusivityProposal(BaseProposal):
    """Generates a Category Exclusivity proposal with competitor lockout."""

    # Intentional photo placement — no scattered behavior.
    PHOTO_DISTRIBUTION = {
        "opportunity":        {"source": "page2", "max": 4},
        "_market_coverage":   {"source": "page4", "max": 6, "cols": 2,
                               "title": "Our Screens in Your Community"},
    }

    @property
    def proposal_type_key(self) -> str:
        return "category_exclusivity"

    def get_sections(self) -> list:
        return [
            ("opportunity", "The Opportunity"),
            ("exclusivity_value", "The Value of Exclusivity"),
            ("_market_coverage", "Your Exclusive Markets"),
            ("_pricing", "Exclusivity Pricing"),
            ("_competitive", "How MCTV Compares"),
            ("_why_mctv", "Why MCTV"),
            ("_social_proof", "The MCTV Network"),
            ("getting_started", "Let's Get Started"),
            ("_team", "Meet Your Team"),
        ]

    def get_prompt_variables(self, data) -> dict:
        rep = get_team_member(self.config, data.sales_rep)

        # Build market details string
        market_details = []
        for market_name in data.selected_markets:
            market = self.config["markets"].get(market_name, {})
            screens = market.get("screens", 0)
            market_details.append(f"{market_name} ({screens} screens)")
        selected_markets = ", ".join(market_details)

        return {
            "business_name": data.business_name,
            "contact_name": data.contact_name,
            "industry": data.industry,
            "exclusive_category": data.exclusive_category,
            "city": data.city,
            "selected_markets": selected_markets,
            "sales_rep": rep["name"],
            "additional_notes": data.additional_notes or "No additional notes.",
        }

    def _build_cover(self, doc, input_data):
        """Build cover page for category exclusivity proposal."""
        rep = get_team_member(self.config, input_data.sales_rep)
        self.docx.add_cover_page(
            doc,
            title="Category\nExclusivity",
            subtitle=f"EXCLUSIVE {input_data.exclusive_category.upper()} PARTNERSHIP",
            prepared_for=f"{input_data.contact_name} \u2014 {input_data.business_name}",
            prepared_by=rep,
        )

    def build_section(self, doc, section_key, data, content):
        if section_key == "opportunity":
            self._build_opportunity(doc, data, content)
        elif section_key == "exclusivity_value":
            self._build_exclusivity_value(doc, content)
        elif section_key == "_market_coverage":
            self._build_market_coverage(doc, data)
        elif section_key == "_pricing":
            self._build_pricing(doc, data)
        elif section_key == "_competitive":
            self._build_competitive(doc, data)
        elif section_key == "_why_mctv":
            self._build_why_mctv(doc, data)
        elif section_key == "_social_proof":
            self._build_social_proof(doc)
        elif section_key == "getting_started":
            self._build_getting_started(doc, data, content)
        elif section_key == "_team":
            self.docx.add_team_section(doc)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_opportunity(self, doc, data, content):
        """The Opportunity section with exclusivity-focused metrics."""
        self.docx.add_section_header(doc, "The Opportunity")

        import re
        parts = re.split(r'\n\s*-\s*', content, maxsplit=1)
        if len(parts) == 2:
            self.docx.add_body_text(doc, parts[0].strip())
            bullets = re.split(r'\n\s*-\s*', parts[1])
            for bullet in bullets:
                bullet = bullet.strip()
                if not bullet:
                    continue
                match = re.match(r'^(.+?)(?::|--)\s+(.+)$', bullet)
                if match:
                    self.docx.add_selling_point(doc, match.group(1).strip(), match.group(2).strip())
                else:
                    self.docx.add_selling_point(doc, bullet, "")
        else:
            self.docx.add_body_text(doc, content)

        network = self.config["network"]
        self.docx.add_metrics_banner(doc, {
            network["total_screens"]: "Screens\nExclusively Yours",
            network["monthly_impressions"]: "Monthly\nImpressions",
            f"{network['avg_dwell_time_minutes']}+ Min": "Avg. Dwell\nTime",
            "100%": "Category\nOwnership",
        })

    def _build_exclusivity_value(self, doc, content):
        """Claude-generated section on the strategic value of exclusivity."""
        self.docx.add_section_header(doc, "The Value of Exclusivity", new_page=True)

        import re
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            bullet_match = re.match(r'^-\s+(.+?)(?::|--)\s+(.+)$', line)
            if bullet_match:
                title = bullet_match.group(1).strip()
                desc = bullet_match.group(2).strip()
                self.docx.add_accent_card(doc, title, desc)
            else:
                clean = line.lstrip('- ').strip()
                if clean:
                    self.docx.add_body_text(doc, clean)

    def _build_market_coverage(self, doc, data):
        """Config-driven display of which markets the client owns exclusively."""
        self.docx.add_section_header(doc, "Your Exclusive Markets", new_page=True)

        self.docx.add_body_text(
            doc,
            f"With category exclusivity, {data.business_name} is the only "
            f"{data.exclusive_category} business on MCTV screens in the following "
            f"markets. No competitor can purchase advertising in your category "
            f"for the duration of your partnership."
        )

        # Show each selected market with screen count and description
        markets = self.config["markets"]
        total_screens = 0
        for market_name in data.selected_markets:
            market_data = markets.get(market_name, {})
            screens = market_data.get("screens", 0)
            description = market_data.get("description", "")
            total_screens += screens

            self.docx.add_sub_header(doc, f"{market_name.upper()} \u2014 {screens} SCREENS (EXCLUSIVE)")
            self.docx.add_body_text(doc, description)

        # Summary
        self.docx.add_sub_header(doc, "TOTAL EXCLUSIVE COVERAGE")
        self.docx.add_body_text(
            doc,
            f"{data.business_name} owns the {data.exclusive_category} category "
            f"across {total_screens} screens in "
            f"{', '.join(data.selected_markets)}. Every impression in your "
            f"category belongs to you \u2014 zero competition."
        )

        # Show expanding markets as growth opportunity
        expanding = [k for k, v in markets.items()
                     if v["status"] == "expanding" and k not in data.selected_markets]
        if expanding:
            self.docx.add_sub_header(doc, "EXPANSION OPPORTUNITY")
            self.docx.add_body_text(
                doc,
                f"MCTV is expanding into {' and '.join(expanding)}. As an "
                f"exclusivity partner, {data.business_name} gets first right of "
                f"refusal to extend your {data.exclusive_category} exclusivity "
                f"into new markets before they open to other advertisers."
            )

        # Compact venue callout box
        venue_text = (
            "Your ads play in: Restaurants & Bars  |  Barbershops & Salons  |  "
            "Medical & Dental  |  Gyms & Fitness  |  Auto & Service Shops  |  "
            "Retail & Boutiques  |  Professional Offices  |  Community Venues"
        )
        self.docx.add_callout_box(doc, venue_text)

    def _build_pricing(self, doc, data):
        """Config-driven pricing section with exclusivity premium."""
        self.docx.add_section_header(doc, "Exclusivity Pricing", new_page=True)

        pricing = self.config["pricing"]
        exclusivity_desc = pricing.get(
            "exclusivity_premium_description",
            "Premium pricing for category exclusivity"
        )

        self.docx.add_body_text(
            doc,
            f"Category exclusivity is a premium offering. By locking out all "
            f"{data.exclusive_category} competitors from the MCTV network, "
            f"{data.business_name} gains a competitive advantage that no amount "
            f"of standard advertising can replicate."
        )

        # Show custom rate if provided
        if data.monthly_rate and data.monthly_rate > 0:
            self.docx.add_sub_header(doc, "YOUR EXCLUSIVITY PACKAGE")

            # Count total exclusive screens
            total_screens = 0
            for market_name in data.selected_markets:
                market = self.config["markets"].get(market_name, {})
                total_screens += market.get("screens", 0)

            cost_per_screen = data.monthly_rate / total_screens if total_screens else 0
            plays_per_hour = self.config["network"]["plays_per_hour"]
            hours_per_day = get_hours_per_day(self.config)
            days_per_month = get_days_per_month(self.config)
            monthly_plays = plays_per_hour * hours_per_day * days_per_month * total_screens

            # CPM for exclusivity package
            tier_impressions = get_tier_impressions(self.config, total_screens)
            cpm = calculate_cpm(data.monthly_rate, tier_impressions)

            metrics = {
                f"${data.monthly_rate:,.0f}/mo": "Exclusivity Rate",
                f"{total_screens}": "Exclusive Screens",
                f"${cost_per_screen:,.2f}": "Cost Per Screen",
            }
            if cpm > 0:
                metrics[f"${cpm:.2f}"] = "CPM"
            else:
                metrics[f"{monthly_plays:,}"] = "Monthly\nAd Plays"

            self.docx.add_metrics_banner(doc, metrics)

            self.docx.add_body_text(
                doc,
                f"{data.business_name} locks in {data.exclusive_category} "
                f"exclusivity across {', '.join(data.selected_markets)} for "
                f"${data.monthly_rate:,.0f} per month. This rate includes your "
                f"ad playing {plays_per_hour}x per hour on every screen in your "
                f"exclusive markets."
            )

            if cpm > 0:
                self.docx.add_callout_box(
                    doc,
                    f"Your Exclusivity CPM: ${cpm:.2f} per 1,000 impressions \u2014 "
                    f"and zero competitor ads in your category.\n"
                    f"{CPM_BENCHMARK_TEXT}"
                )
        else:
            # Show base tier as starting point
            self.docx.add_sub_header(doc, "BASE TIER + EXCLUSIVITY PREMIUM")
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
                    f"Base CPM:  {'  |  '.join(cpm_parts)}\n"
                    f"With exclusivity, you also lock out every competitor \u2014 "
                    f"zero shared impressions.\n"
                    f"{CPM_BENCHMARK_TEXT}"
                )

            self.docx.add_body_text(
                doc,
                f"{exclusivity_desc}. Your partnership manager will work with you "
                f"to determine the right exclusivity rate based on your selected "
                f"markets and coverage goals."
            )

        # Contract terms
        self.docx.add_sub_header(doc, "PARTNERSHIP TERMS")
        self.docx.add_contract_terms(doc, self.config)

    def _build_why_mctv(self, doc, data):
        """Config-driven reasons why MCTV is the right platform."""
        self.docx.add_section_header(doc, "Why MCTV", new_page=True)

        network = self.config["network"]

        reasons = [
            ("Competitor Lockout",
             f"No other {data.exclusive_category} business can advertise on MCTV. "
             f"Period. Every screen impression in your category goes to "
             f"{data.business_name} \u2014 and only {data.business_name}."),

            ("Captive Audience",
             f"MCTV screens are in venues where customers spend an average of "
             f"{network['avg_dwell_time_minutes']}+ minutes. Your ad plays "
             f"{network['plays_per_hour']}x per hour and cannot be skipped, "
             f"blocked, or scrolled past."),

            ("Hyper-Local Precision",
             f"Your ads play in the exact neighborhoods where your customers live, "
             f"eat, work out, and get their hair cut. This is not a billboard on "
             f"the highway \u2014 it is inside the businesses they visit every week."),

            ("First-Mover Advantage",
             f"Category exclusivity is limited by definition. Once {data.business_name} "
             f"locks in the {data.exclusive_category} category, it is off the table "
             f"for every competitor. Early movers win."),

            ("Growing Network",
             f"MCTV currently operates {network['total_screens']} screens and is "
             f"actively expanding. Your exclusivity grows with the network \u2014 more "
             f"screens, more venues, more impressions, same locked-in rate."),

            ("Proven ROI",
             f"With {network['monthly_impressions']} monthly impressions across "
             f"the network, MCTV delivers consistent, measurable exposure that "
             f"outperforms traditional media at a fraction of the cost."),
        ]

        for title, description in reasons:
            self.docx.add_selling_point(doc, title, description)

    def _build_competitive(self, doc, data):
        self.docx.add_section_header(doc, "How MCTV Compares")

        self.docx.add_body_text(
            doc,
            "Local businesses have more advertising options than ever. "
            "Here is how MCTV stacks up against the alternatives."
        )

        total_screens = 0
        for market_name in data.selected_markets:
            market = self.config["markets"].get(market_name, {})
            total_screens += market.get("screens", 0)

        if data.monthly_rate and data.monthly_rate > 0:
            rate = data.monthly_rate
            screens = total_screens
        else:
            tier = get_pricing_tier(self.config, data.base_tier)
            rate = tier["monthly_rate"]
            screens = tier["screens"]

        impressions = get_tier_impressions(self.config, screens)
        self.docx.add_competitive_comparison(doc, rate, screens, impressions)
        self.docx.add_roi_projection(doc, rate, screens, impressions, business_name=data.business_name)

    def _build_social_proof(self, doc):
        self.docx.add_section_header(doc, "The MCTV Network", new_page=True)

        proof = self.config.get("social_proof", {})
        headline = proof.get("headline", "")
        if headline:
            self.docx.add_body_text(doc, headline)

        self.docx.add_social_proof_section(doc)

        self.docx.add_sub_header(doc, "WHERE YOUR ADS PLAY")
        self.docx.add_venue_categories(doc)

    def _build_getting_started(self, doc, data, content):
        """Getting Started section with compact contact callout."""
        self.docx.add_section_header(doc, "Let's Get Started", new_page=True)

        if content:
            self.docx.add_body_text(doc, content)
        else:
            self.docx.add_body_text(
                doc,
                f"Category exclusivity opportunities are limited and subject to "
                f"availability. Once {data.business_name} locks in the "
                f"{data.exclusive_category} category, no competitor can take it. "
                f"We recommend securing your position as soon as possible."
            )
            self.docx.add_body_text(
                doc,
                "The next step is a quick 15-minute call to finalize your market "
                "selections and review the partnership agreement. From there, we "
                "design your ad creative and get you live on the network."
            )

        rep = get_team_member(self.config, data.sales_rep)
        contact_text = f"{rep['name']}  |  {rep['email']}  |  {rep['phone']}  |  MCTV Elite Advertising  |  MCTVofMS.com"
        self.docx.add_callout_box(doc, contact_text)
