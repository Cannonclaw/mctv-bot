# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""SMS messaging service via Twilio.

Provides:
- Send individual texts with opt-in enforcement
- Template-based messaging for common events
- Opt-in/opt-out tracking (Supabase or local JSON fallback)
- Message history logging
- Phone number formatting

Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER
environment variables. Fails gracefully when not configured.
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "sms"

# Carrier/Twilio error codes mapped to plain-English explanations + likely fix.
# Used by the UI to show honest delivery feedback instead of a raw code.
ERROR_CODE_HINTS = {
    "30003": ("Unreachable handset",
              "Phone is off, out of service, or doesn't accept SMS."),
    "30004": ("Recipient blocked sender",
              "The recipient has blocked your number or muted A2P traffic."),
    "30005": ("Unknown handset",
              "Number doesn't exist or isn't provisioned for SMS."),
    "30006": ("Landline / unreachable carrier",
              "Number is a landline or the carrier doesn't support SMS."),
    "30007": ("Message filtered by carrier",
              "Carrier flagged the message as spam. On AT&T/T-Mobile this is "
              "almost always because your A2P 10DLC campaign isn't approved yet."),
    "30008": ("Unknown carrier error",
              "Carrier didn't return a reason. Often transient — retry later."),
    "30032": ("Toll-free number unverified",
              "Your toll-free sender hasn't been verified for A2P."),
    "30034": ("Unregistered A2P 10DLC sender",
              "Your 10DLC campaign isn't approved yet. AT&T blocks 100% of "
              "unregistered traffic. Wait for TCR approval, then retry."),
    "30041": ("Carrier delivery failure",
              "Recipient out of range or carrier downtime."),
    "21610": ("Recipient opted out (STOP)",
              "This number replied STOP. You cannot text them until they "
              "send START."),
    "21614": ("Invalid mobile number",
              "Number isn't a valid US mobile."),
}


def explain_error(error_code) -> tuple:
    """Return (short_label, long_explanation) for a Twilio error code."""
    if error_code is None:
        return ("", "")
    code = str(error_code)
    return ERROR_CODE_HINTS.get(code, (f"Error {code}",
                                       "See twilio.com/docs/api/errors for details."))


# ── Twilio Client ────────────────────────────────────────────────────────────

def _get_twilio_config() -> tuple:
    """Return (account_sid, auth_token, from_number, messaging_service_sid)."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_number = os.environ.get("TWILIO_PHONE_NUMBER", "")
    msg_svc_sid = os.environ.get("TWILIO_MESSAGING_SERVICE_SID", "")
    return sid, token, from_number, msg_svc_sid


def is_configured() -> bool:
    """Check if Twilio SMS is configured."""
    sid, token, from_number, msg_svc_sid = _get_twilio_config()
    # Need SID + token, plus either a Messaging Service or direct phone number
    return bool(sid and token and (msg_svc_sid or from_number))


def _get_client():
    """Get Twilio REST client. Returns None if not configured."""
    sid, token, _, _ = _get_twilio_config()
    if not sid or not token:
        return None
    try:
        from twilio.rest import Client
        return Client(sid, token)
    except ImportError:
        logger.warning("twilio package not installed — pip install twilio")
        return None
    except Exception as e:
        logger.error("Failed to create Twilio client: %s", e)
        return None


# ── Phone Number Formatting ──────────────────────────────────────────────────

def format_phone(phone: str) -> str:
    """Normalize a phone number to E.164 format (+1XXXXXXXXXX).

    Handles: (662) 555-1234, 662-555-1234, 6625551234, +16625551234
    Returns empty string if invalid.
    """
    if not phone:
        return ""
    # Strip everything except digits and leading +
    digits = re.sub(r"[^\d]", "", phone)
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    elif len(digits) > 11 and phone.startswith("+"):
        return f"+{digits}"
    return ""


# ── Consent / Opt-In Management ──────────────────────────────────────────────

def _consent_file() -> Path:
    """Local JSON file for opt-in tracking (fallback when Supabase unavailable)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "consent.json"


def _load_consent() -> dict:
    """Load consent records. Returns {phone: {opted_in: bool, ...}}."""
    # Try Supabase first
    try:
        from services.supabase_client import query_table
        rows = query_table("sms_consent", select="*")
        if rows is not None:
            return {r["phone"]: r for r in rows}
    except Exception:
        pass

    # Fallback: local JSON
    path = _consent_file()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_consent_local(data: dict):
    """Save consent to local JSON."""
    path = _consent_file()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def set_consent(phone: str, opted_in: bool, name: str = ""):
    """Record opt-in or opt-out for a phone number."""
    phone = format_phone(phone)
    if not phone:
        return

    record = {
        "phone": phone,
        "opted_in": opted_in,
        "name": name,
        "updated_at": datetime.now().isoformat(),
    }

    # Try Supabase
    try:
        from services.supabase_client import query_table, insert_row, update_row
        existing = query_table("sms_consent", filters={"phone": phone}, limit=1)
        if existing:
            update_row("sms_consent", existing[0]["id"], record)
        else:
            insert_row("sms_consent", record)
        return
    except Exception:
        pass

    # Fallback: local JSON
    data = _load_consent()
    data[phone] = record
    _save_consent_local(data)


def check_consent(phone: str) -> bool:
    """Check if a phone number has opted in to SMS."""
    phone = format_phone(phone)
    if not phone:
        return False
    consent = _load_consent()
    record = consent.get(phone, {})
    return record.get("opted_in", False)


def get_all_consent() -> list:
    """Get all consent records for the management UI."""
    consent = _load_consent()
    return list(consent.values()) if isinstance(consent, dict) else consent


# ── Message Logging ──────────────────────────────────────────────────────────

def _log_file() -> Path:
    """Local JSON file for message history."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "history.json"


def _log_message(to: str, body: str, template: str = "", status: str = "sent",
                 error: str = ""):
    """Log a sent message to Supabase or local JSON."""
    record = {
        "to": to,
        "body": body,
        "template": template,
        "status": status,
        "error": error,
        "sent_at": datetime.now().isoformat(),
        "sent_by": "MCTV Bot",
    }

    # Try Supabase
    try:
        from services.supabase_client import insert_row
        insert_row("sms_log", record)
        return
    except Exception:
        pass

    # Fallback: local JSON
    path = _log_file()
    history = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            history = json.load(f)
    history.insert(0, record)
    # Keep last 500 messages
    history = history[:500]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_message_history(limit: int = 50) -> list:
    """Get recent message history."""
    # Try Supabase
    try:
        from services.supabase_client import query_table
        rows = query_table("sms_log", order="-sent_at", limit=limit)
        if rows is not None:
            return rows
    except Exception:
        pass

    # Fallback: local JSON
    path = _log_file()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            history = json.load(f)
        return history[:limit]
    return []


# ── Send SMS ─────────────────────────────────────────────────────────────────

def send_sms(to: str, body: str, template: str = "",
             bypass_consent: bool = False) -> dict:
    """Send a text message via Twilio.

    Args:
        to: Phone number (any format — will be normalized)
        body: Message text (auto-appends opt-out instructions)
        template: Template name for logging (optional)
        bypass_consent: Skip consent check (for opt-out confirmations only)

    Returns:
        {"success": bool, "sid": str, "error": str}
    """
    to_formatted = format_phone(to)
    if not to_formatted:
        return {"success": False, "sid": "", "error": f"Invalid phone number: {to}"}

    # Check consent (unless bypassing for opt-out confirmation)
    if not bypass_consent and not check_consent(to_formatted):
        return {
            "success": False,
            "sid": "",
            "error": f"No SMS consent on file for {to_formatted}. "
                     f"Opt them in first.",
        }

    # Check Twilio config
    if not is_configured():
        _log_message(to_formatted, body, template, status="skipped",
                     error="Twilio not configured")
        return {"success": False, "sid": "", "error": "Twilio SMS not configured"}

    _, _, from_number, msg_svc_sid = _get_twilio_config()
    client = _get_client()
    if not client:
        return {"success": False, "sid": "", "error": "Could not create Twilio client"}

    # Append opt-out instructions (TCPA compliance)
    full_body = body.strip()
    if "STOP" not in full_body.upper():
        full_body += "\n\nReply STOP to unsubscribe."

    try:
        # Use Messaging Service SID for A2P 10DLC compliance when available,
        # fall back to direct phone number for backward compatibility
        if msg_svc_sid:
            message = client.messages.create(
                body=full_body,
                messaging_service_sid=msg_svc_sid,
                to=to_formatted,
            )
        else:
            message = client.messages.create(
                body=full_body,
                from_=from_number,
                to=to_formatted,
            )
        _log_message(to_formatted, full_body, template, status="sent")
        return {"success": True, "sid": message.sid, "error": ""}
    except Exception as e:
        error_msg = str(e)
        _log_message(to_formatted, full_body, template, status="failed",
                     error=error_msg)
        logger.error("SMS send failed to %s: %s", to_formatted, error_msg)
        return {"success": False, "sid": "", "error": error_msg}


# ── Message Templates ────────────────────────────────────────────────────────

TEMPLATES = {
    "proposal_sent": {
        "name": "Proposal Sent",
        "body": (
            "Hi {contact_name}! This is {rep_name} from MCTV Elite Advertising. "
            "I just sent over a custom advertising proposal for {business_name}. "
            "Check your email and let me know if you have any questions!"
        ),
        "variables": ["contact_name", "rep_name", "business_name"],
    },
    "follow_up_3day": {
        "name": "3-Day Follow Up",
        "body": (
            "Hi {contact_name}, just following up on the MCTV advertising proposal "
            "I sent for {business_name}. Would love to answer any questions — "
            "feel free to call or text me back. —{rep_name}"
        ),
        "variables": ["contact_name", "business_name", "rep_name"],
    },
    "traction_report": {
        "name": "Traction Report Ready",
        "body": (
            "Hi {contact_name}! Your latest MCTV performance report is ready. "
            "{total_plays} ad plays across {venue_count} venues this period. "
            "Full report sent to your email. —{rep_name}, MCTV"
        ),
        "variables": ["contact_name", "total_plays", "venue_count", "rep_name"],
    },
    "invoice_reminder": {
        "name": "Invoice Reminder",
        "body": (
            "Hi {contact_name}, friendly reminder that your MCTV invoice "
            "({invoice_number} — ${amount}) is due {due_date}. "
            "Let us know if you have any questions. —MCTV"
        ),
        "variables": ["contact_name", "invoice_number", "amount", "due_date"],
    },
    "contract_ready": {
        "name": "Contract Ready",
        "body": (
            "Hi {contact_name}! Your MCTV advertising contract for {business_name} "
            "is ready to sign. Check your email for the link, or log into your "
            "client portal. —{rep_name}, MCTV"
        ),
        "variables": ["contact_name", "business_name", "rep_name"],
    },
    "welcome_new_client": {
        "name": "Welcome New Client",
        "body": (
            "Welcome to the MCTV family, {contact_name}! We're excited to get "
            "{business_name} on screens across North Mississippi. Your rep "
            "{rep_name} will be in touch to get everything set up. —MCTV"
        ),
        "variables": ["contact_name", "business_name", "rep_name"],
    },
    "creative_live": {
        "name": "Creative Now Live",
        "body": (
            "Great news, {contact_name}! Your new ad for {business_name} is now "
            "live on MCTV screens. Keep an eye out for it at venues around town! "
            "—{rep_name}, MCTV"
        ),
        "variables": ["contact_name", "business_name", "rep_name"],
    },
    "host_check_in": {
        "name": "Host Venue Check-In",
        "body": (
            "Hi {contact_name}! Just checking in on the MCTV screens at "
            "{venue_name}. Everything running smoothly? Let me know if you "
            "need anything. —{rep_name}, MCTV"
        ),
        "variables": ["contact_name", "venue_name", "rep_name"],
    },
    "contract_expiring": {
        "name": "Contract Expiring",
        "body": (
            "Hi {contact_name}, your MCTV advertising contract for {business_name} "
            "expires in {days_remaining} days. Contact us to discuss renewal options. "
            "\u2014{rep_name}, MCTV"
        ),
        "variables": ["contact_name", "business_name", "days_remaining", "rep_name"],
    },
    "custom": {
        "name": "Custom Message",
        "body": "{message}",
        "variables": ["message"],
    },
}


def get_templates() -> dict:
    """Return available message templates."""
    return TEMPLATES


def get_message_status(sid: str) -> dict:
    """Fetch current delivery status for a previously-sent message.

    Returns {"status": str, "error_code": str|None, "error_label": str,
             "error_detail": str}. Status values mirror Twilio's:
    queued, sending, sent, delivered, undelivered, failed, accepted.
    Empty status means the lookup failed.
    """
    if not sid:
        return {"status": "", "error_code": None, "error_label": "",
                "error_detail": "No message SID"}
    client = _get_client()
    if not client:
        return {"status": "", "error_code": None, "error_label": "",
                "error_detail": "Twilio client unavailable"}
    try:
        msg = client.messages(sid).fetch()
        label, detail = explain_error(msg.error_code)
        return {
            "status": msg.status or "",
            "error_code": msg.error_code,
            "error_label": label,
            "error_detail": detail,
        }
    except Exception as e:
        logger.error("Failed to fetch message %s: %s", sid, e)
        return {"status": "", "error_code": None, "error_label": "",
                "error_detail": str(e)}


def wait_for_delivery(sid: str, timeout_s: int = 12, poll_s: float = 2.0) -> dict:
    """Poll Twilio until the message reaches a terminal state or timeout.

    Terminal states: delivered, undelivered, failed. Returns the same shape
    as get_message_status. On timeout, returns the last non-terminal status
    (typically "sent" or "queued") so callers can surface "still pending".
    """
    terminal = {"delivered", "undelivered", "failed"}
    deadline = time.time() + timeout_s
    last = {"status": "", "error_code": None, "error_label": "",
            "error_detail": ""}
    while time.time() < deadline:
        last = get_message_status(sid)
        if last.get("status") in terminal:
            return last
        time.sleep(poll_s)
    return last


def send_template(template_key: str, to: str, variables: dict) -> dict:
    """Send a template-based message.

    Args:
        template_key: Key from TEMPLATES dict
        to: Phone number
        variables: Dict of template variable values

    Returns:
        {"success": bool, "sid": str, "error": str}
    """
    template = TEMPLATES.get(template_key)
    if not template:
        return {"success": False, "sid": "", "error": f"Unknown template: {template_key}"}

    try:
        body = template["body"].format(**variables)
    except KeyError as e:
        return {"success": False, "sid": "",
                "error": f"Missing template variable: {e}"}

    return send_sms(to, body, template=template_key)
