# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Expanded email notifications for portal events.

Extends the existing SMTP pattern from leads_service.py for:
- Contract ready / signed
- Invoice sent / overdue
- Creative request status changes
- Report shared
- Portal account created
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _get_smtp_config() -> tuple:
    """Return SMTP config from environment. Returns (host, port, user, pass, from_addr)."""
    host = os.environ.get("SMTP_HOST", "")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    from_addr = os.environ.get("SMTP_FROM", user)  # Separate From address (e.g., shared mailbox)
    return host, port, user, password, from_addr


def _get_portal_url() -> str:
    """Get the portal base URL."""
    return os.environ.get("PORTAL_URL", "https://bot.mctvofms.com")


def _get_team_emails() -> str:
    """Get the team notification emails."""
    return os.environ.get(
        "NOTIFY_EMAILS",
        "creed@mctvofms.com,mmc@mctvofms.com,swayze@mctvofms.com"
    )


def _send_email(to_emails: str, subject: str, body: str) -> bool:
    """Send an email via SMTP. Returns True on success, False on failure.

    Authenticates with SMTP_USER but sends from SMTP_FROM (if set).
    This supports Microsoft 365 shared mailboxes where you authenticate
    as creed@mctvofms.com but send from portal@mctvofms.com.
    """
    host, port, user, password, from_addr = _get_smtp_config()
    if not host or not user:
        print(f"[notify] SMTP not configured — skipping: {subject}")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = f"MCTV Portal <{from_addr}>"
        msg["To"] = to_emails
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        recipients = [e.strip() for e in to_emails.split(",")]

        if port == 465:
            with smtplib.SMTP_SSL(host, port) as server:
                server.login(user, password)
                server.sendmail(from_addr, recipients, msg.as_string())
        else:
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(from_addr, recipients, msg.as_string())

        return True
    except Exception as e:
        print(f"[notify] EMAIL ERROR: {e}")
        return False


# ── Portal Account ───────────────────────────────────────────────────────────

def notify_portal_account_created(client_email: str, client_name: str,
                                  business_name: str, temp_password: str) -> bool:
    """Notify client that their portal account has been created."""
    portal_url = _get_portal_url()
    subject = f"Your MCTV Client Portal Account is Ready"
    body = f"""Hi {client_name},

Welcome to the MCTV Elite Advertising client portal!

Your account has been created for {business_name}. You can now log in to:
- View and sign your advertising contract
- Track your invoices and payment status
- Submit photos and graphics for your ads
- View your campaign performance reports

LOG IN HERE: {portal_url}/portal_login

Your login credentials:
  Email: {client_email}
  Temporary Password: {temp_password}

Please change your password after your first login.

If you have any questions, don't hesitate to reach out to your MCTV representative.

Best,
MCTV Elite Advertising
www.mctvofms.com
"""
    return _send_email(client_email, subject, body)


# ── Contracts ────────────────────────────────────────────────────────────────

def notify_contract_ready(client_email: str, client_name: str,
                          contract_title: str) -> bool:
    """Notify client that their contract is ready to review and sign."""
    portal_url = _get_portal_url()
    subject = f"Your MCTV Advertising Contract is Ready to Sign"
    body = f"""Hi {client_name},

Your advertising contract is ready for review!

Contract: {contract_title}

You can review the full contract and sign it electronically in your MCTV portal:
{portal_url}/portal_contract

If you have any questions about the terms, just reply to this email or call your MCTV representative.

Best,
MCTV Elite Advertising
www.mctvofms.com
"""
    return _send_email(client_email, subject, body)


def notify_contract_signed(contract_title: str, client_name: str,
                           business_name: str, signed_by: str) -> bool:
    """Notify the MCTV team that a client signed their contract."""
    subject = f"Contract Signed: {business_name}"
    body = f"""CONTRACT SIGNED
========================

Business: {business_name}
Contact: {client_name}
Contract: {contract_title}
Signed By: {signed_by}
Signed At: Now

Log in to the MCTV Bot to view the signed contract details.
"""
    return _send_email(_get_team_emails(), subject, body)


# ── Invoices ─────────────────────────────────────────────────────────────────

def notify_invoice_sent(client_email: str, client_name: str,
                        invoice_number: str, amount: float,
                        due_date: str) -> bool:
    """Notify client that a new invoice has been issued."""
    portal_url = _get_portal_url()
    subject = f"MCTV Invoice {invoice_number} — ${amount:.2f}"
    body = f"""Hi {client_name},

A new invoice has been issued for your MCTV advertising:

Invoice: {invoice_number}
Amount: ${amount:.2f}
Due Date: {due_date}

View your invoice details in your MCTV portal:
{portal_url}/portal_invoices

If you have any questions about this invoice, please contact your MCTV representative.

Best,
MCTV Elite Advertising
www.mctvofms.com
"""
    return _send_email(client_email, subject, body)


def notify_invoice_overdue(client_email: str, client_name: str,
                           invoice_number: str, amount: float,
                           due_date: str) -> bool:
    """Remind client about an overdue invoice."""
    subject = f"Reminder: MCTV Invoice {invoice_number} Past Due"
    body = f"""Hi {client_name},

This is a friendly reminder that your MCTV invoice is past due:

Invoice: {invoice_number}
Amount: ${amount:.2f}
Due Date: {due_date}

Please contact your MCTV representative if you need to discuss payment arrangements.

Best,
MCTV Elite Advertising
www.mctvofms.com
"""
    return _send_email(client_email, subject, body)


# ── Creative Requests ────────────────────────────────────────────────────────

def notify_creative_submitted(business_name: str, request_title: str,
                              request_type: str) -> bool:
    """Notify the MCTV team about a new creative request from a client."""
    subject = f"New Creative Request: {business_name}"
    body = f"""NEW CREATIVE REQUEST
========================

Business: {business_name}
Request: {request_title}
Type: {request_type}

Log in to the MCTV Bot to review the submission and attached files.
"""
    return _send_email(_get_team_emails(), subject, body)


def notify_creative_status_update(client_email: str, client_name: str,
                                  request_title: str, new_status: str,
                                  notes: str = "") -> bool:
    """Notify client about a status change on their creative request."""
    portal_url = _get_portal_url()

    status_messages = {
        "in_progress": "Your creative request is now being worked on by our team.",
        "review": "Your ad creative is ready for your review.",
        "approved": "Your ad creative has been approved and is being prepared for deployment.",
        "live": "Your new ad creative is now live on MCTV screens!",
        "rejected": "We need some changes to your submission. Please check the notes below.",
    }

    message = status_messages.get(new_status, f"Status updated to: {new_status}")

    subject = f"Creative Update: {request_title}"
    body = f"""Hi {client_name},

{message}

Request: {request_title}
New Status: {new_status.replace('_', ' ').title()}
"""
    if notes:
        body += f"\nNotes from MCTV: {notes}\n"

    body += f"""
View details in your MCTV portal:
{portal_url}/portal_creative

Best,
MCTV Elite Advertising
www.mctvofms.com
"""
    return _send_email(client_email, subject, body)


# ── Reports ──────────────────────────────────────────────────────────────────

def notify_report_shared(client_email: str, client_name: str,
                         report_title: str) -> bool:
    """Notify client that a new performance report is available."""
    portal_url = _get_portal_url()
    subject = f"Your MCTV Performance Report: {report_title}"
    body = f"""Hi {client_name},

A new performance report is available in your MCTV portal:

Report: {report_title}

View your campaign results, impressions, and insights:
{portal_url}/portal_reports

Best,
MCTV Elite Advertising
www.mctvofms.com
"""
    return _send_email(client_email, subject, body)


# ── SMS Notification Helpers ─────────────────────────────────────────────────
# These mirror the email notifications above but send a short text instead.
# They fail silently if Twilio is not configured or the contact hasn't opted in.

def _try_sms(phone: str, template_key: str, variables: dict):
    """Attempt to send an SMS notification. Fails silently."""
    if not phone:
        return
    try:
        from services.sms_service import send_template, is_configured
        if is_configured():
            send_template(template_key, phone, variables)
    except Exception as e:
        print(f"[notify] SMS failed ({template_key}): {e}")


def sms_proposal_sent(phone: str, contact_name: str, business_name: str,
                      rep_name: str = "Mary Michael"):
    """Text notification when a proposal is sent."""
    _try_sms(phone, "proposal_sent", {
        "contact_name": contact_name,
        "business_name": business_name,
        "rep_name": rep_name,
    })


def sms_contract_ready(phone: str, contact_name: str, business_name: str,
                       rep_name: str = "Mary Michael"):
    """Text notification when a contract is ready to sign."""
    _try_sms(phone, "contract_ready", {
        "contact_name": contact_name,
        "business_name": business_name,
        "rep_name": rep_name,
    })


def sms_invoice_reminder(phone: str, contact_name: str, invoice_number: str,
                         amount: str, due_date: str):
    """Text reminder for an upcoming or overdue invoice."""
    _try_sms(phone, "invoice_reminder", {
        "contact_name": contact_name,
        "invoice_number": invoice_number,
        "amount": amount,
        "due_date": due_date,
    })


def sms_welcome_client(phone: str, contact_name: str, business_name: str,
                       rep_name: str = "Mary Michael"):
    """Welcome text when a new client is onboarded."""
    _try_sms(phone, "welcome_new_client", {
        "contact_name": contact_name,
        "business_name": business_name,
        "rep_name": rep_name,
    })


def sms_creative_live(phone: str, contact_name: str, business_name: str,
                      rep_name: str = "Mary Michael"):
    """Text notification when a client's ad creative goes live."""
    _try_sms(phone, "creative_live", {
        "contact_name": contact_name,
        "business_name": business_name,
        "rep_name": rep_name,
    })


def sms_traction_report(phone: str, contact_name: str, total_plays: str,
                        venue_count: str, rep_name: str = "Mary Michael"):
    """Text summary when a traction report is generated."""
    _try_sms(phone, "traction_report", {
        "contact_name": contact_name,
        "total_plays": total_plays,
        "venue_count": venue_count,
        "rep_name": rep_name,
    })
