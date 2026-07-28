-- Migration 024: Screen Inventory (what actually plays where)
-- Drop into: mctv-bot/scripts/024_screen_inventory.sql
-- Run in Supabase SQL Editor.
--
-- Context
-- -------
-- `screen_loops` (migration from the July 2026 n-compass whitelist sweep) tells
-- us HOW MUCH each screen plays — loop_seconds and item_count per license — but
-- not WHAT. This migration adds the manual book of record for the "what":
--
--   loop_items         one row per creative in a market's loop (the inventory)
--   loop_item_screens  per-screen include/exclude overrides (the whitelist)
--
-- The n-compass model is playlist + per-license whitelist, so the inventory
-- mirrors it: an item is run-of-network across its market by default, and
-- exceptions are recorded as overrides. Expected loop for a screen is then:
--
--   items = run_of_network items in the market not excluded from that screen
--         + items explicitly included on that screen
--
-- ...which reconciles against screen_loops.item_count / loop_seconds, and
-- against the Encompass/NTV360 play export on (venue_name, file_name).

-- =============================================================================
-- 1. Loop items — the creatives in a market's loop
-- =============================================================================

CREATE TABLE IF NOT EXISTS loop_items (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  market           TEXT NOT NULL,          -- oxford | starkville | tupelo | columbus | west_point
  file_name        TEXT NOT NULL,          -- Encompass content file name (join key to play reports)
  advertiser       TEXT,                   -- business the spot belongs to
  client_id        TEXT,                   -- clients.id when the advertiser is a portal client
  bucket           TEXT NOT NULL DEFAULT 'paid'
                   CHECK (bucket IN ('paid','host','house','psa','trade','community')),
  duration_seconds INTEGER NOT NULL DEFAULT 15 CHECK (duration_seconds > 0),
  monthly_value    NUMERIC,                -- paid items only; drives $-at-risk math
  status           TEXT NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active','pending','paused','ended')),
  run_of_network   BOOLEAN NOT NULL DEFAULT TRUE,  -- plays on every screen in the market
                                                   -- unless an 'exclude' override says otherwise
  start_date       DATE,
  end_date         DATE,
  contract_id      TEXT,
  notes            TEXT,
  verified_at      DATE,                   -- last time a human confirmed this against the portal
  updated_by       TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE loop_items IS
  'Manual book of record: one row per creative in a market''s loop. Pairs with '
  'screen_loops (which measures loop length per screen but not its contents). '
  'file_name is the Encompass content name — the join key to NTV360 play exports.';

-- One row per creative per market. Case-insensitive so "Cannon.mp4" and
-- "cannon.mp4" cannot both be entered.
CREATE UNIQUE INDEX IF NOT EXISTS idx_loop_items_market_file
  ON loop_items (market, lower(file_name));

CREATE INDEX IF NOT EXISTS idx_loop_items_market_status ON loop_items (market, status);
CREATE INDEX IF NOT EXISTS idx_loop_items_advertiser    ON loop_items (lower(advertiser));
CREATE INDEX IF NOT EXISTS idx_loop_items_client        ON loop_items (client_id);

ALTER TABLE loop_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS loop_items_service_all ON loop_items;
CREATE POLICY loop_items_service_all ON loop_items
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS loop_items_select_authenticated ON loop_items;
CREATE POLICY loop_items_select_authenticated ON loop_items
  FOR SELECT TO authenticated USING (true);


-- =============================================================================
-- 2. Per-screen overrides — the whitelist exceptions
-- =============================================================================
-- mode='exclude' pulls a run-of-network item off one screen (e.g. category
-- exclusivity keeps a Chevy spot out of a Ford dealer's lobby).
-- mode='include' puts a non-run-of-network item on specific screens (e.g. a
-- host's own promo, or a venue-targeted buy).
--
-- license_id NULL = the override applies to every screen at that venue.

CREATE TABLE IF NOT EXISTS loop_item_screens (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id     UUID NOT NULL REFERENCES loop_items(id) ON DELETE CASCADE,
  venue_name  TEXT NOT NULL,
  license_id  UUID,                        -- NULL = all screens at this venue
  mode        TEXT NOT NULL DEFAULT 'include' CHECK (mode IN ('include','exclude')),
  reason      TEXT,
  created_by  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE loop_item_screens IS
  'Per-screen whitelist exceptions for loop_items. include = plays here even '
  'though the item is not run-of-network; exclude = does not play here despite '
  'being run-of-network. license_id NULL applies to all screens at the venue.';

-- NULLs compare as distinct in a plain UNIQUE, so key off a coalesced uuid to
-- stop duplicate venue-level overrides.
CREATE UNIQUE INDEX IF NOT EXISTS idx_loop_item_screens_unique
  ON loop_item_screens (
    item_id,
    lower(venue_name),
    COALESCE(license_id, '00000000-0000-0000-0000-000000000000'::uuid)
  );

CREATE INDEX IF NOT EXISTS idx_loop_item_screens_item  ON loop_item_screens (item_id);
CREATE INDEX IF NOT EXISTS idx_loop_item_screens_venue ON loop_item_screens (lower(venue_name));

ALTER TABLE loop_item_screens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS loop_item_screens_service_all ON loop_item_screens;
CREATE POLICY loop_item_screens_service_all ON loop_item_screens
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS loop_item_screens_select_authenticated ON loop_item_screens;
CREATE POLICY loop_item_screens_select_authenticated ON loop_item_screens
  FOR SELECT TO authenticated USING (true);


-- =============================================================================
-- 3. updated_at trigger for loop_items
-- =============================================================================

CREATE OR REPLACE FUNCTION set_loop_items_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_loop_items_updated_at ON loop_items;
CREATE TRIGGER trg_loop_items_updated_at
  BEFORE UPDATE ON loop_items
  FOR EACH ROW EXECUTE FUNCTION set_loop_items_updated_at();
