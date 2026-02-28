# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Automated lead follow-up cron script.

Handles three types of automated lead engagement:
  1. Welcome emails — sent to new leads ~24h after submission
  2. Nurture drip — 3-step email sequence over 14 days for uncontacted leads
  3. Team reminders — daily digest of leads needing manual follow-up

Run manually:
    python scripts/lead_followups.py
    python scripts/lead_followups.py --dry-run

Schedule on Render:
    Add a cron job in render.yaml targeting this script.
    Recommended: 8:00 AM CT daily.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
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
logger = logging.getLogger("lead_followups")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# How long after submission to send the welcome email (hours)
WELCOME_DELAY_HOURS = 24

# Nurture drip schedule (days after submission)
NURTURE_STEPS = {
    1: 3,   # Step 1: value prop at day 3
    2: 7,   # Step 2: social proof at day 7
    3: 14,  # Step 3: final check-in at day 14
}

# Only drip to leads in these statuses (don't email people already in talks)
DRIP_ELIGIBLE_STATUSES = {"new"}


def _parse_datetime(value: str) -> datetime | None:
    """Parse an ISO datetime string, handling various formats."""
    if not value:
        return None
    try:
        # Handle both "2026-02-28T10:30:00" and "2026-02-28T10:30:00.123456+00:00"
        clean = value.replace("Z", "+00:00")
        return datetime.fromisoformat(clean).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _get_lead_metadata(lead_id: str) -> dict:
    """Get lead follow-up metadata from Supabase (or empty dict)."""
    try:
        from services.supabase_client import query_table

        rows = query_table(
            "lead_followup_log",
            select="*",
            filters={"lead_id": lead_id},
        )
        if rows:
            return rows[0]
    except Exception:
        pass
    return {}


def _log_followup(lead_id: str, action: str, step: int = 0) -> bool:
    """Record a follow-up action in Supabase."""
    try:
        from services.supabase_client import upsert_row

        data = {
            "lead_id": lead_id,
            f"last_{action}": datetime.now().isoformat(),
        }
        if step:
            data["nurture_step"] = step

        result = upsert_row("lead_followup_log", data, on_conflict="lead_id")
        return result is not None
    except Exception as e:
        logger.error("Failed to log followup for %s: %s", lead_id, e)
        return False


def process_welcome_emails(leads: list[dict], dry_run: bool = False) -> int:
    """Send welcome emails to new leads submitted > WELCOME_DELAY_HOURS ago.

    Returns number of emails sent.
    """
    from services.notification_service import send_lead_welcome_email

    now = datetime.now()
    sent_count = 0

    for lead in leads:
        status = (lead.get("status") or "").lower()
        if status != "new":
            continue

        # Must have an email
        if not lead.get("contact_email"):
            continue

        # Check timing — submitted more than WELCOME_DELAY_HOURS ago
        submitted = _parse_datetime(lead.get("submitted_at", ""))
        if not submitted:
            continue

        hours_since = (now - submitted).total_seconds() / 3600
        if hours_since < WELCOME_DELAY_HOURS:
            continue

        # Don't send if too old (> 3 days)
        if hours_since > 72:
            continue

        # Check if we already sent a welcome email
        meta = _get_lead_metadata(lead.get("id", ""))
        if meta.get("last_welcome"):
            continue

        bname = lead.get("business_name", "Unknown")

        if dry_run:
            logger.info("[DRY RUN] Would send welcome email to %s (%s)",
                        bname, lead.get("contact_email"))
            sent_count += 1
            continue

        logger.info("Sending welcome email to %s...", bname)
        success = send_lead_welcome_email(lead)

        if success:
            _log_followup(lead["id"], "welcome")
            sent_count += 1
            logger.info("  -> Welcome email sent to %s", bname)
        else:
            logger.error("  -> Failed to send welcome to %s", bname)

    return sent_count


def process_nurture_drips(leads: list[dict], dry_run: bool = False) -> int:
    """Send nurture drip emails based on timing since submission.

    Returns number of emails sent.
    """
    from services.notification_service import send_lead_nurture_email

    now = datetime.now()
    sent_count = 0

    for lead in leads:
        status = (lead.get("status") or "").lower()
        if status not in DRIP_ELIGIBLE_STATUSES:
            continue

        if not lead.get("contact_email"):
            continue

        submitted = _parse_datetime(lead.get("submitted_at", ""))
        if not submitted:
            continue

        days_since = (now - submitted).days
        lead_id = lead.get("id", "")
        bname = lead.get("business_name", "Unknown")

        # Check existing nurture progress
        meta = _get_lead_metadata(lead_id)
        current_step = int(meta.get("nurture_step", 0))

        # Determine next step to send
        next_step = current_step + 1
        if next_step > 3:
            continue  # Already completed all nurture steps

        required_days = NURTURE_STEPS.get(next_step)
        if required_days is None or days_since < required_days:
            continue

        if dry_run:
            logger.info("[DRY RUN] Would send nurture step %d to %s (day %d)",
                        next_step, bname, days_since)
            sent_count += 1
            continue

        logger.info("Sending nurture step %d to %s (day %d)...",
                    next_step, bname, days_since)
        success = send_lead_nurture_email(lead, next_step)

        if success:
            _log_followup(lead_id, "nurture", step=next_step)
            sent_count += 1
            logger.info("  -> Nurture step %d sent to %s", next_step, bname)
        else:
            logger.error("  -> Failed to send nurture step %d to %s",
                        next_step, bname)

    return sent_count


def process_team_reminders(leads: list[dict], dry_run: bool = False) -> bool:
    """Send the team a daily digest of leads needing attention.

    Includes:
      - Leads with overdue follow_up_date
      - Hot leads (score >= 70) still in "new" status after 2+ days
      - Leads in "contacted" status with no activity for 7+ days

    Returns True if reminder was sent (or not needed).
    """
    from services.leads_service import calculate_lead_score
    from services.notification_service import send_lead_followup_reminder

    now = datetime.now()
    needs_attention = []

    for lead in leads:
        status = (lead.get("status") or "").lower()
        lead_id = lead.get("id", "")
        score = calculate_lead_score(lead)
        lead["_score"] = score

        # 1. Overdue follow-up date
        fu_date_str = lead.get("follow_up_date", "")
        if fu_date_str:
            try:
                fu_date = datetime.strptime(str(fu_date_str)[:10], "%Y-%m-%d")
                if fu_date.date() <= now.date():
                    days_overdue = (now.date() - fu_date.date()).days
                    lead["_followup_reason"] = (
                        f"Overdue follow-up ({days_overdue} day(s) past due)"
                    )
                    needs_attention.append(lead)
                    continue
            except (ValueError, TypeError):
                pass

        # 2. Hot leads still in "new" status
        submitted = _parse_datetime(lead.get("submitted_at", ""))
        if status == "new" and score >= 70 and submitted:
            days_since = (now - submitted).days
            if days_since >= 2:
                lead["_followup_reason"] = (
                    f"Hot lead (score {score}) - still 'new' after {days_since} days"
                )
                needs_attention.append(lead)
                continue

        # 3. Contacted but stale
        if status == "contacted" and submitted:
            days_since = (now - submitted).days
            if days_since >= 7:
                lead["_followup_reason"] = (
                    f"Contacted {days_since} days ago - no progress to proposal"
                )
                needs_attention.append(lead)
                continue

    if not needs_attention:
        logger.info("No leads need team follow-up today.")
        return True

    logger.info("%d lead(s) need attention", len(needs_attention))

    if dry_run:
        for lead in needs_attention:
            logger.info(
                "  [%s] %s (score %d) — %s",
                lead.get("status", "?").upper(),
                lead.get("business_name", "Unknown"),
                lead.get("_score", 0),
                lead.get("_followup_reason", ""),
            )
        return True

    return send_lead_followup_reminder(needs_attention)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="MCTV Automated Lead Follow-up",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without sending emails",
    )
    args = parser.parse_args()

    logger.info("Starting lead follow-up processing...")

    # Load all leads
    from services.leads_service import get_all_leads

    leads = get_all_leads()
    if not leads:
        logger.info("No leads found. Nothing to do.")
        return 0

    # Filter to non-closed leads
    active_leads = [
        l for l in leads
        if (l.get("status") or "").lower() not in ("closed", "lost", "converted")
    ]

    logger.info("Found %d active lead(s) out of %d total", len(active_leads), len(leads))

    # ── Step 1: Welcome emails ────────────────────────────────────────────
    try:
        welcome_count = process_welcome_emails(active_leads, args.dry_run)
        logger.info("Welcome emails: %d sent", welcome_count)
    except Exception as e:
        logger.error("Welcome emails failed: %s", e, exc_info=True)

    # ── Step 2: Nurture drips ─────────────────────────────────────────────
    try:
        nurture_count = process_nurture_drips(active_leads, args.dry_run)
        logger.info("Nurture drips: %d sent", nurture_count)
    except Exception as e:
        logger.error("Nurture drips failed: %s", e, exc_info=True)

    # ── Step 3: Team reminders ────────────────────────────────────────────
    try:
        reminder_sent = process_team_reminders(active_leads, args.dry_run)
        logger.info("Team reminder: %s", "sent" if reminder_sent else "failed")
    except Exception as e:
        logger.error("Team reminders failed: %s", e, exc_info=True)

    logger.info("Lead follow-up processing complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
