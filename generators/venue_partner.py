"""Venue Partner / Revenue Share proposal generator.

Generates a proposal for high-traffic venues (airports, hospitals, arenas)
where MCTV installs screens at no cost and shares advertising revenue with
the venue owner.
"""

from generators.base_proposal import BaseProposal
from services.config_service import get_team_member
from services.docx_service import NAVY, GOLD, GRAY, Pt, WD_ALIGN_PARAGRAPH


class VenuePartnerProposal(BaseProposal):
    """Generates a Venue Partner / Revenue Share proposal."""

    @property
    def proposal_type_key(self) -> str:
        return "venue_partner"

    def get_sections(self) -> list:
        return [
            ("opportunity", "The Opportunity"),
            ("what_mctv_provides", "What MCTV Provides"),
            ("revenue_model", "Revenue Model"),
            ("_revenue_projection", "Revenue Projections"),
            ("_partnership_terms", "Partnership Terms"),
            ("getting_started", "Let's Get Started"),
            ("_team", "Meet Your Team"),
        ]

    def get_prompt_variables(self, data) -> dict:
        rep = get_team_member(self.config, data.sales_rep)
        return {
            "venue_name": data.venue_name,
            "contact_name": data.contact_name,
            "venue_type": data.venue_type,
            "city": data.city,
            "screen_count": data.proposed_screen_count,
            "monthly_traffic": f"{data.estimated_monthly_traffic:,}" if data.estimated_monthly_traffic else "N/A",
            "revenue_pct": data.revenue_split_pct,
            "premium_slot_rate": data.premium_slot_rate,
            "standard_slot_rate": data.standard_slot_rate,
            "sales_rep": rep["name"],
            "additional_notes": data.additional_notes or "No additional notes.",
        }

    def _build_cover(self, doc, input_data):
        """Build cover page for venue partnership."""
        rep = get_team_member(self.config, input_data.sales_rep)
        self.docx.add_cover_page(
            doc,
            title="Venue\nPartnership",
            subtitle="REVENUE SHARE PROPOSAL",
            prepared_for=f"{input_data.contact_name} \u2014 {input_data.venue_name}",
            prepared_by=rep,
        )

    def build_section(self, doc, section_key, data, content):
        if section_key == "opportunity":
            self._build_opportunity(doc, data, content)
        elif section_key == "what_mctv_provides":
            self._build_what_mctv_provides(doc, content)
        elif section_key == "revenue_model":
            self._build_revenue_model(doc, content)
        elif section_key == "_revenue_projection":
            self._build_revenue_projection(doc, data)
        elif section_key == "_partnership_terms":
            self._build_partnership_terms(doc, data)
        elif section_key == "getting_started":
            self._build_getting_started(doc, data, content)
        elif section_key == "_team":
            self.docx.add_team_section(doc)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_opportunity(self, doc, data, content):
        """The Opportunity section with venue-specific metrics."""
        self.docx.add_section_header(doc, "The Opportunity")
        self.docx.add_body_text(doc, content)

        metrics = {
            f"{data.proposed_screen_count}": "Screens\nInstalled",
            f"{data.estimated_monthly_traffic:,}" if data.estimated_monthly_traffic else "High": "Est. Monthly\nVisitors",
            f"{data.revenue_split_pct}%": "Your Revenue\nShare",
            "$0": "Your Cost\nto Participate",
        }
        self.docx.add_metrics_banner(doc, metrics)
        doc.add_page_break()

    def _build_what_mctv_provides(self, doc, content):
        """Claude-generated section describing what MCTV provides."""
        self.docx.add_section_header(doc, "What MCTV Provides")
        self.docx.add_body_text(doc, content)
        doc.add_page_break()

    def _build_revenue_model(self, doc, content):
        """Claude-generated revenue model explanation."""
        self.docx.add_section_header(doc, "Revenue Model")
        self.docx.add_body_text(doc, content)
        doc.add_page_break()

    def _build_revenue_projection(self, doc, data):
        """Config-driven revenue projection table at different fill levels.

        Shows projected monthly and annual revenue for the venue at 50%, 75%,
        and 100% advertising slot fill rates across both premium and standard
        slot types.
        """
        self.docx.add_section_header(doc, "Revenue Projections")

        self.docx.add_body_text(
            doc,
            f"The table below projects {data.venue_name}'s share of advertising "
            f"revenue based on {data.proposed_screen_count} screens at different "
            f"fill rates. As the network matures and demand grows, fill rates "
            f"increase \u2014 and so does your revenue."
        )

        # Each screen has ad slots. We model total ad inventory as:
        # screens * slots_per_screen. For simplicity, assume each screen
        # can hold approximately 3 premium slots and 5 standard slots.
        premium_slots_per_screen = 3
        standard_slots_per_screen = 5
        total_premium_slots = data.proposed_screen_count * premium_slots_per_screen
        total_standard_slots = data.proposed_screen_count * standard_slots_per_screen

        fill_levels = [0.50, 0.75, 1.00]

        headers = [
            "Fill Rate",
            "Premium Slots Sold",
            "Standard Slots Sold",
            "Gross Monthly Revenue",
            f"Your Share ({data.revenue_split_pct}%)",
            "Annual Revenue",
        ]

        rows = []
        for fill in fill_levels:
            premium_sold = int(total_premium_slots * fill)
            standard_sold = int(total_standard_slots * fill)
            gross_monthly = (premium_sold * data.premium_slot_rate) + (standard_sold * data.standard_slot_rate)
            venue_monthly = gross_monthly * (data.revenue_split_pct / 100.0)
            venue_annual = venue_monthly * 12

            rows.append([
                f"{int(fill * 100)}%",
                f"{premium_sold} of {total_premium_slots}",
                f"{standard_sold} of {total_standard_slots}",
                f"${gross_monthly:,.0f}",
                f"${venue_monthly:,.0f}/mo",
                f"${venue_annual:,.0f}/yr",
            ])

        self.docx.add_data_table(doc, headers, rows)

        self.docx.add_sub_header(doc, "RATE ASSUMPTIONS")
        self.docx.add_body_text(
            doc,
            f"Premium advertising slots: ${data.premium_slot_rate:,.0f} per slot/month. "
            f"Standard advertising slots: ${data.standard_slot_rate:,.0f} per slot/month. "
            f"Rates are subject to advertiser demand and may increase as the network grows."
        )
        doc.add_page_break()

    def _build_partnership_terms(self, doc, data):
        """Config-driven partnership terms for venue deals."""
        self.docx.add_section_header(doc, "Partnership Terms")

        terms_items = [
            ("Installation", f"MCTV installs {data.proposed_screen_count} commercial-grade "
                             f"digital screens at {data.venue_name} at no cost to you."),
            ("Content Management", "MCTV manages all screen content including entertainment "
                                   "(weather, news, sports, trivia) and advertiser creative."),
            ("Revenue Share", f"{data.venue_name} receives {data.revenue_split_pct}% of all "
                              f"advertising revenue generated from screens at your location."),
            ("Payment Schedule", "Revenue share payments are issued monthly, accompanied by "
                                 "a detailed report of advertising activity and earnings."),
            ("Maintenance", "MCTV is responsible for all hardware maintenance, software updates, "
                            "and content management. The venue provides wall space and power."),
            ("Agreement Term", "Initial partnership term of 24 months, with automatic renewal "
                               "unless either party provides 60 days written notice."),
            ("Exclusivity", f"MCTV retains exclusive rights to sell advertising on screens "
                            f"installed at {data.venue_name} during the partnership term."),
        ]

        for title, description in terms_items:
            self.docx.add_bullet_point(doc, title, description)

        doc.add_page_break()

    def _build_getting_started(self, doc, data, content):
        """Getting Started section with contact card."""
        self.docx.add_section_header(doc, "Let's Get Started")

        # If Claude generated content, use it; otherwise provide a default
        if content:
            self.docx.add_body_text(doc, content)
        else:
            self.docx.add_body_text(
                doc,
                f"{data.venue_name} is exactly the kind of high-traffic venue that "
                f"makes the MCTV network powerful for advertisers \u2014 and profitable "
                f"for you. We handle everything: hardware, installation, content, and "
                f"ad sales. You provide the space and share in the revenue."
            )
            self.docx.add_body_text(
                doc,
                "The next step is a brief site visit to finalize screen placement, "
                "followed by a simple partnership agreement. From there, your screens "
                "can be installed and generating revenue within 2-3 weeks."
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
