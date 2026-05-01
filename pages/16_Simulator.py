# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Audience & Package Simulator (internal sales tool).

Pick host venues, see live impressions/plays/CPM, audience demographics, and
generate a shareable link the prospect can open after the sales call.
"""

import sys
from pathlib import Path

import folium
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.simulator_service import (
    build_scenario,
    list_recent_scenarios,
    list_venues,
    save_scenario,
)

# ── Category color palette (matches MCTV brand) ──────────────────────────────
CATEGORY_COLORS = {
    "Bar/Restaurant":              "#E89E3C",
    "Coffee/Donut/Bagel Shop":     "#A0522D",
    "Barbershop/Salon":            "#C48D78",
    "Health & Fitness":            "#2E8B57",
    "Medical":                     "#4682B4",
    "Retail":                      "#9370DB",
    "Gas/ Grocery":                "#708090",
    "Liquor/Wine/Beer Store":      "#722F37",
    "Family Rec & Entertainment":  "#FF6B6B",
    "Professional Services":       "#1B1F3B",
    "Travel & Tourism":            "#5F9EA0",
    "Education":                   "#8B0000",
    "Non Profit, Community, Government": "#556B2F",
    "Auto Shop/Auto Dealer/Oil Change":  "#2F4F4F",
    "Other":                       "#888888",
}

CITY_CENTERS = {
    "Oxford":     (34.366, -89.519),
    "Starkville": (33.450, -88.819),
    "Tupelo":     (34.258, -88.703),
    "Columbus":   (33.495, -88.427),
    "West Point": (33.608, -88.650),
}

st.set_page_config(
    page_title="Simulator - MCTV Bot",
    page_icon="\U0001F4CA",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

st.markdown("## Audience & Package Simulator")
st.caption("Build a custom monthly package for a prospect. Pick venues, see live impressions, plays, CPM, and audience demographics. Share with one click.")

# ── State ────────────────────────────────────────────────────────────────────

if "sim_selected" not in st.session_state:
    st.session_state.sim_selected = []
if "sim_custom_rate" not in st.session_state:
    st.session_state.sim_custom_rate = 0.0


# ── Venue picker (sidebar) ───────────────────────────────────────────────────

VENUES = list_venues()
ALL_CITIES = sorted({v["city"] for v in VENUES if v["city"]})
ALL_CATEGORIES = sorted({v["general_category"] for v in VENUES if v["general_category"]})

with st.sidebar:
    st.markdown("### Filters")
    city_filter = st.multiselect("City", ALL_CITIES, default=[], key="sim_city_filter")
    cat_filter = st.multiselect("Category", ALL_CATEGORIES, default=[], key="sim_cat_filter")
    min_traffic = st.slider("Min monthly traffic", 0, 30000, 0, step=500, key="sim_min_traffic")

    st.markdown("---")
    st.markdown("### Bulk select")
    bulk_cols = st.columns(2)
    if bulk_cols[0].button("All filtered", width="stretch", key="sim_bulk_all"):
        filtered_keys = [
            v["key"] for v in VENUES
            if (not city_filter or v["city"] in city_filter)
            and (not cat_filter or v["general_category"] in cat_filter)
            and v["traffic"] >= min_traffic
        ]
        st.session_state.sim_selected = filtered_keys
        st.rerun()
    if bulk_cols[1].button("Clear", width="stretch", key="sim_bulk_clear"):
        st.session_state.sim_selected = []
        st.rerun()

    st.markdown("---")
    st.markdown("### Recent scenarios")
    recent = list_recent_scenarios(limit=8)
    if recent:
        for r in recent:
            label = r.get("prospect_business") or r.get("prospect_name", "(unnamed)")
            views = r.get("view_count", 0)
            st.caption(f"{label} — {views} views")
    else:
        st.caption("No saved scenarios yet.")


# ── Filter venues ────────────────────────────────────────────────────────────

def _filter_venues():
    return [
        v for v in VENUES
        if (not city_filter or v["city"] in city_filter)
        and (not cat_filter or v["general_category"] in cat_filter)
        and v["traffic"] >= min_traffic
    ]


visible = _filter_venues()

st.markdown(f"**{len(visible)} of {len(VENUES)} venues** match your filters · "
            f"**{len(st.session_state.sim_selected)} selected**")


# ── Interactive map ──────────────────────────────────────────────────────────

def _build_picker_map(venues_to_show, selected_keys):
    """Folium map with one marker per venue. Selected = gold star, else colored dot."""
    plotted = [v for v in venues_to_show if v["lat"] and v["lon"]]
    if plotted:
        avg_lat = sum(v["lat"] for v in plotted) / len(plotted)
        avg_lon = sum(v["lon"] for v in plotted) / len(plotted)
        zoom = 10 if len({v["city"] for v in plotted}) > 1 else 13
    else:
        avg_lat, avg_lon, zoom = 34.30, -89.20, 8

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=zoom, tiles="cartodbpositron")

    for v in plotted:
        is_sel = v["key"] in selected_keys
        color = "#C5A55A" if is_sel else CATEGORY_COLORS.get(v["general_category"], "#888")
        radius = 11 if is_sel else 7
        weight = 3 if is_sel else 1
        popup_html = (
            f"<div style='font-family:Arial; min-width:220px;'>"
            f"<b>{v['host_name']}</b><br>"
            f"<span style='color:#888;'>{v['general_category']} &middot; {v['city']}</span><br><br>"
            f"Traffic: {int(v['traffic']):,}/mo<br>"
            f"Dwell: {v['dwell_time']:.0f} min<br>"
            f"Screens: {v['license_count']}<br>"
            f"Impressions: {int(v['impressions']):,}/mo<br><br>"
            f"<i>Click marker to toggle selection</i>"
            f"</div>"
        )
        folium.CircleMarker(
            location=[v["lat"], v["lon"]],
            radius=radius,
            color="#070707" if is_sel else color,
            weight=weight,
            fill=True,
            fill_color=color,
            fill_opacity=0.85 if is_sel else 0.6,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"{v['host_name']} ({v['general_category']})"
                   + ("  ✓" if is_sel else ""),
        ).add_to(m)
    return m


with st.expander("Map view (click markers to add/remove)", expanded=True):
    map_obj = _build_picker_map(visible, set(st.session_state.sim_selected))
    map_state = st_folium(
        map_obj,
        width=None,
        height=520,
        returned_objects=["last_object_clicked", "last_object_clicked_tooltip"],
        key="sim_map",
    )

    # When a marker is clicked, st_folium sets last_object_clicked to its lat/lon.
    # Match it to a venue and toggle selection.
    clicked = (map_state or {}).get("last_object_clicked")
    if clicked and "lat" in clicked and "lng" in clicked:
        lat, lon = round(clicked["lat"], 6), round(clicked["lng"], 6)
        last_handled = st.session_state.get("sim_last_click")
        if last_handled != (lat, lon):
            for v in visible:
                if abs(v["lat"] - lat) < 0.0001 and abs(v["lon"] - lon) < 0.0001:
                    sel = set(st.session_state.sim_selected)
                    if v["key"] in sel:
                        sel.discard(v["key"])
                    else:
                        sel.add(v["key"])
                    st.session_state.sim_selected = sorted(sel)
                    st.session_state.sim_last_click = (lat, lon)
                    st.rerun()

    # Tiny legend
    legend_html = " &nbsp; ".join(
        f"<span style='color:{c};font-weight:bold;'>●</span> {name.split(',')[0]}"
        for name, c in CATEGORY_COLORS.items()
        if any(v["general_category"] == name for v in visible)
    )
    st.markdown(
        f"<div style='font-size:0.85rem; padding:0.4rem 0;'>"
        f"<span style='color:#C5A55A;font-weight:bold;'>★</span> Selected &nbsp; {legend_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Venue table with checkboxes ──────────────────────────────────────────────

with st.expander("Pick venues", expanded=True):
    # Render in chunks so the page stays responsive
    sel = set(st.session_state.sim_selected)
    cols_per_row = 3
    for i in range(0, len(visible), cols_per_row):
        row = st.columns(cols_per_row)
        for j, v in enumerate(visible[i:i + cols_per_row]):
            with row[j]:
                checked = st.checkbox(
                    f"**{v['host_name']}**",
                    value=v["key"] in sel,
                    key=f"sim_pick_{v['key']}",
                    help=f"{v['category']} · {v['address']}",
                )
                st.caption(
                    f"{v['city']} · {v['general_category']} · "
                    f"{int(v['traffic']):,}/mo traffic · {v['license_count']} screen(s)"
                )
                if checked:
                    sel.add(v["key"])
                else:
                    sel.discard(v["key"])
    st.session_state.sim_selected = sorted(sel)


# ── Build scenario ───────────────────────────────────────────────────────────

if not st.session_state.sim_selected:
    st.info("Select one or more venues above to see the scenario.")
    st.stop()

with st.spinner("Building scenario..."):
    result = build_scenario(
        venue_keys=st.session_state.sim_selected,
        custom_monthly_rate=st.session_state.sim_custom_rate,
    )


# ── Headline metrics ─────────────────────────────────────────────────────────

m = st.columns(5)
m[0].metric("Screens", f"{result.total_screens:,}")
m[1].metric("Monthly Impressions", f"{int(result.total_monthly_impressions):,}")
m[2].metric("Monthly Plays", f"{result.total_monthly_plays:,}")
m[3].metric("Monthly Foot Traffic", f"{int(result.total_monthly_traffic):,}")
m[4].metric("Cities", len(result.cities))

st.divider()


# ── Recommended package ──────────────────────────────────────────────────────

st.markdown("### Recommended Monthly Package")

rec = result.recommendation
pkg_cols = st.columns([2, 1, 1, 1])

with pkg_cols[0]:
    st.markdown(f"**Tier:** {rec.tier_name or 'Custom'}")
    st.markdown(f"**Plays/month label:** {rec.plays_per_month_label or '—'}")

pkg_cols[1].metric("Tier base rate", f"${rec.monthly_rate:,.0f}/mo")
pkg_cols[2].metric("Effective rate", f"${rec.effective_rate:,.0f}/mo")
pkg_cols[3].metric("CPM", f"${rec.cpm:,.2f}")

# Custom override
override = st.number_input(
    "Custom monthly rate (override) — 0 = use tier base",
    min_value=0.0,
    max_value=10_000.0,
    value=float(st.session_state.sim_custom_rate),
    step=25.0,
    key="sim_custom_rate_input",
)
if override != st.session_state.sim_custom_rate:
    st.session_state.sim_custom_rate = override
    st.rerun()

st.divider()


# ── Demographics ─────────────────────────────────────────────────────────────

st.markdown("### Audience Profile (impression-weighted blend)")

blend = result.blend
if blend.median_household_income_blended:
    st.caption(
        f"Blended median household income: ${blend.median_household_income_blended:,} · "
        f"Cities: {', '.join(blend.cities_covered) or '—'}"
    )

dcol1, dcol2, dcol3 = st.columns(3)

AGE_LABELS = {
    "under_18": "Under 18", "18_24": "18-24", "25_34": "25-34",
    "35_44": "35-44", "45_54": "45-54", "55_64": "55-64", "65_plus": "65+",
}
INCOME_LABELS = {
    "under_35k": "<$35K", "35k_50k": "$35-50K", "50k_75k": "$50-75K",
    "75k_100k": "$75-100K", "100k_150k": "$100-150K", "over_150k": "$150K+",
}
EDU_LABELS = {
    "high_school_or_less": "HS or less", "some_college": "Some college",
    "bachelors": "Bachelor's", "graduate": "Graduate",
}


def _bar_chart(title: str, data: dict, label_map: dict):
    st.markdown(f"**{title}**")
    if not data or sum(data.values()) == 0:
        st.caption("Demographic data unavailable.")
        return
    rows = [{"Segment": label_map.get(k, k), "%": v} for k, v in data.items()]
    st.bar_chart(rows, x="Segment", y="%", height=240)


with dcol1:
    _bar_chart("Age", blend.age_pct, AGE_LABELS)
with dcol2:
    _bar_chart("Household Income", blend.income_pct, INCOME_LABELS)
with dcol3:
    _bar_chart("Education", blend.education_pct, EDU_LABELS)

if blend.audience_tags:
    st.markdown("**Audience tags:** " + " · ".join(f"`{t}`" for t in blend.audience_tags))

st.divider()


# ── Per-venue breakdown ──────────────────────────────────────────────────────

with st.expander("Per-venue breakdown", expanded=False):
    rows = [{
        "Venue": v.host_name,
        "City": v.city,
        "Category": v.general_category,
        "Screens": v.license_count,
        "Traffic": int(v.monthly_traffic),
        "Dwell (min)": round(v.dwell_time_minutes, 1),
        "Impressions": int(v.monthly_impressions),
        "Plays": v.monthly_plays,
        "Plays src": v.plays_source,
        "ZIP": v.zip_code,
    } for v in result.venues]
    st.dataframe(rows, width="stretch", hide_index=True)


# ── Save & share ─────────────────────────────────────────────────────────────

st.markdown("### Save & Share")

with st.form("sim_save_form"):
    sc = st.columns(3)
    p_business = sc[0].text_input(
        "Prospect business name *",
        value=st.session_state.get("sim_prefill_business", ""),
    )
    p_name = sc[1].text_input(
        "Contact name *",
        value=st.session_state.get("sim_prefill_contact", ""),
    )
    p_email = sc[2].text_input(
        "Contact email",
        value=st.session_state.get("sim_prefill_email", ""),
    )

    sc2 = st.columns(3)
    p_phone = sc2[0].text_input(
        "Contact phone",
        value=st.session_state.get("sim_prefill_phone", ""),
    )
    rep = sc2[1].text_input("Assigned rep")
    notes = sc2[2].text_input(
        "Notes",
        value=st.session_state.get("sim_prefill_notes", ""),
    )

    submitted = st.form_submit_button("Save & Generate Share Link", type="primary")

if submitted:
    if not p_business or not p_name:
        st.error("Prospect business name and contact name are required.")
    else:
        with st.spinner("Saving..."):
            saved = save_scenario(
                prospect_name=p_name,
                prospect_email=p_email,
                prospect_phone=p_phone,
                prospect_business=p_business,
                venue_keys=st.session_state.sim_selected,
                result=result,
                custom_monthly_rate=st.session_state.sim_custom_rate,
                created_by=st.session_state.get("team_user", ""),
                assigned_rep=rep,
                notes=notes,
            )
        if not saved:
            st.error("Could not save scenario. Check Supabase configuration.")
        else:
            token = saved.get("share_token", "")
            import os as _os
            base_url = _os.environ.get("PORTAL_URL", "https://bot.mctvofms.com").rstrip("/")
            share_url = f"{base_url}/portal_simulator?token={token}"
            st.success("Scenario saved.")
            st.code(share_url, language=None)
            st.caption("Send this link to the prospect. The view tracks open count.")

st.divider()


# ── AI Ad Concept Brief ──────────────────────────────────────────────────────

st.markdown("### Ad Concept Brief")
st.caption(
    "Generate a 1-page creative brief Claude writes from this scenario. "
    "Hand it to your designer, your AI ad tool, or send it to the prospect "
    "as proof you understand their audience."
)

with st.expander("Generate ad concept brief", expanded=False):
    bcol1, bcol2 = st.columns(2)
    brief_business = bcol1.text_input(
        "Business name *",
        value=st.session_state.get("sim_prefill_business", ""),
        key="brief_business",
    )
    brief_industry = bcol2.text_input(
        "Industry *",
        value=st.session_state.get("sim_prefill_industry", ""),
        placeholder="Restaurant, Salon, Law Firm",
        key="brief_industry",
    )

    brief_goal = st.selectbox(
        "Primary goal",
        ["Drive foot traffic",
         "Build brand awareness",
         "Promote a launch / event",
         "Move existing inventory / promo",
         "Recruit / hire",
         "Other"],
        key="brief_goal",
    )

    brief_constraints = st.text_area(
        "Anything we MUST include or AVOID? (optional)",
        placeholder="e.g. must include the dog (mascot), avoid using competitor names, "
                    "reference Ole Miss home games",
        height=80,
        key="brief_constraints",
    )

    if st.button("Generate Brief", type="primary", key="brief_btn",
                 disabled=not (brief_business and brief_industry)):
        import os as _os
        api_key = _os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key or api_key == "your-api-key-here":
            st.error("ANTHROPIC_API_KEY not configured.")
        else:
            # Pull demographic blend + venue category mix to feed the prompt
            blend = result.blend
            top_age = max(blend.age_pct.items(), key=lambda kv: kv[1]) if blend.age_pct else ("?", 0)
            top_income = max(blend.income_pct.items(), key=lambda kv: kv[1]) if blend.income_pct else ("?", 0)
            top_edu = max(blend.education_pct.items(), key=lambda kv: kv[1]) if blend.education_pct else ("?", 0)
            cats = sorted({v.general_category for v in result.venues})
            tags = blend.audience_tags or []
            cities = ", ".join(result.cities) or "Oxford"

            BRIEF_PROMPT = f"""You write 1-page creative briefs for advertisers
running on MCTV's indoor digital billboard network. Output is a brief, not a
finished ad — it's what a designer or AI ad tool needs to do their job.

Voice: practical, confident, no marketing fluff. Short paragraphs.

Length: 280-360 words across the structured sections below. Use ONLY these
section headers, exactly as written, on their own lines:

THE BUSINESS
THE GOAL
THE AUDIENCE
THE MESSAGE
THE TONE
THE CALL TO ACTION
THE CREATIVE DIRECTION
SCREENS THAT WILL CARRY IT

CONTEXT
=======
Business: {brief_business}
Industry: {brief_industry}
Goal: {brief_goal}
Cities: {cities}
Total screens: {result.total_screens}
Monthly impressions: ~{int(result.total_monthly_impressions):,}
Venue categories the ad will run in: {', '.join(cats) or 'mixed'}

Audience profile (impression-weighted blend across selected venues):
- Top age band: {top_age[0]} ({top_age[1]}%)
- Top income band: {top_income[0]} ({top_income[1]}%)
- Top education: {top_edu[0]} ({top_edu[1]}%)
- Audience signals: {', '.join(tags) or '(none)'}
- Blended median household income: ${blend.median_household_income_blended:,}

Constraints / must-include / must-avoid:
{brief_constraints or '(none specified)'}

KEY GUIDANCE FOR THE BRIEF
- Indoor billboard ads are silent. No audio. Big visual + 6-10 words on screen.
- Dwell times average 30-60 minutes — viewers see the ad multiple times.
- Aspect ratio: 1920x1080 landscape.
- The CTA must be readable from across a room. Phone numbers and short URLs
  work; long URLs don't.

WRITE THE BRIEF
"""
            try:
                import anthropic
                claude = anthropic.Anthropic(api_key=api_key)
                with st.spinner("Writing brief..."):
                    resp = claude.messages.create(
                        model="claude-sonnet-4-5-20250929",
                        max_tokens=1500,
                        messages=[{"role": "user", "content": BRIEF_PROMPT}],
                    )
                    brief_text = resp.content[0].text
                st.session_state["sim_ad_brief"] = brief_text
            except Exception as e:
                st.error(f"Generation failed: {e}")

    if st.session_state.get("sim_ad_brief"):
        st.markdown("---")
        st.markdown(st.session_state["sim_ad_brief"])
        st.download_button(
            "Download brief (.txt)",
            data=st.session_state["sim_ad_brief"],
            file_name=f"{(brief_business or 'ad').replace(' ', '_')}_creative_brief.txt",
            mime="text/plain",
            key="sim_brief_dl",
        )


# ── AI Ad Copy Generator ─────────────────────────────────────────────────────

st.markdown("### Ad Copy Generator")
st.caption(
    "Generates 3 ready-to-render ad concepts: headline (6-10 words), "
    "sub-line, visual direction, and a short CTA. Optimized for silent "
    "1920\u00D71080 billboard slots with 30-60 minute dwell. Drop straight "
    "into Creatomate or hand to your designer."
)

with st.expander("Generate ad copy", expanded=False):
    cw_col1, cw_col2 = st.columns(2)
    cw_business = cw_col1.text_input(
        "Business name *",
        value=st.session_state.get("sim_prefill_business", ""),
        key="cw_business",
    )
    cw_industry = cw_col2.text_input(
        "Industry *",
        value=st.session_state.get("sim_prefill_industry", ""),
        placeholder="Restaurant, Salon, Law Firm",
        key="cw_industry",
    )

    cw_offer = st.text_input(
        "What's the offer / promise / hook? *",
        placeholder="e.g. 'Lunch combo $9.99', 'Free consultation', "
                    "'New location now open'",
        key="cw_offer",
    )

    cw_col3, cw_col4 = st.columns(2)
    cw_cta_type = cw_col3.selectbox(
        "Primary CTA",
        ["Phone number", "Short URL / domain", "Visit-in-person",
         "QR code (we'll generate visual)", "Social handle"],
        key="cw_cta_type",
    )
    cw_cta_value = cw_col4.text_input(
        "CTA value",
        placeholder="(601) 201-8202  /  yoursite.com  /  @youraccount",
        key="cw_cta_value",
    )

    cw_tone = st.select_slider(
        "Tone",
        options=["Plain-spoken", "Friendly", "Confident", "Bold",
                 "Sophisticated", "Playful"],
        value="Confident",
        key="cw_tone",
    )

    cw_constraints = st.text_area(
        "Must include / must avoid (optional)",
        placeholder="e.g. must include 'Hotty Toddy', avoid promotional "
                    "claims like 'best in town'",
        height=70,
        key="cw_constraints",
    )

    if st.button("Generate 3 Ad Concepts", type="primary",
                 key="cw_btn",
                 disabled=not (cw_business and cw_industry and cw_offer)):
        import os as _os
        api_key = _os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key or api_key == "your-api-key-here":
            st.error("ANTHROPIC_API_KEY not configured.")
        else:
            blend = result.blend
            top_age = max(blend.age_pct.items(), key=lambda kv: kv[1]) if blend.age_pct else ("?", 0)
            tags = ", ".join(blend.audience_tags or []) or "general audience"
            cities = ", ".join(result.cities) or "Oxford"

            COPY_PROMPT = f"""You are a senior copywriter for indoor digital
billboard ads on the MCTV network in North Mississippi. Generate exactly
THREE distinct ad concepts for the brief below.

CRITICAL CONSTRAINTS — every concept must satisfy these:
- Format: 1920\u00D71080 landscape, SILENT (no audio), seen across a room
- Headline: 6-10 words MAX, scannable from across a room, no jargon
- Sub-line: 0-7 words, optional supporting line
- Visual direction: 1-2 sentences describing the imagery (NOT a finished ad,
  just direction for the designer). Avoid generic stock-photo cliches.
- CTA: short, readable from 20 feet — phone, URL, or social handle
- No long URLs (cap at ~20 chars). No tiny print. No claims a business
  owner couldn't honestly make.
- Each of the 3 concepts must take a DIFFERENT angle (e.g. urgency vs
  curiosity vs social proof vs benefit).

THE BRIEF
=========
Business: {cw_business}
Industry: {cw_industry}
Offer / hook: {cw_offer}
CTA type: {cw_cta_type}
CTA value: {cw_cta_value}
Tone: {cw_tone}
Cities running in: {cities}
Top audience age: {top_age[0]} ({top_age[1]}%)
Audience tags: {tags}
Must include / avoid: {cw_constraints or '(none specified)'}

OUTPUT (return EXACTLY this JSON, no markdown fences, no commentary):
{{
  "concepts": [
    {{
      "angle": "<one-word angle e.g. urgency, curiosity, social-proof, benefit, identity>",
      "headline": "<6-10 word headline>",
      "subline": "<0-7 word supporting line, or empty string>",
      "visual_direction": "<1-2 sentences>",
      "cta": "<final CTA text, exactly as it should appear on screen>",
      "color_mood": "<2-4 words, e.g. 'warm + earthy', 'cool blues, gold accents'>",
      "rationale": "<one sentence on why this hooks the target audience>"
    }},
    ...3 total...
  ]
}}
"""
            try:
                import anthropic, json as _json
                claude = anthropic.Anthropic(api_key=api_key)
                with st.spinner("Writing copy..."):
                    resp = claude.messages.create(
                        model="claude-sonnet-4-5-20250929",
                        max_tokens=2000,
                        messages=[{"role": "user", "content": COPY_PROMPT}],
                    )
                    raw = resp.content[0].text.strip()
                    if raw.startswith("```"):
                        raw = raw.split("```", 2)[1]
                        if raw.startswith("json"):
                            raw = raw[4:]
                        raw = raw.strip()
                    parsed = _json.loads(raw)
                st.session_state["sim_ad_copy"] = parsed
            except _json.JSONDecodeError as e:
                st.error(f"Could not parse Claude's response as JSON: {e}")
                st.code(raw[:1500] if 'raw' in dir() else "(no output)")
            except Exception as e:
                st.error(f"Generation failed: {e}")

    copy_data = st.session_state.get("sim_ad_copy")
    if copy_data and copy_data.get("concepts"):
        st.markdown("---")
        for i, concept in enumerate(copy_data["concepts"], 1):
            st.markdown(
                f"#### Concept {i} — *{concept.get('angle', 'angle').title()}*"
            )
            st.markdown(
                f"<div style='background:#1B1F3B; color:white; padding:1.5rem; "
                f"border-radius:8px; text-align:center; margin:0.5rem 0;'>"
                f"<div style='color:#C5A55A; font-size:2rem; font-weight:bold; "
                f"line-height:1.2;'>{concept.get('headline', '')}</div>"
                + (f"<div style='color:#e8e8e8; font-size:1.1rem; margin-top:0.5rem;'>"
                   f"{concept['subline']}</div>" if concept.get('subline') else "")
                + f"<div style='color:#C5A55A; font-size:1.1rem; margin-top:1rem; "
                f"font-weight:bold;'>{concept.get('cta', '')}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            cc1, cc2 = st.columns(2)
            cc1.markdown(f"**Visual:** {concept.get('visual_direction', '')}")
            cc2.markdown(f"**Mood:** {concept.get('color_mood', '')}")
            st.caption(f"_Rationale:_ {concept.get('rationale', '')}")
            st.divider()

        # Download all three as a single text file
        import json as _json2
        full_text = _json2.dumps(copy_data, indent=2)
        st.download_button(
            "Download all 3 concepts (.json)",
            data=full_text,
            file_name=f"{(cw_business or 'ad').replace(' ', '_')}_ad_copy.json",
            mime="application/json",
            key="cw_dl",
        )

st.divider()


# ── Generate Elite Advertiser proposal PDF from this scenario ────────────────

st.markdown("### Generate Proposal PDF")
st.caption(
    "Pull this scenario straight into the Elite Advertiser proposal generator. "
    "Pre-fills business name, markets, recommended tier, and custom rate from above."
)

with st.expander("Generate proposal", expanded=False):
    from services.config_service import get_team_first_names
    _cfg_for_proposal = __import__("services.config_service", fromlist=["load_config"]).load_config()

    pf = st.columns(2)
    p_business2 = pf[0].text_input(
        "Business name *", value=p_business if 'p_business' in dir() else "",
        key="sim_prop_biz",
    )
    p_contact2 = pf[1].text_input(
        "Contact name *", value=p_name if 'p_name' in dir() else "",
        key="sim_prop_contact",
    )

    pf2 = st.columns(3)
    p_email2 = pf2[0].text_input(
        "Contact email", value=p_email if 'p_email' in dir() else "",
        key="sim_prop_email",
    )
    p_industry = pf2[1].text_input(
        "Industry *", placeholder="Restaurant, Salon, Law Firm, etc.",
        key="sim_prop_industry",
    )
    rep_options = get_team_first_names(_cfg_for_proposal) or ["Mary Michael", "Creed", "Swayze"]
    p_rep = pf2[2].selectbox("Sales rep", rep_options, key="sim_prop_rep")

    p_addl = st.text_area(
        "Additional notes (optional)",
        placeholder="Specific goals, deadlines, or anything you want the proposal to address.",
        height=80, key="sim_prop_notes",
    )

    color_options = ["original", "light_airy", "dark_sophisticated", "peaceful_pastels"]
    p_color = st.selectbox("Color scheme", color_options, key="sim_prop_color")

    if st.button("Generate Proposal PDF", type="primary", key="sim_prop_btn"):
        if not p_business2 or not p_contact2 or not p_industry:
            st.error("Business name, contact name, and industry are required.")
        else:
            import os as _os
            api_key = _os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key or api_key == "your-api-key-here":
                st.error("ANTHROPIC_API_KEY not configured.")
            else:
                from models.proposal_data import ProposalInput
                from services.claude_service import ClaudeService
                from services.docx_service import DocxService
                from services.config_service import get_team_member
                from generators.elite_advertiser import EliteAdvertiserProposal

                # Resolve full sales-rep name (matches "Mary Michael" -> full record)
                team_match = next(
                    (m for m in _cfg_for_proposal.get("team", [])
                     if p_rep.lower() in m["name"].lower()),
                    _cfg_for_proposal["team"][0],
                )

                data = ProposalInput(
                    business_name=p_business2,
                    contact_name=p_contact2,
                    contact_email=p_email2,
                    industry=p_industry,
                    city=(result.cities[0] if result.cities else "Oxford"),
                    selected_markets=list(result.cities) or ["Oxford"],
                    recommended_tier=result.recommendation.tier_index,
                    custom_pricing=bool(st.session_state.sim_custom_rate),
                    custom_screen_count=result.total_screens,
                    custom_monthly_rate=float(st.session_state.sim_custom_rate or 0),
                    sales_rep=team_match["name"],
                    additional_notes=p_addl or "",
                )

                model = _cfg_for_proposal.get("proposal_settings", {}).get(
                    "model", "claude-sonnet-4-5-20250929"
                )
                claude = ClaudeService(api_key=api_key, model=model)
                docx_svc = DocxService(_cfg_for_proposal, color_scheme=p_color)

                # Auto-pick community screen photos for the relevant markets
                from pathlib import Path as _P
                screens_dir = _P(__file__).parent.parent / "assets" / "screens"
                photos = []
                for market in data.selected_markets:
                    market_dir = screens_dir / market
                    if market_dir.exists():
                        photos.extend(sorted(
                            str(p) for p in market_dir.glob("*")
                            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
                        ))
                if not photos and screens_dir.exists():
                    photos = sorted(
                        str(p) for p in screens_dir.glob("*")
                        if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
                    )
                docx_svc.page2_photo_paths = photos[:2]
                docx_svc.page4_photo_paths = photos[2:8]
                docx_svc.page4_captions = []
                docx_svc.venue_photo_paths = []
                docx_svc.ad_example_paths = []
                docx_svc.extra_photo_paths = photos[:8]
                docx_svc.client_logo_path = None

                progress = st.progress(0, text="Starting generation...")
                status_label = st.empty()

                def _on_progress(section_name, current, total):
                    progress.progress(current / total,
                                      text=f"Generating: {section_name} ({current}/{total})")
                    status_label.caption(f"Section {current} of {total}")

                try:
                    generator = EliteAdvertiserProposal(_cfg_for_proposal, claude, docx_svc)
                    proposal_path, _email_path = generator.generate(
                        data, progress_callback=_on_progress,
                    )
                    progress.progress(1.0, text="Complete!")
                    status_label.empty()
                    st.success("Proposal generated.")

                    pdf_path = DocxService.get_pdf_path(proposal_path)
                    cols = st.columns(2 if pdf_path else 1)
                    with open(proposal_path, "rb") as f:
                        cols[0].download_button(
                            "Download Word (.docx)",
                            data=f.read(),
                            file_name=proposal_path.name,
                            mime=("application/vnd.openxmlformats-officedocument."
                                  "wordprocessingml.document"),
                            key="sim_prop_dl_docx",
                        )
                    if pdf_path:
                        with open(pdf_path, "rb") as f:
                            cols[1].download_button(
                                "Download PDF",
                                data=f.read(),
                                file_name=pdf_path.name,
                                mime="application/pdf",
                                key="sim_prop_dl_pdf",
                            )
                except Exception as e:
                    progress.empty()
                    status_label.empty()
                    st.error(f"Generation failed: {e}")
