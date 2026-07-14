# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Sales Pipeline Dashboard — visual pipeline management with revenue forecasting.

Provides a unified view of all opportunities moving through the sales process,
with stage tracking, deal management, nurture sequences, and revenue analytics.
"""

import streamlit as st
from datetime import date, timedelta

from services.auth import check_team_auth

if not check_team_auth():
    st.stop()


from services.team_ui import render_team_sidebar
render_team_sidebar()
from services.pipeline_service import (
    STAGES, TIERS,
    get_all_opportunities, get_opportunity, create_opportunity,
    update_opportunity, delete_opportunity, advance_stage, mark_lost,
    get_pipeline_summary, get_revenue_forecast, get_deals_needing_action,
    get_activity, log_note, log_call, import_lead_to_pipeline,
    get_stage_options,
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


# ── KPI Dashboard ─────────────────────────────────────────────────────────────

summary = get_pipeline_summary()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Active Deals", summary["total_opportunities"])
k2.metric("Pipeline Value", f"${summary['total_pipeline_value']:,.0f}/mo")
k3.metric("Weighted Value", f"${summary['weighted_pipeline_value']:,.0f}/mo")
k4.metric("Won This Month", f"${summary['mrr_won_this_month']:,.0f}/mo")
k5.metric("Win Rate", f"{summary['conversion_rate']:.0f}%")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_pipeline, tab_deals, tab_add, tab_import, tab_nurture, tab_forecast, tab_actions = st.tabs([
    "Pipeline View", "All Deals", "Add Deal", "Import Leads",
    "Nurture Center", "Forecast", "Action Items",
])


# ── Tab 1: Pipeline View ─────────────────────────────────────────────────────

with tab_pipeline:
    # Active stages only (exclude won/lost)
    active_stages = {k: v for k, v in STAGES.items() if k not in ("won", "lost")}

    cols = st.columns(len(active_stages))

    all_opps = get_all_opportunities()

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

    # Get filtered deals
    stage_filter = None
    if filter_stage != "All":
        stage_filter = [k for k, v in STAGES.items() if v["label"] == filter_stage]
        stage_filter = stage_filter[0] if stage_filter else None

    deals = get_all_opportunities(stage=stage_filter)

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
                st.markdown(f"**Industry:** {deal.get('industry', 'N/A')}")
                st.markdown(f"**City:** {deal.get('city', 'N/A')}")
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
                        advance_stage(deal["id"], new_stage_key)
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
                        log_note(deal["id"], note_text)
                        st.success("Note added")
                        st.rerun()

            with a4:
                if st.button("Log Call", key=f"call_{deal['id']}"):
                    log_call(deal["id"])
                    st.success("Call logged")
                    st.rerun()

                if deal.get("stage") != "lost":
                    loss_reason = st.text_input("Loss reason", key=f"loss_{deal['id']}")
                    if st.button("Mark Lost", key=f"lost_{deal['id']}"):
                        mark_lost(deal["id"], reason=loss_reason)
                        st.warning("Marked as lost")
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

    with st.form("add_deal_form"):
        c1, c2 = st.columns(2)

        with c1:
            biz_name = st.text_input("Business Name *")
            contact_name = st.text_input("Contact Name")
            contact_email = st.text_input("Contact Email")
            contact_phone = st.text_input("Contact Phone")
            industry = st.text_input("Industry")

        with c2:
            city = st.selectbox("City", ["Oxford", "Starkville", "Tupelo", "Columbus", "West Point", "Other"])
            source = st.selectbox("Source", ["manual", "intake_form", "prospector", "referral", "website", "cold_outreach"])
            tier = st.selectbox("Tier", list(TIERS.keys()), index=1)
            stage = st.selectbox("Initial Stage", [label for _, label in get_stage_options()], index=0)
            close_date = st.date_input("Expected Close Date", value=date.today() + timedelta(days=30))

        notes = st.text_area("Notes")

        seq_options = {"None": None}
        seq_options.update({v["name"]: k for k, v in get_available_sequences().items()})
        nurture = st.selectbox("Start Nurture Sequence", list(seq_options.keys()))

        assigned = st.selectbox("Assigned Rep", ["Mary Michael", "Creed", "Swayze"])

        submitted = st.form_submit_button("Add to Pipeline", type="primary")

        if submitted and biz_name:
            stage_key = [k for k, label in get_stage_options() if label == stage][0]
            tier_info = TIERS[tier]

            opp = create_opportunity({
                "business_name": biz_name,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "contact_phone": contact_phone,
                "industry": industry,
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
            })

            if opp:
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
            existing_opps = get_all_opportunities()
            existing_lead_ids = {o.get("lead_id") for o in existing_opps if o.get("lead_id")}

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
    nurture_opps = [o for o in get_all_opportunities()
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

    forecast = get_revenue_forecast(months=3)

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

    action_items = get_deals_needing_action()

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
                    log_call(item["id"])
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
