# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Host Media Kit proposal generator — scannable, visual, v20 format."""

from generators.base_proposal import BaseProposal
from services.config_service import (
    get_team_member, get_all_tiers,
    get_tier_impressions, calculate_cpm, CPM_BENCHMARK_TEXT,
    get_hours_per_day, get_days_per_month,
)


class HostMediaKitProposal(BaseProposal):
    """Generates a Host Media Kit proposal for prospective venue partners."""

    # Intentional photo placement — no scattered behavior.
    PHOTO_DISTRIBUTION = {
        "opportunity":    {"source": "page2", "max": 4},
        "_host_package":  {"source": "page4", "max": 6, "cols": 2,
                           "title": "Our Screens in Your Community"},
    }

    @property
    def proposal_type_key(self) -> str:
        return "host_media_kit"

    def get_sections(self) -> list:
        return [
            ("opportunity", "The Opportunity"),
            ("host_benefits", "Host Benefits"),
            ("_host_package", "Your Free Host Package"),
            ("_addon_pricing", "Add-On Advertising Packages"),
            ("_network_locations", "MCTV Network Locations"),
            ("_social_proof", "The MCTV Network"),
            ("getting_started", "Let's Get Started"),
            ("_team", "Meet Your Team"),
        ]

    def get_prompt_variables(self, data) -> dict:
        rep = get_team_member(self.config, data.sales_rep)
        return {
            "venue_name": data.venue_name,
            "contact_name": data.contact_name,
            "venue_category": data.venue_category,
            "city": data.city,
            "proposed_screen_count": data.proposed_screen_count,
            "free_outside_screens": data.free_outside_screens,
            "host_free_screens": data.free_outside_screens,
            "sales_rep": rep["name"],
            "additional_notes": data.additional_notes or "No additional notes.",
        }

    def _build_cover(self, doc, input_data):
        """Build cover page with 'Host Media Kit' title."""
        rep = get_team_member(self.config, input_data.sales_rep)
        self.docx.add_cover_page(
            doc,
            title="Host\nMedia Kit",
            subtitle="PARTNERSHIP OVERVIEW",
            prepared_for=f"{input_data.contact_name} \u2014 {input_data.venue_name}",
            prepared_by=rep,
        )

    def build_section(self, doc, section_key, data, content):
        if section_key == "opportunity":
            self._build_opportunity(doc, data, content)
        elif section_key == "host_benefits":
            self._build_host_benefits(doc, content)
        elif section_key == "_host_package":
            self._build_host_package(doc, data)
        elif section_key == "_addon_pricing":
            self._build_addon_pricing(doc, data)
        elif section_key == "_network_locations":
            self._build_network_locations(doc)
        elif section_key == "_social_proof":
            self._build_social_proof(doc, data)
        elif section_key == "getting_started":
            self._build_getting_started(doc, data, content)
        elif section_key == "_team":
            self.docx.add_team_section(doc)

    # ── THE OPPORTUNITY (paragraph + callout bullets + stats banner) ──

    def _build_opportunity(self, doc, data, content):
        """The Opportunity section with callout box and network stats banner."""
        self.docx.add_section_header(doc, "The Opportunity")

        # Claude returns: 1 paragraph then dash-bullet reasons
        # Split on the first dash to separate paragraph from bullets
        import re
        parts = re.split(r'\n\s*-\s*', content, maxsplit=1)
        if len(parts) == 2:
            # Opening paragraph
            self.docx.add_body_text(doc, parts[0].strip())
            # Reconstruct bullets with clean "- " prefix and put in callout box
            bullets = re.split(r'\n\s*-\s*', parts[1])
            clean_bullets = "\n".join(f"- {b.strip()}" for b in bullets if b.strip())
            self.docx.add_callout_box(doc, clean_bullets)
        else:
            self.docx.add_body_text(doc, content)

        # Network stats banner
        network = self.config["network"]
        self.docx.add_metrics_banner(doc, {
            network["total_screens"]: "Screens Across\nNorth Mississippi",
            network["monthly_impressions"]: "Monthly Impressions",
            f"{network['avg_dwell_time_minutes']}+ Min": "Avg. Dwell Time\nPer Visit",
            f"{network['plays_per_hour']}x/Hour": "Ad Plays\nEvery Hour",
        })

        # Host-specific benefits banner
        pricing = self.config["pricing"]
        free_outside = pricing.get("host_free_outside_screens", 10)
        self.docx.add_metrics_banner(doc, {
            "$0 Cost": "Zero Out-of-Pocket\nExpense",
            f"{pricing['host_free_inside_plays_per_hour']}x/Hour": "In-Store Ad Plays\nOn Every Screen",
            f"{free_outside}": "Free Screens\nNetwork-Wide",
            "Free": "Content Creation\n& Management",
        })

    # ── HOST BENEFITS (selling point cards) ──

    def _build_host_benefits(self, doc, content):
        self.docx.add_section_header(doc, "Host Benefits")

        import re
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            clean = line.lstrip('- ').strip()
            if not clean:
                continue
            match = re.match(r'^(.+?)(?::|--)\s+(.+)$', clean)
            if match:
                self.docx.add_selling_point(doc, match.group(1).strip(), match.group(2).strip())
            elif clean:
                self.docx.add_selling_point(doc, clean, "")

    # ── YOUR FREE HOST PACKAGE (sub-headers + metrics + callout) ──

    def _build_host_package(self, doc, data):
        """Config-driven free host package breakdown."""
        self.docx.add_section_header(doc, "Your Free Host Package", new_page=True)

        pricing = self.config["pricing"]
        inside_plays = pricing["host_free_inside_plays_per_hour"]
        outside_plays = pricing["host_outside_plays_per_hour"]
        free_outside = data.free_outside_screens

        # Calculate monthly ad plays
        hours_per_day = get_hours_per_day(self.config)
        days_per_month = get_days_per_month(self.config)
        inside_monthly = inside_plays * hours_per_day * days_per_month * data.proposed_screen_count
        outside_monthly = outside_plays * hours_per_day * days_per_month * free_outside
        total_monthly = inside_monthly + outside_monthly

        self.docx.add_sub_header(doc, "AT YOUR LOCATION")
        self.docx.add_body_text(
            doc,
            f"Your ad plays {inside_plays}x per hour on "
            f"{'every screen' if data.proposed_screen_count == 1 else f'all {data.proposed_screen_count} screens'} "
            f"at {data.venue_name}. That means your business is front and center "
            f"for every customer who walks through the door \u2014 all day, every day, at no cost."
        )

        self.docx.add_sub_header(doc, "ACROSS THE MCTV NETWORK")
        self.docx.add_body_text(
            doc,
            f"As a host venue, {data.venue_name} also receives FREE advertising "
            f"on {free_outside} additional screens across the MCTV network at "
            f"{outside_plays}x per hour. Your brand reaches customers at restaurants, "
            f"gyms, barbershops, and more \u2014 people who may have never visited your location."
        )

        # Summary metrics banner
        self.docx.add_metrics_banner(doc, {
            f"{inside_plays}x/hr": f"At {data.venue_name}",
            f"{free_outside}": "Additional Screens\nAcross the Network",
            f"{outside_plays}x/hr": "At Each\nNetwork Location",
            f"{total_monthly:,}": "Total Ad Plays\nPer Month",
        })

        # Total value in a callout box instead of plain body_text
        self.docx.add_callout_box(
            doc,
            f"Total value: {total_monthly:,} ad plays every month at absolutely no cost to you."
        )

    # ── ADD-ON PRICING (own page: table + contract terms) ──

    def _build_addon_pricing(self, doc, data):
        """Config-driven add-on pricing tiers with host discount note."""
        self.docx.add_section_header(doc, "Add-On Advertising Packages", new_page=True)

        self.docx.add_body_text(
            doc,
            f"Want even more exposure? As an MCTV host venue, {data.venue_name} "
            f"gets preferred pricing on expanded advertising packages. Add more "
            f"screens to amplify your reach across Oxford, Starkville, and Tupelo."
        )

        # Standard tiers table
        tiers = get_all_tiers(self.config)
        self.docx.add_pricing_table(doc, tiers)

        # CPM value comparison
        cpm_parts = []
        for tier in tiers:
            tier_imp = get_tier_impressions(self.config, tier["screens"])
            tier_cpm = calculate_cpm(tier["monthly_rate"], tier_imp)
            if tier_cpm > 0:
                cpm_parts.append(f"{tier['name']}: ${tier_cpm:.2f}")
        if cpm_parts:
            self.docx.add_callout_box(
                doc,
                f"CPM (Cost Per 1,000 Impressions):  "
                f"{'  |  '.join(cpm_parts)}\n"
                f"{CPM_BENCHMARK_TEXT}"
            )

        self.docx.add_sub_header(doc, "HOST VENUE ADVANTAGE")
        self.docx.add_body_text(
            doc,
            "As a host partner, you already have premium placement at your own "
            "location at no charge. Any add-on package stacks on top of your "
            "free host benefits \u2014 giving you more total exposure than a "
            "standard advertiser at the same price point."
        )

        # Contract terms
        self.docx.add_sub_header(doc, "PARTNERSHIP TERMS")
        self.docx.add_contract_terms(doc, self.config)

    # ── NETWORK LOCATIONS (compact callout box) ──

    def _build_network_locations(self, doc):
        """Config-driven network locations summary."""
        self.docx.add_section_header(doc, "MCTV Network Locations")

        self.docx.add_body_text(
            doc,
            "MCTV Elite Advertising operates the largest indoor digital billboard "
            "network in North Mississippi. Here is where your ads can play:"
        )

        markets = self.config["markets"]
        for market_name, market_data in markets.items():
            screens = market_data["screens"]
            status = market_data["status"]
            description = market_data.get("description", "")

            if status == "active":
                self.docx.add_sub_header(doc, f"{market_name.upper()} \u2014 {screens} SCREENS")
                self.docx.add_body_text(doc, description)
            elif status == "expanding":
                self.docx.add_sub_header(doc, f"{market_name.upper()} \u2014 COMING SOON")
                self.docx.add_body_text(doc, description)

        self.docx.add_sub_header(doc, "WHERE YOUR ADS PLAY")
        self.docx.add_venue_categories(doc)

    # ── SOCIAL PROOF (network stats + venue categories) ──

    def _build_social_proof(self, doc, data):
        self.docx.add_section_header(doc, "The MCTV Network", new_page=True)

        proof = self.config.get("social_proof", {})
        headline = proof.get("headline", "")
        if headline:
            self.docx.add_body_text(doc, headline)

        self.docx.add_social_proof_section(doc)

        self.docx.add_sub_header(doc, "WHERE YOUR ADS PLAY")
        self.docx.add_venue_categories(doc)

    # ── GETTING STARTED (content + compact contact callout) ──

    def _build_getting_started(self, doc, data, content):
        self.docx.add_section_header(doc, "Let's Get Started", new_page=True)
        self.docx.add_body_text(doc, content)

        rep = get_team_member(self.config, data.sales_rep)
        self.docx.add_sub_header(doc, "YOUR PARTNERSHIP CONTACT")

        contact_text = f"{rep['name']}  |  {rep['email']}  |  {rep['phone']}  |  MCTV Elite Advertising  |  MCTVofMS.com"
        self.docx.add_callout_box(doc, contact_text)
