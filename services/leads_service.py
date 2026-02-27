# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Lead/intake storage and email notification service.

Uses Supabase REST API (cloud database) when configured, falls back to local
JSON files for local development.
"""

import csv
import io
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


# ── Update lead (arbitrary fields) ──────────────────────────────────────────

def update_lead(lead_id: str, updates: dict):
    """Update arbitrary fields on a lead record (e.g., follow-up date/note)."""
    result = _sb_request("PATCH", f"leads?id=eq.{lead_id}", updates)
    if result is not None:
        return

    # Fallback: local JSON
    filepath = LEADS_DIR / f"{lead_id}.json"
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.update(updates)
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


# ── Lead Scoring ─────────────────────────────────────────────────────────

# High-value industries that tend to convert better for indoor digital advertising
HIGH_VALUE_INDUSTRIES = {
    "medical", "dental", "healthcare", "restaurant", "bar", "fitness", "gym",
    "salon", "barbershop", "real estate", "insurance", "attorney", "law",
    "chiropractic", "veterinary", "spa", "med spa",
}

# Active markets with established screen presence
ACTIVE_MARKETS = {"oxford", "starkville", "tupelo"}


def calculate_lead_score(lead: dict) -> int:
    """Calculate a lead score (0-100) based on available intake data.

    Scoring breakdown:
      - Interest level:  up to 40 pts
      - Has phone:       10 pts
      - Has email:       10 pts
      - Industry match:  5-15 pts
      - Active market:   5-15 pts
      - Has goals/msg:   10 pts
    """
    score = 0

    # Interest level (max 40)
    interest = (lead.get("interest_level") or "").lower()
    if "ready" in interest:
        score += 40
    elif "very" in interest:
        score += 30
    elif "interested" in interest:
        score += 20
    elif "curious" in interest:
        score += 10

    # Contact completeness
    if lead.get("contact_phone", "").strip():
        score += 10
    if lead.get("contact_email", "").strip():
        score += 10

    # Industry value
    industry = (lead.get("industry") or "").lower()
    if any(kw in industry for kw in HIGH_VALUE_INDUSTRIES):
        score += 15
    elif industry:
        score += 5

    # Market proximity
    city = (lead.get("city") or "").lower().strip()
    if city in ACTIVE_MARKETS:
        score += 15
    elif city:
        score += 5

    # Has goals / message
    if (lead.get("goals") or "").strip() or (lead.get("additional_notes") or "").strip():
        score += 10

    return min(score, 100)


def get_score_label(score: int) -> tuple[str, str]:
    """Return (label, color) for a lead score badge.

    Returns:
        ('Hot', 'green') | ('Warm', 'orange') | ('Cold', 'gray')
    """
    if score >= 70:
        return "Hot", "green"
    elif score >= 40:
        return "Warm", "orange"
    return "Cold", "gray"


# ── Bulk Operations ──────────────────────────────────────────────────────

def bulk_update_status(lead_ids: list[str], status: str):
    """Update status for multiple leads at once."""
    for lid in lead_ids:
        update_lead_status(lid, status)


def export_leads_csv(leads: list[dict]) -> str:
    """Export a list of lead dicts to a CSV string."""
    if not leads:
        return ""

    fieldnames = [
        "business_name", "contact_name", "contact_email", "contact_phone",
        "city", "industry", "interest_level", "how_heard", "goals",
        "additional_notes", "status", "submitted_at",
    ]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for lead in leads:
        writer.writerow(lead)
    return buf.getvalue()


# ── Email notification ───────────────────────────────────────────────────────

def send_notification_email(lead_data: dict):
    """Send email notification to the team about a new lead.

    Uses SMTP settings from environment variables. Fails silently if not configured.
    """
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user)
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
        msg["From"] = f"MCTV Portal <{smtp_from}>"
        msg["To"] = notify_emails
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Port 465 = SSL, Port 587 = STARTTLS
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, notify_emails.split(","), msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, notify_emails.split(","), msg.as_string())

        return True

    except Exception as e:
        print(f"[leads_service] EMAIL ERROR: {e}")
        return False
