# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Renewal / Upgrade proposal generator — scannable, visual v20 layout."""

import re

from generators.base_proposal import BaseProposal
from services.config_service import (
    get_team_member, get_all_tiers,
    get_tier_impressions, calculate_cpm, CPM_BENCHMARK_TEXT,
)


class RenewalUpgradeProposal(BaseProposal):
    """Generates a Renewal/Upgrade proposal for existing clients."""

    # Intentional photo placement — no scattered behavior.
    PHOTO_DISTRIBUTION = {
        "results_summary":  {"source": "page2", "max": 4},
        "_results_table":   {"source": "page4", "max": 6, "cols": 3,
                             "title": "Our Screens in Your Community"},
    }

    @property
    def proposal_type_key(self) -> str:
        return "renewal_upgrade"

    def get_sections(self) -> list:
        return [
            ("results_summary", "Your Results So Far"),
            ("_results_table", "Performance Data"),
            ("upgrade_pitch", "The Next Level"),
            ("_upgrade_pricing", "Upgrade Pricing"),
            ("_competitive", "How MCTV Compares"),
            ("_social_proof", "The MCTV Network"),
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
        elif section_key == "_competitive":
            self._build_competitive(doc, data)
        elif section_key == "_social_proof":
            self._build_social_proof(doc)
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

        parts = re.split(r'\n\s*-\s*', content, maxsplit=1)
        if len(parts) == 2:
            self.docx.add_body_text(doc, parts[0].strip())
            bullets = re.split(r'\n\s*-\s*', parts[1])
            clean_bullets = "\n".join(f"- {b.strip()}" for b in bullets if b.strip())
            self.docx.add_callout_box(doc, clean_bullets)
        else:
            self.docx.add_body_text(doc, content)

        self.docx.add_metrics_banner(doc, {
            f"{data.total_plays:,}": "Total Ad\nPlays",
            str(data.total_venues): "Active\nVenues",
            f"{data.total_impressions:,.0f}": "Total\nImpressions",
            f"{data.months_as_client}": "Months as\nPartner",
        })

    def _build_results_table(self, doc, data):
        """Config-driven results data table if traction_data is provided."""
        if not data.traction_data:
            return

        self.docx.add_section_header(doc, "Performance Data", new_page=True)

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

    def _build_upgrade_pitch(self, doc, content):
        """Claude-generated upgrade pitch rendered as accent cards."""
        self.docx.add_section_header(doc, "The Next Level", new_page=True)

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

    def _build_upgrade_pricing(self, doc, data):
        """Config-driven pricing showing current tier vs. upgrade tier."""
        self.docx.add_section_header(doc, "Upgrade Pricing", new_page=True)

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
            # CPM for current tier
            current_impressions = get_tier_impressions(self.config, current_tier_data["screens"])
            current_cpm = calculate_cpm(current_tier_data["monthly_rate"], current_impressions)

            self.docx.add_sub_header(doc, "YOUR CURRENT PACKAGE")
            current_metrics = {
                f"${current_tier_data['monthly_rate']:,}/mo": "Current Rate",
                f"{current_tier_data['screens']}": "Current Screens",
            }
            if current_cpm > 0:
                current_metrics[f"${current_cpm:.2f}"] = "Current CPM"
            else:
                current_metrics[current_tier_data.get("plays_per_month", "")] = "Current Plays/Mo"
            current_metrics[f"${current_tier_data.get('cost_per_screen', 0):.2f}"] = "Cost Per Screen"
            self.docx.add_metrics_banner(doc, current_metrics)

            # CPM for upgrade tier
            upgrade_impressions = get_tier_impressions(self.config, suggested_tier_data["screens"])
            upgrade_cpm = calculate_cpm(suggested_tier_data["monthly_rate"], upgrade_impressions)

            self.docx.add_sub_header(doc, "RECOMMENDED UPGRADE")
            upgrade_metrics = {
                f"${suggested_tier_data['monthly_rate']:,}/mo": "New Rate",
                f"{suggested_tier_data['screens']}": "Screens",
            }
            if upgrade_cpm > 0:
                upgrade_metrics[f"${upgrade_cpm:.2f}"] = "New CPM"
            else:
                upgrade_metrics[suggested_tier_data.get("plays_per_month", "")] = "Plays/Mo"
            upgrade_metrics[f"${suggested_tier_data.get('cost_per_screen', 0):.2f}"] = "Cost Per Screen"
            self.docx.add_metrics_banner(doc, upgrade_metrics)

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
            value_text = (
                f"For just ${rate_increase:,.0f} more per month, {data.business_name} "
                f"adds {screen_increase} screens to your campaign. Your cost per screen "
                f"drops from ${current_cps:.2f} to ${upgrade_cps:.2f}"
            )
            if current_cpm > 0 and upgrade_cpm > 0:
                value_text += (
                    f", and your CPM improves from ${current_cpm:.2f} to "
                    f"${upgrade_cpm:.2f}"
                )
            value_text += " \u2014 more visibility at a better value per location."
            self.docx.add_body_text(doc, value_text)

            if current_cpm > 0 or upgrade_cpm > 0:
                self.docx.add_callout_box(doc, CPM_BENCHMARK_TEXT)
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
        self.docx.add_callout_box(
            doc,
            f"As a returning partner, {data.business_name} locks in current pricing "
            f"for the full duration of your renewal term. As MCTV grows and demand "
            f"increases, new advertisers will pay higher rates. Your loyalty "
            f"protects your rate."
        )

        # Contract terms
        self.docx.add_sub_header(doc, "PARTNERSHIP TERMS")
        self.docx.add_contract_terms(doc, self.config)

    def _build_competitive(self, doc, data):
        """MCTV vs other media channels — uses suggested upgrade tier."""
        self.docx.add_section_header(doc, "How MCTV Compares")

        self.docx.add_body_text(
            doc,
            "Local businesses have more advertising options than ever. "
            "Here is how MCTV stacks up against the alternatives."
        )

        tiers = get_all_tiers(self.config)
        suggested_tier_data = None
        for tier in tiers:
            if tier["name"].lower() == data.suggested_upgrade_tier.lower():
                suggested_tier_data = tier
                break

        if suggested_tier_data:
            rate = suggested_tier_data["monthly_rate"]
            screens = suggested_tier_data["screens"]
        else:
            rate = tiers[1]["monthly_rate"] if len(tiers) > 1 else tiers[0]["monthly_rate"]
            screens = tiers[1]["screens"] if len(tiers) > 1 else tiers[0]["screens"]

        impressions = get_tier_impressions(self.config, screens)
        self.docx.add_competitive_comparison(doc, rate, screens, impressions)

    def _build_social_proof(self, doc):
        """Network trust section with social proof and venue categories."""
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
        self.docx.add_section_header(doc, "Let's Keep Growing", new_page=True)

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
        contact_text = f"{rep['name']}  |  {rep['email']}  |  {rep['phone']}  |  MCTV Elite Advertising  |  MCTVofMS.com"
        self.docx.add_callout_box(doc, contact_text)
