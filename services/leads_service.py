"""Lead/intake storage and email notification service.

Uses Supabase REST API (cloud database) when configured, falls back to local
JSON files for local development.
"""

import json
import smtplib
import os
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


LEADS_DIR = Path(__file__).parent.parent / "data" / "leads"


# ── Supabase REST helpers ────────────────────────────────────────────────────

def _sb_config():
    """Return (url, key) if Supabase is configured, else (None, None)."""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_KEY", "")
    if url and key:
        return url, key
    return None, None


def _sb_headers(key: str) -> dict:
    """Standard headers for Supabase REST API."""
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _sb_request(method: str, endpoint: str, data: dict | None = None) -> list | None:
    """Make a request to the Supabase REST API. Returns parsed JSON or None."""
    url, key = _sb_config()
    if not url:
        return None

    full_url = f"{url}/rest/v1/{endpoint}"
    body = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(full_url, data=body, headers=_sb_headers(key), method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            if raw:
                return json.loads(raw)
            return []
    except Exception as e:
        print(f"[leads_service] Supabase {method} {endpoint} failed: {e}")
        return None


# ── Save ─────────────────────────────────────────────────────────────────────

def save_lead(lead_data: dict) -> str:
    """Save a lead. Uses Supabase if available, else local JSON."""
    lead_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    lead_data["id"] = lead_id
    lead_data["submitted_at"] = datetime.now().isoformat()
    lead_data["status"] = "new"

    result = _sb_request("POST", "leads", lead_data)
    if result is not None:
        return lead_id

    # Fallback: local JSON
    LEADS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = LEADS_DIR / f"{lead_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(lead_data, f, indent=2)

    return lead_id


# ── Read all ─────────────────────────────────────────────────────────────────

def get_all_leads() -> list[dict]:
    """Get all leads sorted by newest first."""
    result = _sb_request("GET", "leads?select=*&order=submitted_at.desc")
    if result is not None:
        return result

    # Fallback: local JSON
    LEADS_DIR.mkdir(parents=True, exist_ok=True)
    leads = []
    for filepath in sorted(LEADS_DIR.glob("*.json"), reverse=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                leads.append(json.load(f))
        except Exception:
            continue
    return leads


# ── Update status ────────────────────────────────────────────────────────────

def update_lead_status(lead_id: str, status: str):
    """Update a lead's status (new, contacted, proposal_sent, closed)."""
    result = _sb_request("PATCH", f"leads?id=eq.{lead_id}", {"status": status})
    if result is not None:
        return

    # Fallback: local JSON
    filepath = LEADS_DIR / f"{lead_id}.json"
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["status"] = status
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# ── Delete lead ──────────────────────────────────────────────────────────────

def delete_lead(lead_id: str):
    """Delete a lead by ID."""
    result = _sb_request("DELETE", f"leads?id=eq.{lead_id}")
    if result is not None:
        return

    # Fallback: local JSON
    filepath = LEADS_DIR / f"{lead_id}.json"
    if filepath.exists():
        filepath.unlink()


# ── Email notification ───────────────────────────────────────────────────────

def send_notification_email(lead_data: dict):
    """Send email notification to the team about a new lead.

    Uses SMTP settings from environment variables. Fails silently if not configured.
    """
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    notify_emails = os.environ.get("NOTIFY_EMAILS", "creed@mctvofms.com,mmc@mctvofms.com,swayze@mctvofms.com")

    if not smtp_host or not smtp_user:
        # Email not configured — skip silently
        return False

    try:
        subject = f"New MCTV Lead: {lead_data.get('business_name', 'Unknown')}"

        body = f"""
NEW ADVERTISING INQUIRY
========================

Business: {lead_data.get('business_name', 'N/A')}
Contact: {lead_data.get('contact_name', 'N/A')}
Email: {lead_data.get('contact_email', 'N/A')}
Phone: {lead_data.get('contact_phone', 'N/A')}
Industry: {lead_data.get('industry', 'N/A')}
City: {lead_data.get('city', 'N/A')}

Interest Level: {lead_data.get('interest_level', 'N/A')}
How They Heard About Us: {lead_data.get('how_heard', 'N/A')}

What They're Looking For:
{lead_data.get('goals', 'No details provided.')}

Additional Notes:
{lead_data.get('additional_notes', 'None')}

Submitted: {lead_data.get('submitted_at', 'N/A')}

---
Log in to the MCTV Bot to view all leads and generate a proposal.
"""

        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = notify_emails
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Port 465 = SSL, Port 587 = STARTTLS
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, notify_emails.split(","), msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, notify_emails.split(","), msg.as_string())

        return True

    except Exception:
        return False
