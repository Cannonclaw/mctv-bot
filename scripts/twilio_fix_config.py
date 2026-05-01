"""Apply two production-side fixes to the MCTV Twilio config:

1. Set Messaging Service `usecase` from `undeclared` -> `mixed`
2. Clear the phone number's SMS/Voice webhooks that point at demo.twilio.com

These are independent of the A2P campaign, which still needs human re-review.
"""

import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

SID = os.environ["TWILIO_ACCOUNT_SID"]
TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
MS_SID = os.environ["TWILIO_MESSAGING_SERVICE_SID"]
AUTH = "Basic " + base64.b64encode(f"{SID}:{TOKEN}".encode()).decode()


def call(method, url, form=None):
    body = urllib.parse.urlencode(form).encode() if form else None
    headers = {"Authorization": AUTH, "Accept": "application/json"}
    if body:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", errors="replace")[:500]}


# ── 1. Find the phone number SID ────────────────────────────────────────────
status, nums = call("GET", f"https://api.twilio.com/2010-04-01/Accounts/{SID}/IncomingPhoneNumbers.json")
if status != 200:
    print("Could not list phone numbers:", nums)
    sys.exit(1)

phone_sid = None
for p in nums.get("incoming_phone_numbers", []):
    if p.get("phone_number") == os.environ.get("TWILIO_PHONE_NUMBER", "+16627076766"):
        phone_sid = p["sid"]
        print(f"Found phone {p['phone_number']} (sid={phone_sid})")
        print(f"  Current SMS URL:   {p.get('sms_url')}")
        print(f"  Current Voice URL: {p.get('voice_url')}")
        break

if not phone_sid:
    print("Phone number not found in account")
    sys.exit(1)

# ── 2. Set Messaging Service usecase = mixed ────────────────────────────────
print("\n[1/2] Setting Messaging Service usecase = mixed")
status, body = call(
    "POST",
    f"https://messaging.twilio.com/v1/Services/{MS_SID}",
    form={"Usecase": "mixed"},
)
print(f"  HTTP {status}")
if status == 200:
    print(f"  -> usecase is now: {body.get('usecase')}")
else:
    print(f"  ERROR: {body}")

# ── 3. Clear phone webhooks (set to empty string) ───────────────────────────
print("\n[2/2] Clearing phone number's demo webhooks")
status, body = call(
    "POST",
    f"https://api.twilio.com/2010-04-01/Accounts/{SID}/IncomingPhoneNumbers/{phone_sid}.json",
    form={
        "SmsUrl": "",
        "SmsFallbackUrl": "",
        "VoiceUrl": "",
        "VoiceFallbackUrl": "",
    },
)
print(f"  HTTP {status}")
if status == 200:
    print(f"  -> SMS URL:   {body.get('sms_url') or '(empty)'}")
    print(f"  -> Voice URL: {body.get('voice_url') or '(empty)'}")
else:
    print(f"  ERROR: {body}")

print("\nDone.")
