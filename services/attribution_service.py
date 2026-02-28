# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.

"""Lead source attribution and ROI analytics.

Traces the full funnel: leads -> clients -> contracts -> invoices
using the existing how_heard field on leads and lead_id FK on clients.

Since Supabase REST does not support JOINs, we fetch all relevant tables
and join in Python (same pattern as generate_briefing() in briefing_service).
"""

import logging
from datetime import datetime, date
from collections import defaultdict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source label normalization
# ---------------------------------------------------------------------------

SOURCE_LABELS = {
    "Saw a screen in a local business": "Saw a Screen",
    "Referral from another business": "Referral",
    "Social media": "Social Media",
    "Website": "Website",
    "Someone from MCTV reached out": "Outbound",
    "Other": "Other",
    "": "Unknown",
}


def _normalize_source(how_heard: str) -> str:
    """Map raw how_heard text to a short display label."""
    return SOURCE_LABELS.get(how_heard or "", how_heard or "Unknown")


# ---------------------------------------------------------------------------
# Data loaders (cached per call)
# ---------------------------------------------------------------------------

def _load_all_data() -> tuple[list, list, list, list]:
    """Fetch all leads, clients, contracts, and invoices.

    Returns:
        (leads, clients, contracts, invoices) — each a list of dicts.
    """
    leads = []
    clients = []
    contracts = []
    invoices = []

    try:
        from services.leads_service import get_all_leads
        leads = get_all_leads() or []
    except Exception as e:
        logger.error("Attribution: failed to load leads: %s", e)

    try:
        from services.supabase_client import query_table
        clients = query_table("clients") or []
        contracts = query_table("contracts") or []
        invoices = query_table("invoices") or []
    except Exception as e:
        logger.error("Attribution: failed to load from Supabase: %s", e)

    return leads, clients, contracts, invoices


def _build_lookup_maps(leads, clients, contracts, invoices):
    """Build in-memory lookup maps for joining.

    Returns:
        lead_by_id: {lead_id: lead_dict}
        client_by_id: {client_id: client_dict}
        contracts_by_client: {client_id: [contract_dicts]}
        invoices_by_client: {client_id: [invoice_dicts]}
        source_for_client: {client_id: normalized_source_label}
    """
    # Lead lookup by ID
    lead_by_id = {str(l.get("id", "")): l for l in leads}

    # Client lookup by ID
    client_by_id = {str(c.get("id", "")): c for c in clients}

    # Contracts grouped by client
    contracts_by_client = defaultdict(list)
    for c in contracts:
        cid = str(c.get("client_id", ""))
        if cid:
            contracts_by_client[cid].append(c)

    # Invoices grouped by client
    invoices_by_client = defaultdict(list)
    for inv in invoices:
        cid = str(inv.get("client_id", ""))
        if cid:
            invoices_by_client[cid].append(inv)

    # Resolve source for each client via lead_id -> lead.how_heard
    source_for_client = {}
    for client in clients:
        cid = str(client.get("id", ""))
        lead_id = str(client.get("lead_id", "") or "")
        if lead_id and lead_id in lead_by_id:
            how_heard = lead_by_id[lead_id].get("how_heard", "")
            source_for_client[cid] = _normalize_source(how_heard)
        else:
            source_for_client[cid] = "Unknown"

    return lead_by_id, client_by_id, contracts_by_client, invoices_by_client, source_for_client


# ---------------------------------------------------------------------------
# Core analytics functions
# ---------------------------------------------------------------------------

def get_attribution_data() -> dict:
    """Build the complete attribution dataset.

    Returns dict with:
        funnel: {source: {leads, clients, contracts, revenue, conversion_rate}}
        revenue_by_source: {source: total_revenue}
        time_to_close: {source: avg_days}
        rep_performance: [{rep, leads, clients, contracts, revenue, avg_deal_size}]
        top_source: str (highest revenue source)
        totals: {leads, clients, contracts, revenue}
    """
    leads, clients, contracts, invoices = _load_all_data()

    if not leads and not clients:
        return {
            "funnel": {},
            "revenue_by_source": {},
            "time_to_close": {},
            "rep_performance": [],
            "top_source": "N/A",
            "totals": {"leads": 0, "clients": 0, "contracts": 0, "revenue": 0},
        }

    (lead_by_id, client_by_id, contracts_by_client,
     invoices_by_client, source_for_client) = _build_lookup_maps(
        leads, clients, contracts, invoices
    )

    funnel = get_conversion_funnel(
        leads, clients, contracts_by_client, invoices_by_client,
        source_for_client, lead_by_id,
    )
    revenue = get_revenue_by_source(clients, invoices_by_client, source_for_client)
    ttc = get_time_to_close(
        clients, contracts_by_client, source_for_client, lead_by_id,
    )
    reps = get_rep_performance(
        leads, clients, contracts_by_client, invoices_by_client,
        source_for_client, lead_by_id,
    )

    # Determine top source
    top_source = "N/A"
    if revenue:
        top_source = max(revenue, key=revenue.get)

    # Totals
    total_revenue = sum(revenue.values())
    total_contracts = sum(
        len(cl) for cl in contracts_by_client.values()
        if any(c.get("status") in ("active", "signed") for c in cl)
    )

    return {
        "funnel": funnel,
        "revenue_by_source": revenue,
        "time_to_close": ttc,
        "rep_performance": reps,
        "top_source": top_source,
        "totals": {
            "leads": len(leads),
            "clients": len(clients),
            "contracts": total_contracts,
            "revenue": total_revenue,
        },
    }


def get_conversion_funnel(
    leads, clients, contracts_by_client, invoices_by_client,
    source_for_client, lead_by_id,
) -> dict[str, dict]:
    """Full conversion funnel by lead source.

    Returns: {
        source_label: {
            leads: int,
            clients: int,
            contracts: int,
            revenue: float,
            conversion_rate: float,  # leads -> clients %
        }
    }
    """
    # Count leads by source
    leads_by_source = defaultdict(int)
    for lead in leads:
        source = _normalize_source(lead.get("how_heard", ""))
        leads_by_source[source] += 1

    # Count clients by source
    clients_by_source = defaultdict(int)
    for client in clients:
        cid = str(client.get("id", ""))
        source = source_for_client.get(cid, "Unknown")
        clients_by_source[source] += 1

    # Count active/signed contracts and paid revenue by source
    contracts_by_source = defaultdict(int)
    revenue_by_source = defaultdict(float)

    for client in clients:
        cid = str(client.get("id", ""))
        source = source_for_client.get(cid, "Unknown")

        # Count contracts
        for contract in contracts_by_client.get(cid, []):
            if contract.get("status") in ("active", "signed"):
                contracts_by_source[source] += 1

        # Sum paid invoice revenue
        for inv in invoices_by_client.get(cid, []):
            if inv.get("status") == "paid":
                revenue_by_source[source] += float(inv.get("amount", 0))

    # Build funnel dict
    all_sources = set(leads_by_source) | set(clients_by_source)
    funnel = {}
    for source in sorted(all_sources):
        lead_count = leads_by_source.get(source, 0)
        client_count = clients_by_source.get(source, 0)
        contract_count = contracts_by_source.get(source, 0)
        rev = revenue_by_source.get(source, 0)
        conversion = (client_count / lead_count * 100) if lead_count > 0 else 0

        funnel[source] = {
            "leads": lead_count,
            "clients": client_count,
            "contracts": contract_count,
            "revenue": rev,
            "conversion_rate": round(conversion, 1),
        }

    return funnel


def get_revenue_by_source(
    clients, invoices_by_client, source_for_client,
) -> dict[str, float]:
    """Revenue by lead source (paid invoices only).

    Returns: {source_label: total_paid_revenue}
    """
    revenue = defaultdict(float)
    for client in clients:
        cid = str(client.get("id", ""))
        source = source_for_client.get(cid, "Unknown")
        for inv in invoices_by_client.get(cid, []):
            if inv.get("status") == "paid":
                revenue[source] += float(inv.get("amount", 0))

    return dict(sorted(revenue.items(), key=lambda x: x[1], reverse=True))


def get_time_to_close(
    clients, contracts_by_client, source_for_client, lead_by_id,
) -> dict[str, float]:
    """Average days from lead submitted_at to first contract signed_at, by source.

    Returns: {source_label: avg_days_to_close}
    """
    days_by_source = defaultdict(list)

    for client in clients:
        cid = str(client.get("id", ""))
        lead_id = str(client.get("lead_id", "") or "")
        source = source_for_client.get(cid, "Unknown")

        # Get lead submitted date
        lead = lead_by_id.get(lead_id)
        if not lead:
            continue
        submitted_str = lead.get("submitted_at", "")
        if not submitted_str:
            continue

        # Find earliest signed_at among this client's contracts
        earliest_signed = None
        for contract in contracts_by_client.get(cid, []):
            signed_at = contract.get("signed_at", "")
            if signed_at:
                try:
                    signed_date = datetime.fromisoformat(
                        signed_at.replace("Z", "+00:00")
                    ).date()
                    if earliest_signed is None or signed_date < earliest_signed:
                        earliest_signed = signed_date
                except (ValueError, TypeError):
                    pass

        if earliest_signed is None:
            continue

        # Calculate days
        try:
            submitted_date = datetime.fromisoformat(
                submitted_str.replace("Z", "+00:00")
            ).date()
            days = (earliest_signed - submitted_date).days
            if days >= 0:
                days_by_source[source].append(days)
        except (ValueError, TypeError):
            pass

    # Average
    result = {}
    for source, days_list in days_by_source.items():
        result[source] = round(sum(days_list) / len(days_list), 1)

    return dict(sorted(result.items(), key=lambda x: x[1]))


def get_rep_performance(
    leads, clients, contracts_by_client, invoices_by_client,
    source_for_client, lead_by_id,
) -> list[dict]:
    """Sales rep performance: leads assigned, clients converted, revenue closed.

    Uses clients.assigned_rep to attribute.

    Returns: [{rep, leads, clients, contracts, revenue, avg_deal_size}]
    """
    rep_data = defaultdict(lambda: {
        "leads": 0, "clients": 0, "contracts": 0, "revenue": 0.0,
    })

    # Count clients and revenue per rep
    for client in clients:
        rep = client.get("assigned_rep", "") or "Unassigned"
        cid = str(client.get("id", ""))

        rep_data[rep]["clients"] += 1

        # Contracts
        for contract in contracts_by_client.get(cid, []):
            if contract.get("status") in ("active", "signed"):
                rep_data[rep]["contracts"] += 1

        # Revenue (paid invoices)
        for inv in invoices_by_client.get(cid, []):
            if inv.get("status") == "paid":
                rep_data[rep]["revenue"] += float(inv.get("amount", 0))

    # Count leads per rep (from the client's lead record status, attributed via assigned_rep)
    # Since leads don't have assigned_rep, count leads that converted to clients under each rep
    for client in clients:
        rep = client.get("assigned_rep", "") or "Unassigned"
        lead_id = str(client.get("lead_id", "") or "")
        if lead_id and lead_id in lead_by_id:
            rep_data[rep]["leads"] += 1

    # Build result list
    result = []
    for rep, data in sorted(rep_data.items(), key=lambda x: x[1]["revenue"], reverse=True):
        if rep == "Unassigned" and data["clients"] == 0:
            continue
        avg_deal = (
            data["revenue"] / data["contracts"]
            if data["contracts"] > 0
            else 0
        )
        result.append({
            "rep": rep,
            "leads": data["leads"],
            "clients": data["clients"],
            "contracts": data["contracts"],
            "revenue": data["revenue"],
            "avg_deal_size": round(avg_deal, 2),
        })

    return result


def get_client_lifetime_value(
    clients=None, invoices_by_client=None, source_for_client=None,
) -> dict[str, float]:
    """Average client lifetime value by lead source.

    LTV = total paid invoices per client, averaged by source.

    Returns: {source_label: avg_ltv}
    """
    if clients is None or invoices_by_client is None or source_for_client is None:
        leads, clients, contracts, invoices = _load_all_data()
        _, _, _, invoices_by_client, source_for_client = _build_lookup_maps(
            leads, clients, contracts, invoices
        )

    ltv_by_source = defaultdict(list)

    for client in clients:
        cid = str(client.get("id", ""))
        source = source_for_client.get(cid, "Unknown")
        total_paid = sum(
            float(inv.get("amount", 0))
            for inv in invoices_by_client.get(cid, [])
            if inv.get("status") == "paid"
        )
        ltv_by_source[source].append(total_paid)

    result = {}
    for source, values in ltv_by_source.items():
        if values:
            result[source] = round(sum(values) / len(values), 2)

    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
