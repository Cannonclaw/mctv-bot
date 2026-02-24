#!/usr/bin/env python3
"""Service layer integration test for MCTV Client Portal.

Tests portal_service, contract_service, and invoice_service.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.portal_service import (
    create_client, get_client, get_all_clients, get_admin_summary,
    get_client_dashboard, log_activity, delete_client
)
from services.contract_service import (
    create_contract, get_contracts_for_client, get_contract_summary
)
from services.invoice_service import (
    create_invoice, get_invoices_for_client, get_invoice_summary, get_ar_aging
)
from services.supabase_client import delete_row, query_table

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
    print("  MCTV SERVICE LAYER TEST")
    print("=" * 60)

    # ── portal_service ────────────────────────────────────────────
    print()
    print("--- portal_service ---")
    client = create_client("SVC_TEST_Bakery", "Jane Doe", "jane@test.com",
                           city="Starkville", industry="Food")
    if client and client.get("id"):
        cid = client["id"]
        ok(f"create_client: {cid[:8]}...")
    else:
        fail("create_client returned None")
        return 1

    fetched = get_client(cid)
    if fetched and fetched.get("business_name") == "SVC_TEST_Bakery":
        ok("get_client by ID")
    else:
        fail("get_client by ID")

    all_c = get_all_clients()
    found = any(c.get("id") == cid for c in all_c)
    if found:
        ok(f"get_all_clients: {len(all_c)} total, test client found")
    else:
        fail("get_all_clients: test client not found")

    summary = get_admin_summary()
    if "total_clients" in summary:
        ok(f"get_admin_summary: {summary['total_clients']} clients, MRR=${summary['monthly_recurring_revenue']}")
    else:
        fail("get_admin_summary missing keys")

    dashboard = get_client_dashboard(cid)
    if "client" in dashboard and dashboard["client"]:
        ok("get_client_dashboard")
    else:
        fail("get_client_dashboard returned empty")

    log_activity(cid, "test", entity_type="client")
    ok("log_activity (no exception)")

    # ── contract_service ──────────────────────────────────────────
    print()
    print("--- contract_service ---")
    contract = None
    try:
        contract = create_contract(
            client_id=cid,
            contract_type="advertising",
            title="SVC Test Contract",
            tier_name="Starter",
            screen_count=10,
            monthly_rate=200.00,
            start_date="2026-04-01",
            end_date="2026-09-30",
            term_months=6,
            markets=["Starkville"],
            created_by="svc_test",
        )
        if contract and contract.get("id"):
            ok(f"create_contract: {contract['id'][:8]}...")
        else:
            fail("create_contract returned None")
    except Exception as e:
        fail(f"create_contract exception: {e}")

    try:
        contracts = get_contracts_for_client(cid)
        if len(contracts) >= 1:
            ok(f"get_contracts_for_client: {len(contracts)} found")
        else:
            fail("get_contracts_for_client: 0 found")
    except Exception as e:
        fail(f"get_contracts_for_client: {e}")

    try:
        cs = get_contract_summary()
        if "total" in cs:
            ok(f"get_contract_summary: {cs['total']} contracts total")
        else:
            fail("get_contract_summary missing 'total' key")
    except Exception as e:
        fail(f"get_contract_summary: {e}")

    # ── invoice_service ───────────────────────────────────────────
    print()
    print("--- invoice_service ---")
    invoice = None
    try:
        contract_id = contract["id"] if contract else None
        invoice = create_invoice(
            client_id=cid,
            contract_id=contract_id,
            amount=200.00,
            description="Test invoice for April",
            period_start="2026-04-01",
            period_end="2026-04-30",
        )
        if invoice and invoice.get("invoice_number"):
            ok(f"create_invoice: {invoice['invoice_number']}")
        else:
            fail("create_invoice returned None or no invoice_number")
    except Exception as e:
        fail(f"create_invoice: {e}")

    try:
        invs = get_invoices_for_client(cid)
        if len(invs) >= 1:
            ok(f"get_invoices_for_client: {len(invs)} found")
        else:
            fail("get_invoices_for_client: 0 found")
    except Exception as e:
        fail(f"get_invoices_for_client: {e}")

    try:
        isumm = get_invoice_summary()
        if "total" in isumm:
            ok(f"get_invoice_summary: {isumm['total']} invoices total")
        else:
            fail("get_invoice_summary missing 'total' key")
    except Exception as e:
        fail(f"get_invoice_summary: {e}")

    try:
        aging = get_ar_aging()
        buckets = aging.get("buckets", [])
        ok(f"get_ar_aging: {len(buckets)} buckets, total=${aging.get('total_outstanding', 0)}")
    except Exception as e:
        fail(f"get_ar_aging: {e}")

    # ── Cleanup ───────────────────────────────────────────────────
    print()
    print("--- Cleanup ---")
    acts = query_table("activity_log", filters={"client_id": cid})
    for a in acts:
        delete_row("activity_log", a["id"])

    if invoice and invoice.get("id"):
        delete_row("invoices", invoice["id"])

    if contract and contract.get("id"):
        delete_row("contracts", contract["id"])

    delete_client(cid)
    remaining = query_table("clients", filters={"business_name": "SVC_TEST_Bakery"})
    if len(remaining) == 0:
        ok("All test data cleaned up")
    else:
        fail(f"{len(remaining)} test records remain")

    # ── Results ───────────────────────────────────────────────────
    print()
    print("=" * 60)
    total = passed + failed
    if failed == 0:
        print(f"  ALL {total} SERVICE TESTS PASSED!")
    else:
        print(f"  {passed}/{total} passed, {failed} FAILED")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
