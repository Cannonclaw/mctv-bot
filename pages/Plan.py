# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Public self-serve advertiser simulator.

Prospect-facing version of the internal simulator. No auth. Pick venues on
the map, see live impression / play / CPM numbers, then drop your contact
details to lock in the package. Submission creates a lead, saves a shareable
scenario, and emails both the prospect and the team.
"""

import os
import sys
from pathlib import Path

import folium
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.simulator_service import build_scenario, list_venues, save_scenario
from services.leads_service import save_lead, send_notification_email

st.set_page_config(
    page_title="Build Your MCTV Plan",
    page_icon="\U0001F4FA",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { max-width: 1200px; padding-top: 1.5rem; }
    .plan-hero {
        background: #1B1F3B; color: white; padding: 1.6rem 2rem; border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .plan-hero h1 { color: #C5A55A; margin: 0; font-size: 1.7rem; }
    .plan-hero p { color: #e8e8e8; margin: 0.4rem 0 0; }
</style>
""", unsafe_allow_html=True)


# ── Already submitted? ───────────────────────────────────────────────────────

if st.session_state.get("plan_submitted"):
    share_url = st.session_state.get("plan_share_url", "")
    st.markdown(f"""
    <div class="plan-hero">
        <p style="color:#C5A55A; font-size:0.85rem; letter-spacing:2px; margin:0;">MCTV ELITE ADVERTISING</p>
        <h1>Got it — your MCTV rep is on it.</h1>
        <p>You'll hear back within 1 business day with a tailored proposal.
        In the meantime, your custom plan is saved at the link below — bookmark
        it or share it with whoever's signing off.</p>
    </div>
    """, unsafe_allow_html=True)
    if share_url:
        st.code(share_url, language=None)
    st.stop()


# ── Hero ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="plan-hero">
    <p style="color:#C5A55A; font-size:0.85rem; letter-spacing:2px; margin:0;">MCTV ELITE ADVERTISING</p>
    <h1>Build your indoor billboard plan in 60 seconds</h1>
    <p>Pick the venues you want your ad in. We'll show you live impressions,
    plays, and CPM. No login required.</p>
</div>
""", unsafe_allow_html=True)


# ── State ────────────────────────────────────────────────────────────────────

if "plan_selected" not in st.session_state:
    st.session_state.plan_selected = []
if "plan_last_click" not in st.session_state:
    st.session_state.plan_last_click = None


# ── Filters + venue picker ──────────────────────────────────────────────────

VENUES = list_venues()
ALL_CITIES = sorted({v["city"] for v in VENUES if v["city"]})
ALL_CATEGORIES = sorted({v["general_category"] for v in VENUES if v["general_category"]})

f1, f2, f3 = st.columns([1, 1, 2])
city_filter = f1.multiselect("City", ALL_CITIES, default=[])
cat_filter = f2.multiselect("Venue type", ALL_CATEGORIES, default=[])
filter_caption = ", ".join(city_filter) if city_filter else "all cities"

with f3:
    bcol1, bcol2 = st.columns(2)
    if bcol1.button(f"Pick all in {filter_caption}", width="stretch"):
        st.session_state.plan_selected = sorted({
            v["key"] for v in VENUES
            if (not city_filter or v["city"] in city_filter)
            and (not cat_filter or v["general_category"] in cat_filter)
        })
        st.rerun()
    if bcol2.button("Clear selection", width="stretch"):
        st.session_state.plan_selected = []
        st.rerun()

visible = [v for v in VENUES
           if (not city_filter or v["city"] in city_filter)
           and (not cat_filter or v["general_category"] in cat_filter)]

st.caption(f"**{len(st.session_state.plan_selected)} of {len(visible)} venues selected**")


# ── Map ─────────────────────────────────────────────────────────────────────

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


def _build_map(visible_venues, selected):
    plotted = [v for v in visible_venues if v["lat"] and v["lon"]]
    if plotted:
        avg_lat = sum(v["lat"] for v in plotted) / len(plotted)
        avg_lon = sum(v["lon"] for v in plotted) / len(plotted)
        zoom = 10 if len({v["city"] for v in plotted}) > 1 else 13
    else:
        avg_lat, avg_lon, zoom = 34.30, -89.20, 8

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=zoom, tiles="cartodbpositron")
    for v in plotted:
        is_sel = v["key"] in selected
        color = "#C5A55A" if is_sel else CATEGORY_COLORS.get(v["general_category"], "#888")
        radius = 11 if is_sel else 7
        weight = 3 if is_sel else 1
        popup = (
            f"<div style='font-family:Arial; min-width:200px;'>"
            f"<b>{v['host_name']}</b><br>"
            f"<span style='color:#888;'>{v['general_category']} &middot; {v['city']}</span><br><br>"
            f"<i>Click marker to add or remove</i>"
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
            popup=folium.Popup(popup, max_width=240),
            tooltip=v["host_name"] + ("  ✓" if is_sel else ""),
        ).add_to(m)
    return m


fmap = _build_map(visible, set(st.session_state.plan_selected))
map_state = st_folium(
    fmap,
    width=None,
    height=520,
    returned_objects=["last_object_clicked"],
    key="plan_map",
)

clicked = (map_state or {}).get("last_object_clicked")
if clicked and "lat" in clicked and "lng" in clicked:
    lat, lon = round(clicked["lat"], 6), round(clicked["lng"], 6)
    if st.session_state.plan_last_click != (lat, lon):
        for v in visible:
            if abs(v["lat"] - lat) < 0.0001 and abs(v["lon"] - lon) < 0.0001:
                sel = set(st.session_state.plan_selected)
                if v["key"] in sel:
                    sel.discard(v["key"])
                else:
                    sel.add(v["key"])
                st.session_state.plan_selected = sorted(sel)
                st.session_state.plan_last_click = (lat, lon)
                st.rerun()


# ── No selection yet ────────────────────────────────────────────────────────

if not st.session_state.plan_selected:
    st.info("Click venues on the map to start building your plan.")
    st.stop()


# ── Compute scenario ────────────────────────────────────────────────────────

with st.spinner("Crunching your plan..."):
    result = build_scenario(venue_keys=st.session_state.plan_selected)

st.divider()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Screens", result.total_screens)
m2.metric("Monthly Impressions", f"{int(result.total_monthly_impressions):,}")
m3.metric("Cities Reached", len(result.cities))
m4.metric("Suggested Rate", f"${result.recommendation.effective_rate:,.0f}/mo")

st.markdown(
    f"That works out to a CPM of **${result.recommendation.cpm:,.2f}** — "
    f"compare to radio ($5-12), cable ($15-30), and digital display ($5-15)."
)

# Demographic blend in friendly form
blend = result.blend
if blend.median_household_income_blended:
    st.caption(
        f"Audience: blended median household income "
        f"${blend.median_household_income_blended:,} across {', '.join(result.cities) or '—'}. "
        f"{'Tags: ' + ', '.join(blend.audience_tags) if blend.audience_tags else ''}"
    )

st.divider()


# ── Lead capture form ───────────────────────────────────────────────────────

st.markdown("### Lock in this plan")
st.caption(
    "Drop your contact info and we'll save your plan + send your custom "
    "proposal within 1 business day. No obligation, no payment now."
)

with st.form("plan_lead_form"):
    pc1, pc2 = st.columns(2)
    p_business = pc1.text_input("Business name *")
    p_contact = pc2.text_input("Your name *")
    pc3, pc4 = st.columns(2)
    p_email = pc3.text_input("Email *")
    p_phone = pc4.text_input("Phone *")
    p_industry = st.text_input("Industry *", placeholder="Restaurant, Salon, Law Firm, etc.")
    p_notes = st.text_area("Anything we should know? (optional)", height=80)

    SMS_LABEL = (
        "I agree to receive SMS messages from MCTV Digital regarding my "
        "advertising inquiry. Message and data rates may apply. Message "
        "frequency varies. Reply STOP to opt out, HELP for help."
    )
    sms_consent = st.checkbox(SMS_LABEL + " *", key="plan_sms_consent")
    st.caption(
        "Required to text you about your plan. View our "
        "[SMS Terms](https://mctvofms.com/sms-terms/) and "
        "[Privacy Policy](https://mctvofms.com/privacy-policy/)."
    )

    submit = st.form_submit_button("Send Me My Proposal", type="primary",
                                     use_container_width=True)

if submit:
    import re as _re
    missing = []
    if not p_business: missing.append("Business name")
    if not p_contact:  missing.append("Your name")
    if not p_email:    missing.append("Email")
    if not p_phone:    missing.append("Phone")
    if not p_industry: missing.append("Industry")

    phone_digits = _re.sub(r"\D", "", p_phone) if p_phone else ""
    phone_invalid = p_phone and len(phone_digits) < 10

    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
    elif phone_invalid:
        st.error("Please enter a valid phone number (at least 10 digits).")
    elif not sms_consent:
        st.error("Please check the SMS consent box to continue.")
    else:
        # 1. Save the lead
        from datetime import datetime, timezone
        client_ip = ""
        try:
            headers = getattr(st.context, "headers", {}) or {}
            client_ip = (
                headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or headers.get("X-Real-Ip", "")
                or ""
            )
        except Exception:
            pass

        lead = {
            "business_name": p_business,
            "contact_name": p_contact,
            "contact_email": p_email,
            "contact_phone": p_phone,
            "industry": p_industry,
            "city": (result.cities[0] if result.cities else ""),
            "interest_level": "Ready to go — let's get started",
            "goals": "Built a plan via /Plan self-serve simulator",
            "additional_notes": (
                f"Self-serve plan built on /Plan. Selected {result.total_screens} "
                f"screens across {', '.join(result.cities) or 'multiple cities'}. "
                f"Suggested rate ${result.recommendation.effective_rate:,.0f}/mo at "
                f"CPM ${result.recommendation.cpm:.2f}.\n\n"
                f"Notes from prospect: {p_notes or '(none)'}"
            ),
            "how_heard": "Self-serve planner",
            "sms_consent": True,
            "sms_consent_at": datetime.now(timezone.utc).isoformat(),
            "sms_consent_ip": client_ip,
            "sms_consent_text": SMS_LABEL,
            "sms_consent_url": "https://mctvofms.com/plan/",
        }
        try:
            lead_id = save_lead(lead)
        except Exception as _e:
            print(f"[plan] save_lead failed: {_e}")
            lead_id = ""
        try:
            send_notification_email(lead)
        except Exception as _e:
            print(f"[plan] email notify failed: {_e}")

        # Record SMS opt-in
        try:
            from services.sms_service import set_consent
            set_consent(p_phone, opted_in=True, name=p_contact)
        except Exception as _e:
            print(f"[plan] set_consent failed: {_e}")

        # 2. Save the scenario as a token-shareable record
        try:
            saved = save_scenario(
                prospect_name=p_contact,
                prospect_email=p_email,
                prospect_phone=p_phone,
                prospect_business=p_business,
                venue_keys=st.session_state.plan_selected,
                result=result,
                created_by="self_serve_plan",
            )
            if saved:
                base = os.environ.get("PORTAL_URL",
                                       "https://bot.mctvofms.com").rstrip("/")
                share_url = f"{base}/portal_simulator?token={saved.get('share_token', '')}"
                st.session_state["plan_share_url"] = share_url
        except Exception as _e:
            print(f"[plan] save_scenario failed: {_e}")

        st.session_state["plan_submitted"] = True
        st.rerun()


st.markdown(
    '<div style="text-align:center; color:#888; font-size:0.85rem; padding:2rem 0 0;">'
    'MCTV Elite Advertising · Oxford · Starkville · Tupelo<br>'
    '<a href="https://www.mctvofms.com" target="_blank" style="color:#C5A55A;">mctvofms.com</a>'
    '</div>',
    unsafe_allow_html=True,
)
