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
        """Add executive summary section with KPI grid."""
        self.docx.add_section_header(doc, "Executive Summary")

        # Build market breakdown string
        market_breakdown = self._get_market_breakdown(data)

        # Top venue
        top_venue = ""
        if data.venue_records:
            top = max(data.venue_records, key=lambda v: v.total_plays)
            top_venue = f"{top.host_name}\n({top.total_plays:,} plays)"

        # Avg plays per venue
        avg_plays = ""
        if data.venue_records:
            avg = data.total_plays // len(data.venue_records) if data.venue_records else 0
            avg_plays = f"{avg:,}"

        # Build KPI grid (first row — big numbers)
        metrics_row1 = {}
        metrics_row1[f"{data.total_plays:,}"] = "Total Campaign\nAd Plays"
        metrics_row1[str(data.total_screen_count)] = "Active\nVenues"
        if data.total_air_time:
            metrics_row1[data.total_air_time] = "Total\nScreen Time"
        if avg_plays:
            metrics_row1[avg_plays] = "Avg Plays\nPer Venue"

        self.docx.add_metrics_banner(doc, metrics_row1)

        # Summary narrative
        summary_text = (
            f"During this reporting period, {data.advertiser_name}'s campaign reached "
            f"{data.total_screen_count} venue locations with a total of "
            f"{data.total_plays:,} ad plays and {data.total_air_time} of screen time."
        )
        if market_breakdown:
            summary_text += f" {market_breakdown}"

        self.docx.add_body_text(doc, summary_text)

        # Campaign period callout
        if data.campaign_period:
            self.docx.add_callout_box(
                doc,
                f"Campaign Period: {data.campaign_period}"
            )

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
        """Add the category breakdown summary table."""
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

    def _add_insights_section(self, doc, data: TractionReportInput,
                              categories: list):
        """Generate and add AI-powered business insights."""
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

    def _add_analytics_page(self, doc, data: TractionReportInput,
                            categories: list):
        """Add the Performance Analytics page with up to 4 charts."""
        chart_paths = generate_all_charts(data, categories)
        if not chart_paths:
            return

        doc.add_page_break()
        self.docx.add_section_header(doc, "Performance Analytics")

        # Use photos_grid for 2×2 layout
        self.docx.add_photos_grid(doc, chart_paths, cols=2, max_width=3.2)

        # Cleanup temp chart files
        import os
        for path in chart_paths:
            try:
                os.unlink(path)
            except OSError:
                pass

    def _add_team_section(self, doc, data: TractionReportInput):
        """Add the Your MCTV Team closing section."""
        closing = (
            f"Thank you for your continued partnership with MCTV Elite Advertising. "
            f"We're committed to maximizing {data.advertiser_name}'s visibility "
            f"across our network."
        )
        self.docx.add_team_section(doc, closing_text=closing)

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
