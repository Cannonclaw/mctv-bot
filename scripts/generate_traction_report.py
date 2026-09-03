# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Generate one advertiser traction report from an NTV360 export, from the CLI.

Runs the same pipeline the Reports page runs (parse_excel -> build_report_data
-> enrich_report_with_dashboard -> AdvertiserReportGenerator), without Streamlit,
Supabase, or an API key. Use it when you need a single named advertiser's report
and don't want to boot the app — the monthly crons only sweep every active
contract and have no way to target one client.

    python scripts/generate_traction_report.py \\
        --advertiser "Freeman Water Treatment" \\
        --excel ~/Downloads/freeman_ntv360.xlsx \\
        --period "August 2026" \\
        --rate 800 \\
        --rep "Creed Cannon"

Before it writes anything it prints a pre-flight block: how many venues the
export carried, how many matched the network dashboard, the screen count those
venues add up to, and how stale the dashboard is. Nothing in the report is
estimated — every figure traces to the export or to the dashboard, and a metric
we cannot source is left out rather than filled in.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from services.excel_parser import (  # noqa: E402
    parse_excel,
    build_report_data,
    enrich_report_with_dashboard,
    format_date_range,
)

logger = logging.getLogger("generate_traction_report")

# A dashboard older than this is reported as stale — screen counts and venue
# names drift as hosts are added and licenses move.
DASHBOARD_STALE_DAYS = 60


def _load_config() -> dict:
    """Load config/config.json without importing Streamlit-adjacent helpers."""
    with open(ROOT / "config" / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _load_dashboard() -> tuple:
    """Return (lookup, updated_at) for the network dashboard.

    Returns ({}, "") when the dashboard is missing so the caller can decide
    whether to continue without impressions, dwell, and screen counts.
    """
    path = ROOT / "data" / "network_dashboard.json"
    if not path.exists():
        return {}, ""

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"WARNING: could not read {path.name}: {exc}", file=sys.stderr)
        return {}, ""

    # The cached file is already in lookup shape (lowercased host name -> venue
    # dict), which is what dashboard_service writes and what enrichment expects.
    venues = raw.get("venues")
    if not isinstance(venues, dict):
        print(f"WARNING: {path.name} has no venues object — continuing without "
              "impressions, dwell time, and screen counts.", file=sys.stderr)
        return {}, ""
    return venues, raw.get("updated_at", "")


def _dashboard_age_days(updated_at: str) -> int:
    """Whole days since the dashboard was refreshed, or -1 if unknown."""
    if not updated_at or not isinstance(updated_at, str):
        return -1
    try:
        stamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return -1
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    # A stamp slightly in the future is clock skew, not an unreadable date —
    # report it as fresh rather than as "could not read the timestamp".
    return max(0, (datetime.now(timezone.utc) - stamp).days)


def _preflight(data, stats: dict, dashboard_age: int, args) -> list:
    """Print what the report will be built from. Returns a list of warnings."""
    warnings = []

    print()
    print("=" * 68)
    print(f"  TRACTION REPORT PRE-FLIGHT — {data.advertiser_name}")
    print("=" * 68)

    period = data.campaign_period or (
        "(no dates in export — cover page will stamp the current month)")
    print(f"  Campaign period    : {period}")
    print(f"  Dates in export    : {data.campaign_start or '?'} to {data.campaign_end or '?'}")
    print(f"  Total ad plays     : {data.total_plays:,}")
    print(f"  Total air time     : {data.total_air_time or '(none)'}")
    print(f"  Venues in export   : {data.total_screen_count}")

    matched = stats.get("matched", 0)
    unmatched = stats.get("unmatched", [])
    total_venues = matched + len(unmatched)
    print(f"  Matched dashboard  : {matched}/{total_venues}")

    if data.total_screens:
        print(f"  Screens running ad : {data.total_screens}")
    elif stats.get("screens"):
        print(f"  Screens running ad : {stats['screens']} across "
              f"{stats.get('screens_from', 0)} venue(s) — NOT in the report")
        warnings.append(
            f"The report will not state a screen count. {stats['screens']} screens "
            f"is only the venues the dashboard knows; naming it beside the full "
            f"venue count would credit those screens to venues it does not cover. "
            f"Add the venues listed below to data/network_dashboard.json and re-run."
        )
    else:
        print("  Screens running ad : unknown — no dashboard matches")
        warnings.append(
            "No venue matched the network dashboard, so the report cannot state a "
            "screen count. Refresh data/network_dashboard.json from the 'All MCTV "
            "Hosts' export."
        )

    if data.total_impressions:
        print(f"  Est. impressions   : {data.total_impressions:,.0f}")
    if data.avg_dwell_time:
        print(f"  Avg dwell time     : {data.avg_dwell_time} min")

    if data.monthly_rate > 0 and data.total_impressions > 0:
        cpm = (data.monthly_rate / data.total_impressions) * 1000
        print(f"  Monthly rate       : ${data.monthly_rate:,.2f}  (network CPM ${cpm:.2f})")
    elif data.monthly_rate > 0:
        print(f"  Monthly rate       : ${data.monthly_rate:,.2f}  (no CPM — impressions unknown)")
    else:
        print("  Monthly rate       : not set")
        warnings.append(
            "--rate was not passed, so CPM is omitted from the KPI banner, the "
            "venue table, the category table, and the CPM chart."
        )

    print(f"  Sales rep          : {data.sales_rep}")
    print(f"  AI insights        : {'on' if data.include_insights else 'off'}")
    print("=" * 68)

    if unmatched:
        preview = unmatched[:10]
        print(f"  {len(unmatched)} venue(s) not in the network dashboard:")
        for name in preview:
            print(f"    - {name}")
        if len(unmatched) > len(preview):
            print(f"    ... and {len(unmatched) - len(preview)} more")
        warnings.append(
            f"{len(unmatched)} venue(s) had no dashboard entry, so they contribute no "
            "impressions, dwell time, or screens. The screen count is a floor."
        )

    duplicates = stats.get("duplicates", [])
    if duplicates:
        print(f"  {len(duplicates)} venue(s) appear more than once in the export:")
        for name in duplicates[:10]:
            print(f"    - {name}")
        warnings.append(
            f"{len(duplicates)} venue(s) are spelled more than one way in the export. "
            "Their screens and impressions are counted once (correct), but the venue "
            "table lists each spelling as its own row with its plays split between "
            "them. Merge the rows in the export for a clean table."
        )

    if dashboard_age > DASHBOARD_STALE_DAYS:
        warnings.append(
            f"data/network_dashboard.json is {dashboard_age} days old. Screen counts "
            "and impressions may be out of date."
        )
    elif dashboard_age < 0:
        warnings.append("Could not read the dashboard's updated_at timestamp.")

    for w in warnings:
        print(f"  WARNING: {w}")
    if warnings:
        print("=" * 68)
    print()

    return warnings


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate one advertiser traction report from an NTV360 export.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--advertiser", required=True,
                   help="Advertiser name as it should read on the cover page.")
    p.add_argument("--excel", required=True,
                   help="Path to the NTV360 export (per-content, content, or "
                        "traction format — auto-detected).")
    p.add_argument("--period", default="",
                   help="Campaign period label, e.g. 'August 2026'. Defaults to "
                        "the date range found in the export.")
    p.add_argument("--rate", type=float, default=0.0,
                   help="Advertiser's monthly rate in dollars. Required for CPM.")
    p.add_argument("--rep", default="",
                   help="Sales rep on the cover page. Defaults to the "
                        "TractionReportInput default.")
    p.add_argument("--notes", default="",
                   help="Additional notes to include in the report.")
    p.add_argument("--with-insights", action="store_true",
                   help="Add the Claude-written insights section "
                        "(needs ANTHROPIC_API_KEY).")
    p.add_argument("--dry-run", action="store_true",
                   help="Run pre-flight and exit without writing a document.")
    p.add_argument("--yes", "-y", action="store_true",
                   help="Skip the confirmation prompt after pre-flight.")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    if args.rate < 0:
        print("ERROR: --rate cannot be negative.", file=sys.stderr)
        return 2

    excel_path = Path(args.excel).expanduser()
    if not excel_path.exists():
        print(f"ERROR: export not found: {excel_path}", file=sys.stderr)
        return 2

    try:
        records = parse_excel(excel_path)
    except Exception as exc:
        print(f"ERROR: could not read {excel_path.name}: "
              f"{type(exc).__name__}: {exc}\n"
              "  Export it again from NTV360 as .xlsx (not .xls or .csv).",
              file=sys.stderr)
        return 4
    if not records:
        print(
            f"ERROR: no play records parsed from {excel_path.name}.\n"
            "  The per-content export is the one that carries per-host play counts "
            "for a single creative — cell A1 reads 'Filename', row 5 is the "
            "'Host | City | ... | Play Count | Play Duration' header.",
            file=sys.stderr,
        )
        return 3

    data = build_report_data(records, args.advertiser, args.period)
    data.monthly_rate = args.rate
    data.include_insights = args.with_insights
    data.additional_notes = args.notes
    if args.rep:
        data.sales_rep = args.rep

    if not data.campaign_period:
        data.campaign_period = format_date_range(
            data.campaign_start, data.campaign_end)

    dashboard_lookup, updated_at = _load_dashboard()
    stats = enrich_report_with_dashboard(data, dashboard_lookup)

    _preflight(data, stats, _dashboard_age_days(updated_at), args)

    if args.dry_run:
        print("Dry run — no document written.")
        return 0

    if not args.yes:
        # Non-interactive (cron, pipe, CI): refuse rather than crash on EOF, and
        # never assume yes — this writes a document that goes to a client.
        if not sys.stdin.isatty():
            print("ERROR: stdin is not a terminal — re-run with --yes to confirm, "
                  "or --dry-run to preview only.", file=sys.stderr)
            return 1
        try:
            answer = input("Generate this report? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted — nothing written.")
            return 1
        if answer not in ("y", "yes"):
            print("Aborted — nothing written.")
            return 1

    config = _load_config()

    claude = None
    if data.include_insights:
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key or api_key == "your-api-key-here":
            print("WARNING: ANTHROPIC_API_KEY not set — generating without insights.")
            data.include_insights = False
        else:
            from services.claude_service import ClaudeService
            model = config["proposal_settings"].get(
                "model", "claude-sonnet-4-5-20250929")
            claude = ClaudeService(api_key=api_key, model=model)

    from services.docx_service import DocxService
    from generators.advertiser_report import AdvertiserReportGenerator

    generator = AdvertiserReportGenerator(config, claude, DocxService(config))

    def on_progress(step_name, current, total):
        print(f"  [{current}/{total}] {step_name}")

    report_path = generator.generate(data, progress_callback=on_progress)

    print()
    print(f"Report written: {report_path}")

    # save_report attempts PDF conversion and swallows failures, so check rather
    # than assume. LibreOffice Writer must be installed for it to land.
    pdf_path = report_path.with_suffix(".pdf")
    if pdf_path.exists():
        print(f"PDF written   : {pdf_path}")
    else:
        print("PDF           : not produced (LibreOffice Writer unavailable) — "
              "the .docx is complete.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
