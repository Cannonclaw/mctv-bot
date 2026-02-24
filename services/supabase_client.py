"""Centralized Supabase client for Auth, Database, and Storage.

Uses supabase-py SDK for Auth + Storage operations.
Falls back gracefully when Supabase is not configured.
"""

import os
import json
import urllib.request
import urllib.error
from functools import lru_cache


# ── Client factory ───────────────────────────────────────────────────────────

def _get_url_and_keys():
    """Return (url, anon_key, service_key) from environment."""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon_key = os.environ.get("SUPABASE_KEY", "")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    return url, anon_key, service_key


def get_client():
    """Get a Supabase client using the anon key (RLS-enforced).

    Used for client-facing operations where RLS restricts data access.
    Returns None if Supabase is not configured.
    """
    try:
        from supabase import create_client
        url, anon_key, _ = _get_url_and_keys()
        if not url or not anon_key:
            return None
        return create_client(url, anon_key)
    except ImportError:
        print("[supabase_client] supabase-py not installed, using REST fallback")
        return None
    except Exception as e:
        print(f"[supabase_client] Failed to create client: {e}")
        return None


def get_admin_client():
    """Get a Supabase client using the service role key (bypasses RLS).

    Used for internal/admin operations where we need full access.
    Falls back to anon key if service key not set.
    Returns None if Supabase is not configured.
    """
    try:
        from supabase import create_client
        url, anon_key, service_key = _get_url_and_keys()
        if not url:
            return None
        key = service_key if service_key else anon_key
        if not key:
            return None
        return create_client(url, key)
    except ImportError:
        print("[supabase_client] supabase-py not installed, using REST fallback")
        return None
    except Exception as e:
        print(f"[supabase_client] Failed to create admin client: {e}")
        return None


def is_configured() -> bool:
    """Check if Supabase is configured with URL and key."""
    url, anon_key, _ = _get_url_and_keys()
    return bool(url and anon_key)


# ── Auth helpers ─────────────────────────────────────────────────────────────

def sign_up(email: str, password: str, full_name: str, role: str = "advertiser",
            company_name: str = "") -> dict | None:
    """Create a new user account via Supabase Auth.

    The profiles table auto-populates via database trigger.
    Returns user dict on success, None on failure.
    """
    client = get_admin_client()
    if not client:
        return None

    try:
        response = client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,  # Auto-confirm (admin-created accounts)
            "user_metadata": {
                "full_name": full_name,
                "role": role,
                "company_name": company_name,
            },
        })
        return {
            "user_id": response.user.id,
            "email": response.user.email,
        }
    except Exception as e:
        print(f"[supabase_client] Sign up failed: {e}")
        return None


def sign_in(email: str, password: str) -> dict | None:
    """Sign in a user and return session info.

    Returns dict with user_id, email, access_token, role on success.
    """
    client = get_client()
    if not client:
        return None

    try:
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        user = response.user
        session = response.session

        # Fetch role from profiles table
        profile = (client.table("profiles")
                   .select("role, full_name, company_name")
                   .eq("id", user.id)
                   .single()
                   .execute())

        role = profile.data.get("role", "advertiser") if profile.data else "advertiser"
        full_name = profile.data.get("full_name", email) if profile.data else email

        return {
            "user_id": str(user.id),
            "email": user.email,
            "full_name": full_name,
            "role": role,
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        }
    except Exception as e:
        print(f"[supabase_client] Sign in failed: {e}")
        return None


def sign_out(access_token: str) -> bool:
    """Sign out the current user."""
    client = get_client()
    if not client:
        return False

    try:
        client.auth.sign_out()
        return True
    except Exception:
        return False


def reset_password(email: str) -> bool:
    """Send a password reset email."""
    client = get_client()
    if not client:
        return False

    try:
        portal_url = os.environ.get("PORTAL_URL", "https://mctv-bot.onrender.com")
        client.auth.reset_password_email(email, {
            "redirect_to": f"{portal_url}/portal/portal_login",
        })
        return True
    except Exception as e:
        print(f"[supabase_client] Password reset failed: {e}")
        return False


# ── REST API helpers (for use without supabase-py SDK) ───────────────────────
# These mirror the pattern from leads_service.py for backward compatibility

def _rest_headers(key: str) -> dict:
    """Standard headers for Supabase REST API."""
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _rest_request(method: str, endpoint: str, data: dict | None = None,
                  use_service_key: bool = True) -> list | None:
    """Make a raw REST request to Supabase. Returns parsed JSON or None."""
    url, anon_key, service_key = _get_url_and_keys()
    if not url:
        return None

    key = (service_key if use_service_key and service_key else anon_key)
    if not key:
        return None

    full_url = f"{url}/rest/v1/{endpoint}"
    body = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(full_url, data=body, headers=_rest_headers(key),
                                method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else []
    except Exception as e:
        print(f"[supabase_client] REST {method} {endpoint} failed: {e}")
        return None


# ── Table query helpers ──────────────────────────────────────────────────────

def query_table(table: str, select: str = "*", filters: dict | None = None,
                order: str | None = None, limit: int | None = None,
                use_service_key: bool = True) -> list:
    """Query a Supabase table with optional filters, ordering, and limits.

    Args:
        table: Table name
        select: Columns to select (default: all)
        filters: Dict of {column: value} for eq filters
        order: Column to order by (prefix with - for desc, e.g. "-created_at")
        limit: Max rows to return
        use_service_key: Use service key to bypass RLS (default: True for admin)

    Returns:
        List of row dicts, or empty list on failure.
    """
    endpoint = f"{table}?select={select}"

    if filters:
        for col, val in filters.items():
            endpoint += f"&{col}=eq.{val}"

    if order:
        if order.startswith("-"):
            endpoint += f"&order={order[1:]}.desc"
        else:
            endpoint += f"&order={order}.asc"

    if limit:
        endpoint += f"&limit={limit}"

    result = _rest_request("GET", endpoint, use_service_key=use_service_key)
    return result if result is not None else []


def insert_row(table: str, data: dict, use_service_key: bool = True) -> dict | None:
    """Insert a row into a table. Returns the inserted row or None."""
    result = _rest_request("POST", table, data=data, use_service_key=use_service_key)
    if result and len(result) > 0:
        return result[0]
    return None


def update_row(table: str, row_id: str, data: dict,
               id_column: str = "id", use_service_key: bool = True) -> dict | None:
    """Update a row by ID. Returns the updated row or None."""
    result = _rest_request("PATCH", f"{table}?{id_column}=eq.{row_id}",
                           data=data, use_service_key=use_service_key)
    if result and len(result) > 0:
        return result[0]
    return None


def delete_row(table: str, row_id: str, id_column: str = "id",
               use_service_key: bool = True) -> bool:
    """Delete a row by ID. Returns True on success."""
    result = _rest_request("DELETE", f"{table}?{id_column}=eq.{row_id}",
                           use_service_key=use_service_key)
    return result is not None
