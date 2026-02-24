-- ============================================================================
-- MCTV Client Portal — Supabase Schema
-- Run this in Supabase SQL Editor (https://supabase.com/dashboard → SQL Editor)
-- ============================================================================

-- 1. PROFILES — Links Supabase Auth users to roles
-- ============================================================================
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  full_name TEXT NOT NULL,
  phone TEXT,
  role TEXT NOT NULL DEFAULT 'advertiser'
    CHECK (role IN ('admin', 'sales_rep', 'advertiser', 'host')),
  company_name TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Auto-create a profile row when a new user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, role)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
    COALESCE(NEW.raw_user_meta_data->>'role', 'advertiser')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 2. CLIENTS — Business entities (advertisers + hosts)
-- ============================================================================
CREATE TABLE IF NOT EXISTS clients (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id TEXT,
  business_name TEXT NOT NULL,
  contact_name TEXT NOT NULL,
  contact_email TEXT NOT NULL,
  contact_phone TEXT,
  industry TEXT,
  city TEXT,
  client_type TEXT NOT NULL DEFAULT 'advertiser'
    CHECK (client_type IN ('advertiser', 'host')),
  status TEXT DEFAULT 'onboarding'
    CHECK (status IN ('onboarding', 'active', 'paused', 'churned')),
  portal_user_id UUID REFERENCES profiles(id),
  assigned_rep TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. CONTRACTS — Service agreements with click-to-sign
-- ============================================================================
CREATE TABLE IF NOT EXISTS contracts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  contract_type TEXT NOT NULL
    CHECK (contract_type IN ('advertising', 'host_media_kit', 'category_exclusivity', 'bundle')),
  title TEXT NOT NULL,
  -- Pricing terms
  tier_name TEXT,
  screen_count INT,
  monthly_rate DECIMAL(10, 2),
  -- Duration
  start_date DATE,
  end_date DATE,
  auto_renew BOOLEAN DEFAULT true,
  term_months INT DEFAULT 6,
  -- Coverage
  markets TEXT[],
  -- Document
  document_url TEXT,
  -- Status + signing
  status TEXT DEFAULT 'draft'
    CHECK (status IN ('draft', 'sent', 'viewed', 'signed', 'active', 'expired', 'cancelled')),
  signed_by TEXT,
  signed_at TIMESTAMPTZ,
  signed_ip TEXT,
  signed_user_agent TEXT,
  sent_at TIMESTAMPTZ,
  viewed_at TIMESTAMPTZ,
  -- Metadata
  created_by TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 4. INVOICES — Billing records (manual payment tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  contract_id UUID REFERENCES contracts(id),
  invoice_number TEXT NOT NULL UNIQUE,
  amount DECIMAL(10, 2) NOT NULL,
  description TEXT,
  period_start DATE,
  period_end DATE,
  issued_date DATE NOT NULL,
  due_date DATE NOT NULL,
  paid_date DATE,
  status TEXT DEFAULT 'draft'
    CHECK (status IN ('draft', 'sent', 'viewed', 'overdue', 'paid', 'void')),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. CREATIVE_REQUESTS — Client creative/asset submissions
-- ============================================================================
CREATE TABLE IF NOT EXISTS creative_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  submitted_by UUID REFERENCES profiles(id),
  request_type TEXT NOT NULL
    CHECK (request_type IN ('new_ad', 'update_ad', 'logo_upload', 'photo_upload', 'general')),
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'pending'
    CHECK (status IN ('pending', 'in_progress', 'review', 'approved', 'live', 'rejected')),
  priority TEXT DEFAULT 'normal'
    CHECK (priority IN ('low', 'normal', 'urgent')),
  assigned_to TEXT,
  internal_notes TEXT,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 6. CREATIVE_FILES — Files attached to creative requests
-- ============================================================================
CREATE TABLE IF NOT EXISTS creative_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id UUID NOT NULL REFERENCES creative_requests(id) ON DELETE CASCADE,
  file_name TEXT NOT NULL,
  file_type TEXT,
  file_size INT,
  storage_path TEXT NOT NULL,
  uploaded_by UUID REFERENCES profiles(id),
  uploaded_at TIMESTAMPTZ DEFAULT now()
);

-- 7. CLIENT_REPORTS — Traction reports shared with clients
-- ============================================================================
CREATE TABLE IF NOT EXISTS client_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  report_type TEXT NOT NULL
    CHECK (report_type IN ('traction', 'monthly_summary', 'impressions')),
  title TEXT NOT NULL,
  campaign_period TEXT,
  document_url TEXT,
  total_plays INT,
  total_impressions BIGINT,
  total_venues INT,
  highlights TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 8. ACTIVITY_LOG — Audit trail
-- ============================================================================
CREATE TABLE IF NOT EXISTS activity_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  client_id UUID REFERENCES clients(id),
  action TEXT NOT NULL,
  entity_type TEXT,
  entity_id UUID,
  details JSONB,
  ip_address TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- ROW-LEVEL SECURITY POLICIES
-- Clients see only their own data. Admin/service key bypasses RLS.
-- ============================================================================

-- Profiles: users can read their own profile
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY profiles_own_read ON profiles
  FOR SELECT USING (id = auth.uid());
CREATE POLICY profiles_own_update ON profiles
  FOR UPDATE USING (id = auth.uid());

-- Clients: portal users see their own client record
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
CREATE POLICY clients_own_read ON clients
  FOR SELECT USING (portal_user_id = auth.uid());

-- Contracts: see contracts for your client record
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
CREATE POLICY contracts_own_read ON contracts
  FOR SELECT USING (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );
-- Allow clients to update their own contracts (for signing)
CREATE POLICY contracts_own_sign ON contracts
  FOR UPDATE USING (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );

-- Invoices: see invoices for your client
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY invoices_own_read ON invoices
  FOR SELECT USING (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );

-- Creative requests: see and create for your client
ALTER TABLE creative_requests ENABLE ROW LEVEL SECURITY;
CREATE POLICY creative_requests_own_read ON creative_requests
  FOR SELECT USING (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );
CREATE POLICY creative_requests_own_insert ON creative_requests
  FOR INSERT WITH CHECK (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );

-- Creative files: see files for your requests
ALTER TABLE creative_files ENABLE ROW LEVEL SECURITY;
CREATE POLICY creative_files_own_read ON creative_files
  FOR SELECT USING (
    request_id IN (
      SELECT id FROM creative_requests
      WHERE client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
    )
  );
CREATE POLICY creative_files_own_insert ON creative_files
  FOR INSERT WITH CHECK (
    request_id IN (
      SELECT id FROM creative_requests
      WHERE client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
    )
  );

-- Client reports: see reports shared with your client
ALTER TABLE client_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY client_reports_own_read ON client_reports
  FOR SELECT USING (
    client_id IN (SELECT id FROM clients WHERE portal_user_id = auth.uid())
  );

-- Activity log: see your own activity
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY activity_log_own_read ON activity_log
  FOR SELECT USING (user_id = auth.uid());

-- ============================================================================
-- INDEXES for performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_clients_portal_user ON clients(portal_user_id);
CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);
CREATE INDEX IF NOT EXISTS idx_contracts_client ON contracts(client_id);
CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status);
CREATE INDEX IF NOT EXISTS idx_invoices_client ON invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON invoices(due_date);
CREATE INDEX IF NOT EXISTS idx_creative_requests_client ON creative_requests(client_id);
CREATE INDEX IF NOT EXISTS idx_creative_files_request ON creative_files(request_id);
CREATE INDEX IF NOT EXISTS idx_client_reports_client ON client_reports(client_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_client ON activity_log(client_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created ON activity_log(created_at);

-- ============================================================================
-- STORAGE BUCKETS (run these in the Supabase Dashboard > Storage)
-- Or use the Supabase client SDK to create them programmatically
-- ============================================================================
-- Bucket: contracts        (private) — generated contract PDFs
-- Bucket: reports          (private) — shared traction report PDFs
-- Bucket: creative-uploads (private) — client-submitted photos/logos
-- Bucket: creative-deliveries (private) — MCTV-produced ad creatives
