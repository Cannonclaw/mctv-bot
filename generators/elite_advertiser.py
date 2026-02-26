# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Elite Advertiser proposal generator — scannable, visual, 5-6 pages."""

from generators.base_proposal import BaseProposal
from services.config_service import (
    get_team_member, get_pricing_tier, get_all_tiers,
    get_tier_impressions, calculate_cpm, CPM_BENCHMARK_TEXT,
)


class EliteAdvertiserProposal(BaseProposal):
    """Generates the flagship 5-6 page advertiser proposal."""

    # Intentional photo placement — every photo has a specific page.
    # page2 = The Opportunity (max 4 hero photos, responsive grid)
    # page4 = Market Coverage (max 6 in a 2×3 grid with captions)
    # No "scattered" behavior — photos only appear where assigned.
    PHOTO_DISTRIBUTION = {
        "opportunity_hook": {"source": "page2", "max": 4},
        "market_coverage":  {"source": "page4", "max": 6, "cols": 2,
                             "title": "Our Screens in Your Community"},
    }

    @property
    def proposal_type_key(self) -> str:
        return "elite_advertiser"

    def get_sections(self) -> list:
        return [
            ("opportunity_hook", "The Opportunity"),
            ("whats_included", "What's Included"),
            ("market_coverage", "Your Market Coverage"),
            ("_pricing", "Partnership Pricing"),
            ("_competitive", "How MCTV Compares"),
            ("why_choose_mctv", "Why MCTV"),
            ("_social_proof", "The MCTV Network"),
            ("getting_started", "Getting Started"),
            ("_team", "Meet Your Team"),
        ]

    def get_prompt_variables(self, data) -> dict:
        rep = get_team_member(self.config, data.sales_rep)
        markets = ", ".join(data.selected_markets)

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
            "contact_email": data.contact_email,
            "industry": data.industry,
            "city": data.city,
            "selected_markets": selected_markets,
            "sales_rep": rep["name"],
            "additional_notes": data.additional_notes or "No additional notes.",
            "host_free_screens": self.config["pricing"]["host_free_outside_screens"],
        }

    def build_section(self, doc, section_key, data, content):
        if section_key == "opportunity_hook":
            self._build_opportunity_hook(doc, data, content)
        elif section_key == "whats_included":
            self._build_whats_included(doc, content)
        elif section_key == "market_coverage":
            self._build_market_coverage(doc, data, content)
        elif section_key == "_pricing":
            self._build_pricing(doc, data)
        elif section_key == "_competitive":
            self._build_competitive(doc, data)
        elif section_key == "why_choose_mctv":
            self._build_why_choose_mctv(doc, content)
        elif section_key == "_social_proof":
            self._build_social_proof(doc, data)
        elif section_key == "getting_started":
            self._build_getting_started(doc, data, content)
        elif section_key == "_team":
            self.docx.add_team_section(doc)

    # ── THE OPPORTUNITY (1 page: paragraph + selling point cards + stats banner) ──

    def _build_opportunity_hook(self, doc, data, content):
        self.docx.add_section_header(doc, "The Opportunity")

        # Claude returns: 1 paragraph then 3 dash-bullet reasons
        # Split on the first dash to separate paragraph from bullets
        import re
        # Split paragraph from bullet reasons (Claude uses \n- or \n -  prefixes)
        parts = re.split(r'\n\s*-\s*', content, maxsplit=1)
        if len(parts) == 2:
            # Opening paragraph
            self.docx.add_body_text(doc, parts[0].strip())
            # Parse each bullet into (title, description) and render as
            # individual scannable items with bold heading + body text
            bullets = re.split(r'\n\s*-\s*', parts[1])
            for bullet in bullets:
                bullet = bullet.strip()
                if not bullet:
                    continue
                # Match "Title: Description" or "Title -- Description"
                match = re.match(r'^(.+?)(?::|--)\s+(.+)$', bullet)
                if match:
                    title = match.group(1).strip()
                    desc = match.group(2).strip()
                    self.docx.add_selling_point(doc, title, desc)
                else:
                    self.docx.add_selling_point(doc, bullet, "")
        else:
            self.docx.add_body_text(doc, content)

        # Network stats banner
        network = self.config["network"]
        self.docx.add_metrics_banner(doc, {
            network["total_screens"]: "Screens Across\nNorth Mississippi",
            network["monthly_impressions"]: "Monthly Impressions",
            f"{network['avg_dwell_time_minutes']}+ Min": "Avg. Dwell Time\nPer Visit",
            f"{network['plays_per_hour']}x/Hour": "Your Ad Plays\nEvery Day",
        })

    # ── WHAT'S INCLUDED (accent cards — each benefit is its own card) ──

    def _build_whats_included(self, doc, content):
        self.docx.add_section_header(doc, "What's Included", new_page=True)

        # Parse Claude's "- Title: Description" lines into accent cards
        import re
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            # Match "- Title: Description" or "- Title -- Description"
            bullet_match = re.match(r'^-\s+(.+?)(?::|--)\s+(.+)$', line)
            if bullet_match:
                title = bullet_match.group(1).strip()
                desc = bullet_match.group(2).strip()
                self.docx.add_accent_card(doc, title, desc)
            else:
                # Fallback for lines that don't match the pattern
                clean = line.lstrip('- ').strip()
                if clean:
                    self.docx.add_body_text(doc, clean)

    # ── MARKET COVERAGE (compact: short text + inline venue list) ──

    def _build_market_coverage(self, doc, data, content):
        self.docx.add_section_header(doc, "Your Market Coverage", new_page=True)
        self.docx.add_body_text(doc, content)

        # Compact venue list as a callout box instead of a grid
        venue_text = (
            "Your ads play in: Restaurants & Bars  |  Barbershops & Salons  |  "
            "Medical & Dental  |  Gyms & Fitness  |  Auto & Service Shops  |  "
            "Retail & Boutiques  |  Professional Offices  |  Community Venues"
        )
        self.docx.add_callout_box(doc, venue_text)

    # ── PRICING (own page: table + contract terms) ──

    def _build_pricing(self, doc, data):
        self.docx.add_section_header(doc, "Partnership Pricing", new_page=True)

        if data.custom_pricing:
            # Custom pricing display
            self.docx.add_sub_header(doc, f"YOUR PARTNERSHIP PACKAGE")

            tier_impressions = get_tier_impressions(self.config, data.custom_screen_count)
            cpm = calculate_cpm(data.custom_monthly_rate, tier_impressions)

            self.docx.add_body_text(
                doc,
                f"${data.custom_monthly_rate:,.0f} / month  \u2014  "
                f"{data.custom_screen_count} Screens\n\n"
                f"Your ad plays across all {data.custom_screen_count} screens \u2014 "
                f"restaurants, gyms, offices, and retail. "
                f"Each ad slot gets {self.config['network']['plays_per_hour']} plays per hour "
                f"on a {self.config['network']['content_loop_minutes']}-minute loop, "
                f"all day, every day."
            )

            if cpm > 0:
                self.docx.add_callout_box(
                    doc,
                    f"Your CPM (Cost Per 1,000 Impressions): ${cpm:.2f}\n"
                    f"{CPM_BENCHMARK_TEXT}"
                )
        else:
            # Standard 4-tier pricing table — highlight tier 2 (index 1) as recommended
            tiers = get_all_tiers(self.config)
            recommended = 1 if len(tiers) > 1 else None
            self.docx.add_pricing_table(doc, tiers, recommended_idx=recommended)

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
                    f"Your CPM (Cost Per 1,000 Impressions):  "
                    f"{'  |  '.join(cpm_parts)}\n"
                    f"{CPM_BENCHMARK_TEXT}"
                )

        # Pricing callout — encourage conversation
        self.docx.add_callout_box(
            doc,
            "Not sure which package is right for you? Most of our partners start "
            "with our most popular tier and scale up as they see results. "
            "Your dedicated rep can help you find the perfect fit."
        )

        # Contract terms
        self.docx.add_sub_header(doc, "PARTNERSHIP TERMS")
        self.docx.add_contract_terms(doc, self.config)

    # ── COMPETITIVE COMPARISON (MCTV vs other media channels) ──

    def _build_competitive(self, doc, data):
        self.docx.add_section_header(doc, "How MCTV Compares")

        self.docx.add_body_text(
            doc,
            "Local businesses have more advertising options than ever. "
            "Here is how MCTV stacks up against the alternatives."
        )

        # Get rate and impressions for ROI projection
        if data.custom_pricing:
            rate = data.custom_monthly_rate
            screens = data.custom_screen_count
        else:
            tier = get_pricing_tier(self.config, data.recommended_tier)
            rate = tier["monthly_rate"]
            screens = tier["screens"]

        impressions = get_tier_impressions(self.config, screens)
        self.docx.add_competitive_comparison(doc, rate, screens, impressions)

        # ROI projection callout
        self.docx.add_roi_projection(
            doc, rate, screens, impressions,
            business_name=data.business_name,
        )

    # ── SOCIAL PROOF (network stats + trust points) ──

    def _build_social_proof(self, doc, data):
        self.docx.add_section_header(doc, "The MCTV Network", new_page=True)

        proof = self.config.get("social_proof", {})
        headline = proof.get("headline", "")
        if headline:
            self.docx.add_body_text(doc, headline)

        self.docx.add_social_proof_section(doc)

        # Venue category grid
        self.docx.add_sub_header(doc, "WHERE YOUR ADS PLAY")
        self.docx.add_venue_categories(doc)

    # ── WHY MCTV (accent cards — each selling point is its own card) ──

    def _build_why_choose_mctv(self, doc, content):
        self.docx.add_section_header(doc, "Why MCTV", new_page=True)

        # Parse Claude's output into (title, description) pairs.
        # Claude may return various formats:
        #   "Title: Description sentence."
        #   "- Title: Description sentence."
        #   "Title -- Description sentence."
        # Lines without a colon/dash-dash are continuation of the previous item.
        import re
        items = []

        for line in content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            # Strip leading dash
            clean = line.lstrip('- ').strip()
            if not clean:
                continue

            # Try to match "Title: Description" or "Title -- Description"
            match = re.match(r'^(.+?)(?::|--)\s+(.+)$', clean)
            if match:
                items.append((match.group(1).strip(), match.group(2).strip()))
            elif items:
                # Continuation line — append to last item's description
                title, desc = items[-1]
                items[-1] = (title, desc + " " + clean)

        if items:
            for title, desc in items:
                self.docx.add_accent_card(doc, title, desc)
        else:
            # Final fallback if all parsing fails
            self.docx.add_bullet_list(doc, content)

    # ── GETTING STARTED (numbered steps like Good Earth) ──

    def _build_getting_started(self, doc, data, content):
        self.docx.add_section_header(doc, "Getting Started", new_page=True)
        self.docx.add_body_text(doc, content)
