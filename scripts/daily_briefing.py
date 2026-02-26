# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Daily briefing cron script.

Run manually:
    python scripts/daily_briefing.py

Dry run (generate without sending):
    python scripts/daily_briefing.py --dry-run

Schedule on Render:
    Add a cron job in render.yaml targeting this script.
    Recommended: 7:00 AM CT daily (Mon-Fri).

Schedule locally (Windows Task Scheduler):
    Action: python
    Arguments: scripts/daily_briefing.py
    Start in: C:\\Users\\msaac\\OneDrive - Mississippi Asthma & Allergy Clinic, P.A\\Desktop\\MCTV-Bot
"""

import argparse
import json
import logging
import sys
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
logger = logging.getLogger("daily_briefing")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_PATH = ROOT / "config" / "config.json"

# ---------------------------------------------------------------------------
# Imports from project
# ---------------------------------------------------------------------------
from services.briefing_service import send_daily_briefing  # noqa: E402


def _load_config() -> dict:
    """Load config.json from the project config directory."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _dry_run() -> int:
    """Generate the briefing and print a summary without sending."""
    from services.briefing_service import (  # noqa: E402
        generate_briefing,
        format_briefing_sms,
    )

    logger.info("DRY RUN — generating briefing (nothing will be sent)...")

    try:
        briefing = generate_briefing()
    except Exception as exc:
        logger.error("Failed to generate briefing: %s", exc)
        return 1

    es = briefing.get("executive_summary", {})
    alerts = briefing.get("alerts", [])
    contracts = briefing.get("contracts", {})
    revenue = briefing.get("revenue", {})

    print("\n" + "=" * 60)
    print("DAILY BRIEFING — DRY RUN")
    print("=" * 60)

    print(f"\nMRR           : ${es.get('monthly_recurring_revenue', 0):,.0f}")
    print(f"Active Clients: {es.get('active_clients', 0)}")
    print(f"Contracts Pend: {es.get('contracts_awaiting_signature', 0)}")
    print(f"Overdue       : ${es.get('overdue_amount', 0):,.0f}")
    print(f"Hot Leads     : {es.get('hot_leads', 0)}")
    print(f"Revenue Billed: ${revenue.get('total_billed', 0):,.2f}")
    print(f"Active MRR    : ${contracts.get('active_mrr', 0):,.0f}")
    print(f"Alerts        : {len(alerts)}")

    if alerts:
        print("\nAlerts:")
        for alert in alerts:
            print(f"  - {alert}")

    try:
        sms_text = format_briefing_sms(briefing)
        print(f"\nSMS Preview ({len(sms_text)} chars):\n{sms_text}")
    except Exception:
        pass

    print("\n" + "=" * 60)
    logger.info("Dry run complete — no emails or SMS sent.")
    return 0


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="MCTV Daily Briefing")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate briefing without sending",
    )
    args = parser.parse_args()

    try:
        config = _load_config()
    except FileNotFoundError:
        logger.error("Config file not found: %s", CONFIG_PATH)
        return 1
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in config file: %s", exc)
        return 1

    if args.dry_run:
        return _dry_run()

    logger.info("Starting daily briefing...")

    result = send_daily_briefing(config)

    if result["success"]:
        briefing = result["briefing"]
        es = briefing.get("executive_summary", {})
        logger.info(
            "Briefing sent successfully | MRR: $%s | Alerts: %d | Email: %s | SMS: %s",
            f"{es.get('monthly_recurring_revenue', 0):,.0f}",
            len(briefing.get("alerts", [])),
            "sent" if result["email_sent"] else "failed",
            "sent" if result["sms_sent"] else "failed",
        )
        return 0
    else:
        for err in result.get("errors", []):
            logger.error("Briefing error: %s", err)
        return 1


if __name__ == "__main__":
    sys.exit(main())
