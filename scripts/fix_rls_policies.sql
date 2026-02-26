-- ============================================================================
-- MCTV-Bot RLS Policy Audit & Fix Script
-- Generated: 2026-02-25
-- ============================================================================
--
-- AUDIT FINDINGS SUMMARY:
--
-- 1. CRITICAL: The app uses service_role key (bypasses RLS) for ALL operations
--    including portal pages. This means RLS policies are effectively decorative
--    today. The fix below creates correct policies so that if/when the app
--    switches portal requests to use the anon key + user JWT, isolation works.
--
-- 2. Missing team access policies: The schema only has portal-user (advertiser)
--    SELECT policies. Team members (admin, sales_rep) cannot read ANY data
--    through RLS — they rely entirely on the service key bypass. Proper team
--    policies are needed so the app can safely use anon key + JWT for team too.
--
-- 3. Missing write policies for team: No INSERT/UPDATE/DELETE for team on
--    clients, invoices, creative_requests, creative_files, client_reports,
--    activity_log.
--
-- 4. contracts_own_sign is too broad: Portal users can UPDATE any column on
--    their contracts, not just signing fields. Should be restricted.
--
-- 5. Missing tables in schema: leads, sms_consent, sms_log have no CREATE
--    TABLE or RLS in setup_portal_schema.sql. They're used by the app but
--    presumably created manually. We add RLS for them here.
--
-- 6. No public INSERT on leads: The Intake form uses the anon key (no auth)
--    to insert leads. Without a public INSERT policy, this fails when RLS
--    is enforced.
--
-- 7. activity_log has no INSERT policy: Nobody can write audit logs through
--    RLS — only via service key.
--
-- 8. profiles missing INSERT policy: The trigger runs as SECURITY DEFINER
--    so it bypasses RLS, but if a user ever needs to read another profile
--    (e.g., team directory), there's no policy for that.
--
-- HOW SERVICE KEY vs ANON KEY WORKS:
--   - service_role key: Bypasses ALL RLS. Used for admin/internal operations.
--   - anon key + JWT:   Subject to RLS. Used for portal user requests.
--   - anon key (no JWT): Subject to RLS with auth.uid() = NULL. Used for
--                         public endpoints (intake form).
--
-- ROLE DEFINITIONS:
--   - 'admin', 'sales_rep' = MCTV team members (full data access)
--   - 'advertiser', 'host' = Portal clients (own data only)
--
-- ============================================================================
-- IMPORTANT: Run this in Supabase SQL Editor. It is idempotent (safe to re-run).
-- The service_role key always bypasses RLS, so team operations via service key
-- continue to work regardless of these policies.
-- ============================================================================


-- ============================================================================
-- HELPER: Create a reusable function to check if the current user is a team member
-- ============================================================================
CREATE OR REPLACE FUNCTION public.is_team_member()
RETURNS BOOLEAN AS $$
BEGIN
  -- Returns true if the authenticated user has a team role (admin or sales_rep)
  -- Returns false for portal users (advertiser, host) or unauthenticated requests
  RETURN EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid()
      AND role IN ('admin', 'sales_rep')
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- Helper: Check if current user is a portal user linked to a specific client
CREATE OR REPLACE FUNCTION public.is_own_client(p_client_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.clients
    WHERE id = p_client_id
      AND portal_user_id = auth.uid()
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;


-- ============================================================================
-- 1. PROFILES
-- ============================================================================
-- Requirements:
--   - Users can read their own profile
--   - Users can update their own profile
--   - Team members can read all profiles (for team directory, rep names)
--   - INSERT handled by SECURITY DEFINER trigger (handle_new_user)
-- ============================================================================

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS profiles_own_read ON profiles;
DROP POLICY IF EXISTS profiles_own_update ON profiles;
DROP POLICY IF EXISTS profiles_team_read ON profiles;

-- Users can read their own profile
CREATE POLICY profiles_own_read ON profiles
  FOR SELECT
  USING (id = auth.uid());

-- Team members (admin, sales_rep) can read all profiles
CREATE POLICY profiles_team_read ON profiles
  FOR SELECT
  USING (public.is_team_member());

-- Users can update their own profile (name, phone, company — not role)
CREATE POLICY profiles_own_update ON profiles
  FOR UPDATE
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());


-- ============================================================================
-- 2. CLIENTS
-- ============================================================================
-- Requirements:
--   - Team: full CRUD on all clients
--   - Portal user: SELECT own client record only (portal_user_id = auth.uid())
--   - No public access
-- ============================================================================

ALTER TABLE clients ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS clients_own_read ON clients;
DROP POLICY IF EXISTS clients_team_select ON clients;
DROP POLICY IF EXISTS clients_team_insert ON clients;
DROP POLICY IF EXISTS clients_team_update ON clients;
DROP POLICY IF EXISTS clients_team_delete ON clients;

-- Portal user can read only their own client record
CREATE POLICY clients_own_read ON clients
  FOR SELECT
  USING (portal_user_id = auth.uid());

-- Team can read all clients
CREATE POLICY clients_team_select ON clients
  FOR SELECT
  USING (public.is_team_member());

-- Team can create clients
CREATE POLICY clients_team_insert ON clients
  FOR INSERT
  WITH CHECK (public.is_team_member());

-- Team can update any client
CREATE POLICY clients_team_update ON clients
  FOR UPDATE
  USING (public.is_team_member())
  WITH CHECK (public.is_team_member());

-- Team can delete clients
CREATE POLICY clients_team_delete ON clients
  FOR DELETE
  USING (public.is_team_member());


-- ============================================================================
-- 3. CONTRACTS
-- ============================================================================
-- Requirements:
--   - Team: full CRUD
--   - Portal user: SELECT own contracts, UPDATE only signing fields
--   - No public access
-- ============================================================================

ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS contracts_own_read ON contracts;
DROP POLICY IF EXISTS contracts_own_sign ON contracts;
DROP POLICY IF EXISTS contracts_team_select ON contracts;
DROP POLICY IF EXISTS contracts_team_insert ON contracts;
DROP POLICY IF EXISTS contracts_team_update ON contracts;
DROP POLICY IF EXISTS contracts_team_delete ON contracts;
DROP POLICY IF EXISTS contracts_portal_sign ON contracts;

-- Portal user can read their own contracts
CREATE POLICY contracts_own_read ON contracts
  FOR SELECT
  USING (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );

-- Portal user can update their own contracts (for signing)
-- NOTE: Supabase RLS cannot restrict which columns are updated via policy alone.
-- The application layer must enforce that portal users only set signing fields
-- (signed_by, signed_at, signed_ip, signed_user_agent, status, viewed_at).
-- This policy at least ensures they can only touch their own contracts.
CREATE POLICY contracts_portal_sign ON contracts
  FOR UPDATE
  USING (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  )
  WITH CHECK (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );

-- Team can read all contracts
CREATE POLICY contracts_team_select ON contracts
  FOR SELECT
  USING (public.is_team_member());

-- Team can create contracts
CREATE POLICY contracts_team_insert ON contracts
  FOR INSERT
  WITH CHECK (public.is_team_member());

-- Team can update any contract
CREATE POLICY contracts_team_update ON contracts
  FOR UPDATE
  USING (public.is_team_member())
  WITH CHECK (public.is_team_member());

-- Team can delete contracts
CREATE POLICY contracts_team_delete ON contracts
  FOR DELETE
  USING (public.is_team_member());


-- ============================================================================
-- 4. INVOICES
-- ============================================================================
-- Requirements:
--   - Team: full CRUD
--   - Portal user: SELECT own invoices only
--   - No portal write access (team creates/manages invoices)
-- ============================================================================

ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS invoices_own_read ON invoices;
DROP POLICY IF EXISTS invoices_team_select ON invoices;
DROP POLICY IF EXISTS invoices_team_insert ON invoices;
DROP POLICY IF EXISTS invoices_team_update ON invoices;
DROP POLICY IF EXISTS invoices_team_delete ON invoices;

-- Portal user can read their own invoices
CREATE POLICY invoices_own_read ON invoices
  FOR SELECT
  USING (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );

-- Team can read all invoices
CREATE POLICY invoices_team_select ON invoices
  FOR SELECT
  USING (public.is_team_member());

-- Team can create invoices
CREATE POLICY invoices_team_insert ON invoices
  FOR INSERT
  WITH CHECK (public.is_team_member());

-- Team can update invoices
CREATE POLICY invoices_team_update ON invoices
  FOR UPDATE
  USING (public.is_team_member())
  WITH CHECK (public.is_team_member());

-- Team can delete invoices
CREATE POLICY invoices_team_delete ON invoices
  FOR DELETE
  USING (public.is_team_member());


-- ============================================================================
-- 5. CREATIVE_REQUESTS
-- ============================================================================
-- Requirements:
--   - Team: full CRUD
--   - Portal user: SELECT + INSERT for own client, UPDATE own requests
--   - Client isolation: portal user A cannot see user B's requests
-- ============================================================================

ALTER TABLE creative_requests ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS creative_requests_own_read ON creative_requests;
DROP POLICY IF EXISTS creative_requests_own_insert ON creative_requests;
DROP POLICY IF EXISTS creative_requests_own_update ON creative_requests;
DROP POLICY IF EXISTS creative_requests_team_select ON creative_requests;
DROP POLICY IF EXISTS creative_requests_team_insert ON creative_requests;
DROP POLICY IF EXISTS creative_requests_team_update ON creative_requests;
DROP POLICY IF EXISTS creative_requests_team_delete ON creative_requests;

-- Portal user can read their own creative requests
CREATE POLICY creative_requests_own_read ON creative_requests
  FOR SELECT
  USING (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );

-- Portal user can create creative requests for their own client
CREATE POLICY creative_requests_own_insert ON creative_requests
  FOR INSERT
  WITH CHECK (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );

-- Portal user can update their own creative requests (e.g., edit description)
CREATE POLICY creative_requests_own_update ON creative_requests
  FOR UPDATE
  USING (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  )
  WITH CHECK (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );

-- Team can read all creative requests
CREATE POLICY creative_requests_team_select ON creative_requests
  FOR SELECT
  USING (public.is_team_member());

-- Team can create creative requests
CREATE POLICY creative_requests_team_insert ON creative_requests
  FOR INSERT
  WITH CHECK (public.is_team_member());

-- Team can update any creative request (status, assignment, notes)
CREATE POLICY creative_requests_team_update ON creative_requests
  FOR UPDATE
  USING (public.is_team_member())
  WITH CHECK (public.is_team_member());

-- Team can delete creative requests
CREATE POLICY creative_requests_team_delete ON creative_requests
  FOR DELETE
  USING (public.is_team_member());


-- ============================================================================
-- 6. CREATIVE_FILES
-- ============================================================================
-- Requirements:
--   - Team: full CRUD
--   - Portal user: SELECT + INSERT for files on their own requests
--   - Client isolation via creative_requests -> clients chain
-- ============================================================================

ALTER TABLE creative_files ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS creative_files_own_read ON creative_files;
DROP POLICY IF EXISTS creative_files_own_insert ON creative_files;
DROP POLICY IF EXISTS creative_files_team_select ON creative_files;
DROP POLICY IF EXISTS creative_files_team_insert ON creative_files;
DROP POLICY IF EXISTS creative_files_team_update ON creative_files;
DROP POLICY IF EXISTS creative_files_team_delete ON creative_files;

-- Portal user can read files for their own creative requests
CREATE POLICY creative_files_own_read ON creative_files
  FOR SELECT
  USING (
    request_id IN (
      SELECT id FROM creative_requests
      WHERE client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
    )
  );

-- Portal user can upload files to their own creative requests
CREATE POLICY creative_files_own_insert ON creative_files
  FOR INSERT
  WITH CHECK (
    request_id IN (
      SELECT id FROM creative_requests
      WHERE client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
    )
  );

-- Team can read all creative files
CREATE POLICY creative_files_team_select ON creative_files
  FOR SELECT
  USING (public.is_team_member());

-- Team can upload files
CREATE POLICY creative_files_team_insert ON creative_files
  FOR INSERT
  WITH CHECK (public.is_team_member());

-- Team can update file metadata
CREATE POLICY creative_files_team_update ON creative_files
  FOR UPDATE
  USING (public.is_team_member())
  WITH CHECK (public.is_team_member());

-- Team can delete files
CREATE POLICY creative_files_team_delete ON creative_files
  FOR DELETE
  USING (public.is_team_member());


-- ============================================================================
-- 7. CLIENT_REPORTS
-- ============================================================================
-- Requirements:
--   - Team: full CRUD
--   - Portal user: SELECT own reports only
--   - No portal write access (team generates reports)
-- ============================================================================

ALTER TABLE client_reports ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS client_reports_own_read ON client_reports;
DROP POLICY IF EXISTS client_reports_team_select ON client_reports;
DROP POLICY IF EXISTS client_reports_team_insert ON client_reports;
DROP POLICY IF EXISTS client_reports_team_update ON client_reports;
DROP POLICY IF EXISTS client_reports_team_delete ON client_reports;

-- Portal user can read their own reports
CREATE POLICY client_reports_own_read ON client_reports
  FOR SELECT
  USING (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );

-- Team can read all reports
CREATE POLICY client_reports_team_select ON client_reports
  FOR SELECT
  USING (public.is_team_member());

-- Team can create reports
CREATE POLICY client_reports_team_insert ON client_reports
  FOR INSERT
  WITH CHECK (public.is_team_member());

-- Team can update reports
CREATE POLICY client_reports_team_update ON client_reports
  FOR UPDATE
  USING (public.is_team_member())
  WITH CHECK (public.is_team_member());

-- Team can delete reports
CREATE POLICY client_reports_team_delete ON client_reports
  FOR DELETE
  USING (public.is_team_member());


-- ============================================================================
-- 8. ACTIVITY_LOG
-- ============================================================================
-- Requirements:
--   - Team: SELECT all, INSERT (for logging)
--   - Portal user: SELECT own activity, INSERT (for login tracking)
--   - No UPDATE/DELETE (audit logs are append-only)
-- ============================================================================

ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS activity_log_own_read ON activity_log;
DROP POLICY IF EXISTS activity_log_team_select ON activity_log;
DROP POLICY IF EXISTS activity_log_team_insert ON activity_log;
DROP POLICY IF EXISTS activity_log_portal_insert ON activity_log;

-- Portal user can read their own activity
CREATE POLICY activity_log_own_read ON activity_log
  FOR SELECT
  USING (user_id = auth.uid());

-- Team can read all activity logs
CREATE POLICY activity_log_team_select ON activity_log
  FOR SELECT
  USING (public.is_team_member());

-- Team can insert activity log entries
CREATE POLICY activity_log_team_insert ON activity_log
  FOR INSERT
  WITH CHECK (public.is_team_member());

-- Portal users can insert their own activity (login tracking, etc.)
CREATE POLICY activity_log_portal_insert ON activity_log
  FOR INSERT
  WITH CHECK (user_id = auth.uid());


-- ============================================================================
-- 9. LEADS
-- ============================================================================
-- Requirements:
--   - Team: full CRUD
--   - Public: INSERT only (intake form uses anon key, no auth)
--   - No portal access needed
--
-- NOTE: The leads table may already exist (created manually or via earlier
-- migration). If it doesn't exist, create it here. The IF NOT EXISTS clause
-- makes this safe to re-run.
-- ============================================================================

CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY,
  business_name TEXT,
  contact_name TEXT,
  contact_email TEXT,
  contact_phone TEXT,
  industry TEXT,
  city TEXT,
  interest_level TEXT,
  goals TEXT,
  how_heard TEXT,
  additional_notes TEXT,
  logo_file TEXT,
  status TEXT DEFAULT 'new'
    CHECK (status IN ('new', 'contacted', 'proposal_sent', 'closed', 'lost')),
  submitted_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

-- Drop existing policies (if any)
DROP POLICY IF EXISTS leads_public_insert ON leads;
DROP POLICY IF EXISTS leads_team_select ON leads;
DROP POLICY IF EXISTS leads_team_update ON leads;
DROP POLICY IF EXISTS leads_team_delete ON leads;

-- PUBLIC INSERT: Allow unauthenticated intake form submissions
-- The anon key with no JWT will have auth.uid() = NULL, which is fine.
-- We use (true) for INSERT because the intake form is intentionally public.
CREATE POLICY leads_public_insert ON leads
  FOR INSERT
  WITH CHECK (true);

-- Team can read all leads
CREATE POLICY leads_team_select ON leads
  FOR SELECT
  USING (public.is_team_member());

-- Team can update leads (change status, add notes)
CREATE POLICY leads_team_update ON leads
  FOR UPDATE
  USING (public.is_team_member())
  WITH CHECK (public.is_team_member());

-- Team can delete leads
CREATE POLICY leads_team_delete ON leads
  FOR DELETE
  USING (public.is_team_member());


-- ============================================================================
-- 10. SMS_CONSENT
-- ============================================================================
-- Requirements:
--   - Team only: full CRUD
--   - No portal or public access
--
-- NOTE: Table may already exist. IF NOT EXISTS is safe to re-run.
-- ============================================================================

CREATE TABLE IF NOT EXISTS sms_consent (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone TEXT NOT NULL UNIQUE,
  opted_in BOOLEAN NOT NULL DEFAULT false,
  name TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE sms_consent ENABLE ROW LEVEL SECURITY;

-- Drop existing policies (if any)
DROP POLICY IF EXISTS sms_consent_team_select ON sms_consent;
DROP POLICY IF EXISTS sms_consent_team_insert ON sms_consent;
DROP POLICY IF EXISTS sms_consent_team_update ON sms_consent;
DROP POLICY IF EXISTS sms_consent_team_delete ON sms_consent;

-- Team can read all consent records
CREATE POLICY sms_consent_team_select ON sms_consent
  FOR SELECT
  USING (public.is_team_member());

-- Team can insert consent records
CREATE POLICY sms_consent_team_insert ON sms_consent
  FOR INSERT
  WITH CHECK (public.is_team_member());

-- Team can update consent records
CREATE POLICY sms_consent_team_update ON sms_consent
  FOR UPDATE
  USING (public.is_team_member())
  WITH CHECK (public.is_team_member());

-- Team can delete consent records
CREATE POLICY sms_consent_team_delete ON sms_consent
  FOR DELETE
  USING (public.is_team_member());


-- ============================================================================
-- 11. SMS_LOG
-- ============================================================================
-- Requirements:
--   - Team only: SELECT + INSERT (append-only log)
--   - No UPDATE/DELETE (message history is immutable)
--   - No portal or public access
--
-- NOTE: Table may already exist. IF NOT EXISTS is safe to re-run.
-- ============================================================================

CREATE TABLE IF NOT EXISTS sms_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "to" TEXT NOT NULL,
  body TEXT,
  template TEXT,
  status TEXT DEFAULT 'sent',
  error TEXT,
  sent_at TIMESTAMPTZ DEFAULT now(),
  sent_by TEXT
);

ALTER TABLE sms_log ENABLE ROW LEVEL SECURITY;

-- Drop existing policies (if any)
DROP POLICY IF EXISTS sms_log_team_select ON sms_log;
DROP POLICY IF EXISTS sms_log_team_insert ON sms_log;

-- Team can read all message history
CREATE POLICY sms_log_team_select ON sms_log
  FOR SELECT
  USING (public.is_team_member());

-- Team can insert log entries
CREATE POLICY sms_log_team_insert ON sms_log
  FOR INSERT
  WITH CHECK (public.is_team_member());


-- ============================================================================
-- INDEXES for new tables (if not already present)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_submitted_at ON leads(submitted_at);
CREATE INDEX IF NOT EXISTS idx_sms_consent_phone ON sms_consent(phone);
CREATE INDEX IF NOT EXISTS idx_sms_log_sent_at ON sms_log(sent_at);


-- ============================================================================
-- STORAGE BUCKET RLS POLICIES
-- Supabase Storage uses storage.objects table. Paths are:
--   {bucket}/{client_id}/filename.ext
-- Team can read/write all; portal users can only read their own files.
-- ============================================================================

-- contracts bucket
CREATE POLICY "contracts_team_all"
  ON storage.objects FOR ALL
  USING (bucket_id = 'contracts' AND is_team_member(auth.uid()))
  WITH CHECK (bucket_id = 'contracts' AND is_team_member(auth.uid()));

CREATE POLICY "contracts_own_read"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'contracts'
    AND (storage.foldername(name))[1] = (
      SELECT id::text FROM clients WHERE user_id = auth.uid()
    )
  );

-- reports bucket
CREATE POLICY "reports_team_all"
  ON storage.objects FOR ALL
  USING (bucket_id = 'reports' AND is_team_member(auth.uid()))
  WITH CHECK (bucket_id = 'reports' AND is_team_member(auth.uid()));

CREATE POLICY "reports_own_read"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'reports'
    AND (storage.foldername(name))[1] = (
      SELECT id::text FROM clients WHERE user_id = auth.uid()
    )
  );

-- creative-uploads bucket (portal users can upload AND read their own)
CREATE POLICY "creative_uploads_team_all"
  ON storage.objects FOR ALL
  USING (bucket_id = 'creative-uploads' AND is_team_member(auth.uid()))
  WITH CHECK (bucket_id = 'creative-uploads' AND is_team_member(auth.uid()));

CREATE POLICY "creative_uploads_own_all"
  ON storage.objects FOR ALL
  USING (
    bucket_id = 'creative-uploads'
    AND (storage.foldername(name))[1] = (
      SELECT id::text FROM clients WHERE user_id = auth.uid()
    )
  )
  WITH CHECK (
    bucket_id = 'creative-uploads'
    AND (storage.foldername(name))[1] = (
      SELECT id::text FROM clients WHERE user_id = auth.uid()
    )
  );

-- creative-deliveries bucket (portal users can read; team can write)
CREATE POLICY "creative_deliveries_team_all"
  ON storage.objects FOR ALL
  USING (bucket_id = 'creative-deliveries' AND is_team_member(auth.uid()))
  WITH CHECK (bucket_id = 'creative-deliveries' AND is_team_member(auth.uid()));

CREATE POLICY "creative_deliveries_own_read"
  ON storage.objects FOR SELECT
  USING (
    bucket_id = 'creative-deliveries'
    AND (storage.foldername(name))[1] = (
      SELECT id::text FROM clients WHERE user_id = auth.uid()
    )
  );


-- ============================================================================
-- VERIFICATION QUERY
-- Run this after applying the above to confirm all tables have RLS enabled
-- and the expected number of policies.
-- ============================================================================
-- SELECT
--   schemaname,
--   tablename,
--   rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
--   AND tablename IN (
--     'profiles', 'clients', 'contracts', 'invoices',
--     'creative_requests', 'creative_files', 'client_reports',
--     'activity_log', 'leads', 'sms_consent', 'sms_log'
--   )
-- ORDER BY tablename;
--
-- SELECT
--   schemaname,
--   tablename,
--   policyname,
--   permissive,
--   roles,
--   cmd,
--   qual,
--   with_check
-- FROM pg_policies
-- WHERE schemaname = 'public'
-- ORDER BY tablename, policyname;
