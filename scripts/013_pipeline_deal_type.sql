-- ============================================================================
-- 013 — Pipeline deal_type column
-- Adds 'advertiser' / 'host' typing so the same pipeline_opportunities table
-- can power both the advertiser and host acquisition pipelines.
-- ============================================================================

ALTER TABLE pipeline_opportunities
  ADD COLUMN IF NOT EXISTS deal_type TEXT NOT NULL DEFAULT 'advertiser'
    CHECK (deal_type IN ('advertiser', 'host'));

-- Hosts use a different stage taxonomy (no "proposal_sent" — they get an
-- agreement, not a proposal). Loosen the check constraint for hosts.
ALTER TABLE pipeline_opportunities
  DROP CONSTRAINT IF EXISTS pipeline_opportunities_stage_check;

ALTER TABLE pipeline_opportunities
  ADD CONSTRAINT pipeline_opportunities_stage_check
    CHECK (stage IN (
      -- Advertiser stages
      'prospect', 'outreach', 'engaged', 'discovery',
      'proposal_sent', 'negotiation', 'contract_sent', 'won', 'lost',
      -- Host-acquisition stages
      'identified', 'first_visit', 'pitched',
      'agreement_sent', 'install_scheduled', 'live'
    ));

CREATE INDEX IF NOT EXISTS pipeline_opportunities_deal_type_idx
  ON pipeline_opportunities (deal_type, stage);

COMMENT ON COLUMN pipeline_opportunities.deal_type IS
  'advertiser = paying customer pipeline; host = venue acquisition pipeline.';
