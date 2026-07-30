-- Migration 025: Real Estate Feeds Boards (the thing that plays on screen)
-- Drop into: mctv-bot/scripts/025_real_estate_boards.sql
-- Run in Supabase SQL Editor.
--
-- Context
-- -------
-- Migration 024 tracks what plays where. This one backs the boards themselves:
-- the dynamic real estate format sold by generators/real_estate_board.py.
--
--   market_rates    cached mortgage-rate observations (Freddie Mac PMMS)
--   boards          one row per sold board (branding + mode + slug)
--   board_listings  the properties that rotate through a board
--
-- The board renders at /board/<slug> and reads /board/<slug>.json, so the
-- screen never talks to an upstream rate source directly. Rates are fetched on
-- a schedule into market_rates and served from cache. If the cache goes stale
-- the strip hides itself -- a board quoting last month's rate is worse than a
-- board that never mentioned rates.

-- =============================================================================
-- 1. Market rates — the cached rate observations behind the strip
-- =============================================================================
-- One row per series per week. week_ending is the observation date published by
-- the source, NOT the day we fetched it: staleness is judged on the data's age,
-- not on whether the cron ran.

CREATE TABLE IF NOT EXISTS market_rates (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  series        TEXT NOT NULL DEFAULT 'pmms_30yr',  -- pmms_30yr | pmms_15yr
  rate_value    NUMERIC NOT NULL CHECK (rate_value > 0 AND rate_value < 100),
  week_ending   DATE NOT NULL,
  source_name   TEXT NOT NULL DEFAULT 'Freddie Mac Primary Mortgage Market Survey (PMMS)',
  source_url    TEXT,
  fetched_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Re-running the fetch job must not duplicate an observation.
CREATE UNIQUE INDEX IF NOT EXISTS idx_market_rates_series_week
  ON market_rates (series, week_ending);

CREATE INDEX IF NOT EXISTS idx_market_rates_latest
  ON market_rates (series, week_ending DESC);

ALTER TABLE market_rates ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS market_rates_service_all ON market_rates;
CREATE POLICY market_rates_service_all ON market_rates
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS market_rates_select_authenticated ON market_rates;
CREATE POLICY market_rates_select_authenticated ON market_rates
  FOR SELECT TO authenticated USING (true);


-- =============================================================================
-- 2. Boards — one row per sold board
-- =============================================================================
-- board_mode mirrors RealEstateBoardInput.board_mode in the proposal generator,
-- and carries the same meaning: it decides whose branding holds the frame and
-- whether lender identifiers render.
--
-- Lender fields exist on every board but only render for the lender modes. The
-- NMLS ID is stored alongside the name on purpose -- displaying one without the
-- other is exactly the mistake the proposal's disclosure section warns about.

CREATE TABLE IF NOT EXISTS boards (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug              TEXT NOT NULL,          -- URL segment: /board/<slug>
  board_mode        TEXT NOT NULL DEFAULT 'agent'
                    CHECK (board_mode IN ('agent','brokerage','cosponsor','lender')),
  display_name      TEXT NOT NULL,          -- agent or business name on the frame
  brokerage_name    TEXT,
  tagline           TEXT,
  phone             TEXT,
  email             TEXT,
  headshot_url      TEXT,
  logo_url          TEXT,
  -- Lender co-sponsorship. Rendered only for cosponsor/lender modes.
  lender_name       TEXT,
  lender_nmls_id    TEXT,
  lender_logo_url   TEXT,
  -- The rate strip is opt-out per board; the staleness rule still governs it.
  show_rate_strip   BOOLEAN NOT NULL DEFAULT TRUE,
  rate_series       TEXT NOT NULL DEFAULT 'pmms_30yr',
  rotation_seconds  INTEGER NOT NULL DEFAULT 12 CHECK (rotation_seconds BETWEEN 4 AND 120),
  theme             TEXT NOT NULL DEFAULT 'navy'
                    CHECK (theme IN ('navy','light','dark','sage')),
  client_id         TEXT,                   -- clients.id when this is a portal client
  market            TEXT,                   -- oxford | starkville | tupelo | columbus | west_point
  status            TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','paused','ended')),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Slugs are the public URL, so they're unique case-insensitively.
CREATE UNIQUE INDEX IF NOT EXISTS idx_boards_slug ON boards (lower(slug));
CREATE INDEX IF NOT EXISTS idx_boards_status     ON boards (status);
CREATE INDEX IF NOT EXISTS idx_boards_client     ON boards (client_id);

ALTER TABLE boards ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS boards_service_all ON boards;
CREATE POLICY boards_service_all ON boards
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS boards_select_authenticated ON boards;
CREATE POLICY boards_select_authenticated ON boards
  FOR SELECT TO authenticated USING (true);


-- =============================================================================
-- 3. Board listings — the properties that rotate
-- =============================================================================
-- Agent-supplied listings only. These are properties the advertiser has the
-- right to advertise; nothing here comes from an MLS/IDX feed, which carries
-- display rules that do not contemplate third-party digital signage.
--
-- status drives what renders: 'active' rotates, 'pending'/'sold' can be shown
-- with a banner for social proof, 'hidden' never renders.

CREATE TABLE IF NOT EXISTS board_listings (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id     UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  address      TEXT NOT NULL,
  city         TEXT,
  price        NUMERIC CHECK (price IS NULL OR price >= 0),
  beds         NUMERIC CHECK (beds IS NULL OR beds >= 0),
  baths        NUMERIC CHECK (baths IS NULL OR baths >= 0),
  sqft         INTEGER CHECK (sqft IS NULL OR sqft >= 0),
  photo_url    TEXT,
  blurb        TEXT,
  status       TEXT NOT NULL DEFAULT 'active'
               CHECK (status IN ('active','pending','sold','hidden')),
  sort_order   INTEGER NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_board_listings_board
  ON board_listings (board_id, status, sort_order);

ALTER TABLE board_listings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS board_listings_service_all ON board_listings;
CREATE POLICY board_listings_service_all ON board_listings
  FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS board_listings_select_authenticated ON board_listings;
CREATE POLICY board_listings_select_authenticated ON board_listings
  FOR SELECT TO authenticated USING (true);


-- =============================================================================
-- 4. updated_at triggers
-- =============================================================================

CREATE OR REPLACE FUNCTION set_boards_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_boards_updated_at ON boards;
CREATE TRIGGER trg_boards_updated_at
  BEFORE UPDATE ON boards
  FOR EACH ROW EXECUTE FUNCTION set_boards_updated_at();

DROP TRIGGER IF EXISTS trg_board_listings_updated_at ON board_listings;
CREATE TRIGGER trg_board_listings_updated_at
  BEFORE UPDATE ON board_listings
  FOR EACH ROW EXECUTE FUNCTION set_boards_updated_at();
