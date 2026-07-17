-- Migration 023: self-serve rate card
-- Drop into: mctv-bot/scripts/023_self_serve_rate_card.sql
-- Run in Supabase SQL Editor.
-- Author: Creed, 2026-07-17

-- =============================================================================
-- Why this exists
-- =============================================================================
-- The public rate calculator at mctvofms.com/rate-quote (v2.0) lets advertisers
-- build a quote and sign a self-serve agreement request. A Supabase edge
-- function (`contract-initiate`) writes each signature to `contract_requests`
-- and fans out to quote_submissions, leads, pipeline_opportunities
-- (deal_type='advertiser', stage='contract_sent', source='website'), tasks
-- (assigned_to='Creed', source='self_serve'), and activity_log.
--
-- Section 1 (contract_requests) is ALREADY APPLIED to the live project — this
-- file is the version-controlled record.
-- Section 2 (Phase-1 pricing flip) is STAGED — do not run until Creed says go.

-- =============================================================================
-- 1. contract_requests — signed self-serve agreement requests
-- =============================================================================

CREATE TABLE IF NOT EXISTS contract_requests (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ref               TEXT UNIQUE NOT NULL,      -- e.g. 'MCTV-SS-20260717-XXXX'
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  quote_ref         TEXT,                      -- link back to quote_submissions
  business_name     TEXT NOT NULL,
  contact_name      TEXT NOT NULL,
  contact_email     TEXT NOT NULL,
  contact_phone     TEXT,
  mode              TEXT,                      -- 'package' | 'custom'
  term_months       INTEGER,
  prepay            BOOLEAN DEFAULT FALSE,
  monthly_total     NUMERIC,
  term_total        NUMERIC,
  screens           INTEGER,
  est_impressions   NUMERIC,
  selection         JSONB,                     -- venues/package the client picked
  start_date        DATE,
  signed_name       TEXT NOT NULL,             -- typed legal name (e-sign)
  agreement_version TEXT,
  quote_link        TEXT,                      -- shareable prefilled quote URL
  status            TEXT NOT NULL DEFAULT 'new'
                    CHECK (status IN ('new', 'countersigned', 'converted', 'rejected', 'spam')),
  lead_id           TEXT,                      -- auto-created lead
  opportunity_id    UUID,                      -- auto-created pipeline deal
  client_ip         TEXT,
  user_agent        TEXT,
  notes             TEXT
);

COMMENT ON TABLE contract_requests IS
  'Signed self-serve agreement requests from the public rate calculator.';

-- The edge function writes with the service key (bypasses RLS); the team app
-- also reads with the service key. Authenticated portal users get read-only.
ALTER TABLE contract_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY contract_requests_team_read ON contract_requests
  FOR SELECT TO authenticated USING (true);

CREATE INDEX IF NOT EXISTS idx_contract_requests_email
  ON contract_requests (contact_email, created_at);
CREATE INDEX IF NOT EXISTS idx_contract_requests_ip
  ON contract_requests (client_ip, created_at);

-- =============================================================================
-- 2. PHASE-1 PRICING FLIP — run on Creed's go-ahead — changes live list rates
-- =============================================================================
-- Flips the model to the Phase-1 public pricing: CPM $6 -> $5, a $175/venue
-- 4-wk cap, and 20% volume discount at 10+ screens (discount applied by the
-- calculator/custom builds, not the view). The view keeps its existing column
-- order and appends `list_rate_4wk` (uncapped) + `rate_capped` after
-- `rate_4wk`, so CREATE OR REPLACE VIEW is safe.

ALTER TABLE rate_model_params
  ADD COLUMN IF NOT EXISTS venue_cap_4wk NUMERIC DEFAULT 175,
  ADD COLUMN IF NOT EXISTS volume_discount_screens INTEGER DEFAULT 10,
  ADD COLUMN IF NOT EXISTS volume_discount_pct NUMERIC DEFAULT 20;

UPDATE rate_model_params
   SET cpm = 5,
       venue_cap_4wk = 175,
       volume_discount_screens = 10,
       volume_discount_pct = 20,
       updated_at = NOW()
 WHERE id = 1;

CREATE OR REPLACE VIEW venue_rates_v AS
WITH latest AS (
  SELECT max(screen_loops.swept_at) AS d FROM screen_loops
), loops AS (
  SELECT lower(regexp_replace(screen_loops.venue_name, '[^A-Za-z0-9]', '', 'g')) AS norm_name,
         avg(screen_loops.loop_seconds) / 60.0 AS loop_min,
         count(*) AS screens_seen
  FROM screen_loops, latest
  WHERE screen_loops.swept_at = latest.d
  GROUP BY 1
), p AS (
  SELECT id, cpm, exposure_cap, cross_screen_pct, floor_4wk, fallback_loop_min, updated_at,
         COALESCE(venue_cap_4wk, 175) AS venue_cap_4wk
  FROM rate_model_params WHERE id = 1
)
SELECT
  v.venue_name,
  v.market,
  v.city,
  v.screens,
  v.type_code,
  t.label AS type_label,
  COALESCE(l.loop_min, v.loop_min_override, p.fallback_loop_min) AS loop_min,
  l.loop_min IS NOT NULL AS loop_from_sweep,
  COALESCE(v.monthly_traffic * 12::numeric / 52.0, t.visits_per_day * t.days_per_week::numeric) AS weekly_visits,
  v.monthly_traffic IS NOT NULL AS traffic_from_ntv,
  COALESCE(v.dwell_override_min, t.dwell_min) AS dwell_min,
  v.dwell_override_min IS NOT NULL AS dwell_from_form,
  LEAST(p.exposure_cap, COALESCE(v.dwell_override_min, t.dwell_min) / COALESCE(l.loop_min, v.loop_min_override, p.fallback_loop_min)) AS exposures,
  1::numeric + (v.screens - 1)::numeric * p.cross_screen_pct / 100.0 AS coverage,
  COALESCE(v.monthly_traffic * 12::numeric / 52.0, t.visits_per_day * t.days_per_week::numeric)
    * LEAST(p.exposure_cap, COALESCE(v.dwell_override_min, t.dwell_min) / COALESCE(l.loop_min, v.loop_min_override, p.fallback_loop_min))
    * (1::numeric + (v.screens - 1)::numeric * p.cross_screen_pct / 100.0) AS weekly_impressions,
  LEAST(p.venue_cap_4wk,
    GREATEST(p.floor_4wk, round(
      COALESCE(v.monthly_traffic * 12::numeric / 52.0, t.visits_per_day * t.days_per_week::numeric)
        * LEAST(p.exposure_cap, COALESCE(v.dwell_override_min, t.dwell_min) / COALESCE(l.loop_min, v.loop_min_override, p.fallback_loop_min))
        * (1::numeric + (v.screens - 1)::numeric * p.cross_screen_pct / 100.0)
        * 4::numeric / 1000.0 * p.cpm / 5.0) * 5::numeric)) AS rate_4wk,
  GREATEST(p.floor_4wk, round(
    COALESCE(v.monthly_traffic * 12::numeric / 52.0, t.visits_per_day * t.days_per_week::numeric)
      * LEAST(p.exposure_cap, COALESCE(v.dwell_override_min, t.dwell_min) / COALESCE(l.loop_min, v.loop_min_override, p.fallback_loop_min))
      * (1::numeric + (v.screens - 1)::numeric * p.cross_screen_pct / 100.0)
      * 4::numeric / 1000.0 * p.cpm / 5.0) * 5::numeric) AS list_rate_4wk,
  (GREATEST(p.floor_4wk, round(
    COALESCE(v.monthly_traffic * 12::numeric / 52.0, t.visits_per_day * t.days_per_week::numeric)
      * LEAST(p.exposure_cap, COALESCE(v.dwell_override_min, t.dwell_min) / COALESCE(l.loop_min, v.loop_min_override, p.fallback_loop_min))
      * (1::numeric + (v.screens - 1)::numeric * p.cross_screen_pct / 100.0)
      * 4::numeric / 1000.0 * p.cpm / 5.0) * 5::numeric) > p.venue_cap_4wk) AS rate_capped
FROM venue_rate_inputs v
JOIN venue_type_defaults t ON t.type_code = v.type_code
LEFT JOIN loops l ON l.norm_name = lower(regexp_replace(v.venue_name, '[^A-Za-z0-9]', '', 'g'))
CROSS JOIN p;

-- =============================================================================
-- ROLLBACK (Phase-1 flip only) — uncomment to restore the pre-flip model
-- =============================================================================
-- CREATE OR REPLACE VIEW cannot DROP columns, so the view must be dropped and
-- recreated with the original definition. The added params columns can stay.
--
-- UPDATE rate_model_params SET cpm = 6, updated_at = NOW() WHERE id = 1;
--
-- DROP VIEW venue_rates_v;
-- CREATE VIEW venue_rates_v AS
-- WITH latest AS (
--   SELECT max(screen_loops.swept_at) AS d FROM screen_loops
-- ), loops AS (
--   SELECT lower(regexp_replace(screen_loops.venue_name, '[^A-Za-z0-9]', '', 'g')) AS norm_name,
--          avg(screen_loops.loop_seconds) / 60.0 AS loop_min,
--          count(*) AS screens_seen
--   FROM screen_loops, latest
--   WHERE screen_loops.swept_at = latest.d
--   GROUP BY 1
-- ), p AS (
--   SELECT id, cpm, exposure_cap, cross_screen_pct, floor_4wk, fallback_loop_min, updated_at
--   FROM rate_model_params WHERE id = 1
-- )
-- SELECT
--   v.venue_name,
--   v.market,
--   v.city,
--   v.screens,
--   v.type_code,
--   t.label AS type_label,
--   COALESCE(l.loop_min, v.loop_min_override, p.fallback_loop_min) AS loop_min,
--   l.loop_min IS NOT NULL AS loop_from_sweep,
--   COALESCE(v.monthly_traffic * 12::numeric / 52.0, t.visits_per_day * t.days_per_week::numeric) AS weekly_visits,
--   v.monthly_traffic IS NOT NULL AS traffic_from_ntv,
--   COALESCE(v.dwell_override_min, t.dwell_min) AS dwell_min,
--   v.dwell_override_min IS NOT NULL AS dwell_from_form,
--   LEAST(p.exposure_cap, COALESCE(v.dwell_override_min, t.dwell_min) / COALESCE(l.loop_min, v.loop_min_override, p.fallback_loop_min)) AS exposures,
--   1::numeric + (v.screens - 1)::numeric * p.cross_screen_pct / 100.0 AS coverage,
--   COALESCE(v.monthly_traffic * 12::numeric / 52.0, t.visits_per_day * t.days_per_week::numeric)
--     * LEAST(p.exposure_cap, COALESCE(v.dwell_override_min, t.dwell_min) / COALESCE(l.loop_min, v.loop_min_override, p.fallback_loop_min))
--     * (1::numeric + (v.screens - 1)::numeric * p.cross_screen_pct / 100.0) AS weekly_impressions,
--   GREATEST(p.floor_4wk, round(
--     COALESCE(v.monthly_traffic * 12::numeric / 52.0, t.visits_per_day * t.days_per_week::numeric)
--       * LEAST(p.exposure_cap, COALESCE(v.dwell_override_min, t.dwell_min) / COALESCE(l.loop_min, v.loop_min_override, p.fallback_loop_min))
--       * (1::numeric + (v.screens - 1)::numeric * p.cross_screen_pct / 100.0)
--       * 4::numeric / 1000.0 * p.cpm / 5.0) * 5::numeric) AS rate_4wk
-- FROM venue_rate_inputs v
-- JOIN venue_type_defaults t ON t.type_code = v.type_code
-- LEFT JOIN loops l ON l.norm_name = lower(regexp_replace(v.venue_name, '[^A-Za-z0-9]', '', 'g'))
-- CROSS JOIN p;
