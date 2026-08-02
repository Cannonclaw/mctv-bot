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
    # Mirrors the public calculator's PACKAGES array (rate-calculator-v2.0-selfserve.html).
    # Keep both in step: a key listed here that the live page does not carry is ignored by
    # applyParams(), so the client lands on an empty builder instead of their quote.
    PKG_LABELS = {"p10": "10 Screens", "p20": "20 Screens", "p40": "40 Screens",
                  "p75": "75 Screens", "p125": "125+ Screens (whole network)"}
    pkg = st.selectbox("Package", list(PKG_LABELS),
                       format_func=lambda p: PKG_LABELS[p], key="ql_pkg")
    terr = st.multiselect("Territories", ["oxford", "tupelo", "starkville"],
                          format_func=lambda m: MARKET_LABELS.get(m, m.title()),
                          key="ql_terr")
    parts.append(f"pkg={pkg}")
    if terr:
        parts.append("terr=" + ",".join(terr))
    # (All five tiers went live on mctvofms.com/rate-quote 2026-08-02, verified
    # byte-identical to the source, so the temporary "not on the live page yet"
    # guard that sat here is gone.)
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

st.markdown("\U0001F4C7 **Client quote card** — send this one. Clean prepared-quote "
            "card: no builder to wade through, Accept & sign right there.")
st.code(card_link)

# One-tap send — open the rep's own mail/SMS app with the card link already written
# into the message, so there's nothing to copy and no app-switch-then-paste step.
_first_name = ql_name.strip().split()[0] if ql_name.strip() else "there"
_email_subject = "Your MCTV advertising quote"
_email_body = (
    f"Hi {_first_name},\n\n"
    "Here's your prepared MCTV Elite Advertising quote. Review the screens and "
    "pricing, and you can accept and sign right on the page:\n\n"
    f"{card_link}\n\n"
    "Reply here with any questions.\n\n"
    "— MCTV Elite Advertising"
)
_sms_body = f"Your MCTV quote is ready — review & sign here: {card_link}"

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
st.caption(
    "✅ The **v2.0** self-serve calculator is live at both mctvofms.com/rate-quote "
    "and bot.mctvofms.com/rates (deployed 2026-07-23) — prefilled links, the "
    "quote card, and in-page e-signing all work. Send away."
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


def _collateral_button(col, fname: str, label: str, help_text: str) -> None:
    fp = _SALES_DIR / fname
    if fp.exists():
        col.download_button(label, data=fp.read_bytes(), file_name=fname,
                            mime="application/pdf", width="stretch",
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
