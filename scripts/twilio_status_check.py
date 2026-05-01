"""One-shot Twilio account status check for MCTV.

Pulls: account state, balance, phone numbers, A2P 10DLC brand+campaign status,
Messaging Service config, and last-30-day message activity. Read-only.
"""

import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from collections import Counter
from datetime import date, timedelta, datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

SID = os.environ["TWILIO_ACCOUNT_SID"]
TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
MS_SID = os.environ.get("TWILIO_MESSAGING_SERVICE_SID", "")
PHONE = os.environ.get("TWILIO_PHONE_NUMBER", "")

AUTH = "Basic " + base64.b64encode(f"{SID}:{TOKEN}".encode()).decode()
BASE = "https://api.twilio.com/2010-04-01"
MSG_BASE = "https://messaging.twilio.com/v1"


def get(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": AUTH, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"_error": True, "status": e.code, "body": body[:400], "url": url}
    except Exception as e:
        return {"_error": True, "msg": str(e), "url": url}


def section(title):
    print()
    print("-" * 72)
    print(f" {title}")
    print("-" * 72)


def show_err(label, r):
    print(f"  {label}: ERROR {r.get('status', '')} {r.get('body') or r.get('msg')}")


# ── 1. Account ──────────────────────────────────────────────────────────────
section("ACCOUNT")
acct = get(f"{BASE}/Accounts/{SID}.json")
if acct.get("_error"):
    show_err("account", acct)
    sys.exit(1)
print(f"  Friendly Name: {acct.get('friendly_name')}")
print(f"  Status:        {acct.get('status')}")
print(f"  Type:          {acct.get('type')}")
print(f"  Created:       {acct.get('date_created')}")

# ── 2. Balance ──────────────────────────────────────────────────────────────
section("BALANCE")
bal = get(f"{BASE}/Accounts/{SID}/Balance.json")
if bal.get("_error"):
    show_err("balance", bal)
else:
    print(f"  Current balance: ${bal.get('balance')} {bal.get('currency')}")

# ── 3. Phone numbers ────────────────────────────────────────────────────────
section("PHONE NUMBERS")
nums = get(f"{BASE}/Accounts/{SID}/IncomingPhoneNumbers.json")
if nums.get("_error"):
    show_err("phone numbers", nums)
else:
    for p in nums.get("incoming_phone_numbers", []):
        cap = p.get("capabilities", {})
        flags = ",".join(k.upper() for k, v in cap.items() if v)
        print(f"  {p.get('phone_number')}  [{flags}]  -> {p.get('friendly_name')}")
        print(f"      Status: {p.get('status')}  SMS URL: {p.get('sms_url') or '(none)'}")
        print(f"      Origin: {p.get('origin')}  Trunk SID: {p.get('trunk_sid') or '(none)'}")
        print(f"      Voice URL: {p.get('voice_url') or '(none)'}")

# ── 4. A2P 10DLC: Brand registrations ───────────────────────────────────────
section("A2P 10DLC — BRAND")
brands = get(f"{MSG_BASE}/a2p/BrandRegistrations")
if brands.get("_error"):
    show_err("brands", brands)
else:
    for b in brands.get("results", []) or brands.get("data", []):
        print(f"  Brand SID:  {b.get('sid')}")
        print(f"  Status:     {b.get('status')}  TCR id: {b.get('tcr_id') or '(none)'}")
        print(f"  Brand type: {b.get('brand_type')}  Score: {b.get('brand_score')}")
        print(f"  Failure:    {b.get('failure_reason') or '(none)'}")

# ── 5. Messaging Service + A2P Use Case (campaign) ──────────────────────────
section("MESSAGING SERVICE")
if MS_SID:
    ms = get(f"{MSG_BASE}/Services/{MS_SID}")
    if ms.get("_error"):
        show_err("messaging service", ms)
    else:
        print(f"  Service SID:        {ms.get('sid')}")
        print(f"  Friendly Name:      {ms.get('friendly_name')}")
        print(f"  Inbound Method:     {ms.get('inbound_method')}")
        print(f"  Inbound Request URL:{ms.get('inbound_request_url') or '(none)'}")
        print(f"  Sticky Sender:      {ms.get('sticky_sender')}")
        print(f"  MMS Converter:      {ms.get('mms_converter')}")
        print(f"  Smart Encoding:     {ms.get('smart_encoding')}")
        print(f"  Use Case:           {ms.get('usecase')}")

    section("A2P 10DLC — CAMPAIGN (Use Case)")
    uc = get(f"{MSG_BASE}/Services/{MS_SID}/Compliance/Usa2p")
    if uc.get("_error"):
        show_err("usa2p", uc)
    else:
        # Could be a list under "compliance" or a single object
        items = uc.get("compliance") or [uc]
        for c in items:
            if not isinstance(c, dict):
                continue
            print(f"  Campaign SID:    {c.get('sid')}")
            print(f"  Campaign status: {c.get('campaign_status')}")
            print(f"  Brand SID:       {c.get('brand_registration_sid')}")
            print(f"  Use case:        {c.get('us_app_to_person_usecase')}")
            print(f"  Has embedded links: {c.get('has_embedded_links')}")
            print(f"  Has embedded phone: {c.get('has_embedded_phone')}")
            print(f"  Description:     {(c.get('description') or '')[:120]}")
            print(f"  Sample messages: {len(c.get('message_samples') or [])}")
            print(f"  Rate limits:     {c.get('rate_limits')}")
            err = c.get("errors") or c.get("failure_reason")
            if err:
                print(f"  ERRORS:          {err}")
else:
    print("  TWILIO_MESSAGING_SERVICE_SID not set")

# ── 6. Last-30-day message activity ─────────────────────────────────────────
section("MESSAGE ACTIVITY — LAST 30 DAYS")
since = (date.today() - timedelta(days=30)).isoformat()
msgs_data = get(f"{BASE}/Accounts/{SID}/Messages.json", {"DateSent>": since, "PageSize": 200})
if msgs_data.get("_error"):
    show_err("messages", msgs_data)
else:
    msgs = msgs_data.get("messages", [])
    statuses = Counter(m.get("status") for m in msgs)
    directions = Counter(m.get("direction") for m in msgs)
    err_codes = Counter(m.get("error_code") for m in msgs if m.get("error_code"))
    cost_total = 0.0
    for m in msgs:
        try:
            cost_total += abs(float(m.get("price") or 0))
        except (TypeError, ValueError):
            pass
    print(f"  Total messages: {len(msgs)} (since {since})")
    print(f"  By status:    {dict(statuses)}")
    print(f"  By direction: {dict(directions)}")
    if err_codes:
        print(f"  Error codes:  {dict(err_codes)}")
    print(f"  Approx spend: ${cost_total:.4f}")
    # Show 5 most-recent
    if msgs:
        print(f"  Most recent:")
        for m in msgs[:5]:
            err_part = f" err={m.get('error_code')}" if m.get('error_code') else ""
            print(f"    {m.get('date_sent')}  {m.get('direction'):>15}  {m.get('status'):>10}  "
                  f"{m.get('from'):>14} -> {m.get('to'):>14}{err_part}")

# ── 7. Sub-resources health (auth violations, etc.) ─────────────────────────
section("RECENT NOTIFICATIONS / ALERTS")
alerts = get(f"https://monitor.twilio.com/v1/Alerts", {"PageSize": 10})
if alerts.get("_error"):
    show_err("alerts", alerts)
else:
    items = alerts.get("alerts", [])
    print(f"  Recent alert count: {len(items)}")
    for a in items[:8]:
        print(f"    {a.get('date_generated')}  {a.get('log_level'):>8}  {a.get('error_code')}  {a.get('alert_text', '')[:80]}")

print()
print("=" * 72)
print(" Done.")
print("=" * 72)
