"""Renewal / Upgrade proposal generator.

Generates a proposal for existing MCTV clients whose partnership is up
for renewal, highlighting their past performance data and pitching an
upgrade to a higher tier.
"""

from generators.base_proposal import BaseProposal
from services.config_service import get_team_member, get_all_tiers
from services.docx_service import NAVY, GOLD, GRAY, Pt, WD_ALIGN_PARAGRAPH


class RenewalUpgradeProposal(BaseProposal):
    """Generates a Renewal/Upgrade proposal for existing clients."""

    @property
    def proposal_type_key(self) -> str:
        return "renewal_upgrade"

    def get_sections(self) -> list:
        return [
            ("results_summary", "Your Results So Far"),
            ("_results_table", "Performance Data"),
            ("upgrade_pitch", "The Next Level"),
            ("_upgrade_pricing", "Upgrade Pricing"),
            ("getting_started", "Let's Keep Growing"),
            ("_team", "Meet Your Team"),
        ]

    def get_prompt_variables(self, data) -> dict:
        rep = get_team_member(self.config, data.sales_rep)

        # Format impressions nicely
        if data.total_impressions >= 1_000_000:
            impressions_str = f"{data.total_impressions / 1_000_000:.1f}M+"
        elif data.total_impressions >= 1_000:
            impressions_str = f"{data.total_impressions / 1_000:.0f}K+"
        else:
            impressions_str = f"{data.total_impressions:,.0f}"

        return {
            "business_name": data.business_name,
            "contact_name": data.contact_name,
            "current_tier": data.current_tier,
            "months": data.months_as_client,
            "total_plays": f"{data.total_plays:,}",
            "venue_count": data.total_venues,
            "total_impressions": impressions_str,
            "suggested_tier": data.suggested_upgrade_tier,
            "sales_rep": rep["name"],
            "additional_notes": data.additional_notes or "No additional notes.",
        }

    def _build_cover(self, doc, input_data):
        """Build cover page with 'Partnership Renewal' title and thank-you subtitle."""
        rep = get_team_member(self.config, input_data.sales_rep)
        self.docx.add_cover_page(
            doc,
            title="Partnership\nRenewal",
            subtitle="Thank You for Your Partnership",
            prepared_for=f"{input_data.contact_name} \u2014 {input_data.business_name}",
            prepared_by=rep,
        )

    def build_section(self, doc, section_key, data, content):
        if section_key == "results_summary":
            self._build_results_summary(doc, data, content)
        elif section_key == "_results_table":
            self._build_results_table(doc, data)
        elif section_key == "upgrade_pitch":
            self._build_upgrade_pitch(doc, content)
        elif section_key == "_upgrade_pricing":
            self._build_upgrade_pricing(doc, data)
        elif section_key == "getting_started":
            self._build_getting_started(doc, data, content)
        elif section_key == "_team":
            self.docx.add_team_section(doc)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_results_summary(self, doc, data, content):
        """Claude-generated results summary with performance metrics banner."""
        self.docx.add_section_header(doc, "Your Results So Far")
        self.docx.add_body_text(doc, content)

        # Format impressions for the banner
        if data.total_impressions >= 1_000_000:
            impressions_display = f"{data.total_impressions / 1_000_000:.1f}M+"
        elif data.total_impressions >= 1_000:
            impressions_display = f"{data.total_impressions / 1_000:.0f}K+"
        else:
            impressions_display = f"{data.total_impressions:,.0f}"

        self.docx.add_metrics_banner(doc, {
            f"{data.months_as_client}": "Months as\nMCTV Partner",
            f"{data.total_plays:,}": "Total Ad Plays\nDelivered",
            f"{data.total_venues}": "Venues Playing\nYour Ads",
            impressions_display: "Estimated\nImpressions",
        })
        doc.add_page_break()

    def _build_results_table(self, doc, data):
        """Config-driven results data table if traction_data is provided.

        The traction_data dict is expected to contain monthly or periodic
        breakdowns. Supported formats:
          - {"months": [{"month": "Jan 2025", "plays": 1200, "venues": 10, "impressions": 45000}, ...]}
          - {"venues": [{"name": "Venue A", "plays": 500, "impressions": 20000}, ...]}
        If no traction_data is provided, this section is skipped.
        """
        if not data.traction_data:
            return

        self.docx.add_section_header(doc, "Performance Data")

        # Monthly breakdown
        monthly_data = data.traction_data.get("months", [])
        if monthly_data:
            self.docx.add_sub_header(doc, "MONTHLY PERFORMANCE")

            headers = ["Month", "Ad Plays", "Venues", "Est. Impressions"]
            rows = []
            for entry in monthly_data:
                rows.append([
                    entry.get("month", ""),
                    f"{entry.get('plays', 0):,}",
                    str(entry.get("venues", "")),
                    f"{entry.get('impressions', 0):,}",
                ])
            self.docx.add_data_table(doc, headers, rows)

        # Venue breakdown
        venue_data = data.traction_data.get("venues", [])
        if venue_data:
            self.docx.add_sub_header(doc, "TOP PERFORMING VENUES")

            headers = ["Venue", "Ad Plays", "Est. Impressions"]
            rows = []
            for entry in venue_data:
                rows.append([
                    entry.get("name", ""),
                    f"{entry.get('plays', 0):,}",
                    f"{entry.get('impressions', 0):,}",
                ])
            self.docx.add_data_table(doc, headers, rows)

        doc.add_page_break()

    def _build_upgrade_pitch(self, doc, content):
        """Claude-generated upgrade pitch."""
        self.docx.add_section_header(doc, "The Next Level")
        self.docx.add_body_text(doc, content)
        doc.add_page_break()

    def _build_upgrade_pricing(self, doc, data):
        """Config-driven pricing showing current tier vs. upgrade tier."""
        self.docx.add_section_header(doc, "Upgrade Pricing")

        self.docx.add_body_text(
            doc,
            f"As a valued partner, {data.business_name} has earned the opportunity "
            f"to expand your reach at a preferred rate. Below is a comparison of "
            f"your current package and the recommended upgrade."
        )

        tiers = get_all_tiers(self.config)

        # Find current and suggested tiers by name match
        current_tier_data = None
        suggested_tier_data = None
        for tier in tiers:
            if tier["name"].lower() == data.current_tier.lower():
                current_tier_data = tier
            if tier["name"].lower() == data.suggested_upgrade_tier.lower():
                suggested_tier_data = tier

        # Show current vs. upgrade comparison
        if current_tier_data and suggested_tier_data:
            self.docx.add_sub_header(doc, "YOUR CURRENT PACKAGE")
            self.docx.add_metrics_banner(doc, {
                f"${current_tier_data['monthly_rate']:,}/mo": "Current Rate",
                f"{current_tier_data['screens']}": "Current Screens",
                current_tier_data.get("plays_per_month", ""): "Current Plays/Mo",
                f"${current_tier_data.get('cost_per_screen', 0):.2f}": "Cost Per Screen",
            })

            self.docx.add_sub_header(doc, "RECOMMENDED UPGRADE")
            self.docx.add_metrics_banner(doc, {
                f"${suggested_tier_data['monthly_rate']:,}/mo": "New Rate",
                f"{suggested_tier_data['screens']}": "Screens",
                suggested_tier_data.get("plays_per_month", ""): "Plays/Mo",
                f"${suggested_tier_data.get('cost_per_screen', 0):.2f}": "Cost Per Screen",
            })

            # Calculate the value improvement
            current_screens = current_tier_data["screens"]
            upgrade_screens = suggested_tier_data["screens"]
            screen_increase = upgrade_screens - current_screens

            current_rate = current_tier_data["monthly_rate"]
            upgrade_rate = suggested_tier_data["monthly_rate"]
            rate_increase = upgrade_rate - current_rate

            current_cps = current_tier_data.get("cost_per_screen", 0)
            upgrade_cps = suggested_tier_data.get("cost_per_screen", 0)

            self.docx.add_sub_header(doc, "THE VALUE")
            self.docx.add_body_text(
                doc,
                f"For just ${rate_increase:,.0f} more per month, {data.business_name} "
                f"adds {screen_increase} screens to your campaign. Your cost per screen "
                f"drops from ${current_cps:.2f} to ${upgrade_cps:.2f} \u2014 more "
                f"visibility at a better value per location."
            )
        else:
            # Show full pricing table if we cannot match tier names
            self.docx.add_pricing_table(doc, tiers)
            if data.current_tier:
                self.docx.add_body_text(
                    doc,
                    f"You are currently on the {data.current_tier} package. "
                    f"We recommend upgrading to the {data.suggested_upgrade_tier} "
                    f"package to maximize your reach and lower your cost per screen."
                )

        # Renewal loyalty note
        self.docx.add_sub_header(doc, "RENEWAL LOYALTY BENEFIT")
        self.docx.add_body_text(
            doc,
            f"As a returning partner, {data.business_name} locks in current pricing "
            f"for the full duration of your renewal term. As MCTV grows and demand "
            f"increases, new advertisers will pay higher rates. Your loyalty "
            f"protects your rate."
        )

        # Contract terms
        self.docx.add_sub_header(doc, "PARTNERSHIP TERMS")
        self.docx.add_contract_terms(doc, self.config)
        doc.add_page_break()

    def _build_getting_started(self, doc, data, content):
        """Getting Started section with contact card."""
        self.docx.add_section_header(doc, "Let's Keep Growing")

        if content:
            self.docx.add_body_text(doc, content)
        else:
            self.docx.add_body_text(
                doc,
                f"Thank you for being a valued MCTV partner, {data.contact_name}. "
                f"The results speak for themselves \u2014 {data.total_plays:,} ad plays "
                f"across {data.total_venues} venues in just {data.months_as_client} months. "
                f"Let's build on that momentum."
            )
            self.docx.add_body_text(
                doc,
                "Renewing is simple: confirm your preferred package, and we handle the "
                "rest. No interruption to your campaign, no lapse in coverage. Your ads "
                "keep playing while we finalize the paperwork."
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
