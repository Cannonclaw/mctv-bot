-- ============================================================================
-- 021 — Rep assignment column on leads
-- Enables the bulk "Assign Rep" action on the Leads page and rep-filtered
-- lead views (weekly_rep_recap.py already reads this field).
-- ============================================================================

ALTER TABLE leads
  ADD COLUMN IF NOT EXISTS assigned_rep TEXT;

COMMENT ON COLUMN leads.assigned_rep IS 'Team member responsible for working this lead (first name from config team list).';
