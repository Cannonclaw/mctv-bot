-- ============================================================================
-- 018 — Per-rep commission tracking
-- Adds default commission rate to clients + a payouts ledger.
-- ============================================================================

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS commission_rate NUMERIC(5, 4) DEFAULT 0.10;

COMMENT ON COLUMN clients.commission_rate IS
  'Decimal commission rate (0.10 = 10%) paid to the assigned rep on this clients monthly contract value.';

CREATE TABLE IF NOT EXISTS commission_payouts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rep_name TEXT NOT NULL,
  -- Period this payout covers
  period_year INT NOT NULL,
  period_month INT NOT NULL CHECK (period_month >= 1 AND period_month <= 12),
  -- Money
  amount NUMERIC(10, 2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'accrued'
    CHECK (status IN ('accrued', 'approved', 'paid', 'adjusted', 'voided')),
  -- Source breakdown — JSON list of {contract_id, client_name, monthly_rate, commission_rate, amount}
  breakdown JSONB DEFAULT '[]'::jsonb,
  -- Lifecycle
  notes TEXT,
  paid_at TIMESTAMPTZ,
  paid_method TEXT,
  paid_reference TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  -- A rep gets one row per period
  CONSTRAINT commission_payouts_rep_period_unique UNIQUE (rep_name, period_year, period_month)
);

CREATE INDEX IF NOT EXISTS commission_payouts_rep_idx
  ON commission_payouts (rep_name, period_year DESC, period_month DESC);
CREATE INDEX IF NOT EXISTS commission_payouts_status_idx
  ON commission_payouts (status);

COMMENT ON TABLE commission_payouts IS
  'Monthly per-rep commission accruals + payout state. One row per (rep, year, month).';
