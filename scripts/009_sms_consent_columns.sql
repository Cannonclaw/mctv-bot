-- ============================================================================
-- 009 — SMS consent columns on leads (TCPA / A2P 10DLC compliance)
-- Adds proof-of-consent fields captured at intake submission time.
-- ============================================================================

ALTER TABLE leads
  ADD COLUMN IF NOT EXISTS sms_consent BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS sms_consent_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS sms_consent_ip TEXT,
  ADD COLUMN IF NOT EXISTS sms_consent_text TEXT,
  ADD COLUMN IF NOT EXISTS sms_consent_url TEXT;

COMMENT ON COLUMN leads.sms_consent      IS 'TRUE if the user explicitly opted in via the intake form checkbox.';
COMMENT ON COLUMN leads.sms_consent_at   IS 'Timestamp the consent checkbox was submitted.';
COMMENT ON COLUMN leads.sms_consent_ip   IS 'Client IP at time of opt-in (best-effort, X-Forwarded-For).';
COMMENT ON COLUMN leads.sms_consent_text IS 'Verbatim opt-in label text shown beside the checkbox at submission time. Versioned so we can prove what they agreed to.';
COMMENT ON COLUMN leads.sms_consent_url  IS 'URL of the page where consent was collected.';
