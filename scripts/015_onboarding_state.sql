-- ============================================================================
-- 015 — Client onboarding state on contracts
-- ============================================================================

ALTER TABLE contracts
  ADD COLUMN IF NOT EXISTS onboarding_state JSONB DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS onboarding_started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMPTZ;

COMMENT ON COLUMN contracts.onboarding_state IS
  'JSON of {step_key: {done: bool, done_at: iso_ts, notes: str}} tracking the 7-step onboarding checklist.';
