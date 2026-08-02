-- Copyright (c) 2026 MCTV Digital, Inc. All rights reserved.
-- Migration 025 — Event feeds
--
-- A "feed" is a venue calendar we pull on a schedule and render as loop
-- slides on that venue's screens. event_feeds holds the source config,
-- feed_events holds the normalized pull (cache, fully replaced each refresh).
--
-- Apply by hand in the Supabase SQL editor, same as the other migrations.

-- ── event_feeds ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS event_feeds (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    slug             TEXT NOT NULL UNIQUE,
    market           TEXT NOT NULL DEFAULT 'oxford',

    -- Venue this feed belongs to, matched loosely against sweep/inventory
    -- venue names. Blank while the venue is still a prospect.
    venue_name       TEXT DEFAULT '',

    -- Where the calendar lives. source_url is the human-facing site;
    -- endpoint is the resolved machine-readable URL discovery found.
    source_url       TEXT DEFAULT '',
    source_type      TEXT NOT NULL DEFAULT 'manual'
                     CHECK (source_type IN ('tribe', 'ics', 'manual')),
    endpoint         TEXT DEFAULT '',

    -- Shared calendars (a tourism site) list every venue in town. This
    -- narrows the pull to the one whose screens we feed.
    venue_filter     TEXT DEFAULT '',

    -- Slide rendering
    headline         TEXT DEFAULT '',
    footer           TEXT DEFAULT '',
    events_per_slide INTEGER NOT NULL DEFAULT 4 CHECK (events_per_slide BETWEEN 1 AND 8),
    max_slides       INTEGER NOT NULL DEFAULT 6 CHECK (max_slides BETWEEN 1 AND 20),
    window_days      INTEGER NOT NULL DEFAULT 21 CHECK (window_days BETWEEN 1 AND 365),

    status           TEXT NOT NULL DEFAULT 'prospect'
                     CHECK (status IN ('active', 'paused', 'prospect')),
    notes            TEXT DEFAULT '',

    -- Refresh health. last_status is 'ok' or 'error'; a failed refresh keeps
    -- the previous events so a screen never goes blank on a bad morning.
    last_fetched_at  TIMESTAMPTZ,
    last_status      TEXT DEFAULT '',
    last_error       TEXT DEFAULT '',
    event_count      INTEGER NOT NULL DEFAULT 0,

    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_feeds_market ON event_feeds (market);
CREATE INDEX IF NOT EXISTS idx_event_feeds_status ON event_feeds (status);

-- ── feed_events ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS feed_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feed_id     UUID NOT NULL REFERENCES event_feeds (id) ON DELETE CASCADE,

    -- Source-side identifier, used to dedupe. Blank for hand-entered events,
    -- which fall back to title + start date.
    uid         TEXT DEFAULT '',
    title       TEXT NOT NULL,
    starts_at   TIMESTAMPTZ NOT NULL,
    ends_at     TIMESTAMPTZ,
    all_day     BOOLEAN NOT NULL DEFAULT FALSE,
    venue       TEXT DEFAULT '',
    url         TEXT DEFAULT '',
    categories  JSONB NOT NULL DEFAULT '[]'::JSONB,
    description TEXT DEFAULT '',

    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feed_events_feed ON feed_events (feed_id, starts_at);

-- ── RLS ─────────────────────────────────────────────────────────────────────
-- Internal tables: the app reaches them with the service role, same as the
-- other operations tables. Enabled with no permissive policy so anon and
-- authenticated clients get nothing.

ALTER TABLE event_feeds ENABLE ROW LEVEL SECURITY;
ALTER TABLE feed_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service role manages event_feeds" ON event_feeds;
CREATE POLICY "service role manages event_feeds" ON event_feeds
    FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

DROP POLICY IF EXISTS "service role manages feed_events" ON feed_events;
CREATE POLICY "service role manages feed_events" ON feed_events
    FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
