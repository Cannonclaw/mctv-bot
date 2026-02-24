#!/usr/bin/env python3
"""End-to-end contract flow test for MCTV Client Portal.

Tests: create client → create contract → generate PDF → send → sign → activate → cleanup.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.portal_service import create_client, get_client, delete_client, log_activity
from services.contract_service import (
    create_contract, get_contract, get_contracts_for_client,
    generate_contract_document, send_contract, record_contract_view,
    sign_contract, activate_contract, cancel_contract,
    get_contract_download_url, get_contract_summary, delete_contract,
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
    print("  MCTV CONTRACT FLOW TEST")
    print("=" * 60)

    # ── Step 1: Create test client ──────────────────────────────
    print()
    print("--- Step 1: Create test client ---")
    client = create_client(
        "CONTRACT_TEST_Bakery", "Jane Test", "jane@test.com",
        city="Oxford", industry="Food"
    )
    if client and client.get("id"):
        cid = client["id"]
        ok(f"Client created: {cid[:8]}...")
    else:
        fail("Could not create test client")
        return 1

    # ── Step 2: Create contract ─────────────────────────────────
    print()
    print("--- Step 2: Create contract ---")
    contract = None
    try:
        contract = create_contract(
            client_id=cid,
            contract_type="advertising",
            title="Contract Flow Test - 6 Month Starter",
            tier_name="Starter",
            screen_count=10,
            monthly_rate=350.00,
            start_date="2026-04-01",
            end_date="2026-09-30",
            term_months=6,
            markets=["Oxford"],
            created_by="Creed",
        )
        if contract and contract.get("id"):
            contract_id = contract["id"]
            ok(f"Contract created: {contract_id[:8]}... (status: {contract.get('status')})")
        else:
            fail("create_contract returned None")
            contract_id = None
    except Exception as e:
        fail(f"create_contract exception: {e}")
        contract_id = None

    if not contract_id:
        print("  Skipping remaining tests (no contract)")
        _cleanup(cid, None, None)
        return 1

    # ── Step 3: Verify contract in DB ──────────────────────────
    print()
    print("--- Step 3: Verify contract in database ---")
    fetched = get_contract(contract_id)
    if fetched and fetched.get("title") == "Contract Flow Test - 6 Month Starter":
        ok("get_contract: title matches")
    else:
        fail("get_contract: title mismatch or None")

    if fetched and fetched.get("status") == "draft":
        ok("Initial status is 'draft'")
    else:
        fail(f"Expected status 'draft', got '{fetched.get('status') if fetched else 'None'}'")

    client_contracts = get_contracts_for_client(cid)
    if len(client_contracts) >= 1:
        ok(f"get_contracts_for_client: {len(client_contracts)} found")
    else:
        fail("get_contracts_for_client: 0 found")

    # ── Step 4: Generate contract PDF ──────────────────────────
    print()
    print("--- Step 4: Generate contract document ---")
    try:
        doc_result = generate_contract_document(contract_id)
        if doc_result and doc_result.get("document_url"):
            doc_url = doc_result["document_url"]
            ok(f"Document generated: {doc_url[:40]}...")

            # Check if the file actually exists locally
            if doc_url.startswith("output") or doc_url.startswith("C:") or doc_url.startswith("/"):
                local_path = Path(doc_url)
                if not local_path.is_absolute():
                    local_path = Path(__file__).parent.parent / doc_url
                if local_path.exists():
                    size_kb = local_path.stat().st_size / 1024
                    ok(f"Document exists locally: {size_kb:.1f} KB")
                else:
                    fail(f"Document path doesn't exist: {local_path}")
            else:
                ok(f"Document stored in Supabase Storage")
        else:
            fail("generate_contract_document returned None or no document_url")
    except Exception as e:
        fail(f"generate_contract_document exception: {e}")

    # ── Step 5: Send contract ──────────────────────────────────
    print()
    print("--- Step 5: Send contract ---")
    try:
        sent = send_contract(contract_id)
        if sent and sent.get("status") == "sent":
            ok("Contract status -> sent")
            if sent.get("sent_at"):
                ok(f"sent_at recorded: {sent['sent_at'][:19]}")
            else:
                fail("sent_at not recorded")
        else:
            fail(f"send_contract failed (status: {sent.get('status') if sent else 'None'})")
    except Exception as e:
        fail(f"send_contract exception: {e}")

    # ── Step 6: Record view ────────────────────────────────────
    print()
    print("--- Step 6: Record contract view ---")
    try:
        viewed = record_contract_view(contract_id)
        if viewed and viewed.get("status") == "viewed":
            ok("Contract status -> viewed")
            if viewed.get("viewed_at"):
                ok(f"viewed_at recorded: {viewed['viewed_at'][:19]}")
            else:
                fail("viewed_at not recorded")
        else:
            fail(f"record_contract_view failed (status: {viewed.get('status') if viewed else 'None'})")
    except Exception as e:
        fail(f"record_contract_view exception: {e}")

    # ── Step 7: Sign contract ──────────────────────────────────
    print()
    print("--- Step 7: Sign contract ---")
    try:
        signed = sign_contract(
            contract_id=contract_id,
            signed_by="Jane Test",
            ip_address="127.0.0.1",
            user_agent="ContractFlowTest/1.0",
            user_id="test-user",
        )
        if signed and signed.get("status") == "signed":
            ok("Contract status -> signed")
            if signed.get("signed_by") == "Jane Test":
                ok("signed_by recorded correctly")
            else:
                fail(f"signed_by mismatch: {signed.get('signed_by')}")
            if signed.get("signed_at"):
                ok(f"signed_at recorded: {signed['signed_at'][:19]}")
            else:
                fail("signed_at not recorded")
            if signed.get("signed_ip") == "127.0.0.1":
                ok("signed_ip recorded")
            else:
                fail(f"signed_ip mismatch: {signed.get('signed_ip')}")
        else:
            fail(f"sign_contract failed (status: {signed.get('status') if signed else 'None'})")
    except Exception as e:
        fail(f"sign_contract exception: {e}")

    # ── Step 8: Activate contract ──────────────────────────────
    print()
    print("--- Step 8: Activate contract ---")
    try:
        activated = activate_contract(contract_id)
        if activated and activated.get("status") == "active":
            ok("Contract status -> active")
        else:
            fail(f"activate_contract failed (status: {activated.get('status') if activated else 'None'})")
    except Exception as e:
        fail(f"activate_contract exception: {e}")

    # ── Step 9: Download URL ───────────────────────────────────
    print()
    print("--- Step 9: Test download URL ---")
    try:
        url = get_contract_download_url(contract_id)
        if url:
            ok(f"Download URL: {url[:50]}...")
        else:
            fail("get_contract_download_url returned None")
    except Exception as e:
        fail(f"get_contract_download_url exception: {e}")

    # ── Step 10: Contract summary ──────────────────────────────
    print()
    print("--- Step 10: Contract summary ---")
    try:
        summary = get_contract_summary()
        if "total" in summary:
            ok(f"Summary: {summary['total']} total, MRR=${summary.get('active_mrr', 0):,.2f}")
        else:
            fail("get_contract_summary missing 'total'")
    except Exception as e:
        fail(f"get_contract_summary exception: {e}")

    # ── Cleanup ────────────────────────────────────────────────
    print()
    print("--- Cleanup ---")
    _cleanup(cid, contract_id, contract)

    # ── Results ────────────────────────────────────────────────
    print()
    print("=" * 60)
    total = passed + failed
    if failed == 0:
        print(f"  ALL {total} CONTRACT FLOW TESTS PASSED!")
    else:
        print(f"  {passed}/{total} passed, {failed} FAILED")
    print("=" * 60)

    return 0 if failed == 0 else 1


def _cleanup(client_id, contract_id, contract):
    """Clean up test data."""
    # Clean activity log entries
    acts = query_table("activity_log", filters={"client_id": client_id})
    for a in acts:
        delete_row("activity_log", a["id"])

    # Delete contract
    if contract_id:
        delete_row("contracts", contract_id)

    # Delete client
    delete_client(client_id)

    remaining = query_table("clients", filters={"business_name": "CONTRACT_TEST_Bakery"})
    if len(remaining) == 0:
        ok("All test data cleaned up")
    else:
        fail(f"{len(remaining)} test records remain")

    # Clean up local contract files
    output_dir = Path(__file__).parent.parent / "output" / "contracts"
    for f in output_dir.glob("MCTV_Contract_CONTRACT_TEST*"):
        try:
            f.unlink()
            print(f"  Cleaned up: {f.name}")
        except PermissionError:
            print(f"  (Skipped locked file: {f.name} - OneDrive sync)")


if __name__ == "__main__":
    sys.exit(main())
