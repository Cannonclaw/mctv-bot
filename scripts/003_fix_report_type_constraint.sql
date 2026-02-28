-- Migration 003: Fix report_type CHECK constraint on client_reports
--
-- Bug: pages/2_Reports.py inserts report_type = 'advertiser' or 'venue',
-- but the original CHECK constraint only allows ('traction', 'monthly_summary', 'impressions').
-- Also adds 'traction' which is used by the automated monthly report pipeline.
--
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/YOUR_PROJECT/sql
-- Safe to run multiple times (DROP IF EXISTS).

ALTER TABLE client_reports DROP CONSTRAINT IF EXISTS client_reports_report_type_check;

ALTER TABLE client_reports ADD CONSTRAINT client_reports_report_type_check
  CHECK (report_type IN ('traction', 'monthly_summary', 'impressions', 'advertiser', 'venue'));
