# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Task management + daily-email composition service.

Drop into: mctv-bot/services/task_service.py

Public API:
    CRUD ............ create_task, update_task, mark_done, snooze, reassign
    Query ........... list_for_member, list_group, list_overdue, list_upcoming
    Auto-generate ... generate_from_signals() — pulls overdue A/R, stalled deals,
                      renewal alerts, NPS, Field Notes action items
    Compose ......... build_email_for_member(team_member) -> dict with subject,
                      html_body, plain_body, task_count
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from typing import Any

import anthropic
from supabase import create_client, Client

logger = logging.getLogger("tasks")

CLAUDE_MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Lazy clients
# ---------------------------------------------------------------------------

_sb: Client | None = None
_ant: anthropic.Anthropic | None = None


def _supabase() -> Client:
    global _sb
    if _sb is None:
        _sb = create_client(
            os.environ["SUPABASE_URL"],
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"],
        )
    return _sb


def _claude() -> anthropic.Anthropic:
    global _ant
    if _ant is None:
        _ant = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _ant


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_task(
    *,
    title: str,
    description: str | None = None,
    assigned_to: str | None = None,
    priority: str = "normal",
    due_date: date | None = None,
    source: str = "manual",
    source_id: str | None = None,
    related_customer_id: str | None = None,
    related_contract_id: str | None = None,
    created_by: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    row = {
        "title": title,
        "description": description,
        "assigned_to": assigned_to,
        "priority": priority,
        "due_date": due_date.isoformat() if due_date else None,
        "source": source,
        "source_id": source_id,
        "related_customer_id": related_customer_id,
        "related_contract_id": related_contract_id,
        "created_by": created_by,
        "tags": tags or [],
    }
    res = _supabase().table("tasks").insert(row).execute()
    return (res.data or [{}])[0]


def mark_done(task_id: str) -> None:
    _supabase().table("tasks").update({
        "status": "done",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", task_id).execute()


def snooze(task_id: str, until: date) -> None:
    _supabase().table("tasks").update({
        "status": "snoozed",
        "snoozed_until": until.isoformat(),
    }).eq("id", task_id).execute()


def reassign(task_id: str, new_assignee: str | None) -> None:
    _supabase().table("tasks").update({"assigned_to": new_assignee}).eq("id", task_id).execute()


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def list_for_member(team_member_id: str, status: str = "pending") -> list[dict]:
    """All tasks assigned to a specific member."""
    res = (
        _supabase().table("tasks").select("*")
        .eq("assigned_to", team_member_id)
        .eq("status", status)
        .order("priority", desc=True)
        .order("due_date", desc=False)
        .execute()
    )
    return res.data or []


def list_group(status: str = "pending") -> list[dict]:
    """Tasks with no assignee (group/team-wide)."""
    res = (
        _supabase().table("tasks").select("*")
        .is_("assigned_to", "null")
        .eq("status", status)
        .order("priority", desc=True)
        .order("due_date", desc=False)
        .execute()
    )
    return res.data or []


def list_overdue(team_member_id: str | None = None) -> list[dict]:
    today = date.today().isoformat()
    q = _supabase().table("tasks").select("*").eq("status", "pending").lt("due_date", today)
    if team_member_id:
        q = q.eq("assigned_to", team_member_id)
    return (q.order("priority", desc=True).execute()).data or []


def list_upcoming(team_member_id: str | None = None, days: int = 7) -> list[dict]:
    today = date.today()
    end = today + timedelta(days=days)
    q = (
        _supabase().table("tasks").select("*")
        .eq("status", "pending")
        .gte("due_date", today.isoformat())
        .lte("due_date", end.isoformat())
    )
    if team_member_id:
        q = q.eq("assigned_to", team_member_id)
    return (q.order("due_date", desc=False).execute()).data or []


# ---------------------------------------------------------------------------
# Auto-generation (Phase 2 entry point — call from daily cron)
# ---------------------------------------------------------------------------

def generate_from_signals() -> dict[str, int]:
    """Scan the rest of MCTV's data for things that should be tasks.

    Returns counts per source, e.g. {"qbo_ar": 3, "stalled_deal": 1}.
    Idempotent: uses UNIQUE(source, source_id) to avoid duplicates.
    """
    counts: dict[str, int] = {"qbo_ar": 0, "stalled_deal": 0, "renewal": 0, "nps": 0, "field_note": 0}

    # --- 1. QBO overdue A/R ---
    # Reads invoices table populated by qbo_reconcile cron.
    try:
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        invoices = (
            _supabase().table("invoices")
            .select("id, customer_id, customer_name, amount, days_overdue")
            .eq("status", "overdue")
            .gte("days_overdue", 30)
            .execute()
        ).data or []
        for inv in invoices:
            try:
                create_task(
                    title=(
                        f"Call {inv.get('customer_name','customer')} about "
                        f"${inv.get('amount',0):,.0f} overdue {inv.get('days_overdue',0)} days"
                    ),
                    priority="high" if inv.get("days_overdue", 0) >= 60 else "normal",
                    due_date=date.today(),
                    source="qbo_ar",
                    source_id=str(inv["id"]),
                    related_customer_id=inv.get("customer_id"),
                )
                counts["qbo_ar"] += 1
            except Exception:  # noqa: BLE001 — UNIQUE conflict expected for already-seen invoices
                pass
    except Exception as e:  # noqa: BLE001
        logger.warning("auto-gen qbo_ar failed: %s", e)

    # --- 2. Stalled deals (>14 days no movement) ---
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        stalled = (
            _supabase().table("deals")
            .select("id, customer_id, customer_name, stage, last_activity_at")
            .neq("status", "closed")
            .lt("last_activity_at", cutoff)
            .execute()
        ).data or []
        for d in stalled:
            try:
                create_task(
                    title=f"{d.get('customer_name','Deal')} hasn't moved in 14+ days — touch base",
                    priority="normal",
                    due_date=date.today(),
                    source="stalled_deal",
                    source_id=str(d["id"]),
                    related_customer_id=d.get("customer_id"),
                )
                counts["stalled_deal"] += 1
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        logger.warning("auto-gen stalled_deal failed: %s", e)

    # --- 3. Contract renewals in next 30 days ---
    try:
        soon = (date.today() + timedelta(days=30)).isoformat()
        contracts = (
            _supabase().table("contracts")
            .select("id, customer_id, customer_name, renewal_date")
            .gte("renewal_date", date.today().isoformat())
            .lte("renewal_date", soon)
            .execute()
        ).data or []
        for c in contracts:
            try:
                create_task(
                    title=f"{c.get('customer_name','Contract')} renews {c.get('renewal_date','soon')} — propose renewal",
                    priority="normal",
                    due_date=date.today(),
                    source="renewal",
                    source_id=str(c["id"]),
                    related_customer_id=c.get("customer_id"),
                    related_contract_id=str(c["id"]),
                )
                counts["renewal"] += 1
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        logger.warning("auto-gen renewal failed: %s", e)

    # --- 4. NPS detractors (last 14 days, score <= 6) ---
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        nps = (
            _supabase().table("nps_responses")
            .select("id, customer_id, customer_name, score, comment")
            .lte("score", 6)
            .gte("created_at", cutoff)
            .execute()
        ).data or []
        for r in nps:
            try:
                create_task(
                    title=f"Follow up with {r.get('customer_name','customer')} on NPS feedback (score {r.get('score')})",
                    description=r.get("comment"),
                    priority="high",
                    due_date=date.today(),
                    source="nps",
                    source_id=str(r["id"]),
                    related_customer_id=r.get("customer_id"),
                )
                counts["nps"] += 1
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        logger.warning("auto-gen nps failed: %s", e)

    # --- 5. Field Notes action items (open) ---
    # Pulls from field_notes.action_items JSONB array.
    try:
        notes = (
            _supabase().table("field_notes").select("id, team_member_id, action_items, related_customer_id, customer_id")
            .execute()
        ).data or []
        for n in notes:
            for i, ai in enumerate(n.get("action_items") or []):
                if ai.get("done"):
                    continue
                source_id = f"{n['id']}-{i}"
                try:
                    create_task(
                        title=ai.get("text", "Field note follow-up"),
                        priority="normal",
                        due_date=date.fromisoformat(ai["due_date"]) if ai.get("due_date") else date.today(),
                        source="field_note",
                        source_id=source_id,
                        assigned_to=n.get("team_member_id"),
                        related_customer_id=n.get("customer_id") or n.get("related_customer_id"),
                    )
                    counts["field_note"] += 1
                except Exception:  # noqa: BLE001
                    pass
    except Exception as e:  # noqa: BLE001
        logger.warning("auto-gen field_note failed: %s", e)

    logger.info("task auto-gen complete: %s", counts)
    return counts


# ---------------------------------------------------------------------------
# Email composition
# ---------------------------------------------------------------------------

OWNER_EMAILS = {"creed@mctvofms.com", "mmc@mctvofms.com"}


def build_email_for_member(member: dict[str, Any]) -> dict[str, Any] | None:
    """Compose a personalized daily email. Returns None if no content to send."""
    tm_id = member["id"]
    tm_email = member.get("email", "")
    tm_first_name = (member.get("first_name") or member.get("display_name") or "").split()[0] or "there"

    overdue = list_overdue(tm_id)
    today_iso = date.today().isoformat()
    today_tasks = [t for t in list_for_member(tm_id) if t.get("due_date") == today_iso]
    group_tasks = list_group()
    upcoming = [t for t in list_upcoming(tm_id, days=7) if t not in today_tasks]

    if not (overdue or today_tasks or group_tasks or upcoming):
        return None  # nothing to send

    is_owner = tm_email.lower() in OWNER_EMAILS
    opener = _generate_opener(tm_first_name, overdue, today_tasks, upcoming)

    subject = f"\U0001F3AF Your MCTV daily — {date.today().strftime('%A, %B %-d')}"
    html_body = _build_html(opener, overdue, today_tasks, group_tasks, upcoming, is_owner)
    plain_body = _build_plain(opener, overdue, today_tasks, group_tasks, upcoming, is_owner)
    task_count = len(overdue) + len(today_tasks) + len(group_tasks) + len(upcoming)

    return {
        "to": tm_email,
        "subject": subject,
        "html_body": html_body,
        "plain_body": plain_body,
        "task_count": task_count,
        "is_owner": is_owner,
    }


def _generate_opener(first_name: str, overdue: list, today: list, upcoming: list) -> str:
    n_overdue, n_today, n_upcoming = len(overdue), len(today), len(upcoming)
    try:
        msg = _claude().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=120,
            system=(
                "You write friendly, concise daily-briefing openers for sales-team members at "
                "MCTV Elite Advertising, an indoor billboard network in North Mississippi. "
                "Tone: warm, direct, slightly punchy. 30-50 words. No greeting cliches. "
                "Acknowledge the load honestly. Mention overdue if non-zero. End with a forward-looking nudge."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Write the opening for {first_name}'s daily email.\n"
                    f"Today is {date.today().strftime('%A %B %-d')}.\n"
                    f"They have {n_overdue} overdue, {n_today} due today, {n_upcoming} coming up this week."
                ),
            }],
        )
        return msg.content[0].text.strip()  # type: ignore[attr-defined]
    except Exception as e:  # noqa: BLE001
        logger.warning("opener generation failed: %s", e)
        # Fallback opener
        return (
            f"Good morning, {first_name}! "
            f"{n_overdue} overdue, {n_today} due today, {n_upcoming} coming up. Let's go."
        )


# ---------------------------------------------------------------------------
# HTML + plain text email rendering
# ---------------------------------------------------------------------------

def _fmt_task_line(t: dict, html: bool = False) -> str:
    title = t.get("title", "(no title)")
    pri = (t.get("priority") or "normal").upper()
    pri_badge = f"[{pri}] " if pri in ("HIGH", "URGENT") else ""
    if t.get("due_date"):
        title_line = f"{pri_badge}{title} (due {t['due_date']})"
    else:
        title_line = f"{pri_badge}{title}"
    if html:
        color = {"URGENT": "#C00000", "HIGH": "#ED7D31"}.get(pri, "#1F3864")
        return (
            f'<li style="margin: 6px 0;">'
            f'<span style="color:{color}; font-weight:600;">{pri_badge}</span>'
            f'{title}'
            + (f' <span style="color:#888; font-size:12px;">due {t["due_date"]}</span>' if t.get("due_date") else "")
            + '</li>'
        )
    return f"• {title_line}"


def _section_html(label: str, icon: str, tasks: list[dict]) -> str:
    if not tasks:
        return ""
    body = "\n".join(_fmt_task_line(t, html=True) for t in tasks)
    return (
        f'<h3 style="color:#1F3864; border-bottom:2px solid #1F3864; padding-bottom:4px; '
        f'margin-top:24px;">{icon} {label} ({len(tasks)})</h3>\n'
        f'<ul style="padding-left:20px;">\n{body}\n</ul>'
    )


def _section_plain(label: str, icon: str, tasks: list[dict]) -> str:
    if not tasks:
        return ""
    body = "\n".join(_fmt_task_line(t, html=False) for t in tasks)
    return f"\n──────────────────────────────\n{icon} {label} ({len(tasks)})\n──────────────────────────────\n{body}\n"


def _build_html(opener: str, overdue: list, today: list, group: list, upcoming: list, is_owner: bool) -> str:
    sections = (
        _section_html("Overdue", "\U0001F525", overdue)
        + _section_html("Today", "\U0001F4CB", today)
        + _section_html("Group tasks", "\U0001F465", group)
        + _section_html("Coming up this week", "\U0001F4C5", upcoming)
    )
    owner_block = ""
    if is_owner:
        owner_block = (
            '<div style="background:#F4F4F4; padding:12px; margin-top:24px; border-radius:6px;">'
            '<h3 style="color:#1F3864; margin-top:0;">Owner roll-up</h3>'
            '<p style="margin:4px 0;">Cash, A/R, team load and more — coming in Phase 2.</p>'
            '</div>'
        )
    return f"""
<!DOCTYPE html>
<html><body style="font-family:Calibri,Arial,sans-serif; color:#222; max-width:640px; margin:auto; padding:16px;">
  <h2 style="color:#1F3864; margin-bottom:0;">\U0001F3AF Your MCTV daily</h2>
  <p style="color:#888; margin-top:4px;">{date.today().strftime('%A, %B %-d, %Y')}</p>
  <p style="font-size:15px; line-height:1.5;">{opener}</p>
  {sections}
  {owner_block}
  <p style="margin-top:32px; color:#888; font-size:12px;">
    Manage your tasks at
    <a href="https://mctv-bot.onrender.com" style="color:#1F3864;">mctv-bot.onrender.com</a>
  </p>
</body></html>
"""


def _build_plain(opener: str, overdue: list, today: list, group: list, upcoming: list, is_owner: bool) -> str:
    parts = [
        f"\U0001F3AF Your MCTV daily — {date.today().strftime('%A, %B %-d, %Y')}",
        "",
        opener,
        _section_plain("Overdue", "\U0001F525", overdue),
        _section_plain("Today", "\U0001F4CB", today),
        _section_plain("Group tasks", "\U0001F465", group),
        _section_plain("Coming up this week", "\U0001F4C5", upcoming),
    ]
    if is_owner:
        parts.append("\nOwner roll-up: Cash + A/R summary coming in Phase 2.\n")
    parts.append("\nManage tasks: https://mctv-bot.onrender.com")
    return "\n".join(p for p in parts if p)
