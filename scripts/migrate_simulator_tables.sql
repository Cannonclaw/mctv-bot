-- ============================================================================
-- MCTV Audience & Package Simulator — Supabase Schema
-- Run in Supabase SQL Editor.
-- Adds two tables that power the internal simulator + shareable prospect view.
-- ============================================================================

-- 1. SIMULATOR_SCENARIOS — Saved scenarios with shareable tokens
-- ============================================================================
CREATE TABLE IF NOT EXISTS simulator_scenarios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prospect_name TEXT NOT NULL,
  prospect_email TEXT,
  prospect_phone TEXT,
  prospect_business TEXT,
  -- Selected venues — array of venue keys from data/network_dashboard.json
  venue_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
  -- Snapshot of computed metrics at save time so the share link is stable
  -- even if dashboard data changes later
  computed_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
  recommended_tier JSONB NOT NULL DEFAULT '{}'::jsonb,
  custom_monthly_rate DECIMAL(10, 2),
  -- Shareable token (UUID, used as URL query param)
  share_token UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  -- Authorship + lifecycle
  created_by TEXT,
  assigned_rep TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ DEFAULT (now() + INTERVAL '90 days'),
  viewed_at TIMESTAMPTZ,
  view_count INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS simulator_scenarios_share_token_idx
  ON simulator_scenarios (share_token);
CREATE INDEX IF NOT EXISTS simulator_scenarios_created_at_idx
  ON simulator_scenarios (created_at DESC);

-- 2. ZIP_DEMOGRAPHICS_CACHE — Census ACS lookups, cached 90 days
-- ============================================================================
CREATE TABLE IF NOT EXISTS zip_demographics_cache (
  zip TEXT PRIMARY KEY,
  raw_data JSONB NOT NULL,
  fetched_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- RLS — Service-key-only access. The simulator engine uses the service key,
-- and the public share view loads scenarios via service-key REST calls
-- gated by the share_token UUID (effectively the auth).
-- ============================================================================
ALTER TABLE simulator_scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE zip_demographics_cache ENABLE ROW LEVEL SECURITY;

-- No public policies — anon key cannot read or write. All access is via
-- service-role key from the Streamlit backend.
