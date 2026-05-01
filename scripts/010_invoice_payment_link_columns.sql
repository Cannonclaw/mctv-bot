-- ============================================================================
-- 010 — QuickBooks Pay-Now link tracking on invoices
-- Adds columns to capture QBO invoice IDs and emailed-pay-link state.
-- ============================================================================

ALTER TABLE invoices
  ADD COLUMN IF NOT EXISTS qb_invoice_id TEXT,
  ADD COLUMN IF NOT EXISTS qb_invoice_url TEXT,
  ADD COLUMN IF NOT EXISTS qb_email_sent_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS pay_link_provider TEXT
    CHECK (pay_link_provider IN ('qbo', 'stripe') OR pay_link_provider IS NULL);

CREATE INDEX IF NOT EXISTS invoices_qb_invoice_id_idx
  ON invoices (qb_invoice_id);

COMMENT ON COLUMN invoices.qb_invoice_id    IS 'QuickBooks Online Invoice Id (used for re-fetch and send).';
COMMENT ON COLUMN invoices.qb_invoice_url   IS 'Internal QBO invoice URL for the merchant; not the customer pay link.';
COMMENT ON COLUMN invoices.qb_email_sent_at IS 'When QBO last emailed the invoice with the Pay Now link.';
COMMENT ON COLUMN invoices.pay_link_provider IS 'Which processor the Pay Now link routes through. Today: qbo (QB Payments) or stripe.';
