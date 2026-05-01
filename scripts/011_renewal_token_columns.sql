-- ============================================================================
-- 011 — One-click renewal offer tracking on contracts
-- Adds a UUID token + send timestamp so the client can renew via a public
-- link without logging in.
-- ============================================================================

ALTER TABLE contracts
  ADD COLUMN IF NOT EXISTS renewal_token UUID,
  ADD COLUMN IF NOT EXISTS renewal_offer_sent_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS renewal_accepted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS renewal_contract_id UUID REFERENCES contracts(id);

CREATE UNIQUE INDEX IF NOT EXISTS contracts_renewal_token_idx
  ON contracts (renewal_token)
  WHERE renewal_token IS NOT NULL;

COMMENT ON COLUMN contracts.renewal_token         IS 'UUID token for the one-click renewal link sent to the client.';
COMMENT ON COLUMN contracts.renewal_offer_sent_at IS 'When the renewal offer email/SMS was sent.';
COMMENT ON COLUMN contracts.renewal_accepted_at   IS 'When the client clicked Renew on the offer page.';
COMMENT ON COLUMN contracts.renewal_contract_id   IS 'The new draft contract created by accepting the renewal.';
