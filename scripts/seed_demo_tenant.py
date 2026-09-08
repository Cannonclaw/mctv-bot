# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Create (or refresh) a synthetic sandbox tenant for partner evaluation.

Issues a read-only demo portal account to an outside organization — e.g. NTV360
— backed entirely by fabricated data, so an evaluator never sees a real client,
a real rate, or a real invoice.

Prerequisite: run ``scripts/024_partner_demo_access.sql`` first.

Usage::

    python scripts/seed_demo_tenant.py --org "NTV360" \\
        --email partner-demo@mctvofms.com --days 30

    python scripts/seed_demo_tenant.py --org "NTV360" --show
    python scripts/seed_demo_tenant.py --org "NTV360" --revoke

The generated password is printed once. Deliver it out of band, and only after
the NDA / evaluation agreement is signed.
"""

import argparse
import secrets
import string
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.supabase_client import (  # noqa: E402
    query_table, insert_row, update_row, delete_row, sign_up,
)

DEMO_BUSINESS_NAME = "Demo Advertiser Co."
DEMO_CONTACT_NAME = "Sample Contact"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _generate_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _find_demo_client(org: str) -> dict | None:
    rows = query_table("clients", filters={"partner_org": org}) or []
    for row in rows:
        if row.get("is_demo"):
            return row
    return None


def _fail(message: str) -> None:
    print(f"[seed_demo_tenant] ERROR: {message}")
    sys.exit(1)


# ── Synthetic data ──────────────────────────────────────────────────────────

def _seed_contract(client_id: str) -> dict | None:
    start = date.today().replace(day=1) - timedelta(days=120)
    end = start + timedelta(days=365)
    return insert_row("contracts", {
        "client_id": client_id,
        "contract_type": "advertising",
        "title": "Sample Advertising Partnership - Demo",
        "tier_name": "20 Screens",
        "screen_count": 20,
        "monthly_rate": 500.00,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "term_months": 12,
        "status": "active",
        "signed_by": DEMO_CONTACT_NAME,
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "markets": ["Oxford", "Starkville"],
        "created_by": "demo-seed",
    })


def _seed_invoices(client_id: str, contract_id: str) -> int:
    """Three invoices: two paid, one outstanding, so the UI has range."""
    created = 0
    today = date.today()
    stamp = secrets.token_hex(3).upper()

    for offset, status in ((3, "paid"), (2, "paid"), (1, "sent")):
        issued = (today.replace(day=1) - timedelta(days=30 * offset))
        due = issued + timedelta(days=15)
        row = insert_row("invoices", {
            "client_id": client_id,
            "contract_id": contract_id,
            "invoice_number": f"DEMO-{stamp}-{offset:02d}",
            "amount": 500.00,
            "description": "Monthly advertising - 20 screens (sample data)",
            "period_start": issued.isoformat(),
            "period_end": (issued + timedelta(days=29)).isoformat(),
            "issued_date": issued.isoformat(),
            "due_date": due.isoformat(),
            "paid_date": due.isoformat() if status == "paid" else None,
            "status": status,
            "notes": "Sample invoice - not a real charge.",
        })
        if row:
            created += 1
    return created


def _seed_reports(client_id: str) -> int:
    created = 0
    today = date.today()
    for offset in (2, 1):
        month = today.replace(day=1) - timedelta(days=30 * offset)
        row = insert_row("client_reports", {
            "client_id": client_id,
            "report_type": "traction",
            "title": f"Sample Traction Report - {month.strftime('%B %Y')}",
            "campaign_period": month.strftime("%Y-%m"),
            "total_plays": 48_000 + offset * 1_400,
            "total_impressions": (48_000 + offset * 1_400) * 60,
            "total_venues": 20,
            "highlights": "Sample data for evaluation purposes only.",
        })
        if row:
            created += 1
    return created


def _seed_creative(client_id: str) -> int:
    created = 0
    samples = [
        ("new_ad", "Sample: Spring promo ad", "approved"),
        ("update_ad", "Sample: Update hours on existing ad", "in_progress"),
    ]
    for req_type, title, status in samples:
        row = insert_row("creative_requests", {
            "client_id": client_id,
            "request_type": req_type,
            "title": title,
            "description": "Sample creative request for evaluation purposes only.",
            "status": status,
            "priority": "normal",
        })
        if row:
            created += 1
    return created


# ── Commands ────────────────────────────────────────────────────────────────

def show(org: str):
    client = _find_demo_client(org)
    if not client:
        print(f"No demo tenant found for '{org}'.")
        return

    cid = client["id"]
    print(f"Demo tenant for {org}")
    print(f"  client_id     : {cid}")
    print(f"  business_name : {client.get('business_name')}")
    print(f"  contact_email : {client.get('contact_email')}")
    print(f"  portal_user_id: {client.get('portal_user_id') or '(not invited)'}")
    print(f"  expires_at    : {client.get('portal_access_expires_at') or '(no expiry)'}")

    for table in ("contracts", "invoices", "client_reports", "creative_requests"):
        rows = query_table(table, filters={"client_id": cid}) or []
        print(f"  {table:<18}: {len(rows)} row(s)")


def revoke(org: str):
    """Expire access immediately. Data is retained for the audit trail."""
    client = _find_demo_client(org)
    if not client:
        _fail(f"No demo tenant found for '{org}'.")

    update_row("clients", client["id"], {
        "portal_access_expires_at": datetime.now(timezone.utc).isoformat(),
        "status": "paused",
    })
    print(f"Access revoked for '{org}'. Live sessions are ejected within 60s.")
    print("Demo data and the audit trail were left in place.")


def purge(org: str):
    """Delete the demo tenant and every synthetic row attached to it."""
    client = _find_demo_client(org)
    if not client:
        _fail(f"No demo tenant found for '{org}'.")

    cid = client["id"]
    if not client.get("is_demo"):
        _fail("Refusing to purge: client row is not flagged is_demo.")

    for table in ("creative_requests", "client_reports", "invoices", "contracts"):
        rows = query_table(table, select="id", filters={"client_id": cid}) or []
        for row in rows:
            delete_row(table, row["id"])
        print(f"  deleted {len(rows)} row(s) from {table}")

    delete_row("clients", cid)
    print(f"Purged demo tenant for '{org}'.")
    print("Note: the Supabase Auth user was not deleted — remove it in the dashboard.")


def seed(org: str, email: str, days: int):
    existing = _find_demo_client(org)
    if existing:
        print(f"Demo tenant for '{org}' already exists (client_id={existing['id']}).")
        print("Use --show to inspect, --revoke to expire, or --purge to remove and re-seed.")
        return

    expires_at = datetime.now(timezone.utc) + timedelta(days=days)

    client = insert_row("clients", {
        "business_name": DEMO_BUSINESS_NAME,
        "contact_name": DEMO_CONTACT_NAME,
        "contact_email": email,
        "client_type": "advertiser",
        "industry": "Sample",
        "city": "Oxford",
        "status": "active",
        "is_demo": True,
        "partner_org": org,
        "portal_access_expires_at": expires_at.isoformat(),
        "notes": f"Synthetic sandbox tenant for {org} evaluation. Not a real client.",
    })
    if not client:
        _fail("Could not create the demo client row. Is migration 024 applied?")

    cid = client["id"]
    print(f"Created demo client {cid}")

    contract = _seed_contract(cid)
    if not contract:
        _fail("Could not create the demo contract.")
    print("  seeded 1 contract")
    print(f"  seeded {_seed_invoices(cid, contract['id'])} invoices")
    print(f"  seeded {_seed_reports(cid)} reports")
    print(f"  seeded {_seed_creative(cid)} creative requests")

    password = _generate_password()
    user = sign_up(
        email=email,
        password=password,
        full_name=f"{org} Evaluation",
        role="partner",
        company_name=org,
    )
    if not user:
        print("\nWARNING: the client and its demo data were created, but the")
        print("Supabase Auth user was not. Create it manually with role='partner'")
        print(f"and set clients.portal_user_id = <user id> for client {cid}.")
        return

    update_row("clients", cid, {"portal_user_id": user["user_id"]})

    print("\n" + "=" * 68)
    print(f"  Evaluation account for {org}")
    print("=" * 68)
    print(f"  Email    : {email}")
    print(f"  Password : {password}")
    print(f"  Expires  : {expires_at.date().isoformat()} ({days} days)")
    print(f"  Role     : partner (read-only)")
    print("=" * 68)
    print("  Deliver these out of band, and only after the evaluation")
    print("  agreement is signed. The password is not stored anywhere.")
    print("=" * 68)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", required=True,
                        help="Partner organization name, e.g. 'NTV360'")
    parser.add_argument("--email", help="Login email for the evaluation account")
    parser.add_argument("--days", type=int, default=30,
                        help="Days until access expires (default: 30)")
    parser.add_argument("--show", action="store_true", help="Show the demo tenant")
    parser.add_argument("--revoke", action="store_true", help="Expire access now")
    parser.add_argument("--purge", action="store_true",
                        help="Delete the demo tenant and its synthetic data")
    args = parser.parse_args()

    if args.show:
        show(args.org)
    elif args.revoke:
        revoke(args.org)
    elif args.purge:
        purge(args.org)
    else:
        if not args.email:
            _fail("--email is required when seeding.")
        seed(args.org, args.email.strip().lower(), args.days)


if __name__ == "__main__":
    main()
