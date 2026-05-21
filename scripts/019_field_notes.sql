-- Migration 012: Voice Field Notes
-- Drop into: mctv-bot/scripts/012_field_notes.sql
-- Run in Supabase SQL Editor.
-- Author: Cowork + Creed, 2026-05-19
--
-- Defensive design: no foreign-key constraints to customers/team_members,
-- so this migration won't fail if those tables have a different shape than
-- assumed. RLS policies use a soft "own row" check via team_member_id.
-- Tighten constraints later once the feature is in production.

-- =============================================================================
-- 1. Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS field_notes (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_member_id  TEXT NOT NULL,                  -- soft ref to team_members.id (UUID or string)
  customer_id     TEXT,                           -- soft ref to customers.id (nullable)
  audio_url       TEXT,                           -- Supabase storage object path
  raw_transcript  TEXT,
  summary         TEXT,
  structured_data JSONB,                          -- full Claude structuring output
  action_items    JSONB DEFAULT '[]'::jsonb,      -- [{text, due_date, owner, done}]
  sentiment       TEXT DEFAULT 'neutral',
  tags            TEXT[] DEFAULT ARRAY[]::TEXT[],
  location_lat    DECIMAL(9,6),
  location_lng    DECIMAL(9,6),
  review_status   TEXT DEFAULT 'pending'
                  CHECK (review_status IN ('pending', 'reviewed', 'archived')),
  duration_sec    INTEGER,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_field_notes_team_member ON field_notes(team_member_id);
CREATE INDEX IF NOT EXISTS idx_field_notes_customer    ON field_notes(customer_id);
CREATE INDEX IF NOT EXISTS idx_field_notes_created     ON field_notes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_field_notes_pending     ON field_notes(review_status)
  WHERE review_status = 'pending';

-- =============================================================================
-- 2. Storage bucket for audio files
-- =============================================================================

INSERT INTO storage.buckets (id, name, public)
VALUES ('field-notes-audio', 'field-notes-audio', false)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- 3. Row Level Security
-- =============================================================================
-- Conservative MVP: enable RLS but allow service_role full access (used by the
-- Streamlit app via the SUPABASE_SERVICE_ROLE_KEY). Tighten with per-user
-- policies once auth.uid() integration is confirmed against team_members.id.

ALTER TABLE field_notes ENABLE ROW LEVEL SECURITY;

-- Service role can do anything (the app uses this key for all writes)
CREATE POLICY field_notes_service_all ON field_notes
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Authenticated users can read their own notes via team_member_id match
-- (string compare against auth.uid()::text — works whether team_members.id is uuid or text)
CREATE POLICY field_notes_select_own ON field_notes
  FOR SELECT
  TO authenticated
  USING (team_member_id = auth.uid()::text);

-- =============================================================================
-- 4. Storage policies
-- =============================================================================

-- Service role uploads (app does the work)
CREATE POLICY "field_notes_audio_service_all" ON storage.objects
  FOR ALL
  TO service_role
  USING (bucket_id = 'field-notes-audio')
  WITH CHECK (bucket_id = 'field-notes-audio');

-- Authenticated users can read audio in their own subfolder
CREATE POLICY "field_notes_audio_read_own" ON storage.objects
  FOR SELECT
  TO authenticated
  USING (
    bucket_id = 'field-notes-audio'
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

-- =============================================================================
-- Done. Verify with:
--   SELECT count(*) FROM field_notes;        -- should return 0
--   SELECT id FROM storage.buckets WHERE id = 'field-notes-audio';  -- should return 1 row
-- =============================================================================
