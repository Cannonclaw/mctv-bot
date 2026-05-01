-- ============================================================================
-- 014 — NPS surveys
-- Auto-trigger at 30 / 90 / 180 days after contract activation. Captures the
-- score, the verbatim, and lets us tie back to the contract for trend tracking.
-- ============================================================================

CREATE TABLE IF NOT EXISTS nps_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_id UUID REFERENCES contracts(id) ON DELETE CASCADE,
  client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
  milestone TEXT NOT NULL CHECK (milestone IN ('30d', '90d', '180d')),
  -- Survey lifecycle
  survey_token UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  sent_at TIMESTAMPTZ DEFAULT now(),
  responded_at TIMESTAMPTZ,
  -- Response (null until they answer)
  score INT CHECK (score IS NULL OR (score >= 0 AND score <= 10)),
  category TEXT CHECK (category IN ('detractor', 'passive', 'promoter') OR category IS NULL),
  what_working TEXT,
  what_not_working TEXT,
  open_to_referrals BOOLEAN,
  -- Metadata
  reminders_sent INT DEFAULT 0,
  last_reminder_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS nps_responses_token_idx ON nps_responses (survey_token);
CREATE INDEX IF NOT EXISTS nps_responses_contract_idx ON nps_responses (contract_id);
CREATE INDEX IF NOT EXISTS nps_responses_client_idx ON nps_responses (client_id);
CREATE UNIQUE INDEX IF NOT EXISTS nps_responses_unique_milestone_idx
  ON nps_responses (contract_id, milestone);

COMMENT ON TABLE nps_responses IS 'NPS survey responses sent at 30/90/180 days post contract activation.';
