-- Migration 022: app_settings key/value store
-- Drop into: mctv-bot/scripts/022_app_settings.sql
-- Run in Supabase SQL Editor.
-- Author: Creed, 2026-07-17

-- =============================================================================
-- Why this exists
-- =============================================================================
-- services/quickbooks_service.py persists OAuth tokens to TWO places:
--   1. a local file (config/qb_tokens.json) — primary, fast
--   2. the Supabase `app_settings` table under key='qb_tokens' — cross-deploy backup
--
-- On Render the local file is EPHEMERAL: every deploy, restart, and cron run
-- starts a fresh container with no file. Without this table, the Supabase
-- backup write silently fails, so after any restart _load_tokens() returns None,
-- is_connected() is False, and get_recurring_revenue() falls back to $0 MRR
-- (also why the mctv-qbo-reconcile cron errors each morning).
--
-- This table is the durable token store. It is a generic key/value settings
-- bag, so other cross-deploy settings can reuse it.

-- =============================================================================
-- 1. Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS app_settings (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key        TEXT NOT NULL UNIQUE,   -- e.g. 'qb_tokens'
  value      TEXT,                   -- JSON-encoded payload (json.dumps)
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 2. Keep updated_at fresh on writes
-- =============================================================================

CREATE OR REPLACE FUNCTION app_settings_touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_app_settings_touch ON app_settings;
CREATE TRIGGER trg_app_settings_touch
  BEFORE UPDATE ON app_settings
  FOR EACH ROW EXECUTE FUNCTION app_settings_touch_updated_at();

-- =============================================================================
-- 3. Row-level security
-- =============================================================================
-- RLS on, no policies: the app reads/writes with the Supabase SERVICE key
-- (services/supabase_client.py insert_row/update_row default use_service_key=True),
-- which bypasses RLS. The anon/public key can never read these OAuth tokens.

ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;
