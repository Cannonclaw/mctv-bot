"""Category Exclusivity proposal generator.

Generates a proposal for advertisers who want to lock out all competitors
from their industry category across the MCTV network (e.g., Cannon Cleary
McGraw owning the real estate category exclusively).
"""

from generators.base_proposal import BaseProposal
from services.config_service import get_team_member, get_pricing_tier, get_all_tiers
from services.docx_service import NAVY, GOLD, GRAY, Pt, WD_ALIGN_PARAGRAPH


class CategoryExclusivityProposal(BaseProposal):
    """Generates a Category Exclusivity proposal with competitor lockout."""

    @property
    def proposal_type_key(self) -> str:
        return "category_exclusivity"

    def get_sections(self) -> list:
        return [
            ("opportunity", "The Opportunity"),
            ("exclusivity_value", "The Value of Exclusivity"),
            ("_market_coverage", "Your Exclusive Markets"),
            ("_pricing", "Exclusivity Pricing"),
            ("_why_mctv", "Why MCTV"),
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
        elif section_key == "_why_mctv":
            self._build_why_mctv(doc, data)
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
        self.docx.add_body_text(doc, content)

        # Count total screens in selected markets
        total_exclusive_screens = 0
        for market_name in data.selected_markets:
            market = self.config["markets"].get(market_name, {})
            total_exclusive_screens += market.get("screens", 0)

        network = self.config["network"]
        self.docx.add_metrics_banner(doc, {
            f"{total_exclusive_screens}": "Screens Where\nYou're Exclusive",
            "0": f"Competing\n{data.exclusive_category} Ads",
            network["monthly_impressions"]: "Network-Wide\nMonthly Impressions",
            f"{network['plays_per_hour']}x/Hour": "Your Ad Plays\nEvery Day",
        })
        doc.add_page_break()

    def _build_exclusivity_value(self, doc, content):
        """Claude-generated section on the strategic value of exclusivity."""
        self.docx.add_section_header(doc, "The Value of Exclusivity")
        self.docx.add_body_text(doc, content)
        doc.add_page_break()

    def _build_market_coverage(self, doc, data):
        """Config-driven display of which markets the client owns exclusively."""
        self.docx.add_section_header(doc, "Your Exclusive Markets")

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

        doc.add_page_break()

    def _build_pricing(self, doc, data):
        """Config-driven pricing section with exclusivity premium."""
        self.docx.add_section_header(doc, "Exclusivity Pricing")

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
            hours_per_day = 12
            days_per_month = 30
            monthly_plays = plays_per_hour * hours_per_day * days_per_month * total_screens

            self.docx.add_metrics_banner(doc, {
                f"${data.monthly_rate:,.0f}/mo": "Exclusivity Rate",
                f"{total_screens}": "Exclusive Screens",
                f"${cost_per_screen:,.2f}": "Cost Per Screen",
                f"{monthly_plays:,}": "Monthly\nAd Plays",
            })

            self.docx.add_body_text(
                doc,
                f"{data.business_name} locks in {data.exclusive_category} "
                f"exclusivity across {', '.join(data.selected_markets)} for "
                f"${data.monthly_rate:,.0f} per month. This rate includes your "
                f"ad playing {plays_per_hour}x per hour on every screen in your "
                f"exclusive markets."
            )
        else:
            # Show base tier as starting point
            self.docx.add_sub_header(doc, "BASE TIER + EXCLUSIVITY PREMIUM")
            tiers = get_all_tiers(self.config)
            self.docx.add_pricing_table(doc, tiers)

            self.docx.add_body_text(
                doc,
                f"{exclusivity_desc}. Your partnership manager will work with you "
                f"to determine the right exclusivity rate based on your selected "
                f"markets and coverage goals."
            )

        # Contract terms
        self.docx.add_sub_header(doc, "PARTNERSHIP TERMS")
        self.docx.add_contract_terms(doc, self.config)
        doc.add_page_break()

    def _build_why_mctv(self, doc, data):
        """Config-driven reasons why MCTV is the right platform."""
        self.docx.add_section_header(doc, "Why MCTV")

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
            self.docx.add_bullet_point(doc, title, description)

        doc.add_page_break()

    def _build_getting_started(self, doc, data, content):
        """Getting Started section with contact card."""
        self.docx.add_section_header(doc, "Let's Get Started")

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
