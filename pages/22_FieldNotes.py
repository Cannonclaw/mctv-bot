# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Voice Field Notes — Streamlit page for the MCTV Team Member portal.

Tap-to-record voice memos that get transcribed by Claude (audio input),
structured into summary + customer match + action items, and saved to
Supabase for searching and follow-up. Designed for mobile use in the field.

Drop into: mctv-bot/pages/22_FieldNotes.py
"""

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.field_notes_service import (
    process_note,
    list_recent_notes,
    search_notes,
    mark_action_item_done,
)

st.set_page_config(
    page_title="Field Notes - MCTV Bot",
    page_icon="\U0001F399",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()


st.markdown("## \U0001F399 Field Notes")
st.caption(
    "Tap record, speak your note, tap stop. Transcribes, extracts customer + action items, "
    "and saves to your account. Best from your phone."
)

audio_value = st.audio_input(
    "Tap the microphone to record",
    key="field_notes_recorder",
    help="Your phone will ask for microphone permission once. Stop when you finish speaking.",
)

with st.expander("\U0001F4A1 Tips", expanded=False):
    st.markdown(
        "- Say the **customer name** out loud (e.g. 'Cardiology Associates') so it auto-links.\n"
        "- Say a **specific due date** ('follow up Friday' or 'in 3 days') and we'll capture the action item.\n"
        "- Keep notes under 2 minutes — long memos work but the structure pass is sharper on short ones.\n"
        "- All notes are searchable later — speak naturally; the cleanup happens in the background."
    )

if audio_value is not None:
    audio_bytes = audio_value.getvalue()
    cache_key = hash(audio_bytes)

    if st.session_state.get("last_processed_key") != cache_key:
        st.session_state["last_processed_key"] = cache_key
        with st.spinner("Transcribing and structuring your note..."):
            try:
                note = process_note(audio_bytes=audio_bytes)
                st.session_state["latest_note"] = note
                st.success(f"✓ Saved as note `{note['id'][:8]}...`")
            except Exception as e:
                st.error(f"Could not process this recording: {e}")
                st.session_state.pop("latest_note", None)

    note = st.session_state.get("latest_note")
    if note:
        with st.container(border=True):
            st.subheader("Just saved")
            st.write(f"**Summary:** {note.get('summary') or '(no summary)'}")

            customer_match = (note.get("structured_data") or {}).get("customer_match")
            if customer_match and customer_match.get("name"):
                confidence = customer_match.get("confidence", 0)
                badge = "\U0001F7E2 linked" if customer_match.get("id") else "\U0001F7E1 suggested"
                st.write(
                    f"**Customer:** {customer_match['name']}  ·  {badge} "
                    f"(confidence {confidence:.0%})"
                )

            action_items = note.get("action_items") or []
            if action_items:
                st.write("**Action items:**")
                for i, ai in enumerate(action_items):
                    label = ai.get("text", "")
                    if ai.get("due_date"):
                        label += f"  ·  due {ai['due_date']}"
                    if ai.get("owner"):
                        label += f"  ·  owner {ai['owner']}"
                    st.checkbox(
                        label,
                        value=ai.get("done", False),
                        key=f"ai_{note['id']}_{i}",
                        on_change=mark_action_item_done,
                        args=(note["id"], i),
                    )

            with st.expander("Full transcript"):
                st.write(note.get("raw_transcript") or "")

st.divider()
st.subheader("Your recent notes")

query = st.text_input("Search your notes", placeholder="customer name, keyword, or phrase")
notes = search_notes(query, limit=25) if query else list_recent_notes(limit=25)

if not notes:
    st.caption("No notes yet — your dictations will show up here.")
else:
    for n in notes:
        header = (
            f"{n['created_at'][:16].replace('T', ' ')}  ·  "
            f"{n.get('summary') or '(no summary)'}"
        )
        with st.expander(header):
            customer_match = (n.get("structured_data") or {}).get("customer_match") or {}
            if n.get("customer_id"):
                st.caption(f"\U0001F7E2 Linked customer ID: `{n['customer_id']}`")
            elif customer_match.get("name"):
                st.caption(
                    f"\U0001F7E1 Suggested customer: "
                    f"{customer_match['name']} (not auto-linked)"
                )

            action_items = n.get("action_items") or []
            if action_items:
                st.write("**Action items:**")
                for i, ai in enumerate(action_items):
                    line = ai.get("text", "")
                    if ai.get("due_date"):
                        line += f" — due {ai['due_date']}"
                    if ai.get("done"):
                        line = f"~~{line}~~ ✓"
                    st.write(f"- {line}")

            st.write(n.get("raw_transcript", ""))
