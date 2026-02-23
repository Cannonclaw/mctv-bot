"""Elite Advertiser proposal generator — scannable, visual, 5-6 pages."""

from generators.base_proposal import BaseProposal
from services.config_service import get_team_member, get_pricing_tier, get_all_tiers


class EliteAdvertiserProposal(BaseProposal):
    """Generates the flagship 5-6 page advertiser proposal."""

    # Distribute photos across sections to fill whitespace:
    # - opportunity_hook (page 2): up to 2 side-by-side client photos
    # - market_coverage (page 3): up to 2 community screen photos to fill gap
    # NOTE: Do NOT place photos on getting_started or _team pages —
    #       the team section + logo + URL must fit on one page.
    PHOTO_DISTRIBUTION = {
        "opportunity_hook": {"source": "extra", "max": 2},
        "market_coverage":  {"source": "extra", "max": 2, "title": "Our Screens in Your Community"},
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
            ("why_choose_mctv", "Why MCTV"),
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
        elif section_key == "why_choose_mctv":
            self._build_why_choose_mctv(doc, content)
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
        doc.add_page_break()
        self.docx.add_section_header(doc, "What's Included")

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
        doc.add_page_break()
        self.docx.add_section_header(doc, "Your Market Coverage")
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
        doc.add_page_break()
        self.docx.add_section_header(doc, "Partnership Pricing")

        if data.custom_pricing:
            # Custom pricing display
            self.docx.add_sub_header(doc, f"YOUR PARTNERSHIP PACKAGE")
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
        else:
            # Standard 4-tier pricing table — highlight tier 2 (index 1) as recommended
            tiers = get_all_tiers(self.config)
            recommended = 1 if len(tiers) > 1 else None
            self.docx.add_pricing_table(doc, tiers, recommended_idx=recommended)

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

    # ── WHY MCTV (accent cards — each selling point is its own card) ──

    def _build_why_choose_mctv(self, doc, content):
        doc.add_page_break()
        self.docx.add_section_header(doc, "Why MCTV")

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
        doc.add_page_break()
        self.docx.add_section_header(doc, "Getting Started")
        self.docx.add_body_text(doc, content)
