# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Centralized Supabase client for Auth, Database, and Storage.

Uses supabase-py SDK for Auth + Storage operations.
Falls back gracefully when Supabase is not configured.
"""

import os
import json
import urllib.request
import urllib.error
import urllib.parse
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
    """Check if Supabase is configured with URL and at least one key."""
    url, anon_key, service_key = _get_url_and_keys()
    return bool(url and (anon_key or service_key))


# ── Auth helpers ─────────────────────────────────────────────────────────────

def sign_up(email: str, password: str, full_name: str, role: str = "advertiser",
            company_name: str = "") -> dict | None:
    """Create a new user account via Supabase Auth Admin API (REST).

    The profiles table auto-populates via database trigger (if it exists).
    Returns user dict on success, None on failure.
    """
    url, _, service_key = _get_url_and_keys()
    if not url or not service_key:
        return None

    try:
        body = json.dumps({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": full_name,
                "role": role,
                "company_name": company_name,
            },
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/auth/v1/admin/users",
            data=body,
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        return {
            "user_id": result.get("id", ""),
            "email": result.get("email", email),
        }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[supabase_client] Sign up failed ({e.code}): {body[:200]}")
        return None
    except Exception as e:
        print(f"[supabase_client] Sign up failed: {e}")
        return None


def sign_in(email: str, password: str) -> dict | None:
    """Sign in a user and return session info.

    Uses the REST Auth API directly (no SDK dependency for login).
    Returns dict with user_id, email, access_token, role on success.
    """
    url, anon_key, service_key = _get_url_and_keys()
    if not url:
        return None

    # Use whichever key is available (anon key preferred for auth, service key as fallback)
    api_key = anon_key or service_key
    if not api_key:
        return None

    try:
        # Authenticate via Supabase REST Auth endpoint
        body = json.dumps({"email": email, "password": password}).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/auth/v1/token?grant_type=password",
            data=body,
            headers={
                "apikey": api_key,
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        user = result.get("user", {})
        meta = user.get("user_metadata", {})

        # Get role + name from user_metadata (always available, set during user creation)
        role = meta.get("role", "advertiser")
        full_name = meta.get("full_name", email)

        # Try to fetch from profiles table (may have more up-to-date info)
        try:
            profiles = query_table("profiles", select="role,full_name,company_name",
                                   filters={"id": user.get("id", "")}, limit=1)
            if profiles and len(profiles) > 0:
                p = profiles[0]
                role = p.get("role", role)
                full_name = p.get("full_name", full_name)
        except Exception:
            # profiles table may not exist yet — user_metadata is fine
            pass

        return {
            "user_id": str(user.get("id", "")),
            "email": user.get("email", email),
            "full_name": full_name,
            "role": role,
            "access_token": result.get("access_token", ""),
            "refresh_token": result.get("refresh_token", ""),
        }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[supabase_client] Sign in failed ({e.code}): {body[:200]}")
        return None
    except Exception as e:
        print(f"[supabase_client] Sign in failed: {e}")
        return None


def sign_out(access_token: str) -> bool:
    """Sign out the current user via REST API."""
    url, anon_key, service_key = _get_url_and_keys()
    if not url or not access_token:
        return False

    api_key = anon_key or service_key
    if not api_key:
        return False

    try:
        req = urllib.request.Request(
            f"{url}/auth/v1/logout",
            data=b"{}",
            headers={
                "apikey": api_key,
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False


def send_magic_link(email: str) -> bool:
    """Send a magic link (passwordless OTP) email via Supabase Auth REST API.

    Magic link flow:
    1. This function sends an email with a login link to the user.
    2. The email contains a link like: {redirect_url}?token_hash=xxx&type=magiclink
    3. When the user clicks it, Supabase redirects to our portal_login page
       with query params that we exchange for a session via verify_otp().

    The redirect_to URL must be listed in Supabase Dashboard > Auth > URL Configuration
    under "Redirect URLs" (e.g., https://mctv-bot.onrender.com/portal_login).

    Returns True if the email was sent successfully.
    """
    url, anon_key, service_key = _get_url_and_keys()
    if not url:
        return False

    api_key = anon_key or service_key
    if not api_key:
        return False

    try:
        portal_url = os.environ.get("PORTAL_URL", "https://mctv-bot.onrender.com")
        body = json.dumps({
            "email": email,
        }).encode("utf-8")
        # POST /auth/v1/magiclink sends a magic link email.
        # Supabase will use the Site URL from dashboard settings for the redirect.
        req = urllib.request.Request(
            f"{url}/auth/v1/magiclink",
            data=body,
            headers={
                "apikey": api_key,
                "Content-Type": "application/json",
            },
        )
        urllib.request.urlopen(req, timeout=15)
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[supabase_client] Magic link failed ({e.code}): {body[:200]}")
        return False
    except Exception as e:
        print(f"[supabase_client] Magic link failed: {e}")
        return False


def verify_otp(token_hash: str, otp_type: str = "magiclink") -> dict | None:
    """Exchange a magic link or recovery token_hash for a full session.

    After the user clicks a magic link or password reset link, Supabase redirects
    back to our app with ?token_hash=xxx&type=magiclink (or type=recovery).
    This function exchanges that token_hash for access/refresh tokens.

    Args:
        token_hash: The token_hash from the URL query params.
        otp_type: Either "magiclink" or "recovery" (from the 'type' query param).

    Returns:
        dict with user_id, email, full_name, role, access_token, refresh_token
        on success; None on failure.
    """
    url, anon_key, service_key = _get_url_and_keys()
    if not url:
        return None

    api_key = anon_key or service_key
    if not api_key:
        return None

    try:
        body = json.dumps({
            "token_hash": token_hash,
            "type": otp_type,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/auth/v1/verify",
            data=body,
            headers={
                "apikey": api_key,
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        user = result.get("user", {})
        meta = user.get("user_metadata", {})

        role = meta.get("role", "advertiser")
        full_name = meta.get("full_name", user.get("email", ""))

        # Try to fetch from profiles table for up-to-date info
        try:
            profiles = query_table("profiles", select="role,full_name,company_name",
                                   filters={"id": user.get("id", "")}, limit=1)
            if profiles and len(profiles) > 0:
                p = profiles[0]
                role = p.get("role", role)
                full_name = p.get("full_name", full_name)
        except Exception:
            pass

        return {
            "user_id": str(user.get("id", "")),
            "email": user.get("email", ""),
            "full_name": full_name,
            "role": role,
            "access_token": result.get("access_token", ""),
            "refresh_token": result.get("refresh_token", ""),
        }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[supabase_client] OTP verify failed ({e.code}): {body[:200]}")
        return None
    except Exception as e:
        print(f"[supabase_client] OTP verify failed: {e}")
        return None


def get_user_by_token(access_token: str) -> dict | None:
    """Fetch the current user from an access token via Supabase Auth REST API.

    Used to validate and extract user info from an existing access token
    (e.g., after a magic link redirect that includes an access_token fragment).

    Returns dict with user info on success, None on failure.
    """
    url, anon_key, service_key = _get_url_and_keys()
    if not url or not access_token:
        return None

    api_key = anon_key or service_key
    if not api_key:
        return None

    try:
        req = urllib.request.Request(
            f"{url}/auth/v1/user",
            headers={
                "apikey": api_key,
                "Authorization": f"Bearer {access_token}",
            },
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            user = json.loads(resp.read().decode("utf-8"))

        meta = user.get("user_metadata", {})
        role = meta.get("role", "advertiser")
        full_name = meta.get("full_name", user.get("email", ""))

        # Try profiles table
        try:
            profiles = query_table("profiles", select="role,full_name,company_name",
                                   filters={"id": user.get("id", "")}, limit=1)
            if profiles and len(profiles) > 0:
                p = profiles[0]
                role = p.get("role", role)
                full_name = p.get("full_name", full_name)
        except Exception:
            pass

        return {
            "user_id": str(user.get("id", "")),
            "email": user.get("email", ""),
            "full_name": full_name,
            "role": role,
        }
    except Exception as e:
        print(f"[supabase_client] Get user by token failed: {e}")
        return None


def reset_password(email: str) -> bool:
    """Send a password reset email via Supabase Auth REST API.

    Password reset flow:
    1. This function sends an email with a reset link.
    2. The link redirects to portal_login with ?token_hash=xxx&type=recovery.
    3. portal_login detects the 'recovery' type and calls verify_otp() to
       exchange the token, which logs the user in and lets them set a new password.

    The redirect URL must be listed in Supabase Dashboard > Auth > URL Configuration.

    Returns True if the email was sent successfully.
    """
    url, anon_key, service_key = _get_url_and_keys()
    if not url:
        return False

    api_key = anon_key or service_key
    if not api_key:
        return False

    try:
        portal_url = os.environ.get("PORTAL_URL", "https://mctv-bot.onrender.com")
        body = json.dumps({
            "email": email,
            # redirect_to tells Supabase where to send the user after they click
            # the reset link. Supabase appends ?token_hash=xxx&type=recovery.
            "redirect_to": f"{portal_url}/portal_login",
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/auth/v1/recover",
            data=body,
            headers={
                "apikey": api_key,
                "Content-Type": "application/json",
            },
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"[supabase_client] Password reset failed: {e}")
        return False


def refresh_session(refresh_token: str) -> dict | None:
    """Refresh an expired access token using a refresh token.

    Returns dict with new access_token and refresh_token on success, None on failure.
    """
    url, anon_key, service_key = _get_url_and_keys()
    if not url or not refresh_token:
        return None

    api_key = anon_key or service_key
    if not api_key:
        return None

    try:
        body = json.dumps({"refresh_token": refresh_token}).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/auth/v1/token?grant_type=refresh_token",
            data=body,
            headers={
                "apikey": api_key,
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        return {
            "access_token": result.get("access_token", ""),
            "refresh_token": result.get("refresh_token", ""),
        }
    except Exception as e:
        print(f"[supabase_client] Token refresh failed: {e}")
        return None


def update_user_password(access_token: str, new_password: str) -> bool:
    """Update the authenticated user's password via Supabase Auth REST API.

    Called after a password recovery flow: the user clicks the reset link,
    verify_otp() exchanges it for a session, and then this function lets
    them set a new password using their access_token.

    Returns True on success.
    """
    url, anon_key, service_key = _get_url_and_keys()
    if not url or not access_token:
        return False

    api_key = anon_key or service_key
    if not api_key:
        return False

    try:
        body = json.dumps({"password": new_password}).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/auth/v1/user",
            data=body,
            headers={
                "apikey": api_key,
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        urllib.request.urlopen(req, timeout=15)
        return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[supabase_client] Password update failed ({e.code}): {err_body[:200]}")
        return False
    except Exception as e:
        print(f"[supabase_client] Password update failed: {e}")
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
            endpoint += f"&{col}=eq.{urllib.parse.quote(str(val), safe='')}"

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
    result = _rest_request("PATCH", f"{table}?{id_column}=eq.{urllib.parse.quote(str(row_id), safe='')}",
                           data=data, use_service_key=use_service_key)
    if result and len(result) > 0:
        return result[0]
    return None


def delete_row(table: str, row_id: str, id_column: str = "id",
               use_service_key: bool = True) -> bool:
    """Delete a row by ID. Returns True on success."""
    result = _rest_request("DELETE", f"{table}?{id_column}=eq.{urllib.parse.quote(str(row_id), safe='')}",
                           use_service_key=use_service_key)
    return result is not None
