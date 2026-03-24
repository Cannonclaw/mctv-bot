# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Outbound Prospector — systematically find and score local business targets.

Generates prospect lists by industry and market, scores them for fit,
and adds them directly to the sales pipeline with nurture sequences.
"""

import streamlit as st
import os
import json
import logging
from datetime import date, timedelta

from services.auth import check_team_auth

if not check_team_auth():
    st.stop()

from services.pipeline_service import (
    TIERS, create_opportunity, get_all_opportunities,
)
from services.nurture_service import get_available_sequences

logger = logging.getLogger(__name__)


# ── Page Config ───────────────────────────────────────────────────────────────

st.markdown('<p class="main-header">Outbound Prospector</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Find and target local businesses for advertising</p>',
            unsafe_allow_html=True)


# ── Target Industry Database ─────────────────────────────────────────────────

INDUSTRY_TARGETS = {
    "Restaurants & Bars": {
        "icon": "restaurant",
        "fit_score": 95,
        "why": "High foot traffic, long dwell times, repeat customers. Your ad plays while diners wait for food.",
        "pitch_angle": "Reach hungry customers while they wait — ads play every 15 minutes",
        "avg_deal": 500,
        "keywords": ["restaurant", "bar", "grill", "cafe", "diner", "pizza", "bbq", "sushi", "mexican", "italian", "chinese", "thai", "steakhouse", "brewery", "pub"],
    },
    "Fitness & Gyms": {
        "icon": "gym",
        "fit_score": 90,
        "why": "Captive audience during workouts, health-conscious demographics, repeat visits 3-5x/week.",
        "pitch_angle": "Members see your ad 3-5 times per week during their workout",
        "avg_deal": 500,
        "keywords": ["gym", "fitness", "crossfit", "yoga", "pilates", "martial arts", "boxing", "f45", "planet fitness", "anytime fitness", "orange theory"],
    },
    "Salons & Spas": {
        "icon": "salon",
        "fit_score": 90,
        "why": "Clients sit for 30-90 minutes per visit. Predominantly female audience with spending power.",
        "pitch_angle": "Reach clients during 30-90 minute appointments — undivided attention",
        "avg_deal": 350,
        "keywords": ["salon", "spa", "barber", "nail", "hair", "beauty", "aesthetics", "lash", "brow", "tanning", "med spa", "medspa"],
    },
    "Medical & Dental": {
        "icon": "medical",
        "fit_score": 85,
        "why": "Long wait times, professional audience, high trust environment. Perfect for professional services ads.",
        "pitch_angle": "Patients wait 20-40 minutes — your ad fills that dead time",
        "avg_deal": 500,
        "keywords": ["doctor", "dentist", "dental", "medical", "clinic", "dermatology", "optometry", "chiropractic", "veterinary", "vet", "pediatric", "urgent care", "pharmacy"],
    },
    "Auto & Service": {
        "icon": "auto",
        "fit_score": 80,
        "why": "Waiting rooms with 1-3 hour waits. Customers with disposable income for vehicle services.",
        "pitch_angle": "Customers wait 1-3 hours — your ad plays on repeat",
        "avg_deal": 350,
        "keywords": ["auto", "car wash", "oil change", "tire", "mechanic", "body shop", "detailing", "dealer"],
    },
    "Real Estate": {
        "icon": "real_estate",
        "fit_score": 85,
        "why": "Always prospecting for listings and buyers. High-value transactions justify advertising spend.",
        "pitch_angle": "Stay top-of-mind with homebuyers and sellers in their daily routine",
        "avg_deal": 500,
        "keywords": ["real estate", "realtor", "realty", "property", "homes", "mortgage", "title"],
    },
    "Insurance & Financial": {
        "icon": "insurance",
        "fit_score": 80,
        "why": "Need constant brand awareness. Local trust matters for financial decisions.",
        "pitch_angle": "Build local trust — your name on screens in businesses they already trust",
        "avg_deal": 500,
        "keywords": ["insurance", "state farm", "allstate", "farm bureau", "financial", "accounting", "cpa", "tax", "bank", "credit union"],
    },
    "Legal": {
        "icon": "legal",
        "fit_score": 75,
        "why": "Always need new clients. Personal injury, family law, DUI — all benefit from local visibility.",
        "pitch_angle": "Reach potential clients in their daily routine — not just when they're searching",
        "avg_deal": 800,
        "keywords": ["attorney", "lawyer", "law firm", "legal", "injury", "family law", "criminal defense", "bankruptcy"],
    },
    "Home Services": {
        "icon": "home",
        "fit_score": 75,
        "why": "HVAC, plumbing, roofing — all need constant lead gen. Repeat business model.",
        "pitch_angle": "Be the first call when someone needs a plumber or HVAC tech",
        "avg_deal": 350,
        "keywords": ["plumber", "hvac", "roofing", "electrician", "pest control", "landscaping", "cleaning", "painting", "flooring", "contractor"],
    },
    "Retail & Shopping": {
        "icon": "retail",
        "fit_score": 70,
        "why": "Drive foot traffic with promotions. Works especially well for boutiques and specialty stores.",
        "pitch_angle": "Drive foot traffic with promotions on screens near your store",
        "avg_deal": 350,
        "keywords": ["boutique", "clothing", "jewelry", "furniture", "mattress", "pet store", "vape", "smoke shop", "consignment"],
    },
}

MARKETS = {
    "Oxford": {"screens": 75, "population": "28,000+", "notes": "Ole Miss market, college town, high foot traffic"},
    "Starkville": {"screens": 30, "population": "25,000+", "notes": "Mississippi State market, growing town"},
    "Tupelo": {"screens": 25, "population": "38,000+", "notes": "Largest city, diverse business base"},
}


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_target, tab_generate, tab_batch = st.tabs([
    "Target Industries", "Generate Prospect List", "Batch Add to Pipeline",
])


# ── Tab 1: Target Industries ─────────────────────────────────────────────────

with tab_target:
    st.markdown("### Industry Fit Analysis")
    st.caption("Which local businesses are the best fit for MCTV advertising?")

    for industry, info in sorted(INDUSTRY_TARGETS.items(), key=lambda x: x[1]["fit_score"], reverse=True):
        score = info["fit_score"]
        color = "#28a745" if score >= 85 else "#C5A55A" if score >= 75 else "#6c757d"

        with st.expander(f"**{industry}** — Fit Score: {score}/100"):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"**Why it works:** {info['why']}")
                st.markdown(f"**Pitch angle:** *\"{info['pitch_angle']}\"*")
                st.markdown(f"**Avg deal size:** ${info['avg_deal']:,}/mo")
                st.markdown(f"**Search keywords:** {', '.join(info['keywords'][:8])}")
            with c2:
                st.metric("Fit Score", f"{score}/100")
                st.progress(score / 100)


# ── Tab 2: Generate Prospect List ────────────────────────────────────────────

with tab_generate:
    st.markdown("### Generate Prospect List")
    st.caption(
        "Use Claude AI to research and generate a list of businesses "
        "in your target market and industry."
    )

    c1, c2 = st.columns(2)
    with c1:
        target_city = st.selectbox("Target Market", list(MARKETS.keys()), key="prospect_city")
        target_industry = st.selectbox("Target Industry", list(INDUSTRY_TARGETS.keys()), key="prospect_industry")
    with c2:
        num_prospects = st.slider("Number of Prospects", 5, 25, 10, key="num_prospects")
        assigned_rep = st.selectbox("Assign to Rep", ["Mary Michael", "Creed", "Swayze"], key="prospect_rep")

    market_info = MARKETS[target_city]
    industry_info = INDUSTRY_TARGETS[target_industry]

    st.info(
        f"**{target_city}** — {market_info['screens']} screens, "
        f"pop. {market_info['population']} — {market_info['notes']}"
    )

    if st.button("Generate Prospect List with AI", type="primary"):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.error("Claude API key not configured. Set ANTHROPIC_API_KEY in .env")
        else:
            with st.spinner(f"Researching {target_industry} businesses in {target_city}..."):
                try:
                    import urllib.request

                    prompt = f"""You are a sales research assistant for MCTV Elite Advertising, an indoor digital billboard network in North Mississippi.

Generate a list of exactly {num_prospects} REAL {target_industry.lower()} businesses in {target_city}, Mississippi that would be good prospects for indoor digital billboard advertising.

For each business, provide:
1. business_name: The actual business name
2. contact_name: Owner or manager name if known, otherwise "Owner"
3. industry: Specific industry category
4. estimated_interest: "high", "medium", or "low"
5. why: One sentence on why they'd benefit from MCTV advertising
6. website: Business website URL if known, otherwise empty string

Focus on established local businesses, NOT national chains (though local franchises are OK).
Search keywords for this industry: {', '.join(industry_info['keywords'][:6])}

Return ONLY a valid JSON array of objects. No markdown, no explanation.
Example: [{{"business_name": "Joe's Gym", "contact_name": "Joe Smith", "industry": "Fitness", "estimated_interest": "high", "why": "High foot traffic gym with long member visits", "website": "joesgym.com"}}]"""

                    body = json.dumps({
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 4000,
                        "messages": [{"role": "user", "content": prompt}],
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

                    text = result.get("content", [{}])[0].get("text", "[]")

                    # Parse JSON from response
                    # Strip markdown code fences if present
                    if "```" in text:
                        text = text.split("```")[1]
                        if text.startswith("json"):
                            text = text[4:]

                    prospects = json.loads(text.strip())

                    if prospects:
                        st.session_state["generated_prospects"] = prospects
                        st.session_state["prospect_city"] = target_city
                        st.session_state["prospect_industry"] = target_industry
                        st.session_state["prospect_rep"] = assigned_rep
                        st.success(f"Found {len(prospects)} prospects!")
                    else:
                        st.warning("No prospects generated. Try again.")

                except json.JSONDecodeError:
                    st.error("Failed to parse AI response. Try again.")
                except Exception as e:
                    st.error(f"Research failed: {e}")

    # Display generated prospects
    if "generated_prospects" in st.session_state:
        prospects = st.session_state["generated_prospects"]
        p_city = st.session_state.get("prospect_city", target_city)
        p_industry = st.session_state.get("prospect_industry", target_industry)
        p_rep = st.session_state.get("prospect_rep", assigned_rep)

        st.divider()
        st.markdown(f"### Generated Prospects — {p_industry} in {p_city}")

        # Check which are already in pipeline
        existing_opps = get_all_opportunities()
        existing_names = {(o.get("business_name") or "").lower() for o in existing_opps}

        selected = []
        for i, prospect in enumerate(prospects):
            name = prospect.get("business_name", "Unknown")
            already_exists = name.lower() in existing_names
            interest = prospect.get("estimated_interest", "medium")
            interest_icon = {"high": "green", "medium": "orange", "low": "gray"}.get(interest, "gray")

            disabled = already_exists
            label = f"**{name}** — {prospect.get('industry', 'N/A')}"
            if already_exists:
                label += " (already in pipeline)"

            checked = st.checkbox(
                label,
                disabled=disabled,
                key=f"prospect_{i}"
            )
            st.caption(
                f"Contact: {prospect.get('contact_name', 'Unknown')} | "
                f"Interest: {interest} | "
                f"Why: {prospect.get('why', 'N/A')}"
            )

            if checked and not disabled:
                selected.append(prospect)

        if selected:
            tier = st.selectbox("Tier for all selected", list(TIERS.keys()), index=1, key="batch_tier")
            nurture = st.selectbox(
                "Nurture Sequence",
                ["Cold Outreach", "None"],
                key="batch_nurture"
            )

            if st.button(f"Add {len(selected)} Prospect(s) to Pipeline", type="primary"):
                added = 0
                tier_info = TIERS[tier]
                seq = "cold_outreach" if nurture == "Cold Outreach" else None

                for prospect in selected:
                    opp = create_opportunity({
                        "business_name": prospect.get("business_name", "Unknown"),
                        "contact_name": prospect.get("contact_name", ""),
                        "industry": prospect.get("industry", p_industry),
                        "city": p_city,
                        "source": "prospector",
                        "stage": "prospect",
                        "monthly_value": tier_info["monthly"],
                        "screen_count": tier_info["screens"],
                        "tier_name": tier,
                        "expected_close_date": (date.today() + timedelta(days=45)).isoformat(),
                        "notes": prospect.get("why", ""),
                        "assigned_rep": p_rep,
                        "nurture_sequence": seq,
                    })
                    if opp:
                        added += 1

                st.success(f"Added {added} prospect(s) to pipeline!")
                del st.session_state["generated_prospects"]
                st.rerun()


# ── Tab 3: Batch Add ─────────────────────────────────────────────────────────

with tab_batch:
    st.markdown("### Quick-Add Multiple Prospects")
    st.caption("Paste a list of businesses to add them all at once.")

    batch_city = st.selectbox("City", list(MARKETS.keys()), key="batch_city")
    batch_industry = st.text_input("Industry", key="batch_industry_input")
    batch_rep = st.selectbox("Assigned Rep", ["Mary Michael", "Creed", "Swayze"], key="batch_rep")
    batch_tier_sel = st.selectbox("Tier", list(TIERS.keys()), index=1, key="batch_tier_sel")

    st.markdown("**Enter one business per line** (format: `Business Name | Contact Name | Phone | Email`)")
    st.caption("Only business name is required. Phone and email are optional.")

    batch_text = st.text_area(
        "Business List",
        height=200,
        placeholder="Joe's Restaurant | Joe Smith | 662-555-1234 | joe@email.com\nMain Street Salon | Jane Doe\nDowntown Fitness",
        key="batch_text"
    )

    batch_nurture = st.selectbox(
        "Nurture Sequence",
        ["Cold Outreach", "New Lead Nurture", "None"],
        key="batch_nurture_seq"
    )

    if st.button("Add All to Pipeline", type="primary") and batch_text.strip():
        lines = [l.strip() for l in batch_text.strip().split("\n") if l.strip()]
        tier_info = TIERS[batch_tier_sel]
        seq_map = {"Cold Outreach": "cold_outreach", "New Lead Nurture": "new_lead", "None": None}
        seq = seq_map.get(batch_nurture)

        added = 0
        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            biz_name = parts[0] if len(parts) > 0 else ""
            contact = parts[1] if len(parts) > 1 else ""
            phone = parts[2] if len(parts) > 2 else ""
            email = parts[3] if len(parts) > 3 else ""

            if not biz_name:
                continue

            opp = create_opportunity({
                "business_name": biz_name,
                "contact_name": contact,
                "contact_phone": phone,
                "contact_email": email,
                "industry": batch_industry,
                "city": batch_city,
                "source": "prospector",
                "stage": "prospect",
                "monthly_value": tier_info["monthly"],
                "screen_count": tier_info["screens"],
                "tier_name": batch_tier_sel,
                "expected_close_date": (date.today() + timedelta(days=45)).isoformat(),
                "assigned_rep": batch_rep,
                "nurture_sequence": seq,
            })
            if opp:
                added += 1

        st.success(f"Added {added} prospect(s) to pipeline!")
        st.rerun()
