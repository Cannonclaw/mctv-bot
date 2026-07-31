# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Real Estate Feeds Board proposal generator.

Sells a dynamic board rather than a static slot: agent or brokerage
branding held on every frame, listings rotating one at a time, and a
market mortgage-rate strip sourced and dated on screen.

Four sell modes share this generator because the board is the same
product in all four -- what changes is who pays and what has to be
disclosed:

    agent      one agent buys their own board
    brokerage  firm-level buy, usually with category exclusivity
    cosponsor  agent + lender split one board, invoiced separately
    lender     lender-branded rate board

The two lender modes add a Co-Sponsorship & Disclosure section. That
section is not decoration. Agent/lender co-marketing is regulated
(RESPA Section 8), and putting a rate next to a lender's name pulls the
board into TILA / Regulation Z advertising-disclosure territory. Writing
the split, the separate invoicing, and the display rules into the
proposal itself is what keeps the deal from being improvised later.
"""

import re

from generators.base_proposal import BaseProposal
from services.config_service import (
    get_team_member, get_tier_impressions, calculate_cpm,
    CPM_BENCHMARK_TEXT, get_hours_per_day, get_days_per_month,
)

# Modes that put a lender's brand on the board, and therefore pull in the
# co-sponsorship structure and display rules.
LENDER_MODES = ("cosponsor", "lender")

MODE_LABELS = {
    "agent": "Agent Board",
    "brokerage": "Brokerage Board",
    "cosponsor": "Co-Sponsored Board",
    "lender": "Lender Rate Board",
}


class RealEstateBoardProposal(BaseProposal):
    """Generates a Real Estate Feeds Board proposal."""

    PHOTO_DISTRIBUTION = {
        "opportunity":      {"source": "page2", "max": 4},
        "_market_coverage": {"source": "page4", "max": 6, "cols": 3,
                             "title": "Where Your Board Plays"},
    }

    def __init__(self, config, claude, docx):
        super().__init__(config, claude, docx)
        # get_prompt_variables() runs before get_sections() in the base
        # pipeline and refreshes this. Defaulted here so get_sections()
        # is safe to call standalone (tests, section previews).
        self._mode = "agent"

    @property
    def proposal_type_key(self) -> str:
        return "real_estate_board"

    @property
    def _board(self) -> dict:
        return self.config.get("real_estate_board", {})

    def get_sections(self) -> list:
        sections = [
            ("opportunity", "The Opportunity"),
            ("_anatomy", "What's On The Board"),
            ("board_value", "Why This Format Works"),
            ("_market_coverage", "Where Your Board Plays"),
            ("_pricing", "Investment"),
        ]
        if self._mode in LENDER_MODES:
            sections.append(("_compliance", "Co-Sponsorship & Disclosure"))
        sections += [
            ("_competitive", "How MCTV Compares"),
            ("_social_proof", "The MCTV Network"),
            ("getting_started", "Let's Get Started"),
            ("_team", "Meet Your Team"),
        ]
        return sections

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _tier(self, data) -> dict:
        """The selected board tier, with a safe fallback."""
        tiers = self._board.get("tiers", [])
        if not tiers:
            return {"name": "Board", "screens": 20, "monthly_rate": 0, "listings": 4}
        idx = max(0, min(data.board_tier, len(tiers) - 1))
        return tiers[idx]

    def _screens(self, data) -> int:
        return self._tier(data).get("screens", 0)

    def _listings(self, data) -> int:
        return data.listing_count or self._tier(data).get("listings", 4)

    def _rate(self, data) -> float:
        """Board rate: explicit override, else tier rate, plus exclusivity."""
        base = data.monthly_rate or float(self._tier(data).get("monthly_rate", 0))
        if data.include_exclusivity and not data.monthly_rate:
            premium = float(self._board.get("exclusivity_premium_pct", 0))
            base *= (1 + premium / 100.0)
        return base

    def _split(self, data) -> tuple:
        """(agent_share, lender_share) of the monthly rate.

        Stated as two numbers in the document on purpose -- each party is
        invoiced separately for their own share, never one billing the other.
        """
        total = self._rate(data)
        pct = data.lender_share_pct
        if not pct:
            pct = float(self._board.get("lender_cosponsor", {})
                        .get("default_lender_share_pct", 0))
        lender = round(total * pct / 100.0, 2)
        return total - lender, lender

    def _brand_label(self, data) -> str:
        """How to refer to whoever's brand is on the board."""
        if data.board_mode == "brokerage":
            return data.brokerage_name or data.business_name
        return data.business_name

    # ------------------------------------------------------------------
    # Prompt variables
    # ------------------------------------------------------------------

    def get_prompt_variables(self, data) -> dict:
        # Base pipeline calls this before get_sections(), so this is where
        # the mode gets latched for section selection.
        self._mode = data.board_mode

        rep = get_team_member(self.config, data.sales_rep)

        market_details = []
        for market_name in data.selected_markets:
            market = self.config["markets"].get(market_name, {})
            market_details.append(f"{market_name} ({market.get('screens', 0)} screens)")

        if data.board_mode == "brokerage":
            audience_line = "brokerage"
            seller_noun = "brokerage"
        elif data.board_mode == "lender":
            audience_line = "lender"
            seller_noun = "lender"
        else:
            audience_line = "agent"
            seller_noun = "agent"

        return {
            "business_name": data.business_name,
            "contact_name": data.contact_name,
            "brokerage_name": data.brokerage_name or data.business_name,
            "city": data.city,
            "selected_markets": ", ".join(market_details),
            "board_mode": MODE_LABELS.get(data.board_mode, "Board"),
            "audience_line": audience_line,
            "seller_noun": seller_noun,
            "listing_count": str(self._listings(data)),
            "screens": str(self._screens(data)),
            "lender_name": data.lender_name or "the lender",
            "sales_rep": rep["name"],
            "additional_notes": data.additional_notes or "No additional notes.",
        }

    # ------------------------------------------------------------------
    # Cover
    # ------------------------------------------------------------------

    def _build_cover(self, doc, data):
        rep = get_team_member(self.config, data.sales_rep)
        self.docx.preparer_name = rep["name"]
        client_logo = getattr(self.docx, "client_logo_path", None)

        if data.board_mode == "cosponsor" and data.lender_name:
            subtitle = f"{data.business_name.upper()} + {data.lender_name.upper()}"
        elif data.board_mode == "brokerage" and data.brokerage_name:
            subtitle = data.brokerage_name.upper()
        else:
            subtitle = data.business_name.upper()

        self.docx.add_cover_page(
            doc,
            title="Real Estate\nFeeds Board",
            subtitle=subtitle,
            prepared_for=f"{data.contact_name} — {data.business_name}",
            prepared_by=rep,
            client_logo_path=client_logo,
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def build_section(self, doc, section_key, data, content):
        if section_key == "opportunity":
            self._build_opportunity(doc, data, content)
        elif section_key == "_anatomy":
            self._build_anatomy(doc, data)
        elif section_key == "board_value":
            self._build_board_value(doc, content)
        elif section_key == "_market_coverage":
            self._build_market_coverage(doc, data)
        elif section_key == "_pricing":
            self._build_pricing(doc, data)
        elif section_key == "_compliance":
            self._build_compliance(doc, data)
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

    def _build_opportunity(self, doc, data, content):
        self.docx.add_section_header(doc, "The Opportunity")

        parts = re.split(r'\n\s*-\s*', content, maxsplit=1)
        if len(parts) == 2:
            self.docx.add_body_text(doc, parts[0].strip())
            for bullet in re.split(r'\n\s*-\s*', parts[1]):
                bullet = bullet.strip()
                if not bullet:
                    continue
                match = re.match(r'^(.+?)(?::|--)\s+(.+)$', bullet)
                if match:
                    self.docx.add_selling_point(doc, match.group(1).strip(),
                                                match.group(2).strip())
                else:
                    self.docx.add_selling_point(doc, bullet, "")
        elif content:
            self.docx.add_body_text(doc, content)

        network = self.config["network"]
        self.docx.add_metrics_banner(doc, {
            str(self._screens(data)): "Screens\nRunning Your Board",
            str(self._listings(data)): "Listings\nIn Rotation",
            f"{network['avg_dwell_time_minutes']}+ Min": "Avg. Dwell\nTime",
            network["monthly_impressions"]: "Network Monthly\nImpressions",
        })

    def _build_anatomy(self, doc, data):
        """Config-driven walkthrough of what the board actually displays."""
        self.docx.add_section_header(doc, "What's On The Board", new_page=True)

        brand = self._brand_label(data)
        self.docx.add_body_text(
            doc,
            f"This is not a flyer on a screen. It is a board built to be read "
            f"from across a room in the few seconds someone looks up. "
            f"{brand} holds the top of every frame. Listings rotate through "
            f"one at a time so each one gets read instead of competing with "
            f"three others. The rate strip stays put."
        )

        for title, body in self._board.get("board_features", []):
            self.docx.add_selling_point(doc, title, body)

        if data.show_rate_strip:
            strip = self._board.get("rate_strip", {})
            self.docx.add_sub_header(doc, "THE RATE STRIP")
            self.docx.add_body_text(doc, strip.get("note", ""))
            self.docx.add_callout_box(
                doc,
                f"{strip.get('source_name', '')}  |  "
                f"{strip.get('cadence', '')}  |  "
                f"Source and date shown on screen\n"
                f"{self._board.get('staleness_promise', '')}"
            )

        self.docx.add_sub_header(doc, "KEEPING IT CURRENT")
        self.docx.add_body_text(doc, self._board.get("listing_refresh", ""))

    def _build_board_value(self, doc, content):
        self.docx.add_section_header(doc, "Why This Format Works")

        for line in content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            match = re.match(r'^-\s+(.+?)(?::|--)\s+(.+)$', line)
            if match:
                self.docx.add_accent_card(doc, match.group(1).strip(),
                                          match.group(2).strip())
            else:
                clean = line.lstrip('- ').strip()
                if clean:
                    self.docx.add_body_text(doc, clean)

    def _build_market_coverage(self, doc, data):
        self.docx.add_section_header(doc, "Where Your Board Plays", new_page=True)

        self.docx.add_body_text(
            doc,
            "Your board runs in the rooms where people sit still long enough "
            "to read it — waiting rooms, salons, gyms, and coffee shops. "
            "That is the whole reason a rate strip works here and would not "
            "work on a highway billboard."
        )

        markets = self.config["markets"]
        total_screens = 0
        for market_name in data.selected_markets:
            market_data = markets.get(market_name, {})
            screens = market_data.get("screens", 0)
            total_screens += screens
            self.docx.add_sub_header(doc, f"{market_name.upper()} — {screens} SCREENS")
            self.docx.add_body_text(doc, market_data.get("description", ""))

        if data.include_exclusivity:
            self.docx.add_sub_header(doc, "CATEGORY EXCLUSIVITY")
            self.docx.add_body_text(
                doc,
                f"{self._brand_label(data)} owns the {data.exclusive_category} "
                f"category across {total_screens} screens in "
                f"{', '.join(data.selected_markets)}. No competing "
                f"{data.exclusive_category.lower()} business can buy a board, a "
                f"slot, or a single frame in these markets while this agreement "
                f"is active."
            )

        self.docx.add_callout_box(
            doc,
            "Your board plays in: Medical & Dental  |  Salons & Barbershops  |  "
            "Gyms & Fitness  |  Coffee & Restaurants  |  Auto & Service  |  "
            "Retail & Boutiques  |  Community Venues"
        )

    def _build_pricing(self, doc, data):
        self.docx.add_section_header(doc, "Investment", new_page=True)

        tier = self._tier(data)
        screens = self._screens(data)
        rate = self._rate(data)

        self.docx.add_body_text(
            doc,
            "The board prices above a standard advertising slot for one "
            "reason: the content does not sit still. Listings turn over, the "
            "rate strip refreshes, and the board is current every week "
            "without a creative request or a re-design fee."
        )

        self.docx.add_sub_header(doc, f"YOUR PACKAGE — {tier.get('name', 'BOARD').upper()}")
        self.docx.add_body_text(doc, tier.get("description", ""))

        plays_per_hour = self.config["network"]["plays_per_hour"]
        monthly_plays = (plays_per_hour * get_hours_per_day(self.config)
                         * get_days_per_month(self.config) * screens)
        impressions = get_tier_impressions(self.config, screens)
        cpm = calculate_cpm(rate, impressions)

        metrics = {
            f"${rate:,.0f}/mo": "Board Rate",
            str(screens): "Screens",
            str(self._listings(data)): "Listings",
        }
        metrics[f"${cpm:.2f}" if cpm > 0 else f"{monthly_plays:,}"] = (
            "CPM" if cpm > 0 else "Monthly\nAd Plays"
        )
        self.docx.add_metrics_banner(doc, metrics)

        if data.include_exclusivity and not data.monthly_rate:
            premium = self._board.get("exclusivity_premium_pct", 0)
            self.docx.add_body_text(
                doc,
                f"This rate includes the {premium}% category exclusivity "
                f"premium. Without exclusivity the same board runs at "
                f"${float(tier.get('monthly_rate', 0)):,.0f} per month."
            )

        # Co-sponsored boards state both shares here so the split is on the
        # page before either party gets an invoice.
        if data.board_mode == "cosponsor":
            agent_share, lender_share = self._split(data)
            self.docx.add_sub_header(doc, "HOW THE COST SPLITS")
            self.docx.add_data_table(
                doc,
                ["Party", "Share of Board", "Monthly", "Invoiced By"],
                [
                    [data.business_name,
                     f"{100 - (lender_share / rate * 100 if rate else 0):.0f}%",
                     f"${agent_share:,.0f}", "MCTV — separate invoice"],
                    [data.lender_name or "Lender",
                     f"{(lender_share / rate * 100 if rate else 0):.0f}%",
                     f"${lender_share:,.0f}", "MCTV — separate invoice"],
                ],
                totals_row=["Total Board", "100%", f"${rate:,.0f}", ""],
            )
            self.docx.add_body_text(
                doc,
                "Each party signs its own agreement and receives its own "
                "invoice from MCTV for its own share. Neither party pays any "
                "portion of the other's cost, and neither is billed through "
                "the other."
            )

        if cpm > 0:
            self.docx.add_callout_box(
                doc,
                f"Your board CPM: ${cpm:.2f} per 1,000 impressions.\n"
                f"{CPM_BENCHMARK_TEXT}"
            )

        self.docx.add_sub_header(doc, "PARTNERSHIP TERMS")
        self.docx.add_contract_terms(doc, self.config)

    def _build_compliance(self, doc, data):
        """Co-sponsorship structure and lender display rules.

        Renders only for the lender modes. This is the section that keeps a
        good idea from turning into a regulatory problem -- it states the
        split, the separate invoicing, and what does and does not appear
        next to a lender's name.
        """
        self.docx.add_section_header(doc, "Co-Sponsorship & Disclosure", new_page=True)

        co = self._board.get("lender_cosponsor", {})

        if data.board_mode == "cosponsor":
            self.docx.add_body_text(doc, co.get("intro", ""))
            self.docx.add_sub_header(doc, "HOW THE ARRANGEMENT IS STRUCTURED")
            for title, body in co.get("structure_points", []):
                self.docx.add_accent_card(doc, title, body)

        self.docx.add_sub_header(doc, "HOW THE LENDER APPEARS ON THE BOARD")
        rules = list(co.get("lender_display_rules", []))
        if data.lender_nmls_id:
            rules = [r.replace("its NMLS ID", f"NMLS ID {data.lender_nmls_id}")
                     for r in rules]
        for rule in rules:
            self.docx.add_body_text(doc, f"•  {rule}")

        self.docx.add_body_text(doc, co.get("lender_display_note", ""))

        review = co.get("review_note", "")
        if review:
            self.docx.add_callout_box(doc, review)

    def _build_competitive(self, doc, data):
        self.docx.add_section_header(doc, "How MCTV Compares")
        self.docx.add_body_text(
            doc,
            "Real estate marketing budgets get pulled in a dozen directions. "
            "Here is how a board on MCTV stacks up against where that money "
            "usually goes."
        )
        screens = self._screens(data)
        rate = self._rate(data)
        impressions = get_tier_impressions(self.config, screens)
        self.docx.add_competitive_comparison(doc, rate, screens, impressions)
        self.docx.add_roi_projection(doc, rate, screens, impressions,
                                     business_name=data.business_name)

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
        self.docx.add_section_header(doc, "Let's Get Started", new_page=True)

        if content:
            self.docx.add_body_text(doc, content)
        else:
            self.docx.add_body_text(
                doc,
                f"We build the board template around {self._brand_label(data)}'s "
                f"branding, load your first {self._listings(data)} listings, and "
                f"go live. After that the listings are yours to manage — post a "
                f"new one or mark one sold and the board picks it up on its next "
                f"refresh."
            )

        rep = get_team_member(self.config, data.sales_rep)
        self.docx.add_callout_box(
            doc,
            f"{rep['name']}  |  {rep['email']}  |  {rep['phone']}  |  "
            f"MCTV Elite Advertising  |  MCTVofMS.com"
        )
