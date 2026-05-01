-- ============================================================================
-- 012 — Host referral program
-- Hosts (venue owners) can refer advertisers and earn credit when those
-- advertisers sign their first contract.
-- ============================================================================

CREATE TABLE IF NOT EXISTS referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- Who referred (host client) — uses clients.id; nullable for ad-hoc tests
  referrer_client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
  referrer_code TEXT NOT NULL,                -- short alphanumeric, what gets shared
  -- The lead they brought in
  referred_lead_id TEXT,                       -- text (matches leads.id text format)
  referred_business_name TEXT,
  referred_contact_name TEXT,
  referred_contact_email TEXT,
  -- Conversion tracking
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'qualified', 'converted', 'expired', 'paid')),
  converted_client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
  converted_contract_id UUID REFERENCES contracts(id) ON DELETE SET NULL,
  -- Reward
  reward_type TEXT DEFAULT 'screen_time'
    CHECK (reward_type IN ('screen_time', 'cash', 'credit', 'none')),
  reward_value NUMERIC(10, 2) DEFAULT 0,
  reward_paid_at TIMESTAMPTZ,
  -- Metadata
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS referrals_referrer_idx ON referrals (referrer_client_id);
CREATE INDEX IF NOT EXISTS referrals_referrer_code_idx ON referrals (referrer_code);
CREATE INDEX IF NOT EXISTS referrals_status_idx ON referrals (status);
CREATE INDEX IF NOT EXISTS referrals_lead_idx ON referrals (referred_lead_id);

-- A short referral code per client. Stored on the clients table so the
-- intake URL can be deep-linked: /Intake?ref=<code>
ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS referral_code TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS clients_referral_code_idx
  ON clients (referral_code)
  WHERE referral_code IS NOT NULL;

COMMENT ON TABLE referrals IS 'Host referral program — hosts refer advertisers and earn rewards on conversion.';
COMMENT ON COLUMN clients.referral_code IS 'Short alphanumeric code shared by hosts to attribute referred leads.';
