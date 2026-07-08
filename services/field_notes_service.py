# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution,
# or modification of this file is strictly prohibited.
"""Voice Field Notes service.

End-to-end ingest pipeline for team member dictated notes:

    raw audio bytes
        -> Supabase storage upload
        -> Anthropic Claude (Sonnet 4.6 audio input): transcript + structured extraction
        -> Supabase row save

Reuses existing dependencies only — no openai, no audio_recorder library.

Drop into: mctv-bot/services/field_notes_service.py
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import anthropic
from supabase import create_client, Client

logger = logging.getLogger("field_notes")

BUCKET = "field-notes-audio"
CLAUDE_MODEL = "claude-sonnet-4-6"
MAX_AUDIO_SECONDS = 600
CUSTOMER_CANDIDATE_LIMIT = 200


_supabase: Client | None = None
_anthropic: anthropic.Anthropic | None = None


def _sb() -> Client:
    global _supabase
    if _supabase is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
        _supabase = create_client(url, key)
    return _supabase


def _claude() -> anthropic.Anthropic:
    global _anthropic
    if _anthropic is None:
        _anthropic = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _anthropic


def _current_team_member_id() -> str:
    try:
        import streamlit as st
        tm = (
            st.session_state.get("team_member")
            or st.session_state.get("current_user")
            or st.session_state.get("user")
            or {}
        )
        if isinstance(tm, dict) and tm.get("id"):
            return tm["id"]
        if isinstance(tm, str):
            return tm
    except Exception:
        pass
    return os.environ.get("MCTV_DEFAULT_TEAM_MEMBER_ID", "system")


def process_note(
    *,
    audio_bytes: bytes,
    team_member_id: str | None = None,
    filename_hint: str = "field_note.wav",
    location_lat: float | None = None,
    location_lng: float | None = None,
) -> dict[str, Any]:
    tm_id = team_member_id or _current_team_member_id()
    audio_path = _upload_audio(tm_id, audio_bytes, filename_hint)
    transcript, structured = _transcribe_and_structure(audio_bytes, filename_hint)
    row = _save_note(
        team_member_id=tm_id,
        audio_url=audio_path,
        transcript=transcript,
        structured=structured,
        location_lat=location_lat,
        location_lng=location_lng,
    )
    logger.info("field_notes: saved %s", row.get("id"))
    return row


def list_recent_notes(team_member_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    tm_id = team_member_id or _current_team_member_id()
    res = (
        _sb()
        .table("field_notes")
        .select("*")
        .eq("team_member_id", tm_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def search_notes(query: str, team_member_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    tm_id = team_member_id or _current_team_member_id()
    # PostgREST .or_() filters are comma/paren-delimited — strip those chars
    # from user input so a search like "Smith, John (Oxford)" can't break
    # the filter syntax and crash the page.
    safe = "".join(ch if ch not in ',()"' else " " for ch in query).strip()
    if not safe:
        return list_recent_notes(team_member_id=tm_id, limit=limit)
    pattern = f"%{safe}%"
    res = (
        _sb()
        .table("field_notes")
        .select("*")
        .eq("team_member_id", tm_id)
        .or_(f"raw_transcript.ilike.{pattern},summary.ilike.{pattern}")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def mark_action_item_done(note_id: str, action_item_index: int) -> None:
    # Used as a Streamlit on_change callback — must never raise, or the
    # whole page run dies on a transient DB hiccup.
    try:
        res = (
            _sb()
            .table("field_notes")
            .select("action_items")
            .eq("id", note_id)
            .single()
            .execute()
        )
        items = (res.data or {}).get("action_items") or []
        if 0 <= action_item_index < len(items):
            items[action_item_index]["done"] = not items[action_item_index].get("done", False)
            _sb().table("field_notes").update({"action_items": items}).eq("id", note_id).execute()
    except Exception as e:
        logger.warning("field_notes: could not toggle action item %s[%s]: %s", note_id, action_item_index, e)


_AUDIO_MIME = {
    "wav": "audio/wav",
    "webm": "audio/webm",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "ogg": "audio/ogg",
}


def _upload_audio(team_member_id: str, audio_bytes: bytes, filename_hint: str) -> str:
    ext = filename_hint.rsplit(".", 1)[-1].lower() if "." in filename_hint else "wav"
    if ext not in _AUDIO_MIME:
        ext = "wav"
    object_name = f"{team_member_id}/{uuid.uuid4()}.{ext}"
    try:
        _sb().storage.from_(BUCKET).upload(
            path=object_name,
            file=audio_bytes,
            file_options={"content-type": _AUDIO_MIME[ext]},
        )
    except Exception as e:
        logger.warning("field_notes: storage upload failed (%s); continuing without audio file", e)
        return ""
    return object_name


def _transcribe_and_structure(audio_bytes: bytes, filename_hint: str):
    ext = filename_hint.rsplit(".", 1)[-1].lower() if "." in filename_hint else "wav"
    media_type = _AUDIO_MIME.get(ext, "audio/wav")
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

    candidate_lines = "\n".join(
        f"- {c['name']} (id: {c['id']})" for c in _candidate_customers()
    )

    system = (
        "You are a sales-operations assistant for MCTV Elite Advertising, an indoor "
        "digital billboard network in North Mississippi. Listen to a voice memo from "
        "a sales team member in the field and return STRICT JSON only — no markdown, "
        "no commentary — with this exact shape:\n"
        "{\n"
        '  "transcript": "verbatim transcription of the audio",\n'
        '  "summary": "one short sentence capturing the gist",\n'
        '  "customer_match": {\n'
        '      "id": "<uuid or null>",\n'
        '      "name": "<best-guess customer name or null>",\n'
        '      "confidence": 0.0-1.0\n'
        "  } or null,\n"
        '  "action_items": [\n'
        '     {"text": "...", "due_date": "YYYY-MM-DD or null", "owner": "...", "done": false}\n'
        "  ],\n"
        '  "sentiment": "positive|neutral|negative|mixed",\n'
        '  "tags": ["..."]\n'
        "}\n"
        "Set customer_match.id ONLY when confidence >= 0.80, otherwise leave id null. "
        "Only extract action items the speaker clearly stated. "
        "Resolve relative dates like 'Friday' or 'in 3 days' against today's date."
    )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d (%A)")
    user_text = (
        f"Today's date: {today}\n\n"
        f"Known customers (id and name):\n{candidate_lines}\n\n"
        "Now transcribe the attached audio and return the JSON structure described."
    )

    msg = _claude().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=system,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "audio",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": audio_b64,
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            }
        ],
    )

    raw = msg.content[0].text
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("field_notes: Claude returned non-JSON, salvaging transcript only: %s", exc)
        return raw[:5000], {
            "summary": raw[:200],
            "customer_match": None,
            "action_items": [],
            "sentiment": "neutral",
            "tags": [],
        }

    transcript = data.pop("transcript", "")
    return transcript, data


def _candidate_customers():
    # Live schema: the CRM table is `clients` with `business_name`
    # (there is no `customers` table).
    try:
        res = (
            _sb()
            .table("clients")
            .select("id, business_name")
            .order("created_at", desc=True)
            .limit(CUSTOMER_CANDIDATE_LIMIT)
            .execute()
        )
        return [
            {"id": r["id"], "name": r.get("business_name") or "(unnamed)"}
            for r in (res.data or [])
        ]
    except Exception as e:
        logger.warning("field_notes: could not load customer candidates: %s", e)
        return []


def _save_note(
    *,
    team_member_id: str,
    audio_url: str,
    transcript: str,
    structured,
    location_lat,
    location_lng,
):
    customer_id = None
    customer_match = structured.get("customer_match") or None
    if customer_match and customer_match.get("id"):
        customer_id = customer_match["id"]

    row = {
        "team_member_id": team_member_id,
        "customer_id": customer_id,
        "audio_url": audio_url,
        "raw_transcript": transcript,
        "summary": structured.get("summary"),
        "structured_data": structured,
        "action_items": structured.get("action_items") or [],
        "sentiment": structured.get("sentiment", "neutral"),
        "tags": structured.get("tags") or [],
        "location_lat": location_lat,
        "location_lng": location_lng,
    }

    res = _sb().table("field_notes").insert(row).execute()
    return (res.data or [{}])[0]
