# Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
# Proprietary and confidential.
"""Event Feeds — Streamlit page for the MCTV Team Member portal.

A feed is a venue's public calendar, pulled on a schedule and rendered as
loop slides for that venue's screens. The venue gets an always-current event
board they don't have to maintain; we get a standing reason to be on the wall.

Four tabs:

    Feeds    every feed with its refresh health, and Add feed
    Source   where a feed pulls from — discover, test, or import by hand
    Slides   what actually goes on screen, previewed and exportable
    Pitch    the one-screen brief for selling the feed to the venue

Drop into: mctv-bot/pages/26_Feeds.py
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from services.auth import check_password
from services.event_feed_service import (
    DEFAULT_EVENTS_PER_SLIDE,
    DEFAULT_MAX_SLIDES,
    DEFAULT_WINDOW_DAYS,
    MARKETS,
    SOURCE_TYPES,
    STATUSES,
    FeedFetchError,
    delete_feed,
    discover,
    feed_health,
    feed_slides,
    fetch_feed_events,
    format_event_date,
    format_event_time,
    get_events,
    get_feeds,
    import_events,
    market_label,
    parse_ics,
    refresh_all,
    refresh_feed,
    save_feed,
    slides_to_html,
    slides_to_text,
    update_feed,
)

st.set_page_config(
    page_title="Event Feeds - MCTV Bot",
    page_icon="\U0001F4C5",
    layout="wide",
)

if not check_password():
    st.stop()

from services.team_ui import render_team_sidebar
render_team_sidebar()

st.title("\U0001F4C5 Event Feeds")
st.caption(
    "Pull a venue's calendar, render it as loop slides, keep it current without "
    "anyone retyping a tournament schedule."
)

HEALTH_ICON = {"ok": "\U0001F7E2", "warn": "\U0001F7E1", "error": "\U0001F534"}

# One fetch per rerun, passed into every tab — same convention as the
# Pipeline and Loop Inventory pages.
feeds = get_feeds()


# ── Header metrics ───────────────────────────────────────────────────────────

active = [f for f in feeds if f.get("status") == "active"]
unhealthy = [f for f in feeds if feed_health(f)["level"] != "ok" and f.get("status") == "active"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Feeds", len(feeds))
col2.metric("Live", len(active))
col3.metric("Needs attention", len(unhealthy))
col4.metric("Events cached", sum(int(f.get("event_count") or 0) for f in feeds))

tab_feeds, tab_source, tab_slides, tab_pitch = st.tabs(
    ["Feeds", "Source", "Slides", "Pitch"]
)


# ── Tab: Feeds ───────────────────────────────────────────────────────────────

with tab_feeds:
    top_left, top_right = st.columns([3, 1])
    with top_right:
        if st.button("\U0001F504 Refresh all live feeds", use_container_width=True):
            results = refresh_all()
            if not results:
                st.info("No live feeds to refresh.")
            for result in results:
                if result["ok"]:
                    st.success(f"{result['feed']}: {result['count']} events")
                else:
                    st.error(f"{result['feed']}: {result['error']}")
            st.rerun()

    if not feeds:
        st.info(
            "No feeds yet. Add one below — start with the venue's website and let "
            "Discover find the calendar."
        )
    else:
        rows = []
        for feed in feeds:
            health = feed_health(feed)
            rows.append({
                "": HEALTH_ICON.get(health["level"], ""),
                "Feed": feed.get("name", ""),
                "Market": market_label(feed.get("market", "")),
                "Status": feed.get("status", ""),
                "Source": SOURCE_TYPES.get(feed.get("source_type", ""), feed.get("source_type", "")),
                "Events": int(feed.get("event_count") or 0),
                "Health": health["message"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()

    with st.expander("➕ Add a feed", expanded=not feeds):
        with st.form("add_feed"):
            name_col, market_col = st.columns([2, 1])
            name = name_col.text_input(
                "Venue name *", placeholder="mTrade Park",
                help="Shows in the feed list and seeds the default headline.",
            )
            market = market_col.selectbox(
                "Market", MARKETS, format_func=market_label,
            )

            source_url = st.text_input(
                "Calendar website", placeholder="https://mtradepark.com",
                help="The venue's site. Discover probes it for a machine-readable calendar.",
            )
            venue_filter = st.text_input(
                "Venue filter (optional)",
                help=(
                    "Only needed on shared calendars — a tourism site lists every "
                    "venue in town. Leave blank for a venue's own site."
                ),
            )

            head_col, foot_col = st.columns(2)
            headline = head_col.text_input(
                "Slide headline", placeholder="This Week at mTrade Park",
            )
            footer = foot_col.text_input(
                "Slide footer", placeholder="mtradepark.com",
            )

            status = st.selectbox(
                "Status", STATUSES, index=STATUSES.index("prospect"),
                help=(
                    "'prospect' while we're still pitching the venue — the feed "
                    "runs and previews, but Refresh all skips it."
                ),
            )
            notes = st.text_area("Notes", height=80)

            if st.form_submit_button("Create feed", type="primary"):
                if not name.strip():
                    st.error("Venue name is required.")
                else:
                    try:
                        created = save_feed({
                            "name": name, "market": market, "source_url": source_url,
                            "venue_filter": venue_filter, "headline": headline,
                            "footer": footer, "status": status, "notes": notes,
                            "venue_name": name,
                        })
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        if created:
                            st.success(
                                f"Created **{name}**. Open the Source tab to point it "
                                "at their calendar."
                            )
                            st.session_state["feed_selected"] = created.get("id")
                            st.rerun()
                        else:
                            st.error("Could not save the feed.")


# ── Feed picker shared by Source / Slides / Pitch ────────────────────────────

def pick_feed(key: str) -> dict | None:
    """Feed selector that remembers the choice across tabs."""
    if not feeds:
        st.info("Add a feed on the Feeds tab first.")
        return None
    ids = [f["id"] for f in feeds]
    remembered = st.session_state.get("feed_selected")
    index = ids.index(remembered) if remembered in ids else 0
    chosen = st.selectbox(
        "Feed", ids, index=index, key=key,
        format_func=lambda i: next(
            (f"{f['name']} ({market_label(f.get('market', ''))})"
             for f in feeds if f["id"] == i), i
        ),
    )
    st.session_state["feed_selected"] = chosen
    return next((f for f in feeds if f["id"] == chosen), None)


# ── Tab: Source ──────────────────────────────────────────────────────────────

with tab_source:
    feed = pick_feed("source_feed")
    if feed:
        health = feed_health(feed)
        {"ok": st.success, "warn": st.warning, "error": st.error}[health["level"]](
            f"{HEALTH_ICON[health['level']]} {health['message']}"
        )

        st.subheader("Where it pulls from")

        url_col, button_col = st.columns([3, 1])
        source_url = url_col.text_input(
            "Calendar website", value=feed.get("source_url") or "",
            key="src_url", placeholder="https://mtradepark.com",
        )
        button_col.write("")
        button_col.write("")
        if button_col.button("\U0001F50D Discover", use_container_width=True):
            if not source_url.strip():
                st.error("Enter the venue's website first.")
            else:
                with st.spinner("Probing for a calendar endpoint..."):
                    found = discover(source_url)
                if found["source_type"]:
                    update_feed(feed["id"], {
                        "source_url": source_url, "source_type": found["source_type"],
                        "endpoint": found["endpoint"],
                    })
                    st.success(
                        f"Found a {SOURCE_TYPES[found['source_type']]} feed with "
                        f"{found['event_count']} events."
                    )
                    st.rerun()
                else:
                    st.warning(
                        "No machine-readable calendar found. What each path said:"
                    )
                    for attempt in found["attempts"]:
                        st.caption(f"- `{attempt['endpoint']}` — {attempt['detail']}")
                    st.info(
                        "If the site refused the request, it's behind a bot filter. "
                        "Use **Import by hand** below — ask the venue for an .ics "
                        "export or a calendar share link, which is a fair thing to "
                        "ask for while you're selling them the screens anyway."
                    )

        type_col, endpoint_col = st.columns([1, 3])
        source_type = type_col.selectbox(
            "Source type", list(SOURCE_TYPES),
            index=list(SOURCE_TYPES).index(feed.get("source_type") or "manual"),
            format_func=lambda t: SOURCE_TYPES[t], key="src_type",
        )
        endpoint = endpoint_col.text_input(
            "Endpoint", value=feed.get("endpoint") or "", key="src_endpoint",
            help="Filled in by Discover. Paste one directly if you already know it.",
        )

        venue_filter = st.text_input(
            "Venue filter", value=feed.get("venue_filter") or "", key="src_filter",
            help="Only for shared calendars that list more than one venue.",
        )

        save_col, test_col = st.columns(2)
        if save_col.button("Save source", type="primary", use_container_width=True):
            update_feed(feed["id"], {
                "source_url": source_url, "source_type": source_type,
                "endpoint": endpoint, "venue_filter": venue_filter,
            })
            st.success("Saved.")
            st.rerun()

        if test_col.button("\U0001F9EA Test fetch", use_container_width=True):
            probe = dict(feed)
            probe.update({"source_type": source_type, "endpoint": endpoint})
            try:
                with st.spinner("Fetching..."):
                    raw = fetch_feed_events(probe)
                st.success(f"Fetched {len(raw)} raw events before filtering.")
                if raw:
                    st.dataframe(
                        pd.DataFrame([{
                            "Title": e.get("title", ""), "Starts": e.get("starts_at", ""),
                            "Venue": e.get("venue", ""),
                        } for e in raw[:15]]),
                        use_container_width=True, hide_index=True,
                    )
            except FeedFetchError as exc:
                st.error(str(exc))

        st.divider()
        st.subheader("Slide settings")

        set1, set2, set3 = st.columns(3)
        per_slide = set1.number_input(
            "Events per slide", 1, 8,
            int(feed.get("events_per_slide") or DEFAULT_EVENTS_PER_SLIDE),
            help="Four reads cleanly from across a room. More than six gets small.",
        )
        max_slides = set2.number_input(
            "Max slides", 1, 20, int(feed.get("max_slides") or DEFAULT_MAX_SLIDES),
            help="Caps how much of the loop the feed can take.",
        )
        window_days = set3.number_input(
            "Window (days ahead)", 1, 365,
            int(feed.get("window_days") or DEFAULT_WINDOW_DAYS),
        )

        head_col, foot_col = st.columns(2)
        headline = head_col.text_input("Headline", value=feed.get("headline") or "")
        footer = foot_col.text_input("Footer", value=feed.get("footer") or "")

        stat_col, notes_col = st.columns([1, 2])
        status = stat_col.selectbox(
            "Status", STATUSES,
            index=STATUSES.index(feed.get("status") or "prospect"), key="src_status",
        )
        notes = notes_col.text_area("Notes", value=feed.get("notes") or "", height=90)

        if st.button("Save slide settings", type="primary"):
            update_feed(feed["id"], {
                "events_per_slide": int(per_slide), "max_slides": int(max_slides),
                "window_days": int(window_days), "headline": headline,
                "footer": footer, "status": status, "notes": notes,
            })
            st.success("Saved.")
            st.rerun()

        st.divider()
        with st.expander("\U0001F4E5 Import by hand (pasted .ics)"):
            st.caption(
                "The fallback when a site blocks automated fetches. Export the "
                "calendar from the venue's system, or paste a share link's .ics "
                "contents here. This replaces the feed's cached events."
            )
            pasted = st.text_area("iCalendar text", height=200,
                                  placeholder="BEGIN:VCALENDAR ...")
            if st.button("Import events"):
                if not pasted.strip():
                    st.error("Paste the .ics contents first.")
                else:
                    try:
                        parsed = parse_ics(pasted)
                    except FeedFetchError as exc:
                        st.error(str(exc))
                    else:
                        result = import_events(feed["id"], parsed)
                        if result["ok"]:
                            st.success(
                                f"Imported {result['count']} events "
                                f"(from {len(parsed)} in the file)."
                            )
                            st.rerun()
                        else:
                            st.error(result["error"])

        with st.expander("\U0001F5D1 Delete this feed"):
            st.caption("Removes the feed and its cached events. Not reversible.")
            if st.button("Delete feed", type="secondary"):
                if delete_feed(feed["id"]):
                    st.session_state.pop("feed_selected", None)
                    st.success("Deleted.")
                    st.rerun()
                else:
                    st.error("Could not delete the feed.")


# ── Tab: Slides ──────────────────────────────────────────────────────────────

with tab_slides:
    feed = pick_feed("slides_feed")
    if feed:
        action_col, _ = st.columns([1, 3])
        if action_col.button("\U0001F504 Refresh now", type="primary",
                             use_container_width=True):
            result = refresh_feed(feed["id"])
            if result["ok"]:
                st.success(f"Pulled {result['count']} events.")
            else:
                st.error(result["error"])
                st.caption("Previous events kept — the screen won't go blank.")
            st.rerun()

        events = get_events(feed["id"])
        if not events:
            st.info(
                "No events cached yet. Refresh now, or import by hand from the "
                "Source tab."
            )
        else:
            st.dataframe(
                pd.DataFrame([{
                    "When": format_event_date(e),
                    "Time": format_event_time(e),
                    "Event": e.get("title", ""),
                    "Venue": e.get("venue", ""),
                } for e in events]),
                use_container_width=True, hide_index=True,
            )

            slides = feed_slides(feed, events)
            st.subheader(f"On screen — {len(slides)} slide(s)")

            html = slides_to_html(slides, title=f"{feed.get('name', '')} — Event Feed")
            st.components.v1.html(html, height=760, scrolling=True)

            dl1, dl2 = st.columns(2)
            dl1.download_button(
                "⬇ Download preview (HTML)", data=html,
                file_name=f"{feed.get('slug', 'feed')}-preview.html",
                mime="text/html", use_container_width=True,
            )
            dl2.download_button(
                "⬇ Download slide script (TXT)", data=slides_to_text(slides),
                file_name=f"{feed.get('slug', 'feed')}-slides.txt",
                mime="text/plain", use_container_width=True,
                help="Hand this to whoever builds the creative.",
            )


# ── Tab: Pitch ───────────────────────────────────────────────────────────────

with tab_pitch:
    feed = pick_feed("pitch_feed")
    if feed:
        events = get_events(feed["id"])
        slides = feed_slides(feed, events)
        name = feed.get("name", "the venue")

        st.subheader(f"Selling the feed to {name}")
        st.markdown(f"""
**The offer.** We run their event calendar on their screens, current every day,
with nobody at {name} maintaining it. It pulls straight from the calendar they
already publish — if they add a tournament to their website, it's on the screens
the next refresh.

**Why it opens the door.** A feed is not an ad buy, so there's nothing for them
to approve, budget, or explain to a board. It's content they already own, shown
to people already standing there. The screens go in to carry it, and the paid
inventory around it is the business.

**What's ready to show them right now:**

- {len(events)} events in the next {feed.get('window_days', DEFAULT_WINDOW_DAYS)} days
- {len(slides)} slide(s) of loop content, refreshed automatically
- A live preview on the Slides tab you can pull up on a phone in their office
""")

        if feed.get("notes"):
            st.info(feed["notes"])

        st.caption(
            "Download the HTML preview from the Slides tab and open it on a tablet — "
            "showing the board built from their own calendar lands better than "
            "describing it."
        )
