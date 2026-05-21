# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Daily task email cron.

Runs every weekday at 13:00 UTC (= 7 AM CDT, 6 AM CST).
For each active team member:
  1. Refresh auto-generated tasks from QBO / pipeline / NPS / Field Notes
  2. Compose a personalized email (overdue, today, group, this week)
  3. Send via notification_service
  4. Log result to daily_task_email_log

Drop into: mctv-bot/scripts/daily_tasks.py

Render cron service config:
  Service name:    mctv-daily-tasks
  Type:            Cron Job
  Schedule:        0 13 * * 1-5     (weekdays 13:00 UTC)
  Command:         python scripts/daily_tasks.py
  Env vars:        ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
                   GMAIL_USER, GMAIL_APP_PASSWORD (or whatever notification_service uses)
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Make 'services' importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from supabase import create_client

import services.task_service as task_service
from services.notification_service import _send_email  # existing helper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("daily_tasks")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _supabase():
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"],
    )


def _load_active_team_members() -> list[dict]:
    """Return all active team members. Tolerates schema variation."""
    sb = _supabase()
    # Try a few plausible table names. Adjust to your actual schema.
    for table_name in ("team_members", "users", "staff"):
        try:
            res = sb.table(table_name).select("*").execute()
            if res.data:
                # Best-effort filter to active members only
                rows = [r for r in res.data if r.get("status") != "inactive" and r.get("active") is not False]
                if rows:
                    logger.info("Loaded %d team members from %s", len(rows), table_name)
                    return rows
        except Exception as e:  # noqa: BLE001
            logger.debug("table %s not usable: %s", table_name, e)
    logger.warning("No team members loaded — nothing to send.")
    return []


def _log_send(team_member_id: str, subject: str, task_count: int, status: str, error: str | None = None) -> None:
    try:
        _supabase().table("daily_task_email_log").insert({
            "team_member_id": team_member_id,
            "subject": subject,
            "body_summary": "auto",
            "task_count": task_count,
            "status": status,
            "error_message": error,
        }).execute()
    except Exception as e:  # noqa: BLE001
        logger.warning("could not write email log row: %s", e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    started = datetime.now(timezone.utc)
    logger.info("daily_tasks cron starting at %s UTC", started.isoformat())

    # 1. Refresh auto-generated tasks
    try:
        gen_counts = task_service.generate_from_signals()
        logger.info("auto-gen produced: %s", gen_counts)
    except Exception as e:  # noqa: BLE001
        logger.exception("auto-generation failed; continuing with existing tasks: %s", e)

    # 2. Send per-member emails
    members = _load_active_team_members()
    if not members:
        logger.warning("No active team members — exiting cleanly.")
        return 0

    sent, skipped, failed = 0, 0, 0
    for m in members:
        tm_id = m.get("id") or m.get("email")
        tm_email = m.get("email")
        if not tm_email:
            logger.info("skip member %s: no email on file", tm_id)
            skipped += 1
            continue

        try:
            payload = task_service.build_email_for_member(m)
            if not payload:
                logger.info("skip %s: nothing to send", tm_email)
                _log_send(tm_id, "(skipped — empty)", 0, "skipped")
                skipped += 1
                continue

            _send_email(
                to=tm_email,
                subject=payload["subject"],
                html_body=payload["html_body"],
                plain_body=payload["plain_body"],
            )
            _log_send(tm_id, payload["subject"], payload["task_count"], "sent")
            sent += 1
            logger.info("sent to %s (%d tasks)", tm_email, payload["task_count"])
        except Exception as e:  # noqa: BLE001
            failed += 1
            _log_send(tm_id, "(error)", 0, "failed", str(e))
            logger.exception("send failed for %s: %s", tm_email, e)

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    logger.info(
        "daily_tasks cron complete in %.1fs — sent=%d skipped=%d failed=%d",
        duration, sent, skipped, failed,
    )
    # Exit non-zero if everything failed so Render flags it
    if sent == 0 and failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
