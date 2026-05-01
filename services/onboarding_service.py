# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Client onboarding wizard.

Triggered automatically when a contract activates. Sends a welcome email
with a 7-step checklist, seeds onboarding_state on the contract, and exposes
helpers for the team / client to mark steps complete.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from services.supabase_client import update_row, query_table

logger = logging.getLogger(__name__)


# Canonical 7-step onboarding checklist. Order matters — UI renders in order.
STEPS = [
    ("welcome",       "Welcome email received"),
    ("kickoff_call",  "Schedule a 15-min kickoff call"),
    ("creative",      "Submit your creative (logo, photos, ad copy)"),
    ("preview",       "Approve your first ad preview"),
    ("first_play",    "Confirm first ad ran on the network"),
    ("first_invoice", "Receive + pay first invoice"),
    ("first_report",  "Open your first traction report"),
]
STEP_KEYS = [s[0] for s in STEPS]
STEP_LABEL = dict(STEPS)


def default_state() -> dict:
    """Return a fresh onboarding state with all steps unchecked."""
    return {key: {"done": False, "done_at": None, "notes": ""} for key, _ in STEPS}


def start_onboarding(contract_id: str) -> dict | None:
    """Initialize onboarding state on a contract and send the welcome email.

    Idempotent — running twice on the same contract returns the existing
    state without re-sending email.
    """
    if not contract_id:
        return None

    rows = query_table("contracts", filters={"id": contract_id}, limit=1)
    if not rows:
        return None
    contract = rows[0]

    state = contract.get("onboarding_state")
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except (json.JSONDecodeError, TypeError):
            state = {}
    if not state:
        state = default_state()

    started = contract.get("onboarding_started_at")
    if started:
        return state  # already ran

    now_iso = datetime.now().isoformat()
    state["welcome"] = {"done": True, "done_at": now_iso, "notes": "Auto-sent on activation"}
    update_row("contracts", contract_id, {
        "onboarding_state": state,
        "onboarding_started_at": now_iso,
    })

    # Welcome email
    try:
        from services.notification_service import _send_email
        from services.portal_service import get_client
        client = get_client(contract.get("client_id", "")) or {}
        email = client.get("contact_email")
        contact = client.get("contact_name", "there")
        business = client.get("business_name", "")
        portal_url = os.environ.get("PORTAL_URL", "https://bot.mctvofms.com").rstrip("/")
        if email:
            _send_email(email, _welcome_subject(business), _welcome_body(contact, business, portal_url))
    except Exception as e:
        logger.warning("Welcome email failed for contract %s: %s", contract_id, e)

    return state


def mark_step(contract_id: str, step_key: str, done: bool = True,
              notes: str = "") -> dict | None:
    """Mark a single onboarding step done/undone."""
    if step_key not in STEP_KEYS:
        return None
    rows = query_table("contracts", filters={"id": contract_id}, limit=1)
    if not rows:
        return None
    contract = rows[0]
    state = contract.get("onboarding_state")
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except (json.JSONDecodeError, TypeError):
            state = {}
    if not state:
        state = default_state()

    state[step_key] = {
        "done": done,
        "done_at": datetime.now().isoformat() if done else None,
        "notes": notes,
    }

    completed_all = all(state.get(k, {}).get("done") for k in STEP_KEYS)
    update = {"onboarding_state": state}
    if completed_all:
        update["onboarding_completed_at"] = datetime.now().isoformat()
    elif contract.get("onboarding_completed_at"):
        # Un-complete if a step was un-done
        update["onboarding_completed_at"] = None

    update_row("contracts", contract_id, update)
    return state


def get_state(contract_id: str) -> dict:
    rows = query_table("contracts",
                        select="onboarding_state,onboarding_started_at,onboarding_completed_at",
                        filters={"id": contract_id}, limit=1)
    if not rows:
        return default_state()
    state = rows[0].get("onboarding_state")
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except (json.JSONDecodeError, TypeError):
            state = {}
    return state or default_state()


def progress_pct(state: dict) -> int:
    if not state:
        return 0
    done = sum(1 for k in STEP_KEYS if state.get(k, {}).get("done"))
    return int(done / len(STEP_KEYS) * 100)


# ── Email templates ──────────────────────────────────────────────────────────

def _welcome_subject(business: str) -> str:
    return f"Welcome to MCTV — Here's What Happens Next"


def _welcome_body(contact: str, business: str, portal_url: str) -> str:
    return f"""Hi {contact},

Welcome to the MCTV network. We're glad to have {business} on board.

Here's exactly what happens over the next 30 days, in order:

  1. ✅ Welcome email (you're reading it).
  2. Your MCTV rep schedules a 15-minute kickoff call this week.
  3. You send us your creative — logo, photos, ad copy, or anything you
     already have. If you don't have it yet, no worries; we'll help build it.
  4. We send a preview of your first ad for your approval.
  5. Your ad starts running on the network. You'll get confirmation.
  6. Your first invoice arrives via QuickBooks with a Pay Now link.
  7. End of month one, your first traction report drops in your portal.

Your client portal is here:
{portal_url}/portal_dashboard

It tracks every step above plus live performance once we get our first
NTV360 sync.

Questions any time:
- Email: creed@mctvofms.com
- Phone: (601) 201-8202

Welcome aboard.

— Team MCTV
www.mctvofms.com
"""
