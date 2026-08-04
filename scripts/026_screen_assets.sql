-- Migration 026: Screen assets (what the field audit brings back)
-- Drop into: mctv-bot/scripts/026_screen_assets.sql
-- Run in Supabase SQL Editor.
--
-- Context
-- -------
-- `screen_loops` says how long each screen's loop runs. `loop_items` says what
-- is in it. Neither says anything about the physical thing hanging on the wall:
-- what display it is, how it is mounted, which Raspberry Pi drives it, or
-- whether anyone has laid eyes on it lately.
--
-- This table is where a physical audit lands. One row per license — the same
-- license_id used by screen_loops and loop_item_screens — written by importing
-- a completed field sheet on the Field Audit page.
--
-- license_id is nullable on purpose. Screens whose license number is not yet
-- known (the Tupelo Airport playlist was never captured by the July 2026
-- whitelist sweep) still need somewhere to record what the technician found;
-- the number gets filled in afterwards.

CREATE TABLE IF NOT EXISTS screen_assets (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Identity. license_id is the join key to screen_loops; short_code is the
  -- human-readable label code physically stuck to the Pi (e.g. TUP-6ABE3B).
  license_id       UUID,
  venue_name       TEXT NOT NULL,
  market           TEXT,
  short_code       TEXT,
  screen_label     TEXT,                   -- where this screen sits, when a venue has several

  -- What the technician observed.
  screen_on        TEXT,                   -- Yes | No | No screen found
  content_playing  TEXT,                   -- Yes | Frozen | Black | Error / no signal

  -- The display.
  display_brand    TEXT,
  display_model    TEXT,
  display_size_in  NUMERIC,
  orientation      TEXT,                   -- Landscape | Portrait
  mount_type       TEXT,

  -- The player.
  pi_model         TEXT,
  pi_serial        TEXT,
  power_source     TEXT,                   -- TV USB ports cut power with the TV; worth knowing
  network_type     TEXT,                   -- Wi-Fi | Ethernet | Unknown
  label_applied    TEXT,

  -- Condition and follow-up.
  condition        TEXT,                   -- Good | Fair | Poor | Needs replacement
  issues           TEXT,
  photo_taken      TEXT,                   -- what the technician reported
  photo_url        TEXT,                   -- filled in later, once photos are filed
  notes            TEXT,

  audited_by       TEXT,
  audited_at       DATE,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE screen_assets IS
  'Physical record of each screen: display, mount, Raspberry Pi, condition, and '
  'when it was last laid eyes on. One row per license, written by importing a '
  'completed field-audit sheet. license_id is nullable so screens whose license '
  'number is not yet known can still be recorded.';

COMMENT ON COLUMN screen_assets.short_code IS
  'The code printed on the label affixed to the Pi, e.g. TUP-6ABE3B. Derived '
  'from the license UUID, so it survives venues being added or removed.';

-- One row per license. Partial, so the rows with no license number yet do not
-- collide with each other.
CREATE UNIQUE INDEX IF NOT EXISTS idx_screen_assets_license
  ON screen_assets (license_id)
  WHERE license_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_screen_assets_venue      ON screen_assets (lower(venue_name));
CREATE INDEX IF NOT EXISTS idx_screen_assets_market     ON screen_assets (market);
CREATE INDEX IF NOT EXISTS idx_screen_assets_short_code ON screen_assets (short_code);
CREATE INDEX IF NOT EXISTS idx_screen_assets_audited_at ON screen_assets (audited_at DESC);

ALTER TABLE screen_assets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS screen_assets_service_all ON screen_assets;
CREATE POLICY screen_assets_service_all ON screen_assets
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS screen_assets_select_authenticated ON screen_assets;
CREATE POLICY screen_assets_select_authenticated ON screen_assets
  FOR SELECT TO authenticated USING (true);


-- updated_at trigger, same pattern as loop_items in migration 024.
CREATE OR REPLACE FUNCTION set_screen_assets_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_screen_assets_updated_at ON screen_assets;
CREATE TRIGGER trg_screen_assets_updated_at
  BEFORE UPDATE ON screen_assets
  FOR EACH ROW EXECUTE FUNCTION set_screen_assets_updated_at();
