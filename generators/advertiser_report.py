"""Advertiser Traction Report generator.

Generates branded Word documents showing an advertiser's campaign performance
across the MCTV network. Used for clients like Rebel Body Fitness, Paysinger
Tech, Stouts, BJ's Family Pharmacy, etc.

The report includes:
  - Branded cover page (shared design system)
  - Executive summary with KPI grid
  - Per-venue performance table with city, category, bold top performers
  - Category breakdown
  - Optional AI-generated business insights
  - Team section and footer branding
"""

import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from services.claude_service import ClaudeService
from services.docx_service import DocxService
from services.config_service import get_team_member
from services.excel_parser import format_duration
from services.chart_service import generate_all_charts
from models.report_data import TractionReportInput, VenueRecord, CategoryBreakdown

logger = logging.getLogger(__name__)


class AdvertiserReportGenerator:
    """Generates advertiser-facing traction reports as Word documents.

    These reports show an advertiser how their campaign is performing across
    the MCTV indoor digital billboard network -- total plays, screen time,
    per-venue breakdowns, and category analysis.

    Usage:
        generator = AdvertiserReportGenerator(config, claude_service, docx_service)
        report_path = generator.generate(traction_data, progress_callback=update_ui)
    """

    def __init__(self, config: dict, claude: ClaudeService, docx: DocxService):
        self.config = config
        self.claude = claude
        self.docx = docx

    def generate(self, data: TractionReportInput, progress_callback=None) -> Path:
        """Generate a complete advertiser traction report."""
        total_steps = self._count_steps(data)
        current_step = 0

        # --- Step 1: Create document ---
        doc = self.docx.create_document()
        current_step += 1
        if progress_callback:
            progress_callback("Creating document", current_step, total_steps)

        # --- Step 2: Cover page (shared design) ---
        self._add_cover_page(doc, data)
        current_step += 1
        if progress_callback:
            progress_callback("Building cover page", current_step, total_steps)

        # --- Step 3: Executive summary + KPI grid ---
        self._add_executive_summary(doc, data)
        current_step += 1
        if progress_callback:
            progress_callback("Adding executive summary", current_step, total_steps)

        # --- Step 4: Per-venue performance table ---
        doc.add_page_break()
        self._add_venue_table(doc, data)
        current_step += 1
        if progress_callback:
            progress_callback("Building venue breakdown", current_step, total_steps)

        # --- Step 5: Category breakdown (always present now with classify_venue) ---
        categories = self._build_category_breakdown(data)
        if categories:
            self._add_category_table(doc, categories, data)
            current_step += 1
            if progress_callback:
                progress_callback("Adding category analysis", current_step, total_steps)

        # --- Step 5b: Performance Analytics charts ---
        current_step += 1
        if progress_callback:
            progress_callback("Generating performance charts", current_step, total_steps)
        self._add_analytics_page(doc, data, categories)

        # --- Step 6: AI insights (if requested) ---
        if data.include_insights and self.claude:
            current_step += 1
            if progress_callback:
                progress_callback("Generating AI insights", current_step, total_steps)
            self._add_insights_section(doc, data, categories)

        # --- Step 7: Team section ---
        doc.add_page_break()
        self._add_team_section(doc, data)
        current_step += 1
        if progress_callback:
            progress_callback("Adding team section", current_step, total_steps)

        # --- Step 8: Footer ---
        self.docx.add_footer(doc, footer_text="Ad Performance Report")
        current_step += 1
        if progress_callback:
            progress_callback("Finalizing report", current_step, total_steps)

        # --- Save ---
        safe_name = self._make_safe_filename(data.advertiser_name)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"MCTV_TractionReport_{safe_name}_{date_str}.docx"
        report_path = self.docx.save_report(doc, filename)

        logger.info(
            "Advertiser traction report saved: %s (%d venues, %s total plays)",
            report_path.name, len(data.venue_records), f"{data.total_plays:,}"
        )
        return report_path

    def generate_email(self, data: TractionReportInput) -> str:
        """Generate a professional send-along email for the traction report.

        Returns the email text, or empty string if Claude is not available.
        """
        if not self.claude:
            return ""

        rep = get_team_member(self.config, data.sales_rep)
        top_venue = max(data.venue_records, key=lambda v: v.total_plays) if data.venue_records else None
        markets = sorted(set(v.city for v in data.venue_records if v.city))

        prompt_template = self.config.get("prompts", {}).get("report_email", "")
        if not prompt_template:
            # Build inline prompt if not in config
            prompt_template = (
                "Write a professional email from {sales_rep} at MCTV Elite Advertising "
                "to accompany an ad performance report for {advertiser_name}. "
                "Total plays: {total_plays}. Venues: {venue_count}. "
                "Top venue: {top_venue}. Markets: {markets}. "
                "Keep it under 150 words. Warm but professional. No markdown."
            )

        # Use Claude to fill the template
        prompt = (
            f"Write a professional email from {rep['name']} at MCTV Elite Advertising "
            f"to accompany an ad performance traction report for {data.advertiser_name}.\n\n"
            f"CAMPAIGN DATA:\n"
            f"- Total ad plays: {data.total_plays:,}\n"
            f"- Active venues: {data.total_screen_count}\n"
            f"- Total screen time: {data.total_air_time}\n"
        )
        if top_venue:
            prompt += f"- Top venue: {top_venue.host_name} ({top_venue.total_plays:,} plays)\n"
        if markets:
            prompt += f"- Markets: {', '.join(markets)}\n"
        if data.campaign_period:
            prompt += f"- Campaign period: {data.campaign_period}\n"

        prompt += (
            f"\nThe email should:\n"
            f"- Have a compelling subject line\n"
            f"- Summarize key performance numbers in 2-3 sentences\n"
            f"- Call out one standout venue with specific data\n"
            f"- Suggest a quick call to discuss next quarter's strategy\n"
            f"- Sign off with: {rep['name']}, {rep['title']}, "
            f"MCTV Elite Advertising, {rep['phone']} | {rep['email']}\n\n"
            f"Format as: Subject: [line]\\n\\n[body]\\n\\n[signature]\n"
            f"Keep under 150 words. No markdown."
        )

        try:
            return self.claude.generate_insights(prompt)
        except Exception as e:
            logger.error("Failed to generate report email: %s", e)
            return ""

    # ------------------------------------------------------------------
    # Document sections
    # ------------------------------------------------------------------

    def _add_cover_page(self, doc, data: TractionReportInput):
        """Add a branded cover page using the shared design system."""
        rep = get_team_member(self.config, data.sales_rep)
        self.docx.preparer_name = rep["name"]
        self.docx.add_cover_page(
            doc,
            title="AD TRACTION\nREPORT",
            subtitle=f"Indoor Digital Billboard Performance",
            prepared_for=data.advertiser_name,
            prepared_by=rep,
            date=data.campaign_period or datetime.now().strftime("%B %Y"),
        )

    def _add_executive_summary(self, doc, data: TractionReportInput):
        """Add executive summary section with 8-cell KPI grid + expanded narrative."""
        self.docx.add_section_header(doc, "Executive Summary")

        # Build supporting data
        market_detail = self._get_market_detail(data)
        categories = self._build_category_breakdown(data)
        num_categories = len(categories) if categories else 0

        # Top venue
        top_venue_name = ""
        top_venue_plays = 0
        if data.venue_records:
            top = max(data.venue_records, key=lambda v: v.total_plays)
            top_venue_name = top.host_name
            top_venue_plays = top.total_plays

        # Avg plays per venue
        avg_plays = data.total_plays // len(data.venue_records) if data.venue_records else 0

        # Markets covered
        markets = sorted(set(v.city for v in data.venue_records if v.city))
        markets_str = " & ".join(markets) if markets else "N/A"

        # Days active (from campaign dates)
        days_active = self._calc_days_active(data)

        # ── KPI Row 1 — Primary metrics ──
        metrics_row1 = {}
        metrics_row1[f"{data.total_plays:,}"] = "Total Campaign\nAd Plays"
        metrics_row1[str(data.total_screen_count)] = "Active\nVenues"
        if data.total_air_time:
            metrics_row1[data.total_air_time] = "Total\nScreen Time"
        metrics_row1[f"{avg_plays:,}"] = "Avg Plays\nPer Venue"
        self.docx.add_metrics_banner(doc, metrics_row1)

        # ── KPI Row 2 — Contextual metrics ──
        metrics_row2 = {}
        if top_venue_name:
            # Truncate long venue names for the KPI cell
            display_name = top_venue_name[:25] + ("..." if len(top_venue_name) > 25 else "")
            metrics_row2[display_name] = f"Top Venue\n({top_venue_plays:,} plays)"
        metrics_row2[markets_str] = "Markets\nCovered"
        if num_categories > 0:
            metrics_row2[str(num_categories)] = "Venue\nCategories"
        if days_active:
            metrics_row2[str(days_active)] = "Days\nActive"
        if metrics_row2:
            self.docx.add_metrics_banner(doc, metrics_row2)

        # ── Campaign period callout ──
        if data.campaign_period:
            self.docx.add_callout_box(
                doc,
                f"Campaign Period: {data.campaign_period}"
            )

        # ── Expanded narrative — AI-generated if Claude available, else template ──
        if self.claude:
            narrative = self._generate_exec_summary(data, market_detail, categories)
            if narrative:
                self.docx.add_body_text(doc, narrative)
            else:
                self._add_template_narrative(doc, data, market_detail, categories)
        else:
            self._add_template_narrative(doc, data, market_detail, categories)

    def _add_venue_table(self, doc, data: TractionReportInput):
        """Add the per-venue performance breakdown table."""
        self.docx.add_section_header(doc, "Performance by Venue")

        if not data.venue_records:
            self.docx.add_body_text(doc, "No venue data available for this report period.")
            return

        self.docx.add_body_text(
            doc,
            f"Your ad played across {len(data.venue_records)} venue locations during "
            f"this campaign period. The table below shows performance at each host, "
            f"sorted by total ad plays."
        )

        # Build table headers and rows — now includes City column
        headers = ["Venue", "City", "Category", "Total Plays", "Air Time", "% of Total"]

        sorted_venues = sorted(
            data.venue_records, key=lambda v: v.total_plays, reverse=True
        )

        rows = []
        for venue in sorted_venues:
            rows.append([
                venue.host_name,
                venue.city or "--",
                venue.business_category or "General",
                f"{venue.total_plays:,}",
                venue.total_air_time or "--",
                f"{venue.pct_of_total:.1f}%",
            ])

        # Totals row
        total_seconds = sum(
            _parse_air_time_to_seconds(v.total_air_time) for v in sorted_venues
        )
        totals_row = [
            "TOTAL", "", "",
            f"{data.total_plays:,}",
            format_duration(total_seconds),
            "100.0%",
        ]

        self.docx.add_data_table(doc, headers, rows,
                                 bold_rows=3, totals_row=totals_row)

    def _add_category_table(self, doc, categories: list, data: TractionReportInput):
        """Add the category breakdown summary table + market breakdown below."""
        self.docx.add_section_header(doc, "Performance by Venue Category")

        self.docx.add_body_text(
            doc,
            f"Your campaign reaches audiences across {len(categories)} distinct "
            f"business categories. This breakdown shows which venue types drive "
            f"the most ad exposure for {data.advertiser_name}."
        )

        headers = ["Category", "# Venues", "Total Plays", "% of Total"]
        sorted_cats = sorted(categories, key=lambda c: c.total_plays, reverse=True)

        rows = []
        for cat in sorted_cats:
            rows.append([
                cat.category,
                str(cat.host_count),
                f"{cat.total_plays:,}",
                f"{cat.pct_of_total:.1f}%",
            ])

        self.docx.add_data_table(doc, headers, rows)

        # ── Market Breakdown table (fills dead space below category table) ──
        market_detail = self._get_market_detail(data)
        if len(market_detail) > 1:
            self.docx.add_sub_header(doc, "PERFORMANCE BY MARKET")

            # Find top venue per market
            top_by_market = {}
            for v in data.venue_records:
                city = v.city or "Unknown"
                if city not in top_by_market or v.total_plays > top_by_market[city].total_plays:
                    top_by_market[city] = v

            mkt_headers = ["Market", "Venues", "Total Plays", "% of Total", "Top Venue"]
            mkt_rows = []
            for city, venues, plays, pct in market_detail:
                top_v = top_by_market.get(city)
                top_name = top_v.host_name[:25] if top_v else "--"
                mkt_rows.append([
                    city, str(venues), f"{plays:,}", f"{pct}%", top_name,
                ])

            self.docx.add_data_table(doc, mkt_headers, mkt_rows)

    def _add_insights_section(self, doc, data: TractionReportInput,
                              categories: list):
        """Generate and add AI-powered business insights.

        Gives insights their own full page with:
          - AI narrative (2 tight paragraphs)
          - Key Takeaways callout (3-4 bullet points)
          - Recommended Actions callout
          - Next Reporting Period line
        """
        doc.add_page_break()
        self.docx.add_section_header(doc, "What This Means for Your Business")

        # Sanity check: don't let Claude fabricate explanations for broken data
        if data.total_plays == 0 and len(data.venue_records) > 0:
            self.docx.add_body_text(
                doc,
                "Data Warning: The uploaded file contains venue records but all play "
                "counts show zero. This likely indicates a parsing issue with the "
                "Excel format. Please contact your MCTV representative for a manual "
                "review of the raw data."
            )
            return

        prompt = self._build_insights_prompt(data, categories)

        try:
            insights_text = self.claude.generate_insights(prompt)
            if insights_text:
                self.docx.add_body_text(doc, insights_text)
            else:
                logger.warning("Claude returned empty insights; skipping section content.")
                self.docx.add_body_text(
                    doc,
                    "Insights are currently being compiled. Contact your MCTV "
                    "representative for a detailed campaign analysis."
                )
        except Exception as e:
            logger.error("Failed to generate AI insights: %s", e)
            self.docx.add_body_text(
                doc,
                "Insights are currently being compiled. Contact your MCTV "
                "representative for a detailed campaign analysis."
            )

        # ── Key Takeaways ──
        takeaways = self._build_key_takeaways(data, categories)
        if takeaways:
            self.docx.add_sub_header(doc, "KEY TAKEAWAYS")
            for point in takeaways:
                self.docx.add_selling_point(doc, point[0], point[1])

        # ── Recommended Actions callout ──
        actions = self._build_recommended_actions(data)
        self.docx.add_callout_box(doc, actions)

        # ── Next Reporting Period ──
        next_period = self._get_next_period_text(data)
        if next_period:
            p = doc.add_paragraph()
            p.alignment = 1  # WD_ALIGN_PARAGRAPH.CENTER
            from docx.shared import Pt as DPt
            p.paragraph_format.space_before = DPt(12)
            p.paragraph_format.space_after = DPt(4)
            run = p.add_run(next_period)
            run.font.size = DPt(10)
            run.font.italic = True
            run.font.color.rgb = self.docx.c["accent"]

    def _add_analytics_page(self, doc, data: TractionReportInput,
                            categories: list):
        """Add the Performance Analytics page with up to 4 charts."""
        chart_paths = generate_all_charts(data, categories)
        if not chart_paths:
            return

        doc.add_page_break()
        self.docx.add_section_header(doc, "Performance Analytics")

        # Use photos_grid for 2×2 layout
        self.docx.add_photos_grid(doc, chart_paths, cols=2, max_width=3.5)

        # Cleanup temp chart files
        import os
        for path in chart_paths:
            try:
                os.unlink(path)
            except OSError:
                pass

    def _add_team_section(self, doc, data: TractionReportInput):
        """Add the Your MCTV Team closing section with dark navy background."""
        closing = (
            f"Thank you for your continued partnership with MCTV Elite Advertising. "
            f"We're committed to maximizing {data.advertiser_name}'s visibility "
            f"across our network."
        )
        self.docx.add_team_section(doc, closing_text=closing, dark_mode=True)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _get_market_breakdown(self, data: TractionReportInput) -> str:
        """Build a market breakdown string from venue cities."""
        market_counts = defaultdict(lambda: {"venues": 0, "plays": 0})
        for v in data.venue_records:
            city = v.city or "Unknown"
            market_counts[city]["venues"] += 1
            market_counts[city]["plays"] += v.total_plays

        if len(market_counts) <= 1:
            return ""

        parts = []
        for city, stats in sorted(market_counts.items(),
                                   key=lambda x: x[1]["plays"], reverse=True):
            pct = (stats["plays"] / data.total_plays * 100) if data.total_plays > 0 else 0
            parts.append(f"{city}: {pct:.1f}%")

        return "Market breakdown: " + " | ".join(parts) + "."

    def _get_market_detail(self, data: TractionReportInput) -> list:
        """Build detailed market breakdown: [(city, venues, plays, pct), ...]."""
        market_counts = defaultdict(lambda: {"venues": 0, "plays": 0})
        for v in data.venue_records:
            city = v.city or "Unknown"
            market_counts[city]["venues"] += 1
            market_counts[city]["plays"] += v.total_plays

        result = []
        for city, stats in sorted(market_counts.items(),
                                   key=lambda x: x[1]["plays"], reverse=True):
            pct = (stats["plays"] / data.total_plays * 100) if data.total_plays > 0 else 0
            result.append((city, stats["venues"], stats["plays"], round(pct, 1)))
        return result

    def _calc_days_active(self, data: TractionReportInput) -> int:
        """Calculate days between campaign start and end dates."""
        from datetime import datetime as dt
        start = data.campaign_start or ""
        end = data.campaign_end or ""
        if not start or not end:
            return 0
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"):
            try:
                d1 = dt.strptime(start[:10], fmt)
                d2 = dt.strptime(end[:10], fmt)
                return max((d2 - d1).days, 1)
            except (ValueError, IndexError):
                continue
        return 0

    def _generate_exec_summary(self, data: TractionReportInput,
                                market_detail: list,
                                categories: list) -> str:
        """Use Claude to generate a 2-3 paragraph executive summary narrative."""
        top_venues = sorted(
            data.venue_records, key=lambda v: v.total_plays, reverse=True
        )[:3]
        top_str = ", ".join(
            f"{v.host_name} ({v.total_plays:,} plays)" for v in top_venues
        )

        market_str = ""
        if len(market_detail) > 1:
            market_str = ". ".join(
                f"{city}: {venues} venues, {pct}% of plays"
                for city, venues, plays, pct in market_detail
            )

        cat_str = ""
        if categories:
            sorted_cats = sorted(categories, key=lambda c: c.total_plays, reverse=True)[:3]
            cat_str = ", ".join(f"{c.category} ({c.pct_of_total}%)" for c in sorted_cats)

        prompt = (
            f"Write a 2-3 paragraph executive summary for {data.advertiser_name}'s "
            f"indoor digital billboard advertising campaign report.\n\n"
            f"Key data:\n"
            f"  - Total ad plays: {data.total_plays:,}\n"
            f"  - Active venues: {data.total_screen_count}\n"
            f"  - Total screen time: {data.total_air_time}\n"
        )
        if market_str:
            prompt += f"  - Market breakdown: {market_str}\n"
        prompt += f"  - Top performers: {top_str}\n"
        if cat_str:
            prompt += f"  - Leading categories: {cat_str}\n"

        prompt += (
            f"\nParagraph 1: Headline the overall campaign performance — total plays, "
            f"venues reached, screen time. Make it feel like a win.\n"
            f"Paragraph 2: Break down the market and category performance. "
            f"Name specific venues and cities. Be data-specific.\n"
            f"Paragraph 3: Forward-looking recommendation — suggest continuing or "
            f"expanding, reference upcoming seasonal opportunities.\n\n"
            f"Rules: No markdown, no bullet points, no headers. Just flowing paragraphs. "
            f"Professional but warm tone. Keep under 200 words total."
        )

        try:
            return self.claude.generate_insights(prompt)
        except Exception as e:
            logger.warning("Failed to generate exec summary: %s", e)
            return ""

    def _add_template_narrative(self, doc, data: TractionReportInput,
                                 market_detail: list, categories: list):
        """Add a template-based executive summary when Claude is not available."""
        # Paragraph 1: Overview
        text = (
            f"During this reporting period, {data.advertiser_name}'s campaign reached "
            f"{data.total_screen_count} venue locations across the MCTV network with a "
            f"total of {data.total_plays:,} ad plays and {data.total_air_time} of "
            f"screen time."
        )

        # Paragraph 2: Market breakdown
        if len(market_detail) > 1:
            market_parts = []
            for city, venues, plays, pct in market_detail:
                market_parts.append(f"{city} ({venues} venues, {pct}% of plays)")
            text += (
                f"\n\nYour campaign is active across {len(market_detail)} markets: "
                + ", ".join(market_parts) + "."
            )

        # Top performers
        if data.venue_records:
            top3 = sorted(data.venue_records, key=lambda v: v.total_plays, reverse=True)[:3]
            top_str = ", ".join(
                f"{v.host_name} ({v.total_plays:,} plays)" for v in top3
            )
            text += f" Top performing venues include {top_str}."

        # Category insight
        if categories:
            sorted_cats = sorted(categories, key=lambda c: c.total_plays, reverse=True)[:2]
            cat_str = " and ".join(c.category for c in sorted_cats)
            text += (
                f"\n\nYour ads are reaching audiences across {len(categories)} distinct "
                f"venue categories, with {cat_str} leading in total ad exposure. "
                f"This diverse reach ensures your brand connects with customers in "
                f"multiple environments throughout their daily routines."
            )

        self.docx.add_body_text(doc, text)

    def _build_key_takeaways(self, data: TractionReportInput,
                              categories: list) -> list:
        """Build 3-4 key takeaway (title, description) pairs from the data."""
        takeaways = []
        if data.venue_records:
            top = max(data.venue_records, key=lambda v: v.total_plays)
            takeaways.append((
                "Top Performer",
                f"{top.host_name} leads with {top.total_plays:,} ad plays"
                + (f" in {top.city}" if top.city else "") + "."
            ))

        markets = sorted(set(v.city for v in data.venue_records if v.city))
        if len(markets) > 1:
            takeaways.append((
                "Multi-Market Reach",
                f"Your campaign is active across {len(markets)} markets: "
                + ", ".join(markets) + "."
            ))

        if categories:
            sorted_cats = sorted(categories, key=lambda c: c.total_plays, reverse=True)
            takeaways.append((
                "Category Diversity",
                f"Ads reach {len(categories)} venue categories — "
                f"{sorted_cats[0].category} leads at {sorted_cats[0].pct_of_total}% of plays."
            ))

        avg = data.total_plays // len(data.venue_records) if data.venue_records else 0
        if avg > 0:
            takeaways.append((
                "Network Consistency",
                f"Your ad averages {avg:,} plays per venue, showing strong "
                f"distribution across the network."
            ))

        return takeaways[:4]

    def _build_recommended_actions(self, data: TractionReportInput) -> str:
        """Build a recommended actions text block."""
        return (
            f"Recommended Next Steps: Continue the current campaign to build on "
            f"{data.advertiser_name}'s momentum. Consider a quarterly content refresh "
            f"to keep your ad creative seasonal and relevant — this is included at no "
            f"extra charge. Contact your MCTV representative to discuss expanding into "
            f"additional markets or upgrading your screen count."
        )

    def _get_next_period_text(self, data: TractionReportInput) -> str:
        """Generate a 'Next Reporting Period' line."""
        from datetime import datetime as dt, timedelta
        end = data.campaign_end or ""
        if not end:
            return ""
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                end_date = dt.strptime(end[:10], fmt)
                next_start = end_date + timedelta(days=1)
                next_end = next_start + timedelta(days=29)
                return (
                    f"Next Reporting Period: "
                    f"{next_start.strftime('%B %d')} \u2013 "
                    f"{next_end.strftime('%B %d, %Y')}"
                )
            except (ValueError, IndexError):
                continue
        return ""

    def _build_category_breakdown(self, data: TractionReportInput) -> list:
        """Group venue records by business_category and compute aggregates."""
        has_categories = any(
            v.business_category and v.business_category.strip()
            and v.business_category != "General"
            for v in data.venue_records
        )
        if not has_categories:
            return []

        cat_data = defaultdict(lambda: {"hosts": set(), "total_plays": 0})
        for venue in data.venue_records:
            category = venue.business_category.strip() if venue.business_category else "General"
            cat_data[category]["hosts"].add(venue.host_name)
            cat_data[category]["total_plays"] += venue.total_plays

        total_plays = data.total_plays if data.total_plays > 0 else 1

        categories = []
        for cat_name, agg in cat_data.items():
            pct = (agg["total_plays"] / total_plays) * 100
            categories.append(CategoryBreakdown(
                category=cat_name,
                host_count=len(agg["hosts"]),
                total_plays=agg["total_plays"],
                pct_of_total=round(pct, 1),
            ))

        return categories

    def _build_insights_prompt(self, data: TractionReportInput,
                               categories: list) -> str:
        """Build a detailed prompt for Claude to generate campaign insights."""
        top_venues = sorted(
            data.venue_records, key=lambda v: v.total_plays, reverse=True
        )[:5]
        venue_summary = "\n".join(
            f"  - {v.host_name} ({v.business_category or 'General'}, {v.city or 'N/A'}): "
            f"{v.total_plays:,} plays, {v.total_air_time}"
            for v in top_venues
        )

        category_summary = ""
        if categories:
            sorted_cats = sorted(categories, key=lambda c: c.total_plays, reverse=True)
            category_summary = "\n".join(
                f"  - {c.category}: {c.host_count} venues, {c.total_plays:,} plays ({c.pct_of_total}%)"
                for c in sorted_cats
            )

        # Market breakdown for prompt
        market_info = self._get_market_breakdown(data)

        prompt = (
            f"You are writing a business insights section for an indoor digital billboard "
            f"advertising traction report. The advertiser is {data.advertiser_name}.\n\n"
            f"Campaign Summary:\n"
            f"  - Total Ad Plays: {data.total_plays:,}\n"
            f"  - Active Venues: {data.total_screen_count}\n"
            f"  - Total Screen Time: {data.total_air_time}\n"
        )

        if market_info:
            prompt += f"  - {market_info}\n"

        if data.total_impressions and data.total_impressions > 0:
            prompt += f"  - Est. Monthly Impressions: {self._format_large_number(data.total_impressions)}\n"
        if data.avg_dwell_time and data.avg_dwell_time > 0:
            prompt += f"  - Avg. Dwell Time: {data.avg_dwell_time:.0f} minutes\n"

        prompt += f"\nTop 5 Venues by Ad Plays:\n{venue_summary}\n"

        if category_summary:
            prompt += f"\nPerformance by Category:\n{category_summary}\n"

        prompt += (
            f"\nWrite 2-3 concise paragraphs explaining what these numbers mean for "
            f"{data.advertiser_name}'s business. Highlight which venue types are "
            f"delivering the most exposure, note any standout performers, and give a "
            f"brief actionable recommendation. Keep the tone professional but warm -- "
            f"this is a partner update, not a sales pitch. Do not use bullet points or "
            f"headers -- just flowing paragraphs."
        )

        return prompt

    def _count_steps(self, data: TractionReportInput) -> int:
        """Count total generation steps for progress reporting."""
        steps = 4  # create doc, cover page, executive summary, venue table
        # Category breakdown
        has_categories = any(
            v.business_category and v.business_category.strip()
            and v.business_category != "General"
            for v in data.venue_records
        )
        if has_categories:
            steps += 1
        # Charts page
        steps += 1
        # AI insights
        if data.include_insights and self.claude:
            steps += 1
        # Team section + footer
        steps += 2
        return steps

    @staticmethod
    def _format_large_number(value: float) -> str:
        """Format a large number for display (e.g., 1900000 -> '1.9M+')."""
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M+"
        elif value >= 1_000:
            return f"{value / 1_000:.0f}K+"
        else:
            return f"{value:,.0f}"

    @staticmethod
    def _make_safe_filename(name: str) -> str:
        """Convert a business name to a filesystem-safe string."""
        safe = name.strip()
        for char in r' /\:*?"<>|':
            safe = safe.replace(char, "_")
        safe = safe.replace("'", "")
        while "__" in safe:
            safe = safe.replace("__", "_")
        return safe.strip("_")


def _parse_air_time_to_seconds(air_time_str: str) -> int:
    """Parse an air time string like '5h 12m' back to total seconds."""
    import re
    if not air_time_str:
        return 0
    hours = minutes = 0
    h_match = re.search(r"(\d[\d,]*)h", air_time_str.replace(",", ""))
    m_match = re.search(r"(\d+)m", air_time_str)
    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))
    return hours * 3600 + minutes * 60
