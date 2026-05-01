# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""AI Sales Coach.

Paste a sales-call transcript or recap. Claude grades the call across six
dimensions, surfaces three specific improvements, and writes the next-step
follow-up the rep should send.

Use it after every prospect call to keep getting better.
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

st.set_page_config(
    page_title="Sales Coach - MCTV Bot",
    page_icon="\U0001F3C6",
    layout="wide",
)

if not check_password():
    st.stop()

st.markdown("## AI Sales Coach")
st.caption(
    "Paste your call transcript or recap. You'll get a scorecard, three "
    "specific things to improve next time, and a follow-up message you can "
    "send the prospect."
)


COACH_PROMPT = """You are a senior B2B sales coach grading a call for an MCTV
Elite Advertising rep selling indoor digital billboard advertising in North
Mississippi (Oxford, Starkville, Tupelo). MCTV's pricing tiers run from
$350/mo (10 screens) to $1,300/mo (75+ screens), with industry CPMs of
$1-3 vs. $5-12 for radio. The rep should be discovering business goals
(foot traffic, brand awareness, event promotion), addressing typical
objections (price, attribution, ad fatigue), and ending with a clear next
step.

Score the rep across these six dimensions on a 1-10 scale. Be tough but
fair. Anchor each score in a specific quote or moment from the transcript.

  1. rapport          — Did the rep build personal connection?
  2. discovery        — Did the rep uncover real goals + pain points?
  3. value_articulation — Did the rep tie MCTV to the prospect's needs?
  4. objection_handling — Did the rep handle pushback well?
  5. closing          — Did the rep ask for the business / next step clearly?
  6. follow_up_clarity — Is the follow-up commitment crisp and time-bound?

Then give:
  - "headline": one-sentence overall verdict (positive or critical, no fluff).
  - "wins": 1-3 specific things the rep did well (each 1 sentence, with a quote).
  - "improvements": exactly 3 specific, actionable improvements for next time
    (each 1-2 sentences). Reference the call. Avoid generic advice.
  - "follow_up_email": A 5-8 line follow-up email the rep can send right now.
    Subject line + body. Reference something specific from the call.
  - "next_step": Crisp one-line next move the rep should take this week.

Return ONLY valid JSON in this shape:
{{"scores": {{"rapport": int, "discovery": int, "value_articulation": int,
              "objection_handling": int, "closing": int,
              "follow_up_clarity": int}},
  "headline": str,
  "wins": [str, ...],
  "improvements": [str, str, str],
  "follow_up_email": {{"subject": str, "body": str}},
  "next_step": str}}

No commentary, no markdown fences, no preamble.

TRANSCRIPT / RECAP
==================
{transcript}
"""


# ── Inputs ───────────────────────────────────────────────────────────────────

transcript = st.text_area(
    "Paste call transcript or recap",
    height=300,
    placeholder=("Either a verbatim transcript or your recap notes. The more "
                 "detail you paste, the sharper the coaching."),
)

col_a, _ = st.columns([1, 4])
go_btn = col_a.button("Grade the call", type="primary",
                       width="stretch", disabled=not transcript.strip())

if go_btn:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your-api-key-here":
        st.error("ANTHROPIC_API_KEY not configured.")
        st.stop()

    with st.spinner("Coaching..."):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2200,
                messages=[{"role": "user",
                           "content": COACH_PROMPT.format(transcript=transcript)}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            review = json.loads(raw)
        except json.JSONDecodeError as e:
            st.error(f"Could not parse Claude's response as JSON: {e}")
            st.code(raw[:1500] if 'raw' in dir() else "(no output)")
            st.stop()
        except Exception as e:
            st.error(f"Coaching failed: {e}")
            st.stop()

    st.session_state["coach_review"] = review
    st.rerun()


# ── Render review ────────────────────────────────────────────────────────────

review = st.session_state.get("coach_review")
if not review:
    st.stop()

st.divider()

# Headline
st.markdown(f"### {review.get('headline', 'Review')}")

# Scorecard
scores = review.get("scores", {}) or {}
score_labels = {
    "rapport": "Rapport",
    "discovery": "Discovery",
    "value_articulation": "Value Articulation",
    "objection_handling": "Objection Handling",
    "closing": "Closing",
    "follow_up_clarity": "Follow-up Clarity",
}
total = sum(int(scores.get(k, 0) or 0) for k in score_labels.keys())
overall = round(total / max(len(score_labels), 1), 1)

st.metric("Overall Score", f"{overall}/10")

cols = st.columns(3)
for i, (key, label) in enumerate(score_labels.items()):
    val = int(scores.get(key, 0) or 0)
    cols[i % 3].metric(label, f"{val}/10",
                        delta="strong" if val >= 8 else (
                              "weak" if val <= 5 else None),
                        delta_color="normal")

st.divider()

# Wins + Improvements
wcol, icol = st.columns(2)
with wcol:
    st.markdown("### Wins")
    wins = review.get("wins") or []
    if wins:
        for w in wins:
            st.markdown(f"- {w}")
    else:
        st.caption("No wins called out.")

with icol:
    st.markdown("### Improvements")
    improvements = review.get("improvements") or []
    for i, imp in enumerate(improvements, 1):
        st.markdown(f"**{i}.** {imp}")

st.divider()

# Follow-up email
st.markdown("### Send-Ready Follow-Up Email")
fu = review.get("follow_up_email") or {}
subject = fu.get("subject", "")
body = fu.get("body", "")
st.text_input("Subject", value=subject, key="coach_fu_subject")
st.text_area("Body", value=body, height=240, key="coach_fu_body")

st.divider()

# Next step
nxt = review.get("next_step", "")
if nxt:
    st.success(f"**Next step:** {nxt}")
