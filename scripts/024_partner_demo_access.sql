-- 024_partner_demo_access.sql
-- Partner / evaluation access for the client portal.
--
-- Backs the read-only demo account given to outside organizations (e.g. NTV360)
-- so they can evaluate the portal without ever touching real client data.
--
-- Adds:
--   * a 'partner' role on profiles
--   * demo-tenant + time-boxed access columns on clients
--   * portal_terms_acceptances — click-through proof that evaluation terms were accepted
--   * portal_login_attempts — server-side rate limiting (replaces the per-tab
--     st.session_state limiter in services/auth.py)
--
-- Run via Supabase SQL Editor. All additive / nullable — safe on live data.

-- ── 1. Allow the 'partner' role ────────────────────────────────────────────
-- profiles.role is CHECK-constrained; 'partner' must be added explicitly.
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE profiles ADD CONSTRAINT profiles_role_check
    CHECK (role IN ('admin', 'sales_rep', 'advertiser', 'host', 'partner'));

COMMENT ON COLUMN profiles.role IS
    'admin | sales_rep | advertiser | host | partner. '
    '''partner'' is read-only evaluation access — see services/partner_access.py';


-- ── 2. Demo tenant + time-boxed access on clients ──────────────────────────
ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS partner_org TEXT,
    ADD COLUMN IF NOT EXISTS portal_access_expires_at TIMESTAMPTZ;

COMMENT ON COLUMN clients.is_demo IS
    'True for synthetic sandbox tenants. Demo rows must never mix with real client data.';
COMMENT ON COLUMN clients.partner_org IS
    'Outside organization this demo account was issued to (e.g. "NTV360"). Used in watermarks.';
COMMENT ON COLUMN clients.portal_access_expires_at IS
    'Hard expiry for portal access. Enforced in services/auth.py:check_portal_auth() '
    'so live sessions are ejected, not just new logins. NULL = no expiry.';

-- get_client_by_user_id() runs on every portal page load.
CREATE INDEX IF NOT EXISTS idx_clients_portal_user_id
    ON clients (portal_user_id) WHERE portal_user_id IS NOT NULL;

-- Keeps demo rows cheap to exclude from real reporting.
CREATE INDEX IF NOT EXISTS idx_clients_is_demo ON clients (is_demo) WHERE is_demo = true;


-- ── 3. Terms acceptance record ─────────────────────────────────────────────
-- Passive "by using this you agree" is not evidence. This is.
CREATE TABLE IF NOT EXISTS portal_terms_acceptances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    terms_version TEXT NOT NULL,
    terms_kind TEXT NOT NULL DEFAULT 'partner_evaluation'
        CHECK (terms_kind IN ('partner_evaluation', 'client')),
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address TEXT,
    user_agent TEXT
);

COMMENT ON TABLE portal_terms_acceptances IS
    'Proof-of-acceptance for portal terms. One row per user per terms_version.';

CREATE UNIQUE INDEX IF NOT EXISTS idx_terms_acceptance_unique
    ON portal_terms_acceptances (user_id, terms_kind, terms_version);
CREATE INDEX IF NOT EXISTS idx_terms_acceptance_email
    ON portal_terms_acceptances (email);


-- ── 4. Server-side login rate limiting ─────────────────────────────────────
-- The existing limiter lives in st.session_state, so it resets on a new tab.
CREATE TABLE IF NOT EXISTS portal_login_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_key TEXT NOT NULL,      -- normalized email, IP, or "team:<ip>"
    kind TEXT NOT NULL DEFAULT 'password'
        CHECK (kind IN ('password', 'magic_link', 'reset', 'team')),
    succeeded BOOLEAN NOT NULL DEFAULT false,
    ip_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE portal_login_attempts IS
    'Append-only auth attempt log backing server-side rate limiting. '
    'Prune rows older than 24h periodically.';

CREATE INDEX IF NOT EXISTS idx_login_attempts_lookup
    ON portal_login_attempts (attempt_key, kind, created_at DESC);


-- ── 5. RLS ─────────────────────────────────────────────────────────────────
-- Enabled for correctness on the day the portal migrates off the service-role
-- key. Today the service key bypasses these (see scripts/fix_rls_policies.sql).
ALTER TABLE portal_terms_acceptances ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_login_attempts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS terms_acceptance_own_read ON portal_terms_acceptances;
CREATE POLICY terms_acceptance_own_read ON portal_terms_acceptances
    FOR SELECT USING (user_id = auth.uid());

DROP POLICY IF EXISTS terms_acceptance_own_insert ON portal_terms_acceptances;
CREATE POLICY terms_acceptance_own_insert ON portal_terms_acceptances
    FOR INSERT WITH CHECK (user_id = auth.uid());

-- No policies on portal_login_attempts: service-role only, by design.
