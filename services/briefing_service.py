# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Daily briefing service for MCTV Elite Advertising.

Aggregates data from all operational services into a structured briefing,
then formats for email (HTML) and SMS delivery. Designed to run once daily
via scheduled task or manual trigger from the Settings page.

Sections:
- Executive summary (KPI snapshot)
- Contract pipeline status
- Revenue / AR aging
- Lead pipeline and follow-ups due
- Prioritized action alerts
- Recent activity log
- SMS activity summary
"""

import logging
import os
import smtplib
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


# ── Data Aggregation ────────────────────────────────────────────────────────

def generate_briefing() -> dict:
    """Aggregate data from all services into a structured daily briefing.

    Each service call is wrapped in try/except so a single service failure
    does not prevent the rest of the briefing from generating. Missing
    sections default to safe empty values.

    Returns:
        Structured briefing dict with executive_summary, contracts, revenue,
        leads, alerts, recent_activity, and sms_summary.
    """
    briefing = {
        "generated_at": datetime.now().isoformat(),
        "executive_summary": {},
        "contracts": {},
        "revenue": {},
        "leads": {},
        "alerts": [],
        "recent_activity": [],
        "sms_summary": {},
    }

    # ── Admin summary (clients + high-level stats) ──────────────────────
    admin_summary = {}
    try:
        from services.portal_service import get_admin_summary
        admin_summary = get_admin_summary() or {}
    except Exception as e:
        logger.error("Briefing: failed to load admin summary: %s", e)

    # ── Contract data ───────────────────────────────────────────────────
    contract_summary = {}
    all_contracts = []
    try:
        from services.contract_service import get_contract_summary, get_all_contracts
        contract_summary = get_contract_summary() or {}
        all_contracts = get_all_contracts() or []
    except Exception as e:
        logger.error("Briefing: failed to load contracts: %s", e)

    # ── Invoice / revenue data ──────────────────────────────────────────
    invoice_summary = {}
    ar_aging = {}
    overdue_invoices = []
    try:
        from services.invoice_service import (
            get_invoice_summary, get_ar_aging, get_overdue_invoices,
        )
        invoice_summary = get_invoice_summary() or {}
        ar_aging = get_ar_aging() or {}
        overdue_invoices = get_overdue_invoices() or []
    except Exception as e:
        logger.error("Briefing: failed to load invoices: %s", e)

    # ── Leads data ──────────────────────────────────────────────────────
    all_leads = []
    try:
        from services.leads_service import (
            get_all_leads, calculate_lead_score, get_score_label,
        )
        all_leads = get_all_leads() or []
    except Exception as e:
        logger.error("Briefing: failed to load leads: %s", e)

    # ── SMS activity ────────────────────────────────────────────────────
    sms_history = []
    try:
        from services.sms_service import get_message_history
        sms_history = get_message_history(limit=50) or []
    except Exception as e:
        logger.error("Briefing: failed to load SMS history: %s", e)

    # ── Recent activity log ─────────────────────────────────────────────
    recent_activity = []
    try:
        from services.supabase_client import query_table
        recent_activity = query_table(
            "activity_log", order="-created_at", limit=10,
        ) or []
    except Exception as e:
        logger.error("Briefing: failed to load activity log: %s", e)

    # ====================================================================
    # Build executive summary
    # ====================================================================
    today = date.today()

    # Score all leads for pipeline breakdown
    hot_leads = []
    warm_leads = []
    cold_leads = []
    for lead in all_leads:
        try:
            score = calculate_lead_score(lead)
            label, _color = get_score_label(score)
            lead_entry = {
                "business_name": lead.get("business_name", "Unknown"),
                "score": score,
                "status": lead.get("status", ""),
                "city": lead.get("city", ""),
            }
            if label == "Hot":
                hot_leads.append(lead_entry)
            elif label == "Warm":
                warm_leads.append(lead_entry)
            else:
                cold_leads.append(lead_entry)
        except Exception:
            cold_leads.append({
                "business_name": lead.get("business_name", "Unknown"),
                "score": 0,
                "status": lead.get("status", ""),
                "city": lead.get("city", ""),
            })

    # Count leads created today
    today_str = today.isoformat()
    new_leads_today = 0
    for lead in all_leads:
        created = lead.get("created_at") or lead.get("submitted_at") or ""
        if created.startswith(today_str):
            new_leads_today += 1

    # MRR: prefer real recurring revenue from QuickBooks (the system of record
    # for billing); fall back to the contract sum only if QB is unavailable.
    try:
        from services.quickbooks_service import get_recurring_revenue
        qb_mrr = get_recurring_revenue()
    except Exception:
        qb_mrr = 0.0

    briefing["executive_summary"] = {
        "active_clients": admin_summary.get("active_clients", 0),
        "monthly_recurring_revenue": float(
            qb_mrr
            or contract_summary.get("active_mrr", 0)
            or admin_summary.get("monthly_recurring_revenue", 0)
        ),
        "contracts_awaiting_signature": contract_summary.get(
            "awaiting_signature", 0
        ),
        "overdue_invoices_count": invoice_summary.get("overdue", 0),
        "overdue_amount": float(invoice_summary.get("total_overdue", 0)),
        "total_outstanding": float(
            invoice_summary.get("total_outstanding", 0)
        ),
        "hot_leads": len(hot_leads),
        "warm_leads": len(warm_leads),
        "new_leads_today": new_leads_today,
    }

    # ====================================================================
    # Build contracts section
    # ====================================================================
    # Find contracts that need attention: sent but not signed for 3+ days
    needs_attention = []
    for contract in all_contracts:
        if contract.get("status") in ("sent", "viewed"):
            sent_at = contract.get("sent_at") or contract.get("created_at") or ""
            if sent_at:
                try:
                    sent_date = datetime.fromisoformat(
                        sent_at.replace("Z", "+00:00")
                    ).date()
                    days_waiting = (today - sent_date).days
                    if days_waiting >= 3:
                        needs_attention.append({
                            "title": contract.get("title", "Untitled"),
                            "client_id": contract.get("client_id", ""),
                            "status": contract.get("status", ""),
                            "sent_at": sent_at,
                            "days_waiting": days_waiting,
                        })
                except (ValueError, TypeError):
                    pass

    # Sort by longest waiting first
    needs_attention.sort(key=lambda c: c.get("days_waiting", 0), reverse=True)

    briefing["contracts"] = {
        "total": contract_summary.get("total", 0),
        "draft": contract_summary.get("draft", 0),
        "sent": contract_summary.get("sent", 0),
        "awaiting_signature": contract_summary.get("awaiting_signature", 0),
        "signed": contract_summary.get("signed", 0),
        "active": contract_summary.get("active", 0),
        "active_mrr": float(contract_summary.get("active_mrr", 0)),
        "needs_attention": needs_attention,
    }

    # ====================================================================
    # Build revenue section
    # ====================================================================
    overdue_list = []
    for inv in overdue_invoices:
        due_str = inv.get("due_date", "")
        days_overdue = 0
        if due_str:
            try:
                due_date = date.fromisoformat(due_str)
                days_overdue = (today - due_date).days
            except (ValueError, TypeError):
                pass

        # Try to get business name from joined client data or fall back
        biz_name = (
            inv.get("business_name")
            or inv.get("client_name")
            or inv.get("client_id", "Unknown")
        )
        balance = float(inv.get("amount", 0)) - float(inv.get("amount_paid", 0))

        overdue_list.append({
            "business_name": biz_name,
            "invoice_number": inv.get("invoice_number", ""),
            "amount": balance,
            "days_overdue": days_overdue,
        })

    # Sort by most overdue first
    overdue_list.sort(key=lambda i: i.get("days_overdue", 0), reverse=True)

    briefing["revenue"] = {
        "total_billed": float(invoice_summary.get("total_billed", 0)),
        "total_collected": float(invoice_summary.get("total_collected", 0)),
        "total_outstanding": float(
            invoice_summary.get("total_outstanding", 0)
        ),
        "total_overdue": float(invoice_summary.get("total_overdue", 0)),
        "ar_aging": ar_aging,
        "overdue_list": overdue_list,
    }

    # ====================================================================
    # Build leads section
    # ====================================================================
    follow_ups_due = []
    for lead in all_leads:
        fu_date_str = lead.get("follow_up_date") or ""
        if fu_date_str:
            try:
                fu_date = date.fromisoformat(fu_date_str)
                if fu_date <= today:
                    follow_ups_due.append({
                        "business_name": lead.get("business_name", "Unknown"),
                        "contact_name": lead.get("contact_name", ""),
                        "follow_up_date": fu_date_str,
                        "follow_up_notes": lead.get("follow_up_notes", ""),
                        "status": lead.get("status", ""),
                    })
            except (ValueError, TypeError):
                pass

    briefing["leads"] = {
        "total": len(all_leads),
        "hot": hot_leads,
        "warm_count": len(warm_leads),
        "cold_count": len(cold_leads),
        "follow_ups_due": follow_ups_due,
    }

    # ====================================================================
    # Build alerts (prioritized plain-English action items)
    # ====================================================================
    alerts = []

    # Contracts awaiting signature
    awaiting = briefing["contracts"]["awaiting_signature"]
    if awaiting > 0:
        oldest_days = 0
        if needs_attention:
            oldest_days = needs_attention[0].get("days_waiting", 0)
        if oldest_days > 0:
            alerts.append(
                f"{awaiting} contract{'s' if awaiting != 1 else ''} "
                f"awaiting signature (oldest sent {oldest_days} days ago)"
            )
        else:
            alerts.append(
                f"{awaiting} contract{'s' if awaiting != 1 else ''} "
                f"awaiting signature"
            )

    # Overdue invoices
    overdue_count = briefing["executive_summary"]["overdue_invoices_count"]
    overdue_amt = briefing["executive_summary"]["overdue_amount"]
    if overdue_count > 0:
        alerts.append(
            f"{overdue_count} invoice{'s' if overdue_count != 1 else ''} "
            f"overdue totaling ${overdue_amt:,.2f}"
        )

    # Severely overdue invoices (45+ days) get individual alerts
    for inv in overdue_list:
        if inv.get("days_overdue", 0) >= 45:
            alerts.append(
                f"${inv['amount']:,.2f} invoice for {inv['business_name']} "
                f"is {inv['days_overdue']}+ days past due"
            )

    # Hot leads
    hot_count = len(hot_leads)
    if hot_count > 0:
        alerts.append(
            f"{hot_count} Hot lead{'s' if hot_count != 1 else ''} "
            f"ready to close"
        )

    # Follow-ups due
    fu_count = len(follow_ups_due)
    if fu_count > 0:
        alerts.append(
            f"{fu_count} follow-up call{'s' if fu_count != 1 else ''} overdue"
        )

    # New leads today
    if new_leads_today > 0:
        alerts.append(
            f"{new_leads_today} new lead{'s' if new_leads_today != 1 else ''} "
            f"submitted today"
        )

    # Draft contracts sitting around
    draft_count = briefing["contracts"]["draft"]
    if draft_count > 0:
        alerts.append(
            f"{draft_count} draft contract{'s' if draft_count != 1 else ''} "
            f"not yet sent"
        )

    briefing["alerts"] = alerts

    # ====================================================================
    # Recent activity + SMS summary
    # ====================================================================
    briefing["recent_activity"] = recent_activity

    # Count SMS messages sent in the last 24 hours
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    recent_sms_count = 0
    for msg in sms_history:
        sent_at = msg.get("sent_at", "")
        if sent_at and sent_at >= cutoff:
            recent_sms_count += 1

    briefing["sms_summary"] = {
        "recent_count": recent_sms_count,
    }

    # ── Lead source attribution ──────────────────────────────────────
    attribution = {}
    try:
        from services.attribution_service import get_attribution_data
        attribution = get_attribution_data() or {}
    except Exception as e:
        logger.error("Briefing: failed to load attribution: %s", e)

    briefing["attribution"] = attribution

    return briefing


# ── Email Formatting ────────────────────────────────────────────────────────

def format_briefing_email(briefing: dict, config: dict) -> tuple[str, str]:
    """Format the briefing as a branded HTML email.

    Args:
        briefing: Structured briefing dict from generate_briefing().
        config: App config dict (used for company info, team contacts).

    Returns:
        Tuple of (subject_line, html_body).
    """
    es = briefing.get("executive_summary", {})
    alerts = briefing.get("alerts", [])
    contracts = briefing.get("contracts", {})
    revenue = briefing.get("revenue", {})
    leads = briefing.get("leads", {})
    activity = briefing.get("recent_activity", [])

    mrr = es.get("monthly_recurring_revenue", 0)
    alert_count = len(alerts)
    date_str = datetime.now().strftime("%a %b %d")

    subject = (
        f"MCTV Daily Briefing \u2014 ${mrr:,.0f} MRR | "
        f"{alert_count} Alert{'s' if alert_count != 1 else ''} | {date_str}"
    )

    # ── Brand colors (inline CSS for email clients) ─────────────────────
    navy = "#1B1F3B"
    gold = "#C5A55A"
    light_bg = "#F7F8FA"
    white = "#FFFFFF"
    text_dark = "#2D2D2D"
    text_muted = "#6B7280"
    red = "#DC2626"
    green = "#16A34A"

    # ── Build HTML ──────────────────────────────────────────────────────
    html_parts = []

    # Wrapper
    html_parts.append(f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:{light_bg};font-family:Arial,Helvetica,sans-serif;color:{text_dark};font-size:14px;line-height:1.5;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{light_bg};">
<tr><td align="center" style="padding:20px 0;">
<table width="600" cellpadding="0" cellspacing="0" style="background:{white};border-radius:8px;overflow:hidden;">
""")

    # Header bar
    html_parts.append(f"""
<tr><td style="background:{navy};padding:24px 30px;">
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td style="color:{gold};font-size:22px;font-weight:bold;font-family:Arial,Helvetica,sans-serif;">
      MCTV Daily Briefing
    </td>
    <td align="right" style="color:{white};font-size:13px;font-family:Arial,Helvetica,sans-serif;">
      {datetime.now().strftime("%B %d, %Y")}
    </td>
  </tr>
  </table>
</td></tr>
""")

    # ── Executive Summary ───────────────────────────────────────────────
    html_parts.append(f"""
<tr><td style="padding:24px 30px 12px;">
  <h2 style="margin:0 0 16px;font-size:18px;color:{navy};">Executive Summary</h2>
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td width="33%" align="center" style="padding:12px 8px;background:{navy};border-radius:6px 0 0 6px;">
      <div style="color:{gold};font-size:24px;font-weight:bold;">${mrr:,.0f}</div>
      <div style="color:{white};font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">Monthly MRR</div>
    </td>
    <td width="34%" align="center" style="padding:12px 8px;background:{navy};">
      <div style="color:{gold};font-size:24px;font-weight:bold;">{es.get('active_clients', 0)}</div>
      <div style="color:{white};font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">Active Clients</div>
    </td>
    <td width="33%" align="center" style="padding:12px 8px;background:{navy};border-radius:0 6px 6px 0;">
      <div style="color:{gold};font-size:24px;font-weight:bold;">{es.get('hot_leads', 0)}</div>
      <div style="color:{white};font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">Hot Leads</div>
    </td>
  </tr>
  </table>
</td></tr>
""")

    # Secondary KPI row
    outstanding = es.get("total_outstanding", 0)
    awaiting_sig = es.get("contracts_awaiting_signature", 0)
    overdue_ct = es.get("overdue_invoices_count", 0)
    overdue_color = red if overdue_ct > 0 else green

    html_parts.append(f"""
<tr><td style="padding:8px 30px 20px;">
  <table width="100%" cellpadding="8" cellspacing="0" style="background:{light_bg};border-radius:6px;">
  <tr>
    <td width="33%" style="font-size:13px;">
      <strong style="color:{navy};">{awaiting_sig}</strong> contracts pending sig
    </td>
    <td width="34%" style="font-size:13px;">
      <strong style="color:{overdue_color};">{overdue_ct}</strong> invoices overdue
    </td>
    <td width="33%" style="font-size:13px;">
      <strong style="color:{navy};">${outstanding:,.0f}</strong> outstanding
    </td>
  </tr>
  </table>
</td></tr>
""")

    # ── Alerts ──────────────────────────────────────────────────────────
    if alerts:
        alert_rows = ""
        for alert_text in alerts:
            alert_rows += (
                f'<tr><td style="padding:6px 12px;font-size:13px;'
                f'border-bottom:1px solid #F3F4F6;">'
                f'\u26a0\ufe0f {alert_text}</td></tr>\n'
            )

        html_parts.append(f"""
<tr><td style="padding:0 30px 20px;">
  <h2 style="margin:0 0 10px;font-size:16px;color:{red};">Action Items ({len(alerts)})</h2>
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#FEF2F2;border-radius:6px;border-left:4px solid {red};">
  {alert_rows}
  </table>
</td></tr>
""")

    # ── Revenue Section ─────────────────────────────────────────────────
    billed = revenue.get("total_billed", 0)
    collected = revenue.get("total_collected", 0)
    rev_outstanding = revenue.get("total_outstanding", 0)
    rev_overdue = revenue.get("total_overdue", 0)

    html_parts.append(f"""
<tr><td style="padding:0 30px 20px;">
  <h2 style="margin:0 0 10px;font-size:16px;color:{navy};">Revenue</h2>
  <table width="100%" cellpadding="8" cellspacing="0"
         style="border:1px solid #E5E7EB;border-radius:6px;">
  <tr style="background:{light_bg};">
    <td style="font-size:13px;font-weight:bold;color:{text_muted};">Total Billed</td>
    <td style="font-size:13px;font-weight:bold;color:{text_muted};">Collected</td>
    <td style="font-size:13px;font-weight:bold;color:{text_muted};">Outstanding</td>
    <td style="font-size:13px;font-weight:bold;color:{text_muted};">Overdue</td>
  </tr>
  <tr>
    <td style="font-size:14px;font-weight:bold;">${billed:,.2f}</td>
    <td style="font-size:14px;font-weight:bold;color:{green};">${collected:,.2f}</td>
    <td style="font-size:14px;font-weight:bold;">${rev_outstanding:,.2f}</td>
    <td style="font-size:14px;font-weight:bold;color:{red};">${rev_overdue:,.2f}</td>
  </tr>
  </table>
""")

    # Overdue list
    overdue_list = revenue.get("overdue_list", [])
    if overdue_list:
        html_parts.append("""
  <table width="100%" cellpadding="6" cellspacing="0"
         style="margin-top:8px;border:1px solid #E5E7EB;border-radius:6px;font-size:12px;">
  <tr style="background:#FEF2F2;">
    <td style="font-weight:bold;">Client</td>
    <td style="font-weight:bold;">Invoice</td>
    <td style="font-weight:bold;">Balance</td>
    <td style="font-weight:bold;">Days Overdue</td>
  </tr>
""")
        for inv in overdue_list[:5]:
            days = inv.get("days_overdue", 0)
            day_style = f"color:{red};font-weight:bold;" if days >= 30 else ""
            html_parts.append(
                f'  <tr>'
                f'<td>{inv.get("business_name", "")}</td>'
                f'<td>{inv.get("invoice_number", "")}</td>'
                f'<td>${inv.get("amount", 0):,.2f}</td>'
                f'<td style="{day_style}">{days}</td>'
                f'</tr>\n'
            )
        html_parts.append("  </table>\n")

    html_parts.append("</td></tr>\n")

    # ── Contracts Section ───────────────────────────────────────────────
    html_parts.append(f"""
<tr><td style="padding:0 30px 20px;">
  <h2 style="margin:0 0 10px;font-size:16px;color:{navy};">Contracts</h2>
  <table width="100%" cellpadding="8" cellspacing="0"
         style="border:1px solid #E5E7EB;border-radius:6px;font-size:13px;">
  <tr style="background:{light_bg};">
    <td><strong>Draft</strong></td>
    <td><strong>Sent</strong></td>
    <td><strong>Awaiting Sig</strong></td>
    <td><strong>Active</strong></td>
    <td><strong>MRR</strong></td>
  </tr>
  <tr>
    <td>{contracts.get('draft', 0)}</td>
    <td>{contracts.get('sent', 0)}</td>
    <td style="color:{gold};font-weight:bold;">{contracts.get('awaiting_signature', 0)}</td>
    <td style="color:{green};font-weight:bold;">{contracts.get('active', 0)}</td>
    <td style="font-weight:bold;">${contracts.get('active_mrr', 0):,.0f}</td>
  </tr>
  </table>
""")

    # Contracts needing attention
    attention = contracts.get("needs_attention", [])
    if attention:
        html_parts.append(f"""
  <div style="margin-top:8px;padding:8px 12px;background:#FFFBEB;border-radius:6px;
              border-left:4px solid {gold};font-size:12px;">
    <strong>Needs Follow-Up:</strong><br>
""")
        for c in attention[:5]:
            html_parts.append(
                f'    \u2022 {c.get("title", "")} '
                f'({c.get("days_waiting", 0)} days waiting)<br>\n'
            )
        html_parts.append("  </div>\n")

    html_parts.append("</td></tr>\n")

    # ── Leads Section ───────────────────────────────────────────────────
    hot = leads.get("hot", [])
    warm_ct = leads.get("warm_count", 0)
    cold_ct = leads.get("cold_count", 0)
    fups = leads.get("follow_ups_due", [])

    html_parts.append(f"""
<tr><td style="padding:0 30px 20px;">
  <h2 style="margin:0 0 10px;font-size:16px;color:{navy};">Leads Pipeline</h2>
  <table width="100%" cellpadding="8" cellspacing="0"
         style="border:1px solid #E5E7EB;border-radius:6px;font-size:13px;">
  <tr style="background:{light_bg};">
    <td><strong>Total</strong></td>
    <td><strong>Hot</strong></td>
    <td><strong>Warm</strong></td>
    <td><strong>Cold</strong></td>
    <td><strong>Follow-Ups Due</strong></td>
  </tr>
  <tr>
    <td>{leads.get('total', 0)}</td>
    <td style="color:{green};font-weight:bold;">{len(hot)}</td>
    <td style="color:{gold};font-weight:bold;">{warm_ct}</td>
    <td>{cold_ct}</td>
    <td style="color:{red if fups else text_dark};font-weight:{'bold' if fups else 'normal'};">{len(fups)}</td>
  </tr>
  </table>
""")

    # Hot leads detail
    if hot:
        html_parts.append(f"""
  <div style="margin-top:8px;padding:8px 12px;background:#F0FDF4;border-radius:6px;
              border-left:4px solid {green};font-size:12px;">
    <strong>Hot Leads:</strong><br>
""")
        for hl in hot[:5]:
            city = f" ({hl.get('city', '')})" if hl.get("city") else ""
            html_parts.append(
                f'    \u2022 {hl.get("business_name", "")}{city} '
                f'&mdash; score {hl.get("score", 0)}<br>\n'
            )
        html_parts.append("  </div>\n")

    # Follow-ups due
    if fups:
        html_parts.append(f"""
  <div style="margin-top:8px;padding:8px 12px;background:#FEF2F2;border-radius:6px;
              border-left:4px solid {red};font-size:12px;">
    <strong>Follow-Ups Overdue:</strong><br>
""")
        for fu in fups[:5]:
            html_parts.append(
                f'    \u2022 {fu.get("business_name", "")} '
                f'(due {fu.get("follow_up_date", "")})<br>\n'
            )
        html_parts.append("  </div>\n")

    html_parts.append("</td></tr>\n")

    # ── Lead Attribution ─────────────────────────────────────────────
    attribution = briefing.get("attribution", {})
    funnel = attribution.get("funnel", {})
    if funnel:
        html_parts.append(f"""
<tr><td style="padding:0 30px 20px;">
  <h2 style="margin:0 0 10px;font-size:16px;color:{navy};">Lead Attribution</h2>
  <table width="100%" cellpadding="6" cellspacing="0"
         style="border:1px solid #E5E7EB;border-radius:6px;font-size:12px;">
  <tr style="background:{light_bg};">
    <td style="font-weight:bold;">Source</td>
    <td style="font-weight:bold;">Leads</td>
    <td style="font-weight:bold;">Clients</td>
    <td style="font-weight:bold;">Revenue</td>
    <td style="font-weight:bold;">Conv %</td>
  </tr>
""")
        for source, data in sorted(
            funnel.items(), key=lambda x: x[1].get("revenue", 0), reverse=True,
        )[:5]:
            rev = data.get("revenue", 0)
            rev_style = f"color:{green};font-weight:bold;" if rev > 0 else ""
            html_parts.append(
                f'  <tr style="border-bottom:1px solid #F3F4F6;">'
                f'<td>{source}</td>'
                f'<td>{data.get("leads", 0)}</td>'
                f'<td>{data.get("clients", 0)}</td>'
                f'<td style="{rev_style}">${rev:,.0f}</td>'
                f'<td>{data.get("conversion_rate", 0):.0f}%</td>'
                f'</tr>\n'
            )
        html_parts.append("  </table>\n</td></tr>\n")

    # ── Recent Activity ─────────────────────────────────────────────────
    if activity:
        html_parts.append(f"""
<tr><td style="padding:0 30px 20px;">
  <h2 style="margin:0 0 10px;font-size:16px;color:{navy};">Recent Activity</h2>
  <table width="100%" cellpadding="6" cellspacing="0"
         style="border:1px solid #E5E7EB;border-radius:6px;font-size:12px;">
""")
        for entry in activity[:10]:
            action = entry.get("action", "")
            created = entry.get("created_at", "")
            # Format timestamp
            time_str = ""
            if created:
                try:
                    dt = datetime.fromisoformat(
                        created.replace("Z", "+00:00")
                    )
                    time_str = dt.strftime("%b %d %I:%M %p")
                except (ValueError, TypeError):
                    time_str = created[:16]

            html_parts.append(
                f'  <tr style="border-bottom:1px solid #F3F4F6;">'
                f'<td style="color:{text_muted};white-space:nowrap;">{time_str}</td>'
                f'<td>{action}</td></tr>\n'
            )
        html_parts.append("  </table>\n</td></tr>\n")

    # ── Footer ──────────────────────────────────────────────────────────
    html_parts.append(f"""
<tr><td style="background:{navy};padding:16px 30px;text-align:center;">
  <div style="color:{gold};font-size:13px;font-weight:bold;">
    MCTV Elite Advertising
  </div>
  <div style="color:{text_muted};font-size:11px;margin-top:4px;">
    Generated by MCTV Bot &middot; {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
  </div>
</td></tr>
""")

    # Close wrapper
    html_parts.append("""
</table>
</td></tr></table>
</body>
</html>
""")

    html_body = "".join(html_parts)
    return subject, html_body


# ── SMS Formatting ──────────────────────────────────────────────────────────

def format_briefing_sms(briefing: dict) -> str:
    """Format the briefing as a concise SMS message (max 320 characters).

    Args:
        briefing: Structured briefing dict from generate_briefing().

    Returns:
        SMS body string, 320 characters or less.
    """
    es = briefing.get("executive_summary", {})
    contracts = briefing.get("contracts", {})
    leads = briefing.get("leads", {})

    mrr = es.get("monthly_recurring_revenue", 0)
    awaiting = contracts.get("awaiting_signature", 0)
    overdue_ct = es.get("overdue_invoices_count", 0)
    overdue_amt = es.get("overdue_amount", 0)
    hot = es.get("hot_leads", 0)
    fups = len(leads.get("follow_ups_due", []))

    parts = [f"MCTV Daily: ${mrr:,.0f} MRR"]

    if awaiting:
        parts.append(
            f"{awaiting} contract{'s' if awaiting != 1 else ''} pending sig"
        )
    if overdue_ct:
        parts.append(
            f"{overdue_ct} invoice{'s' if overdue_ct != 1 else ''} "
            f"overdue (${overdue_amt:,.0f})"
        )
    if hot:
        parts.append(f"{hot} hot lead{'s' if hot != 1 else ''}")
    if fups:
        parts.append(
            f"{fups} follow-up{'s' if fups != 1 else ''} due"
        )

    message = " | ".join(parts)

    # Append inbox note if there is room
    suffix = ". Full briefing in your inbox."
    if len(message) + len(suffix) <= 320:
        message += suffix
    elif len(message) + len(". Check email.") <= 320:
        message += ". Check email."

    # Hard cap at 320 characters
    return message[:320]


# ── SMTP Email Sending ──────────────────────────────────────────────────────

def _send_html_email(
    to_emails: list[str],
    subject: str,
    html_body: str,
) -> bool:
    """Send an HTML email via SMTP.

    Uses the same SMTP env-var pattern as notification_service.py.

    Args:
        to_emails: List of recipient email addresses.
        subject: Email subject line.
        html_body: Full HTML email body.

    Returns:
        True on success, False on failure.
    """
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_host or not smtp_user:
        logger.warning("SMTP not configured -- skipping briefing email")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"MCTV Portal <{smtp_from}>"
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = subject

        # Plain-text fallback
        plain_fallback = (
            f"{subject}\n\n"
            "View the full HTML version in a modern email client.\n\n"
            "-- MCTV Elite Advertising"
        )
        msg.attach(MIMEText(plain_fallback, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, to_emails, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, to_emails, msg.as_string())

        logger.info("Briefing email sent to %s", ", ".join(to_emails))
        return True

    except Exception as e:
        logger.error("Briefing email failed: %s", e)
        return False


# ── Orchestrator ────────────────────────────────────────────────────────────

def send_daily_briefing(config: dict) -> dict:
    """Orchestrate the full daily briefing flow.

    Steps:
        1. Auto-mark overdue invoices.
        2. Generate the briefing data.
        3. Format and send the HTML email to all team members.
        4. Format and send the SMS summary to all team members.
        5. Log the briefing send in the activity_log.

    Args:
        config: App config dict. Expected keys:
            - config["team"]: list of dicts, each with "name", "email", "phone"

    Returns:
        Result dict with success flag, briefing data, and delivery status.
    """
    result = {
        "success": False,
        "briefing": {},
        "email_sent": False,
        "sms_sent": False,
        "errors": [],
    }

    # Step 1: Auto-mark overdue invoices
    try:
        from services.invoice_service import check_and_mark_overdue
        newly_overdue = check_and_mark_overdue()
        if newly_overdue:
            logger.info("Marked %d invoices as overdue", newly_overdue)
    except Exception as e:
        err = f"Failed to check overdue invoices: {e}"
        logger.error(err)
        result["errors"].append(err)

    # Step 2: Generate briefing
    try:
        briefing = generate_briefing()
        result["briefing"] = briefing
    except Exception as e:
        err = f"Failed to generate briefing: {e}"
        logger.error(err)
        result["errors"].append(err)
        return result

    # Gather team contact info
    team = config.get("team", [])
    team_emails = [
        m["email"] for m in team
        if m.get("email")
    ]
    team_phones = [
        m["phone"] for m in team
        if m.get("phone")
    ]

    # Step 3: Format and send email
    if team_emails:
        try:
            subject, html_body = format_briefing_email(briefing, config)
            result["email_sent"] = _send_html_email(
                team_emails, subject, html_body,
            )
        except Exception as e:
            err = f"Email formatting/send failed: {e}"
            logger.error(err)
            result["errors"].append(err)
    else:
        result["errors"].append("No team email addresses in config")

    # Step 4: Format and send SMS
    if team_phones:
        try:
            from services.sms_service import send_sms
            sms_body = format_briefing_sms(briefing)
            sms_successes = 0
            for phone in team_phones:
                sms_result = send_sms(
                    to=phone,
                    body=sms_body,
                    template="daily_briefing",
                    bypass_consent=True,
                )
                if sms_result.get("success"):
                    sms_successes += 1
                else:
                    sms_err = sms_result.get("error", "Unknown SMS error")
                    logger.warning("SMS to %s failed: %s", phone, sms_err)

            result["sms_sent"] = sms_successes > 0
            if sms_successes < len(team_phones):
                result["errors"].append(
                    f"SMS sent to {sms_successes}/{len(team_phones)} team members"
                )
        except Exception as e:
            err = f"SMS send failed: {e}"
            logger.error(err)
            result["errors"].append(err)
    else:
        result["errors"].append("No team phone numbers in config")

    # Step 5: Log the briefing send
    try:
        from services.portal_service import log_activity
        alert_count = len(briefing.get("alerts", []))
        mrr = briefing.get("executive_summary", {}).get(
            "monthly_recurring_revenue", 0
        )
        log_activity(
            client_id="",
            action="Daily briefing sent",
            entity_type="briefing",
            details={
                "mrr": mrr,
                "alerts": alert_count,
                "email_sent": result["email_sent"],
                "sms_sent": result["sms_sent"],
                "recipients_email": len(team_emails),
                "recipients_sms": len(team_phones),
            },
        )
    except Exception as e:
        logger.error("Failed to log briefing activity: %s", e)

    result["success"] = True
    return result


# ── History ─────────────────────────────────────────────────────────────────

def get_briefing_history(limit: int = 30) -> list[dict]:
    """Retrieve recent briefing send records from the activity log.

    Args:
        limit: Maximum number of records to return (default 30).

    Returns:
        List of activity_log rows for daily briefing sends, newest first.
    """
    try:
        from services.supabase_client import query_table
        return query_table(
            "activity_log",
            filters={"action": "Daily briefing sent"},
            order="-created_at",
            limit=limit,
        ) or []
    except Exception as e:
        logger.error("Failed to load briefing history: %s", e)
        return []
