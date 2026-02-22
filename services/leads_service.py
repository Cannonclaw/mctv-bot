"""Lead/intake storage and email notification service."""

import json
import smtplib
import os
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


LEADS_DIR = Path(__file__).parent.parent / "data" / "leads"


def save_lead(lead_data: dict) -> str:
    """Save a lead submission to a JSON file. Returns the lead ID."""
    LEADS_DIR.mkdir(parents=True, exist_ok=True)

    lead_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    lead_data["id"] = lead_id
    lead_data["submitted_at"] = datetime.now().isoformat()
    lead_data["status"] = "new"

    filepath = LEADS_DIR / f"{lead_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(lead_data, f, indent=2)

    return lead_id


def get_all_leads() -> list[dict]:
    """Get all leads sorted by newest first."""
    LEADS_DIR.mkdir(parents=True, exist_ok=True)
    leads = []
    for filepath in sorted(LEADS_DIR.glob("*.json"), reverse=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                leads.append(json.load(f))
        except Exception:
            continue
    return leads


def update_lead_status(lead_id: str, status: str):
    """Update a lead's status (new, contacted, proposal_sent, closed)."""
    filepath = LEADS_DIR / f"{lead_id}.json"
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["status"] = status
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


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
