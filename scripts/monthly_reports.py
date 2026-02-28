# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Automated monthly traction report generation.

Generates traction reports for all active advertiser clients, uploads them
to the client portal, and sends email + SMS notifications.

Usage:
    python scripts/monthly_reports.py              # Generate + share + notify
    python scripts/monthly_reports.py --dry-run    # Preview what would happen
    python scripts/monthly_reports.py --force      # Regenerate even if already sent
    python scripts/monthly_reports.py --month 1 --year 2026  # Specific period

Scheduling:
    Recommended: 1st of each month, 9:00 AM CT.
    - Render cron: add to render.yaml
    - Windows Task Scheduler: Action=python, Args=scripts/monthly_reports.py,
      Start in=C:\\...\\MCTV-Bot
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root on sys.path so services/ imports work
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("monthly_reports")


def _check_dashboard_freshness() -> dict:
    """Verify the network dashboard exists and isn't stale.

    Returns:
        {"loaded": bool, "venue_count": int, "stale": bool, "warning": str}
    """
    from services.dashboard_service import get_dashboard_status

    status = get_dashboard_status()
    result = {
        "loaded": status.get("loaded", False),
        "venue_count": status.get("venue_count", 0),
        "stale": False,
        "warning": "",
    }

    if not result["loaded"]:
        result["warning"] = (
            "No network dashboard found. Upload the MCTV Network Dashboard Excel "
            "via the Reports page before running automated reports."
        )
        return result

    # Check staleness (> 45 days old)
    updated_at = status.get("updated_at", "")
    if updated_at:
        try:
            updated_date = datetime.fromisoformat(updated_at)
            days_old = (datetime.now() - updated_date).days
            if days_old > 45:
                result["stale"] = True
                result["warning"] = (
                    f"Dashboard is {days_old} days old. Consider uploading "
                    f"a fresh Network Dashboard export for accurate data."
                )
        except (ValueError, TypeError):
            pass

    return result


def _dry_run(target_month: int, target_year: int) -> int:
    """Preview which clients would receive reports (no side effects)."""
    from services.report_service import (
        determine_report_period,
        get_reportable_clients,
        client_needs_report,
    )

    period_label, start_date, end_date = determine_report_period(
        target_month, target_year,
    )

    print("\n" + "=" * 60)
    print("MONTHLY REPORTS -- DRY RUN")
    print("=" * 60)
    print(f"Report period: {period_label} ({start_date} to {end_date})")
    print()

    # Dashboard check
    db_check = _check_dashboard_freshness()
    if db_check["warning"]:
        print(f"WARNING: {db_check['warning']}")
    if db_check["loaded"]:
        print(f"Dashboard: {db_check['venue_count']} venues loaded")
    else:
        print("Dashboard: NOT LOADED -- reports cannot be generated")
        print("=" * 60)
        return 1
    print()

    # Find reportable clients
    clients = get_reportable_clients()
    if not clients:
        print("No active advertiser clients with contracts found.")
        print("=" * 60)
        return 0

    print(f"Found {len(clients)} reportable client(s):\n")

    would_generate = 0
    would_skip = 0

    for client in clients:
        bname = client.get("business_name", "Unknown")
        rate = client.get("monthly_rate", 0)
        screens = client.get("screen_count", 0)
        email = client.get("contact_email", "")
        phone = client.get("contact_phone", "")

        needs = client_needs_report(client["id"], target_month, target_year)

        if needs:
            would_generate += 1
            flag = "[WOULD GENERATE]"
        else:
            would_skip += 1
            flag = "[ALREADY SENT]"

        print(
            f"  {flag} {bname}\n"
            f"           Rate: ${rate:,.0f}/mo | Screens: {screens} | "
            f"Email: {email or 'N/A'} | Phone: {phone or 'N/A'}"
        )

    print(f"\nSummary: {would_generate} to generate, {would_skip} already sent")
    print("=" * 60)
    return 0


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="MCTV Automated Monthly Traction Reports",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which clients would receive reports (no side effects)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate reports even if already sent this month",
    )
    parser.add_argument(
        "--month",
        type=int,
        default=None,
        help="Target month (1-12). Defaults to previous month.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Target year. Defaults to current/previous year.",
    )
    parser.add_argument(
        "--with-insights",
        action="store_true",
        help="Include AI-generated insights (uses Claude API credits)",
    )
    args = parser.parse_args()

    # Resolve target month/year
    from services.report_service import determine_report_period

    period_label, start_date, end_date = determine_report_period(
        args.month, args.year,
    )

    # Extract month/year from resolved period for dedup checks
    period_date = datetime.strptime(start_date, "%Y-%m-%d")
    target_month = period_date.month
    target_year = period_date.year

    if args.dry_run:
        return _dry_run(target_month, target_year)

    logger.info(
        "Starting monthly report generation for %s...", period_label,
    )

    # ── Step 1: Check dashboard ──────────────────────────────────────────
    db_check = _check_dashboard_freshness()
    if not db_check["loaded"]:
        logger.error("No network dashboard loaded. Cannot generate reports.")
        logger.error("Upload the MCTV Network Dashboard via the Reports page first.")
        return 1

    if db_check["stale"]:
        logger.warning(db_check["warning"])

    from services.dashboard_service import load_dashboard

    dashboard_lookup = load_dashboard()
    if not dashboard_lookup:
        logger.error("Dashboard loaded but contains no venue data.")
        return 1

    logger.info("Dashboard loaded: %d venues", len(dashboard_lookup))

    # ── Step 2: Load config ──────────────────────────────────────────────
    import json

    config_path = ROOT / "config" / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # ── Step 3: Find reportable clients ──────────────────────────────────
    from services.report_service import (
        get_reportable_clients,
        client_needs_report,
        generate_and_share_report,
    )

    clients = get_reportable_clients()
    if not clients:
        logger.info("No active advertiser clients with contracts. Nothing to do.")
        return 0

    logger.info("Found %d reportable client(s)", len(clients))

    # ── Step 4: Generate reports ─────────────────────────────────────────
    results = []
    skip_insights = not args.with_insights

    for client in clients:
        bname = client.get("business_name", "Unknown")

        # Deduplication check (unless --force)
        if not args.force:
            if not client_needs_report(client["id"], target_month, target_year):
                logger.info("Skipping %s -- report already sent for %s", bname, period_label)
                results.append({
                    "success": True,
                    "client_name": bname,
                    "skipped": True,
                })
                continue

        # Generate + share + notify
        logger.info("Generating report for %s...", bname)
        result = generate_and_share_report(
            client=client,
            dashboard_lookup=dashboard_lookup,
            config=config,
            period_label=period_label,
            skip_ai_insights=skip_insights,
        )
        results.append(result)

        if result.get("success"):
            logger.info(
                "  -> %s: email=%s, sms=%s",
                bname,
                result.get("email_sent", False),
                result.get("sms_sent", False),
            )
        else:
            logger.error("  -> %s FAILED: %s", bname, result.get("error", "Unknown"))

    # ── Step 5: Team summary notification ────────────────────────────────
    try:
        from services.notification_service import notify_monthly_reports_summary

        notify_monthly_reports_summary(results, period_label)
        logger.info("Team summary email sent")
    except ImportError:
        logger.warning("notify_monthly_reports_summary not available yet")
    except Exception as e:
        logger.error("Failed to send team summary: %s", e)

    # ── Summary ──────────────────────────────────────────────────────────
    generated = [r for r in results if r.get("success") and not r.get("skipped")]
    skipped = [r for r in results if r.get("skipped")]
    failed = [r for r in results if not r.get("success")]

    logger.info(
        "Monthly reports complete | Generated: %d | Skipped: %d | Failed: %d",
        len(generated), len(skipped), len(failed),
    )

    if failed:
        for r in failed:
            logger.error("  FAILED: %s -- %s", r.get("client_name"), r.get("error"))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
