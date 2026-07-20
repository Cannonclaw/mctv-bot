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
    STAGES, TIERS, FOLLOW_UP_SLA,
    get_all_opportunities, get_opportunity, create_opportunity,
    update_opportunity, delete_opportunity, advance_stage, mark_lost,
    get_pipeline_summary, get_revenue_forecast, get_deals_needing_action,
    get_activity, log_note, log_call, log_event, import_lead_to_pipeline,
    get_stage_options, get_rep_scoreboard,
)
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
k4.metric("Won This Month", f"${summary['mrr_won_this_month']:,.0f}/mo")
k5.metric("Win Rate", f"{summary['conversion_rate']:.0f}%")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_pipeline, tab_deals, tab_add, tab_import, tab_nurture, tab_forecast, tab_actions, tab_scoreboard = st.tabs([
    "Pipeline View", "All Deals", "Add Deal", "Import Leads",
    "Nurture Center", "Forecast", "Action Items", "Rep Scoreboard",
])


# ── Tab 1: Pipeline View ─────────────────────────────────────────────────────

with tab_pipeline:
    # Active stages only (exclude won/lost)
    active_stages = {k: v for k, v in STAGES.items() if k not in ("won", "lost")}

    cols = st.columns(len(active_stages))

    for col, (stage_key, stage_info) in zip(cols, sorted(active_stages.items(), key=lambda x: x[1]["order"])):
        with col:
            stage_opps = [o for o in all_opps if o.get("stage") == stage_key]
            stage_value = sum(float(o.get("monthly_value", 0)) for o in stage_opps)

            st.markdown(
                f'<div class="stage-header" style="background:{stage_info["color"]}">'
                f'{stage_info["label"]} ({len(stage_opps)})<br>'
                f'<span style="font-size:0.75rem">${stage_value:,.0f}/mo</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            for opp in stage_opps[:10]:
                value = float(opp.get("monthly_value", 0))
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

    st.caption(f"Showing {len(deals)} deal(s)")

    for deal in deals:
        stage_info = STAGES.get(deal.get("stage", "prospect"), STAGES["prospect"])
        value = float(deal.get("monthly_value", 0))
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
                st.markdown(f"**Tier:** {deal.get('tier_name', 'N/A')} ({deal.get('screen_count', 0)} screens)")
                st.markdown(f"**Expected Close:** {deal.get('expected_close_date', 'N/A')}")
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
                        advance_stage(deal["id"], new_stage_key, performed_by=active_rep)
                        _sla = FOLLOW_UP_SLA.get(new_stage_key)
                        if _sla:
                            st.success(
                                f"Moved to {new_stage} — follow-up auto-scheduled: "
                                f"{_sla['action']} in {_sla['days']} day(s)"
                            )
                        else:
                            st.success(f"Moved to {new_stage}")
                        st.rerun()

            with a2:
                new_value = st.selectbox(
                    "Update Tier",
                    list(TIERS.keys()),
                    index=list(TIERS.keys()).index(deal.get("tier_name", "20 Screens"))
                    if deal.get("tier_name") in TIERS else 1,
                    key=f"tier_{deal['id']}"
                )
                if new_value != deal.get("tier_name"):
                    if st.button("Update", key=f"upd_tier_{deal['id']}"):
                        tier = TIERS[new_value]
                        update_opportunity(deal["id"], {
                            "tier_name": new_value,
                            "screen_count": tier["screens"],
                            "monthly_value": tier["monthly"],
                        })
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
                    if st.button("Mark Lost", key=f"lost_{deal['id']}"):
                        mark_lost(deal["id"], reason=loss_reason, performed_by=active_rep)
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

                # ── Manual edit form
                with st.form(f"edit_form_{did}"):
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
                            value=date.fromisoformat(_nd[:10]) if _nd else date.today() + timedelta(days=3),
                        )
                    e_notes = st.text_area("Notes", value=deal.get("notes") or "")

                    if st.form_submit_button("Save Changes", type="primary"):
                        update_opportunity(did, {
                            "contact_name": e_contact,
                            "contact_email": e_email,
                            "contact_phone": e_phone,
                            "industry": e_industry,
                            "address": e_address,
                            "city": e_city,
                            "assigned_rep": e_rep,
                            "next_action": e_next,
                            "next_action_date": e_next_date.isoformat(),
                            "notes": e_notes,
                            "website": normalize_url(st.session_state.get(f"edit_web_{did}", deal.get("website") or "")),
                        })
                        log_event(did, "value_updated", details="Deal details edited",
                                  performed_by=active_rep)
                        st.success("Deal updated!")
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

    with st.form("add_deal_form"):
        c1, c2 = st.columns(2)

        _cities = ["Oxford", "Starkville", "Tupelo", "Columbus", "West Point", "Other"]
        _enr_city = (enr.get("city") or "").strip().title()
        _city_idx = _cities.index(_enr_city) if _enr_city in _cities else 0

        with c1:
            biz_name = st.text_input("Business Name *", value=enr.get("title", "").split("|")[0].split("–")[0].strip() if enr else "")
            contact_name = st.text_input("Contact Name", value=enr.get("contact_name", ""))
            contact_email = st.text_input("Contact Email", value=enr.get("contact_email", ""))
            contact_phone = st.text_input("Contact Phone", value=enr.get("contact_phone", ""))
            industry = st.text_input("Industry", value=enr.get("industry", ""))
            address = st.text_input("Address", value=enr.get("address", ""))

        with c2:
            city = st.selectbox("City", _cities, index=_city_idx)
            source = st.selectbox("Source", ["manual", "intake_form", "prospector", "referral", "website", "cold_outreach"])
            tier = st.selectbox("Tier", list(TIERS.keys()), index=1)
            stage = st.selectbox("Initial Stage", [label for _, label in get_stage_options()], index=0)
            close_date = st.date_input("Expected Close Date", value=date.today() + timedelta(days=30))

        notes = st.text_area("Notes", value=enr.get("description", ""))

        seq_options = {"None": None}
        seq_options.update({v["name"]: k for k, v in get_available_sequences().items()})
        nurture = st.selectbox("Start Nurture Sequence", list(seq_options.keys()))

        _rep_default = TEAM_REPS.index(active_rep) if active_rep in TEAM_REPS else 0
        assigned = st.selectbox("Assigned Rep", TEAM_REPS, index=_rep_default)

        submitted = st.form_submit_button("Add to Pipeline", type="primary")

        if submitted and biz_name:
            # Duplicate guard: warn once, add on second submit
            _existing_names = {(o.get("business_name") or "").strip().lower() for o in all_opps}
            _name_key = biz_name.strip().lower()
            if _name_key in _existing_names and st.session_state.get("add_dup_ok") != _name_key:
                st.session_state["add_dup_ok"] = _name_key
                st.warning(
                    f"**{biz_name}** is already in the pipeline. "
                    "Click **Add to Pipeline** again to add it anyway."
                )
            else:
                stage_key = [k for k, label in get_stage_options() if label == stage][0]
                tier_info = TIERS[tier]

                opp_payload = {
                    "business_name": biz_name,
                    "contact_name": contact_name,
                    "contact_email": contact_email,
                    "contact_phone": contact_phone,
                    "industry": industry,
                    "address": address,
                    "city": city if city != "Other" else "",
                    "source": source,
                    "stage": stage_key,
                    "monthly_value": tier_info["monthly"],
                    "screen_count": tier_info["screens"],
                    "tier_name": tier,
                    "expected_close_date": close_date.isoformat(),
                    "notes": notes,
                    "assigned_rep": assigned,
                    "nurture_sequence": seq_options.get(nurture),
                }

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

                opp = create_opportunity(opp_payload)

                if opp:
                    st.session_state.pop("deal_enrichment", None)
                    st.session_state.pop("add_dup_ok", None)
                    st.success(f"Added {biz_name} to pipeline!")
                    st.rerun()
                else:
                    st.error("Failed to create opportunity")
        elif submitted:
            st.warning("Business name is required")


# ── Tab 4: Import Leads ──────────────────────────────────────────────────────

with tab_import:
    st.markdown("### Import Existing Leads into Pipeline")
    st.caption("Pull leads from your Incoming Leads page into the sales pipeline for tracking.")

    try:
        from services.leads_service import get_all_leads, calculate_lead_score, get_score_label

        leads = get_all_leads()

        if not leads:
            st.info("No leads found. New leads come in through the intake form.")
        else:
            # Filter out leads already in pipeline
            existing_lead_ids = {o.get("lead_id") for o in all_opps if o.get("lead_id")}

            available = [l for l in leads if l.get("id") not in existing_lead_ids
                        and l.get("status") != "closed"]

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
                    if st.button(f"Import {len(selected)} Lead(s) to Pipeline", type="primary"):
                        imported = 0
                        for lead in selected:
                            result = import_lead_to_pipeline(lead)
                            if result:
                                imported += 1
                        st.success(f"Imported {imported} lead(s) into the pipeline!")
                        st.rerun()

    except Exception as e:
        st.error(f"Could not load leads: {e}")


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
    st.caption("Projected MRR from weighted pipeline over the next 3 months.")

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
            value = float(item.get("monthly_value", 0))
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
