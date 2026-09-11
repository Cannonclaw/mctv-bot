#!/usr/bin/env python3
# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""
ONE-SHOT Portal Setup Script
=============================
Run this ONCE to set up everything for the MCTV Client Portal.

Usage:
    python scripts/setup_portal.py

It will:
1. Run the SQL schema (8 tables + RLS + indexes)
2. Create 3 team logins (Creed, Mary Michael, Swayze)
3. Create 4 storage buckets
4. Save the service key to .env

Just paste your service_role key when prompted.
"""

import json
import os
import secrets
import string
import sys
import urllib.request
import urllib.error
import getpass

# ── Config ───────────────────────────────────────────────────────────────────

SUPABASE_URL = "https://dtapevlfnekzepbtlabj.supabase.co"
PROJECT_ID = "dtapevlfnekzepbtlabj"

# No password literals here, deliberately.
#
# Until the September 2026 credential review this list carried one shared
# password in plain text for all three accounts — two of them admins. A literal
# in a tracked file is a live credential in every clone, every fork and every
# commit of the repo's history, and rotating it later does not remove it from
# any of those. The "CHANGE THESE PASSWORDS after first login" note that used to
# sit at the bottom of this script did not help: nothing enforced it.
#
# Each account now gets its own random password, generated at run time and shown
# once to the operator running the script. Nothing is persisted here.
TEAM_USERS = [
    {
        "email": "creed@mctvofms.com",
        "full_name": "T. Creed Cannon",
        "role": "admin",
    },
    {
        "email": "mmc@mctvofms.com",
        "full_name": "Mary Michael Cannon",
        "role": "admin",
    },
    {
        "email": "swayze@mctvofms.com",
        "full_name": "Swayze Hollingsworth",
        "role": "sales_rep",
    },
]


def initial_password() -> str:
    """Return a fresh random password for one team account.

    ``secrets`` rather than ``random``: the value is a real credential the
    moment the account exists, and ``random`` is seeded predictably enough to
    be guessable. The Mctv- prefix and the mixed alphabet satisfy Supabase
    Auth's complexity rule without making the tail any less random.
    """
    alphabet = string.ascii_letters + string.digits
    return "Mctv-" + "".join(secrets.choice(alphabet) for _ in range(20))


STORAGE_BUCKETS = ["contracts", "reports", "creative-uploads", "creative-deliveries"]


def _request(url, data=None, headers=None, method=None):
    """Make an HTTP request and return parsed JSON."""
    if data is not None:
        data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    if data and "Content-Type" not in (headers or {}):
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return {"error": json.loads(body), "status": e.code}
        except Exception:
            return {"error": body, "status": e.code}


def run_sql(service_key, sql):
    """Run SQL via the Supabase REST SQL endpoint (PostgREST rpc)."""
    # Use the pg-meta SQL execution endpoint
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    # Try the rpc approach first
    result = _request(url, {"query": sql}, headers)
    return result


def run_sql_via_pg(service_key, sql):
    """Run SQL statements one at a time via PostgREST."""
    # Since there's no direct SQL endpoint in the REST API,
    # we'll need to run it via the Supabase Management API or pg-meta
    # Let's try the pg-meta endpoint
    url = f"{SUPABASE_URL}/pg/sql"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    result = _request(url, {"query": sql}, headers)
    return result


def create_user(service_key, email, password, full_name, role):
    """Create a user via Supabase Auth Admin API."""
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    data = {
        "email": email,
        "password": password,
        "email_confirm": True,  # Auto-confirm email
        "user_metadata": {
            "full_name": full_name,
            "role": role,
        },
    }
    return _request(url, data, headers)


def create_bucket(service_key, bucket_name):
    """Create a storage bucket."""
    url = f"{SUPABASE_URL}/storage/v1/bucket"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    data = {
        "id": bucket_name,
        "name": bucket_name,
        "public": False,
    }
    return _request(url, data, headers)


def save_to_env(service_key):
    """Add SUPABASE_SERVICE_KEY and PORTAL_URL to .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

    existing = ""
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            existing = f.read()

    additions = []
    if "SUPABASE_SERVICE_KEY" not in existing:
        additions.append(f"SUPABASE_SERVICE_KEY={service_key}")
    if "SUPABASE_URL" not in existing:
        additions.append(f"SUPABASE_URL={SUPABASE_URL}")
    if "PORTAL_URL" not in existing:
        additions.append("PORTAL_URL=https://bot.mctvofms.com")

    if additions:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(additions) + "\n")
        print(f"  ✅ Added {len(additions)} vars to .env")
    else:
        print("  ℹ️  .env already has all portal vars")


def main():
    print("=" * 60)
    print("  MCTV Client Portal — One-Shot Setup")
    print("=" * 60)
    print()
    print("I need your Supabase SERVICE ROLE key.")
    print("Find it at:")
    print(f"  https://supabase.com/dashboard/project/{PROJECT_ID}/settings/api")
    print()
    print("Scroll to 'service_role' (the secret one). Copy & paste it below.")
    print()

    service_key = getpass.getpass("Paste service_role key (hidden): ").strip()

    if not service_key or len(service_key) < 20:
        print("❌ That doesn't look like a valid key. Aborting.")
        sys.exit(1)

    # ── Step 1: Verify the key works ─────────────────────────────
    print()
    print("─" * 40)
    print("Step 1: Verifying key...")
    test = _request(
        f"{SUPABASE_URL}/auth/v1/admin/users?page=1&per_page=1",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        },
    )
    if isinstance(test, dict) and "error" in test and test.get("status", 0) >= 400:
        print(f"❌ Key verification failed: {test}")
        print("Make sure you're using the service_role key, not the anon key.")
        sys.exit(1)
    print("  ✅ Key is valid!")

    # ── Step 2: Run SQL schema ───────────────────────────────────
    print()
    print("─" * 40)
    print("Step 2: Running SQL schema...")

    sql_path = os.path.join(os.path.dirname(__file__), "setup_portal_schema.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Try different SQL execution methods
    result = run_sql(service_key, sql)
    if isinstance(result, dict) and "error" in result:
        print(f"  ⚠️  RPC method didn't work (expected): {result.get('status', 'unknown')}")
        print("  Trying pg-meta endpoint...")
        result = run_sql_via_pg(service_key, sql)
        if isinstance(result, dict) and "error" in result:
            print(f"  ⚠️  pg-meta method didn't work either: {result.get('status', 'unknown')}")
            print()
            print("  📋 SQL schema must be run manually in the Supabase SQL Editor.")
            print(f"     Go to: https://supabase.com/dashboard/project/{PROJECT_ID}/sql/new")
            print("     The SQL has been copied to your clipboard.")
            try:
                import subprocess
                subprocess.run(
                    ["powershell", "-Command",
                     f"Get-Content '{sql_path}' | Set-Clipboard"],
                    check=True, capture_output=True
                )
                print("     ✅ SQL copied to clipboard! Just Ctrl+V in the SQL editor and Run.")
            except Exception:
                print("     Open the file manually: scripts/setup_portal_schema.sql")
        else:
            print("  ✅ SQL schema executed!")
    else:
        print("  ✅ SQL schema executed!")

    # ── Step 3: Create team users ────────────────────────────────
    print()
    print("─" * 40)
    print("Step 3: Creating team logins...")

    for user in TEAM_USERS:
        user["password"] = initial_password()
        result = create_user(
            service_key,
            user["email"],
            user["password"],
            user["full_name"],
            user["role"]
        )
        if isinstance(result, dict) and result.get("id"):
            user["created"] = True
            print(f"  ✅ {user['full_name']} ({user['email']}) — created!")
        elif isinstance(result, dict) and "error" in result:
            err = result["error"]
            if isinstance(err, dict) and "already" in str(err).lower():
                # The account predates this run, so the password generated above
                # was never applied. Forget it rather than printing a value that
                # does not log anyone in.
                user["password"] = None
                print(f"  ℹ️  {user['full_name']} ({user['email']}) — already exists")
            else:
                user["password"] = None
                print(f"  ⚠️  {user['full_name']}: {err}")
        else:
            user["created"] = True
            print(f"  ✅ {user['full_name']} ({user['email']}) — done!")

    # ── Step 4: Create storage buckets ───────────────────────────
    print()
    print("─" * 40)
    print("Step 4: Creating storage buckets...")

    for bucket in STORAGE_BUCKETS:
        result = create_bucket(service_key, bucket)
        if isinstance(result, dict) and result.get("name"):
            print(f"  ✅ Bucket '{bucket}' — created!")
        elif isinstance(result, dict) and "error" in result:
            err = result["error"]
            if "already" in str(err).lower() or "duplicate" in str(err).lower():
                print(f"  ℹ️  Bucket '{bucket}' — already exists")
            else:
                print(f"  ⚠️  Bucket '{bucket}': {err}")
        else:
            print(f"  ✅ Bucket '{bucket}' — done!")

    # ── Step 5: Save to .env ─────────────────────────────────────
    print()
    print("─" * 40)
    print("Step 5: Saving to .env...")
    save_to_env(service_key)

    # ── Done! ────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  🎉  SETUP COMPLETE!")
    print("=" * 60)
    print()
    created = [u for u in TEAM_USERS if u.get("password")]
    if created:
        print("  Team logins — copy these now, they are shown once and stored nowhere:")
        for u in created:
            print(f"  ├── {u['email']}  ({u['role']})")
            print(f"  │     {u['password']}")
        print()
        print("  ⚠️  Hand each password to its owner over a private channel, and")
        print("      have them change it at first login. Do not paste them into")
        print("      chat, a ticket, or any file in this repo.")
    else:
        print("  Team logins: all three accounts already existed — no passwords")
        print("  were set or changed by this run.")
    print()
    print("  Storage Buckets:")
    print("  ├── contracts, reports")
    print("  └── creative-uploads, creative-deliveries")
    print()
    print("  🔑  Don't forget to set on Render:")
    print(f"      SUPABASE_SERVICE_KEY = (the key you just pasted)")
    print(f"      PORTAL_URL = https://bot.mctvofms.com")
    print()
    print("  📋  If SQL didn't auto-run, paste it in the SQL editor:")
    print(f"      https://supabase.com/dashboard/project/{PROJECT_ID}/sql/new")
    print()
    print("  🚀  Then go to: https://bot.mctvofms.com/portal_login")
    print()


if __name__ == "__main__":
    main()
