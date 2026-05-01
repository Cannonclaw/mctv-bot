# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Host referral program — track who referred whom and reward conversions.

Flow:
  1. A host gets a referral_code (auto-generated on demand).
  2. Their share URL: https://bot.mctvofms.com/Intake?ref=<CODE>
  3. When a prospect submits the intake with a ref param, a row is inserted
     in `referrals` with status='pending' and the lead_id captured.
  4. When that lead converts to a client + signs a contract, the referral
     is marked 'converted' and a reward is queued for fulfillment.
"""

import logging
import secrets
import string
from datetime import datetime

from services.supabase_client import (
    insert_row, query_table, update_row, upsert_row,
)

logger = logging.getLogger(__name__)


def _generate_code(length: int = 6) -> str:
    """Generate a short, readable referral code (uppercase letters + digits, no ambiguous chars)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I/O/0/1
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_or_create_code(client_id: str) -> str:
    """Return the host's referral_code, generating one on first call."""
    if not client_id:
        return ""
    rows = query_table("clients", select="id,referral_code",
                       filters={"id": client_id}, limit=1)
    if rows and rows[0].get("referral_code"):
        return rows[0]["referral_code"]

    # Generate + persist with a couple of retries on collision
    for _ in range(5):
        code = _generate_code()
        existing = query_table("clients", select="id",
                               filters={"referral_code": code}, limit=1)
        if not existing:
            update_row("clients", client_id, {"referral_code": code})
            return code
    # Fallback: unlikely to collide at length 8
    code = _generate_code(8)
    update_row("clients", client_id, {"referral_code": code})
    return code


def find_client_by_code(code: str) -> dict | None:
    """Look up the host who owns this referral code."""
    if not code:
        return None
    code = code.strip().upper()
    rows = query_table("clients", select="*",
                       filters={"referral_code": code}, limit=1)
    return rows[0] if rows else None


def record_referral_signup(referral_code: str, lead: dict) -> dict | None:
    """Called when a new intake lands with ?ref=<code>.

    Creates a 'pending' referral row tying the host to the new lead.
    Returns the inserted row, or None if the code didn't match.
    """
    if not referral_code or not lead:
        return None
    host = find_client_by_code(referral_code)
    if not host:
        logger.info("Referral code %s did not match any client", referral_code)
        return None

    payload = {
        "referrer_client_id": host["id"],
        "referrer_code": referral_code.upper(),
        "referred_lead_id": str(lead.get("id", "")),
        "referred_business_name": lead.get("business_name", ""),
        "referred_contact_name": lead.get("contact_name", ""),
        "referred_contact_email": lead.get("contact_email", ""),
        "status": "pending",
    }
    return insert_row("referrals", payload)


def mark_referral_qualified(lead_id: str, client_id: str = "") -> dict | None:
    """Bump a pending referral to 'qualified' when the lead becomes a client.

    Lifecycle: pending -> qualified -> converted -> paid. No reward at this
    stage; that fires on contract activation in mark_referral_converted.
    """
    rows = query_table(
        "referrals",
        filters={"referred_lead_id": str(lead_id), "status": "pending"},
        limit=1,
    )
    if not rows:
        return None
    ref = rows[0]
    return update_row("referrals", ref["id"], {
        "status": "qualified",
        "converted_client_id": client_id or None,
        "updated_at": datetime.now().isoformat(),
    })


def mark_referral_converted(lead_id: str, client_id: str = "",
                            contract_id: str = "",
                            reward_value: float = 0.0,
                            reward_type: str = "screen_time") -> dict | None:
    """Mark a referral as converted when the contract activates.

    Matches both 'pending' and 'qualified' rows so it works whether or not
    mark_referral_qualified ran earlier.

    Returns the updated referral row, or None if no matching referral exists.
    """
    # Try qualified first, then pending
    for status in ("qualified", "pending"):
        rows = query_table(
            "referrals",
            filters={"referred_lead_id": str(lead_id), "status": status},
            limit=1,
        )
        if rows:
            ref = rows[0]
            return update_row("referrals", ref["id"], {
                "status": "converted",
                "converted_client_id": client_id or None,
                "converted_contract_id": contract_id or None,
                "reward_value": reward_value,
                "reward_type": reward_type,
                "updated_at": datetime.now().isoformat(),
            })
    return None


def get_host_referrals(client_id: str) -> list:
    """Return all referrals attributed to this host, newest first."""
    return query_table(
        "referrals",
        filters={"referrer_client_id": client_id},
        order="-created_at",
    )


def get_host_referral_summary(client_id: str) -> dict:
    """Summarize referral activity for the host dashboard."""
    refs = get_host_referrals(client_id)
    pending = [r for r in refs if r.get("status") == "pending"]
    converted = [r for r in refs if r.get("status") == "converted"]
    paid = [r for r in refs if r.get("status") == "paid"]
    pending_reward = sum(float(r.get("reward_value", 0) or 0) for r in converted if r.get("status") != "paid")
    paid_reward = sum(float(r.get("reward_value", 0) or 0) for r in paid)
    return {
        "total": len(refs),
        "pending_count": len(pending),
        "converted_count": len(converted),
        "paid_count": len(paid),
        "pending_reward_value": pending_reward,
        "paid_reward_value": paid_reward,
        "rows": refs,
    }
