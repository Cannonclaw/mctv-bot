#!/usr/bin/env python3
# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Integration test for MCTV Client Portal.

Tests the full CRUD lifecycle: client → contract → invoice → creative → report → activity.
Creates test data, verifies operations, then cleans up.

Usage:
    python scripts/integration_test.py
"""

import sys
import os
import json

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Load .env
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

# Force UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.supabase_client import (
    query_table, insert_row, update_row, delete_row, is_configured, sign_in
)

passed = 0
failed = 0


def ok(msg):
    global passed
    passed += 1
    print(f"  [PASS] {msg}")


def fail(msg):
    global failed
    failed += 1
    print(f"  [FAIL] {msg}")


def main():
    global passed, failed

    print("=" * 60)
    print("  MCTV CLIENT PORTAL - INTEGRATION TEST")
    print("=" * 60)

    # ── Step 0: Configuration ─────────────────────────────────────
    print()
    print("--- Step 0: Verify configuration ---")
    if is_configured():
        ok("Supabase is configured")
    else:
        fail("Supabase is NOT configured")
        print("  Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        sys.exit(1)

    # ── Step 1: Test sign_in ──────────────────────────────────────
    print()
    print("--- Step 1: Test authentication (sign_in) ---")
    result = sign_in("creed@mctvofms.com", "MCTV2026!")
    if result and result.get("user_id"):
        ok(f"Sign in worked: {result.get('full_name')} ({result.get('role')})")
        ok(f"Access token received: {result.get('access_token', '')[:20]}...")
    else:
        fail("Sign in failed for creed@mctvofms.com")

    # ── Step 2: Create test client ────────────────────────────────
    print()
    print("--- Step 2: Create test client ---")
    test_client = insert_row("clients", {
        "business_name": "INTEGRATION_TEST_Coffee_Shop",
        "contact_name": "Test User",
        "contact_email": "test@example.com",
        "contact_phone": "662-555-0100",
        "industry": "Food & Beverage",
        "city": "Oxford",
        "client_type": "advertiser",
        "status": "active",
        "assigned_rep": "T. Creed Cannon",
        "notes": "Integration test - safe to delete",
    })
    if test_client and test_client.get("id"):
        client_id = test_client["id"]
        ok(f"Client created: {client_id}")
    else:
        fail("Could not create test client")
        sys.exit(1)

    # ── Step 3: Create contract ───────────────────────────────────
    print()
    print("--- Step 3: Create test contract ---")
    test_contract = insert_row("contracts", {
        "client_id": client_id,
        "contract_type": "advertising",
        "title": "Integration Test - 6 Month Ad Package",
        "tier_name": "Starter",
        "screen_count": 10,
        "monthly_rate": 200.00,
        "start_date": "2026-03-01",
        "end_date": "2026-08-31",
        "term_months": 6,
        "markets": ["Oxford"],
        "status": "draft",
        "created_by": "integration_test",
    })
    contract_id = None
    if test_contract and test_contract.get("id"):
        contract_id = test_contract["id"]
        ok(f"Contract created: {contract_id}")
    else:
        fail("Could not create contract")

    # ── Step 4: Create invoice ────────────────────────────────────
    print()
    print("--- Step 4: Create test invoice ---")
    test_invoice = insert_row("invoices", {
        "client_id": client_id,
        "contract_id": contract_id,
        "invoice_number": "MCTV-202603-TEST",
        "amount": 200.00,
        "description": "March 2026 - Starter Package (10 screens)",
        "period_start": "2026-03-01",
        "period_end": "2026-03-31",
        "issued_date": "2026-03-01",
        "due_date": "2026-03-15",
        "status": "draft",
    })
    invoice_id = None
    if test_invoice and test_invoice.get("id"):
        invoice_id = test_invoice["id"]
        ok(f"Invoice created: {invoice_id} (MCTV-202603-TEST)")
    else:
        fail("Could not create invoice")

    # ── Step 5: Create creative request ───────────────────────────
    print()
    print("--- Step 5: Create test creative request ---")
    test_creative = insert_row("creative_requests", {
        "client_id": client_id,
        "request_type": "new_ad",
        "title": "Spring coffee promo ad",
        "description": "Need a 15-second ad for our spring latte special.",
        "status": "pending",
        "priority": "normal",
    })
    creative_id = None
    if test_creative and test_creative.get("id"):
        creative_id = test_creative["id"]
        ok(f"Creative request created: {creative_id}")
    else:
        fail("Could not create creative request")

    # ── Step 6: Create client report ──────────────────────────────
    print()
    print("--- Step 6: Create test report record ---")
    test_report = insert_row("client_reports", {
        "client_id": client_id,
        "report_type": "traction",
        "title": "March 2026 Traction Report",
        "campaign_period": "March 1-31, 2026",
        "total_plays": 8500,
        "total_impressions": 125000,
        "total_venues": 10,
        "highlights": "Strong performance across all Oxford locations.",
    })
    report_id = None
    if test_report and test_report.get("id"):
        report_id = test_report["id"]
        ok(f"Report created: {report_id}")
    else:
        fail("Could not create report")

    # ── Step 7: Create activity log ───────────────────────────────
    print()
    print("--- Step 7: Create activity log entry ---")
    test_activity = insert_row("activity_log", {
        "client_id": client_id,
        "action": "integration_test",
        "entity_type": "client",
        "entity_id": client_id,
        "details": json.dumps({"test": True}),
    })
    activity_id = None
    if test_activity and test_activity.get("id"):
        activity_id = test_activity["id"]
        ok("Activity logged")
    else:
        fail("Could not log activity")

    # ── Step 8: Test updates ──────────────────────────────────────
    print()
    print("--- Step 8: Test updates ---")

    if contract_id:
        updated = update_row("contracts", contract_id, {
            "status": "sent",
            "sent_at": "2026-02-24T12:00:00Z",
        })
        if updated and updated.get("status") == "sent":
            ok("Contract status -> sent")
        else:
            fail("Could not update contract status")

        # Simulate signing
        signed = update_row("contracts", contract_id, {
            "status": "signed",
            "signed_by": "Test User",
            "signed_at": "2026-02-24T14:00:00Z",
            "signed_ip": "127.0.0.1",
            "signed_user_agent": "IntegrationTest/1.0",
        })
        if signed and signed.get("status") == "signed":
            ok("Contract signed (name + timestamp + IP recorded)")
        else:
            fail("Could not sign contract")

    if invoice_id:
        updated = update_row("invoices", invoice_id, {"status": "sent"})
        if updated and updated.get("status") == "sent":
            ok("Invoice status -> sent")
        else:
            fail("Could not update invoice status")

        # Mark paid
        paid = update_row("invoices", invoice_id, {
            "status": "paid",
            "paid_date": "2026-03-10",
        })
        if paid and paid.get("status") == "paid":
            ok("Invoice marked as paid")
        else:
            fail("Could not mark invoice paid")

    if creative_id:
        updated = update_row("creative_requests", creative_id, {
            "status": "in_progress",
            "assigned_to": "T. Creed Cannon",
        })
        if updated and updated.get("status") == "in_progress":
            ok("Creative request assigned and in progress")
        else:
            fail("Could not update creative request")

    # ── Step 9: Test queries ──────────────────────────────────────
    print()
    print("--- Step 9: Test queries ---")

    clients = query_table("clients", filters={"id": client_id})
    if len(clients) == 1:
        ok(f"Query client by ID: found {clients[0].get('business_name')}")
    else:
        fail(f"Query client by ID: expected 1, got {len(clients)}")

    contracts = query_table("contracts", filters={"client_id": client_id})
    if len(contracts) >= 1:
        ok(f"Query contracts by client: {len(contracts)} found")
    else:
        fail("Query contracts by client: 0 found")

    invoices = query_table("invoices", filters={"client_id": client_id})
    if len(invoices) >= 1:
        ok(f"Query invoices by client: {len(invoices)} found")
    else:
        fail("Query invoices by client: 0 found")

    creatives = query_table("creative_requests", filters={"client_id": client_id})
    if len(creatives) >= 1:
        ok(f"Query creative requests by client: {len(creatives)} found")
    else:
        fail("Query creative requests by client: 0 found")

    reports = query_table("client_reports", filters={"client_id": client_id})
    if len(reports) >= 1:
        ok(f"Query reports by client: {len(reports)} found")
    else:
        fail("Query reports by client: 0 found")

    # Test ordering
    ordered = query_table("contracts", order="-created_at", limit=5)
    if ordered is not None:
        ok(f"Query with ordering + limit: {len(ordered)} results")
    else:
        fail("Query with ordering failed")

    # Test profiles table
    profiles = query_table("profiles", select="email,full_name,role")
    if len(profiles) >= 3:
        ok(f"Profiles table: {len(profiles)} profiles found")
        for p in profiles:
            print(f"       - {p.get('full_name')} ({p.get('email')}) [{p.get('role')}]")
    else:
        fail(f"Profiles table: expected 3+, got {len(profiles)}")

    # ── Step 10: Cleanup ──────────────────────────────────────────
    print()
    print("--- Step 10: Cleanup test data ---")
    cleanup_items = [
        ("activity_log", activity_id),
        ("client_reports", report_id),
        ("creative_requests", creative_id),
        ("invoices", invoice_id),
        ("contracts", contract_id),
        ("clients", client_id),
    ]
    for table, row_id in cleanup_items:
        if row_id:
            success = delete_row(table, row_id)
            if success:
                ok(f"Deleted {table} {row_id[:8]}...")
            else:
                fail(f"Could not delete {table} {row_id[:8]}...")

    # Verify cleanup
    remaining = query_table("clients", filters={"business_name": "INTEGRATION_TEST_Coffee_Shop"})
    if len(remaining) == 0:
        ok("All test data cleaned up")
    else:
        fail(f"{len(remaining)} test client(s) still exist")

    # ── Results ───────────────────────────────────────────────────
    print()
    print("=" * 60)
    total = passed + failed
    if failed == 0:
        print(f"  ALL {total} TESTS PASSED!")
    else:
        print(f"  {passed}/{total} passed, {failed} FAILED")
    print("=" * 60)
    print()

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
