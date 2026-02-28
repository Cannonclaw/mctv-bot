# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Headless traction report generation, sharing, and notification service.

Extracts report-sharing logic from pages/2_Reports.py into a reusable service
with no Streamlit dependency.  Used by both the Reports page (interactive)
and scripts/monthly_reports.py (automated).

Pipeline:
    1. get_reportable_clients()     -- active advertisers with contracts
    2. determine_report_period()    -- previous calendar month label + dates
    3. client_needs_report()        -- deduplication check
    4. generate_and_share_report()  -- generate DOCX -> upload -> DB -> notify
"""

import logging
import os
from calendar import monthrange
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

def determine_report_period(
    target_month: int | None = None,
    target_year: int | None = None,
) -> tuple[str, str, str]:
    """Auto-detect the report period (default: previous calendar month).

    Args:
        target_month: Override month (1-12). Defaults to last month.
        target_year:  Override year. Defaults to current/previous year.

    Returns:
        (period_label, start_date, end_date)
        e.g. ("January 2026", "2026-01-01", "2026-01-31")
    """
    today = date.today()

    if target_month is None or target_year is None:
        # Default to previous calendar month
        if today.month == 1:
            target_month = 12
            target_year = today.year - 1
        else:
            target_month = today.month - 1
            target_year = today.year

    _, last_day = monthrange(target_year, target_month)

    period_label = date(target_year, target_month, 1).strftime("%B %Y")
    start_date = f"{target_year}-{target_month:02d}-01"
    end_date = f"{target_year}-{target_month:02d}-{last_day:02d}"

    return period_label, start_date, end_date


# ---------------------------------------------------------------------------
# Client discovery
# ---------------------------------------------------------------------------

def get_reportable_clients() -> list[dict]:
    """Get active advertiser clients that have active/signed contracts.

    Each returned client is enriched with ``monthly_rate`` and
    ``screen_count`` from their most valuable active contract.

    Returns:
        List of client dicts with extra keys: monthly_rate, screen_count.
    """
    try:
        from services.portal_service import get_all_clients
        from services.contract_service import get_contracts_for_client
    except ImportError as e:
        logger.error("report_service: missing import: %s", e)
        return []

    clients = get_all_clients(status="active") or []
    reportable = []

    for client in clients:
        cid = client.get("id", "")
        client_type = (client.get("client_type") or "").lower()

        # Skip host/venue-only clients
        if client_type == "host":
            continue

        # Check for active/signed contracts
        try:
            contracts = get_contracts_for_client(cid) or []
        except Exception:
            contracts = []

        active_contracts = [
            c for c in contracts
            if c.get("status") in ("active", "signed")
        ]

        if not active_contracts:
            continue

        # Pick best contract for enrichment (highest monthly rate)
        best = max(
            active_contracts,
            key=lambda c: float(c.get("monthly_rate", 0) or c.get("rate", 0) or 0),
        )

        client["monthly_rate"] = float(
            best.get("monthly_rate", 0) or best.get("rate", 0) or 0
        )
        client["screen_count"] = int(best.get("screen_count", 0) or 0)
        client["contract_id"] = best.get("id", "")
        reportable.append(client)

    logger.info("Found %d reportable clients", len(reportable))
    return reportable


def get_last_report_date(client_id: str) -> str | None:
    """Get the most recent report date for a client.

    Returns ISO date string or None if no reports exist.
    """
    try:
        from services.supabase_client import query_table

        rows = query_table(
            "client_reports",
            select="created_at",
            filters={"client_id": client_id},
            order="-created_at",
            limit=1,
        )
        if rows:
            return rows[0].get("created_at", "")[:10]
    except Exception as e:
        logger.error("report_service: failed to check last report: %s", e)

    return None


def client_needs_report(
    client_id: str,
    target_month: int,
    target_year: int,
) -> bool:
    """Check whether a client still needs a report for the given month.

    Looks at ``client_reports.campaign_period`` and ``created_at`` to see
    if a report for the target month has already been shared.

    Returns:
        True if a report should be generated; False if already sent.
    """
    try:
        from services.supabase_client import query_table

        period_label = date(target_year, target_month, 1).strftime("%B %Y")

        rows = query_table(
            "client_reports",
            select="id,campaign_period,created_at",
            filters={"client_id": client_id},
        )
        if not rows:
            return True

        for row in rows:
            cp = (row.get("campaign_period") or "").strip()
            if period_label.lower() in cp.lower():
                logger.info(
                    "Report for %s / %s already exists (id=%s)",
                    client_id, period_label, row.get("id"),
                )
                return False

        return True
    except Exception as e:
        logger.error("report_service: dedup check failed: %s", e)
        return True  # fail-open so reports still get generated


# ---------------------------------------------------------------------------
# Sharing & notification (headless — extracted from pages/2_Reports.py)
# ---------------------------------------------------------------------------

def share_report(
    report_path: Path,
    data,
    client: dict,
) -> dict | None:
    """Upload a report to Supabase Storage and create a client_reports record.

    This is the headless equivalent of ``_do_share_report()`` in
    ``pages/2_Reports.py`` (lines 97-151).

    Args:
        report_path: Local path to the generated .docx file.
        data: TractionReportInput (or any object with campaign_period, etc.)
        client: Client dict with ``id``, ``business_name``, etc.

    Returns:
        Inserted client_reports row dict on success, None on failure.
    """
    from services.supabase_client import insert_row
    from services.storage_service import upload_from_path, BUCKET_REPORTS

    client_id = client.get("id", "")
    bname = client.get("business_name", "")

    # Upload file to Supabase Storage
    storage_path = f"{client_id}/{report_path.name}"
    uploaded = upload_from_path(BUCKET_REPORTS, storage_path, str(report_path))

    # Build report title
    title = f"{bname} Traction Report"
    if hasattr(data, "campaign_period") and data.campaign_period:
        title += f" - {data.campaign_period}"
    elif hasattr(data, "report_period") and data.report_period:
        title += f" - {data.report_period}"

    # Extract totals
    total_plays = None
    total_venues = None
    if hasattr(data, "venue_records") and data.venue_records:
        total_venues = len(data.venue_records)
        total_plays = sum(
            v.total_plays for v in data.venue_records
            if hasattr(v, "total_plays")
        )

    # Build DB record
    report_data = {
        "client_id": client_id,
        "report_type": getattr(data, "report_type", "traction"),
        "title": title,
        "document_url": storage_path if uploaded else str(report_path),
    }
    if hasattr(data, "campaign_period") and data.campaign_period:
        report_data["campaign_period"] = data.campaign_period
    elif hasattr(data, "report_period") and data.report_period:
        report_data["campaign_period"] = data.report_period
    if total_plays:
        report_data["total_plays"] = total_plays
    if total_venues:
        report_data["total_venues"] = total_venues

    result = insert_row("client_reports", report_data)

    if result:
        logger.info("Report shared: %s -> %s", title, bname)
    else:
        logger.error("Failed to insert client_reports row for %s", bname)

    return result


def notify_client_report(
    client: dict,
    report_title: str,
    total_plays: int = 0,
    venue_count: int = 0,
) -> dict:
    """Send email + SMS notification to a client about their new report.

    Args:
        client: Client dict with contact_email, contact_name, contact_phone.
        report_title: Report title for the notification.
        total_plays: Total ad plays (for SMS summary).
        venue_count: Number of venues (for SMS summary).

    Returns:
        {"email_sent": bool, "sms_sent": bool}
    """
    result = {"email_sent": False, "sms_sent": False}

    email = client.get("contact_email", "")
    name = client.get("contact_name", "")
    phone = client.get("contact_phone", "")

    # Email notification
    if email:
        try:
            from services.notification_service import notify_report_shared

            result["email_sent"] = notify_report_shared(
                client_email=email,
                client_name=name,
                report_title=report_title,
            )
        except Exception as e:
            logger.error("Report email failed for %s: %s", email, e)

    # SMS notification
    if phone and (total_plays or venue_count):
        try:
            from services.notification_service import sms_traction_report

            sms_traction_report(
                phone=phone,
                contact_name=name,
                total_plays=f"{total_plays:,}" if total_plays else "0",
                venue_count=str(venue_count),
            )
            result["sms_sent"] = True
        except Exception as e:
            logger.error("Report SMS failed for %s: %s", phone, e)

    return result


# ---------------------------------------------------------------------------
# Full generation pipeline
# ---------------------------------------------------------------------------

def generate_and_share_report(
    client: dict,
    dashboard_lookup: dict,
    config: dict,
    period_label: str,
    skip_ai_insights: bool = True,
    dry_run: bool = False,
) -> dict:
    """Generate a traction report, upload to portal, and notify the client.

    End-to-end pipeline:
        1. Build TractionReportInput from dashboard data + client info
        2. Generate DOCX via AdvertiserReportGenerator
        3. Upload to Supabase Storage + insert client_reports record
        4. Send email + SMS notification

    Args:
        client: Client dict (from get_reportable_clients()).
        dashboard_lookup: Parsed network dashboard {host_name_lower: {...}}.
        config: App config dict (from config.json).
        period_label: e.g. "January 2026".
        skip_ai_insights: Skip Claude API call (saves cost for bulk runs).
        dry_run: If True, build the report but don't upload/notify.

    Returns:
        {success, client_name, report_path, email_sent, sms_sent, error?}
    """
    from models.report_data import TractionReportInput, VenueRecord
    from services.docx_service import DocxService
    from generators.advertiser_report import AdvertiserReportGenerator
    from services.excel_parser import enrich_report_with_dashboard

    bname = client.get("business_name", "Unknown")
    result = {
        "success": False,
        "client_name": bname,
        "report_path": None,
        "email_sent": False,
        "sms_sent": False,
    }

    try:
        # ── Build venue records from dashboard ────────────────────────────
        venue_records = []
        for host_key, venue_data in dashboard_lookup.items():
            venue_records.append(VenueRecord(
                host_name=venue_data.get("name", host_key),
                business_category=venue_data.get("category", ""),
                city=venue_data.get("city", ""),
                screen_count=int(venue_data.get("screens", 1)),
                monthly_traffic=float(venue_data.get("traffic", 0)),
                dwell_time_minutes=float(venue_data.get("dwell_time", 0)),
                monthly_impressions=float(venue_data.get("impressions", 0)),
            ))

        if not venue_records:
            result["error"] = "No venue data in dashboard"
            logger.warning("No dashboard venue data for %s", bname)
            return result

        # Sort by impressions descending
        venue_records.sort(
            key=lambda v: v.monthly_impressions, reverse=True,
        )

        # Compute totals
        total_impressions = sum(v.monthly_impressions for v in venue_records)
        total_traffic = sum(v.monthly_traffic for v in venue_records)

        # Build TractionReportInput
        report_data = TractionReportInput(
            advertiser_name=bname,
            report_type="traction",
            campaign_period=period_label,
            venue_records=venue_records,
            total_plays=0,  # no NTV360 play data in automated mode
            total_screen_count=len(venue_records),
            total_impressions=total_impressions,
            total_monthly_traffic=total_traffic,
            monthly_rate=client.get("monthly_rate", 0),
            sales_rep=config.get("proposal_settings", {}).get(
                "default_rep", "Mary Michael Cannon"
            ),
            include_insights=not skip_ai_insights,
        )

        # Enrich with dashboard data (fills in any missing fields)
        enrich_report_with_dashboard(report_data, dashboard_lookup)

        if dry_run:
            result["success"] = True
            result["dry_run"] = True
            logger.info("[DRY RUN] Would generate report for %s (%s)", bname, period_label)
            return result

        # ── Generate DOCX ────────────────────────────────────────────────
        claude = None
        if not skip_ai_insights:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if api_key and api_key != "your-api-key-here":
                try:
                    from services.claude_service import ClaudeService

                    model = config.get("proposal_settings", {}).get(
                        "model", "claude-sonnet-4-5-20250929"
                    )
                    claude = ClaudeService(api_key=api_key, model=model)
                except Exception as e:
                    logger.warning("Claude service unavailable: %s", e)

        docx_service = DocxService(config)
        generator = AdvertiserReportGenerator(config, claude, docx_service)

        report_path = generator.generate(report_data)
        result["report_path"] = str(report_path)
        logger.info("Report generated: %s", report_path)

        # ── Share to portal ──────────────────────────────────────────────
        db_row = share_report(report_path, report_data, client)
        if not db_row:
            result["error"] = "Failed to upload/insert report"
            return result

        # ── Notify client ────────────────────────────────────────────────
        title = db_row.get("title", f"{bname} Traction Report - {period_label}")
        notif = notify_client_report(
            client,
            report_title=title,
            total_plays=report_data.total_plays,
            venue_count=len(venue_records),
        )
        result["email_sent"] = notif.get("email_sent", False)
        result["sms_sent"] = notif.get("sms_sent", False)

        result["success"] = True
        logger.info(
            "Report pipeline complete for %s | email=%s sms=%s",
            bname, result["email_sent"], result["sms_sent"],
        )

    except Exception as e:
        result["error"] = str(e)
        logger.error("Report pipeline failed for %s: %s", bname, e, exc_info=True)

    return result
