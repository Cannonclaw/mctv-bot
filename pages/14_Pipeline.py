# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Sales Pipeline Dashboard — visual pipeline management with revenue forecasting.

Provides a unified view of all opportunities moving through the sales process,
with stage tracking, deal management, nurture sequences, and revenue analytics.
"""

import streamlit as st
from datetime import date, datetime, timedelta

from services.auth import check_team_auth

if not check_team_auth():
    st.stop()


from services.team_ui import render_team_sidebar
render_team_sidebar()
from services.pipeline_service import (
    STAGES, TIERS, FOLLOW_UP_SLA, CLOSED_STAGES,
    get_all_opportunities, get_opportunity, create_opportunity,
    update_opportunity, delete_opportunity, advance_stage, mark_lost,
    get_pipeline_summary, get_revenue_forecast, get_deals_needing_action,
    get_activity, log_note, log_call, log_event, import_lead_to_pipeline,
    get_stage_options, get_rep_scoreboard,
    # Editability + data hygiene
    get_deleted, restore_opportunity, purge_deleted, merge_opportunities,
    find_duplicate_groups, find_junk_rows, looks_like_junk,
    validate_business_name, normalize_name, deleted_fingerprints,
    tier_payload, custom_payload, total_contract_value, is_custom_priced,
    get_forecast_gaps, local_today, counted,
)


# ── Write helpers ─────────────────────────────────────────────────────────────
# Every save goes through one of these so a rejected write is shown instead of
# silently swallowed. st.rerun() ALWAYS happens at the call site, never inside
# the try — RerunException subclasses Exception and would be caught as a bogus
# error (same trap documented in pages/23_Tasks.py).

def _run(fn, *args, **kwargs) -> bool:
    """Run a write and surface any failure. True when it actually succeeded."""
    try:
        result = fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        st.error(f"That didn't save: {e}")
        return False
    if result is False or result is None:
        st.error("That didn't save. The database rejected the change.")
        return False
    return True


def _save_deal(stage_moved: bool, did: str, stage_key: str,
               payload: dict, rep: str) -> bool:
    """Save an edited deal, routing a stage change through advance_stage."""
    try:
        if stage_moved:
            advance_stage(did, stage_key, performed_by=rep)
        if not update_opportunity(did, payload):
            st.error("That didn't save. The database rejected the change.")
            return False
        log_event(did, "value_updated", details="Deal details edited",
                  performed_by=rep)
    except Exception as e:  # noqa: BLE001
        st.error(f"That didn't save: {e}")
        return False
    st.success("Deal updated.")
    return True
from services.enrichment_service import (
    enrich_from_website, merge_enrichment, format_hours, normalize_url,
)
from services.nurture_service import (
    get_available_sequences, start_sequence, stop_sequence,
    get_next_step, send_nurture_step, run_nurture_batch,
)


# ── Page Config ───────────────────────────────────────────────────────────────

st.markdown('<p class="main-header">Sales Pipeline</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Track every deal from prospect to close</p>',
            unsafe_allow_html=True)

# Custom CSS for pipeline
st.markdown("""
<style>
    .pipeline-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 0.5rem;
        border-left: 4px solid #6c757d;
    }
    .pipeline-card h4 {
        margin: 0 0 0.3rem 0;
        font-size: 0.95rem;
        color: #1B1F3B;
    }
    .pipeline-card p {
        margin: 0;
        font-size: 0.82rem;
        color: #555;
    }
    .stage-header {
        text-align: center;
        padding: 0.5rem;
        border-radius: 6px;
        color: white;
        font-weight: bold;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
    }
    .forecast-card {
        background: #1B1F3B;
        border-radius: 10px;
        padding: 1rem;
        color: white;
        text-align: center;
    }
    .forecast-card h3 {
        color: #C5A55A;
        margin: 0;
    }
    .forecast-card p {
        color: #ccc;
        margin: 0.3rem 0 0;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Who's working ─────────────────────────────────────────────────────────────
# Shared team login means no per-user identity — this selector attributes
# every call, note, and stage move to the rep actually doing the work,
# which feeds the Rep Scoreboard's productivity-to-revenue metrics.

TEAM_REPS = ["Mary Michael", "Creed", "Swayze"]
_hdr1, _hdr2 = st.columns([4, 1])
with _hdr2:
    active_rep = st.selectbox("Working as", TEAM_REPS, key="active_rep")


# ── KPI Dashboard ─────────────────────────────────────────────────────────────

# Fetch the pipeline ONCE per rerun — every tab below reuses this list
# instead of making its own Supabase round-trip.
all_opps = get_all_opportunities()
summary = get_pipeline_summary(opps=all_opps)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Active Deals", summary["total_opportunities"])
k2.metric("Pipeline Value", f"${summary['total_pipeline_value']:,.0f}/mo")
k3.metric("Weighted Value", f"${summary['weighted_pipeline_value']:,.0f}/mo")
k4.metric(
    "Won This Month", f"${summary['mrr_won_this_month']:,.0f}/mo",
    help="Counted by the date each deal was actually won, so editing an old "
         "deal no longer moves its revenue into this month.",
)
k5.metric(
    "Win Rate", f"{summary['conversion_rate']:.0f}%",
    help=f"{summary['total_won']} won vs {summary['total_lost']} lost. "
         "Duplicates and junk rows marked Lost drag this down. Clear them "
         "in the Cleanup tab.",
)

_notes = []
if summary.get("excluded_count"):
    _notes.append(f"{summary['excluded_count']} deal(s) left out of these "
                  "numbers on purpose")
if summary.get("one_time_pipeline_value"):
    _notes.append(f"${summary['one_time_pipeline_value']:,.0f} in one-time "
                  "fees is tracked separately from MRR")
if summary.get("undated_wins"):
    _notes.append(f"{summary['undated_wins']} won deal(s) have no close date, "
                  "so they aren't in any month")
if _notes:
    st.caption(" - ".join(_notes))

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

(tab_pipeline, tab_deals, tab_add, tab_cleanup, tab_import,
 tab_nurture, tab_forecast, tab_actions, tab_scoreboard) = st.tabs([
    "Pipeline View", "All Deals", "Add Deal", "Cleanup", "Import Leads",
    "Nurture Center", "Forecast", "Action Items", "Rep Scoreboard",
])


# ── Shared pricing editor ────────────────────────────────────────────────────
# Used by both Add Deal and Edit Deal so a custom package is entered the same
# way in both places. Returns the pricing fields ready to save.

def render_pricing_inputs(key_prefix: str, deal: dict | None = None) -> dict:
    """Tier-or-custom pricing controls. Cannot be used inside st.form."""
    deal = deal or {}
    # is_custom_priced, not pricing_mode: the column defaults to 'tier', so a
    # negotiated rate or a $0 placeholder would otherwise open on the tier
    # dropdown and be rewritten to a stock $500 the moment anything was saved.
    is_custom = is_custom_priced(deal) if deal else False

    mode = st.radio(
        "Pricing",
        ["Standard tier", "Custom package"],
        index=1 if is_custom else 0,
        horizontal=True,
        key=f"{key_prefix}_mode",
        help="Use Custom for any proposal that doesn't fit the four stock "
             "tiers: a bundled rate, a flat project fee, a political flight.",
    )

    if mode == "Standard tier":
        tier_keys = list(TIERS.keys())
        cur = deal.get("tier_name")
        idx = tier_keys.index(cur) if cur in tier_keys else 1
        chosen = st.selectbox("Tier", tier_keys, index=idx, key=f"{key_prefix}_tier")
        st.caption(
            f"{TIERS[chosen]['screens']} screens - "
            f"${TIERS[chosen]['monthly']:,.0f}/mo"
        )
        _was = float(deal.get("monthly_value") or 0)
        if deal and is_custom_priced(deal) and _was != float(TIERS[chosen]["monthly"]):
            st.warning(
                f"This deal is priced at ${_was:,.0f}/mo. Saving on **Standard "
                f"tier** replaces that with ${TIERS[chosen]['monthly']:,.0f}/mo. "
                "Switch back to **Custom package** to keep the negotiated rate."
            )
        return tier_payload(chosen)

    p1, p2 = st.columns(2)
    with p1:
        pkg = st.text_input(
            "Package name",
            value=deal.get("tier_name", "") if is_custom else "",
            placeholder="e.g. Full Flight, Founding Partner, Project bundle",
            key=f"{key_prefix}_pkg",
        )
        monthly = st.number_input(
            "Monthly rate ($/mo)", min_value=0.0, step=50.0, format="%.2f",
            value=float(deal.get("monthly_value") or 0),
            key=f"{key_prefix}_monthly",
            help="Recurring revenue only. Put one-time project fees on the right.",
        )
    with p2:
        screens = st.number_input(
            "Screens", min_value=0, step=5,
            value=int(deal.get("screen_count") or 0),
            key=f"{key_prefix}_screens",
        )
        one_time = st.number_input(
            "One-time / flat fee ($)", min_value=0.0, step=100.0, format="%.2f",
            value=float(deal.get("one_time_value") or 0),
            key=f"{key_prefix}_onetime",
            help="Flat project or flight fees. Tracked separately so they "
                 "never get counted as monthly recurring revenue.",
        )

    term = st.number_input(
        "Contract term (months, 0 = not set)", min_value=0, max_value=120, step=1,
        value=int(deal.get("term_months") or 0),
        key=f"{key_prefix}_term",
    )

    payload = custom_payload(pkg, monthly, one_time, screens, term or None)
    tcv = total_contract_value({
        "monthly_value": monthly, "one_time_value": one_time, "term_months": term})
    st.caption(
        f"Total contract value: **${tcv:,.0f}**"
        + (f"  (${monthly:,.0f}/mo x {int(term)} mo"
           + (f" + ${one_time:,.0f} flat" if one_time else "") + ")"
           if term else "  (no term set - counted as one month)")
    )
    return payload


# ── Tab 1: Pipeline View ─────────────────────────────────────────────────────

with tab_pipeline:
    # Active stages only (exclude won/lost)
    active_stages = {k: v for k, v in STAGES.items() if k not in ("won", "lost")}

    cols = st.columns(len(active_stages))

    for col, (stage_key, stage_info) in zip(cols, sorted(active_stages.items(), key=lambda x: x[1]["order"])):
        with col:
            stage_opps = [o for o in all_opps if o.get("stage") == stage_key]
            # Column total counts only what the KPI row counts, or this board
            # and the Forecast tab's "Pipeline by Stage" disagree on one page.
            stage_value = sum(float(o.get("monthly_value") or 0)
                              for o in counted(stage_opps))
            _excl_here = len(stage_opps) - len(counted(stage_opps))

            st.markdown(
                f'<div class="stage-header" style="background:{stage_info["color"]}">'
                f'{stage_info["label"]} ({len(stage_opps)})<br>'
                f'<span style="font-size:0.75rem">${stage_value:,.0f}/mo</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            for opp in stage_opps[:10]:
                value = float(opp.get("monthly_value") or 0)
                city = opp.get("city", "")
                contact = opp.get("contact_name", "")

                st.markdown(
                    f'<div class="pipeline-card" style="border-left-color:{stage_info["color"]}">'
                    f'<h4>{opp.get("business_name", "Unknown")}</h4>'
                    f'<p>${value:,.0f}/mo'
                    f'{" | " + city if city else ""}'
                    f'{" | " + contact if contact else ""}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            if len(stage_opps) > 10:
                st.caption(f"+{len(stage_opps) - 10} more")

            if _excl_here:
                st.caption(f"{_excl_here} not counted in the total")

            if not stage_opps:
                st.caption("No deals")


# ── Tab 2: All Deals ─────────────────────────────────────────────────────────

with tab_deals:
    # Filters
    f1, f2, f3 = st.columns(3)
    with f1:
        filter_stage = st.selectbox(
            "Filter by Stage",
            ["All"] + [v["label"] for v in sorted(STAGES.values(), key=lambda x: x["order"])],
            key="deals_filter_stage"
        )
    with f2:
        filter_city = st.selectbox(
            "Filter by City",
            ["All", "Oxford", "Starkville", "Tupelo", "Other"],
            key="deals_filter_city"
        )
    with f3:
        search = st.text_input("Search", placeholder="Business name...", key="deals_search")

    # Get filtered deals (filter the already-fetched list — no extra round-trip)
    stage_filter = None
    if filter_stage != "All":
        stage_filter = [k for k, v in STAGES.items() if v["label"] == filter_stage]
        stage_filter = stage_filter[0] if stage_filter else None

    deals = [d for d in all_opps if d.get("stage") == stage_filter] if stage_filter else list(all_opps)

    if filter_city != "All":
        if filter_city == "Other":
            deals = [d for d in deals if (d.get("city") or "").lower() not in ("oxford", "starkville", "tupelo")]
        else:
            deals = [d for d in deals if (d.get("city") or "").lower() == filter_city.lower()]

    if search:
        search_lower = search.lower()
        deals = [d for d in deals if search_lower in (d.get("business_name") or "").lower()
                 or search_lower in (d.get("contact_name") or "").lower()]

    # Each deal renders a full editor, so drawing all 80+ at once makes the
    # tab crawl. Show a page at a time; the filters above narrow it further.
    PAGE = 15
    _total = len(deals)
    _shown = st.session_state.get("deals_shown", PAGE)
    if _shown > _total:
        _shown = max(PAGE, _total)
    deals = deals[:_shown]

    st.caption(f"Showing {len(deals)} of {_total} deal(s)")

    for deal in deals:
        stage_info = STAGES.get(deal.get("stage", "prospect"), STAGES["prospect"])
        value = float(deal.get("monthly_value") or 0)
        prob = deal.get("probability", 0)

        with st.expander(
            f"**{deal.get('business_name', 'Unknown')}** — "
            f"{stage_info['label']} — ${value:,.0f}/mo ({prob}%)"
        ):
            c1, c2 = st.columns(2)

            with c1:
                st.markdown(f"**Contact:** {deal.get('contact_name', 'N/A')}")
                st.markdown(f"**Email:** {deal.get('contact_email', 'N/A')}")
                st.markdown(f"**Phone:** {deal.get('contact_phone', 'N/A')}")
                if deal.get("website"):
                    st.markdown(f"**Website:** [{deal['website']}]({deal['website']})")
                st.markdown(f"**Industry:** {deal.get('industry', 'N/A')}")
                st.markdown(f"**City:** {deal.get('city', 'N/A')}")
                if deal.get("address"):
                    st.markdown(f"**Address:** {deal['address']}")
                if deal.get("business_hours"):
                    st.markdown(f"**Hours:** {format_hours(deal['business_hours'])}")
                st.markdown(f"**Source:** {deal.get('source', 'N/A')}")
                st.markdown(f"**Rep:** {deal.get('assigned_rep', 'N/A')}")

            with c2:
                _pkg = deal.get("tier_name") or "N/A"
                _label = "Package" if deal.get("pricing_mode") == "custom" else "Tier"
                st.markdown(f"**{_label}:** {_pkg} ({deal.get('screen_count', 0)} screens)")
                st.markdown(f"**Monthly:** ${float(deal.get('monthly_value') or 0):,.0f}/mo")
                if float(deal.get("one_time_value") or 0):
                    st.markdown(
                        f"**One-time fee:** ${float(deal['one_time_value']):,.0f} "
                        "(not counted as recurring)")
                if deal.get("term_months"):
                    st.markdown(
                        f"**Term:** {deal['term_months']} months - "
                        f"total ${total_contract_value(deal):,.0f}")
                st.markdown(f"**Expected Close:** {deal.get('expected_close_date', 'N/A')}")
                if deal.get("closed_date"):
                    _verb = "Won" if deal.get("stage") == "won" else "Lost"
                    st.markdown(f"**{_verb} on:** {str(deal['closed_date'])[:10]}")
                st.markdown(f"**Last Contact:** {(deal.get('last_contact_date') or 'Never')[:10]}")
                st.markdown(f"**Next Action:** {deal.get('next_action', 'None set')}")
                st.markdown(f"**Next Action Date:** {deal.get('next_action_date', 'N/A')}")

                nurture_seq = deal.get("nurture_sequence")
                if nurture_seq:
                    seq_info = get_available_sequences().get(nurture_seq, {})
                    st.markdown(f"**Nurture:** {seq_info.get('name', nurture_seq)} (Step {deal.get('nurture_step', 0)})")

            if deal.get("notes"):
                st.markdown(f"**Notes:** {deal['notes']}")

            # Actions
            st.markdown("---")
            a1, a2, a3, a4 = st.columns(4)

            with a1:
                stage_options = get_stage_options()
                _cur_stage_idx = [
                    i for i, (k, _) in enumerate(stage_options)
                    if k == deal.get("stage", "prospect")
                ]
                new_stage = st.selectbox(
                    "Move to Stage",
                    [label for _, label in stage_options],
                    index=_cur_stage_idx[0] if _cur_stage_idx else 0,
                    key=f"stage_{deal['id']}"
                )
                new_stage_key = [k for k, label in stage_options if label == new_stage][0]
                if new_stage_key != deal.get("stage"):
                    if st.button("Move", key=f"move_{deal['id']}", type="primary"):
                        # advance_stage returns None when the deal is gone
                        # (someone else deleted it); _run turns that into a
                        # visible error instead of a false "Moved to X".
                        if _run(advance_stage, deal["id"], new_stage_key,
                                performed_by=active_rep):
                            _sla = FOLLOW_UP_SLA.get(new_stage_key)
                            if _sla:
                                st.success(
                                    f"Moved to {new_stage}. Follow-up auto-scheduled: "
                                    f"{_sla['action']} in {_sla['days']} day(s)"
                                )
                            elif new_stage_key in CLOSED_STAGES:
                                st.success(
                                    f"Moved to {new_stage}, closed today. "
                                    "If it actually closed on a different day, "
                                    "set the date under Edit Deal."
                                )
                            else:
                                st.success(f"Moved to {new_stage}")
                            st.rerun()

            with a2:
                if deal.get("pricing_mode") == "custom":
                    # Never offer a tier dropdown on a hand-priced deal — one
                    # stray click would overwrite a negotiated package with a
                    # stock rate. Editing custom pricing happens in Edit Deal.
                    st.markdown("**Custom pricing**")
                    st.caption(
                        f"{deal.get('tier_name') or 'Custom package'}  \n"
                        f"${float(deal.get('monthly_value') or 0):,.0f}/mo"
                        + (f" + ${float(deal.get('one_time_value') or 0):,.0f} one-time"
                           if float(deal.get('one_time_value') or 0) else "")
                    )
                    st.caption("Change it under Edit Deal below.")
                else:
                    new_value = st.selectbox(
                        "Update Tier",
                        list(TIERS.keys()),
                        index=list(TIERS.keys()).index(deal.get("tier_name", "20 Screens"))
                        if deal.get("tier_name") in TIERS else 1,
                        key=f"tier_{deal['id']}"
                    )
                    if new_value != deal.get("tier_name"):
                        if st.button("Update", key=f"upd_tier_{deal['id']}"):
                            if _run(update_opportunity, deal["id"],
                                    tier_payload(new_value)):
                                st.success(f"Updated to {new_value}")
                                st.rerun()

            with a3:
                note_text = st.text_input("Add Note", key=f"note_{deal['id']}")
                if note_text:
                    if st.button("Save Note", key=f"save_note_{deal['id']}"):
                        log_note(deal["id"], note_text, performed_by=active_rep)
                        st.success("Note added")
                        st.rerun()

            with a4:
                if st.button("Log Call", key=f"call_{deal['id']}"):
                    log_call(deal["id"], performed_by=active_rep)
                    st.success("Call logged")
                    st.rerun()

                if deal.get("stage") != "lost":
                    loss_reason = st.text_input("Loss reason", key=f"loss_{deal['id']}")
                    st.caption(
                        "Only for deals you actually pitched and lost. "
                        "Duplicates and bad rows belong in **Cleanup**. "
                        "marking those Lost is what drags the win rate down."
                    )
                    if st.button("Mark Lost", key=f"lost_{deal['id']}"):
                        if _run(mark_lost, deal["id"], reason=loss_reason,
                                performed_by=active_rep):
                            st.warning("Marked as lost")
                            st.rerun()

            # Quick send — hand this deal off to the proposal/contract tools
            q1, q2, q3 = st.columns(3)
            with q1:
                if st.button("Draft Proposal →", key=f"prop_{deal['id']}"):
                    _extra = []
                    if deal.get("website"):
                        _extra.append(f"Website: {deal['website']}")
                    if deal.get("business_hours"):
                        _extra.append(f"Hours: {format_hours(deal['business_hours'])}")
                    if deal.get("notes"):
                        _extra.append(f"Pipeline notes: {deal['notes']}")
                    st.session_state["prefill_proposal"] = {
                        "business_name": deal.get("business_name", ""),
                        "industry": deal.get("industry", ""),
                        "city": deal.get("city", ""),
                        "contact_email": deal.get("contact_email", ""),
                        "sales_rep": deal.get("assigned_rep", active_rep),
                        "additional_notes": "\n".join(_extra),
                        "website_url": deal.get("website", ""),
                    }
                    log_event(deal["id"], "proposal_generated",
                              details="Proposal draft started from Pipeline",
                              performed_by=active_rep)
                    st.switch_page("pages/1_Proposals.py")
            with q2:
                if st.button("Create Contract →", key=f"contract_{deal['id']}"):
                    st.switch_page("pages/9_Contracts.py")
            with q3:
                if st.button("Send SMS →", key=f"sms_{deal['id']}"):
                    st.switch_page("pages/12_Messaging.py")

            # Edit deal — full contact/detail editing + website re-scan
            with st.expander("Edit Deal"):
                did = deal["id"]

                # ── Website re-scan (outside the form — buttons can't live in one)
                rc1, rc2 = st.columns([3, 1])
                rescan_url = rc1.text_input(
                    "Business Website",
                    value=deal.get("website") or "",
                    placeholder="www.example.com",
                    key=f"edit_web_{did}",
                )
                rc2.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
                if rc2.button("Scan Site", key=f"rescan_{did}"):
                    if not rescan_url.strip():
                        st.warning("Enter a website URL first.")
                    else:
                        with st.spinner("Scanning website for contact info, hours, and photos..."):
                            enr = enrich_from_website(rescan_url)
                        if enr.get("ok"):
                            st.session_state[f"enr_{did}"] = enr
                        else:
                            st.error(f"Scan failed: {enr.get('error') or 'no data found'}")
                        st.rerun()

                enr = st.session_state.get(f"enr_{did}")
                if enr:
                    merge = merge_enrichment(deal, enr)
                    updates, conflicts = merge["updates"], merge["conflicts"]

                    st.markdown("**Scan results**")
                    if updates:
                        st.markdown("Will fill these empty fields:")
                        for field, val in updates.items():
                            shown = format_hours(val) if field == "business_hours" else val
                            if isinstance(shown, list):
                                shown = ", ".join(str(v) for v in shown)
                            st.caption(f"• {field.replace('_', ' ').title()}: {shown}")
                    if conflicts:
                        st.markdown("Conflicts — check any you want to **overwrite**:")
                        for field, pair in conflicts.items():
                            cur, new = pair["current"], pair["new"]
                            if field == "business_hours":
                                cur, new = format_hours(cur), format_hours(new)
                            if isinstance(cur, list):
                                cur = ", ".join(str(v) for v in cur)
                            if isinstance(new, list):
                                new = ", ".join(str(v) for v in new)
                            st.checkbox(
                                f"{field.replace('_', ' ').title()}: `{cur}` → `{new}`",
                                key=f"conf_{did}_{field}",
                            )
                    if not updates and not conflicts:
                        st.caption("Nothing new found — deal already matches the website.")

                    scan_images = enr.get("images") or []
                    if scan_images:
                        st.markdown("**Photos found** — check any to save on this deal:")
                        icols = st.columns(4)
                        for i, img in enumerate(scan_images):
                            with icols[i % 4]:
                                st.image(img["url"], width='stretch')
                                st.checkbox(
                                    img.get("category", "photo"),
                                    value=i < 4,
                                    key=f"scanimg_{did}_{i}",
                                )

                    ap1, ap2 = st.columns([1, 1])
                    if ap1.button("Apply Scan Results", type="primary", key=f"apply_{did}"):
                        applied = dict(updates)
                        for field in conflicts:
                            if st.session_state.get(f"conf_{did}_{field}"):
                                applied[field] = conflicts[field]["new"]
                        applied["website"] = enr.get("website") or normalize_url(rescan_url)
                        selected_imgs = [
                            {"url": img["url"], "alt": img.get("alt", ""),
                             "category": img.get("category", "")}
                            for i, img in enumerate(scan_images)
                            if st.session_state.get(f"scanimg_{did}_{i}")
                        ]
                        if selected_imgs:
                            applied["website_images"] = selected_imgs
                        applied["enrichment"] = {
                            "pages_fetched": enr.get("pages_fetched", []),
                            "claude_used": enr.get("claude_used", False),
                            "scanned_at": datetime.now().isoformat(),
                        }
                        update_opportunity(did, applied)
                        log_event(did, "value_updated",
                                  details=f"Website scan applied: {', '.join(applied.keys())}",
                                  performed_by=active_rep)
                        del st.session_state[f"enr_{did}"]
                        st.success("Scan results applied!")
                        st.rerun()
                    if ap2.button("Discard Scan", key=f"discard_{did}"):
                        del st.session_state[f"enr_{did}"]
                        st.rerun()

                st.markdown("---")

                # ── Pricing (outside the form: the Tier/Custom switch has to
                #    react immediately, and form widgets don't rerun until submit)
                st.markdown("**Pricing**")
                e_pricing = render_pricing_inputs(f"editprice_{did}", deal)

                # ── Dates (outside the form for the same reason: whether a
                #    close date is even relevant depends on the stage picked)
                st.markdown("**Stage and dates**")
                d1, d2, d3 = st.columns(3)
                _stage_opts = get_stage_options()
                _stage_labels = [lbl for _, lbl in _stage_opts]
                _cur_i = [i for i, (k, _) in enumerate(_stage_opts)
                          if k == deal.get("stage")]
                e_stage_label = d1.selectbox(
                    "Stage", _stage_labels,
                    index=_cur_i[0] if _cur_i else 0,
                    key=f"editstage_{did}",
                )
                e_stage_key = next(k for k, lbl in _stage_opts if lbl == e_stage_label)

                _ecd = deal.get("expected_close_date")
                e_close = d2.date_input(
                    "Expected close",
                    value=date.fromisoformat(str(_ecd)[:10]) if _ecd else None,
                    key=f"editclose_{did}",
                )

                if e_stage_key in CLOSED_STAGES:
                    _cd = deal.get("closed_date")
                    e_closed_on = d3.date_input(
                        "Actually closed on",
                        value=date.fromisoformat(str(_cd)[:10]) if _cd else local_today(),
                        key=f"editclosed_{did}",
                        help="The real won/lost date. Reporting reads this, so "
                             "editing an old deal never re-dates the win into "
                             "this month.",
                    )
                else:
                    e_closed_on = None
                    d3.caption("Close date applies once the deal is won or lost.")

                x1, x2 = st.columns([1, 2])
                e_excluded = x1.checkbox(
                    "Leave out of stats",
                    value=bool(deal.get("excluded_from_stats")),
                    key=f"editexcl_{did}",
                    help="Keeps the deal on the board but drops it from win "
                         "rate, pipeline value and averages. For partnerships, "
                         "barters and placeholders that aren't real revenue.",
                )
                e_excl_reason = x2.text_input(
                    "Why it's excluded",
                    value=deal.get("exclusion_reason") or "",
                    placeholder="e.g. barter partnership, not advertiser revenue",
                    key=f"editexclwhy_{did}",
                    disabled=not e_excluded,
                )

                # ── Manual edit form
                with st.form(f"edit_form_{did}"):
                    e_name = st.text_input("Business Name", value=deal.get("business_name") or "")
                    e1, e2 = st.columns(2)
                    with e1:
                        e_contact = st.text_input("Contact Name", value=deal.get("contact_name") or "")
                        e_email = st.text_input("Contact Email", value=deal.get("contact_email") or "")
                        e_phone = st.text_input("Contact Phone", value=deal.get("contact_phone") or "")
                        e_industry = st.text_input("Industry", value=deal.get("industry") or "")
                        e_address = st.text_input("Address", value=deal.get("address") or "")
                    with e2:
                        e_city = st.text_input("City", value=deal.get("city") or "")
                        _reps = ["Mary Michael", "Creed", "Swayze"]
                        _rep_idx = _reps.index(deal["assigned_rep"]) if deal.get("assigned_rep") in _reps else 0
                        e_rep = st.selectbox("Assigned Rep", _reps, index=_rep_idx)
                        e_next = st.text_input("Next Action", value=deal.get("next_action") or "")
                        _nd = deal.get("next_action_date")
                        e_next_date = st.date_input(
                            "Next Action Date",
                            value=date.fromisoformat(str(_nd)[:10]) if _nd else local_today() + timedelta(days=3),
                        )
                    e_loss = st.text_input(
                        "Loss reason", value=deal.get("loss_reason") or "",
                        placeholder="Only used when the stage is Lost",
                    )
                    e_notes = st.text_area("Notes", value=deal.get("notes") or "")

                    save_edit = st.form_submit_button("Save Changes", type="primary")

                if save_edit:
                    _ok, _clean_name, _why = validate_business_name(e_name)
                    if not _ok:
                        st.error(f"{_why}.")
                    else:
                        _payload = {
                            "business_name": _clean_name,
                            "contact_name": e_contact,
                            "contact_email": e_email,
                            "contact_phone": e_phone,
                            "industry": e_industry,
                            "address": e_address,
                            "city": e_city,
                            "assigned_rep": e_rep,
                            "next_action": e_next,
                            "next_action_date": e_next_date.isoformat() if e_next_date else None,
                            "loss_reason": e_loss,
                            "notes": e_notes,
                            "expected_close_date": e_close.isoformat() if e_close else None,
                            "excluded_from_stats": e_excluded,
                            "exclusion_reason": e_excl_reason if e_excluded else None,
                            "website": normalize_url(st.session_state.get(f"edit_web_{did}", deal.get("website") or "")),
                        }
                        _payload.update(e_pricing)

                        # Stage changes go through advance_stage so probability,
                        # the SLA follow-up and the close date all stay in step.
                        _stage_moved = e_stage_key != deal.get("stage")
                        if e_stage_key in CLOSED_STAGES and e_closed_on:
                            _payload["closed_date"] = e_closed_on.isoformat()
                            _payload["next_action"] = None
                            _payload["next_action_date"] = None
                        elif e_stage_key not in CLOSED_STAGES:
                            _payload["closed_date"] = None

                        if _save_deal(_stage_moved, did, e_stage_key, _payload, active_rep):
                            st.rerun()

                # ── Danger zone: delete this deal outright ───────────────
                st.markdown("---")
                st.caption(
                    "A duplicate or a bad row is not a lost deal. Deleting it "
                    "keeps the win rate honest. Marking it Lost does not. "
                    "Deleted deals go to the Cleanup tab, where you can put "
                    "them back."
                )
                if st.button("Delete this deal", key=f"del_deals_{did}"):
                    st.session_state[f"confirm_delete_{did}"] = True

                if st.session_state.get(f"confirm_delete_{did}"):
                    st.warning(
                        f"Delete **{deal.get('business_name', 'this deal')}** "
                        f"and its {len(get_activity(did))} activity record(s)? "
                        "It moves to Recently deleted and can be restored."
                    )
                    _why_del = st.text_input(
                        "Reason (optional)", key=f"delwhy_deals_{did}",
                        placeholder="duplicate / junk row / test data",
                    )
                    dc1, dc2 = st.columns(2)
                    if dc1.button("Yes, delete it", key=f"yesdel_deals_{did}",
                                  type="primary", width='stretch'):
                        if _run(delete_opportunity, did, deleted_by=active_rep,
                                reason=_why_del or "Deleted from All Deals"):
                            del st.session_state[f"confirm_delete_{did}"]
                            st.rerun()
                    if dc2.button("Cancel", key=f"nodel_deals_{did}", width='stretch'):
                        del st.session_state[f"confirm_delete_{did}"]
                        st.rerun()

            # Activity history
            with st.expander("Activity History"):
                activities = get_activity(deal["id"])
                if activities:
                    for act in activities[:15]:
                        ts = (act.get("created_at") or "")[:16].replace("T", " ")
                        action = act.get("action", "")
                        details = act.get("details", "")
                        performer = act.get("performed_by", "")
                        st.caption(f"{ts} — **{action}** — {details} ({performer})")
                else:
                    st.caption("No activity yet")

    if _total > _shown:
        if st.button(f"Show {min(PAGE, _total - _shown)} more "
                     f"({_total - _shown} left)", key="deals_show_more"):
            st.session_state["deals_shown"] = _shown + PAGE
            st.rerun()
    elif _shown > PAGE:
        if st.button("Collapse the list", key="deals_show_less"):
            st.session_state["deals_shown"] = PAGE
            st.rerun()


# ── Tab 3: Add Deal ──────────────────────────────────────────────────────────

with tab_add:
    st.markdown("### Add New Opportunity")
    st.caption(
        "Tip: enter the business website and hit **Scan Website** first — "
        "contact info, hours, and photos fill in automatically."
    )

    # ── Website scan (outside the form so it can pre-fill it) ────────────
    sc1, sc2 = st.columns([3, 1])
    scan_url = sc1.text_input(
        "Business Website",
        placeholder="www.oxfordfloral.com",
        key="add_scan_url",
    )
    sc2.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
    if sc2.button("Scan Website", type="secondary", key="add_scan_btn"):
        if not scan_url.strip():
            st.warning("Enter a website URL to scan.")
        else:
            with st.spinner("Scanning website for contact info, hours, and photos..."):
                _enr = enrich_from_website(scan_url)
            if _enr.get("ok"):
                st.session_state["deal_enrichment"] = _enr
                st.rerun()
            else:
                st.session_state.pop("deal_enrichment", None)
                st.error(f"Could not scan that website: {_enr.get('error') or 'no data found'}")

    enr = st.session_state.get("deal_enrichment") or {}
    if enr:
        pages_n = len(enr.get("pages_fetched", []))
        st.success(
            f"Scanned {pages_n} page(s) on {enr.get('website', '')} — "
            "form pre-filled below. Review, adjust, then add."
        )
        with st.expander("What the scan found", expanded=False):
            if enr.get("description"):
                st.caption(enr["description"])
            if enr.get("business_hours"):
                st.markdown(f"**Hours:** {format_hours(enr['business_hours'])}")
            if enr.get("social_links"):
                st.markdown("**Social:** " + " • ".join(enr["social_links"][:5]))
            if enr.get("address"):
                st.markdown(f"**Address:** {enr['address']}")
        if st.button("Clear scan", key="add_clear_scan"):
            del st.session_state["deal_enrichment"]
            st.rerun()

    # Photos found — opt-in selection, saved on the deal for later use
    enr_images = enr.get("images") or []
    if enr_images:
        st.markdown("**Photos found** — check any to save with this prospect:")
        img_cols = st.columns(4)
        for i, img in enumerate(enr_images):
            with img_cols[i % 4]:
                st.image(img["url"], width='stretch')
                st.checkbox(
                    img.get("category", "photo"),
                    value=i < 4,
                    key=f"add_img_{i}",
                )

    # ── Pricing and dates sit OUTSIDE the form so the Tier/Custom switch and
    #    the "already closed" switch react as soon as you flip them.
    st.markdown("**Pricing**")
    add_pricing = render_pricing_inputs("addprice")

    st.markdown("**Stage and dates**")
    s1, s2 = st.columns([1, 1])
    stage = s1.selectbox(
        "Stage", [label for _, label in get_stage_options()], index=0,
        key="add_stage",
    )
    stage_key = next(k for k, label in get_stage_options() if label == stage)

    is_history = stage_key in CLOSED_STAGES
    if not is_history:
        is_history = s2.checkbox(
            "This is an old deal I'm entering after the fact",
            key="add_backdate",
            help="Log a deal that already happened so the historical numbers "
                 "are right. You set the dates instead of today's.",
        )
    else:
        s2.caption("Entering a won or lost deal. Set the real dates below.")

    if is_history:
        h1, h2 = st.columns(2)
        started_on = h1.date_input(
            "Deal started", value=local_today() - timedelta(days=60),
            key="add_started_on",
            help="When this deal actually entered the pipeline.",
        )
        if stage_key in CLOSED_STAGES:
            closed_on = h2.date_input(
                "Won / lost on", value=local_today(), key="add_closed_on",
                help="Reporting counts the deal in this month, not the month "
                     "you happen to type it in.",
            )
        else:
            closed_on = None
            h2.caption("Not closed yet, so no close date.")
    else:
        started_on = None
        closed_on = None

    with st.form("add_deal_form"):
        c1, c2 = st.columns(2)

        _cities = ["Oxford", "Starkville", "Tupelo", "Columbus", "West Point", "Other"]
        _enr_city = (enr.get("city") or "").strip().title()
        _city_idx = _cities.index(_enr_city) if _enr_city in _cities else 0

        # The scraped <title> is a poor name source ("Home | Brock Partners"
        # prefills as "Home"), so only use it when it survives validation.
        _prefill = ""
        if enr:
            _cand = (enr.get("title", "") or "").split("|")[0].split("–")[0].strip()
            _cand_ok, _cand_clean, _ = validate_business_name(_cand)
            _prefill = _cand_clean if _cand_ok else ""

        with c1:
            biz_name = st.text_input("Business Name *", value=_prefill)
            contact_name = st.text_input("Contact Name", value=enr.get("contact_name", ""))
            contact_email = st.text_input("Contact Email", value=enr.get("contact_email", ""))
            contact_phone = st.text_input("Contact Phone", value=enr.get("contact_phone", ""))
            industry = st.text_input("Industry", value=enr.get("industry", ""))
            address = st.text_input("Address", value=enr.get("address", ""))

        with c2:
            city = st.selectbox("City", _cities, index=_city_idx)
            source = st.selectbox("Source", ["manual", "intake_form", "prospector", "referral", "website", "cold_outreach"])
            close_date = st.date_input(
                "Expected Close Date",
                value=(closed_on or local_today()) if is_history
                else local_today() + timedelta(days=30),
            )
            loss_reason_new = st.text_input(
                "Loss reason", placeholder="Only used if the stage is Lost")

        notes = st.text_area("Notes", value=enr.get("description", ""))

        seq_options = {"None": None}
        seq_options.update({v["name"]: k for k, v in get_available_sequences().items()})
        nurture = st.selectbox("Start Nurture Sequence", list(seq_options.keys()))

        _rep_default = TEAM_REPS.index(active_rep) if active_rep in TEAM_REPS else 0
        assigned = st.selectbox("Assigned Rep", TEAM_REPS, index=_rep_default)

        submitted = st.form_submit_button("Add to Pipeline", type="primary")

        _name_ok, _name_clean, _name_why = (
            validate_business_name(biz_name) if submitted else (False, "", ""))

        if submitted and not _name_ok:
            st.warning(_name_why or "Business name is required")
        elif submitted:
            # Duplicate guard on the canonical key, so "Enterprise tupelo "
            # and "Enterprise Tupelo" are recognised as the same business.
            _existing = {normalize_name(o.get("business_name") or ""): o
                         for o in all_opps}
            _name_key = normalize_name(_name_clean)
            _match = _existing.get(_name_key)
            if _match and st.session_state.get("add_dup_ok") != _name_key:
                st.session_state["add_dup_ok"] = _name_key
                _mstage = STAGES.get(_match.get("stage", ""), {}).get(
                    "label", _match.get("stage"))
                st.warning(
                    f"**{_match.get('business_name')}** is already in the "
                    f"pipeline. {_mstage}, "
                    f"${float(_match.get('monthly_value') or 0):,.0f}/mo, "
                    f"{_match.get('assigned_rep') or 'no rep'}, added "
                    f"{str(_match.get('created_at'))[:10]}.  \n"
                    "Edit that one over in **All Deals**, or click **Add to "
                    "Pipeline** again to add this as a separate deal."
                )
            else:
                opp_payload = {
                    "business_name": _name_clean,
                    "contact_name": contact_name,
                    "contact_email": contact_email,
                    "contact_phone": contact_phone,
                    "industry": industry,
                    "address": address,
                    "city": city if city != "Other" else "",
                    "source": source,
                    "stage": stage_key,
                    "expected_close_date": close_date.isoformat(),
                    "notes": notes,
                    "assigned_rep": assigned,
                    "nurture_sequence": seq_options.get(nurture),
                    "loss_reason": loss_reason_new or None,
                }
                opp_payload.update(add_pricing)

                # Backdated entry: the deal's own dates, not today's.
                if started_on:
                    opp_payload["created_at"] = datetime.combine(
                        started_on, datetime.min.time()).isoformat()
                    opp_payload["stage_entered_at"] = opp_payload["created_at"]
                if closed_on:
                    opp_payload["closed_date"] = closed_on.isoformat()

                if enr:
                    opp_payload["website"] = enr.get("website") or normalize_url(scan_url)
                    if enr.get("business_hours"):
                        opp_payload["business_hours"] = enr["business_hours"]
                    if enr.get("social_links"):
                        opp_payload["social_links"] = enr["social_links"]
                    selected_imgs = [
                        {"url": img["url"], "alt": img.get("alt", ""),
                         "category": img.get("category", "")}
                        for i, img in enumerate(enr_images)
                        if st.session_state.get(f"add_img_{i}")
                    ]
                    if selected_imgs:
                        opp_payload["website_images"] = selected_imgs
                    opp_payload["enrichment"] = {
                        "pages_fetched": enr.get("pages_fetched", []),
                        "claude_used": enr.get("claude_used", False),
                        "scanned_at": datetime.now().isoformat(),
                    }
                elif scan_url.strip():
                    opp_payload["website"] = normalize_url(scan_url)

                # st.rerun() stays OUTSIDE the try — RerunException subclasses
                # Exception and would be swallowed as a bogus error.
                opp = None
                try:
                    opp = create_opportunity(opp_payload)
                except Exception as e:  # noqa: BLE001
                    st.error(f"Could not add the deal: {e}")

                if opp:
                    st.session_state.pop("deal_enrichment", None)
                    st.session_state.pop("add_dup_ok", None)
                    _when = (" (backdated to "
                             f"{started_on.isoformat()})" if started_on else "")
                    st.success(f"Added {_name_clean} to the pipeline{_when}.")
                    st.rerun()


# ── Tab 4: Cleanup ───────────────────────────────────────────────────────────

with tab_cleanup:
    st.markdown("### Clean up the pipeline")
    st.caption(
        "Duplicates and junk rows that got marked Lost drag the win rate down "
        "and inflate lost revenue. Deleting them is what makes the numbers "
        "true. Nothing here is permanent. Every delete lands in "
        "**Recently deleted** at the bottom of this tab."
    )

    _dupes = find_duplicate_groups(all_opps)
    _junk = find_junk_rows(all_opps)
    _junk_ids = {j["id"] for j in _junk}

    # ── What the cleanup is worth, before you do it ──────────────────────
    _won_now = [o for o in counted(all_opps) if o.get("stage") == "won"]
    _lost_now = [o for o in counted(all_opps) if o.get("stage") == "lost"]

    # Rows a full cleanup would remove: every junk row, plus every duplicate
    # past the first in each group.
    _removable = set(_junk_ids)
    for g in _dupes:
        for d in g["deals"][1:]:
            _removable.add(d["id"])
    _lost_after = [o for o in _lost_now if o["id"] not in _removable]
    _fake_lost = sum(float(o.get("monthly_value") or 0)
                     for o in _lost_now if o["id"] in _removable)

    _rate_now = (len(_won_now) / (len(_won_now) + len(_lost_now)) * 100
                 if (_won_now or _lost_now) else 0)
    _rate_after = (len(_won_now) / (len(_won_now) + len(_lost_after)) * 100
                   if (_won_now or _lost_after) else 0)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Duplicate groups", len(_dupes))
    m2.metric("Junk rows", len(_junk))
    m3.metric("Fake lost revenue", f"${_fake_lost:,.0f}/mo")
    m4.metric(
        "Win rate once clean", f"{_rate_after:.0f}%",
        delta=f"{_rate_after - _rate_now:+.0f} pts" if _removable else None,
        help=f"Reads {_rate_now:.0f}% today ({len(_won_now)} won vs "
             f"{len(_lost_now)} lost) because {len(_removable)} duplicate or "
             "junk row(s) count as real losses. This projection assumes you "
             "keep the furthest-along row in each duplicate group.",
    )

    st.divider()

    # ── Junk rows ────────────────────────────────────────────────────────
    st.markdown("#### Rows that don't look like businesses")
    if not _junk:
        st.success("No junk rows. Every deal has a real business name.")
    else:
        st.caption(
            "These came in through a paste that split one contact block into "
            "one deal per line. New deals are validated now, so this list "
            "should stay empty."
        )
        for j in _junk:
            jid = j["id"]
            jc1, jc2 = st.columns([4, 1])
            jc1.warning(
                f"**{j.get('business_name')}**  \n{j['_junk_reason']}  \n"
                f"{STAGES.get(j.get('stage', ''), {}).get('label', j.get('stage'))}"
                f" - ${float(j.get('monthly_value') or 0):,.0f}/mo"
                f" - added {str(j.get('created_at'))[:10]}"
            )
            if jc2.button("Delete", key=f"deljunk_{jid}", width='stretch'):
                st.session_state[f"confirm_junk_{jid}"] = True

            if st.session_state.get(f"confirm_junk_{jid}"):
                k1, k2 = st.columns(2)
                if k1.button("Confirm delete", key=f"yesjunk_{jid}",
                             type="primary", width='stretch'):
                    if _run(delete_opportunity, jid, deleted_by=active_rep,
                            reason=f"Junk row: {j['_junk_reason']}"):
                        del st.session_state[f"confirm_junk_{jid}"]
                        st.rerun()
                if k2.button("Keep it", key=f"nojunk_{jid}", width='stretch'):
                    del st.session_state[f"confirm_junk_{jid}"]
                    st.rerun()

        st.markdown("")
        if st.button(f"Delete all {len(_junk)} junk rows", key="deljunk_all"):
            st.session_state["confirm_junk_all"] = True
        if st.session_state.get("confirm_junk_all"):
            st.warning(f"Delete all {len(_junk)} rows listed above?")
            ja1, ja2 = st.columns(2)
            if ja1.button("Yes, delete them all", key="yesjunk_all",
                          type="primary", width='stretch'):
                _done = 0
                for j in _junk:
                    try:
                        if delete_opportunity(j["id"], deleted_by=active_rep,
                                              reason=f"Junk row: {j['_junk_reason']}"):
                            _done += 1
                    except Exception as e:  # noqa: BLE001
                        st.error(f"{j.get('business_name')}: {e}")
                st.session_state.pop("confirm_junk_all", None)
                st.success(f"Deleted {_done} junk row(s).")
                st.rerun()
            if ja2.button("Cancel", key="nojunk_all", width='stretch'):
                del st.session_state["confirm_junk_all"]
                st.rerun()

    st.divider()

    # ── Duplicates ───────────────────────────────────────────────────────
    st.markdown("#### Duplicates")
    if not _dupes:
        st.success("No duplicates. Every business appears once.")
    else:
        st.caption(
            "Pick the row that's right, then merge. Merging moves the other "
            "rows' call log and notes onto the one you keep, fills in any "
            "blanks from them, and deletes the extras. Nothing is lost "
            "except the double count."
        )

    for _gi, g in enumerate(_dupes):
        # Index-based key: two different groups could otherwise truncate to
        # the same string and collide.
        gkey = f"{_gi}_{g['key'].replace(' ', '_')[:24]}"
        flag = ", stages disagree" if g["has_conflict"] else ""
        with st.expander(f"**{g['name']}**: {len(g['deals'])} rows{flag}",
                         expanded=g["has_conflict"]):
            if g["has_conflict"]:
                st.warning(
                    "These rows are in different stages, so one of them is the "
                    "real outcome and the rest are stale copies. Keep the one "
                    "that actually happened."
                )

            _labels, _ids = [], []
            for d in g["deals"]:
                _st = STAGES.get(d.get("stage", ""), {}).get("label", d.get("stage"))
                _labels.append(
                    f"{_st} - ${float(d.get('monthly_value') or 0):,.0f}/mo"
                    f" - {d.get('assigned_rep') or 'no rep'}"
                    f" - added {str(d.get('created_at'))[:10]}"
                    f" - {len(get_activity(d['id']))} activity"
                )
                _ids.append(d["id"])

            keep_label = st.radio(
                "Keep this one", _labels, index=0, key=f"dupkeep_{gkey}",
            )
            keep_id = _ids[_labels.index(keep_label)]
            drop_ids = [i for i in _ids if i != keep_id]

            g1, g2 = st.columns(2)
            if g1.button(f"Merge the other {len(drop_ids)} into it",
                         key=f"dupmerge_{gkey}", type="primary", width='stretch'):
                if _run(merge_opportunities, keep_id, drop_ids,
                        performed_by=active_rep):
                    st.success(f"Merged {len(drop_ids)} duplicate(s) into one deal.")
                    st.rerun()
            if g2.button(f"Delete the other {len(drop_ids)}, don't merge",
                         key=f"dupdel_{gkey}", width='stretch'):
                _done = 0
                for i in drop_ids:
                    try:
                        if delete_opportunity(i, deleted_by=active_rep,
                                              reason=f"Duplicate of {g['name']}"):
                            _done += 1
                    except Exception as e:  # noqa: BLE001
                        st.error(str(e))
                st.success(f"Deleted {_done} duplicate(s).")
                st.rerun()

    st.divider()

    # ── Undo ─────────────────────────────────────────────────────────────
    st.markdown("#### Recently deleted")
    st.caption("Everything deleted from the pipeline lands here, with its "
               "activity history, until you clear it out for good.")

    _trash = get_deleted(limit=50)
    if not _trash:
        st.info("Nothing deleted yet.")
    for t in _trash:
        tid = t["id"]
        t1, t2, t3 = st.columns([4, 1, 1])
        t1.markdown(
            f"**{t.get('business_name')}**: "
            f"{STAGES.get(t.get('stage', ''), {}).get('label', t.get('stage') or '?')}"
            f" - ${float(t.get('monthly_value') or 0):,.0f}/mo  \n"
            f"<span style='font-size:0.8rem;color:#666'>"
            f"{t.get('deleted_reason') or 'no reason given'} - "
            f"deleted {str(t.get('deleted_at'))[:16].replace('T', ' ')} "
            f"by {t.get('deleted_by') or 'unknown'}</span>",
            unsafe_allow_html=True,
        )
        if t2.button("Restore", key=f"restore_{tid}", width='stretch'):
            if _run(restore_opportunity, tid, performed_by=active_rep):
                st.success(f"Restored {t.get('business_name')}.")
                st.rerun()
        if t3.button("Purge", key=f"purge_{tid}", width='stretch',
                     help="Delete permanently. This one cannot be undone."):
            st.session_state[f"confirm_purge_{tid}"] = True

        if st.session_state.get(f"confirm_purge_{tid}"):
            st.warning(f"Permanently erase **{t.get('business_name')}**? "
                       "There is no undo past this point.")
            p1, p2 = st.columns(2)
            if p1.button("Erase it", key=f"yespurge_{tid}", type="primary",
                         width='stretch'):
                if _run(purge_deleted, tid):
                    del st.session_state[f"confirm_purge_{tid}"]
                    st.rerun()
            if p2.button("Keep it", key=f"nopurge_{tid}", width='stretch'):
                del st.session_state[f"confirm_purge_{tid}"]
                st.rerun()


# ── Tab 5: Import Leads ──────────────────────────────────────────────────────

with tab_import:
    st.markdown("### Import Existing Leads into Pipeline")
    st.caption("Pull leads from your Incoming Leads page into the sales pipeline for tracking.")

    # Declared up front so the import runs AFTER the try block below. Running
    # it inside would put st.rerun() under `except Exception`, which catches
    # the RerunException and reports a successful import as an error.
    _do_import, selected = False, []

    try:
        from services.leads_service import get_all_leads, calculate_lead_score, get_score_label

        leads = get_all_leads()

        if not leads:
            st.info("No leads found. New leads come in through the intake form.")
        else:
            # Filter out leads already in pipeline
            existing_lead_ids = {o.get("lead_id") for o in all_opps if o.get("lead_id")}
            existing_names = {normalize_name(o.get("business_name") or "")
                              for o in all_opps}

            # ...and leads whose deal was deliberately deleted. Without this,
            # cleaning up a duplicate just makes it importable again and the
            # next import recreates it.
            _dead_names, _dead_leads = deleted_fingerprints()

            available = [
                l for l in leads
                if l.get("id") not in existing_lead_ids
                and l.get("id") not in _dead_leads
                and normalize_name(l.get("business_name") or "") not in existing_names
                and normalize_name(l.get("business_name") or "") not in _dead_names
                and l.get("status") != "closed"
            ]

            _suppressed = len([
                l for l in leads
                if l.get("id") in _dead_leads
                or normalize_name(l.get("business_name") or "") in _dead_names
            ])
            if _suppressed:
                st.caption(
                    f"{_suppressed} lead(s) hidden because their deal was "
                    "deleted on purpose. Restore it from the Cleanup tab if "
                    "that was a mistake."
                )

            if not available:
                st.success("All active leads are already in the pipeline!")
            else:
                st.caption(f"{len(available)} lead(s) available to import")

                # Select leads to import
                selected = []
                for lead in available:
                    score = calculate_lead_score(lead)
                    label, color = get_score_label(score)

                    checked = st.checkbox(
                        f"**{lead.get('business_name', 'Unknown')}** — "
                        f"{lead.get('contact_name', 'N/A')} — "
                        f"{lead.get('city', 'N/A')} — "
                        f"Score: {score} ({label})",
                        key=f"import_{lead.get('id', '')}"
                    )
                    if checked:
                        selected.append(lead)

                if selected:
                    _do_import = st.button(
                        f"Import {len(selected)} Lead(s) to Pipeline", type="primary")

    except Exception as e:
        st.error(f"Could not load leads: {e}")

    if _do_import:
        imported, rejected = 0, []
        for lead in selected:
            # A lead with a junk business name now raises instead of creating
            # another bad row. Catch per lead so one bad record cannot abort
            # the whole import half-way through.
            try:
                if import_lead_to_pipeline(lead):
                    imported += 1
            except Exception as e:  # noqa: BLE001
                rejected.append(f"{lead.get('business_name') or lead.get('id')}: {e}")
        for msg in rejected:
            st.warning(msg)
        if imported:
            st.success(f"Imported {imported} lead(s) into the pipeline.")
            st.rerun()
        elif not rejected:
            st.info("Nothing was imported.")


# ── Tab 5: Nurture Center ────────────────────────────────────────────────────

with tab_nurture:
    st.markdown("### Nurture Sequences")
    st.caption("Automated email and SMS drip campaigns to keep prospects warm.")

    # Show available sequences
    sequences = get_available_sequences()
    for seq_key, seq_info in sequences.items():
        with st.expander(f"**{seq_info['name']}** — {seq_info['description']}"):
            for step in seq_info["steps"]:
                icon = "email" if step["channel"] == "email" else "sms"
                st.markdown(
                    f"**Step {step['step']}** (Day {step['delay_days']}) — "
                    f"[{icon.upper()}] {step['description']}"
                )

    st.divider()

    # Opportunities with active nurture sequences
    st.markdown("### Active Nurture Campaigns")
    nurture_opps = [o for o in all_opps
                    if o.get("nurture_sequence") and o.get("stage") not in ("won", "lost")]

    if nurture_opps:
        for opp in nurture_opps:
            seq = sequences.get(opp.get("nurture_sequence"), {})
            total_steps = len(seq.get("steps", []))
            current_step = opp.get("nurture_step", 0)
            next = get_next_step(opp)

            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.markdown(
                    f"**{opp.get('business_name')}** — "
                    f"{seq.get('name', 'Unknown')} — "
                    f"Step {current_step}/{total_steps}"
                )
            with col2:
                if next:
                    st.caption(f"Next: {next.get('description', '')} ({next['channel'].upper()})")
                    if st.button("Send Now", key=f"send_{opp['id']}"):
                        result = send_nurture_step(opp, next)
                        if result["success"]:
                            st.success(f"Sent step {next['step']}!")
                            st.rerun()
                        else:
                            st.error(result.get("error", "Failed"))
                else:
                    if current_step >= total_steps:
                        st.caption("Sequence complete")
                    else:
                        st.caption("Waiting for next step...")
            with col3:
                if st.button("Stop", key=f"stop_{opp['id']}"):
                    stop_sequence(opp["id"])
                    st.info("Stopped nurture sequence")
                    st.rerun()
    else:
        st.info("No active nurture campaigns. Start one from the All Deals tab or when adding a new deal.")

    st.divider()

    # Batch send button
    st.markdown("### Batch Send")
    st.caption("Process all pending nurture steps across all opportunities.")
    if st.button("Run Nurture Batch", type="primary"):
        with st.spinner("Sending nurture messages..."):
            results = run_nurture_batch()
        if results:
            for r in results:
                status = "Sent" if r["success"] else f"Failed: {r['error']}"
                st.markdown(f"- **{r['business_name']}** — Step {r['step']} ({r['channel']}) — {status}")
        else:
            st.info("No pending nurture steps to send.")


# ── Tab 6: Revenue Forecast ──────────────────────────────────────────────────

with tab_forecast:
    st.markdown("### Revenue Forecast")
    st.caption(
        "Projected MRR from the weighted pipeline. Each month holds the deals "
        "whose expected close lands **in that month**. The three figures are "
        "three separate months, not a running total."
    )

    forecast = get_revenue_forecast(months=3, opps=all_opps)

    if forecast:
        cols = st.columns(len(forecast))
        for col, fc in zip(cols, forecast):
            with col:
                st.markdown(
                    f'<div class="forecast-card">'
                    f'<h3>${fc["expected_mrr"]:,.0f}/mo</h3>'
                    f'<p><strong>{fc["month"]}</strong></p>'
                    f'<p>Best case: ${fc["best_case"]:,.0f}/mo</p>'
                    f'<p>High confidence: ${fc["worst_case"]:,.0f}/mo</p>'
                    f'<p>{fc["deal_count"]} deal(s)</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # ── Open pipeline the forecast can't place ───────────────────────────
    _gaps = get_forecast_gaps(all_opps)
    if _gaps["undated"] or _gaps["overdue"]:
        st.markdown("#### Not in any month above")
        st.caption(
            "Real open pipeline the forecast can't place. These used to be "
            "invisible here. Undated deals were dropped and past-due ones "
            "were counted in every month at once."
        )
        gc1, gc2 = st.columns(2)
        with gc1:
            st.metric(
                "No close date set", f"${_gaps['undated_value']:,.0f}/mo",
                help=f"{len(_gaps['undated'])} open deal(s) with no expected "
                     "close date. Set one under Edit Deal to forecast them.")
            for o in _gaps["undated"][:8]:
                st.caption(f"- {o.get('business_name')} "
                           f"(${float(o.get('monthly_value') or 0):,.0f}/mo)")
            if len(_gaps["undated"]) > 8:
                st.caption(f"+{len(_gaps['undated']) - 8} more")
        with gc2:
            st.metric(
                "Close date already passed", f"${_gaps['overdue_value']:,.0f}/mo",
                help=f"{len(_gaps['overdue'])} open deal(s) whose expected "
                     "close date is in the past. Move the date or the stage.")
            for o in _gaps["overdue"][:8]:
                st.caption(f"- {o.get('business_name')} "
                           f"(due {str(o.get('expected_close_date'))[:10]})")
            if len(_gaps["overdue"]) > 8:
                st.caption(f"+{len(_gaps['overdue']) - 8} more")

    st.divider()

    # Pipeline stage breakdown
    st.markdown("### Pipeline by Stage")
    by_stage = summary["by_stage"]

    for stage_key in sorted(by_stage.keys(), key=lambda x: STAGES[x]["order"]):
        data = by_stage[stage_key]
        if data["count"] > 0:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            col1.markdown(f"**{data['label']}**")
            col2.markdown(f"{data['count']} deals")
            col3.markdown(f"${data['value']:,.0f}/mo")
            col4.markdown(f"${data['weighted_value']:,.0f} weighted")

    st.divider()

    # Won/Lost summary
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Won", summary["total_won"])
    c2.metric("Total Lost", summary["total_lost"])
    c3.metric("Avg Deal Size", f"${summary['avg_deal_size']:,.0f}/mo")


# ── Tab 7: Action Items ──────────────────────────────────────────────────────

with tab_actions:
    st.markdown("### Deals Needing Attention")
    st.caption(
        "The follow-up schedule is enforced automatically: every stage move "
        "schedules the next touch, and deals land here the moment they slip. "
        "Contact limits by stage — "
        + " • ".join(
            f"{STAGES[k]['label']}: {v['days']}d"
            for k, v in FOLLOW_UP_SLA.items()
        )
    )

    action_items = get_deals_needing_action(opps=all_opps)

    if action_items:
        for item in action_items:
            stage_info = STAGES.get(item.get("stage", "prospect"), STAGES["prospect"])
            value = float(item.get("monthly_value") or 0)
            reason = item.get("_action_reason", "")

            st.warning(
                f"**{item.get('business_name', 'Unknown')}** — "
                f"{stage_info['label']} — ${value:,.0f}/mo\n\n"
                f"{reason}"
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Log Call", key=f"action_call_{item['id']}"):
                    log_call(item["id"], performed_by=active_rep)
                    st.success("Call logged")
                    st.rerun()
            with c2:
                next_date = st.date_input(
                    "Set Follow-up",
                    value=date.today() + timedelta(days=3),
                    key=f"action_date_{item['id']}"
                )
                if st.button("Set", key=f"action_set_{item['id']}"):
                    update_opportunity(item["id"], {
                        "next_action_date": next_date.isoformat(),
                        "next_action": "Follow up",
                    })
                    st.success("Follow-up set")
                    st.rerun()
            with c3:
                if st.button("View Deal", key=f"action_view_{item['id']}"):
                    st.info(f"See the All Deals tab for details on {item.get('business_name')}")

    else:
        st.success("All caught up! No deals need immediate attention.")


# ── Tab 8: Rep Scoreboard ────────────────────────────────────────────────────

with tab_scoreboard:
    st.markdown("### Rep Scoreboard — Activity to Revenue")
    st.caption(
        "Accountability at a glance: every call, note, and stage move is "
        "attributed to the rep who did it (set **Working as** at the top of "
        "the page). Touches over the last 30 days are tied directly to "
        "revenue produced, so time spent working the pipeline shows up next "
        "to the dollars it generates."
    )

    scoreboard = get_rep_scoreboard(opps=all_opps, days=30)

    if not scoreboard:
        st.info("No pipeline data yet — add deals to see the scoreboard.")
    else:
        import pandas as pd

        df = pd.DataFrame([{
            "Rep": r["rep"],
            "Open Deals": r["open_deals"],
            "Pipeline $/mo": f"${r['pipeline_value']:,.0f}",
            "Weighted $/mo": f"${r['weighted_value']:,.0f}",
            "Overdue": r["overdue"],
            "No Follow-up": r["no_followup"],
            "Avg Days Since Touch": r["avg_days_since_touch"],
            "Touches (30d)": r["touches"],
            "Touches/Deal": r["touches_per_deal"],
            "MRR Won (Mo)": f"${r['mrr_won_month']:,.0f}",
            "$ Won per Touch": f"${r['revenue_per_touch']:,.2f}",
            "Win Rate": f"{r['win_rate']}%",
        } for r in scoreboard])
        st.dataframe(df, hide_index=True, width='stretch')

        # Accountability flags — slipping reps called out by name
        flagged = [r for r in scoreboard if r["overdue"] or r["no_followup"]]
        if flagged:
            st.markdown("#### Accountability Flags")
            for r in flagged:
                parts = []
                if r["overdue"]:
                    parts.append(f"{r['overdue']} overdue follow-up(s)")
                if r["no_followup"]:
                    parts.append(f"{r['no_followup']} deal(s) with no follow-up scheduled")
                st.warning(f"**{r['rep']}** — {' and '.join(parts)}. "
                           "See the Action Items tab to clear them.")
        else:
            st.success("Every open deal has a scheduled follow-up and nothing is overdue.")
