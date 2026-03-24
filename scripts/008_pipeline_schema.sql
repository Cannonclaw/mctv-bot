-- 008_pipeline_schema.sql
-- Sales pipeline tables for opportunity tracking and activity logging
-- Run via Supabase SQL Editor

-- Pipeline opportunities (core sales pipeline)
CREATE TABLE IF NOT EXISTS pipeline_opportunities (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    lead_id TEXT,                    -- links to leads.id (text format)
    client_id UUID,                 -- links to clients.id (after conversion)
    business_name TEXT NOT NULL,
    contact_name TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    industry TEXT,
    city TEXT,
    source TEXT DEFAULT 'manual' CHECK (source IN (
        'manual', 'intake_form', 'prospector', 'referral', 'website', 'cold_outreach'
    )),
    stage TEXT DEFAULT 'prospect' CHECK (stage IN (
        'prospect', 'outreach', 'engaged', 'discovery',
        'proposal_sent', 'negotiation', 'contract_sent', 'won', 'lost'
    )),
    monthly_value NUMERIC(10,2) DEFAULT 0,
    screen_count INTEGER DEFAULT 0,
    tier_name TEXT,
    expected_close_date DATE,
    probability INTEGER DEFAULT 10 CHECK (probability >= 0 AND probability <= 100),
    loss_reason TEXT,
    assigned_rep TEXT DEFAULT 'Mary Michael',
    notes TEXT,
    last_contact_date TIMESTAMPTZ,
    next_action TEXT,
    next_action_date DATE,
    nurture_sequence TEXT,         -- which drip sequence they're in
    nurture_step INTEGER DEFAULT 0,
    last_nurture_sent TIMESTAMPTZ,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Pipeline activity log (tracks all actions on an opportunity)
CREATE TABLE IF NOT EXISTS pipeline_activity (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    opportunity_id UUID NOT NULL REFERENCES pipeline_opportunities(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN (
        'created', 'stage_change', 'note_added', 'email_sent', 'sms_sent',
        'call_logged', 'proposal_generated', 'contract_sent', 'value_updated',
        'nurture_sent', 'follow_up_set', 'assigned'
    )),
    from_stage TEXT,
    to_stage TEXT,
    details TEXT,
    performed_by TEXT DEFAULT 'MCTV Bot',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_pipeline_stage ON pipeline_opportunities(stage);
CREATE INDEX IF NOT EXISTS idx_pipeline_city ON pipeline_opportunities(city);
CREATE INDEX IF NOT EXISTS idx_pipeline_assigned ON pipeline_opportunities(assigned_rep);
CREATE INDEX IF NOT EXISTS idx_pipeline_next_action ON pipeline_opportunities(next_action_date);
CREATE INDEX IF NOT EXISTS idx_pipeline_nurture ON pipeline_opportunities(nurture_sequence, nurture_step);
CREATE INDEX IF NOT EXISTS idx_pipeline_activity_opp ON pipeline_activity(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_activity_date ON pipeline_activity(created_at);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_pipeline_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_pipeline_updated_at ON pipeline_opportunities;
CREATE TRIGGER trigger_pipeline_updated_at
    BEFORE UPDATE ON pipeline_opportunities
    FOR EACH ROW EXECUTE FUNCTION update_pipeline_updated_at();

-- RLS policies
ALTER TABLE pipeline_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_activity ENABLE ROW LEVEL SECURITY;

-- Service role has full access
CREATE POLICY "service_role_pipeline" ON pipeline_opportunities
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "service_role_pipeline_activity" ON pipeline_activity
    FOR ALL USING (true) WITH CHECK (true);
