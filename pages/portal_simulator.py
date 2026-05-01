# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Public, token-gated view of a saved simulator scenario.

Loaded via ``?token=<uuid>``. No login — the share token is the auth.
The team email allowlist does NOT apply here; this is a prospect-facing page.
"""

import sys
from pathlib import Path

import folium
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.simulator_service import load_scenario_by_token

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

st.set_page_config(
    page_title="Your MCTV Custom Package",
    page_icon="\U0001F4FA",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit chrome on the public view
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    #MainMenu, footer { visibility: hidden; }
    .block-container { max-width: 1100px; margin: 0 auto; padding-top: 2rem; }
    .mctv-hero {
        background: #1B1F3B; color: white; padding: 2rem; border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .mctv-hero h1 { color: #C5A55A; margin: 0; font-size: 1.6rem; }
    .mctv-hero p { color: #e8e8e8; margin: 0.4rem 0 0; }
</style>
""", unsafe_allow_html=True)


# ── Token gate ───────────────────────────────────────────────────────────────

token = st.query_params.get("token", "").strip()
if not token:
    st.error("This link is missing or invalid.")
    st.stop()

scenario = load_scenario_by_token(token)
if not scenario:
    st.error("This link has expired or was never valid. Please contact your MCTV representative.")
    st.stop()


# ── Hero ─────────────────────────────────────────────────────────────────────

prospect = scenario.get("prospect_business") or scenario.get("prospect_name", "your business")
st.markdown(f"""
<div class="mctv-hero">
    <p style="color:#C5A55A; font-size:0.85rem; letter-spacing:2px; margin:0;">MCTV ELITE ADVERTISING</p>
    <h1>Custom Package for {prospect}</h1>
    <p>Built by your MCTV rep based on the venues we discussed. Numbers below are your estimated reach across our indoor digital billboard network.</p>
</div>
""", unsafe_allow_html=True)


# ── Pull saved metrics ───────────────────────────────────────────────────────

metrics = scenario.get("computed_metrics", {}) or {}
recommendation = scenario.get("recommended_tier", {}) or {}

total_screens = int(metrics.get("total_screens", 0) or 0)
total_impressions = float(metrics.get("total_monthly_impressions", 0) or 0)
total_plays = int(metrics.get("total_monthly_plays", 0) or 0)
total_traffic = float(metrics.get("total_monthly_traffic", 0) or 0)
cities = metrics.get("cities", []) or []
venues = metrics.get("venues", []) or []
blend = metrics.get("blend", {}) or {}


# ── Headline metrics ─────────────────────────────────────────────────────────

m = st.columns(4)
m[0].metric("Screens", f"{total_screens:,}")
m[1].metric("Monthly Impressions", f"{int(total_impressions):,}")
m[2].metric("Monthly Plays", f"{total_plays:,}")
m[3].metric("Foot Traffic", f"{int(total_traffic):,}")

if cities:
    st.caption(f"Network coverage: {', '.join(cities)}")

st.divider()


# ── Package ──────────────────────────────────────────────────────────────────

st.markdown("### Your Monthly Package")

pkg = st.columns([2, 1, 1])
with pkg[0]:
    st.markdown(f"**Tier:** {recommendation.get('tier_name', 'Custom')}")
    plays_label = recommendation.get("plays_per_month_label", "")
    if plays_label:
        st.markdown(f"**Plays per month:** {plays_label}")

effective_rate = float(recommendation.get("effective_rate") or recommendation.get("monthly_rate") or 0)
cpm = float(recommendation.get("cpm", 0) or 0)
pkg[1].metric("Monthly investment", f"${effective_rate:,.0f}")
pkg[2].metric("CPM", f"${cpm:,.2f}")

st.caption(
    "CPM = cost per 1,000 impressions. Industry comparison: Radio $5-12 · Cable TV $15-30 · "
    "Print $10-30 · Outdoor $3-8 · Digital display $5-15. MCTV typically lands $1-3."
)

st.divider()


# ── Audience ─────────────────────────────────────────────────────────────────

st.markdown("### Who You're Reaching")

med_income = int(blend.get("median_household_income_blended", 0) or 0)
if med_income:
    st.caption(f"Blended median household income across selected venues: ${med_income:,}")

age_pct = blend.get("age_pct", {}) or {}
income_pct = blend.get("income_pct", {}) or {}
edu_pct = blend.get("education_pct", {}) or {}

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


def _bar(title: str, data: dict, labels: dict):
    st.markdown(f"**{title}**")
    if not data or sum(float(v or 0) for v in data.values()) == 0:
        st.caption("Demographic data unavailable for these venues.")
        return
    rows = [{"Segment": labels.get(k, k), "%": float(v or 0)} for k, v in data.items()]
    st.bar_chart(rows, x="Segment", y="%", height=220)


a, b, c = st.columns(3)
with a:
    _bar("Age", age_pct, AGE_LABELS)
with b:
    _bar("Household Income", income_pct, INCOME_LABELS)
with c:
    _bar("Education", edu_pct, EDU_LABELS)

tags = blend.get("audience_tags", []) or []
if tags:
    st.markdown("**Audience signals:** " + " · ".join(f"`{t}`" for t in tags))

st.caption(
    "Audience profile is an estimate built from US Census data for each venue's ZIP code, "
    "weighted by venue type. Not a measurement of individual visitors."
)

st.divider()


# ── Map of selected venues ───────────────────────────────────────────────────

mapped = [v for v in venues if v.get("lat") and v.get("lon")]
if mapped:
    st.markdown("### Where Your Ads Will Run")
    avg_lat = sum(float(v["lat"]) for v in mapped) / len(mapped)
    avg_lon = sum(float(v["lon"]) for v in mapped) / len(mapped)
    zoom = 10 if len({v.get("city") for v in mapped}) > 1 else 13
    fmap = folium.Map(location=[avg_lat, avg_lon], zoom_start=zoom, tiles="cartodbpositron")
    for v in mapped:
        color = CATEGORY_COLORS.get(v.get("general_category", "Other"), "#888")
        popup = (
            f"<div style='font-family:Arial;'><b>{v.get('host_name','')}</b><br>"
            f"<span style='color:#888;'>{v.get('general_category','')} · {v.get('city','')}</span><br><br>"
            f"Monthly Impressions: {int(float(v.get('monthly_impressions', 0) or 0)):,}<br>"
            f"Screens: {int(v.get('license_count', 1) or 1)}</div>"
        )
        folium.CircleMarker(
            location=[float(v["lat"]), float(v["lon"])],
            radius=9,
            color="#070707",
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(popup, max_width=260),
            tooltip=v.get("host_name", ""),
        ).add_to(fmap)
    st_folium(
        fmap,
        width=None,
        height=420,
        returned_objects=[],
        key="portal_map",
    )
    st.divider()


# ── Selected venues ──────────────────────────────────────────────────────────

st.markdown("### Venues in Your Plan")

if venues:
    rows = [{
        "Venue": v.get("host_name", ""),
        "Category": v.get("general_category", ""),
        "City": v.get("city", ""),
        "Screens": int(v.get("license_count", 1) or 1),
        "Monthly Traffic": int(float(v.get("monthly_traffic", 0) or 0)),
        "Monthly Impressions": int(float(v.get("monthly_impressions", 0) or 0)),
    } for v in venues]
    st.dataframe(rows, width="stretch", hide_index=True)

st.divider()


# ── CTA ──────────────────────────────────────────────────────────────────────

import os as _os
contact_email = _os.environ.get("MCTV_CONTACT_EMAIL", "creed@mctvofms.com")
contact_phone = _os.environ.get("MCTV_CONTACT_PHONE", "(601) 201-8202")

prospect_name = scenario.get("prospect_name", "")
subject = f"MCTV proposal — {prospect}"
body = (
    f"Hi MCTV team,\n\n"
    f"I reviewed the custom package and would like to move forward.\n\n"
    f"Prospect: {prospect}\n"
    f"Contact: {prospect_name}\n"
)
mailto = (
    f"mailto:{contact_email}"
    f"?subject={subject.replace(' ', '%20')}"
    f"&body={body.replace(chr(10), '%0A').replace(' ', '%20')}"
)

# ── Calendar booking ─────────────────────────────────────────────────────────
# Resolve the assigned rep's calendar URL (or the default) at view time so
# config changes take effect without needing to re-save scenarios.

def _booking_url() -> tuple[str, str]:
    """Return (url, rep_name) for the booking widget. Empty url = no widget."""
    try:
        from services.config_service import load_config
        cfg = load_config()
    except Exception:
        return "", ""
    assigned = (scenario.get("assigned_rep") or "").strip().lower()
    booking_cfg = cfg.get("booking", {}) or {}
    # Match the assigned rep first
    for m in cfg.get("team", []):
        if assigned and assigned in m.get("name", "").lower():
            cal = (m.get("calendar_url") or "").strip()
            if cal:
                return cal, m.get("name", "")
    # Fallback to default
    default = (booking_cfg.get("default_calendar_url") or "").strip()
    if default:
        # Use first team member's name as the host label
        first = (cfg.get("team") or [{}])[0]
        return default, first.get("name", "MCTV team")
    return "", ""

_cal_url, _cal_rep = _booking_url()

if _cal_url:
    try:
        from services.config_service import load_config as _lc
        _booking_label = (_lc().get("booking", {}) or {}).get("label",
                                                              "Book a 15-Minute Discovery Call")
        _booking_subtitle = (_lc().get("booking", {}) or {}).get("subtitle", "")
    except Exception:
        _booking_label, _booking_subtitle = "Book a 15-Minute Discovery Call", ""

    st.markdown(f"### {_booking_label}")
    if _booking_subtitle:
        st.caption(_booking_subtitle)

    # Embed Cal.com / Calendly / Google Appointment via iframe; users get a
    # working scheduler in-page. If a host blocks iframing, the link button
    # below still opens it in a new tab.
    st.components.v1.iframe(_cal_url, height=720, scrolling=True)
    st.caption(f"Trouble loading? [Open the booking page in a new tab]({_cal_url}).")
    st.divider()


cta = st.columns([2, 1])
with cta[0]:
    st.markdown("### Ready to move forward?")
    st.markdown(
        f"Reach your MCTV rep at **{contact_phone}** or "
        f"[{contact_email}]({mailto}) and we'll lock in your package."
    )
with cta[1]:
    st.link_button("Email MCTV", mailto, type="primary", width="stretch")

st.markdown(
    '<div style="text-align:center; color:#888; font-size:0.85rem; padding:2rem 0 0;">'
    '<p>MCTV Elite Advertising | Oxford | Starkville | Tupelo</p>'
    '<p>www.mctvofms.com | &copy; 2026 MCTV Digital, Inc.</p>'
    '</div>',
    unsafe_allow_html=True,
)
