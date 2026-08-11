# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Rate Card — Streamlit page for the MCTV Team Member portal.

Live impression-model pricing for every venue: OOH-style rates computed
from NTV360 traffic, calibrated dwell profiles, and each venue's ACTUAL
per-screen loop from the latest whitelist sweep. Rates update themselves
when loops are trimmed, traffic snapshots refresh, or the model knobs
change — no more static rate sheets.

Drop into: mctv-bot/pages/25_Rate_Card.py
"""
import re
import sys
import urllib.parse
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.config_service import (
    get_market_names,
    get_team_first_names,
    load_config,
)
from services.pipeline_service import advance_stage
from services.portal_service import create_client
from services.rate_service import (
    apply_tiers,
    market_rate_summary,
    model_params,
    venue_rates,
)
from services.supabase_client import query_table, update_row

st.set_page_config(
    page_title="Rate Card - MCTV Bot",
    page_icon="\U0001F4B5",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

MARKET_LABELS = {"oxford": "Oxford", "tupelo": "Tupelo",
                 "starkville": "Starkville", "special": "Special Venues"}

# Same dropdown vocabulary the Clients page offers, so a client created from a
# signed request is indistinguishable from one typed in by hand.
_CFG = load_config()
_TEAM_NAMES = get_team_first_names(_CFG) if _CFG.get("team") else []
_CITY_OPTIONS = (get_market_names(_CFG, active_only=False) + ["Other"]
                 if _CFG.get("markets") else [])


def mmss(minutes: float) -> str:
    s = int(round(minutes * 60))
    return f"{s // 60}:{s % 60:02d}"


rows = venue_rates()
params = model_params()
apply_tiers(rows)
summary = market_rate_summary(rows)

st.markdown("## \U0001F4B5 Rate Card")
# cap/discount only exist after the Phase-1 flip (scripts/023 section 2) runs —
# describing them earlier would contradict the uncapped rates shown below
_cap_caption = (
    f"capped ${params.get('venue_cap_4wk')}/venue · "
    f"{params.get('volume_discount_pct', 20)}% volume discount at "
    f"{params.get('volume_discount_screens', 10)}+ screens (custom builds). "
    if params.get("venue_cap_4wk") else ""
)
st.caption(
    "OOH-style impression pricing, computed **live**: NTV360 traffic × "
    "exposures (dwell ÷ the venue's *actual* loop from the latest sweep) "
    "× screen coverage. "
    f"CPM **${params.get('cpm', 6)}** · exposure cap {params.get('exposure_cap', 6)}. "
    f"4-wk rate = max(${params.get('floor_4wk', 25)} floor, impr×CPM), "
    + _cap_caption +
    "Knobs live in `rate_model_params`; venue inputs in `venue_rate_inputs`."
)

if not rows:
    st.info("No venues in `venue_rate_inputs` yet.")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Venues priced", len(rows))
k2.metric("Network weekly impressions", f"{sum(r['weekly_impressions'] for r in rows):,.0f}")
k3.metric("Network list value / 4wk", f"${sum(r['rate_4wk'] for r in rows):,.0f}")
k4.metric("Marquee venues", sum(1 for r in rows if r.get("tier") == "Marquee"))

st.divider()

# ── Self-serve agreement requests (public rate calculator signups) ───────────

STATUS_EMOJI = {"new": "\U0001F195", "countersigned": "✅",
                "converted": "\U0001F4C1", "rejected": "\U0001F6AB",
                "spam": "\U0001F6AB"}


def countersign_email(q: dict) -> tuple[str, str]:
    """Subject + plain-text body of the countersigned copy the client is owed.

    The public calculator's confirmation screen promises every signer, by
    name, that "Creed Cannon countersigns & emails your copy (typically
    within 1 business day)", and agreement term 6 makes the request binding
    only ON that countersignature. Marking the row `countersigned` here sent
    the client nothing, so the last step of the sale was a blank page and a
    hand-written email.

    Every figure below is read off the request row exactly as the client
    signed it -- nothing is computed, priced or re-derived, so this can never
    quote a number the agreement does not carry. The only mirrored rule is
    the prepay bonus (6 -> +1 free month, 12 -> +2, added free at the end of
    the paid term, agreement term 3), used to say "14 months" instead of
    making the client do the arithmetic.

    Body is deliberately ASCII-only and compact: it travels inside a mailto:
    URL, and mail clients on Windows start truncating those around 2 KB.
    """
    ref = q.get("ref") or ""
    name_parts = (q.get("contact_name") or "").strip().split()
    greeting = name_parts[0] if name_parts else "there"
    term = int(q.get("term_months") or 0)
    bonus = (2 if term == 12 else 1) if q.get("prepay") else 0

    lines = [
        f"Hi {greeting},",
        "",
        f"MCTV has countersigned your agreement ({ref}) - it's official. "
        "Your copy:",
        "",
    ]
    if q.get("business_name"):
        lines.append(f"  Business: {q['business_name']}")
    if q.get("screens"):
        lines.append(f"  Screens: {q['screens']} across the MCTV network")
    if q.get("monthly_total"):
        lines.append(f"  Monthly: ${float(q['monthly_total']):,.0f}")
    if term:
        term_line = f"  Term: {term} months"
        if bonus:
            term_line += (f" + {bonus} free (prepay bonus) = "
                          f"{term + bonus} months")
        lines.append(term_line)
    if q.get("term_total"):
        label = "Prepaid total" if q.get("prepay") else "Term total"
        lines.append(f"  {label}: ${float(q['term_total']):,.0f}")
    if q.get("start_date"):
        lines.append(f"  Start date: {q['start_date']}")
    if q.get("signed_name"):
        lines.append(f"  Signed: {q['signed_name']}")

    lines += [
        "",
        "NEXT",
        "1. We design your ad at no extra cost - reply here with your logo, "
        "any photos, and anything you want it to say.",
        "2. You approve the creative before it airs.",
        "3. Your first invoice goes out after you approve it, and your "
        "campaign starts on your start date.",
        "",
        "Terms are exactly as you signed them: 6-month minimum, 30 days' "
        "written notice to cancel after that, and any bonus months added "
        "free at the end of the paid term.",
        "",
        "Glad to have you on the network.",
        "",
        # Signature block quoted from the agreement footer the client
        # already read (calculator CFG repName/repPhone/repEmail).
        "Creed Cannon",
        "MCTV Elite Advertising (MCTV Digital, Inc.)",
        "601-405-5054 | creed@mctvofms.com",
    ]
    subject = f"Countersigned - your MCTV agreement {ref}".strip()
    return subject, "\n".join(lines)


def request_client_notes(q: dict) -> str:
    """One-line summary of the signed agreement, for the client record's notes.

    Quoted off the request row, never recomputed -- the client record must not
    be able to disagree with the paper the client signed.
    """
    bits = []
    if q.get("monthly_total"):
        bits.append(f"${float(q['monthly_total']):,.0f}/mo")
    if q.get("screens"):
        bits.append(f"{q['screens']} screens")
    if q.get("term_months"):
        bits.append(f"{int(q['term_months'])} months"
                    + (" PREPAID" if q.get("prepay") else ""))
    if q.get("term_total"):
        bits.append(f"term total ${float(q['term_total']):,.0f}")
    if q.get("start_date"):
        bits.append(f"start {q['start_date']}")
    if q.get("signed_name"):
        bits.append(f"signed by {q['signed_name']}")

    note = f"Self-serve signed agreement {q.get('ref') or '(no ref)'}"
    if bits:
        note += ": " + ", ".join(bits)
    return note + "."


def convert_request_to_client(q: dict, assigned_rep: str = "",
                              city: str = "", industry: str = "") -> tuple[str, str]:
    """Create the client record a signed self-serve agreement earned.

    Marking a request `converted` used to change a status string and nothing
    else, so the customer who had *just signed* still had to be retyped by
    hand on the Clients page (business, contact, email, phone) before anything
    downstream -- portal invite, invoices, campaign records -- could reference
    them, and their pipeline deal sat at Contract Sent / 90% until someone
    remembered to close it.

    Returns ("success" | "warning" | "error", message) instead of drawing, so
    the write path can be read and reasoned about on its own.
    """
    biz = (q.get("business_name") or "").strip()
    name = (q.get("contact_name") or "").strip()
    email = (q.get("contact_email") or "").strip()
    if not (biz and name and email):
        return "error", ("This request is missing a business name, contact "
                         "name or email, so there is nothing to create a "
                         "client from.")

    # `clients.contact_email` carries no unique constraint, so a second tap --
    # or a customer Creed already added by hand -- would otherwise silently
    # create a duplicate customer record.
    existing = next(
        (c for c in query_table("clients", select="id,business_name,contact_email")
         if (c.get("contact_email") or "").strip().lower() == email.lower()),
        None,
    )
    if existing:
        update_row("contract_requests", q["id"], {"status": "converted"})
        return "warning", (
            f"**{existing.get('business_name') or biz}** is already a client "
            f"({email}) — no duplicate was created. The request is marked "
            "converted; check the Clients page if the details changed."
        )

    client = create_client(
        business_name=biz,
        contact_name=name,
        contact_email=email,
        client_type="advertiser",
        contact_phone=(q.get("contact_phone") or "").strip(),
        industry=industry.strip(),
        city=city,
        assigned_rep=assigned_rep,
        lead_id=q.get("lead_id") or "",
        notes=request_client_notes(q),
    )
    if not client:
        return "error", ("Could not create the client record — nothing else "
                         "was changed. Try again, or add them on the Clients "
                         "page.")

    # The deal the edge function opened at Contract Sent / 90% when they
    # signed. `opportunity_id` is written back onto the request by
    # contract-initiate; older or partial rows may not carry one.
    opp_id = q.get("opportunity_id")
    if opp_id:
        if advance_stage(str(opp_id), "won", performed_by="Rate Card (self-serve)"):
            deal_note = " Their pipeline deal is now **Won**."
        else:
            deal_note = (" Their pipeline deal could not be found — close it "
                         "by hand on the Sales Pipeline page.")
    else:
        deal_note = (" No pipeline deal is linked to this request — check the "
                     "Sales Pipeline page.")

    update_row("contract_requests", q["id"], {"status": "converted"})
    return "success", (
        f"**{biz}** is now a client (advertiser, onboarding)." + deal_note
        + " Invite them to the portal from the Clients page when you are "
        "ready."
    )


st.markdown("### \U0001F91D Self-Serve Agreement Requests")

requests = query_table("contract_requests", order="-created_at", limit=50)
if not requests:
    st.success("No self-serve requests yet — share quote links below.")
else:
    new_reqs = [q for q in requests if q.get("status") == "new"]
    m1, m2 = st.columns(2)
    m1.metric("New requests", len(new_reqs))
    m2.metric("Pending $/mo", f"${sum(float(q.get('monthly_total') or 0) for q in new_reqs):,.0f}")

    for q in requests:
        emoji = STATUS_EMOJI.get(q.get("status") or "new", "\U0001F195")
        label = (
            f"{emoji} {q.get('business_name', '?')} — "
            f"${float(q.get('monthly_total') or 0):,.0f}/mo · "
            f"{q.get('ref', '')} · {(q.get('created_at') or '')[:10]}"
        )
        with st.expander(label):
            c1, c2 = st.columns(2)
            c1.markdown(
                f"**Contact:** {q.get('contact_name', '')}  \n"
                f"**Email:** {q.get('contact_email', '')}  \n"
                f"**Phone:** {q.get('contact_phone') or '—'}"
            )
            c2.markdown(
                f"**Term:** {q.get('term_months') or '—'} months · "
                f"{'prepaid' if q.get('prepay') else 'billed monthly'}  \n"
                f"**Start date:** {q.get('start_date') or 'ASAP'}  \n"
                f"**Screens:** {q.get('screens') or '—'} · "
                f"**Term total:** ${float(q.get('term_total') or 0):,.0f}"
            )

            selection = q.get("selection")
            if isinstance(selection, list) and selection:
                st.dataframe(selection, use_container_width=True, hide_index=True)
            elif selection:
                st.json(selection)

            st.markdown(
                f"**Signed:** {q.get('signed_name', '')} · "
                f"{(q.get('created_at') or '')[:19].replace('T', ' ')} · "
                f"IP {q.get('client_ip') or '?'}"
            )
            if q.get("quote_link"):
                st.code(q["quote_link"])

            # contract-initiate writes the request row first (record of truth),
            # then five best-effort CRM rows. Those five used to fail in silence:
            # the `leads` insert no-opped for a month against NOT NULL columns,
            # and every `activity_log` row was rejected because entity_id is a
            # uuid and the function passed the SSA- ref. Function v2 parks any
            # such failure on the request as "CRM sync warnings: ..." — show it,
            # because the signed agreement is still good and what's missing is
            # the lead/deal/task a rep would go looking for.
            _sync = str(q.get("notes") or "")
            if _sync.startswith("CRM sync warnings:"):
                st.warning(
                    "**This request did not fully reach the CRM.** The signed "
                    "agreement above is intact — but one or more follow-on "
                    "records were not created, so check the Pipeline and Tasks "
                    "pages before relying on them.",
                    icon="⚠️",
                )
                # st.code, not markdown: a raw Postgres error can carry $ (which
                # Streamlit would pair up as LaTeX), backticks or underscores.
                st.code(_sync)

            b1, b2, b3 = st.columns(3)
            if b1.button("✅ Mark countersigned", key=f"cr_counter_{q['id']}"):
                update_row("contract_requests", q["id"], {"status": "countersigned"})
                st.rerun()
            if b2.button("\U0001F4C1 Convert to client", key=f"cr_convert_{q['id']}"):
                st.session_state[f"cr_show_convert_{q['id']}"] = True
            if b3.button("\U0001F6AB Spam", key=f"cr_spam_{q['id']}"):
                update_row("contract_requests", q["id"], {"status": "spam"})
                st.rerun()

            # Last mile of the sale: signed here -> a real customer everywhere
            # else. Two steps on purpose (button, then confirm) so a stray tap
            # in the inbox can't create a client record.
            if st.session_state.get(f"cr_show_convert_{q['id']}"):
                st.markdown("**Convert to client**")
                st.caption(
                    "Creates an **advertiser** client record from this signed "
                    "request and closes its pipeline deal. Every field is "
                    "copied off the agreement as signed — nothing is re-priced."
                )
                cv1, cv2, cv3 = st.columns(3)
                _cv_rep = cv1.selectbox(
                    "Assign rep", [""] + _TEAM_NAMES, key=f"cr_rep_{q['id']}")
                _cv_city = cv2.selectbox(
                    "City", [""] + _CITY_OPTIONS, key=f"cr_city_{q['id']}",
                    format_func=lambda m: m or "—")
                _cv_industry = cv3.text_input(
                    "Industry", key=f"cr_ind_{q['id']}",
                    placeholder="Dental, Restaurant, Fitness…")

                cb1, cb2, cb3 = st.columns(3)
                _do_convert = cb1.button(
                    "Create client record", key=f"cr_do_convert_{q['id']}",
                    type="primary", width="stretch")
                _mark_only = cb2.button(
                    "Just mark converted", key=f"cr_mark_only_{q['id']}",
                    width="stretch",
                    help="They are already a client — leave the client list alone.")
                if cb3.button("Cancel", key=f"cr_cancel_convert_{q['id']}",
                              width="stretch"):
                    st.session_state.pop(f"cr_show_convert_{q['id']}", None)
                    st.rerun()

                if _mark_only:
                    update_row("contract_requests", q["id"], {"status": "converted"})
                    st.session_state.pop(f"cr_show_convert_{q['id']}", None)
                    st.rerun()

                if _do_convert:
                    with st.spinner("Creating the client record…"):
                        _lvl, _msg = convert_request_to_client(
                            q, assigned_rep=_cv_rep, city=_cv_city,
                            industry=_cv_industry)
                    st.session_state.pop(f"cr_show_convert_{q['id']}", None)
                    # Deliberately no st.rerun() here: a rerun would wipe the
                    # only report of what was written. The status above
                    # refreshes on the next interaction.
                    if _lvl == "success":
                        st.success(_msg)
                    elif _lvl == "warning":
                        st.warning(_msg)
                    else:
                        st.error(_msg)

            # Send the copy the client was promised. One tap opens your own
            # mail app with the whole confirmation already written -- ref,
            # what they bought, start date, and what happens next -- so the
            # 1-business-day promise on the public page is a click, not a
            # blank page and a hand-written email.
            _cs_subject, _cs_body = countersign_email(q)
            _cs_to = (q.get("contact_email") or "").strip()
            if _cs_to:
                st.link_button(
                    "\U0001F4E7 Email the countersigned copy to "
                    f"{q.get('contact_name') or _cs_to}",
                    "mailto:" + _cs_to
                    + "?subject=" + urllib.parse.quote(_cs_subject)
                    + "&body=" + urllib.parse.quote(_cs_body),
                    width="stretch",
                )
            else:
                st.button("\U0001F4E7 Email the countersigned copy",
                          key=f"cr_send_{q['id']}", width="stretch",
                          disabled=True,
                          help="This request carries no contact email.")
            st.caption(
                "Mark it countersigned, then send the copy — the "
                "agreement only becomes binding when MCTV countersigns "
                "(term 6), and the page they signed on promises the copy "
                "**within 1 business day**. Opens your own mail app with "
                "everything already written; read it before you send."
            )

    st.caption(
        "Each signed request auto-creates a **Contract Sent** deal on the "
        "Sales Pipeline page and a lead on the Leads page (source: website). "
        "Countersign → send the copy → **Convert to client**, which writes the "
        "client record and moves that deal to Won for you."
    )

st.divider()

# ── Shareable prefilled quote links ──────────────────────────────────────────

st.markdown("### \U0001F517 Shareable Quote Links")

QUOTE_BASE = "https://mctvofms.com/rate-quote/"

# Mirrors the public calculator's PACKAGES array (rate-calculator-v2.0-selfserve.html):
# label, screen count, the FLAT monthly price, and the ad-plays line printed on the card.
# Keep both in step: a key listed here that the live page does not carry is ignored by
# applyParams(), so the client lands on an empty builder instead of their quote.
# Package prices are flat and locked, so mirroring them here cannot drift with
# `rate_model_params` the way the a la carte table further down does.
PACKAGES = {
    "p10": {"label": "10 Screens", "screens": 10,
            "monthly": 350, "plays": "15,000"},
    "p20": {"label": "20 Screens", "screens": 20,
            "monthly": 500, "plays": "30,000"},
    "p40": {"label": "40 Screens", "screens": 40,
            "monthly": 800, "plays": "60,000"},
    "p75": {"label": "75 Screens", "screens": 75,
            "monthly": 1300, "plays": "110,000"},
    "p125": {"label": "125+ Screens (whole network)", "screens": 125,
             "monthly": 2000, "plays": "180,000+"},
}

# ── Audience plays: what the client sells → which rooms to put them in ───────
# Mirrors the PLAYS array in OneDrive\mctv-rate-quote\sales\_build-audience-plays.js
# — the source of the "Audience Plays" PDFs offered further down this page. Same
# ten verticals, same suggested venue-type mix, so a rep who reads a play on the
# sheet can build that exact quote here in one tap instead of hand-picking a
# dozen venues out of a flat 100-item list.
#
# The sheet keys each mix by venue-type CODE; this page only ever sees the
# label. The two vocabularies are identical — all 29 `type_label` values in
# `venue_rates_v` match the calculator's TYPES labels verbatim (checked
# 2026-08-06) — so labels are listed directly and the codes are kept in the
# comments, letting a future run diff the two lists without a translation step.
# A mix is a suggested STARTING point, never a fixed SKU: add or drop venues
# after the quick-add. Screen counts here are this page's inventory
# (`venue_rate_inputs`), which is 1 short of the calculator on 4 Corner's
# Chevron — so a gas-and-c-store play reads one screen lighter than the sheet.
AUDIENCE_PLAYS = {
    "Home Services": {  # bar rest sal asv gol par
        "eg": "HVAC, roofing, plumbing, restoration, pest, lawn",
        "types": ["Bar & Nightlife", "Restaurant", "Salon & Barber",
                  "Auto Service & Collision", "Golf Course",
                  "Parks & Recreation"]},
    "Bank · Credit Union · Insurance": {  # cha cli aut rest ret cof
        "eg": "branches, lenders, agents, financial advisors",
        "types": ["Chamber / Office Lobby", "Medical Clinic", "Auto Dealer",
                  "Restaurant", "Retail & Boutique", "Coffee & Smoothie"]},
    "Dental · Ortho · Specialty Practice": {  # gym sal nai spa vet pha
        "eg": "dentist, ortho, dermatology, urology, urgent care",
        "types": ["Gym & Fitness", "Salon & Barber", "Nail Salon",
                  "MedSpa & Wellness", "Veterinary", "Pharmacy"]},
    "Restaurant · Bar · Food": {  # gas shc hot par gym rnk
        "eg": "new location, daily specials, catering, food truck",
        "types": ["Gas & C-Store", "Shopping Center", "Hotel Lobby",
                  "Parks & Recreation", "Gym & Fitness", "Skating Rink"]},
    "Auto Dealer · Service · Tire": {  # rest bar gas rnk cop ret
        "eg": "dealership, collision, tires, detailing, glass",
        "types": ["Restaurant", "Bar & Nightlife", "Gas & C-Store",
                  "Skating Rink", "Farm Co-op", "Retail & Boutique"]},
    "Fitness · Nutrition · Wellness": {  # nai sal tan spa cof rest
        "eg": "gym, studio, supplements, med weight-loss, chiropractic",
        "types": ["Nail Salon", "Salon & Barber", "Tanning Salon",
                  "MedSpa & Wellness", "Coffee & Smoothie", "Restaurant"]},
    "Retail · Boutique · Furniture": {  # sal nai cof spa rest ret
        "eg": "clothing, gifts, jewelry, furniture, flooring",
        "types": ["Salon & Barber", "Nail Salon", "Coffee & Smoothie",
                  "MedSpa & Wellness", "Restaurant", "Retail & Boutique"]},
    "Real Estate · Rentals · Property": {  # air hot cof rest gym dcl
        "eg": "agents, brokerages, rentals, storage, developments",
        "types": ["Airport Terminal", "Hotel Lobby", "Coffee & Smoothie",
                  "Restaurant", "Gym & Fitness", "Dry Cleaner"]},
    "Internet · Telecom · Tech": {  # cha cof gas ret rest hot
        "eg": "fiber, IT services, security, phone systems",
        "types": ["Chamber / Office Lobby", "Coffee & Smoothie",
                  "Gas & C-Store", "Retail & Boutique", "Restaurant",
                  "Hotel Lobby"]},
    "Events · Campus · Civic": {  # par cof rest ret rnk gym
        "eg": "festivals, nonprofits, churches, ticketed events",
        "types": ["Parks & Recreation", "Coffee & Smoothie", "Restaurant",
                  "Retail & Boutique", "Skating Rink", "Gym & Fitness"]},
}

link_mode = st.radio("Link type", ["Network Package", "Custom venues"],
                     horizontal=True, key="ql_mode")
parts = []
quote_pkg = None   # set in package mode — drives the preview + the send templates
chosen = []        # set in custom mode
terr = []
if link_mode == "Network Package":
    pkg = st.selectbox("Package", list(PACKAGES),
                       format_func=lambda p: PACKAGES[p]["label"], key="ql_pkg")
    terr = st.multiselect("Territories", ["oxford", "tupelo", "starkville"],
                          format_func=lambda m: MARKET_LABELS.get(m, m.title()),
                          key="ql_terr")
    quote_pkg = PACKAGES[pkg]
    parts.append(f"pkg={pkg}")
    if terr:
        parts.append("terr=" + ",".join(terr))
    # (All five tiers went live on mctvofms.com/rate-quote 2026-08-02, verified
    # byte-identical to the source, so the temporary "not on the live page yet"
    # guard that sat here is gone.)
else:
    # Quick add. Building a "Tupelo restaurants" link used to mean typing a
    # dozen names into a flat 100-item list one at a time; the public tool got
    # a market/type venue finder in run #13 and the rep's own tool did not.
    # Filter to a market and/or venue type, see what it adds up to, add the lot.
    #
    # The multiselect below deliberately keeps ALL 100 venues as its options:
    # Streamlit prunes a selection down to whatever options it is handed, so
    # filtering the option list would silently drop venues already picked.
    # Filter what you ADD, never what is selected.
    _ql_sel = list(st.session_state.get("ql_venues", []))

    def _ql_add(names: list[str]) -> None:
        cur = list(st.session_state.get("ql_venues", []))
        st.session_state["ql_venues"] = cur + [n for n in names if n not in cur]

    def _ql_clear() -> None:
        st.session_state["ql_venues"] = []

    _mkts = sorted({r["market"] for r in rows if r.get("market")})
    _types = sorted({r["type_label"] for r in rows if r.get("type_label")})

    # The rep's actual first question is "what does this client sell?", not
    # "which venue type do I want". Answer that once and the mix from the
    # Audience Plays sheet is already filtered; the market/type controls below
    # narrow it further. All three filters AND together.
    _f_play = st.selectbox(
        "Quick add — audience play (what does the client sell?)",
        ["*"] + list(AUDIENCE_PLAYS), key="ql_f_play",
        format_func=lambda p: ("Any — I'll pick the rooms myself" if p == "*"
                               else f"{p} — {AUDIENCE_PLAYS[p]['eg']}"))
    _play_types = AUDIENCE_PLAYS[_f_play]["types"] if _f_play != "*" else None

    _f1, _f2 = st.columns(2)
    with _f1:
        _f_mkt = st.selectbox(
            "Quick add — market", ["*"] + _mkts, key="ql_f_mkt",
            format_func=lambda m: ("Any market" if m == "*"
                                   else MARKET_LABELS.get(m, m.title())))
    with _f2:
        _f_type = st.selectbox(
            "Quick add — venue type", ["*"] + _types, key="ql_f_type",
            format_func=lambda t: "Any type" if t == "*" else t)

    if _play_types:
        # Network size of the whole play, before the market/type narrowing —
        # context for the button below, which counts only what it will add.
        _p_rows = [r for r in rows if r.get("type_label") in _play_types]
        _p_screens = sum(int(r.get("screens") or 0) for r in _p_rows)
        _p_missing = [t for t in _play_types if t not in _types]
        st.caption(
            f"**{_f_play}** — the rooms this client should be in: "
            + ", ".join(_play_types)
            + f". {len(_p_rows)} venues / {_p_screens} screens network-wide"
            + (f" (no venues on this page for: {', '.join(_p_missing)})"
               if _p_missing else "")
            + ". Narrow it by market above, then add the lot. The full play "
            "— why those rooms land and the script to open with — is "
            "on the **Audience plays** sheet further down this page."
        )

    _matches = [r for r in rows
                if (_f_mkt == "*" or r.get("market") == _f_mkt)
                and (_f_type == "*" or r.get("type_label") == _f_type)
                and (_play_types is None
                     or r.get("type_label") in _play_types)]
    _new = [r for r in _matches if r["venue_name"] not in _ql_sel]
    _new_screens = sum(int(r.get("screens") or 0) for r in _new)

    _a1, _a2 = st.columns([3, 1])
    with _a1:
        if _new:
            st.button(
                f"\u2795 Add these {len(_new)} venues ({_new_screens} screens)",
                key="ql_add_matches", width="stretch",
                on_click=_ql_add, args=([r["venue_name"] for r in _new],))
        else:
            st.button(
                "\u2795 Add these venues", key="ql_add_matches",
                width="stretch", disabled=True,
                help=("Every venue matching this filter is already selected."
                      if _matches else "No venues match this filter."))
    with _a2:
        st.button("Clear all", key="ql_clear_venues", width="stretch",
                  disabled=not _ql_sel, on_click=_ql_clear)
    if _matches:
        _names = [r["venue_name"] for r in _matches]
        _already = len(_matches) - len(_new)
        st.caption(
            f"{len(_matches)} matching venue{'s' if len(_matches) != 1 else ''}: "
            + ", ".join(_names[:6])
            + (f" … +{len(_names) - 6} more" if len(_names) > 6 else "")
            + (f" — {_already} already selected." if _already else ""))

    chosen = st.multiselect("Venues", [r["venue_name"] for r in rows],
                            key="ql_venues")
    # Slug MUST match the calculator's JS:
    # s.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'')
    slugs = [re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-") for n in chosen]
    if slugs:
        parts.append("v=" + ".".join(slugs))

ql_months = st.radio("Term (months)", [6, 12], horizontal=True, key="ql_months")
ql_prepay = st.checkbox("Prepay the full term", key="ql_prepay")

st.markdown("**Prefill the client's details** — every field you fill here is one "
            "they don't type at signing (all optional).")
_c1, _c2 = st.columns(2)
with _c1:
    ql_biz = st.text_input("Business name", key="ql_biz")
    ql_email = st.text_input("Contact email", key="ql_email")
with _c2:
    ql_name = st.text_input("Contact name", key="ql_name")
    ql_phone = st.text_input("Contact phone", key="ql_phone")

parts.append(f"months={ql_months}")
if ql_prepay:
    parts.append("prepay=1")
for _param, _val in (("biz", ql_biz), ("name", ql_name),
                     ("email", ql_email), ("phone", ql_phone)):
    if _val.strip():
        parts.append(f"{_param}=" + urllib.parse.quote(_val.strip()))

query = "?" + "&".join(parts)

card_link = QUOTE_BASE + query + "&print=1"
builder_link = QUOTE_BASE + query

# ── What the client will see ─────────────────────────────────────────────────
# A rep used to have to open the link to find out what they were about to send,
# so the price never made it into the call, the text or their notes. Term math
# mirrors the calculator's currentQuote(): termTotal = monthly x term months,
# prepay bonus 6 -> +1 month, 12 -> +2, effective = termTotal / total months.
bonus_months = (2 if ql_months == 12 else 1) if ql_prepay else 0
total_months = ql_months + bonus_months

st.markdown("**What the client will see**")
if quote_pkg:
    monthly = quote_pkg["monthly"]
    term_total = monthly * ql_months
    effective = round(term_total / total_months)
    _q1, _q2, _q3 = st.columns(3)
    _q1.metric("They pay / month", f"${monthly:,}")
    _q2.metric(f"{ql_months}-month term total", f"${term_total:,}")
    _q3.metric("Screens", quote_pkg["screens"])
    # Territory wording is quoted from the card itself: currentQuote() prints
    # the selected market labels, and literally "To be selected" when the link
    # carries no `terr` — so an empty multiselect is worth flagging, not
    # silently calling it "all markets".
    _terr_txt = (", ".join(MARKET_LABELS.get(m, m.title()) for m in terr)
                 if terr else "**To be selected** — pick the territories "
                              "above or the card leaves that line blank for them")
    st.caption(
        f"{quote_pkg['label']} · Territories: {_terr_txt} · approx "
        f"{quote_pkg['plays']} ad plays/mo. Flat package price — the same "
        "number the card shows, whatever the table below says."
    )
    if bonus_months:
        st.success(
            f"**Prepay bonus:** pay the \\${term_total:,} upfront and they get "
            f"**{bonus_months} extra month{'s' if bonus_months > 1 else ''} free "
            f"— {total_months} months** for the price of {ql_months} "
            f"(effective \\${effective:,}/mo)."
        )
else:
    _sel_screens = sum(int(r.get("screens") or 0)
                       for r in rows if r["venue_name"] in chosen)
    # Nearest flat package, by the same rule the card's Compare uses: the
    # smallest absolute screen gap, ties going to the smaller tier (JS
    # `reduce` with a strict `<`, Python `min` keeping the first — same
    # answer). Safe to show pre-flip: package prices are flat and locked, so
    # this quotes the package sheet, not the engine.
    _near = (min(PACKAGES.values(), key=lambda p: abs(p["screens"] - _sel_screens))
             if _sel_screens else None)
    _v1, _v2, _v3 = st.columns(3)
    _v1.metric("Venues selected", len(chosen))
    _v2.metric("Screens (this page)", _sel_screens)
    _v3.metric("Nearest flat package",
               f"${_near['monthly']:,}" if _near else "—",
               _near["label"] if _near else None, delta_color="off")
    # Deliberately no dollar figure: a custom build is priced by the public
    # calculator's locked Phase-1 engine, and this page's rates are pre-flip.
    # Quoting one from here would hand the client a different number than the
    # page they sign on.
    # The screen count is this page's inventory (`venue_rate_inputs`), which as
    # of 2026-08-04 disagrees with the calculator on exactly one venue —
    # 4 Corner's Chevron (Chicken On A Stick): 1 here, 2 on the public page
    # (network 122 vs 123). Hence "this page" in the label; the card is the
    # number that counts. Drop the caveat once the two are reconciled.
    st.caption(
        "Custom builds are priced on the card itself, at the public tool's "
        "locked rates (\\$5 CPM, \\$25 floor, \\$175/venue cap"
        + (", 20% volume discount at 10+ screens" if _sel_screens >= 10 else "")
        + "). **Open the card link below to read the number before you quote it** "
        "\u2014 do not read it off the a la carte table further down this page, "
        "which is pre-flip."
        + (" The card's Compare panel will put this build next to the "
           f"**{_near['label']} package (\\${_near['monthly']:,}/mo flat)**; "
           "read which way it falls before you send it." if _near else "")
    )

st.markdown("\U0001F4C7 **Client quote card** — send this one. Clean prepared-quote "
            "card: no builder to wade through, Accept & sign right there.")
st.code(card_link)

# One-tap send — open the rep's own mail/SMS app with the card link already written
# into the message, so there's nothing to copy and no app-switch-then-paste step.
_first_name = ql_name.strip().split()[0] if ql_name.strip() else "there"

# Lead with the number. A package price is flat and known here, so the message
# can carry it instead of asking the client to click to find out what it costs.
# Custom builds get no figure — see the note above.
if quote_pkg:
    _headline = (f"{quote_pkg['screens']} screens across our network "
                 f"for ${quote_pkg['monthly']:,}/month")
    _terms_line = f"{ql_months}-month term, ${quote_pkg['monthly'] * ql_months:,} total"
    if bonus_months:
        _terms_line += (f" — prepay and you get {bonus_months} extra month"
                        f"{'s' if bonus_months > 1 else ''} free "
                        f"({total_months} months for the price of {ql_months})")
    _email_subject = f"Your MCTV quote — ${quote_pkg['monthly']:,}/mo"
    _email_intro = (f"Here's your prepared MCTV Elite Advertising quote: "
                    f"{_headline}. {_terms_line}.\n\n"
                    "The full breakdown is on the page, and you can accept and "
                    "sign right there:")
    _sms_body = (f"Your MCTV quote: {_headline}. Review & sign here: {card_link}")
else:
    _email_subject = "Your MCTV advertising quote"
    _email_intro = ("Here's your prepared MCTV Elite Advertising quote. Review "
                    "the screens and pricing, and you can accept and sign right "
                    "on the page:")
    _sms_body = f"Your MCTV quote is ready — review & sign here: {card_link}"

_email_body = (
    f"Hi {_first_name},\n\n"
    f"{_email_intro}\n\n"
    f"{card_link}\n\n"
    "Reply here with any questions.\n\n"
    "— MCTV Elite Advertising"
)

_send_l, _send_r = st.columns(2)
with _send_l:
    if ql_email.strip():
        st.link_button(
            "\U0001F4E7 Email this quote",
            "mailto:" + ql_email.strip()
            + "?subject=" + urllib.parse.quote(_email_subject)
            + "&body=" + urllib.parse.quote(_email_body),
            width="stretch",
        )
    else:
        st.button("\U0001F4E7 Email this quote", disabled=True,
                  width="stretch",
                  help="Add the contact email above to enable one-tap email.")
with _send_r:
    _sms_num = re.sub(r"[^\d+]", "", ql_phone)
    if _sms_num:
        st.link_button(
            "\U0001F4AC Text this quote",
            "sms:" + _sms_num + "?&body=" + urllib.parse.quote(_sms_body),
            width="stretch",
        )
    else:
        st.button("\U0001F4AC Text this quote", disabled=True,
                  width="stretch",
                  help="Add the contact phone above to enable one-tap text.")
st.caption("These open your own mail or messaging app with the quote-card link "
           "already in the message — one tap to send, nothing to copy. Email works "
           "on desktop and phone; text works from your phone.")

st.markdown("\U0001F527 **Full builder link** — for a client who wants to change "
            "screens or term before signing.")
st.code(builder_link)

st.caption("Text or email either link — the client sees their quote pre-built "
           "and can sign self-serve. Contact details you prefill travel inside "
           "the link, so send it only to that client.")
# bot.mctvofms.com/rates serves static/rates.html, still the 2026-07-23 build
# (three packages, tops out at $800, no venue finder). The re-synced copy is
# committed on branch `sync/rates-page-aug2026` and goes live the moment that
# branch merges — delete this caveat then.
st.caption(
    "✅ The current **v2.0** calculator is live at **mctvofms.com/rate-quote** "
    "— which is the URL every link above points at, so prefilled links, the "
    "quote card and in-page e-signing all work. Send away. "
    "⚠️ **Do not hand out bot.mctvofms.com/rates** — it is still the July build "
    "(three packages, tops out at \\$800, no venue search) until the "
    "`sync/rates-page-aug2026` branch is merged."
)

st.divider()

# ── Print-ready sales collateral ─────────────────────────────────────────────
# These PDFs are generated in OneDrive\mctv-rate-quote\sales\ (the market
# sheets by _build-rate-sheets.js, which mirrors the public calculator's
# venue/rate config) and copied into assets/sales/. If venues or rates
# change, regenerate there and re-copy — these are snapshots, not live.

_SALES_DIR = Path(__file__).parent.parent / "assets" / "sales"

st.markdown("### \U0001F4C4 Print-Ready Sales Collateral")
st.caption(
    "Grab the right leave-behind without digging through shared drives. The "
    "market sheets list every in-market screen at the public tool's locked "
    "Phase-1 rates (\\$5 CPM / \\$175 venue cap) — the same numbers your "
    "client sees at mctvofms.com/rate-quote, so they're always safe to hand "
    "out. Every client-facing piece carries the scannable QR straight to the "
    "self-serve tool. Not sure *which* screens to pitch a prospect? Start with "
    "the audience plays sheet."
)


def _collateral_button(col, fname: str, label: str, help_text: str,
                       mime: str = "application/pdf") -> None:
    fp = _SALES_DIR / fname
    if fp.exists():
        col.download_button(label, data=fp.read_bytes(), file_name=fname,
                            mime=mime, width="stretch",
                            help=help_text)
    else:
        col.button(label, disabled=True, width="stretch",
                   help="Missing from assets/sales/ — regenerate in "
                        "OneDrive mctv-rate-quote/sales and re-copy.")


_m1, _m2, _m3 = st.columns(3)
_collateral_button(_m1, "rate-sheet-oxford.pdf", "\U0001F4C4 Oxford rate sheet",
                   "55 screens / 44 venues, each at its exact 4-week rate. 2 pages.")
_collateral_button(_m2, "rate-sheet-tupelo.pdf", "\U0001F4C4 Tupelo rate sheet",
                   "33 screens / 27 venues, each at its exact 4-week rate. 1 page.")
_collateral_button(_m3, "rate-sheet-starkville.pdf", "\U0001F4C4 Starkville rate sheet",
                   "35 screens / 29 venues, each at its exact 4-week rate. 1 page.")

# The three sheets above are per-market, per-page and unsortable. This is the
# same 100 venues as one spreadsheet, so a rep can filter and sum a mix that
# crosses markets. Generated by sales/_build-network-csv.js off the SAME engine
# mirror as the sheets (it aborts unless all three market totals still match the
# printed pages), NOT off `venue_rates_v` — that table is still pre-flip.
st.caption(
    "**Pricing a mix that crosses markets?** The spreadsheet is all 100 venues "
    "in one sortable file, at the same locked rates as the sheets above and the "
    "client-facing tool. Filter to the rooms you want, sum "
    "`rate_at_10plus_screens_4wk` when the build carries 10+ screens, and "
    "compare that against the flat packages before you send it."
)
_c1, _c2, _c3 = st.columns(3)
_collateral_button(_c1, "network-rate-card.csv",
                   "\U0001F4CA Network rate card (CSV)",
                   "All 123 screens / 100 venues in one spreadsheet: market, "
                   "venue, type, screens, 4-week impressions, list rate, the "
                   "same rate with the 20% 10+ screen discount, and cost per "
                   "screen. Opens in Excel. Locked Phase-1 rates — matches the "
                   "printed sheets and the public tool exactly.",
                   mime="text/csv")

_o1, _o2, _o3 = st.columns(3)
_collateral_button(_o1, "rate-card-onepager.pdf", "\U0001F5FA Network one-pager",
                   "Whole-network overview: packages, prepay bonus, how to buy. "
                   "Client-facing, 1 page.")
_collateral_button(_o2, "audience-plays.pdf",
                   "\U0001F3AF Audience plays — INTERNAL",
                   "10 advertiser types (home services, banks, dental, "
                   "restaurants...) with the venue mix to pitch each one, its "
                   "screen count by market, and a script. For reps only — "
                   "2 pages.")
_collateral_button(_o3, "objection-handling-cheatsheet.pdf",
                   "\U0001F6E1 Objection cheat sheet — INTERNAL",
                   "11 objections with grounded rebuttals — including the "
                   "answer to \"I priced my own screens cheaper than your "
                   "package\" (same screen count, about a third of the "
                   "audience). For reps only — do NOT hand to clients. "
                   "2 pages.")

# The per-market cross of the two sheets above: the same 10 plays, filtered to
# one town, with the actual venue names and that mix's own 4-week price. This
# is the one a rep opens sitting in the parking lot.
st.caption(
    "**Working one town?** These are the same 10 plays filtered to that "
    "market — real venue names plus what that exact mix costs for 4 weeks, "
    "volume discount already applied where the mix carries 10+ screens."
)
_p1, _p2, _p3 = st.columns(3)
_collateral_button(_p1, "audience-plays-oxford.pdf",
                   "\U0001F3AF Oxford plays — INTERNAL",
                   "Oxford only: which rooms to pitch each advertiser type, "
                   "named, with the 4-week price for the mix. 55 screens / "
                   "44 venues. For reps only — 2 pages.")
_collateral_button(_p2, "audience-plays-tupelo.pdf",
                   "\U0001F3AF Tupelo plays — INTERNAL",
                   "Tupelo only: which rooms to pitch each advertiser type, "
                   "named, with the 4-week price for the mix. 33 screens / "
                   "27 venues. For reps only — 2 pages.")
_collateral_button(_p3, "audience-plays-starkville.pdf",
                   "\U0001F3AF Starkville plays — INTERNAL",
                   "Starkville only: which rooms to pitch each advertiser "
                   "type, named, with the 4-week price for the mix. 35 "
                   "screens / 29 venues. For reps only — 2 pages.")

# The public tool is on locked Phase-1 pricing ($5 CPM / $175 venue cap); this
# page follows `rate_model_params`, which only gains those knobs when the flip
# in scripts/023 section 2 runs. Until then a rep reading rates off this page
# quotes MORE than the page their client signs on — so say so, loudly. The
# warning disappears by itself the moment the flip lands.
# Dollar signs are escaped (\$) so Streamlit's markdown can't pair them up and
# swallow the run between two amounts as LaTeX — this block carries six of them.
if not params.get("venue_cap_4wk"):
    st.warning(
        "**Rates below are pre-flip — they do not match the client-facing tool.** "
        f"This page is still on \\${params.get('cpm', 6)} CPM with no venue cap. "
        "The public calculator (the page your client actually signs on) uses "
        "locked Phase-1 pricing: **\\$5 CPM, \\$175/venue 4-wk cap, 20% volume "
        "discount at 10+ screens** — so it quotes *lower* than the a la carte "
        "rates in the tabs below. Quote from a quote link or a market rate "
        "sheet above, not from this table, until the flip is run "
        "(`scripts/023_self_serve_rate_card.sql` "
        "section 2). Flat package prices (\\$350 / \\$500 / \\$800 / \\$1,300 / "
        "\\$2,000) are unaffected either way.",
        icon="⚠️",
    )

st.divider()

markets = [m for m in ("oxford", "tupelo", "starkville", "special") if m in summary]
tabs = st.tabs([MARKET_LABELS.get(m, m.title()) for m in markets])

for tab, market in zip(tabs, markets):
    with tab:
        s = summary[market]
        c1, c2, c3 = st.columns(3)
        c1.metric("Venues", s["venues"])
        c2.metric("Weekly impressions", f"{s['weekly_impressions']:,.0f}")
        c3.metric("List value / 4wk", f"${s['list_4wk']:,.0f}")

        st.dataframe(
            [
                {
                    "Venue": r["venue_name"],
                    "Type": r["type_label"],
                    "Screens": r["screens"],
                    "Loop": mmss(r["loop_min"]) + ("" if r["loop_from_sweep"] else " *"),
                    "Impr/wk": round(r["weekly_impressions"]),
                    "List $/4wk": r["rate_4wk"],
                    "Tier": r.get("tier", ""),
                    "Tier $/4wk": r.get("tier_rate", r["rate_4wk"]),
                }
                for r in rows
                if r["market"] == market
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Impr/wk": st.column_config.NumberColumn(format="%d"),
                "List $/4wk": st.column_config.NumberColumn(format="$%d"),
                "Tier $/4wk": st.column_config.NumberColumn(format="$%d"),
            },
        )
        st.caption(
            "Loop = venue's actual per-screen loop from the latest sweep "
            "(* = manual/fallback value, not sweep-matched). Tier price = "
            "median of the venue's rank quartile; Marquee venues priced "
            "individually."
        )

st.divider()
with st.expander("Model sources & how to adjust"):
    st.markdown(
        "- **Traffic**: NTV360 network-dashboard monthly snapshots (the same "
        "basis metric as MCTV traction reports); venues without NTV data use "
        "calibrated type defaults (`venue_type_defaults`).\n"
        "- **Dwell**: host-reported Install Form values where available "
        "(e.g. Oxford Park Commission 3:00), else type defaults.\n"
        "- **Loop**: per-venue actual from `screen_loops` (latest whitelist "
        "sweep) — shorter loops = more exposures per visit = higher rates.\n"
        "- **Adjust**: edit `rate_model_params` (CPM, cap, floor) or "
        "`venue_rate_inputs` (traffic/dwell/type) in Supabase; this page and "
        "`venue_rates_v` recompute instantly.\n"
        "- **Self-serve**: the public calculator at mctvofms.com/rate-quote "
        "prices from this same model; signed agreement requests land in "
        "`contract_requests` (inbox above) and auto-create the lead + "
        "Contract Sent pipeline deal. `quote_submissions` keeps every quote "
        "— including declines — for follow-up.\n"
        "- Impression counts are modeled upper-bound estimates (disclosed as "
        "such) — n-compass has no native impression counting."
    )
