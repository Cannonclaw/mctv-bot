# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Category exclusivity conflict checker.

Some contracts grant a client exclusive rights to advertise in their industry
within specific markets. Before sending a new proposal or contract, we need
to make sure we're not double-booking that exclusivity.

A "conflict" is any active or signed contract with:
  - exclusive_category that case-insensitively overlaps the proposed category
  - markets that overlap the proposed markets
  - end_date in the future (or null/auto-renewing)
"""

from __future__ import annotations
import logging
from datetime import date, datetime

from services.supabase_client import query_table

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _overlap(a: list, b: list) -> list[str]:
    """Case-insensitive intersection of two market lists."""
    lower_b = {(m or "").strip().lower() for m in (b or [])}
    return [m for m in (a or []) if (m or "").strip().lower() in lower_b]


def _is_active(contract: dict, today: date) -> bool:
    """Active if signed/active and end_date in the future (or absent + auto_renew)."""
    status = (contract.get("status") or "").lower()
    if status not in ("signed", "active"):
        return False
    end = contract.get("end_date")
    if not end:
        return bool(contract.get("auto_renew"))
    try:
        end_d = datetime.fromisoformat(str(end)).date()
    except (ValueError, TypeError):
        return True  # unknown end → assume still active
    if end_d >= today:
        return True
    return bool(contract.get("auto_renew"))


def find_conflicts(category: str, markets: list[str],
                   exclude_contract_id: str = "") -> list[dict]:
    """Return active contracts whose exclusivity blocks this category+markets.

    Args:
        category: industry / category being proposed (e.g. "Real Estate").
        markets: markets the proposal targets.
        exclude_contract_id: skip this id (useful when re-checking your own).

    Returns:
        list of conflict dicts with: contract_id, business_name, exclusive_category,
        overlapping_markets, end_date, monthly_rate.
    """
    cat = _normalize(category)
    if not cat or not markets:
        return []

    rows = query_table(
        "contracts",
        select=("id,client_id,title,exclusive_category,markets,monthly_rate,"
                "end_date,start_date,status,auto_renew,contract_type"),
        order="-created_at",
    ) or []

    today = date.today()
    conflicts = []

    for c in rows:
        if exclude_contract_id and c.get("id") == exclude_contract_id:
            continue
        if not c.get("exclusive_category"):
            continue
        if not _is_active(c, today):
            continue

        c_cat = _normalize(c["exclusive_category"])
        if c_cat != cat and cat not in c_cat and c_cat not in cat:
            continue

        overlapping = _overlap(c.get("markets") or [], markets)
        if not overlapping:
            continue

        # Resolve client name
        client_rows = query_table(
            "clients", select="business_name",
            filters={"id": c.get("client_id", "")}, limit=1,
        )
        business_name = (client_rows[0].get("business_name", "")
                          if client_rows else c.get("title", ""))

        conflicts.append({
            "contract_id": c.get("id"),
            "business_name": business_name,
            "exclusive_category": c.get("exclusive_category"),
            "overlapping_markets": overlapping,
            "all_markets": c.get("markets") or [],
            "end_date": c.get("end_date") or "",
            "monthly_rate": float(c.get("monthly_rate", 0) or 0),
            "contract_type": c.get("contract_type") or "",
        })

    return conflicts


def is_clear(category: str, markets: list[str],
             exclude_contract_id: str = "") -> bool:
    """True if there are zero exclusivity conflicts."""
    return len(find_conflicts(category, markets, exclude_contract_id)) == 0


def format_conflict_message(conflicts: list[dict]) -> str:
    """Human-readable warning suitable for surfacing in the UI."""
    if not conflicts:
        return ""
    lines = [f"Found {len(conflicts)} exclusivity conflict(s):"]
    for c in conflicts:
        markets = ", ".join(c["overlapping_markets"])
        end = c["end_date"][:10] if c["end_date"] else "no end date"
        lines.append(
            f"  • {c['business_name']} holds '{c['exclusive_category']}' "
            f"exclusivity in {markets} until {end} "
            f"(${c['monthly_rate']:,.0f}/mo)."
        )
    return "\n".join(lines)
