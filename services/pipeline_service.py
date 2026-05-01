# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Sales pipeline service for opportunity tracking and revenue forecasting.

Manages the full sales pipeline from prospect to close, with stage tracking,
revenue forecasting, and pipeline analytics. Uses Supabase REST API with
local JSON fallback.
"""

import json
import logging
import os
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "pipeline"

# ── Stage Configuration ──────────────────────────────────────────────────────

STAGES = {
    "prospect":      {"label": "Prospect",       "probability": 10, "color": "#6c757d", "order": 0},
    "outreach":      {"label": "Outreach",        "probability": 15, "color": "#17a2b8", "order": 1},
    "engaged":       {"label": "Engaged",         "probability": 30, "color": "#007bff", "order": 2},
    "discovery":     {"label": "Discovery",       "probability": 45, "color": "#6610f2", "order": 3},
    "proposal_sent": {"label": "Proposal Sent",   "probability": 60, "color": "#C5A55A", "order": 4},
    "negotiation":   {"label": "Negotiation",     "probability": 75, "color": "#fd7e14", "order": 5},
    "contract_sent": {"label": "Contract Sent",   "probability": 90, "color": "#28a745", "order": 6},
    "won":           {"label": "Won",             "probability": 100, "color": "#155724", "order": 7},
    "lost":          {"label": "Lost",            "probability": 0,   "color": "#dc3545", "order": 8},
}

# Tier pricing for quick-select
TIERS = {
    "10 Screens":  {"screens": 10, "monthly": 350},
    "20 Screens":  {"screens": 20, "monthly": 500},
    "40 Screens":  {"screens": 40, "monthly": 800},
    "75+ Screens": {"screens": 75, "monthly": 1300},
}


# ── Supabase REST helpers ─────────────────────────────────────────────────────

def _sb_config():
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    if url and key:
        return url, key
    return None, None


def _sb_headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _sb_request(method: str, endpoint: str, data: dict | None = None) -> list | None:
    url, key = _sb_config()
    if not url:
        return None

    full_url = f"{url}/rest/v1/{endpoint}"
    body = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(full_url, data=body, headers=_sb_headers(key), method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:200]
        logger.error("Pipeline REST %s %s HTTP %s: %s", method, endpoint, e.code, err)
        return None
    except Exception as e:
        logger.error("Pipeline REST %s %s failed: %s", method, endpoint, e)
        return None


# ── Local JSON fallback ───────────────────────────────────────────────────────

def _local_file() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "opportunities.json"


def _local_activity_file() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "activity.json"


def _load_local() -> list[dict]:
    path = _local_file()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_local(data: list[dict]):
    path = _local_file()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_local_activity() -> list[dict]:
    path = _local_activity_file()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_local_activity(data: list[dict]):
    path = _local_activity_file()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_opportunity(opp_data: dict) -> dict | None:
    """Create a new pipeline opportunity.

    Args:
        opp_data: Dict with business_name (required) and optional fields:
            contact_name, contact_email, contact_phone, industry, city,
            source, stage, monthly_value, screen_count, tier_name,
            expected_close_date, assigned_rep, notes, tags

    Returns:
        The created opportunity dict, or None on failure.
    """
    now = datetime.now().isoformat()
    opp_data.setdefault("stage", "prospect")
    opp_data.setdefault("source", "manual")
    opp_data.setdefault("probability", STAGES.get(opp_data["stage"], {}).get("probability", 10))
    opp_data.setdefault("assigned_rep", "Mary Michael")
    opp_data.setdefault("created_at", now)
    opp_data.setdefault("updated_at", now)

    # Try Supabase
    result = _sb_request("POST", "pipeline_opportunities", opp_data)
    if result and len(result) > 0:
        _log_activity(result[0]["id"], "created", details=f"Added to pipeline: {opp_data.get('business_name', '')}")
        return result[0]

    # Fallback: local JSON
    import uuid
    opp_data["id"] = str(uuid.uuid4())
    opps = _load_local()
    opps.insert(0, opp_data)
    _save_local(opps)
    _log_activity(opp_data["id"], "created", details=f"Added to pipeline: {opp_data.get('business_name', '')}")
    return opp_data


def get_all_opportunities(stage: str | None = None, city: str | None = None,
                          assigned_rep: str | None = None) -> list[dict]:
    """Get all pipeline opportunities with optional filters."""
    endpoint = "pipeline_opportunities?select=*&order=updated_at.desc"

    if stage:
        endpoint += f"&stage=eq.{stage}"
    if city:
        endpoint += f"&city=eq.{city}"
    if assigned_rep:
        endpoint += f"&assigned_rep=eq.{assigned_rep}"

    result = _sb_request("GET", endpoint)
    if result is not None:
        return result

    # Fallback: local
    opps = _load_local()
    if stage:
        opps = [o for o in opps if o.get("stage") == stage]
    if city:
        opps = [o for o in opps if (o.get("city") or "").lower() == city.lower()]
    if assigned_rep:
        opps = [o for o in opps if o.get("assigned_rep") == assigned_rep]
    return opps


def get_opportunity(opp_id: str) -> dict | None:
    """Get a single opportunity by ID."""
    result = _sb_request("GET", f"pipeline_opportunities?id=eq.{opp_id}&limit=1")
    if result and len(result) > 0:
        return result[0]

    opps = _load_local()
    for o in opps:
        if o.get("id") == opp_id:
            return o
    return None


def update_opportunity(opp_id: str, updates: dict) -> dict | None:
    """Update fields on an opportunity."""
    updates["updated_at"] = datetime.now().isoformat()

    result = _sb_request("PATCH", f"pipeline_opportunities?id=eq.{opp_id}", updates)
    if result and len(result) > 0:
        return result[0]

    # Fallback: local
    opps = _load_local()
    for o in opps:
        if o.get("id") == opp_id:
            o.update(updates)
            _save_local(opps)
            return o
    return None


def delete_opportunity(opp_id: str) -> bool:
    """Delete an opportunity."""
    result = _sb_request("DELETE", f"pipeline_opportunities?id=eq.{opp_id}")
    if result is not None:
        return True

    opps = _load_local()
    opps = [o for o in opps if o.get("id") != opp_id]
    _save_local(opps)
    return True


# ── Stage Management ──────────────────────────────────────────────────────────

def advance_stage(opp_id: str, new_stage: str, performed_by: str = "MCTV Bot") -> dict | None:
    """Move an opportunity to a new stage with automatic probability update."""
    opp = get_opportunity(opp_id)
    if not opp:
        return None

    old_stage = opp.get("stage", "prospect")
    if old_stage == new_stage:
        return opp

    stage_info = STAGES.get(new_stage, {})
    from datetime import datetime as _dt
    updates = {
        "stage": new_stage,
        "probability": stage_info.get("probability", 10),
        "stage_entered_at": _dt.now().isoformat(),
    }

    if new_stage == "won":
        updates["probability"] = 100
    elif new_stage == "lost":
        updates["probability"] = 0

    result = update_opportunity(opp_id, updates)

    _log_activity(opp_id, "stage_change",
                  from_stage=old_stage, to_stage=new_stage,
                  details=f"Moved from {STAGES.get(old_stage, {}).get('label', old_stage)} to {stage_info.get('label', new_stage)}",
                  performed_by=performed_by)

    return result


def mark_lost(opp_id: str, reason: str = "", performed_by: str = "MCTV Bot") -> dict | None:
    """Mark an opportunity as lost with an optional reason."""
    opp = get_opportunity(opp_id)
    if not opp:
        return None

    old_stage = opp.get("stage", "prospect")
    updates = {
        "stage": "lost",
        "probability": 0,
        "loss_reason": reason,
    }

    result = update_opportunity(opp_id, updates)

    _log_activity(opp_id, "stage_change",
                  from_stage=old_stage, to_stage="lost",
                  details=f"Lost: {reason}" if reason else "Marked as lost",
                  performed_by=performed_by)

    return result


# ── Activity Logging ──────────────────────────────────────────────────────────

def _log_activity(opp_id: str, action: str, from_stage: str = "",
                  to_stage: str = "", details: str = "",
                  performed_by: str = "MCTV Bot"):
    """Log an activity on a pipeline opportunity."""
    record = {
        "opportunity_id": opp_id,
        "action": action,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "details": details,
        "performed_by": performed_by,
        "created_at": datetime.now().isoformat(),
    }

    result = _sb_request("POST", "pipeline_activity", record)
    if result is not None:
        return

    # Fallback: local
    activity = _load_local_activity()
    import uuid
    record["id"] = str(uuid.uuid4())
    activity.insert(0, record)
    activity = activity[:1000]  # Keep last 1000
    _save_local_activity(activity)


def get_activity(opp_id: str, limit: int = 50) -> list[dict]:
    """Get activity history for an opportunity."""
    result = _sb_request(
        "GET",
        f"pipeline_activity?opportunity_id=eq.{opp_id}&order=created_at.desc&limit={limit}"
    )
    if result is not None:
        return result

    activity = _load_local_activity()
    return [a for a in activity if a.get("opportunity_id") == opp_id][:limit]


def log_note(opp_id: str, note: str, performed_by: str = "MCTV Bot"):
    """Add a note to an opportunity."""
    _log_activity(opp_id, "note_added", details=note, performed_by=performed_by)


def log_call(opp_id: str, notes: str = "", performed_by: str = "MCTV Bot"):
    """Log a phone call on an opportunity."""
    update_opportunity(opp_id, {"last_contact_date": datetime.now().isoformat()})
    _log_activity(opp_id, "call_logged", details=notes, performed_by=performed_by)


# ── Lead Conversion ──────────────────────────────────────────────────────────

def import_lead_to_pipeline(lead: dict, source: str = "intake_form") -> dict | None:
    """Convert a lead record into a pipeline opportunity."""
    from services.leads_service import calculate_lead_score

    score = calculate_lead_score(lead)

    # Map lead interest to initial stage
    interest = (lead.get("interest_level") or "").lower()
    if "ready" in interest:
        initial_stage = "discovery"
    elif "very" in interest:
        initial_stage = "engaged"
    elif "interested" in interest:
        initial_stage = "outreach"
    else:
        initial_stage = "prospect"

    # Estimate value based on city/industry
    estimated_monthly = 500  # Default to 20-screen tier
    city = (lead.get("city") or "").lower()
    if city in ("oxford", "starkville", "tupelo"):
        estimated_monthly = 500

    opp_data = {
        "lead_id": lead.get("id", ""),
        "business_name": lead.get("business_name", "Unknown"),
        "contact_name": lead.get("contact_name", ""),
        "contact_email": lead.get("contact_email", ""),
        "contact_phone": lead.get("contact_phone", ""),
        "industry": lead.get("industry", ""),
        "city": lead.get("city", ""),
        "source": source,
        "stage": initial_stage,
        "monthly_value": estimated_monthly,
        "screen_count": 20,
        "tier_name": "20 Screens",
        "expected_close_date": (date.today() + timedelta(days=30)).isoformat(),
        "notes": lead.get("goals", "") or lead.get("additional_notes", ""),
        "nurture_sequence": "new_lead",
        "nurture_step": 0,
    }

    return create_opportunity(opp_data)


# ── Pipeline Analytics ────────────────────────────────────────────────────────

def get_pipeline_summary() -> dict:
    """Get a summary of the pipeline for the dashboard.

    Returns:
        Dict with total_opportunities, total_pipeline_value,
        weighted_pipeline_value, by_stage (counts + values),
        avg_deal_size, conversion_rate, deals_won_this_month, mrr_won.
    """
    opps = get_all_opportunities()

    # Exclude lost/won from active pipeline
    active = [o for o in opps if o.get("stage") not in ("won", "lost")]
    won = [o for o in opps if o.get("stage") == "won"]
    lost = [o for o in opps if o.get("stage") == "lost"]

    # By stage
    by_stage = {}
    for stage_key, stage_info in STAGES.items():
        stage_opps = [o for o in opps if o.get("stage") == stage_key]
        value = sum(float(o.get("monthly_value", 0)) for o in stage_opps)
        by_stage[stage_key] = {
            "count": len(stage_opps),
            "value": value,
            "weighted_value": value * stage_info["probability"] / 100,
            "label": stage_info["label"],
            "color": stage_info["color"],
        }

    total_value = sum(float(o.get("monthly_value", 0)) for o in active)
    weighted_value = sum(
        float(o.get("monthly_value", 0)) * float(o.get("probability", 0)) / 100
        for o in active
    )

    # This month's wins
    this_month = date.today().replace(day=1).isoformat()
    won_this_month = [
        o for o in won
        if (o.get("updated_at") or o.get("created_at", "")) >= this_month
    ]
    mrr_won = sum(float(o.get("monthly_value", 0)) for o in won_this_month)

    # Conversion rate (won / (won + lost))
    total_decided = len(won) + len(lost)
    conversion_rate = (len(won) / total_decided * 100) if total_decided > 0 else 0

    # Average deal size
    avg_deal = total_value / len(active) if active else 0

    return {
        "total_opportunities": len(active),
        "total_pipeline_value": total_value,
        "weighted_pipeline_value": weighted_value,
        "by_stage": by_stage,
        "avg_deal_size": avg_deal,
        "conversion_rate": conversion_rate,
        "deals_won_this_month": len(won_this_month),
        "mrr_won_this_month": mrr_won,
        "total_won": len(won),
        "total_lost": len(lost),
    }


def get_revenue_forecast(months: int = 3) -> list[dict]:
    """Forecast revenue for the next N months based on weighted pipeline.

    Returns list of dicts: [{month, expected_mrr, best_case, worst_case}]
    """
    active = [o for o in get_all_opportunities() if o.get("stage") not in ("won", "lost")]

    forecast = []
    for i in range(months):
        target_date = date.today() + timedelta(days=30 * (i + 1))
        month_label = target_date.strftime("%B %Y")

        # Deals expected to close by this month
        closing = [
            o for o in active
            if o.get("expected_close_date") and o["expected_close_date"] <= target_date.isoformat()
        ]

        expected = sum(
            float(o.get("monthly_value", 0)) * float(o.get("probability", 0)) / 100
            for o in closing
        )
        best_case = sum(float(o.get("monthly_value", 0)) for o in closing)
        worst_case = sum(
            float(o.get("monthly_value", 0))
            for o in closing
            if float(o.get("probability", 0)) >= 75
        )

        forecast.append({
            "month": month_label,
            "expected_mrr": expected,
            "best_case": best_case,
            "worst_case": worst_case,
            "deal_count": len(closing),
        })

    return forecast


def get_deals_needing_action() -> list[dict]:
    """Get opportunities that need attention (overdue actions, stale deals)."""
    opps = get_all_opportunities()
    today = date.today().isoformat()
    needs_action = []

    for opp in opps:
        if opp.get("stage") in ("won", "lost"):
            continue

        reason = None

        # Overdue next action
        next_date = opp.get("next_action_date")
        if next_date and next_date <= today:
            reason = f"Overdue action: {opp.get('next_action', 'Follow up')}"

        # Stale deal (no update in 7+ days)
        elif opp.get("updated_at"):
            updated = opp["updated_at"][:10]
            stale_date = (date.today() - timedelta(days=7)).isoformat()
            if updated <= stale_date:
                reason = "No activity in 7+ days"

        if reason:
            opp["_action_reason"] = reason
            needs_action.append(opp)

    return needs_action


def get_stage_options() -> list[tuple[str, str]]:
    """Return stage options as [(key, label)] sorted by pipeline order."""
    return sorted(
        [(k, v["label"]) for k, v in STAGES.items()],
        key=lambda x: STAGES[x[0]]["order"]
    )
