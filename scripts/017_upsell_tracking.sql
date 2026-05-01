-- ============================================================================
-- 017 — Upsell trigger tracking
-- Tracks when an upsell suggestion was last sent to avoid spamming clients.
-- ============================================================================

ALTER TABLE contracts
  ADD COLUMN IF NOT EXISTS last_upsell_sent_at TIMESTAMPTZ;

COMMENT ON COLUMN contracts.last_upsell_sent_at IS
  'Timestamp the last upsell suggestion email was sent. Throttled to one per 60 days.';
