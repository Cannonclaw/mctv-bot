# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Per-rep performance + commission service.

Attribution rule: a contract counts toward a rep if EITHER
  (a) contract.created_by matches the rep's name, OR
  (b) the client's assigned_rep matches the rep's name.

Commission accrues monthly on every active contract:
    accrual = monthly_rate * client.commission_rate (default 0.10)

YTD commission = sum of accruals across each calendar month the contract
was active in the current year. MTD commission = current calendar month.
"""

from __future__ import annotations
import logging
from datetime import date, datetime
from collections import defaultdict

from services.supabase_client import query_table, upsert_row

logger = logging.getLogger(__name__)

DEFAULT_COMMISSION_RATE = 0.10


# ── Attribution helpers ─────────────────────────────────────────────────────

def _matches_rep(value: str, rep_full: str, rep_first: str) -> bool:
    v = (value or "").strip().lower()
    if not v:
        return False
    return (rep_full.lower() in v) or (v in rep_full.lower()) or \
           (rep_first.lower() in v)


def _months_between(start_d: date, end_d: date) -> int:
    """Inclusive months between two dates (capped at 0 if reversed)."""
    if not start_d or not end_d or end_d < start_d:
        return 0
    return (end_d.year - start_d.year) * 12 + (end_d.month - start_d.month) + 1


# ── Core metrics ────────────────────────────────────────────────────────────

def compute_rep_metrics(rep_full: str, rep_first: str = "") -> dict:
    """Roll up everything a rep's dashboard needs in one query pass."""
    today = date.today()
    if not rep_first:
        parts = rep_full.split()
        rep_first = parts[0] if parts else rep_full

    contracts = query_table("contracts", order="-created_at", limit=500) or []
    clients = query_table("clients", select="id,business_name,assigned_rep,commission_rate", limit=500) or []
    client_lookup = {c["id"]: c for c in clients}

    deals = query_table("pipeline_opportunities", order="-updated_at", limit=500) or []

    leads = query_table("leads", order="-submitted_at", limit=200) or []

    # Filter contracts to this rep
    my_contracts = []
    for c in contracts:
        client = client_lookup.get(c.get("client_id", ""), {})
        if (_matches_rep(c.get("created_by", ""), rep_full, rep_first)
                or _matches_rep(client.get("assigned_rep", ""), rep_full, rep_first)):
            c["_client"] = client
            my_contracts.append(c)

    active = [c for c in my_contracts if c.get("status") in ("signed", "active")]
    won = [c for c in my_contracts if c.get("status") in ("active", "signed", "expired")]

    mrr_attributed = sum(float(c.get("monthly_rate", 0) or 0) for c in active)

    # Pipeline (deals)
    my_deals = [d for d in deals
                if _matches_rep(d.get("assigned_rep", ""), rep_full, rep_first)]
    OPEN = {"prospect", "outreach", "engaged", "discovery", "proposal_sent",
            "negotiation", "contract_sent",
            "identified", "first_visit", "pitched", "agreement_sent",
            "install_scheduled"}
    open_deals = [d for d in my_deals if d.get("stage") in OPEN]
    pipeline_value = sum(float(d.get("monthly_value", 0) or 0) for d in open_deals)
    weighted_pipeline = sum(
        float(d.get("monthly_value", 0) or 0) * (int(d.get("probability", 0) or 0) / 100.0)
        for d in open_deals
    )

    # Hot leads
    try:
        from services.leads_service import calculate_lead_score
        hot_leads = [l for l in leads if calculate_lead_score(l) >= 75]
    except Exception:
        hot_leads = []

    # Commission accrual — per active contract, per month it was active in current year
    ytd_commission = 0.0
    mtd_commission = 0.0
    breakdown_ytd: list[dict] = []
    breakdown_mtd: list[dict] = []
    year_start = date(today.year, 1, 1)
    month_start = date(today.year, today.month, 1)

    for c in active:
        client = c.get("_client") or {}
        rate = float(client.get("commission_rate")
                      if client.get("commission_rate") is not None
                      else DEFAULT_COMMISSION_RATE)
        monthly = float(c.get("monthly_rate", 0) or 0)
        if monthly <= 0:
            continue

        sd_str = c.get("start_date") or ""
        try:
            sd = datetime.fromisoformat(sd_str).date() if sd_str else year_start
        except (ValueError, TypeError):
            sd = year_start
        ed_str = c.get("end_date") or ""
        try:
            ed = datetime.fromisoformat(ed_str).date() if ed_str else today
        except (ValueError, TypeError):
            ed = today

        # Months active in this year up to today
        ytd_start = max(sd, year_start)
        ytd_end = min(ed, today)
        ytd_months = _months_between(date(ytd_start.year, ytd_start.month, 1),
                                      date(ytd_end.year, ytd_end.month, 1))
        commission_y = monthly * rate * ytd_months
        ytd_commission += commission_y
        breakdown_ytd.append({
            "contract_id": c.get("id"),
            "client_name": client.get("business_name", ""),
            "monthly_rate": monthly,
            "commission_rate": rate,
            "months_in_year": ytd_months,
            "amount": round(commission_y, 2),
        })

        # MTD: 1 month if active in current month
        if sd <= today and ed >= month_start:
            commission_m = monthly * rate
            mtd_commission += commission_m
            breakdown_mtd.append({
                "contract_id": c.get("id"),
                "client_name": client.get("business_name", ""),
                "amount": round(commission_m, 2),
            })

    # Recent wins (active contracts created in last 60 days)
    cutoff_60 = (today - timedelta(days=60)).isoformat() if False else None
    from datetime import timedelta as _td
    cutoff = (today - _td(days=60)).isoformat()
    recent_wins = [c for c in active
                    if (c.get("created_at") or "") >= cutoff][:10]

    # Stalled deals owned by this rep
    stalled = []
    THRESHOLDS = {
        "outreach": 7, "engaged": 10, "discovery": 14,
        "proposal_sent": 10, "negotiation": 14, "contract_sent": 7,
        "prospect": 21, "first_visit": 14, "pitched": 14,
        "agreement_sent": 10, "install_scheduled": 14,
    }
    for d in open_deals:
        threshold = THRESHOLDS.get(d.get("stage", ""))
        if not threshold:
            continue
        entered = (d.get("stage_entered_at") or d.get("updated_at") or "")[:10]
        try:
            entered_d = date.fromisoformat(entered)
            days = (today - entered_d).days
            if days >= threshold:
                d["_days_stalled"] = days
                stalled.append(d)
        except (ValueError, TypeError):
            pass
    stalled.sort(key=lambda x: -x.get("_days_stalled", 0))

    return {
        "rep": rep_full,
        "as_of": today.isoformat(),
        # Revenue
        "mrr_attributed": round(mrr_attributed, 2),
        "active_contract_count": len(active),
        "won_contract_count": len(won),
        # Commission
        "ytd_commission": round(ytd_commission, 2),
        "mtd_commission": round(mtd_commission, 2),
        "breakdown_ytd": breakdown_ytd,
        "breakdown_mtd": breakdown_mtd,
        # Pipeline
        "open_deal_count": len(open_deals),
        "pipeline_value": round(pipeline_value, 2),
        "weighted_pipeline": round(weighted_pipeline, 2),
        # Activity
        "hot_lead_count": len(hot_leads),
        "stalled_deal_count": len(stalled),
        "stalled_deals": stalled[:10],
        "recent_wins": recent_wins,
        "active_contracts": active[:25],
    }


# ── Payout ledger ───────────────────────────────────────────────────────────

def accrue_current_month(rep_full: str, rep_first: str = "") -> dict | None:
    """Snapshot the rep's MTD commission into the commission_payouts table.

    Idempotent — re-running on the same (rep, year, month) updates the
    existing row instead of creating a duplicate.
    """
    metrics = compute_rep_metrics(rep_full, rep_first)
    today = date.today()
    payload = {
        "rep_name": rep_full,
        "period_year": today.year,
        "period_month": today.month,
        "amount": metrics["mtd_commission"],
        "status": "accrued",
        "breakdown": metrics["breakdown_mtd"],
    }
    return upsert_row("commission_payouts", payload,
                      on_conflict="rep_name,period_year,period_month")


def list_payouts(rep_full: str, limit: int = 12) -> list:
    """Return recent payout rows for a rep, newest first."""
    return query_table(
        "commission_payouts",
        filters={"rep_name": rep_full},
        order="-period_year",
        limit=limit,
    )
