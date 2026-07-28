# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Loop Inventory — Streamlit page for the MCTV Team Member portal.

Four tabs:

    Screens     loop length per screen from the n-compass whitelist sweep
    Inventory   the manual book of record — what creative plays in each market,
                and the per-screen exceptions
    Reconcile   inventory vs the sweep, and inventory vs the Encompass /
                NTV360 play export
    Dark        playlist items whitelisted to zero screens

The sweep measures how long each screen's loop runs; the inventory says what
is in it. Reconcile is where the two meet.

Drop into: mctv-bot/pages/24_Loop_Inventory.py
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.loop_inventory_service import (
    TARGET_SECONDS,
    dark_content,
    dark_monthly_at_stake,
    latest_sweep_date,
    market_summary,
    screen_loops,
)
from services.screen_inventory_service import (
    BUCKETS,
    MARKETS,
    STATUSES,
    add_override,
    delete_item,
    delete_override,
    get_items,
    get_overrides,
    get_screens,
    get_venues,
    inventory_summary,
    mark_verified,
    market_label,
    mmss,
    reconcile_plays,
    reconcile_sweep,
    save_item,
    seed_from_plays,
    update_item,
)

st.set_page_config(
    page_title="Loop Inventory - MCTV Bot",
    page_icon="\U0001F4FA",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()


MARKET_LABELS = {"oxford": "Oxford", "tupelo": "Tupelo", "starkville": "Starkville"}

# Fields the bulk grid can edit, mapped to their display labels.
GRID_FIELDS = {
    "file_name": "Creative / file",
    "advertiser": "Advertiser",
    "bucket": "Type",
    "duration_seconds": "Seconds",
    "monthly_value": "$/mo",
    "status": "Status",
    "run_of_network": "All screens",
    "start_date": "Start",
    "end_date": "End",
    "notes": "Notes",
}


# ---------------------------------------------------------------------------
# Shared data — fetched once per rerun and passed into every tab
# ---------------------------------------------------------------------------

sweep = latest_sweep_date()
rows = screen_loops(sweep) if sweep else []
dark = dark_content()
at_stake = dark_monthly_at_stake(dark)
summary = market_summary(rows)

all_items = get_items()
all_overrides = get_overrides()
all_screens = get_screens()

st.markdown("## \U0001F4FA Loop Inventory")
st.caption(
    "What each screen plays and how long its loop runs. Sweep data is the "
    "measured side; the Inventory tab is the book of record you keep by hand. "
    f"Target: **{mmss(TARGET_SECONDS)}** (4 plays/hr)."
    + (f" Last sweep: **{sweep}**." if sweep else "")
)

tab_screens, tab_inventory, tab_reconcile, tab_dark = st.tabs(
    ["Screens", "Inventory", "Reconcile", "Dark content"]
)


# ---------------------------------------------------------------------------
# Tab 1 — Screens (measured loop length per screen)
# ---------------------------------------------------------------------------

with tab_screens:
    if not rows:
        st.info(
            "No sweep data yet. Run the per-screen whitelist sweep and load "
            "`screen_loops` (see the loop-inventory manifest in OneDrive)."
        )
    else:
        st.caption(
            "Per-screen **actual** loops from the n-compass whitelist sweep — a "
            "screen's real loop is the sum of playlist items whitelisted to its "
            "license, not the playlist total."
        )

        over_total = sum(1 for r in rows if r.get("over_target"))
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Screens swept", len(rows))
        k2.metric("Over 15:00 target", over_total,
                  delta=None if over_total == 0 else f"{over_total} to trim",
                  delta_color="inverse")
        k3.metric("Worst loop", mmss(max(r["loop_seconds"] for r in rows)))
        k4.metric("Dark-ad $ at stake", f"${at_stake:,.0f}/mo")

        st.divider()

        markets = [m for m in ("oxford", "tupelo", "starkville") if m in summary]
        markets += [m for m in summary if m not in markets]
        market_tabs = st.tabs([MARKET_LABELS.get(m, m.title()) for m in markets])

        for market_tab, market in zip(market_tabs, markets):
            with market_tab:
                s = summary[market]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Screens", s["screens"])
                c2.metric("Over target", s["over_target"])
                c3.metric("Avg loop", mmss(s["avg_seconds"]))
                c4.metric("Range", f"{mmss(s['min_seconds'])} – {mmss(s['max_seconds'])}")

                table = [
                    {
                        "Venue / screen": r["venue_name"],
                        "Loop": mmss(r["loop_seconds"]),
                        "Seconds": r["loop_seconds"],
                        "Items": r["item_count"],
                        "Over target": bool(r.get("over_target")),
                    }
                    for r in rows
                    if r["market"] == market
                ]
                st.dataframe(
                    table,
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "Seconds": st.column_config.ProgressColumn(
                            "vs 25:00", min_value=0, max_value=1500, format="%d",
                        ),
                        "Over target": st.column_config.CheckboxColumn(disabled=True),
                    },
                )
                if s["over_target"]:
                    st.caption(
                        f"{s['over_target']} screen(s) above {mmss(TARGET_SECONDS)} — "
                        "trim candidates (see the Oxford Phase-1 playbook)."
                    )
                else:
                    st.caption("All screens at or under target \U00002705")


# ---------------------------------------------------------------------------
# Tab 2 — Inventory (the manual book of record)
# ---------------------------------------------------------------------------

with tab_inventory:
    st.caption(
        "One row per creative in a market's loop. Items are **run-of-network** by "
        "default — they play on every screen in the market — and you record only "
        "the exceptions below. That mirrors how n-compass works (one playlist per "
        "market, whitelisted per license), so this stays a few dozen rows instead "
        "of a few thousand."
    )

    inv_market = st.radio(
        "Market",
        MARKETS,
        format_func=market_label,
        horizontal=True,
        key="inv_market",
    )
    working_by = st.session_state.get("active_rep", "")

    market_items = [i for i in all_items if (i.get("market") or "") == inv_market]
    stats = inventory_summary(market_items)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active items", stats["active"])
    m2.metric(
        "Base loop",
        mmss(stats["base_loop_seconds"]),
        delta=(
            None if stats["base_loop_seconds"] <= TARGET_SECONDS
            else f"+{mmss(stats['base_loop_seconds'] - TARGET_SECONDS)} over"
        ),
        delta_color="inverse",
        help="Total length of the run-of-network items — what a screen with no "
             "exceptions should be running.",
    )
    m3.metric("Paid revenue", f"${stats['monthly_value']:,.0f}/mo")
    m4.metric("Never verified", stats["unverified"],
              help="Active items nobody has confirmed against the portal yet.")

    if stats["base_loop_seconds"] > TARGET_SECONDS:
        st.warning(
            f"The run-of-network items alone total {mmss(stats['base_loop_seconds'])}, "
            f"over the {mmss(TARGET_SECONDS)} target. Every screen in "
            f"{market_label(inv_market)} is long before venue-specific items are added."
        )

    # ── Add a creative ──────────────────────────────────────────────────────
    with st.expander("\U00002795 Add a creative"):
        with st.form(f"add_item_{inv_market}", clear_on_submit=True):
            a1, a2 = st.columns(2)
            new_file = a1.text_input(
                "Creative / file name *",
                help="Spell it the way the Encompass portal does — this is what "
                     "the play export gets matched on.",
            )
            new_advertiser = a2.text_input("Advertiser")

            b1, b2, b3 = st.columns(3)
            new_bucket = b1.selectbox("Type", list(BUCKETS),
                                      format_func=lambda b: BUCKETS[b])
            new_seconds = b2.number_input("Length (seconds)", min_value=1,
                                          max_value=300, value=15, step=5)
            new_value = b3.number_input("$/mo (paid only)", min_value=0.0,
                                        value=0.0, step=25.0)

            c1, c2, c3 = st.columns(3)
            new_status = c1.selectbox("Status", STATUSES, index=0)
            new_start = c2.date_input("Start date", value=None)
            new_end = c3.date_input("End date", value=None)

            new_ron = st.checkbox(
                "Plays on every screen in this market", value=True,
                help="Leave on for a normal buy. Turn it off for a host promo or "
                     "venue-targeted spot, then add the screens below.",
            )
            new_notes = st.text_input("Notes")

            if st.form_submit_button("Add creative", type="primary"):
                if not new_file.strip():
                    st.error("A creative / file name is required.")
                else:
                    saved = save_item({
                        "market": inv_market,
                        "file_name": new_file,
                        "advertiser": new_advertiser,
                        "bucket": new_bucket,
                        "duration_seconds": new_seconds,
                        "monthly_value": new_value or None,
                        "status": new_status,
                        "run_of_network": new_ron,
                        "start_date": new_start,
                        "end_date": new_end,
                        "notes": new_notes,
                        "updated_by": working_by,
                    })
                    if saved:
                        st.success(f"Added {new_file}.")
                        st.rerun()
                    else:
                        st.error(
                            f"Could not add {new_file} — a creative with that "
                            f"name is already tracked in {market_label(inv_market)}."
                        )

    st.divider()

    # ── Bulk grid ───────────────────────────────────────────────────────────
    if not market_items:
        st.info(
            f"Nothing tracked in {market_label(inv_market)} yet. Add creatives "
            "above, or seed the list from a play export on the Reconcile tab."
        )
    else:
        st.markdown("#### Creatives in this market")
        st.caption("Edit in place, then save. Deleting a row here removes the creative.")

        grid_rows = []
        for item in market_items:
            grid_rows.append({
                "id": item.get("id"),
                "file_name": item.get("file_name") or "",
                "advertiser": item.get("advertiser") or "",
                "bucket": item.get("bucket") or "paid",
                "duration_seconds": int(item.get("duration_seconds") or 15),
                "monthly_value": float(item.get("monthly_value") or 0),
                "status": item.get("status") or "active",
                "run_of_network": bool(item.get("run_of_network")),
                "start_date": pd.to_datetime(item.get("start_date")).date()
                              if item.get("start_date") else None,
                "end_date": pd.to_datetime(item.get("end_date")).date()
                            if item.get("end_date") else None,
                "notes": item.get("notes") or "",
                "verified": item.get("verified_at") or "",
            })
        original = pd.DataFrame(grid_rows)

        edited = st.data_editor(
            original,
            width='stretch',
            hide_index=True,
            num_rows="dynamic",
            key=f"inv_grid_{inv_market}",
            column_config={
                "id": None,
                "file_name": st.column_config.TextColumn(
                    GRID_FIELDS["file_name"], required=True, width="medium"),
                "advertiser": st.column_config.TextColumn(GRID_FIELDS["advertiser"]),
                "bucket": st.column_config.SelectboxColumn(
                    GRID_FIELDS["bucket"], options=list(BUCKETS), required=True),
                "duration_seconds": st.column_config.NumberColumn(
                    GRID_FIELDS["duration_seconds"], min_value=1, max_value=300, step=5),
                "monthly_value": st.column_config.NumberColumn(
                    GRID_FIELDS["monthly_value"], format="$%.0f", min_value=0.0, step=25.0),
                "status": st.column_config.SelectboxColumn(
                    GRID_FIELDS["status"], options=STATUSES, required=True),
                "run_of_network": st.column_config.CheckboxColumn(
                    GRID_FIELDS["run_of_network"],
                    help="Plays on every screen in the market unless excluded below."),
                "start_date": st.column_config.DateColumn(GRID_FIELDS["start_date"]),
                "end_date": st.column_config.DateColumn(GRID_FIELDS["end_date"]),
                "notes": st.column_config.TextColumn(GRID_FIELDS["notes"], width="large"),
                "verified": st.column_config.TextColumn("Verified", disabled=True),
            },
        )

        if st.button("\U0001F4BE Save changes", type="primary", key=f"save_{inv_market}"):
            before = {str(r["id"]): r for r in grid_rows}
            after = edited.to_dict("records")
            seen_ids, created, updated, removed, errors = set(), 0, 0, 0, []

            for row in after:
                row_id = row.get("id")
                if not row_id or pd.isna(row_id):
                    # New row typed straight into the grid.
                    name = (row.get("file_name") or "").strip()
                    if not name:
                        continue
                    payload = {k: row.get(k) for k in GRID_FIELDS}
                    payload.update({
                        "market": inv_market,
                        "file_name": name,
                        "updated_by": working_by,
                    })
                    if save_item(payload):
                        created += 1
                    else:
                        errors.append(f"{name} is already tracked in this market.")
                    continue

                seen_ids.add(str(row_id))
                prior = before.get(str(row_id))
                if not prior:
                    continue
                changes = {}
                for field in GRID_FIELDS:
                    new_val, old_val = row.get(field), prior.get(field)
                    if pd.isna(new_val) if not isinstance(new_val, (bool, str)) else False:
                        new_val = None
                    if new_val != old_val:
                        changes[field] = new_val
                if changes:
                    changes["updated_by"] = working_by
                    if update_item(str(row_id), changes):
                        updated += 1
                    else:
                        errors.append(f"Could not update {prior['file_name']}.")

            for row_id, prior in before.items():
                if row_id not in seen_ids:
                    if delete_item(row_id):
                        removed += 1
                    else:
                        errors.append(f"Could not delete {prior['file_name']}.")

            parts = []
            if created:
                parts.append(f"{created} added")
            if updated:
                parts.append(f"{updated} updated")
            if removed:
                parts.append(f"{removed} removed")
            if parts:
                st.success(", ".join(parts).capitalize() + ".")
            elif not errors:
                st.info("No changes to save.")
            for err in errors:
                st.error(err)
            if parts:
                st.rerun()

        # ── Per-screen exceptions ───────────────────────────────────────────
        st.divider()
        st.markdown("#### Per-screen exceptions")
        st.caption(
            "**Exclude** pulls a run-of-network creative off one venue's screens "
            "(category exclusivity, a competitor's lobby). **Include** puts a "
            "non-run-of-network creative on specific screens (a host's own promo)."
        )

        item_lookup = {
            f"{i.get('advertiser') or i.get('file_name')} — {i.get('file_name')}": i
            for i in market_items
        }
        picked_label = st.selectbox("Creative", list(item_lookup),
                                    key=f"ovr_item_{inv_market}")
        picked = item_lookup[picked_label]
        picked_overrides = [o for o in all_overrides
                            if str(o.get("item_id")) == str(picked.get("id"))]

        venues = get_venues(market=inv_market)
        if not venues:
            st.info(
                "Venue names come from the latest whitelist sweep, and there is no "
                f"sweep for {market_label(inv_market)} yet. Run the sweep to enable "
                "per-screen exceptions."
            )
        else:
            o1, o2, o3 = st.columns([3, 2, 2])
            ovr_venue = o1.selectbox("Venue", venues, key=f"ovr_venue_{inv_market}")
            ovr_mode = o2.selectbox(
                "Rule", ["exclude", "include"],
                format_func=lambda m: "Does not play here" if m == "exclude"
                                      else "Plays here",
                key=f"ovr_mode_{inv_market}",
            )
            ovr_reason = o3.text_input("Reason", key=f"ovr_reason_{inv_market}")

            if st.button("Add exception", key=f"ovr_add_{inv_market}"):
                if add_override(picked["id"], ovr_venue, mode=ovr_mode,
                                reason=ovr_reason, created_by=working_by):
                    st.success(f"{picked['file_name']}: {ovr_mode} at {ovr_venue}.")
                    st.rerun()
                else:
                    st.error("Could not save that exception.")

        if picked_overrides:
            for override in picked_overrides:
                col_text, col_btn = st.columns([6, 1])
                verb = ("does not play at" if override.get("mode") == "exclude"
                        else "plays at")
                reason = f" — {override['reason']}" if override.get("reason") else ""
                col_text.write(f"• {verb} **{override.get('venue_name')}**{reason}")
                if col_btn.button("Remove", key=f"ovr_del_{override['id']}"):
                    delete_override(override["id"])
                    st.rerun()
        else:
            scope = ("every screen in the market"
                     if picked.get("run_of_network") else "no screens")
            st.caption(f"No exceptions — this creative plays on {scope}.")

        if st.button("\U00002714 Mark verified against the portal",
                     key=f"verify_{inv_market}"):
            if mark_verified(picked["id"], working_by):
                st.success(f"{picked['file_name']} marked verified today.")
                st.rerun()


# ---------------------------------------------------------------------------
# Tab 3 — Reconcile
# ---------------------------------------------------------------------------

with tab_reconcile:
    rec_market = st.radio(
        "Market",
        MARKETS,
        format_func=market_label,
        horizontal=True,
        key="rec_market",
    )
    rec_items = [i for i in all_items if (i.get("market") or "") == rec_market]
    rec_screens = [s for s in all_screens if (s.get("market") or "") == rec_market]

    sub_sweep, sub_plays = st.tabs(["vs whitelist sweep", "vs Encompass play export"])

    # ── Inventory vs sweep ──────────────────────────────────────────────────
    with sub_sweep:
        st.caption(
            "Does the loop you have on the books match the loop the sweep measured? "
            "A gap means either the portal changed without the book being updated, "
            "or a creative is on screens it shouldn't be."
        )

        if not rec_screens:
            st.info(f"No sweep data for {market_label(rec_market)} yet.")
        elif not rec_items:
            st.info(
                f"Nothing tracked in {market_label(rec_market)} yet — add creatives "
                "on the Inventory tab, or seed them from a play export below."
            )
        else:
            tolerance = st.slider(
                "Forgive a difference of up to this many items", 0, 5, 1,
                key="rec_tolerance",
                help="Small deltas are normal between sweeps. Raise this to see "
                     "only the screens that are genuinely out of line.",
            )
            variance = reconcile_sweep(rec_market, items=rec_items,
                                       overrides=all_overrides,
                                       screens=rec_screens, tolerance=tolerance)

            matches = sum(1 for v in variance if v["verdict"] == "match")
            untracked_screens = sum(1 for v in variance
                                    if v["verdict"] == "untracked_items")
            missing_screens = sum(1 for v in variance
                                  if v["verdict"] == "missing_from_screen")

            v1, v2, v3 = st.columns(3)
            v1.metric("Screens in line", f"{matches}/{len(variance)}")
            v2.metric("Running more than we track", untracked_screens,
                      delta=None if not untracked_screens else "investigate",
                      delta_color="inverse",
                      help="The sweep counted more items than the book expects.")
            v3.metric("Missing what we track", missing_screens,
                      delta=None if not missing_screens else "investigate",
                      delta_color="inverse",
                      help="The book expects more items than the sweep counted.")

            VERDICTS = {
                "match": "In line",
                "untracked_items": "Running more than tracked",
                "missing_from_screen": "Missing tracked items",
            }
            st.dataframe(
                [
                    {
                        "Venue / screen": v["venue_name"],
                        "Expected items": v["expected_count"],
                        "Swept items": v["actual_count"],
                        "Item gap": v["count_delta"],
                        "Expected loop": mmss(v["expected_seconds"]),
                        "Swept loop": mmss(v["actual_seconds"]),
                        "Verdict": VERDICTS.get(v["verdict"], v["verdict"]),
                    }
                    for v in variance
                ],
                width='stretch',
                hide_index=True,
                column_config={
                    "Item gap": st.column_config.NumberColumn(
                        help="Expected minus swept. Negative means the screen is "
                             "running items that aren't on the books."),
                    "Verdict": st.column_config.TextColumn(width="medium"),
                },
            )
            st.caption(
                f"Compared against the {sweep} sweep. Re-run the sweep after making "
                "portal changes, then check this again."
            )

    # ── Inventory vs play export ────────────────────────────────────────────
    with sub_plays:
        st.caption(
            "Upload the Encompass / NTV360 content export — the one with a row per "
            "creative per host. It answers the question the sweep can't: is what "
            "we booked actually airing?"
        )

        upload = st.file_uploader(
            "Play export (.xlsx)", type=["xlsx", "xlsm"], key="rec_upload",
        )

        if upload is not None:
            from services.excel_parser import parse_excel

            try:
                records = parse_excel(upload)
            except Exception as exc:
                records = []
                st.error(f"Could not read that file: {exc}")

            if records:
                result = reconcile_plays(records, rec_market, items=rec_items,
                                         overrides=all_overrides,
                                         screens=rec_screens)

                if not result["has_content_names"]:
                    st.warning(
                        "This export has host names but no creative names, so it "
                        "can only be matched at the venue level. Export the "
                        "**content report** from Encompass for a full check."
                    )

                p1, p2, p3, p4 = st.columns(4)
                p1.metric("Pairs confirmed airing",
                          f"{result['matched']}/{result['expected_pairs']}")
                p2.metric("Booked, not airing", len(result["not_airing"]),
                          delta=None if not result["not_airing"] else "chase",
                          delta_color="inverse")
                p3.metric("Airing, not tracked", len(result["untracked"]))
                p4.metric("Revenue at risk", f"${result['monthly_at_risk']:,.0f}/mo")

                if result["dark_items"]:
                    st.markdown("##### Tracked but playing nowhere")
                    st.caption(
                        "Active on the books, zero plays anywhere in this export. "
                        "Paid rows here are money going out the door."
                    )
                    st.dataframe(
                        [
                            {
                                "Advertiser": d.get("advertiser") or d["file_name"],
                                "Creative": d["file_name"],
                                "Type": d.get("bucket"),
                                "$/mo": d.get("monthly_value"),
                            }
                            for d in result["dark_items"]
                        ],
                        width='stretch', hide_index=True,
                        column_config={"$/mo": st.column_config.NumberColumn(format="$%d")},
                    )

                if result["not_airing"]:
                    st.markdown("##### Booked at a venue but not airing there")
                    st.dataframe(
                        [
                            {
                                "Venue": n["venue_name"],
                                "Advertiser": n.get("advertiser") or n["file_name"],
                                "Creative": n["file_name"],
                                "Type": n.get("bucket"),
                                "$/mo": n.get("monthly_value"),
                            }
                            for n in result["not_airing"]
                        ],
                        width='stretch', hide_index=True,
                        column_config={"$/mo": st.column_config.NumberColumn(format="$%d")},
                    )

                if result["untracked"]:
                    st.markdown("##### Airing but not on the books")
                    st.caption(
                        "Creatives with plays in the export that have no inventory "
                        "row. Add them so the loop math and revenue stay honest."
                    )
                    st.dataframe(
                        [
                            {"Creative": u["file_name"], "Plays": u["plays"],
                             "Venues": u["venues"]}
                            for u in result["untracked"]
                        ],
                        width='stretch', hide_index=True,
                    )

                    if st.button(
                        f"\U0001F4E5 Seed {len(result['untracked'])} creative(s) into "
                        f"{market_label(rec_market)}",
                        key="rec_seed",
                        help="Creates a pending, run-of-network row for each creative "
                             "in the export so you can correct the details by hand.",
                    ):
                        seeded = seed_from_plays(
                            records, rec_market,
                            created_by=st.session_state.get("active_rep", ""),
                        )
                        st.success(
                            f"Seeded {seeded['created']} creative(s); "
                            f"{seeded['skipped']} already tracked. Set each one's "
                            "advertiser, length, and status on the Inventory tab."
                        )
                        st.rerun()

                if (not result["dark_items"] and not result["not_airing"]
                        and not result["untracked"]):
                    st.success(
                        "Everything on the books is airing, and everything airing is "
                        "on the books \U00002705"
                    )

                st.caption(
                    f"Matched against {result['venues_in_export']} venue(s) in the "
                    "export. Venues missing from the export entirely are left out of "
                    "these counts — a screen that reported nothing is a screen-health "
                    "question, not an inventory error. Check the Screen Health page."
                )
            elif upload is not None:
                st.warning("No play records found in that file.")


# ---------------------------------------------------------------------------
# Tab 4 — Dark content
# ---------------------------------------------------------------------------

with tab_dark:
    st.markdown("### \U0001F573\U0000FE0F Dark content — in a playlist, playing nowhere")
    st.caption("From the whitelist sweep: items present in a playlist but "
               "whitelisted to zero licenses.")

    if not dark:
        st.success("No open dark-content findings.")
    else:
        paid_dark = [d for d in dark if d.get("bucket") == "paid"]
        if paid_dark:
            st.warning(
                f"**{len(paid_dark)} paid ad(s) not airing** — "
                f"${at_stake:,.0f}/mo at stake. Resolve in the portal "
                "(whitelist or remove) and update status here."
            )
        st.dataframe(
            [
                {
                    "Advertiser / item": d.get("advertiser") or d["file_name"],
                    "Market": MARKET_LABELS.get(d["market"], d["market"]),
                    "Type": d["bucket"],
                    "$/mo": d.get("monthly_value"),
                    "Status": d["status"],
                    "Finding": d.get("finding") or "",
                    "File": d["file_name"],
                }
                for d in dark
            ],
            width='stretch',
            hide_index=True,
            column_config={
                "$/mo": st.column_config.NumberColumn(format="$%d"),
                "Finding": st.column_config.TextColumn(width="large"),
            },
        )

st.caption(
    "Sources: `screen_loops` / `dark_content` from the n-compass whitelist sweep, "
    "and `loop_items` / `loop_item_screens` maintained by hand on the Inventory tab."
)
