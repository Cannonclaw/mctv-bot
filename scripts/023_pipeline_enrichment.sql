-- 023_pipeline_enrichment.sql
-- Website enrichment columns for the sales pipeline.
-- Adds the fields populated by services/enrichment_service.py when a
-- prospect's website is scanned (contact info, hours, socials, images).
-- Run via Supabase SQL Editor (all additive / nullable — safe on live data).

ALTER TABLE pipeline_opportunities
    ADD COLUMN IF NOT EXISTS website TEXT,
    ADD COLUMN IF NOT EXISTS address TEXT,
    ADD COLUMN IF NOT EXISTS business_hours JSONB,
    ADD COLUMN IF NOT EXISTS social_links JSONB,
    ADD COLUMN IF NOT EXISTS website_images JSONB,
    ADD COLUMN IF NOT EXISTS enrichment JSONB;

COMMENT ON COLUMN pipeline_opportunities.website IS 'Business website URL (normalized https://...)';
COMMENT ON COLUMN pipeline_opportunities.business_hours IS 'Day->hours object or list of hour strings from website scan';
COMMENT ON COLUMN pipeline_opportunities.social_links IS 'Array of social profile URLs';
COMMENT ON COLUMN pipeline_opportunities.website_images IS 'Array of {url, alt, category} image refs selected from website scan';
COMMENT ON COLUMN pipeline_opportunities.enrichment IS 'Raw enrichment metadata (pages fetched, claude_used, scanned_at)';
