# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""NTV360 play data snapshot service.

Stores and retrieves aggregated NTV360 play data in Supabase so automated
monthly reports can include real play counts instead of showing zeros.

Flow:
    1. User uploads NTV360 Excel via Reports page
    2. parse_excel() extracts play records
    3. save_snapshot() stores aggregated data in ntv360_snapshots table
    4. scripts/monthly_reports.py calls get_latest_snapshot() to enrich reports
"""

import json
import logging
from datetime import date

logger = logging.getLogger(__name__)


def save_snapshot(
    venue_records: list,
    total_plays: int,
    total_air_time: str = "",
    snapshot_month: str | None = None,
    uploaded_by: str = "",
    source_file: str = "",
) -> bool:
    """Store aggregated NTV360 play data as a monthly snapshot.

    Args:
        venue_records: List of VenueRecord-like dicts or dataclass instances
            with host_name, total_plays, total_air_time, etc.
        total_plays: Total play count across all venues.
        total_air_time: Total air time string (e.g., "125h 30m 15s").
        snapshot_month: Month key in YYYY-MM format. Defaults to current month.
        uploaded_by: Team member who uploaded the data.
        source_file: Original Excel filename.

    Returns:
        True if saved successfully.
    """
    try:
        from services.supabase_client import upsert_row
    except ImportError:
        logger.error("supabase_client not available")
        return False

    if not snapshot_month:
        snapshot_month = date.today().strftime("%Y-%m")

    # Convert venue records to serializable dicts
    venue_data = []
    for v in venue_records:
        if hasattr(v, "__dict__"):
            # Dataclass or object — convert to dict
            d = {}
            for key in ("host_name", "total_plays", "total_air_time",
                        "first_aired", "last_aired", "pct_of_total",
                        "business_category", "city", "screen_count",
                        "monthly_traffic", "dwell_time_minutes",
                        "monthly_impressions"):
                val = getattr(v, key, None)
                if val is not None:
                    d[key] = val
            venue_data.append(d)
        elif isinstance(v, dict):
            venue_data.append(v)

    data = {
        "snapshot_month": snapshot_month,
        "total_plays": total_plays,
        "total_air_time": total_air_time,
        "venue_count": len(venue_data),
        "venue_data": json.dumps(venue_data),
        "uploaded_by": uploaded_by,
        "source_file": source_file,
    }

    result = upsert_row("ntv360_snapshots", data, on_conflict="snapshot_month")

    if result:
        logger.info(
            "NTV360 snapshot saved: %s — %d plays across %d venues",
            snapshot_month, total_plays, len(venue_data),
        )
        return True
    else:
        logger.error("Failed to save NTV360 snapshot for %s", snapshot_month)
        return False


def get_latest_snapshot(target_month: str | None = None) -> dict | None:
    """Retrieve the most recent NTV360 snapshot.

    Args:
        target_month: Specific month in YYYY-MM format. If None, returns
            the most recent snapshot regardless of month.

    Returns:
        Dict with total_plays, total_air_time, venue_count, venue_data,
        or None if no snapshot exists.
    """
    try:
        from services.supabase_client import query_table

        if target_month:
            rows = query_table(
                "ntv360_snapshots",
                select="*",
                filters={"snapshot_month": target_month},
                limit=1,
            )
        else:
            rows = query_table(
                "ntv360_snapshots",
                select="*",
                order="-snapshot_month",
                limit=1,
            )

        if not rows:
            return None

        row = rows[0]

        # Parse venue_data JSON
        venue_data = row.get("venue_data", "[]")
        if isinstance(venue_data, str):
            try:
                venue_data = json.loads(venue_data)
            except (json.JSONDecodeError, TypeError):
                venue_data = []

        return {
            "snapshot_month": row.get("snapshot_month", ""),
            "total_plays": int(row.get("total_plays", 0)),
            "total_air_time": row.get("total_air_time", ""),
            "venue_count": int(row.get("venue_count", 0)),
            "venue_data": venue_data,
            "uploaded_by": row.get("uploaded_by", ""),
            "source_file": row.get("source_file", ""),
            "created_at": row.get("created_at", ""),
        }

    except Exception as e:
        logger.error("Failed to retrieve NTV360 snapshot: %s", e)
        return None


def get_play_data_for_report(target_month: str) -> dict:
    """Get NTV360 play data formatted for report generation.

    Tries the exact target month first, then falls back to the most
    recent available snapshot.

    Args:
        target_month: YYYY-MM format (e.g., "2026-01").

    Returns:
        Dict with:
            - total_plays: int
            - total_air_time: str
            - venue_plays: dict mapping host_name_lower -> {total_plays, total_air_time}
            - snapshot_month: str (the month the data is from)
            - is_exact_match: bool (True if data is from the target month)
    """
    result = {
        "total_plays": 0,
        "total_air_time": "",
        "venue_plays": {},
        "snapshot_month": "",
        "is_exact_match": False,
    }

    # Try exact month first
    snapshot = get_latest_snapshot(target_month)
    if snapshot:
        result["is_exact_match"] = True
    else:
        # Fall back to most recent
        snapshot = get_latest_snapshot()
        if not snapshot:
            return result

    result["total_plays"] = snapshot.get("total_plays", 0)
    result["total_air_time"] = snapshot.get("total_air_time", "")
    result["snapshot_month"] = snapshot.get("snapshot_month", "")

    # Build venue lookup
    for venue in snapshot.get("venue_data", []):
        host = (venue.get("host_name") or "").strip().lower()
        if host:
            result["venue_plays"][host] = {
                "total_plays": int(venue.get("total_plays", 0)),
                "total_air_time": venue.get("total_air_time", ""),
            }

    return result
