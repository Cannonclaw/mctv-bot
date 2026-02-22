"""Elite Advertiser proposal generator — scannable, visual, 5-6 pages."""

from generators.base_proposal import BaseProposal
from services.config_service import get_team_member, get_pricing_tier, get_all_tiers


class EliteAdvertiserProposal(BaseProposal):
    """Generates the flagship 5-6 page advertiser proposal."""

    # Scatter scraped/extra photos across these sections (consumed in order)
    PHOTO_DISTRIBUTION = {
        "opportunity_hook": {"source": "extra", "max": 2},
        "whats_included":   {"source": "extra", "max": 1},
        "why_choose_mctv":  {"source": "extra", "max": 1},
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
            ("getting_started", "Let's Get Started"),
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

    # ── THE OPPORTUNITY (1 page: paragraph + callout bullets + stats banner) ──

    def _build_opportunity_hook(self, doc, data, content):
        self.docx.add_section_header(doc, "The Opportunity")

        # Claude returns: 1 paragraph then 3 dash-bullet reasons
        # Split on the first dash to separate paragraph from bullets
        parts = content.split("\n-", 1)
        if len(parts) == 2:
            # Opening paragraph
            self.docx.add_body_text(doc, parts[0].strip())
            # Bullet reasons in a callout box
            self.docx.add_callout_box(doc, "-" + parts[1].strip())
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

    # ── WHAT'S INCLUDED (half page: 5 bullet points, no intro) ──

    def _build_whats_included(self, doc, content):
        self.docx.add_section_header(doc, "What's Included")
        # Claude returns 5 dash-bullet items — render with bold navy titles
        self.docx.add_bullet_list(doc, content)

    # ── MARKET COVERAGE (compact: short text + inline venue list) ──

    def _build_market_coverage(self, doc, data, content):
        self.docx.add_section_header(doc, "Your Market Coverage")
        self.docx.add_body_text(doc, content)

        # Compact venue list as a callout box instead of a grid
        venue_text = (
            "Your ads play in: Restaurants & Bars  |  Barbershops & Salons  |  "
            "Medical & Dental  |  Gyms & Fitness  |  Auto & Service Shops  |  "
            "Retail & Boutiques  |  Professional Offices  |  Community Venues"
        )
        self.docx.add_callout_box(doc, venue_text, bg_color="F0EDE4")

    # ── PRICING (1 page: table + contract terms) ──

    def _build_pricing(self, doc, data):
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
            # Standard 4-tier pricing table
            tiers = get_all_tiers(self.config)
            self.docx.add_pricing_table(doc, tiers)

        # Contract terms
        self.docx.add_sub_header(doc, "PARTNERSHIP TERMS")
        self.docx.add_contract_terms(doc, self.config)

    # ── WHY MCTV (half page: 4 callout boxes) ──

    def _build_why_choose_mctv(self, doc, content):
        self.docx.add_section_header(doc, "Why MCTV")

        # Claude returns 4 dash-bullet items — render each as a callout box
        import re
        items = re.findall(r'-\s+(.+?)(?::|--)\s+(.+)', content)
        if items:
            for title, desc in items:
                self.docx.add_callout_box(
                    doc,
                    f"{title.strip()}: {desc.strip()}",
                    bg_color="F0EDE4",
                )
        else:
            # Fallback if parsing fails
            self.docx.add_bullet_list(doc, content)

    # ── LET'S GET STARTED (half page: short close + steps + contact inline) ──

    def _build_getting_started(self, doc, data, content):
        self.docx.add_section_header(doc, "Let's Get Started")
        self.docx.add_body_text(doc, content)

        # Contact info as a callout box (compact, stays on same page)
        rep = get_team_member(self.config, data.sales_rep)
        contact_text = (
            f"Ready to get started? Reach out to {rep['name']} at "
            f"{rep['email']} or {rep['phone']}."
        )
        self.docx.add_callout_box(doc, contact_text)
