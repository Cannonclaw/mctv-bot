-- ============================================================================
-- MCTV-Bot Schema Update: Contract Columns
-- Created: 2026-03-09
-- ============================================================================
--
-- This script adds missing columns to the contracts table that the
-- application code already references but were never added via migration.
--
-- WHAT THIS DOES:
--   1. Adds exclusive_category (TEXT) for Category Exclusivity contracts
--   2. Adds bundle_brands (TEXT[]) for Bundle contracts
--   3. Adds tier_options (JSONB) for Good/Better/Best tier comparison
--   4. Adds selected_tier (TEXT) to track client's tier choice
--
-- HOW TO RUN:
--   Paste this into the Supabase SQL Editor and click "Run".
--   Safe to re-run (uses IF NOT EXISTS).
--
-- ============================================================================

ALTER TABLE contracts ADD COLUMN IF NOT EXISTS exclusive_category TEXT;
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS bundle_brands TEXT[];
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS tier_options JSONB;
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS selected_tier TEXT;
