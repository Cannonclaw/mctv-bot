-- ============================================================================
-- MCTV-Bot Schema Updates
-- Created: 2026-02-25
-- ============================================================================
--
-- This script adds new columns to the invoices and leads tables.
-- It is idempotent (safe to re-run) thanks to IF NOT EXISTS.
--
-- WHAT THIS DOES:
--   1. Adds payment tracking columns to invoices (amount_paid, payments, last_reminder_sent)
--   2. Adds follow-up reminder columns to leads (follow_up_date, follow_up_note)
--
-- HOW TO RUN:
--   Paste this into the Supabase SQL Editor and click "Run".
--
-- ============================================================================


-- ============================================================================
-- 1. INVOICES — Payment tracking columns
-- ============================================================================
-- amount_paid:        Running total of payments received (numeric, defaults to 0)
-- payments:           JSONB array of payment records, e.g.:
--                     [{"amount": 500, "date": "2026-02-15", "method": "check", "note": "Partial"}]
-- last_reminder_sent: ISO timestamp or description of when the last payment reminder was sent
-- ============================================================================

ALTER TABLE invoices ADD COLUMN IF NOT EXISTS amount_paid numeric DEFAULT 0;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payments jsonb DEFAULT '[]';
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS last_reminder_sent text;


-- ============================================================================
-- 2. LEADS — Follow-up reminder columns
-- ============================================================================
-- follow_up_date: Date when the team should follow up with this lead
-- follow_up_note: Context for the follow-up (e.g., "Call back after proposal review")
-- ============================================================================

ALTER TABLE leads ADD COLUMN IF NOT EXISTS follow_up_date date;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS follow_up_note text;


-- ============================================================================
-- NOTE: RLS policy updates are in a separate file:
--
--   scripts/fix_rls_policies.sql
--
-- That script is more complex (creates helper functions, drops/recreates all
-- policies across 11 tables, adds team CRUD policies, etc.) and should be
-- reviewed carefully before applying. Run it separately after this file.
-- ============================================================================
