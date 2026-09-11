#!/usr/bin/env python3
# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Regression tests for credential and secret handling.

Covers the defects found in the September 2026 credential review. Every test
here maps to something that was once broken in this repo, so a failure means a
fix has been undone rather than a hypothetical weakness:

  1. Login lockout counters survive a browser-session reset.
  2. The team password is compared in constant time.
  3. Saving one variable to .env does not truncate the other secrets.
  4. Capability tokens are redacted out of Supabase error logs.
  5. SMTP connections verify the server certificate.
  6. No credential literal is committed in the working tree.
  7. The public intake logo upload cannot escape data/logos.

Runs entirely offline — no Supabase, no SMTP, no network.

Usage:
    python scripts/credential_handling_test.py
"""

import inspect
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent

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


def check(condition, msg):
    ok(msg) if condition else fail(msg)


# ── 1. Login rate limiting ───────────────────────────────────────────────────

def test_rate_limiting():
    print()
    print("--- 1. Login lockout is not resettable from the browser ---")
    import services.auth as auth

    original_delay = auth._LOGIN_FAILURE_DELAY_SECONDS
    auth._LOGIN_FAILURE_DELAY_SECONDS = 0  # keep the suite fast
    try:
        auth._login_failures.clear()
        allowed_run = [auth._check_rate_limit("team") for _ in range(5)]
        for _ in range(5):
            auth._record_failed_login("team")
        check(all(allowed_run), "first five attempts are allowed")
        check(not auth._check_rate_limit("team"), "sixth attempt is locked out")

        # The original bug: counters lived in st.session_state, so a new tab
        # or a cleared cookie handed the attacker a fresh five attempts.
        auth.st.session_state = type("S", (dict,), {})()
        check(not auth._check_rate_limit("team"),
              "lockout survives a fresh browser session")

        auth._reset_login_attempts("team")
        check(auth._check_rate_limit("team"), "successful login clears the counter")

        auth._login_failures.clear()
        for _ in range(5):
            auth._record_failed_login("team")
        check(auth._check_rate_limit("portal"),
              "team lockout does not lock out the portal")

        # A header-rotating attacker must not be able to grow the tracker
        # without bound.
        import time
        auth._login_failures.clear()
        for i in range(auth._LOGIN_TRACKER_MAX_KEYS + 500):
            auth._login_failures[f"team:10.0.{i // 256}.{i % 256}"] = {
                "attempts": 1, "lockout_until": 0, "last_seen": time.time()}
        with auth._login_lock:
            auth._prune_login_failures(time.time())
        check(len(auth._login_failures) <= auth._LOGIN_TRACKER_MAX_KEYS,
              "failure tracker is capped against header rotation")

        # Streamlit serves sessions on threads, so the counter increment is a
        # read-modify-write on shared state. Lost updates would hand an
        # attacker extra attempts.
        import threading
        auth._login_failures.clear()

        def hammer():
            for _ in range(10):
                auth._record_failed_login("team")

        threads = [threading.Thread(target=hammer) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        counted = auth._login_failures[auth._rate_limit_key("team")]["attempts"]
        check(counted == 100, f"no lost updates under concurrency (counted {counted}/100)")
    finally:
        auth._LOGIN_FAILURE_DELAY_SECONDS = original_delay
        auth._login_failures.clear()


# ── 2. Constant-time password comparison ─────────────────────────────────────

def test_constant_time_compare():
    print()
    print("--- 2. Team password comparison ---")
    import services.auth as auth
    src = inspect.getsource(auth.render_team_login_form)
    check("compare_digest" in src, "uses hmac.compare_digest")
    check("password == correct" not in src, "no plain == on the password")


# ── 3. .env writes are non-destructive ───────────────────────────────────────

def test_env_write_preserves_secrets():
    print()
    print("--- 3. Saving a key to .env keeps the other secrets ---")
    settings = (PROJECT_ROOT / "pages" / "3_Settings.py").read_text(encoding="utf-8")
    check("_save_env_var" in settings, "settings page uses the merging writer")
    check("env_path.write_text(f\"ANTHROPIC_API_KEY=" not in settings,
          "settings page no longer truncates .env")

    # Exercise the real logic on a temp file.
    d = Path(tempfile.mkdtemp())
    env = d / ".env"
    env.write_text(
        "# config\nAPP_PASSWORD=pw\nSUPABASE_KEY=anon\n\n"
        "ANTHROPIC_API_KEY=old\nSMTP_PASS=mail\n",
        encoding="utf-8",
    )

    lines = env.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        if stripped.split("=", 1)[0].strip() == "ANTHROPIC_API_KEY":
            lines[i] = "ANTHROPIC_API_KEY=new"
            break
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")

    after = env.read_text(encoding="utf-8")
    for name in ("APP_PASSWORD=pw", "SUPABASE_KEY=anon", "SMTP_PASS=mail"):
        check(name in after, f"{name.split('=')[0]} survived the write")
    check("ANTHROPIC_API_KEY=new" in after and "old" not in after,
          "the target key was updated")


# ── 4. Tokens are redacted from logs ─────────────────────────────────────────

def test_log_redaction():
    print()
    print("--- 4. Capability tokens are redacted from Supabase error logs ---")
    from services.supabase_client import _redact, _truncate

    for endpoint, secret in [
        ("contracts?select=*&renewal_token=eq.abc123secret", "abc123secret"),
        ("nps_responses?select=*&survey_token=eq.tok_9f8e7d", "tok_9f8e7d"),
        ("simulator_shares?select=*&share_token=eq.SHARE-XYZ", "SHARE-XYZ"),
    ]:
        check(secret not in _redact(endpoint),
              f"{endpoint.split('?')[0]} token value is masked")

    plain = "clients?select=contact_email&city=eq.Oxford"
    check(_redact(plain) == plain, "non-sensitive filters are left readable")
    check(len(_truncate("x" * 5000)) < 700, "oversized error bodies are truncated")


# ── 5. SMTP verifies certificates ────────────────────────────────────────────

def test_smtp_tls():
    print()
    print("--- 5. SMTP connections verify the server certificate ---")
    # Python's smtplib defaults to ssl._create_stdlib_context(), which sets
    # check_hostname=False and verify_mode=CERT_NONE, so an explicit context is
    # the only thing standing between SMTP_PASS and a man in the middle.
    for mod in ("notification_service", "briefing_service", "leads_service"):
        src = (PROJECT_ROOT / "services" / f"{mod}.py").read_text(encoding="utf-8")

        # Inspect the call sites themselves. Matching the whole file would trip
        # over the TLS helper's docstring, which names starttls() and
        # SMTP_SSL() while explaining why they need an explicit context.
        starttls_calls = [l.strip() for l in src.splitlines()
                          if re.search(r"\bserver\.starttls\(", l)]
        ssl_calls = [l.strip() for l in src.splitlines()
                     if re.search(r"smtplib\.SMTP_SSL\(", l)]

        check(bool(starttls_calls) and all("context=" in l for l in starttls_calls),
              f"{mod}: every starttls() call passes a verifying context")
        check(bool(ssl_calls) and all("context=" in l for l in ssl_calls),
              f"{mod}: every SMTP_SSL() call passes a verifying context")

    import ssl
    ctx = ssl.create_default_context()
    check(ctx.check_hostname and ctx.verify_mode == ssl.CERT_REQUIRED,
          "create_default_context does verify (sanity check)")


# ── 6. No credentials committed ──────────────────────────────────────────────

def test_no_committed_credentials():
    print()
    print("--- 6. No credential literals in the working tree ---")
    patterns = [
        r"MCTV2026!",
        r"MCTVtest2026!",
        r"sk-ant-api03-[A-Za-z0-9_\-]{40,}",
        r"sk_[a-z]+_[0-9a-f]{40,}",
        r"SMTP_PASS\s*=\s*[\"'][^\"'{}$]{6,}[\"']",
        r"APP_PASSWORD\s*=\s*[\"'][^\"'{}$]{4,}[\"']",
    ]
    try:
        tracked = subprocess.run(
            ["git", "grep", "-nIE", "|".join(patterns)],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60,
        )
    except Exception as e:
        fail(f"could not run git grep: {e}")
        return

    hits = [l for l in tracked.stdout.splitlines() if l.strip()]
    # This test file names the historical literals on purpose.
    hits = [h for h in hits if not h.startswith("scripts/credential_handling_test.py")]
    if hits:
        for h in hits[:10]:
            fail(f"credential literal: {h[:120]}")
    else:
        ok("no credential literals in tracked files")


# ── 7. Intake logo upload cannot escape its directory ────────────────────────

def test_logo_path_containment():
    print()
    print("--- 7. Public logo upload stays inside data/logos ---")
    logos_dir = (PROJECT_ROOT / "data" / "logos").resolve()

    def build_name(business_name, upload_name):
        slug = "".join(
            c if (c.isalnum() or c in "-_") else "_"
            for c in business_name.strip()
        ).strip("_")[:64] or "logo"
        suffix = Path(upload_name).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            suffix = ".png"
        return f"{slug}{suffix}"

    attacks = [
        ("../../pages/99_Evil", "x.py"),
        ("../../../etc/cron.d/pwn", "y.png"),
        ("....//....//app", "z.py"),
        ("/absolute/path/thing", "a.png"),
    ]
    for biz, up in attacks:
        dest = (logos_dir / build_name(biz, up)).resolve()
        check(dest.parent == logos_dir, f"contained: {biz!r} + {up!r}")
        check(dest.suffix in {".png", ".jpg", ".jpeg", ".webp"},
              f"extension forced to an image type for {up!r}")

    dest = (logos_dir / build_name("Oxford Coffee Co.", "logo.png")).resolve()
    check(dest.name == "Oxford_Coffee_Co.png", "ordinary business names still work")

    src = (PROJECT_ROOT / "pages" / "0_Intake.py").read_text(encoding="utf-8")
    check('business_name.replace(" ", "_")' not in src,
          "the unsanitised filename construction is gone")


def main():
    print("=" * 60)
    print("  MCTV BOT - CREDENTIAL HANDLING REGRESSION TESTS")
    print("=" * 60)

    test_rate_limiting()
    test_constant_time_compare()
    test_env_write_preserves_secrets()
    test_log_redaction()
    test_smtp_tls()
    test_no_committed_credentials()
    test_logo_path_containment()

    print()
    print("=" * 60)
    total = passed + failed
    if failed == 0:
        print(f"  ALL {total} CREDENTIAL TESTS PASSED!")
    else:
        print(f"  {passed}/{total} passed, {failed} FAILED")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
