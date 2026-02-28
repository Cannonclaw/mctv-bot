-- Migration 005: NTV360 play data snapshots
--
-- Stores aggregated NTV360 play data when uploaded via the Reports page,
-- so automated monthly reports (scripts/monthly_reports.py) can pull
-- real play counts instead of showing total_plays=0.
--
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/YOUR_PROJECT/sql
-- Safe to run multiple times (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS ntv360_snapshots (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    snapshot_month  TEXT NOT NULL,           -- e.g. "2026-01" (YYYY-MM)
    total_plays     INT DEFAULT 0,
    total_air_time  TEXT DEFAULT '',         -- e.g. "125h 30m 15s"
    venue_count     INT DEFAULT 0,
    venue_data      JSONB DEFAULT '[]'::jsonb,  -- array of per-venue play records
    uploaded_by     TEXT DEFAULT '',         -- team member who uploaded
    source_file     TEXT DEFAULT '',         -- original Excel filename
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Unique constraint: one snapshot per month (upsert-friendly)
CREATE UNIQUE INDEX IF NOT EXISTS idx_ntv360_snapshots_month
    ON ntv360_snapshots(snapshot_month);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_ntv360_snapshots_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ntv360_snapshots_updated ON ntv360_snapshots;
CREATE TRIGGER trg_ntv360_snapshots_updated
    BEFORE UPDATE ON ntv360_snapshots
    FOR EACH ROW
    EXECUTE FUNCTION update_ntv360_snapshots_updated_at();

-- RLS: Allow service role full access
ALTER TABLE ntv360_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "Service role full access on ntv360_snapshots"
    ON ntv360_snapshots
    FOR ALL
    USING (true)
    WITH CHECK (true);
