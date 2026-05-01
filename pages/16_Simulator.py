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
    p_business = sc[0].text_input("Prospect business name *")
    p_name = sc[1].text_input("Contact name *")
    p_email = sc[2].text_input("Contact email")

    sc2 = st.columns(3)
    p_phone = sc2[0].text_input("Contact phone")
    rep = sc2[1].text_input("Assigned rep")
    notes = sc2[2].text_input("Notes")

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
