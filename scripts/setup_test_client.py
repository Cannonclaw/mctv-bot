#!/usr/bin/env python3
"""Set up a complete test client in the MCTV Portal for end-to-end testing.

Creates:
  1. A test client record (advertiser) in the clients table
  2. A Supabase Auth user (portal login account) linked to the client
  3. A sample contract (status: "sent" — ready for e-signature testing)
  4. A second contract (status: "active" — shows as already signed)
  5. Two invoices (one pending, one paid — tests both states)
  6. A creative request (status: "in_progress" — tests the creative workflow)
  7. A traction report (tests report viewing/download)
  8. Activity log entries (tests the audit trail / recent activity feed)

Usage:
    cd Desktop/MCTV-Bot
    python scripts/setup_test_client.py

Login credentials (after running):
    Email:    test@mctvofms.com
    Password: MCTVtest2026!
    Role:     advertiser
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path so we can import services
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from services.supabase_client import (
    sign_up, insert_row, update_row, query_table
)

# ── Test Client Configuration ────────────────────────────────────────────────

TEST_EMAIL = "test@mctvofms.com"
TEST_PASSWORD = "MCTVtest2026!"
TEST_FULL_NAME = "Jordan Mitchell"
TEST_COMPANY = "Oxford Coffee Co."
TEST_PHONE = "(662) 555-0142"
TEST_INDUSTRY = "Bar/Restaurant"
TEST_CITY = "Oxford"
TEST_CLIENT_TYPE = "advertiser"
TEST_ASSIGNED_REP = "T. Creed Cannon"


def main():
    print("=" * 60)
    print("  MCTV Portal — Test Client Setup")
    print("=" * 60)
    print()

    # ── Step 1: Check for existing test client ────────────────────────────
    print("[1/8] Checking for existing test client...")
    existing = query_table("clients", filters={"contact_email": TEST_EMAIL})
    if existing:
        print(f"  >> Test client already exists (ID: {existing[0]['id']})")
        print(f"  >> Business: {existing[0].get('business_name')}")
        print(f"  >> To re-create, delete the existing record first.")
        client_id = existing[0]["id"]
        portal_user_id = existing[0].get("portal_user_id", "")
    else:
        # ── Step 2: Create client record ──────────────────────────────────
        print("[2/8] Creating test client record...")
        client = insert_row("clients", {
            "business_name": TEST_COMPANY,
            "contact_name": TEST_FULL_NAME,
            "contact_email": TEST_EMAIL,
            "contact_phone": TEST_PHONE,
            "industry": TEST_INDUSTRY,
            "city": TEST_CITY,
            "client_type": TEST_CLIENT_TYPE,
            "status": "onboarding",
            "assigned_rep": TEST_ASSIGNED_REP,
            "notes": "Test client for portal QA. Safe to delete after testing.",
        })
        if not client:
            print("  !! FAILED to create client record. Check Supabase connection.")
            sys.exit(1)
        client_id = client["id"]
        print(f"  >> Client created: {client_id}")

        # ── Step 3: Create Supabase Auth user ─────────────────────────────
        print("[3/8] Creating portal auth user...")
        user = sign_up(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_FULL_NAME,
            role=TEST_CLIENT_TYPE,
            company_name=TEST_COMPANY,
        )
        if not user:
            print("  !! FAILED to create auth user. May already exist in Supabase Auth.")
            print("  >> Attempting to continue anyway (user may already be linked)...")
            portal_user_id = ""
        else:
            portal_user_id = user["user_id"]
            print(f"  >> Auth user created: {portal_user_id}")

            # Link auth user to client
            update_row("clients", client_id, {"portal_user_id": portal_user_id})
            print(f"  >> Linked portal user to client record")

    # ── Step 4: Create sample contracts ───────────────────────────────────
    print("[4/8] Creating sample contracts...")

    today = datetime.now().date()
    six_months_later = today + timedelta(days=180)
    three_months_ago = today - timedelta(days=90)
    three_months_later = three_months_ago + timedelta(days=180)

    # Contract 1: Ready for e-signature (status: "sent")
    contract1 = insert_row("contracts", {
        "client_id": client_id,
        "contract_type": "advertising",
        "title": f"{TEST_COMPANY} — 20-Screen Elite Advertising Agreement",
        "tier_name": "Elite 20",
        "screen_count": 20,
        "monthly_rate": 500.00,
        "start_date": today.isoformat(),
        "end_date": six_months_later.isoformat(),
        "term_months": 6,
        "auto_renew": True,
        "markets": ["Oxford"],
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
        "created_by": TEST_ASSIGNED_REP,
    })
    c1_id = contract1["id"] if contract1 else None
    print(f"  >> Contract 1 (awaiting signature): {c1_id or 'FAILED'}")

    # Contract 2: Already active (signed 3 months ago)
    contract2 = insert_row("contracts", {
        "client_id": client_id,
        "contract_type": "advertising",
        "title": f"{TEST_COMPANY} — 10-Screen Starter Agreement",
        "tier_name": "Elite 10",
        "screen_count": 10,
        "monthly_rate": 350.00,
        "start_date": three_months_ago.isoformat(),
        "end_date": three_months_later.isoformat(),
        "term_months": 6,
        "auto_renew": False,
        "markets": ["Oxford"],
        "status": "active",
        "signed_by": TEST_FULL_NAME,
        "signed_at": three_months_ago.isoformat(),
        "created_by": TEST_ASSIGNED_REP,
    })
    c2_id = contract2["id"] if contract2 else None
    print(f"  >> Contract 2 (active/signed): {c2_id or 'FAILED'}")

    # ── Step 5: Create sample invoices ────────────────────────────────────
    print("[5/8] Creating sample invoices...")

    # Invoice 1: Pending payment (current month)
    inv1 = insert_row("invoices", {
        "client_id": client_id,
        "contract_id": c2_id,
        "invoice_number": "MCTV-TEST-001",
        "amount": 350.00,
        "description": "Elite 10 Advertising — March 2026",
        "period_start": today.replace(day=1).isoformat(),
        "period_end": (today.replace(day=1) + timedelta(days=30)).isoformat(),
        "issued_date": (today - timedelta(days=5)).isoformat(),
        "due_date": (today + timedelta(days=10)).isoformat(),
        "status": "sent",
    })
    print(f"  >> Invoice 1 (pending): {inv1['id'] if inv1 else 'FAILED'}")

    # Invoice 2: Already paid (last month)
    last_month = today - timedelta(days=30)
    inv2 = insert_row("invoices", {
        "client_id": client_id,
        "contract_id": c2_id,
        "invoice_number": "MCTV-TEST-002",
        "amount": 350.00,
        "description": "Elite 10 Advertising — February 2026",
        "period_start": last_month.replace(day=1).isoformat(),
        "period_end": (last_month.replace(day=1) + timedelta(days=27)).isoformat(),
        "issued_date": (last_month - timedelta(days=5)).isoformat(),
        "due_date": (last_month + timedelta(days=10)).isoformat(),
        "paid_date": (last_month + timedelta(days=8)).isoformat(),
        "status": "paid",
        "notes": "Paid via check #1042",
    })
    print(f"  >> Invoice 2 (paid): {inv2['id'] if inv2 else 'FAILED'}")

    # Invoice 3: Overdue (older)
    two_months_ago = today - timedelta(days=60)
    inv3 = insert_row("invoices", {
        "client_id": client_id,
        "contract_id": c2_id,
        "invoice_number": "MCTV-TEST-003",
        "amount": 350.00,
        "description": "Elite 10 Advertising — January 2026",
        "period_start": two_months_ago.replace(day=1).isoformat(),
        "period_end": (two_months_ago.replace(day=1) + timedelta(days=30)).isoformat(),
        "issued_date": (two_months_ago - timedelta(days=5)).isoformat(),
        "due_date": (two_months_ago + timedelta(days=10)).isoformat(),
        "status": "overdue",
    })
    print(f"  >> Invoice 3 (overdue): {inv3['id'] if inv3 else 'FAILED'}")

    # ── Step 6: Create sample creative request ────────────────────────────
    print("[6/8] Creating sample creative request...")

    cr1 = insert_row("creative_requests", {
        "client_id": client_id,
        "request_type": "new_ad",
        "title": "Grand Opening Spring Promo — 15s Video Ad",
        "description": (
            "We're launching our spring menu and want a 15-second video ad "
            "highlighting our new cold brew lineup. Please use our logo and the "
            "attached menu photos. Gold/brown color scheme preferred."
        ),
        "priority": "normal",
        "status": "in_progress",
        "assigned_to": "Swayze Cannon",
        "internal_notes": "Client sent logo via email. Need to pull menu photos from intake.",
    })
    cr1_id = cr1["id"] if cr1 else None
    print(f"  >> Creative request: {cr1_id or 'FAILED'}")

    # Second creative request (completed)
    cr2 = insert_row("creative_requests", {
        "client_id": client_id,
        "request_type": "logo_upload",
        "title": "Logo File Upload — PNG + SVG",
        "description": "Uploading our official logo files for use in ad creatives.",
        "priority": "low",
        "status": "approved",
        "assigned_to": "Mary Michael Cannon",
        "completed_at": (today - timedelta(days=14)).isoformat(),
    })
    print(f"  >> Creative request 2 (completed): {cr2['id'] if cr2 else 'FAILED'}")

    # ── Step 7: Create sample traction report ─────────────────────────────
    print("[7/8] Creating sample traction report...")

    report = insert_row("client_reports", {
        "client_id": client_id,
        "report_type": "traction",
        "title": "February 2026 Traction Report — Oxford Coffee Co.",
        "campaign_period": "February 1 – February 28, 2026",
        "total_plays": 8640,
        "total_impressions": 43200,
        "total_venues": 10,
        "highlights": json.dumps([
            "8,640 total ad plays across 10 Oxford venues",
            "43,200 estimated impressions (5x viewer multiplier)",
            "Peak performance at The Library Sports Bar (1,200 plays)",
            "CPM of $8.10 — 72% below industry average for indoor digital",
            "Month-over-month play count increased 12%",
        ]),
    })
    print(f"  >> Traction report: {report['id'] if report else 'FAILED'}")

    # ── Step 8: Create activity log entries ───────────────────────────────
    print("[8/8] Creating activity log entries...")

    activities = [
        {
            "client_id": client_id,
            "user_id": portal_user_id or None,
            "action": "client_created",
            "entity_type": "client",
            "entity_id": client_id,
            "details": json.dumps({"source": "test_setup", "rep": TEST_ASSIGNED_REP}),
        },
        {
            "client_id": client_id,
            "action": "contract_sent",
            "entity_type": "contract",
            "entity_id": c1_id or "",
            "details": json.dumps({"title": "20-Screen Elite Agreement", "monthly_rate": 500}),
        },
        {
            "client_id": client_id,
            "action": "contract_signed",
            "entity_type": "contract",
            "entity_id": c2_id or "",
            "details": json.dumps({"title": "10-Screen Starter Agreement", "signed_by": TEST_FULL_NAME}),
        },
        {
            "client_id": client_id,
            "action": "invoice_sent",
            "entity_type": "invoice",
            "entity_id": inv1["id"] if inv1 else "",
            "details": json.dumps({"amount": 350, "period": "March 2026"}),
        },
        {
            "client_id": client_id,
            "action": "creative_submitted",
            "entity_type": "creative_request",
            "entity_id": cr1_id or "",
            "details": json.dumps({"title": "Grand Opening Spring Promo"}),
        },
        {
            "client_id": client_id,
            "action": "report_generated",
            "entity_type": "report",
            "entity_id": report["id"] if report else "",
            "details": json.dumps({"period": "February 2026", "plays": 8640}),
        },
    ]

    for act in activities:
        # Remove None user_id to avoid FK issues
        if not act.get("user_id"):
            act.pop("user_id", None)
        result = insert_row("activity_log", act)
        status = "ok" if result else "FAILED"
        print(f"  >> {act['action']}: {status}")

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  TEST CLIENT SETUP COMPLETE")
    print("=" * 60)
    print()
    print(f"  Business:     {TEST_COMPANY}")
    print(f"  Contact:      {TEST_FULL_NAME}")
    print(f"  Client ID:    {client_id}")
    print(f"  Portal User:  {portal_user_id or '(not linked)'}")
    print()
    print("  Portal Login Credentials:")
    print(f"    Email:      {TEST_EMAIL}")
    print(f"    Password:   {TEST_PASSWORD}")
    print()
    print("  Test Data Created:")
    print(f"    Contracts:        2 (1 awaiting signature, 1 active)")
    print(f"    Invoices:         3 (1 pending, 1 paid, 1 overdue)")
    print(f"    Creative Reqs:    2 (1 in progress, 1 approved)")
    print(f"    Traction Reports: 1 (February 2026)")
    print(f"    Activity Log:     6 entries")
    print()
    print("  IMPORTANT: Make sure 'test@mctvofms.com' is in your")
    print("  PORTAL_ALLOWED_EMAILS in .env (or it defaults to team-only).")
    print()
    print("  To test, go to: https://bot.mctvofms.com")
    print("  Select 'Client Portal' and log in with the credentials above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
