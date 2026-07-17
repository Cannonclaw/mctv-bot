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

            b1, b2, b3 = st.columns(3)
            if b1.button("✅ Mark countersigned", key=f"cr_counter_{q['id']}"):
                update_row("contract_requests", q["id"], {"status": "countersigned"})
                st.rerun()
            if b2.button("\U0001F4C1 Mark converted", key=f"cr_convert_{q['id']}"):
                update_row("contract_requests", q["id"], {"status": "converted"})
                st.rerun()
            if b3.button("\U0001F6AB Spam", key=f"cr_spam_{q['id']}"):
                update_row("contract_requests", q["id"], {"status": "spam"})
                st.rerun()

    st.caption(
        "Each signed request auto-creates a **Contract Sent** deal on the "
        "Sales Pipeline page and a lead on the Leads page (source: website)."
    )

st.divider()

# ── Shareable prefilled quote links ──────────────────────────────────────────

st.markdown("### \U0001F517 Shareable Quote Links")

QUOTE_BASE = "https://mctvofms.com/rate-quote/"

link_mode = st.radio("Link type", ["Network Package", "Custom venues"],
                     horizontal=True, key="ql_mode")
parts = []
if link_mode == "Network Package":
    pkg = st.selectbox("Package", ["p10", "p20", "p40"],
                       format_func=lambda p: f"{p[1:]} Screens", key="ql_pkg")
    terr = st.multiselect("Territories", ["oxford", "tupelo", "starkville"],
                          format_func=lambda m: MARKET_LABELS.get(m, m.title()),
                          key="ql_terr")
    parts.append(f"pkg={pkg}")
    if terr:
        parts.append("terr=" + ",".join(terr))
else:
    chosen = st.multiselect("Venues", [r["venue_name"] for r in rows],
                            key="ql_venues")
    # Slug MUST match the calculator's JS:
    # s.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'')
    slugs = [re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-") for n in chosen]
    if slugs:
        parts.append("v=" + ".".join(slugs))

ql_months = st.radio("Term (months)", [6, 12], horizontal=True, key="ql_months")
ql_prepay = st.checkbox("Prepay the full term", key="ql_prepay")
ql_biz = st.text_input("Business name (optional)", key="ql_biz")

parts.append(f"months={ql_months}")
if ql_prepay:
    parts.append("prepay=1")
if ql_biz.strip():
    parts.append("biz=" + urllib.parse.quote(ql_biz.strip()))

st.code(QUOTE_BASE + "?" + "&".join(parts))
st.caption("text or email this link — the client sees their quote pre-built "
           "and can sign self-serve.")
st.warning(
    "Prefilled links need the **v2.0** calculator live at mctvofms.com/rate-quote — "
    "the old v1.6 page ignores them (opens blank). Check the page footer version "
    "before sending links.",
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
