-- ============================================================================
-- 016 — Win-back tracking + stalled-deal age helper for pipeline_opportunities
-- ============================================================================

ALTER TABLE pipeline_opportunities
  ADD COLUMN IF NOT EXISTS win_back_sent_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS win_back_responded_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS stage_entered_at TIMESTAMPTZ DEFAULT now(),
  ADD COLUMN IF NOT EXISTS last_stalled_alert_at TIMESTAMPTZ;

COMMENT ON COLUMN pipeline_opportunities.win_back_sent_at IS
  'Timestamp the 90-day win-back email/SMS was sent. Null = not yet attempted.';
COMMENT ON COLUMN pipeline_opportunities.stage_entered_at IS
  'When the deal entered its current stage; powers stalled-deal alerts.';
