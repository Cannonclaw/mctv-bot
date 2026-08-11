-- Migration 025: Venue events (the schedule behind the lobby feed board)
-- Drop into: mctv-bot/scripts/025_venue_events.sql
-- Run in Supabase SQL Editor.
--
-- Context
-- -------
-- Host venues that run programming — the Oxford Conference Center first — want
-- their day's schedule on the MCTV screen in the lobby, the way an airport
-- board shows departures. This table is that schedule. One row per event per
-- venue, entered by hand (by the team or by the venue), read by the public
-- feed board at GET /board.
--
-- Deliberately NOT modelled on loop_items: a loop item is a creative that
-- plays in rotation, an event is a thing happening in a room at a time. They
-- share a screen and nothing else.
--
-- Privacy matters here. A conference center hosts private functions whose
-- names should not go on a public screen. `is_private` keeps the row (so the
-- room reads as occupied) while the board renders it as "Private Event" —
-- masking happens in venue_events_service.board_payload(), not here, so the
-- internal record stays intact.

-- =============================================================================
-- 1. Events
-- =============================================================================

CREATE TABLE IF NOT EXISTS venue_events (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  venue_slug    TEXT NOT NULL,          -- url key, e.g. 'oxford-conference-center'
  venue_name    TEXT NOT NULL,          -- display name for the board header
  title         TEXT NOT NULL,          -- event name as the public should see it
  host_org      TEXT,                   -- who is holding it (shown under the title)
  room          TEXT,                   -- 'Ballroom A', 'Magnolia Room', ...
  starts_at     TIMESTAMPTZ NOT NULL,
  ends_at       TIMESTAMPTZ,            -- NULL = open-ended, board shows start only
  all_day       BOOLEAN NOT NULL DEFAULT FALSE,
  is_private    BOOLEAN NOT NULL DEFAULT FALSE,  -- board masks title + host_org
  status        TEXT NOT NULL DEFAULT 'scheduled'
                CHECK (status IN ('scheduled','cancelled','postponed')),
  public_note   TEXT,                   -- one line shown on screen ('Check in at the lobby')
  internal_note TEXT,                   -- never rendered on the board
  source        TEXT NOT NULL DEFAULT 'manual',  -- 'manual' today; 'ical'/'import' later
  external_id   TEXT,                   -- upstream id when a feed ever supplies one
  created_by    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT venue_events_time_order CHECK (ends_at IS NULL OR ends_at >= starts_at)
);

COMMENT ON TABLE venue_events IS
  'Schedule rows for host venues that run programming. Read by the public feed '
  'board at GET /board (see server_routes.py + services/venue_events_service.py). '
  'is_private keeps the booking on the books while the board shows "Private Event".';

-- The board only ever asks for one venue and one window at a time.
CREATE INDEX IF NOT EXISTS idx_venue_events_venue_start
  ON venue_events (venue_slug, starts_at);

CREATE INDEX IF NOT EXISTS idx_venue_events_start ON venue_events (starts_at);

-- Same event typed twice is the likeliest data-entry mistake on a shared login.
CREATE UNIQUE INDEX IF NOT EXISTS idx_venue_events_dedupe
  ON venue_events (venue_slug, starts_at, lower(title));

-- Feed imports (if one is ever wired up) need somewhere to land idempotently.
CREATE UNIQUE INDEX IF NOT EXISTS idx_venue_events_external
  ON venue_events (venue_slug, external_id)
  WHERE external_id IS NOT NULL;

ALTER TABLE venue_events ENABLE ROW LEVEL SECURITY;

-- No anon policy on purpose. The board is public but it is served by our own
-- route, which reads this table with the service key and masks private rows on
-- the way out. Granting anon SELECT would hand the raw schedule — private
-- titles and internal notes included — to anyone with the project URL.
DROP POLICY IF EXISTS venue_events_service_all ON venue_events;
CREATE POLICY venue_events_service_all ON venue_events
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS venue_events_select_authenticated ON venue_events;
CREATE POLICY venue_events_select_authenticated ON venue_events
  FOR SELECT TO authenticated USING (true);


-- =============================================================================
-- 2. updated_at trigger
-- =============================================================================

CREATE OR REPLACE FUNCTION set_venue_events_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_venue_events_updated_at ON venue_events;
CREATE TRIGGER trg_venue_events_updated_at
  BEFORE UPDATE ON venue_events
  FOR EACH ROW EXECUTE FUNCTION set_venue_events_updated_at();


-- =============================================================================
-- 3. SAMPLE DATA — Oxford Conference Center
-- =============================================================================
-- These are made-up bookings so the board has something to render the moment
-- the migration lands. REPLACE THEM with the real schedule. To clear:
--
--   DELETE FROM venue_events WHERE created_by = 'sample';
--
-- Times are Central (America/Chicago), which is what the board renders in.
-- Dates are relative to whenever this runs, so the board is never empty on the
-- day someone first opens it.

INSERT INTO venue_events
  (venue_slug, venue_name, title, host_org, room, starts_at, ends_at,
   is_private, public_note, source, created_by)
SELECT * FROM (VALUES
  ('oxford-conference-center', 'Oxford Conference Center',
   'Lafayette County Chamber Breakfast', 'Oxford-Lafayette Chamber of Commerce',
   'Ballroom A',
   (CURRENT_DATE + TIME '07:30') AT TIME ZONE 'America/Chicago',
   (CURRENT_DATE + TIME '09:00') AT TIME ZONE 'America/Chicago',
   FALSE, 'Check in at the lobby table', 'manual', 'sample'),

  ('oxford-conference-center', 'Oxford Conference Center',
   'North Mississippi Small Business Workshop', 'MS Small Business Development',
   'Magnolia Room',
   (CURRENT_DATE + TIME '10:00') AT TIME ZONE 'America/Chicago',
   (CURRENT_DATE + TIME '12:30') AT TIME ZONE 'America/Chicago',
   FALSE, NULL, 'manual', 'sample'),

  ('oxford-conference-center', 'Oxford Conference Center',
   'Private Event', NULL,
   'Ballroom B',
   (CURRENT_DATE + TIME '11:00') AT TIME ZONE 'America/Chicago',
   (CURRENT_DATE + TIME '14:00') AT TIME ZONE 'America/Chicago',
   TRUE, NULL, 'manual', 'sample'),

  ('oxford-conference-center', 'Oxford Conference Center',
   'Ole Miss Alumni Association Reception', 'Ole Miss Alumni Association',
   'Ballroom A',
   (CURRENT_DATE + TIME '17:30') AT TIME ZONE 'America/Chicago',
   (CURRENT_DATE + TIME '20:00') AT TIME ZONE 'America/Chicago',
   FALSE, 'Doors at 5:15', 'manual', 'sample'),

  ('oxford-conference-center', 'Oxford Conference Center',
   'Mississippi Tourism Association Annual Meeting', 'MS Tourism Association',
   'Ballroom A + B',
   (CURRENT_DATE + INTERVAL '1 day' + TIME '08:30') AT TIME ZONE 'America/Chicago',
   (CURRENT_DATE + INTERVAL '1 day' + TIME '16:00') AT TIME ZONE 'America/Chicago',
   FALSE, 'Registration opens at 8:00', 'manual', 'sample')
) AS seed (venue_slug, venue_name, title, host_org, room, starts_at, ends_at,
           is_private, public_note, source, created_by)
WHERE NOT EXISTS (
  SELECT 1 FROM venue_events WHERE created_by = 'sample'
);
