# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
"""End-to-end QA suite — runs every backend pipeline and reports.

Cleans up after itself. Designed to leave production data untouched aside
from temporary rows created and deleted within the run.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

REPORT: list[dict] = []


def record(area: str, name: str, ok: bool, detail: str = ""):
    REPORT.append({"area": area, "name": name, "ok": ok, "detail": detail})
    icon = "PASS" if ok else "FAIL"
    print(f"[{icon}] {area:20} {name:55} {detail[:80]}")


# ── 1. Simulator round-trip ─────────────────────────────────────────────────
def test_simulator():
    try:
        from services.simulator_service import (
            build_scenario, save_scenario, load_scenario_by_token, list_venues,
        )
        from services.supabase_client import delete_row

        venues = list_venues()
        with_geo = [v for v in venues if v["lat"] and v["lon"]]
        record("simulator", "venues loaded", len(venues) >= 90,
               f"{len(venues)} total, {len(with_geo)} with geocodes")

        oxford = [v for v in venues if v["city"] == "Oxford"][:5]
        keys = [v["key"] for v in oxford]
        result = build_scenario(venue_keys=keys)
        record("simulator", "build_scenario(5 Oxford venues)", True,
               f"{result.total_screens} screens, {int(result.total_monthly_impressions):,} impressions")

        # Hand-compute and compare
        expected_imp = sum(v["traffic"] * v["dwell_time"] * v["license_count"] / 15.0
                           for v in oxford)
        match = abs(result.total_monthly_impressions - expected_imp) < 1.0
        record("simulator", "impressions match hand-computed", match,
               f"sim={int(result.total_monthly_impressions):,}, hand={int(expected_imp):,}")

        # Demographic blend
        blend_ok = (sum(result.blend.age_pct.values()) > 95.0
                    and sum(result.blend.income_pct.values()) > 95.0)
        record("simulator", "demographic blend renormalized", blend_ok,
               f"age sum={sum(result.blend.age_pct.values()):.1f}, "
               f"income sum={sum(result.blend.income_pct.values()):.1f}")

        # Save + reload
        saved = save_scenario(
            prospect_name="QA Test", prospect_email="qa@example.com",
            prospect_business="QA Co", venue_keys=keys, result=result,
            created_by="qa_suite",
        )
        record("simulator", "save_scenario", bool(saved),
               f"share_token={saved.get('share_token', '')[:8] if saved else 'None'}")

        if saved:
            loaded = load_scenario_by_token(saved["share_token"])
            ok = loaded and int(loaded["computed_metrics"]["total_screens"]) == result.total_screens
            record("simulator", "load_scenario_by_token", bool(ok),
                   f"view_count={loaded.get('view_count') if loaded else 'N/A'}")

            # Cleanup
            delete_row("simulator_scenarios", saved["id"])
            record("simulator", "cleanup test row", True, "")
    except Exception as e:
        record("simulator", "EXCEPTION", False, str(e)[:200])


# ── 2. Referral lifecycle ────────────────────────────────────────────────────
def test_referrals():
    try:
        from services.referral_service import (
            get_or_create_code, find_client_by_code, record_referral_signup,
            mark_referral_qualified, mark_referral_converted,
            get_host_referral_summary,
        )
        from services.supabase_client import (
            insert_row, query_table, update_row, delete_row,
        )

        # Create a fake host client
        host = insert_row("clients", {
            "business_name": "QA Host Venue", "contact_name": "QA Host",
            "contact_email": "qa-host@example.com", "client_type": "host",
            "status": "active",
        })
        if not host:
            record("referrals", "host client setup", False, "insert failed")
            return
        host_id = host["id"]

        # Generate referral code
        code = get_or_create_code(host_id)
        record("referrals", "get_or_create_code", bool(code and len(code) >= 6),
               f"code={code}")

        # Find by code
        found = find_client_by_code(code)
        record("referrals", "find_client_by_code", found and found["id"] == host_id, "")

        # Simulate intake form submission with ?ref=
        fake_lead = {
            "id": f"qa_lead_{datetime.now().strftime('%H%M%S')}",
            "business_name": "QA Referred Biz", "contact_name": "QA Customer",
            "contact_email": "qa-cust@example.com",
        }
        ref = record_referral_signup(code, fake_lead)
        record("referrals", "record_referral_signup", bool(ref),
               f"status={ref.get('status') if ref else 'None'}")

        # Qualify (lead becomes client)
        q = mark_referral_qualified(fake_lead["id"], host_id)
        record("referrals", "mark_referral_qualified", bool(q and q["status"] == "qualified"), "")

        # Convert (contract activates)
        c = mark_referral_converted(
            lead_id=fake_lead["id"], client_id=host_id,
            reward_value=25.0, reward_type="screen_time",
        )
        ok = c and c["status"] == "converted" and float(c.get("reward_value", 0)) == 25.0
        record("referrals", "mark_referral_converted with reward", bool(ok),
               f"reward=${c.get('reward_value', 0)}")

        # Summary
        summary = get_host_referral_summary(host_id)
        record("referrals", "get_host_referral_summary", summary["converted_count"] >= 1,
               f"converted={summary['converted_count']}")

        # Cleanup
        if ref:
            delete_row("referrals", ref["id"])
        delete_row("clients", host_id)
        record("referrals", "cleanup", True, "")
    except Exception as e:
        record("referrals", "EXCEPTION", False, str(e)[:200])


# ── 3. Renewal token flow ────────────────────────────────────────────────────
def test_renewal():
    try:
        from services.contract_service import (
            generate_renewal_offer, find_contract_by_renewal_token,
            accept_renewal_offer,
        )
        from services.supabase_client import insert_row, delete_row, query_table

        # Stub a client + contract
        client = insert_row("clients", {
            "business_name": "QA Renewal Co", "contact_name": "QA Renewal",
            "contact_email": "qa-renew@example.com", "client_type": "advertiser",
            "status": "active",
        })
        if not client:
            record("renewal", "client setup", False, "")
            return
        client_id = client["id"]

        contract = insert_row("contracts", {
            "client_id": client_id, "contract_type": "advertising",
            "title": "QA Test Contract", "tier_name": "10 Screens",
            "screen_count": 10, "monthly_rate": 350,
            "start_date": "2025-12-01", "end_date": "2026-06-01",
            "term_months": 6, "status": "active",
        })
        if not contract:
            delete_row("clients", client_id)
            record("renewal", "contract setup", False, "")
            return
        contract_id = contract["id"]

        # Generate offer
        offer = generate_renewal_offer(contract_id)
        record("renewal", "generate_renewal_offer", bool(offer and offer.get("token")),
               f"token={offer.get('token', '')[:8] if offer else 'None'}")

        # Find by token
        if offer:
            found = find_contract_by_renewal_token(offer["token"])
            record("renewal", "find_contract_by_renewal_token",
                   found and found["id"] == contract_id, "")

            # Accept
            new_draft = accept_renewal_offer(offer["token"], term_months=12)
            record("renewal", "accept_renewal_offer creates draft",
                   new_draft and new_draft.get("status") == "draft",
                   f"new_id={new_draft.get('id', '')[:8] if new_draft else 'None'}")

            # Cleanup new draft
            if new_draft:
                delete_row("contracts", new_draft["id"])

        delete_row("contracts", contract_id)
        delete_row("clients", client_id)
        record("renewal", "cleanup", True, "")
    except Exception as e:
        record("renewal", "EXCEPTION", False, str(e)[:200])


# ── 4. Exclusivity checker ──────────────────────────────────────────────────
def test_exclusivity():
    try:
        from services.exclusivity_service import (
            find_conflicts, is_clear, format_conflict_message,
        )
        from services.supabase_client import insert_row, delete_row

        # Create a client + contract WITH exclusivity to check against
        client = insert_row("clients", {
            "business_name": "QA Exclusive Realtor", "contact_name": "QA",
            "contact_email": "qa-excl@example.com", "client_type": "advertiser",
            "status": "active",
        })
        contract = insert_row("contracts", {
            "client_id": client["id"], "contract_type": "category_exclusivity",
            "title": "QA Exclusive", "screen_count": 75, "monthly_rate": 2000,
            "start_date": "2025-01-01", "end_date": "2027-01-01",
            "exclusive_category": "Real Estate Brokerage",
            "markets": ["Oxford"], "status": "active",
        })

        # Test conflict found
        conflicts = find_conflicts("Real Estate Brokerage", ["Oxford"])
        record("exclusivity", "detects same category + same market",
               any(c["contract_id"] == contract["id"] for c in conflicts),
               f"{len(conflicts)} conflict(s)")

        # Test no-conflict for different market
        conflicts2 = find_conflicts("Real Estate Brokerage", ["Tupelo"])
        no_conflict = not any(c["contract_id"] == contract["id"] for c in conflicts2)
        record("exclusivity", "ignores different market", no_conflict, "")

        # Test no-conflict for different category
        conflicts3 = find_conflicts("Bank", ["Oxford"])
        no_conflict_cat = not any(c["contract_id"] == contract["id"] for c in conflicts3)
        record("exclusivity", "ignores different category", no_conflict_cat, "")

        # is_clear shorthand
        record("exclusivity", "is_clear() works",
               not is_clear("Real Estate Brokerage", ["Oxford"]) and
               is_clear("Bank", ["Oxford"]), "")

        # Cleanup
        delete_row("contracts", contract["id"])
        delete_row("clients", client["id"])
        record("exclusivity", "cleanup", True, "")
    except Exception as e:
        record("exclusivity", "EXCEPTION", False, str(e)[:200])


# ── 5. NPS lifecycle ────────────────────────────────────────────────────────
def test_nps():
    try:
        from services.nps_service import (
            find_due_surveys, create_survey, find_survey_by_token,
            submit_response, categorize, get_aggregate,
        )
        from services.supabase_client import insert_row, delete_row

        # Categorize known scores
        record("nps", "categorize 9=promoter", categorize(9) == "promoter", "")
        record("nps", "categorize 7=passive", categorize(7) == "passive", "")
        record("nps", "categorize 5=detractor", categorize(5) == "detractor", "")

        # Stub a client + 100-day-old contract
        client = insert_row("clients", {
            "business_name": "QA NPS Co", "contact_name": "QA",
            "contact_email": "qa-nps@example.com", "client_type": "advertiser",
            "status": "active",
        })
        contract = insert_row("contracts", {
            "client_id": client["id"], "contract_type": "advertising",
            "title": "QA NPS Contract", "screen_count": 10, "monthly_rate": 350,
            "start_date": "2025-12-01",  # >100 days ago from 2026-04-30
            "end_date": "2026-12-01", "term_months": 12, "status": "active",
        })

        due = find_due_surveys()
        ours = [d for d in due if d["contract_id"] == contract["id"]]
        record("nps", "find_due_surveys picks up old contract",
               len(ours) > 0, f"due milestone={ours[0]['milestone'] if ours else 'none'}")

        # Create + respond
        if ours:
            survey = create_survey(contract["id"], client["id"], ours[0]["milestone"])
            record("nps", "create_survey", bool(survey and survey.get("survey_token")),
                   f"token={survey.get('survey_token', '')[:8] if survey else 'None'}")

            if survey:
                token = survey["survey_token"]
                found = find_survey_by_token(token)
                record("nps", "find_survey_by_token", bool(found), "")

                resp = submit_response(token, score=10,
                                        what_working="Everything",
                                        open_to_referrals=True)
                record("nps", "submit_response score=10", bool(resp), "")

                # Aggregate
                agg = get_aggregate(window_days=365)
                record("nps", "get_aggregate computes",
                       agg["response_count"] >= 1, f"NPS={agg['nps']}")

                delete_row("nps_responses", survey["id"])

        delete_row("contracts", contract["id"])
        delete_row("clients", client["id"])
        record("nps", "cleanup", True, "")
    except Exception as e:
        record("nps", "EXCEPTION", False, str(e)[:200])


# ── 6. Lead scoring ─────────────────────────────────────────────────────────
def test_lead_scoring():
    try:
        from services.leads_service import (
            calculate_lead_score, calculate_lead_score_breakdown,
        )

        hot = {
            "business_name": "Hot Co", "contact_name": "Sara", "contact_email": "s@x.com",
            "contact_phone": "6625551234", "industry": "Restaurant", "city": "Oxford",
            "source": "intake_form", "interest_level": "Ready to go", "sms_consent": True,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        cold = {
            "business_name": "Cold Co", "contact_name": "", "contact_email": "",
            "industry": "", "city": "Atlanta", "source": "cold_outreach",
            "submitted_at": "2025-01-01T00:00:00",
        }

        hot_score = calculate_lead_score(hot)
        cold_score = calculate_lead_score(cold)
        record("lead_scoring", "hot lead scores >= 80",
               hot_score >= 80, f"score={hot_score}")
        record("lead_scoring", "cold lead scores <= 30",
               cold_score <= 30, f"score={cold_score}")

        breakdown = calculate_lead_score_breakdown(hot)
        ok = ("breakdown" in breakdown and
              breakdown["bucket"] == "hot" and
              breakdown["breakdown"].get("source", 0) >= 30)
        record("lead_scoring", "breakdown returns rich detail", ok,
               f"bucket={breakdown.get('bucket')}")
    except Exception as e:
        record("lead_scoring", "EXCEPTION", False, str(e)[:200])


# ── 7. Screen health ────────────────────────────────────────────────────────
def test_screen_health():
    try:
        from services.screen_health_service import check_screen_health
        h = check_screen_health()
        if h.get("warning"):
            record("screen_health", "snapshot available", False, h["warning"][:80])
            return
        record("screen_health", "expected_per_screen calc",
               h["expected_per_screen"] > 0, f"{h['expected_per_screen']}/screen")
        record("screen_health", "venues classified",
               h["venue_count"] > 0, f"{h['venue_count']} venues, "
               f"dark={len(h['dark'])} low={len(h['low'])} ok={h['ok']}")
    except Exception as e:
        record("screen_health", "EXCEPTION", False, str(e)[:200])


# ── 8. Onboarding hook ──────────────────────────────────────────────────────
def test_onboarding():
    try:
        from services.onboarding_service import (
            STEPS, default_state, start_onboarding, mark_step,
            get_state, progress_pct,
        )
        from services.supabase_client import insert_row, delete_row

        ds = default_state()
        record("onboarding", "default_state has all steps",
               len(ds) == len(STEPS), f"{len(ds)} steps")
        record("onboarding", "progress_pct empty=0", progress_pct(ds) == 0, "")

        client = insert_row("clients", {
            "business_name": "QA Onboard", "contact_name": "QA",
            "contact_email": "qa-onboard@example.com", "client_type": "advertiser",
            "status": "active",
        })
        contract = insert_row("contracts", {
            "client_id": client["id"], "contract_type": "advertising",
            "title": "QA Onboard Contract", "screen_count": 10,
            "monthly_rate": 350, "term_months": 12,
            "start_date": "2026-04-30", "status": "active",
        })

        state = start_onboarding(contract["id"])
        record("onboarding", "start_onboarding seeds state + welcome",
               state and state["welcome"]["done"], "")

        mark_step(contract["id"], "kickoff_call", done=True, notes="Tested")
        s2 = get_state(contract["id"])
        record("onboarding", "mark_step persists",
               s2["kickoff_call"]["done"], f"pct={progress_pct(s2)}%")

        delete_row("contracts", contract["id"])
        delete_row("clients", client["id"])
        record("onboarding", "cleanup", True, "")
    except Exception as e:
        record("onboarding", "EXCEPTION", False, str(e)[:200])


# ── 9. Cron --dry-run smoke ─────────────────────────────────────────────────
def test_crons():
    import subprocess
    py = "C:/Users/msaac/AppData/Local/Python/bin/python.exe"
    crons = [
        "scripts/qbo_reconcile.py",
        "scripts/upsell_triggers.py",
        "scripts/win_back_lost_leads.py",
        "scripts/stalled_deal_alerts.py",
        "scripts/weekly_advertiser_pulse.py",
        "scripts/weekly_rep_recap.py",
        "scripts/nps_send.py",
        "scripts/push_briefing.py",
    ]
    for cron in crons:
        try:
            r = subprocess.run(
                [py, cron, "--dry-run"],
                cwd=str(ROOT),
                capture_output=True, text=True, timeout=60,
                env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
            )
            ok = r.returncode == 0
            stderr_tail = (r.stderr or "")[-150:].replace("\n", " ")
            record("cron", cron, ok, stderr_tail if not ok else "exit=0")
        except subprocess.TimeoutExpired:
            record("cron", cron, False, "TIMEOUT after 60s")
        except Exception as e:
            record("cron", cron, False, str(e)[:200])


# ── 10. Twilio status ───────────────────────────────────────────────────────
def test_twilio():
    import base64, os, urllib.request, urllib.error
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    tok = os.environ.get("TWILIO_AUTH_TOKEN")
    ms = os.environ.get("TWILIO_MESSAGING_SERVICE_SID")
    if not (sid and tok and ms):
        record("twilio", "credentials present", False, "missing env vars")
        return

    auth = "Basic " + base64.b64encode(f"{sid}:{tok}".encode()).decode()

    # Balance
    try:
        req = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Balance.json",
            headers={"Authorization": auth},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            b = json.loads(r.read().decode())
        bal = float(b.get("balance", 0))
        record("twilio", "account balance", bal > 0, f"${bal:.2f}")
    except Exception as e:
        record("twilio", "balance check", False, str(e)[:80])

    # Campaign status
    try:
        req = urllib.request.Request(
            f"https://messaging.twilio.com/v1/Services/{ms}/Compliance/Usa2p",
            headers={"Authorization": auth},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        items = data.get("compliance") or [data]
        c = next((x for x in items if isinstance(x, dict) and x.get("sid")), None)
        if c:
            status = c.get("campaign_status", "?")
            record("twilio", "A2P campaign status",
                   status in ("IN_PROGRESS", "VERIFIED"), f"status={status}")
        else:
            record("twilio", "A2P campaign exists", False, "no campaign")
    except Exception as e:
        record("twilio", "campaign check", False, str(e)[:80])

    # Phone number webhook (should be empty after our fix)
    try:
        req = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json",
            headers={"Authorization": auth},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        for p in data.get("incoming_phone_numbers", []):
            sms_url = (p.get("sms_url") or "")
            no_demo = "demo.twilio.com" not in sms_url
            record("twilio", "phone webhook clean (no demo URL)",
                   no_demo, f"sms_url='{sms_url}'")
    except Exception as e:
        record("twilio", "phone check", False, str(e)[:80])


# ── 11. Exclusivity message formatting ──────────────────────────────────────
def test_misc():
    try:
        from services.exclusivity_service import format_conflict_message
        msg = format_conflict_message([{
            "business_name": "Test Co", "exclusive_category": "Test",
            "overlapping_markets": ["Oxford"], "end_date": "2026-12-31",
            "monthly_rate": 1000, "contract_id": "x", "all_markets": ["Oxford"],
            "contract_type": "category_exclusivity",
        }])
        record("misc", "format_conflict_message produces text",
               len(msg) > 50 and "Oxford" in msg, "")
    except Exception as e:
        record("misc", "EXCEPTION", False, str(e)[:80])

    # Audience profiles
    try:
        from services.simulator_service import load_audience_profiles
        p = load_audience_profiles()
        record("misc", "audience profiles loaded",
               len([k for k in p if not k.startswith("_")]) >= 14, f"{len(p)} entries")
    except Exception as e:
        record("misc", "audience profiles", False, str(e)[:80])

    # Geocodes
    try:
        from services.simulator_service import load_geocodes
        g = load_geocodes()
        record("misc", "venue geocodes loaded",
               len(g) >= 80, f"{len(g)} venues geocoded")
    except Exception as e:
        record("misc", "geocodes", False, str(e)[:80])

    # Census
    try:
        from services.census_service import get_demographics
        d = get_demographics("38655")
        record("misc", "census ZIP 38655 returns data",
               d["population"] > 1000, f"pop={d['population']}, "
               f"income=${d['median_household_income']:,}")
    except Exception as e:
        record("misc", "census check", False, str(e)[:80])


# ── Run everything ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 100)
    print("MCTV-Bot QA Suite — full backend test pass")
    print("=" * 100)

    test_simulator()
    test_referrals()
    test_renewal()
    test_exclusivity()
    test_nps()
    test_lead_scoring()
    test_screen_health()
    test_onboarding()
    test_crons()
    test_twilio()
    test_misc()

    print("=" * 100)
    passed = sum(1 for r in REPORT if r["ok"])
    failed = sum(1 for r in REPORT if not r["ok"])
    print(f"TOTAL: {len(REPORT)} checks  PASS={passed}  FAIL={failed}")
    print("=" * 100)

    # Save a JSON report for later
    out = ROOT / "docs" / "qa_results.json"
    out.write_text(json.dumps(REPORT, indent=2, default=str), encoding="utf-8")
    print(f"Detailed report: {out}")

    sys.exit(0 if failed == 0 else 1)
