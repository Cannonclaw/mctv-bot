# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Auto-generated case study one-pagers for clients past 90 days.

Pulls a client's accumulated traction (NTV360 plays + modeled impressions),
asks Claude to write a sales-ready narrative, and outputs a branded DOCX.
"""

import logging
import os
from datetime import date, datetime
from pathlib import Path

from services.config_service import load_config
from services.portal_service import get_client
from services.supabase_client import query_table

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "case_studies"
NARRATIVE_PROMPT = """You write 1-page case studies for MCTV Elite Advertising,
an indoor digital billboard network in North Mississippi.

Voice: confident, specific, no marketing fluff. Write like a fellow business
owner. No buzzwords. Short paragraphs.

Below are the client's facts. Write a 4-paragraph narrative:
1. Who they are and why they came to MCTV (1-2 sentences).
2. The campaign — markets, screen count, monthly investment, duration.
3. The results — total impressions, plays, audience reached, biggest venues.
4. The takeaway — what this means for similar businesses considering MCTV.

Total length: 220-280 words. No headers, no bullet points, just prose.
Don't fabricate quotes or numbers — use only what's provided.

CLIENT FACTS
============
Business: {business_name}
Industry: {industry}
City: {city}
Contract started: {start_date}
Months active: {months_active}
Tier: {tier_name} ({screen_count} screens)
Monthly rate: ${monthly_rate:,.0f}
Total invested to date: ${total_invested:,.0f}

PERFORMANCE
============
Total plays delivered: {total_plays:,}
Total impressions: {total_impressions:,}
Average plays per month: {avg_plays_per_month:,.0f}
Markets covered: {markets}
Top venues: {top_venues}

WRITE THE NARRATIVE
"""


def is_eligible(contract: dict, min_days: int = 90) -> tuple[bool, int]:
    """Return (eligible, days_since_start). Eligible if >= min_days active."""
    sd = contract.get("start_date")
    if not sd:
        return False, 0
    try:
        start = datetime.fromisoformat(sd).date()
    except (ValueError, TypeError):
        return False, 0
    days = (date.today() - start).days
    return days >= min_days, days


def gather_traction(contract: dict) -> dict:
    """Aggregate NTV360 snapshots that fall within the contract's lifetime."""
    sd = contract.get("start_date", "")[:7]  # YYYY-MM
    if not sd:
        return {"total_plays": 0, "total_impressions": 0, "snapshots": [],
                "top_venues": [], "avg_plays_per_month": 0}

    snapshots = query_table(
        "ntv360_snapshots",
        order="-snapshot_month",
        limit=24,
    ) or []
    relevant = [s for s in snapshots if s.get("snapshot_month", "") >= sd]

    total_plays = sum(int(s.get("total_plays", 0) or 0) for s in relevant)
    total_impressions = total_plays * 60  # rough conversion; matches dashboard

    # Top venues across all relevant snapshots
    import json as _json
    venue_totals: dict[str, int] = {}
    for s in relevant:
        vd = s.get("venue_data")
        if isinstance(vd, str):
            try:
                vd = _json.loads(vd)
            except (_json.JSONDecodeError, TypeError):
                vd = []
        for v in vd or []:
            host = v.get("host_name", "")
            if not host:
                continue
            venue_totals[host] = venue_totals.get(host, 0) + int(v.get("total_plays", 0) or 0)

    top_venues = sorted(venue_totals.items(), key=lambda kv: kv[1], reverse=True)[:5]

    months = max(len(relevant), 1)
    return {
        "total_plays": total_plays,
        "total_impressions": total_impressions,
        "snapshots": relevant,
        "top_venues": top_venues,
        "avg_plays_per_month": total_plays / months if months else 0,
    }


def generate_case_study(contract_id: str) -> Path | None:
    """Generate a 1-page case-study DOCX for a contract.

    Returns the path to the generated file, or None on failure.
    """
    from services.contract_service import get_contract
    from services.claude_service import ClaudeService
    from services.docx_service import DocxService

    contract = get_contract(contract_id)
    if not contract:
        logger.warning("Contract %s not found", contract_id)
        return None

    eligible, days = is_eligible(contract)
    if not eligible:
        logger.info("Contract %s only %d days old (need 90+)", contract_id, days)
        return None

    client = get_client(contract.get("client_id", "")) or {}
    business_name = client.get("business_name", "Client")
    industry = client.get("industry", "")
    city = client.get("city", "")

    months_active = max(days // 30, 1)
    monthly_rate = float(contract.get("monthly_rate", 0) or 0)
    total_invested = monthly_rate * months_active

    traction = gather_traction(contract)
    top_venues_str = ", ".join(f"{name} ({plays:,} plays)"
                                for name, plays in traction["top_venues"])
    markets = contract.get("markets") or []
    markets_str = ", ".join(markets) if markets else "Network-wide"

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    config = load_config()
    model = config.get("proposal_settings", {}).get("model",
                                                     "claude-sonnet-4-5-20250929")

    if api_key and api_key != "your-api-key-here":
        claude = ClaudeService(api_key=api_key, model=model)
        narrative = claude.generate_section(
            NARRATIVE_PROMPT.format(
                business_name=business_name,
                industry=industry or "—",
                city=city or "—",
                start_date=contract.get("start_date", ""),
                months_active=months_active,
                tier_name=contract.get("tier_name", "Custom"),
                screen_count=int(contract.get("screen_count", 0) or 0),
                monthly_rate=monthly_rate,
                total_invested=total_invested,
                total_plays=traction["total_plays"],
                total_impressions=traction["total_impressions"],
                avg_plays_per_month=traction["avg_plays_per_month"],
                markets=markets_str,
                top_venues=top_venues_str or "Network-wide rotation",
            ),
            max_tokens=900,
        )
    else:
        narrative = (f"{business_name} began advertising on the MCTV network "
                     f"{months_active} months ago. Over that span, MCTV delivered "
                     f"{traction['total_plays']:,} plays and an estimated "
                     f"{traction['total_impressions']:,} impressions across "
                     f"{markets_str}. Notable venues: {top_venues_str or 'multiple network locations'}.")

    # Build the DOCX
    docx_svc = DocxService(config)
    doc = docx_svc.create_document()
    docx_svc.add_cover_page(
        doc,
        title=f"Case Study: {business_name}",
        subtitle=f"{months_active}-month performance with MCTV Elite Advertising",
        rep=docx_svc.config.get("team", [{}])[0].get("name", ""),
    ) if hasattr(docx_svc, "add_cover_page") else None

    docx_svc.add_section_header(doc, f"Case Study — {business_name}")
    docx_svc.add_metrics_banner(doc, [
        ("Total Plays", f"{traction['total_plays']:,}"),
        ("Impressions", f"{traction['total_impressions']:,}"),
        ("Months Active", f"{months_active}"),
        ("Total Invested", f"${total_invested:,.0f}"),
    ])
    docx_svc.add_body_text(doc, narrative.strip())

    if traction["top_venues"]:
        docx_svc.add_section_header(doc, "Top-Performing Venues")
        for name, plays in traction["top_venues"]:
            docx_svc.add_body_text(doc, f"• {name} — {plays:,} plays")

    docx_svc.add_footer(doc) if hasattr(docx_svc, "add_footer") else None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in business_name if c.isalnum() or c in "_-").strip("_") or "Client"
    filename = f"{safe}_CaseStudy_{date.today().strftime('%Y-%m-%d')}.docx"
    out_path = OUTPUT_DIR / filename
    doc.save(out_path)
    logger.info("Case study generated: %s", out_path)
    return out_path
