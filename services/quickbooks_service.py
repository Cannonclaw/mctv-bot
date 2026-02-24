"""QuickBooks Online API integration service.

Handles OAuth 2.0 token management, customer sync, invoice sync,
and payment tracking via QuickBooks REST API.

Uses raw urllib (no QB SDK) to match the project's REST-first pattern.
Token storage in Supabase for persistence across deploys.
"""

import os
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import hashlib
import hmac
import base64
from datetime import datetime, date, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)


# ── Configuration ────────────────────────────────────────────────────────────

QB_CLIENT_ID = os.environ.get("QB_CLIENT_ID", "")
QB_CLIENT_SECRET = os.environ.get("QB_CLIENT_SECRET", "")
QB_ENVIRONMENT = os.environ.get("QB_ENVIRONMENT", "sandbox")
QB_WEBHOOK_VERIFIER = os.environ.get("QB_WEBHOOK_VERIFIER", "")

# Redirect URI — Intuit sends the user back here after OAuth authorization.
# This MUST match what's registered in the Intuit Developer Portal exactly.
# For local dev:  http://localhost:8501/Settings
# For production: https://mctv-bot.onrender.com/Settings
QB_REDIRECT_URI = os.environ.get("QB_REDIRECT_URI", "http://localhost:8501/Settings")

# API base URLs
QB_AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
QB_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QB_REVOKE_URL = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"

QB_API_BASE = (
    "https://sandbox-quickbooks.api.intuit.com"
    if QB_ENVIRONMENT == "sandbox"
    else "https://quickbooks.api.intuit.com"
)

# Token file for local persistence (Supabase used as primary)
TOKEN_FILE = Path(__file__).parent.parent / "config" / "qb_tokens.json"


# ── Token Management ─────────────────────────────────────────────────────────

def _save_tokens(tokens: dict):
    """Save OAuth tokens to local file and optionally Supabase."""
    tokens["saved_at"] = datetime.now().isoformat()

    # Local file backup
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

    # Also save to Supabase for cross-deploy persistence
    try:
        from services.supabase_client import query_table, insert_row, update_row
        existing = query_table("app_settings", filters={"key": "qb_tokens"})
        data = {"key": "qb_tokens", "value": json.dumps(tokens)}
        if existing:
            update_row("app_settings", existing[0]["id"], data)
        else:
            insert_row("app_settings", data)
    except Exception as e:
        print(f"[quickbooks] Could not save tokens to Supabase: {e}")


def _load_tokens() -> dict | None:
    """Load OAuth tokens (try local file first, then Supabase).

    Local file is checked first for speed; Supabase is tried as backup
    for cross-deploy persistence (e.g., Render redeploy loses local files).
    """
    # Try local file first (fast, always available)
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, "r") as f:
                tokens = json.load(f)
            if tokens.get("access_token"):
                return tokens
        except Exception:
            pass

    # Try Supabase (for production deploys where local file may not persist)
    try:
        from services.supabase_client import query_table
        results = query_table("app_settings", filters={"key": "qb_tokens"})
        if results:
            tokens = json.loads(results[0].get("value", "{}"))
            if tokens.get("access_token"):
                # Sync back to local file for next time
                try:
                    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
                    with open(TOKEN_FILE, "w") as f:
                        json.dump(tokens, f, indent=2)
                except Exception:
                    pass
                return tokens
    except Exception:
        pass

    return None


def is_connected() -> bool:
    """Check if QuickBooks is connected (has valid tokens)."""
    tokens = _load_tokens()
    if not tokens:
        return False
    return bool(tokens.get("access_token")) and bool(tokens.get("realm_id"))


def get_realm_id() -> str:
    """Get the QuickBooks company (realm) ID."""
    tokens = _load_tokens()
    return tokens.get("realm_id", "") if tokens else ""


# ── OAuth 2.0 Flow ──────────────────────────────────────────────────────────

def get_auth_url(state: str = "") -> str:
    """Generate the OAuth authorization URL for QuickBooks connect.

    Args:
        state: Random state string for CSRF protection

    Returns:
        URL to redirect user to for QuickBooks authorization.
    """
    params = {
        "client_id": QB_CLIENT_ID,
        "redirect_uri": QB_REDIRECT_URI,
        "response_type": "code",
        "scope": "com.intuit.quickbooks.accounting",
        "state": state or str(int(time.time())),
    }
    return f"{QB_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code(auth_code: str, realm_id: str) -> dict | None:
    """Exchange authorization code for access + refresh tokens.

    Args:
        auth_code: Code from OAuth callback
        realm_id: QuickBooks company ID from callback

    Returns:
        Token dict or None on failure.
    """
    auth_header = base64.b64encode(
        f"{QB_CLIENT_ID}:{QB_CLIENT_SECRET}".encode()
    ).decode()

    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": QB_REDIRECT_URI,
    }).encode("utf-8")

    req = urllib.request.Request(
        QB_TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        tokens = {
            "access_token": result.get("access_token", ""),
            "refresh_token": result.get("refresh_token", ""),
            "realm_id": realm_id,
            "token_type": result.get("token_type", "bearer"),
            "expires_in": result.get("expires_in", 3600),
            "x_refresh_token_expires_in": result.get("x_refresh_token_expires_in", 8726400),
            "obtained_at": datetime.now().isoformat(),
        }

        _save_tokens(tokens)
        print(f"[quickbooks] Connected successfully (realm: {realm_id})")
        return tokens

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        print(f"[quickbooks] Token exchange failed ({e.code}): {body}")
        return None
    except Exception as e:
        print(f"[quickbooks] Token exchange error: {e}")
        return None


def refresh_access_token() -> dict | None:
    """Refresh the access token using the refresh token.

    Called automatically when API calls get 401.
    Returns updated token dict or None.
    """
    tokens = _load_tokens()
    if not tokens or not tokens.get("refresh_token"):
        print("[quickbooks] No refresh token available")
        return None

    auth_header = base64.b64encode(
        f"{QB_CLIENT_ID}:{QB_CLIENT_SECRET}".encode()
    ).decode()

    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
    }).encode("utf-8")

    req = urllib.request.Request(
        QB_TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        tokens["access_token"] = result.get("access_token", tokens["access_token"])
        tokens["refresh_token"] = result.get("refresh_token", tokens["refresh_token"])
        tokens["expires_in"] = result.get("expires_in", 3600)
        tokens["obtained_at"] = datetime.now().isoformat()

        _save_tokens(tokens)
        print("[quickbooks] Access token refreshed")
        return tokens

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        print(f"[quickbooks] Token refresh failed ({e.code}): {body}")
        return None
    except Exception as e:
        print(f"[quickbooks] Token refresh error: {e}")
        return None


def disconnect():
    """Disconnect QuickBooks (revoke tokens)."""
    tokens = _load_tokens()
    if tokens and tokens.get("refresh_token"):
        try:
            auth_header = base64.b64encode(
                f"{QB_CLIENT_ID}:{QB_CLIENT_SECRET}".encode()
            ).decode()
            body = json.dumps({"token": tokens["refresh_token"]}).encode("utf-8")
            req = urllib.request.Request(
                QB_REVOKE_URL,
                data=body,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=15)
        except Exception:
            pass

    # Clear stored tokens
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
    try:
        from services.supabase_client import query_table, delete_row
        results = query_table("app_settings", filters={"key": "qb_tokens"})
        for r in results:
            delete_row("app_settings", r["id"])
    except Exception:
        pass

    print("[quickbooks] Disconnected")


# ── API Helpers ──────────────────────────────────────────────────────────────

def _api_request(method: str, endpoint: str, data: dict | None = None,
                 retry_on_401: bool = True) -> dict | list | None:
    """Make an authenticated QuickBooks API request.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API path after /v3/company/{realm_id}/
        data: Request body for POST/PUT
        retry_on_401: Auto-refresh token and retry on 401

    Returns:
        Parsed JSON response or None on failure.
    """
    tokens = _load_tokens()
    if not tokens or not tokens.get("access_token"):
        print("[quickbooks] Not connected")
        return None

    realm_id = tokens.get("realm_id", "")
    url = f"{QB_API_BASE}/v3/company/{realm_id}/{endpoint}"

    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    body = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_text = resp.read().decode("utf-8")
            return json.loads(response_text) if response_text else {}

    except urllib.error.HTTPError as e:
        if e.code == 401 and retry_on_401:
            print("[quickbooks] Access token expired, refreshing...")
            if refresh_access_token():
                return _api_request(method, endpoint, data, retry_on_401=False)
        error_body = e.read().decode("utf-8", errors="replace")[:300]
        print(f"[quickbooks] API error ({e.code}): {error_body}")
        return None
    except Exception as e:
        print(f"[quickbooks] API request failed: {e}")
        return None


def _query(entity: str, where: str = "", max_results: int = 1000) -> list[dict]:
    """Run a QuickBooks query (SQL-like syntax).

    Args:
        entity: Entity type (e.g., 'Customer', 'Invoice', 'Payment')
        where: WHERE clause (e.g., "DisplayName = 'Acme Corp'")
        max_results: Max results to return

    Returns:
        List of entity dicts.
    """
    query = f"SELECT * FROM {entity}"
    if where:
        query += f" WHERE {where}"
    query += f" MAXRESULTS {max_results}"

    encoded = urllib.parse.quote(query)
    result = _api_request("GET", f"query?query={encoded}")

    if result and "QueryResponse" in result:
        return result["QueryResponse"].get(entity, [])
    return []


# ── Customer Sync ────────────────────────────────────────────────────────────

def find_qb_customer(display_name: str) -> dict | None:
    """Find a QuickBooks customer by display name."""
    customers = _query("Customer", f"DisplayName = '{display_name}'")
    return customers[0] if customers else None


def create_qb_customer(
    display_name: str,
    contact_name: str = "",
    email: str = "",
    phone: str = "",
    city: str = "",
    notes: str = "",
) -> dict | None:
    """Create a customer in QuickBooks.

    Returns the created customer dict or None.
    """
    customer_data = {
        "DisplayName": display_name,
        "CompanyName": display_name,
    }

    if contact_name:
        parts = contact_name.split(" ", 1)
        customer_data["GivenName"] = parts[0][:25]  # QB max 25 chars
        if len(parts) > 1:
            customer_data["FamilyName"] = parts[1][:25]

    if email:
        customer_data["PrimaryEmailAddr"] = {"Address": email}
    if phone:
        customer_data["PrimaryPhone"] = {"FreeFormNumber": phone}
    if city:
        customer_data["BillAddr"] = {"City": city, "CountrySubDivisionCode": "MS"}
    if notes:
        customer_data["Notes"] = notes[:2000]  # QB max

    result = _api_request("POST", "customer", customer_data)
    if result and "Customer" in result:
        return result["Customer"]
    return None


def sync_client_to_qb(client: dict) -> dict | None:
    """Sync an MCTV client to QuickBooks as a customer.

    Creates if not exists, returns QB customer dict.
    """
    business_name = client.get("business_name", "")
    if not business_name:
        return None

    # Check if already exists
    existing = find_qb_customer(business_name)
    if existing:
        return existing

    # Create new
    return create_qb_customer(
        display_name=business_name,
        contact_name=client.get("contact_name", ""),
        email=client.get("contact_email", ""),
        phone=client.get("contact_phone", ""),
        city=client.get("city", ""),
        notes=f"MCTV Portal ID: {client.get('id', '')} | Type: {client.get('client_type', '')}",
    )


def get_all_qb_customers() -> list[dict]:
    """Get all customers from QuickBooks."""
    return _query("Customer")


# ── Invoice Sync ─────────────────────────────────────────────────────────────

def create_qb_invoice(
    customer_id: str,
    amount: float,
    description: str = "MCTV Advertising",
    invoice_number: str = "",
    due_date: str = "",
    email: str = "",
) -> dict | None:
    """Create an invoice in QuickBooks.

    Args:
        customer_id: QB Customer ID (from sync)
        amount: Invoice total
        description: Line item description
        invoice_number: Your invoice number (DocNumber in QB)
        due_date: Due date string (YYYY-MM-DD)
        email: Customer email for delivery

    Returns:
        Created QB invoice dict or None.
    """
    invoice_data = {
        "CustomerRef": {"value": customer_id},
        "Line": [
            {
                "Amount": amount,
                "DetailType": "SalesItemLineDetail",
                "Description": description,
                "SalesItemLineDetail": {
                    "UnitPrice": amount,
                    "Qty": 1,
                },
            }
        ],
    }

    if invoice_number:
        invoice_data["DocNumber"] = invoice_number
    if due_date:
        invoice_data["DueDate"] = due_date
    if email:
        invoice_data["BillEmail"] = {"Address": email}

    result = _api_request("POST", "invoice", invoice_data)
    if result and "Invoice" in result:
        return result["Invoice"]
    return None


def sync_invoice_to_qb(invoice: dict, client: dict) -> dict | None:
    """Sync an MCTV portal invoice to QuickBooks.

    Creates the customer in QB if needed, then creates the invoice.
    Returns QB invoice dict or None.
    """
    # Ensure customer exists in QB
    qb_customer = sync_client_to_qb(client)
    if not qb_customer:
        print(f"[quickbooks] Could not sync customer: {client.get('business_name')}")
        return None

    qb_customer_id = qb_customer.get("Id", "")

    return create_qb_invoice(
        customer_id=qb_customer_id,
        amount=float(invoice.get("amount", 0)),
        description=invoice.get("description", "MCTV Advertising"),
        invoice_number=invoice.get("invoice_number", ""),
        due_date=invoice.get("due_date", ""),
        email=client.get("contact_email", ""),
    )


def get_qb_invoice(invoice_id: str) -> dict | None:
    """Get a single invoice from QuickBooks by ID."""
    result = _api_request("GET", f"invoice/{invoice_id}")
    if result and "Invoice" in result:
        return result["Invoice"]
    return None


def find_qb_invoice(doc_number: str) -> dict | None:
    """Find a QB invoice by DocNumber (our invoice_number)."""
    invoices = _query("Invoice", f"DocNumber = '{doc_number}'")
    return invoices[0] if invoices else None


def get_all_qb_invoices(since_date: str = "") -> list[dict]:
    """Get invoices from QuickBooks, optionally since a date."""
    where = f"TxnDate >= '{since_date}'" if since_date else ""
    return _query("Invoice", where)


# ── Payment Tracking ─────────────────────────────────────────────────────────

def get_qb_payments(since_date: str = "") -> list[dict]:
    """Get payments from QuickBooks, optionally since a date."""
    where = f"TxnDate >= '{since_date}'" if since_date else ""
    return _query("Payment", where)


def get_qb_payment(payment_id: str) -> dict | None:
    """Get a single payment from QuickBooks."""
    result = _api_request("GET", f"payment/{payment_id}")
    if result and "Payment" in result:
        return result["Payment"]
    return None


def check_invoice_payments(invoice_number: str) -> dict | None:
    """Check if an invoice has been paid in QuickBooks.

    Returns payment info if found, None if unpaid.
    """
    # Find the QB invoice first
    qb_invoice = find_qb_invoice(invoice_number)
    if not qb_invoice:
        return None

    balance = float(qb_invoice.get("Balance", 0))
    total = float(qb_invoice.get("TotalAmt", 0))

    if balance == 0 and total > 0:
        # Fully paid
        return {
            "status": "paid",
            "total": total,
            "balance": balance,
            "qb_invoice_id": qb_invoice.get("Id", ""),
        }
    elif balance < total:
        # Partially paid
        return {
            "status": "partial",
            "total": total,
            "balance": balance,
            "paid": total - balance,
            "qb_invoice_id": qb_invoice.get("Id", ""),
        }
    return None


# ── Batch Sync ───────────────────────────────────────────────────────────────

def sync_all_clients() -> dict:
    """Sync all MCTV clients to QuickBooks as customers.

    Returns summary dict with counts.
    """
    from services.portal_service import get_all_clients

    clients = get_all_clients()
    created = 0
    existing = 0
    failed = 0

    for client in clients:
        try:
            result = sync_client_to_qb(client)
            if result:
                # Check if it was newly created or already existed
                existing += 1  # We don't differentiate easily, count as synced
            else:
                failed += 1
        except Exception as e:
            print(f"[quickbooks] Failed to sync {client.get('business_name')}: {e}")
            failed += 1

    return {"total": len(clients), "synced": existing, "failed": failed}


def sync_unpaid_invoices() -> dict:
    """Check QuickBooks for payments on our outstanding invoices.

    Auto-marks invoices as paid in the portal when QB shows them paid.
    Returns summary dict.
    """
    from services.invoice_service import get_all_invoices, mark_paid

    outstanding = []
    for status in ("sent", "viewed", "overdue"):
        outstanding.extend(get_all_invoices(status=status))

    checked = 0
    newly_paid = 0

    for inv in outstanding:
        inv_num = inv.get("invoice_number", "")
        if not inv_num:
            continue

        payment_info = check_invoice_payments(inv_num)
        checked += 1

        if payment_info and payment_info.get("status") == "paid":
            mark_paid(inv.get("id", ""))
            newly_paid += 1
            print(f"[quickbooks] Invoice {inv_num} auto-marked paid from QB")

    return {"checked": checked, "newly_paid": newly_paid}


# ── Company Info ─────────────────────────────────────────────────────────────

def get_company_info() -> dict | None:
    """Get the connected QuickBooks company info."""
    realm_id = get_realm_id()
    if not realm_id:
        return None

    result = _api_request("GET", f"companyinfo/{realm_id}")
    if result and "CompanyInfo" in result:
        return result["CompanyInfo"]
    return None


# ── Webhook Verification ────────────────────────────────────────────────────

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify a QuickBooks webhook signature using HMAC-SHA256.

    Args:
        payload: Raw request body bytes
        signature: intuit-signature header value

    Returns:
        True if signature is valid.
    """
    if not QB_WEBHOOK_VERIFIER:
        return False

    expected = base64.b64encode(
        hmac.new(
            QB_WEBHOOK_VERIFIER.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    return hmac.compare_digest(expected, signature)


def process_webhook(payload: dict) -> list[dict]:
    """Process a QuickBooks webhook notification.

    Extracts entity changes and returns list of events.
    Each event: {"entity": "Payment", "id": "123", "operation": "Create"}
    """
    events = []
    for notification in payload.get("eventNotifications", []):
        realm_id = notification.get("realmId", "")
        for event in notification.get("dataChangeEvent", {}).get("entities", []):
            events.append({
                "entity": event.get("name", ""),
                "id": event.get("id", ""),
                "operation": event.get("operation", ""),
                "realm_id": realm_id,
                "last_updated": event.get("lastUpdated", ""),
            })
    return events


# ── Status Check ─────────────────────────────────────────────────────────────

def get_connection_status() -> dict:
    """Get QuickBooks connection status and summary."""
    if not QB_CLIENT_ID:
        return {
            "configured": False,
            "connected": False,
            "message": "QuickBooks API credentials not configured",
        }

    tokens = _load_tokens()
    if not tokens or not tokens.get("access_token"):
        return {
            "configured": True,
            "connected": False,
            "message": "QuickBooks not connected. Click Connect to authorize.",
        }

    # Try to get company info
    company = get_company_info()
    if company:
        return {
            "configured": True,
            "connected": True,
            "company_name": company.get("CompanyName", ""),
            "realm_id": tokens.get("realm_id", ""),
            "environment": QB_ENVIRONMENT,
            "message": f"Connected to {company.get('CompanyName', 'QuickBooks')}",
        }
    else:
        # Token might be expired, try refresh
        if refresh_access_token():
            company = get_company_info()
            if company:
                return {
                    "configured": True,
                    "connected": True,
                    "company_name": company.get("CompanyName", ""),
                    "realm_id": tokens.get("realm_id", ""),
                    "environment": QB_ENVIRONMENT,
                    "message": f"Connected to {company.get('CompanyName', 'QuickBooks')}",
                }

        return {
            "configured": True,
            "connected": False,
            "message": "Connection expired. Please reconnect QuickBooks.",
        }
