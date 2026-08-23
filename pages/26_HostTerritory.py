# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Host Territory Map — plan a new market before a rep ever drives it.

Three jobs, in the order a new territory gets worked:
  1. Read the map — which zone gets walked first, and why.
  2. Build a candidate list for a zone (typed in, or researched with Claude)
     and score every venue on host desirability.
  3. Push the winners into the host pipeline as 'identified' deals.

Scoring and the territory map live in ``services/host_territory_service``.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.config_service import load_config, get_team_first_names
from services.pipeline_service import create_opportunity, get_all_opportunities
from services.host_territory_service import (
    FACTORS, CATEGORY_BASELINES, GRADES,
    get_territory, get_zone, list_territories, list_zones,
    rank_candidates, research_prompt, to_host_pipeline_row,
)

st.set_page_config(
    page_title="Host Territory - MCTV Bot",
    page_icon="\U0001F5FA",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

st.markdown("## Host Territory Map")
st.caption(
    "Where to put screens in a new market, in what order, and which venues "
    "are worth the first knock."
)

cfg = load_config()
team_first = get_team_first_names(cfg) or ["Creed", "Mary Michael", "Swayze"]

territory = st.selectbox("Territory", list_territories())
terr = get_territory(territory)
st.info(terr.get("description", ""))

tab_map, tab_score, tab_find = st.tabs(
    ["Territory Zones", "Scoring Model", "Find & Score Hosts"]
)


# ── Tab 1: the map ───────────────────────────────────────────────────────────

with tab_map:
    st.markdown("### Zones, in walk order")
    st.caption(
        "Screens sell better in clusters than scattered across a metro. Work "
        "zone 1 until it has a sellable block of screens, then move down."
    )

    STATUS_BADGE = {
        "granted": ("GRANTED", "#2E8B57"),
        "granted-transition": ("GRANTED — INCUMBENT TRANSITION", "#C5A55A"),
        "verify-grant": ("VERIFY GRANT MAP", "#E89E3C"),
        "partner": ("PARTNER ZONE — NO DIRECT OUTREACH", "#722F37"),
        "future": ("FUTURE ASK", "#888888"),
    }
    for zone_name, info in list_zones(territory):
        badge, badge_color = STATUS_BADGE.get(
            info.get("status", "granted"), ("", "#888888"))
        with st.expander(
            f"**{info['priority']}. {zone_name}** — {info['profile']}",
            expanded=info["priority"] <= 2,
        ):
            if badge:
                st.markdown(
                    f"<span style='background:{badge_color};color:white;"
                    f"padding:2px 10px;border-radius:10px;font-size:0.75rem;"
                    f"font-weight:700'>{badge}</span>",
                    unsafe_allow_html=True,
                )
            demo = info.get("demographics") or {}
            if demo:
                st.caption(
                    f"{demo.get('population', '')}  ·  {demo.get('income', '')}"
                )
                if demo.get("note"):
                    st.caption(demo["note"])
            st.markdown(f"**Why here:** {info['why_first']}")
            st.markdown(f"**Anchors:** {', '.join(info.get('anchors', []))}")
            if info.get("target_categories"):
                st.markdown(
                    "**Best host categories:** "
                    + ", ".join(info.get("target_categories", []))
                )


# ── Tab 2: the rubric ────────────────────────────────────────────────────────

with tab_score:
    st.markdown("### What makes a venue worth a screen")
    st.caption(
        "Every candidate is scored 0-100 on these six factors. Dwell time "
        "carries the most weight because captive minutes are the product."
    )

    for key, meta in sorted(FACTORS.items(), key=lambda kv: -kv[1]["weight"]):
        c1, c2 = st.columns([1, 4])
        c1.metric(meta["label"], f"{meta['weight']}%")
        c2.write(meta["help"])
        c2.progress(meta["weight"] / 100)

    st.divider()
    st.markdown("### Grade bands")
    for floor, letter, action, color in GRADES:
        st.markdown(
            f"<span style='color:{color};font-weight:700'>{letter}</span> "
            f"&nbsp; {floor}+ &nbsp;—&nbsp; {action}",
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("### Category baselines")
    st.caption(
        "The starting rating for a venue we know nothing else about. A rep's "
        "own read on a specific venue always beats the baseline."
    )
    rows = []
    for cat, base in CATEGORY_BASELINES.items():
        scored = rank_candidates([{"business_name": cat, "category": cat}])[0]
        rows.append({
            "Category": cat,
            "Baseline score": scored["score"],
            "Grade": scored["grade"],
            **{FACTORS[k]["label"]: v for k, v in base.items()},
        })
    rows.sort(key=lambda r: r["Baseline score"], reverse=True)
    st.dataframe(rows, use_container_width=True, hide_index=True)


# ── Tab 3: build and score a candidate list ──────────────────────────────────

with tab_find:
    # Only buildable zones get prospecting — partner and future zones are
    # off-limits for host outreach by design.
    zone_names = [z for z, info in list_zones(territory)
                  if info.get("status", "granted") not in ("partner", "future")]
    c1, c2, c3 = st.columns(3)
    zone = c1.selectbox("Zone", zone_names, key="terr_zone")
    zone_info = get_zone(territory, zone)
    cats = zone_info.get("target_categories") or list(CATEGORY_BASELINES.keys())
    category = c2.selectbox(
        "Venue category",
        cats + [c for c in CATEGORY_BASELINES if c not in cats],
        key="terr_cat",
    )
    rep = c3.selectbox("Assign to rep", team_first, key="terr_rep")

    st.caption(zone_info.get("why_first", ""))

    gen_c1, gen_c2 = st.columns([1, 2])
    count = gen_c1.slider("How many to research", 5, 25, 10, key="terr_count")

    if gen_c2.button("Research host candidates with AI", type="primary"):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.error("Claude API key not configured. Set ANTHROPIC_API_KEY in .env")
        else:
            with st.spinner(f"Researching {category} venues in {zone}..."):
                try:
                    body = json.dumps({
                        "model": "claude-sonnet-5",
                        "max_tokens": 4000,
                        "messages": [{
                            "role": "user",
                            "content": research_prompt(territory, zone, category, count),
                        }],
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        "https://api.anthropic.com/v1/messages",
                        data=body,
                        headers={
                            "x-api-key": api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        result = json.loads(resp.read().decode("utf-8"))

                    blocks = result.get("content", []) or []
                    text = "".join(
                        b.get("text", "") for b in blocks if isinstance(b, dict)
                    ).strip()

                    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
                    if fence:
                        candidate_json = fence.group(1).strip()
                    else:
                        arr = re.search(r"\[.*\]", text, re.DOTALL)
                        candidate_json = arr.group(0) if arr else text

                    try:
                        parsed = json.loads(candidate_json) if candidate_json else []
                    except json.JSONDecodeError:
                        parsed = []
                    if isinstance(parsed, dict):
                        parsed = parsed.get("venues") or next(
                            (v for v in parsed.values() if isinstance(v, list)), []
                        )

                    found = []
                    for item in parsed if isinstance(parsed, list) else []:
                        if not isinstance(item, dict):
                            continue
                        # The model rates three factors directly; the rest of
                        # the score comes from the category baseline.
                        ratings = {
                            k: item.get(k) for k in ("dwell", "traffic", "install_ease")
                            if isinstance(item.get(k), (int, float))
                        }
                        found.append({**item, "category": category,
                                      "city": zone, "ratings": ratings})

                    if found:
                        st.session_state["territory_candidates"] = found
                        st.session_state["territory_meta"] = {
                            "territory": territory, "zone": zone,
                            "category": category, "rep": rep,
                        }
                        st.success(f"Found {len(found)} candidate venues.")
                    else:
                        st.warning("No candidates came back. Try again.")
                        with st.expander("Show raw AI response (debug)"):
                            st.code((text or "(empty response)")[:2000])
                except Exception as e:
                    st.error(f"Research failed: {e}")

    with st.expander("Or paste venues by hand (one per line)"):
        pasted = st.text_area(
            "Venue names", height=120,
            placeholder="Poplar Tire & Auto\nSaddle Creek Barber Co.",
            key="terr_paste",
        )
        if st.button("Score pasted venues", key="terr_paste_btn"):
            names = [n.strip() for n in pasted.splitlines() if n.strip()]
            if names:
                st.session_state["territory_candidates"] = [
                    {"business_name": n, "category": category, "city": zone}
                    for n in names
                ]
                st.session_state["territory_meta"] = {
                    "territory": territory, "zone": zone,
                    "category": category, "rep": rep,
                }
                st.rerun()

    # ── Ranked results ──────────────────────────────────────────────────────
    if st.session_state.get("territory_candidates"):
        meta = st.session_state.get("territory_meta", {})
        ranked = rank_candidates(st.session_state["territory_candidates"])

        st.divider()
        st.markdown(
            f"### Ranked host targets — {meta.get('category', '')} in "
            f"{meta.get('zone', '')}"
        )

        existing = get_all_opportunities(deal_type="host")
        existing_names = {(o.get("business_name") or "").lower() for o in existing}

        selected = []
        for i, cand in enumerate(ranked):
            name = cand.get("business_name", "Unknown")
            already = name.lower() in existing_names
            label = (
                f"**{name}** — {cand['score']}/100 "
                f"(grade {cand['grade']} · {cand['action']})"
            )
            if already:
                label += " (already in host pipeline)"

            checked = st.checkbox(
                label, key=f"terr_cand_{i}",
                value=not already and cand["grade"] in ("A", "B"),
                disabled=already,
            )
            detail = [d for d in (
                cand.get("address"), cand.get("dwell_note"), cand.get("why"),
            ) if d]
            if detail:
                st.caption(" | ".join(detail))

            if checked and not already:
                selected.append(cand)

        if selected:
            st.markdown(f"**{len(selected)} selected**")
            if st.button(f"Add {len(selected)} to Host Pipeline", type="primary"):
                added = 0
                for cand in selected:
                    row = to_host_pipeline_row(
                        cand,
                        meta.get("territory", territory),
                        meta.get("zone", zone),
                        meta.get("rep", rep),
                    )
                    if create_opportunity(row):
                        added += 1
                st.success(
                    f"Added {added} venue(s) to the host pipeline as "
                    f"'Identified'. Work them on the Host Pipeline page."
                )
                del st.session_state["territory_candidates"]
                st.rerun()

        if st.button("Clear list", key="terr_clear"):
            del st.session_state["territory_candidates"]
            st.rerun()
