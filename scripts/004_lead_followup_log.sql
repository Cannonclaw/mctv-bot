-- Migration 004: Lead follow-up tracking table
--
-- Tracks automated follow-up actions per lead to prevent duplicate sends.
-- Used by scripts/lead_followups.py for welcome emails and nurture drips.
--
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/YOUR_PROJECT/sql
-- Safe to run multiple times (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS lead_followup_log (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    lead_id       TEXT NOT NULL UNIQUE,
    last_welcome  TIMESTAMPTZ,        -- when welcome email was sent
    last_nurture  TIMESTAMPTZ,        -- when last nurture email was sent
    nurture_step  INT DEFAULT 0,      -- current nurture step (0=none, 1-3)
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

-- Index for fast lookups by lead_id
CREATE INDEX IF NOT EXISTS idx_lead_followup_log_lead_id
    ON lead_followup_log(lead_id);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_lead_followup_log_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_lead_followup_log_updated ON lead_followup_log;
CREATE TRIGGER trg_lead_followup_log_updated
    BEFORE UPDATE ON lead_followup_log
    FOR EACH ROW
    EXECUTE FUNCTION update_lead_followup_log_updated_at();

-- RLS: Allow service role full access (cron scripts use service key)
ALTER TABLE lead_followup_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "Service role full access on lead_followup_log"
    ON lead_followup_log
    FOR ALL
    USING (true)
    WITH CHECK (true);
