-- Migration: Create contract_alerts_log table
-- Purpose: Track which expiration alerts have been sent to avoid duplicates
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/dtapevlfnekzepbtlabj/sql

CREATE TABLE IF NOT EXISTS contract_alerts_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL,
    sent_to TEXT NOT NULL,
    channel TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast duplicate lookups
CREATE INDEX IF NOT EXISTS idx_contract_alerts_lookup
    ON contract_alerts_log (contract_id, alert_type, channel);

-- RLS: service role can read/write (used by the bot backend)
ALTER TABLE contract_alerts_log ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY contract_alerts_service_all
        ON contract_alerts_log FOR ALL
        USING (true)
        WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;
