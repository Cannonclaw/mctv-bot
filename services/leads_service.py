"""Lead/intake storage and email notification service.

Uses Supabase (cloud database) when configured, falls back to local JSON files.
"""

import json
import smtplib
import os
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


LEADS_DIR = Path(__file__).parent.parent / "data" / "leads"


# ── Supabase client (lazy init) ─────────────────────────────────────────────

_supabase_client = None


def _get_supabase():
    """Return a Supabase client if configured, else None."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        print(f"[leads_service] Supabase init failed: {e}")
        return None


# ── Save ─────────────────────────────────────────────────────────────────────

def save_lead(lead_data: dict) -> str:
    """Save a lead. Uses Supabase if available, else local JSON."""
    lead_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    lead_data["id"] = lead_id
    lead_data["submitted_at"] = datetime.now().isoformat()
    lead_data["status"] = "new"

    sb = _get_supabase()
    if sb:
        try:
            sb.table("leads").insert(lead_data).execute()
            return lead_id
        except Exception as e:
            print(f"[leads_service] Supabase insert failed: {e}")
            # Fall through to JSON backup

    # Fallback: local JSON
    LEADS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = LEADS_DIR / f"{lead_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(lead_data, f, indent=2)

    return lead_id


# ── Read all ─────────────────────────────────────────────────────────────────

def get_all_leads() -> list[dict]:
    """Get all leads sorted by newest first."""
    sb = _get_supabase()
    if sb:
        try:
            resp = sb.table("leads").select("*").order(
                "submitted_at", desc=True
            ).execute()
            return resp.data or []
        except Exception as e:
            print(f"[leads_service] Supabase read failed: {e}")

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
    sb = _get_supabase()
    if sb:
        try:
            sb.table("leads").update({"status": status}).eq(
                "id", lead_id
            ).execute()
            return
        except Exception as e:
            print(f"[leads_service] Supabase update failed: {e}")

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
    sb = _get_supabase()
    if sb:
        try:
            sb.table("leads").delete().eq("id", lead_id).execute()
            return
        except Exception as e:
            print(f"[leads_service] Supabase delete failed: {e}")

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

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, notify_emails.split(","), msg.as_string())

        return True

    except Exception:
        return False
