# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Monthly traction report cron.

Run on or after the 1st of each month. For every advertiser with an active
contract, generates a previous-month traction report PDF, posts it to the
client portal (client_reports table + Storage), and emails the advertiser.

Usage:
    python scripts/monthly_traction_reports.py            # current run
    python scripts/monthly_traction_reports.py --dry-run  # preview targets
    python scripts/monthly_traction_reports.py --month 2026-04  # backfill

Schedule on Render: 8:00 AM CT on the 2nd of each month.
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("monthly_reports")


def _previous_month_key() -> str:
    """Return YYYY-MM for the month before the current one."""
    today = date.today()
    if today.month == 1:
        return f"{today.year - 1}-12"
    return f"{today.year}-{today.month - 1:02d}"


def _build_report_input(client: dict, contract: dict, target_month: str,
                        ntv_data: dict):
    """Build a TractionReportInput from client + contract + NTV360 data."""
    from models.report_data import TractionReportInput, VenueRecord

    # Convert NTV360 venue rows to VenueRecord dataclasses
    venue_records = []
    for v in ntv_data.get("venue_data", []) or []:
        try:
            venue_records.append(VenueRecord(
                host_name=v.get("host_name", ""),
                business_category=v.get("business_category", ""),
                city=v.get("city", ""),
                screen_count=int(v.get("screen_count", 1) or 1),
                monthly_traffic=float(v.get("monthly_traffic", 0) or 0),
                dwell_time_minutes=float(v.get("dwell_time_minutes", 0) or 0),
                monthly_impressions=float(v.get("monthly_impressions", 0) or 0),
                total_plays=int(v.get("total_plays", 0) or 0),
                total_air_time=v.get("total_air_time", ""),
            ))
        except (ValueError, TypeError):
            continue

    # Period label: e.g. "April 2026"
    try:
        dt = datetime.strptime(target_month, "%Y-%m")
        period_label = dt.strftime("%B %Y")
    except ValueError:
        period_label = target_month

    return TractionReportInput(
        advertiser_name=client.get("business_name", "Client"),
        report_type="advertiser",
        campaign_period=period_label,
        campaign_start=contract.get("start_date", ""),
        campaign_end=contract.get("end_date", ""),
        network_name="MCTV Elite Advertising",
        venue_records=venue_records,
        total_plays=ntv_data.get("total_plays", 0),
        total_screen_count=int(contract.get("screen_count", 0) or 0),
        total_air_time=ntv_data.get("total_air_time", ""),
        total_impressions=float(ntv_data.get("total_plays", 0) * 60),
        monthly_rate=float(contract.get("monthly_rate", 0) or 0),
        sales_rep=contract.get("created_by") or "Mary Michael Cannon",
        include_insights=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview targets, don't generate or send.")
    parser.add_argument("--month", default="",
                        help="YYYY-MM to report on. Defaults to previous month.")
    args = parser.parse_args()

    target_month = args.month or _previous_month_key()
    logger.info("Target month: %s", target_month)

    from services.supabase_client import query_table, insert_row
    from services.ntv360_service import get_play_data_for_report
    from services.notification_service import notify_report_shared

    # Pull NTV360 snapshot for the target month
    ntv = get_play_data_for_report(target_month)
    if not ntv or ntv.get("total_plays", 0) == 0:
        logger.warning("No NTV360 data for %s — aborting (run a manual upload first).",
                       target_month)
        return 1

    # Build a single source-of-truth ntv_data dict for the report builder
    snap = query_table("ntv360_snapshots", filters={"snapshot_month": target_month}, limit=1)
    if not snap:
        snap = query_table("ntv360_snapshots", order="-snapshot_month", limit=1)
    if not snap:
        logger.warning("No snapshot row for %s.", target_month)
        return 1
    snap_row = snap[0]
    import json as _json
    venue_data = snap_row.get("venue_data") or []
    if isinstance(venue_data, str):
        try:
            venue_data = _json.loads(venue_data)
        except _json.JSONDecodeError:
            venue_data = []
    ntv_data = {
        "total_plays": int(snap_row.get("total_plays", 0) or 0),
        "total_air_time": snap_row.get("total_air_time", ""),
        "venue_data": venue_data,
    }

    # Find active advertiser contracts
    contracts = query_table(
        "contracts",
        filters={"status": "active"},
        order="-created_at",
    )
    advertiser_contracts = [c for c in (contracts or [])
                            if c.get("contract_type", "") in ("advertising",
                                                              "advertiser",
                                                              "renewal",
                                                              "category_exclusivity",
                                                              "bundle")]
    logger.info("Found %d active advertiser contracts", len(advertiser_contracts))

    sent = 0
    skipped = 0
    failed = 0

    for c in advertiser_contracts:
        client_id = c.get("client_id", "")
        if not client_id:
            continue
        client_rows = query_table("clients", filters={"id": client_id}, limit=1)
        if not client_rows:
            continue
        client = client_rows[0]

        # Skip if a report for this period was already generated
        existing = query_table(
            "client_reports",
            filters={"client_id": client_id},
            order="-created_at",
            limit=10,
        ) or []
        if any(target_month in (r.get("title", "") + r.get("period", ""))
               for r in existing):
            logger.info("Skipping %s — report for %s already exists",
                        client.get("business_name"), target_month)
            skipped += 1
            continue

        if args.dry_run:
            logger.info("[DRY RUN] Would generate for %s (contract %s)",
                        client.get("business_name"), c.get("id"))
            continue

        try:
            from generators.advertiser_report import AdvertiserReportGenerator
            from services.claude_service import ClaudeService
            from services.docx_service import DocxService
            from services.config_service import load_config

            cfg = load_config()
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key or api_key == "your-api-key-here":
                logger.error("ANTHROPIC_API_KEY missing — cannot generate insights")
                failed += 1
                continue

            claude = ClaudeService(
                api_key=api_key,
                model=cfg.get("proposal_settings", {}).get(
                    "model", "claude-sonnet-4-5-20250929"),
            )
            docx_svc = DocxService(cfg)
            data = _build_report_input(client, c, target_month, ntv_data)
            generator = AdvertiserReportGenerator(cfg, claude, docx_svc)
            report_path = generator.generate(data)

            # Persist to client_reports
            insert_row("client_reports", {
                "client_id": client_id,
                "title": f"Traction Report — {data.campaign_period}",
                "period": target_month,
                "report_type": "advertiser",
                "file_path": str(report_path),
                "total_plays": data.total_plays,
                "total_impressions": data.total_impressions,
            })

            # Email the advertiser
            try:
                notify_report_shared(
                    client_email=client.get("contact_email", ""),
                    client_name=client.get("contact_name", ""),
                    report_title=f"{data.campaign_period} Traction Report",
                )
            except Exception as e:
                logger.warning("Email failed for %s: %s",
                               client.get("business_name"), e)

            sent += 1
            logger.info("Report generated + delivered for %s",
                        client.get("business_name"))

        except Exception as e:
            failed += 1
            logger.error("Generation failed for %s: %s",
                         client.get("business_name"), e)

    logger.info("Done. sent=%d skipped=%d failed=%d", sent, skipped, failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
