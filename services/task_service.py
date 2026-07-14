# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Task management + daily-email composition service.

Drop into: mctv-bot/services/task_service.py

Public API:
    CRUD ............ create_task, update_task, mark_done, snooze, reassign
    Query ........... list_for_member, list_group, list_overdue, list_upcoming
    Maintenance ..... unsnooze_due() — wake snoozed tasks whose date arrived
    Auto-generate ... generate_from_signals() — pulls overdue A/R, stalled deals,
                      renewal alerts, NPS, Field Notes action items
    Compose ......... build_email_for_member(team_member) -> dict with subject,
                      html_body, plain_body, task_count
"""
from __future__ import annotations

import html
import logging
import os
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from typing import Any

import anthropic
from supabase import create_client, Client

logger = logging.getLogger("tasks")

CLAUDE_MODEL = "claude-sonnet-5"

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


def local_today() -> date:
    """Today in MCTV's timezone (America/Chicago), not the server's UTC.

    Render runs in UTC — the plain stdlib "today" would roll over at
    6-7 PM Central and shift due dates, overdue buckets, and the daily
    email a day early every evening.
    """
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Chicago")).date()
    except Exception:  # tzdata missing in the image — fall back to fixed CST
        return (datetime.now(timezone.utc) - timedelta(hours=6)).date()


# ---------------------------------------------------------------------------
# Priority ordering — tasks.priority is TEXT, so server-side ORDER BY sorts
# alphabetically (urgent > normal > low > high). Rank in Python instead.
# ---------------------------------------------------------------------------

_PRI_RANK = {"urgent": 0, "high": 1, "normal": 2, "low": 3}

# Assignee identity is a first name (see the Tasks page + EMAIL_TO_NAME below).
TEAM_NAMES = {"Creed", "Mary", "Swayze", "Jagger", "Elliot"}


def _sort_tasks(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda t: (
            _PRI_RANK.get((t.get("priority") or "normal"), 2),
            t.get("due_date") or "9999-12-31",
        ),
    )


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


def unsnooze_due() -> int:
    """Wake snoozed tasks whose snooze date has arrived (back to pending).

    Without this, snoozed tasks never reappear: every list query filters
    status='pending'. Called from the Tasks page and the daily cron.
    """
    res = (
        _supabase().table("tasks")
        .update({"status": "pending"})
        .eq("status", "snoozed")
        .lte("snoozed_until", local_today().isoformat())
        .execute()
    )
    n = len(res.data or [])
    if n:
        logger.info("unsnoozed %d task(s)", n)
    return n


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def list_for_member(team_member_id: str, status: str = "pending") -> list[dict]:
    """All tasks assigned to a specific member."""
    res = (
        _supabase().table("tasks").select("*")
        .eq("assigned_to", team_member_id)
        .eq("status", status)
        .execute()
    )
    return _sort_tasks(res.data or [])


def list_group(status: str = "pending") -> list[dict]:
    """Tasks with no assignee (group/team-wide)."""
    res = (
        _supabase().table("tasks").select("*")
        .is_("assigned_to", "null")
        .eq("status", status)
        .execute()
    )
    return _sort_tasks(res.data or [])


def list_overdue(team_member_id: str | None = None) -> list[dict]:
    today = local_today().isoformat()
    q = _supabase().table("tasks").select("*").eq("status", "pending").lt("due_date", today)
    if team_member_id:
        q = q.eq("assigned_to", team_member_id)
    return _sort_tasks((q.execute()).data or [])


def list_upcoming(team_member_id: str | None = None, days: int = 7) -> list[dict]:
    today = local_today()
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

def _client_names(ids: set) -> dict[str, str]:
    """Map clients.id -> business_name for task titles."""
    ids = {i for i in ids if i}
    if not ids:
        return {}
    try:
        res = (
            _supabase().table("clients")
            .select("id, business_name")
            .in_("id", list(ids))
            .execute()
        )
        return {r["id"]: (r.get("business_name") or "client") for r in (res.data or [])}
    except Exception as e:  # noqa: BLE001
        logger.warning("client name lookup failed: %s", e)
        return {}


def generate_from_signals() -> dict[str, int]:
    """Scan the rest of MCTV's data for things that should be tasks.

    Returns counts per source, e.g. {"qbo_ar": 3, "stalled_deal": 1}.
    Idempotent: uses UNIQUE(source, source_id) to avoid duplicates.
    Column/table names verified against the live schema 2026-07-08.
    """
    counts: dict[str, int] = {"qbo_ar": 0, "stalled_deal": 0, "renewal": 0, "nps": 0, "field_note": 0}

    try:
        unsnooze_due()
    except Exception as e:  # noqa: BLE001
        logger.warning("unsnooze failed: %s", e)

    # --- 1. Overdue A/R: unpaid invoices 30+ days past due ---
    try:
        today = local_today()
        cutoff = (today - timedelta(days=30)).isoformat()
        invoices = (
            _supabase().table("invoices")
            .select("id, client_id, invoice_number, amount, due_date, status")
            .is_("paid_date", "null")
            .lt("due_date", cutoff)
            .neq("status", "draft")
            .neq("status", "cancelled")
            .execute()
        ).data or []
        names = _client_names({i.get("client_id") for i in invoices})
        for inv in invoices:
            try:
                days_over = (
                    (today - date.fromisoformat(inv["due_date"])).days
                    if inv.get("due_date") else 0
                )
                create_task(
                    title=(
                        f"Call {names.get(inv.get('client_id'), 'client')} about "
                        f"${float(inv.get('amount') or 0):,.0f} overdue {days_over} days "
                        f"(inv {inv.get('invoice_number', '?')})"
                    ),
                    priority="high" if days_over >= 60 else "normal",
                    due_date=today,
                    source="qbo_ar",
                    source_id=str(inv["id"]),
                    related_customer_id=inv.get("client_id"),
                )
                counts["qbo_ar"] += 1
            except Exception:  # noqa: BLE001 — UNIQUE conflict expected for already-seen invoices
                pass
    except Exception as e:  # noqa: BLE001
        logger.warning("auto-gen qbo_ar failed: %s", e)

    # --- 2. Stalled pipeline deals (>14 days since last contact) ---
    try:
        cutoff = (local_today() - timedelta(days=14)).isoformat()
        rows = (
            _supabase().table("pipeline_opportunities")
            .select("id, client_id, business_name, stage, last_contact_date")
            .lt("last_contact_date", cutoff)
            .execute()
        ).data or []
        # stage vocabulary is uncontrolled — filter closed/won/lost client-side
        stalled = [
            r for r in rows
            if not str(r.get("stage") or "").lower().startswith(("closed", "won", "lost"))
        ]
        for d in stalled:
            try:
                create_task(
                    title=f"{d.get('business_name', 'Deal')} hasn't moved in 14+ days — touch base",
                    priority="normal",
                    due_date=local_today(),
                    source="stalled_deal",
                    source_id=str(d["id"]),
                    related_customer_id=d.get("client_id"),
                )
                counts["stalled_deal"] += 1
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        logger.warning("auto-gen stalled_deal failed: %s", e)

    # --- 3. Contracts ending in the next 30 days ---
    try:
        today = local_today()
        soon = (today + timedelta(days=30)).isoformat()
        rows = (
            _supabase().table("contracts")
            .select("id, client_id, title, end_date, status, auto_renew")
            .gte("end_date", today.isoformat())
            .lte("end_date", soon)
            .execute()
        ).data or []
        contracts = [
            c for c in rows
            if str(c.get("status") or "").lower() not in ("cancelled", "expired", "declined", "void")
        ]
        names = _client_names({c.get("client_id") for c in contracts})
        for c in contracts:
            try:
                who = names.get(c.get("client_id")) or c.get("title") or "Contract"
                create_task(
                    title=f"{who} ends {c.get('end_date', 'soon')} — propose renewal",
                    priority="normal",
                    due_date=today,
                    source="renewal",
                    source_id=str(c["id"]),
                    related_customer_id=c.get("client_id"),
                    related_contract_id=str(c["id"]),
                )
                counts["renewal"] += 1
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        logger.warning("auto-gen renewal failed: %s", e)

    # --- 4. NPS detractors (responded in last 14 days, score <= 6) ---
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        nps = (
            _supabase().table("nps_responses")
            .select("id, client_id, score, what_not_working, responded_at")
            .lte("score", 6)
            .gte("responded_at", cutoff)
            .execute()
        ).data or []
        names = _client_names({r.get("client_id") for r in nps})
        for r in nps:
            try:
                create_task(
                    title=(
                        f"Follow up with {names.get(r.get('client_id'), 'client')} "
                        f"on NPS feedback (score {r.get('score')})"
                    ),
                    description=r.get("what_not_working"),
                    priority="high",
                    due_date=local_today(),
                    source="nps",
                    source_id=str(r["id"]),
                    related_customer_id=r.get("client_id"),
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
            _supabase().table("field_notes")
            .select("id, team_member_id, action_items, customer_id")
            .execute()
        ).data or []
        for n in notes:
            for i, ai in enumerate(n.get("action_items") or []):
                if not isinstance(ai, dict) or ai.get("done"):
                    continue
                source_id = f"{n['id']}-{i}"
                # field_notes.team_member_id is usually 'system' under the
                # shared-password portal — only assign when it's a real
                # team first name, else surface as a group task.
                tm = n.get("team_member_id")
                try:
                    create_task(
                        title=ai.get("text", "Field note follow-up"),
                        priority="normal",
                        due_date=date.fromisoformat(ai["due_date"]) if ai.get("due_date") else local_today(),
                        source="field_note",
                        source_id=source_id,
                        assigned_to=tm if tm in TEAM_NAMES else None,
                        related_customer_id=n.get("customer_id"),
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

# Task assignees are first names (set by the Tasks page); cron members are
# identified by email. This map bridges the two.
EMAIL_TO_NAME = {
    "creed@mctvofms.com": "Creed",
    "mmc@mctvofms.com": "Mary",
    "swayze@mctvofms.com": "Swayze",
    "jagger@mctvofms.com": "Jagger",
    "elliot@mctvofms.com": "Elliot",
}


def build_email_for_member(member: dict[str, Any]) -> dict[str, Any] | None:
    """Compose a personalized daily email. Returns None if no content to send."""
    tm_email = member.get("email", "") or ""
    tm_id = member.get("id") or tm_email or "unknown"
    name_src = (
        EMAIL_TO_NAME.get(tm_email.lower())
        or member.get("first_name")
        or member.get("display_name")
        or member.get("name")
        or ""
    ).strip()
    tm_first_name = name_src.split()[0] if name_src else "there"

    # Tasks are assigned by first name (see Tasks page), so query by name
    # when we have one; fall back to the raw member id.
    assignee_key = tm_first_name if name_src else tm_id

    overdue = list_overdue(assignee_key)
    today_iso = local_today().isoformat()
    today_tasks = [t for t in list_for_member(assignee_key) if t.get("due_date") == today_iso]
    group_tasks = list_group()
    upcoming = [t for t in list_upcoming(assignee_key, days=7) if t not in today_tasks]

    if not (overdue or today_tasks or group_tasks or upcoming):
        return None  # nothing to send

    is_owner = tm_email.lower() in OWNER_EMAILS
    opener = _generate_opener(tm_first_name, overdue, today_tasks, upcoming)

    today_str = f"{local_today():%A, %B} {local_today().day}"
    subject = f"\U0001F3AF Your MCTV daily — {today_str}"
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
                    f"Today is {local_today():%A} {local_today():%B} {local_today().day}.\n"
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

def _fmt_task_line(t: dict, as_html: bool = False) -> str:
    title = t.get("title", "(no title)")
    pri = (t.get("priority") or "normal").upper()
    pri_badge = f"[{pri}] " if pri in ("HIGH", "URGENT") else ""
    if t.get("due_date"):
        title_line = f"{pri_badge}{title} (due {t['due_date']})"
    else:
        title_line = f"{pri_badge}{title}"
    if as_html:
        # titles carry client names like "B&B Rentals" — escape for HTML email
        safe_title = html.escape(str(title))
        color = {"URGENT": "#C00000", "HIGH": "#ED7D31"}.get(pri, "#1F3864")
        return (
            f'<li style="margin: 6px 0;">'
            f'<span style="color:{color}; font-weight:600;">{pri_badge}</span>'
            f'{safe_title}'
            + (f' <span style="color:#888; font-size:12px;">due {html.escape(str(t["due_date"]))}</span>' if t.get("due_date") else "")
            + '</li>'
        )
    return f"• {title_line}"


def _section_html(label: str, icon: str, tasks: list[dict]) -> str:
    if not tasks:
        return ""
    body = "\n".join(_fmt_task_line(t, as_html=True) for t in tasks)
    return (
        f'<h3 style="color:#1F3864; border-bottom:2px solid #1F3864; padding-bottom:4px; '
        f'margin-top:24px;">{icon} {label} ({len(tasks)})</h3>\n'
        f'<ul style="padding-left:20px;">\n{body}\n</ul>'
    )


def _section_plain(label: str, icon: str, tasks: list[dict]) -> str:
    if not tasks:
        return ""
    body = "\n".join(_fmt_task_line(t, as_html=False) for t in tasks)
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
    date_str = f"{local_today():%A, %B} {local_today().day}, {local_today().year}"
    return f"""
<!DOCTYPE html>
<html><body style="font-family:Calibri,Arial,sans-serif; color:#222; max-width:640px; margin:auto; padding:16px;">
  <h2 style="color:#1F3864; margin-bottom:0;">\U0001F3AF Your MCTV daily</h2>
  <p style="color:#888; margin-top:4px;">{date_str}</p>
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
    date_str = f"{local_today():%A, %B} {local_today().day}, {local_today().year}"
    parts = [
        f"\U0001F3AF Your MCTV daily — {date_str}",
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
