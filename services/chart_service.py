"""Chart generation for MCTV traction reports.

Produces 4 branded PNG charts using matplotlib:
  1. Venue Performance Bar Chart (top venues by plays)
  2. Category Distribution Donut Chart (% of plays by category)
  3. Engagement Scatter Plot (plays vs. air time)
  4. Market Comparison Bar Chart (side-by-side market stats)

All charts use MCTV brand colors and save to temp files.
"""

import tempfile
import logging
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from models.report_data import TractionReportInput, CategoryBreakdown

logger = logging.getLogger(__name__)

# ── MCTV Brand Colors ────────────────────────────────────────────────────────
NAVY = "#1B1F3B"
GOLD = "#C5A55A"
LIGHT_GOLD = "#E8D5A3"
GRAY = "#7A7A7A"
LIGHT_BG = "#F5F5F0"
WHITE = "#FFFFFF"

# Market-specific colors for multi-market charts
MARKET_COLORS = {
    "Oxford": "#1B1F3B",      # Navy
    "Tupelo": "#C5A55A",      # Gold
    "Starkville": "#5F7D6E",  # Sage
    "Columbus": "#C4836E",    # Coral
    "West Point": "#4A90B8",  # Steel blue
}

# Category colors for donut chart
CATEGORY_COLORS = [
    "#1B1F3B", "#C5A55A", "#5F7D6E", "#C4836E", "#4A90B8",
    "#8B6F47", "#6B8E7B", "#B07A5B", "#5B8BAE", "#9E8B6E",
    "#7A9B8F", "#D4A574",
]

DEFAULT_MARKET_COLOR = "#7A7A7A"


def _get_market_color(city: str) -> str:
    """Get the brand color for a market/city."""
    for market, color in MARKET_COLORS.items():
        if market.lower() in city.lower():
            return color
    return DEFAULT_MARKET_COLOR


def _setup_chart(fig, ax):
    """Apply consistent styling to a chart."""
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRAY)
    ax.spines["bottom"].set_color(GRAY)
    ax.tick_params(colors=GRAY, labelsize=8)


def build_venue_bar_chart(data: TractionReportInput, max_venues: int = 15) -> str:
    """Horizontal bar chart showing top venues by play count.

    Color-coded by market/city. Returns path to saved PNG.
    """
    sorted_venues = sorted(
        data.venue_records, key=lambda v: v.total_plays, reverse=True
    )[:max_venues]

    # Reverse for horizontal bar (top venue at top of chart)
    venues = list(reversed(sorted_venues))
    names = [v.host_name[:30] for v in venues]  # Truncate long names
    plays = [v.total_plays for v in venues]
    colors = [_get_market_color(v.city or "") for v in venues]

    fig, ax = plt.subplots(figsize=(7, 5))
    _setup_chart(fig, ax)

    bars = ax.barh(names, plays, color=colors, edgecolor="none", height=0.7)

    # Add value labels
    for bar, play_count in zip(bars, plays):
        ax.text(bar.get_width() + max(plays) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{play_count:,}", va="center", ha="left",
                fontsize=7, color=NAVY, fontweight="bold")

    ax.set_xlabel("Total Ad Plays", fontsize=9, color=NAVY)
    ax.set_title("Top Venue Performance", fontsize=12, color=NAVY,
                 fontweight="bold", pad=10)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{int(x):,}"))

    # Add legend if multiple markets
    cities = set(v.city for v in sorted_venues if v.city)
    if len(cities) > 1:
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=_get_market_color(c), label=c) for c in sorted(cities)
        ]
        ax.legend(handles=legend_elements, loc="lower right", fontsize=7,
                  framealpha=0.9, edgecolor=GRAY)

    plt.tight_layout()
    path = tempfile.mktemp(suffix=".png", prefix="mctv_venue_bar_")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    return path


def build_category_donut(categories: list) -> str:
    """Donut/pie chart showing % of plays by venue category.

    Returns path to saved PNG.
    """
    if not categories:
        return ""

    sorted_cats = sorted(categories, key=lambda c: c.total_plays, reverse=True)
    labels = [c.category for c in sorted_cats]
    sizes = [c.total_plays for c in sorted_cats]
    colors = CATEGORY_COLORS[:len(sorted_cats)]

    fig, ax = plt.subplots(figsize=(5.5, 5))
    fig.patch.set_facecolor(WHITE)

    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, autopct="%1.0f%%", startangle=90,
        colors=colors, pctdistance=0.8,
        wedgeprops=dict(width=0.4, edgecolor=WHITE, linewidth=2),
    )

    for text in autotexts:
        text.set_fontsize(8)
        text.set_color(WHITE)
        text.set_fontweight("bold")

    # Center text
    ax.text(0, 0, f"{sum(sizes):,}\nPlays", ha="center", va="center",
            fontsize=11, color=NAVY, fontweight="bold")

    ax.set_title("Plays by Venue Category", fontsize=12, color=NAVY,
                 fontweight="bold", pad=10)

    # Legend
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5),
              fontsize=7, frameon=False)

    plt.tight_layout()
    path = tempfile.mktemp(suffix=".png", prefix="mctv_category_donut_")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    return path


def build_scatter_plot(data: TractionReportInput) -> str:
    """Scatter plot: X = play count, Y = air time (hours).

    Each dot is a venue, color-coded by market. Returns path to saved PNG.
    """
    venues = data.venue_records
    if not venues:
        return ""

    plays = [v.total_plays for v in venues]
    # Parse air time strings to hours
    hours = []
    for v in venues:
        h = 0
        if v.total_air_time:
            import re
            hm = re.search(r"(\d[\d,]*)h", v.total_air_time.replace(",", ""))
            mm = re.search(r"(\d+)m", v.total_air_time)
            if hm:
                h += int(hm.group(1))
            if mm:
                h += int(mm.group(1)) / 60
        hours.append(h)

    colors = [_get_market_color(v.city or "") for v in venues]

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    _setup_chart(fig, ax)

    ax.scatter(plays, hours, c=colors, s=50, alpha=0.75, edgecolors=NAVY,
               linewidths=0.5)

    # Label top 5 outlier venues by play count
    sorted_by_plays = sorted(enumerate(venues), key=lambda x: x[1].total_plays, reverse=True)
    for rank, (idx, v) in enumerate(sorted_by_plays[:5]):
        label = v.host_name[:20] + ("..." if len(v.host_name) > 20 else "")
        ax.annotate(
            label,
            (plays[idx], hours[idx]),
            textcoords="offset points",
            xytext=(5, 5 if rank % 2 == 0 else -10),
            fontsize=6, color=NAVY, fontweight="bold",
            alpha=0.85,
        )

    ax.set_xlabel("Total Ad Plays", fontsize=9, color=NAVY)
    ax.set_ylabel("Screen Time (hours)", fontsize=9, color=NAVY)
    ax.set_title("Engagement Distribution", fontsize=12, color=NAVY,
                 fontweight="bold", pad=10)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{int(x):,}"))

    # Add legend if multiple markets
    cities = set(v.city for v in venues if v.city)
    if len(cities) > 1:
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=_get_market_color(c), label=c) for c in sorted(cities)
        ]
        ax.legend(handles=legend_elements, loc="upper left", fontsize=7,
                  framealpha=0.9, edgecolor=GRAY)

    plt.tight_layout()
    path = tempfile.mktemp(suffix=".png", prefix="mctv_scatter_")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    return path


def build_market_comparison(data: TractionReportInput) -> str:
    """Grouped bar chart comparing markets (plays, venues, avg per venue).

    Returns path to saved PNG, or empty string if only one market.
    """
    # Group by city
    market_stats = defaultdict(lambda: {"venues": 0, "plays": 0})
    for v in data.venue_records:
        city = v.city or "Unknown"
        market_stats[city]["venues"] += 1
        market_stats[city]["plays"] += v.total_plays

    if len(market_stats) <= 1:
        return ""

    markets = sorted(market_stats.keys(), key=lambda m: market_stats[m]["plays"],
                     reverse=True)
    venue_counts = [market_stats[m]["venues"] for m in markets]
    play_counts = [market_stats[m]["plays"] for m in markets]
    avg_plays = [p // v if v > 0 else 0 for p, v in zip(play_counts, venue_counts)]
    market_colors = [_get_market_color(m) for m in markets]

    fig, axes = plt.subplots(1, 3, figsize=(8, 4))
    fig.patch.set_facecolor(WHITE)

    titles = ["Total Plays", "Venues", "Avg Plays/Venue"]
    datasets = [play_counts, venue_counts, avg_plays]

    for ax, title, values in zip(axes, titles, datasets):
        ax.set_facecolor(WHITE)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(GRAY)
        ax.spines["bottom"].set_color(GRAY)
        ax.tick_params(colors=GRAY, labelsize=7)

        bars = ax.bar(markets, values, color=market_colors, edgecolor="none", width=0.6)
        ax.set_title(title, fontsize=9, color=NAVY, fontweight="bold")

        # Value labels on bars
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{val:,}", ha="center", va="bottom",
                    fontsize=7, color=NAVY, fontweight="bold")

        ax.set_xticks(range(len(markets)))
        ax.set_xticklabels(markets, fontsize=7, rotation=15, ha="right")

    fig.suptitle("Market Comparison", fontsize=12, color=NAVY,
                 fontweight="bold", y=1.02)

    plt.tight_layout()
    path = tempfile.mktemp(suffix=".png", prefix="mctv_market_compare_")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    return path


def generate_all_charts(data: TractionReportInput,
                        categories: list = None) -> list:
    """Generate all available charts for a traction report.

    Returns a list of PNG file paths (only charts with sufficient data).
    """
    charts = []

    try:
        # 1. Venue bar chart (always available if venues exist)
        if data.venue_records:
            path = build_venue_bar_chart(data)
            if path:
                charts.append(path)

        # 2. Category donut (needs categories)
        if categories:
            path = build_category_donut(categories)
            if path:
                charts.append(path)

        # 3. Scatter plot (needs venues with air time)
        has_air_time = any(v.total_air_time for v in data.venue_records)
        if data.venue_records and has_air_time:
            path = build_scatter_plot(data)
            if path:
                charts.append(path)

        # 4. Market comparison (needs 2+ markets)
        cities = set(v.city for v in data.venue_records if v.city)
        if len(cities) > 1:
            path = build_market_comparison(data)
            if path:
                charts.append(path)

    except Exception as e:
        logger.error("Chart generation failed: %s", e)

    return charts
