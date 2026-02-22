"""Advertiser Traction Report generator.

Generates branded Word documents showing an advertiser's campaign performance
across the MCTV network. Used for clients like Rebel Body Fitness, Paysinger
Tech, Stouts, BJ's Family Pharmacy, etc.

The report includes summary metrics, per-venue breakdowns, category analysis,
and optional AI-generated business insights.
"""

import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from services.claude_service import ClaudeService
from services.docx_service import DocxService, NAVY, GOLD, GRAY, DARK_TEXT
from services.config_service import get_team_member
from models.report_data import TractionReportInput, VenueRecord, CategoryBreakdown

from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

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
        """Initialize the advertiser report generator.

        Args:
            config: Master application config dict (from config.json).
            claude: ClaudeService instance for AI-generated insights.
            docx: DocxService instance for document creation and formatting.
        """
        self.config = config
        self.claude = claude
        self.docx = docx

    def generate(self, data: TractionReportInput, progress_callback=None) -> Path:
        """Generate a complete advertiser traction report.

        Builds a branded Word document with campaign summary metrics,
        per-venue performance table, category breakdown, optional AI
        insights, and MCTV footer branding.

        Args:
            data: TractionReportInput populated with campaign data.
            progress_callback: Optional callable(section_name, step, total)
                               for UI progress updates.

        Returns:
            Path to the saved .docx report file.
        """
        total_steps = self._count_steps(data)
        current_step = 0

        # --- Step 1: Create document ---
        doc = self.docx.create_document()
        current_step += 1
        if progress_callback:
            progress_callback("Creating document", current_step, total_steps)

        # --- Step 2: Title and subtitle ---
        self._add_title_block(doc, data)
        current_step += 1
        if progress_callback:
            progress_callback("Adding report header", current_step, total_steps)

        # --- Step 3: Summary metrics banner ---
        self._add_summary_metrics(doc, data)
        current_step += 1
        if progress_callback:
            progress_callback("Adding summary metrics", current_step, total_steps)

        # --- Step 4: Per-venue performance table ---
        self._add_venue_table(doc, data)
        current_step += 1
        if progress_callback:
            progress_callback("Building venue breakdown", current_step, total_steps)

        # --- Step 5: Category breakdown (if categories exist) ---
        categories = self._build_category_breakdown(data)
        if categories:
            self._add_category_table(doc, categories, data)
            current_step += 1
            if progress_callback:
                progress_callback("Adding category analysis", current_step, total_steps)

        # --- Step 6: AI insights (if requested) ---
        if data.include_insights:
            current_step += 1
            if progress_callback:
                progress_callback("Generating AI insights", current_step, total_steps)
            self._add_insights_section(doc, data, categories)

        # --- Step 7: Footer ---
        self.docx.add_footer(doc)
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

    def _add_title_block(self, doc, data: TractionReportInput):
        """Add the report title, advertiser name, and campaign period."""
        # MCTV branding header
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("MCTV ELITE ADVERTISING")
        run.font.size = Pt(12)
        run.font.color.rgb = GOLD
        run.font.bold = True
        run.font.name = "Calibri"

        # Spacer
        doc.add_paragraph()

        # Report title
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"{data.advertiser_name}")
        run.font.size = Pt(28)
        run.font.color.rgb = NAVY
        run.font.bold = True
        run.font.name = "Calibri"

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("Indoor Digital Billboard Ad Traction Report")
        run.font.size = Pt(16)
        run.font.color.rgb = NAVY
        run.font.bold = False
        run.font.name = "Calibri"

        # Campaign period and network
        doc.add_paragraph()
        subtitle_parts = []
        if data.campaign_period:
            subtitle_parts.append(f"Campaign Period: {data.campaign_period}")
        if data.network_name:
            subtitle_parts.append(f"Network: {data.network_name}")

        if subtitle_parts:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run("  |  ".join(subtitle_parts))
            run.font.size = Pt(11)
            run.font.color.rgb = GRAY
            run.font.name = "Calibri"

        # Report generation date
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"Generated {datetime.now().strftime('%B %d, %Y')}")
        run.font.size = Pt(10)
        run.font.color.rgb = GRAY
        run.font.italic = True

        # Divider
        doc.add_paragraph()

    def _add_summary_metrics(self, doc, data: TractionReportInput):
        """Add the large summary metrics banner at the top of the report."""
        self.docx.add_section_header(doc, "Campaign Performance Summary")

        # Build metrics dict -- keys are the display values, values are labels
        # (this matches the add_metrics_banner API where dict key = value, dict value = label)
        metrics = {}

        # Total ad plays
        metrics[f"{data.total_plays:,}"] = "Total Campaign\nAd Plays"

        # Active venues / screens
        metrics[str(data.total_screen_count)] = "Active\nVenues"

        # Total screen time
        if data.total_air_time:
            metrics[data.total_air_time] = "Total\nScreen Time"

        # Estimated monthly impressions (if available)
        if data.total_impressions and data.total_impressions > 0:
            impressions_display = self._format_large_number(data.total_impressions)
            metrics[impressions_display] = "Est. Monthly\nImpressions"

        # Average dwell time (if available)
        if data.avg_dwell_time and data.avg_dwell_time > 0:
            metrics[f"{data.avg_dwell_time:.0f} min"] = "Avg. Dwell Time\nPer Visit"

        self.docx.add_metrics_banner(doc, metrics)

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

        # Build table headers and rows
        headers = ["Host Location", "Category", "Total Plays", "Air Time", "% of Total"]

        # Sort venue records by total plays descending
        sorted_venues = sorted(
            data.venue_records, key=lambda v: v.total_plays, reverse=True
        )

        rows = []
        for venue in sorted_venues:
            rows.append([
                venue.host_name,
                venue.business_category or "General",
                f"{venue.total_plays:,}",
                venue.total_air_time or "--",
                f"{venue.pct_of_total:.1f}%",
            ])

        self.docx.add_data_table(doc, headers, rows)

    def _add_category_table(self, doc, categories: list, data: TractionReportInput):
        """Add the category breakdown summary table."""
        self.docx.add_section_header(doc, "Performance by Venue Category")

        self.docx.add_body_text(
            doc,
            f"Your campaign reaches audiences across {len(categories)} distinct "
            f"business categories. This breakdown shows which venue types drive "
            f"the most ad exposure for {data.advertiser_name}."
        )

        headers = ["Category", "# Hosts", "Total Plays", "% of Total"]

        # Sort categories by total plays descending
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

        # Build the insight prompt with campaign data context
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

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _build_category_breakdown(self, data: TractionReportInput) -> list:
        """Group venue records by business_category and compute aggregates.

        Returns a list of CategoryBreakdown objects, or an empty list if no
        category data is available.
        """
        # Check if any venue records have a category assigned
        has_categories = any(
            v.business_category and v.business_category.strip()
            for v in data.venue_records
        )
        if not has_categories:
            return []

        # Aggregate by category
        cat_data = defaultdict(lambda: {"hosts": set(), "total_plays": 0})
        for venue in data.venue_records:
            category = venue.business_category.strip() if venue.business_category else "Uncategorized"
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
        # Assemble venue summary for the prompt
        top_venues = sorted(
            data.venue_records, key=lambda v: v.total_plays, reverse=True
        )[:5]
        venue_summary = "\n".join(
            f"  - {v.host_name} ({v.business_category or 'General'}): "
            f"{v.total_plays:,} plays, {v.total_air_time}"
            for v in top_venues
        )

        category_summary = ""
        if categories:
            sorted_cats = sorted(categories, key=lambda c: c.total_plays, reverse=True)
            category_summary = "\n".join(
                f"  - {c.category}: {c.host_count} hosts, {c.total_plays:,} plays ({c.pct_of_total}%)"
                for c in sorted_cats
            )

        prompt = (
            f"You are writing a business insights section for an indoor digital billboard "
            f"advertising traction report. The advertiser is {data.advertiser_name}.\n\n"
            f"Campaign Summary:\n"
            f"  - Total Ad Plays: {data.total_plays:,}\n"
            f"  - Active Venues: {data.total_screen_count}\n"
            f"  - Total Screen Time: {data.total_air_time}\n"
        )

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
        steps = 4  # create doc, title, metrics, venue table
        # Category breakdown step
        has_categories = any(
            v.business_category and v.business_category.strip()
            for v in data.venue_records
        )
        if has_categories:
            steps += 1
        # AI insights step
        if data.include_insights:
            steps += 1
        # Footer step
        steps += 1
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
        # Replace common problem characters
        for char in r' /\:*?"<>|':
            safe = safe.replace(char, "_")
        # Collapse multiple underscores and strip apostrophes
        safe = safe.replace("'", "")
        while "__" in safe:
            safe = safe.replace("__", "_")
        return safe.strip("_")
