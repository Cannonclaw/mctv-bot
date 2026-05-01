"""Resubmit the A2P 10DLC campaign with corrected message_flow + description.

The previous submission failed with TCR error 30896 because the message_flow
narrative referenced opt-in via private channels (contracts, internal portal).
This rewrites both fields to reference the publicly verifiable lead intake form
at https://mctvofms.com/get-started/, which now requires an explicit consent
checkbox.
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

NEW_DESCRIPTION = (
    "MCTV Digital, Inc. (d/b/a MCTV Elite Advertising) sends transactional SMS "
    "to business prospects and clients who explicitly opt in via the lead intake "
    "form at https://mctvofms.com/get-started/. Messages include: confirmation of "
    "inquiry receipt, monthly advertising performance reports, payment due "
    "reminders, and service updates. Messages are sent only to recipients who "
    "checked the SMS consent box at intake. Full SMS terms: "
    "https://mctvofms.com/sms-terms/"
)

NEW_MESSAGE_FLOW = (
    "End users opt in to receive SMS messages from MCTV Digital exclusively "
    "through the lead intake form publicly available at "
    "https://mctvofms.com/get-started/ (which embeds the form hosted at "
    "https://bot.mctvofms.com/Intake). The form requires users to check a "
    "mandatory consent checkbox labeled verbatim: \"I agree to receive SMS "
    "messages from MCTV Digital regarding my advertising inquiry. Message and "
    "data rates may apply. Message frequency varies. Reply STOP to opt out, "
    "HELP for help.\" A link to the SMS Terms (https://mctvofms.com/sms-terms/) "
    "and Privacy Policy is shown directly beside the checkbox. The form blocks "
    "submission unless the checkbox is checked. Each consent is persisted with "
    "a UTC timestamp, the user's IP address, the verbatim consent text, and "
    "the URL where consent was captured."
)


def call(method, url, form=None):
    body = urllib.parse.urlencode(form, doseq=True).encode() if form else None
    headers = {"Authorization": AUTH, "Accept": "application/json"}
    if body:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", errors="replace")[:600]}


# 1. Snapshot the current campaign for rollback record
print("[1/3] Fetching current campaign...")
status, current = call("GET", f"https://messaging.twilio.com/v1/Services/{MS_SID}/Compliance/Usa2p")
if status != 200:
    print(f"  ERROR fetching: {current}")
    sys.exit(1)
items = current.get("compliance") or [current]
campaign = items[0] if items and isinstance(items[0], dict) else None
if not campaign or not campaign.get("sid"):
    print(f"  No campaign found: {current}")
    sys.exit(1)
campaign_sid = campaign["sid"]
print(f"  Campaign SID: {campaign_sid}")
print(f"  Current status: {campaign.get('campaign_status')}")

# Save backup
backup_path = ROOT / "scripts" / f"a2p_backup_{campaign_sid}.json"
backup_path.write_text(json.dumps(campaign, indent=2), encoding="utf-8")
print(f"  Backup saved: {backup_path.name}")

# 2. Twilio's API for FAILED A2P campaigns: DELETE then POST a new one with
#    the same brand. POST-update of a FAILED campaign isn't allowed.
print("\n[2/3] Deleting failed campaign so we can resubmit fresh...")
del_status, del_body = call("DELETE", f"https://messaging.twilio.com/v1/Services/{MS_SID}/Compliance/Usa2p/{campaign_sid}")
print(f"  HTTP {del_status}")
if del_status not in (200, 204):
    print(f"  ERROR: {del_body}")
    print("  Aborting — campaign was not deleted, no resubmission attempted.")
    sys.exit(1)

# 3. Submit a fresh campaign with corrected fields
print("\n[3/3] Submitting fresh campaign with corrected message_flow + description...")
form = {
    "BrandRegistrationSid": campaign["brand_registration_sid"],
    "Description":          NEW_DESCRIPTION,
    "MessageFlow":          NEW_MESSAGE_FLOW,
    "MessageSamples":       campaign.get("message_samples") or [],
    "UsAppToPersonUsecase": campaign.get("us_app_to_person_usecase") or "LOW_VOLUME",
    "HasEmbeddedLinks":     str(bool(campaign.get("has_embedded_links"))).lower(),
    "HasEmbeddedPhone":     str(bool(campaign.get("has_embedded_phone"))).lower(),
    "OptInKeywords":        campaign.get("opt_in_keywords") or [],
    "OptOutKeywords":       campaign.get("opt_out_keywords") or [],
    "HelpKeywords":         campaign.get("help_keywords") or [],
    "OptInMessage":         campaign.get("opt_in_message") or "",
    "OptOutMessage":        campaign.get("opt_out_message") or "",
    "HelpMessage":          campaign.get("help_message") or "",
}
sub_status, sub_body = call("POST", f"https://messaging.twilio.com/v1/Services/{MS_SID}/Compliance/Usa2p", form=form)
print(f"  HTTP {sub_status}")
if sub_status not in (200, 201):
    print(f"  ERROR: {sub_body}")
    print(f"  Backup remains at {backup_path}")
    sys.exit(1)

print(f"  New campaign SID:   {sub_body.get('sid')}")
print(f"  New campaign status: {sub_body.get('campaign_status')}")
print()
print("Resubmitted. TCR review typically completes within 1-2 weeks.")
