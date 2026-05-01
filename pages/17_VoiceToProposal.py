# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Paste a sales-call transcript and Claude extracts a simulator scenario.

Output: prospect contact info, industry, target city/cities, target audience,
mentioned venues (matched against the network dashboard), budget hints,
and notes — all pre-filled into simulator session state. One click jumps
to the simulator with everything ready for review.
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st
import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.simulator_service import list_venues

st.set_page_config(
    page_title="Voice-to-Proposal - MCTV Bot",
    page_icon="\U0001F3A4",
    layout="wide",
)

if not check_password():
    st.stop()

st.markdown("## Voice-to-Proposal")
st.caption(
    "Paste a sales-call transcript or your post-call notes. Claude extracts "
    "the prospect details, target market, mentioned venues, and budget — and "
    "loads everything into the Simulator for you."
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _venue_index() -> dict:
    """Map lowercased host_name -> venue dict for fuzzy match."""
    return {v["host_name"].lower(): v for v in list_venues()}


def _match_venues(mentioned: list[str]) -> list[str]:
    """Match free-text venue names from the transcript to venue keys."""
    idx = _venue_index()
    matched = []
    for name in mentioned or []:
        nlow = (name or "").strip().lower()
        if not nlow:
            continue
        if nlow in idx:
            matched.append(idx[nlow]["key"])
            continue
        # Substring fuzzy match
        for host, v in idx.items():
            if nlow in host or host in nlow:
                matched.append(v["key"])
                break
    # De-dupe preserving order
    seen, out = set(), []
    for k in matched:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


EXTRACT_PROMPT = """You are an extraction assistant for MCTV Elite Advertising's sales team.

A rep just got off a sales call with a prospect. Below is the transcript or
the rep's post-call notes. Extract the structured details below into JSON.

Fields:
- "business_name": prospect's business name (string)
- "contact_name": person spoken with (string)
- "contact_email": if mentioned (string, "" if not)
- "contact_phone": if mentioned (string, "" if not)
- "industry": short label like "Restaurant", "Salon", "Law Firm" (string)
- "target_cities": list of city names mentioned among Oxford, Starkville, Tupelo, Columbus, West Point. Lowercase first letter title case.
- "target_categories": list of venue categories of interest (e.g. "Bar/Restaurant", "Health & Fitness", "Medical", "Retail", "Barbershop/Salon")
- "mentioned_venues": list of specific venue/business names the rep wrote down or that came up. Match-quality strings; keep verbatim.
- "monthly_budget": if a budget or rate was discussed, the number in USD as an integer (e.g. 500). 0 if not.
- "audience_notes": one-sentence description of the audience the prospect wants to reach.
- "additional_notes": one-paragraph free-text capturing other relevant context (deadlines, events, special asks, objections to address).

Return ONLY valid JSON — no commentary, no markdown fences. If a field is
unknown, use "" or [] or 0 as appropriate.

Transcript / notes:
---
{transcript}
---
"""


# ── UI ───────────────────────────────────────────────────────────────────────

transcript = st.text_area(
    "Paste transcript or notes",
    height=300,
    placeholder=("Example: 'Talked to Sarah at Bep Haus. Wants to advertise the new "
                 "lunch menu starting in October. Looking at Oxford only, mostly "
                 "around the Square. Budget around $500/mo. Mentioned Grove "
                 "Collective and Square Books as competitors. Wants to reach "
                 "college students and faculty.'"),
)

col_a, col_b = st.columns([1, 3])
extract_btn = col_a.button("Extract", type="primary", width="stretch", disabled=not transcript.strip())

if extract_btn:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your-api-key-here":
        st.error("ANTHROPIC_API_KEY not configured.")
        st.stop()

    with st.spinner("Extracting..."):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1500,
                messages=[{"role": "user",
                           "content": EXTRACT_PROMPT.format(transcript=transcript)}],
            )
            raw = resp.content[0].text.strip()
            # Strip optional code fences
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            extracted = json.loads(raw)
        except json.JSONDecodeError as e:
            st.error(f"Could not parse Claude's response as JSON: {e}")
            st.code(raw[:1000] if 'raw' in dir() else "(no output)")
            st.stop()
        except Exception as e:
            st.error(f"Extraction failed: {e}")
            st.stop()

    st.session_state["v2p_extracted"] = extracted
    st.session_state["v2p_matched_venues"] = _match_venues(extracted.get("mentioned_venues", []))
    st.rerun()


# ── Show extracted data ──────────────────────────────────────────────────────

extracted = st.session_state.get("v2p_extracted")
if extracted:
    st.divider()
    st.markdown("### Extracted")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Business:** {extracted.get('business_name', '—') or '—'}")
        st.markdown(f"**Contact:** {extracted.get('contact_name', '—') or '—'}")
        st.markdown(f"**Email:** {extracted.get('contact_email', '—') or '—'}")
        st.markdown(f"**Phone:** {extracted.get('contact_phone', '—') or '—'}")
        st.markdown(f"**Industry:** {extracted.get('industry', '—') or '—'}")
    with c2:
        cities = extracted.get("target_cities") or []
        cats = extracted.get("target_categories") or []
        st.markdown(f"**Target cities:** {', '.join(cities) or '—'}")
        st.markdown(f"**Target categories:** {', '.join(cats) or '—'}")
        budget = int(extracted.get("monthly_budget", 0) or 0)
        st.markdown(f"**Budget hint:** {('$' + format(budget, ',') + '/mo') if budget else '—'}")

    if extracted.get("audience_notes"):
        st.markdown(f"**Audience:** {extracted['audience_notes']}")
    if extracted.get("additional_notes"):
        st.markdown(f"**Notes:** {extracted['additional_notes']}")

    matched = st.session_state.get("v2p_matched_venues", [])
    mentioned = extracted.get("mentioned_venues", []) or []
    if mentioned:
        st.markdown("**Mentioned venues:**")
        idx = _venue_index()
        for raw_name in mentioned:
            nlow = (raw_name or "").lower()
            hit = idx.get(nlow) or next(
                (v for h, v in idx.items() if nlow in h or h in nlow), None,
            )
            if hit:
                st.markdown(f"- {raw_name} → matched: **{hit['host_name']}** ({hit['city']})")
            else:
                st.markdown(f"- {raw_name} → no match in network")

    st.divider()
    if st.button("Load into Simulator", type="primary"):
        # Pre-fill simulator session state and jump to the simulator page
        st.session_state.sim_selected = matched
        st.session_state.sim_custom_rate = float(extracted.get("monthly_budget", 0) or 0)
        # Pre-fill picker filters by city + category
        st.session_state.sim_city_filter = list(extracted.get("target_cities") or [])
        st.session_state.sim_cat_filter = list(extracted.get("target_categories") or [])
        st.session_state.sim_min_traffic = 0
        # Stash prospect details so the Save & Share form can grab them
        st.session_state.sim_prefill_business = extracted.get("business_name", "")
        st.session_state.sim_prefill_contact = extracted.get("contact_name", "")
        st.session_state.sim_prefill_email = extracted.get("contact_email", "")
        st.session_state.sim_prefill_phone = extracted.get("contact_phone", "")
        st.session_state.sim_prefill_industry = extracted.get("industry", "")
        st.session_state.sim_prefill_notes = extracted.get("additional_notes", "")
        st.switch_page("pages/16_Simulator.py")
