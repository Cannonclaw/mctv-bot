-- 026_host_creative_refresh.sql
-- Ad-refresh tracking for signed host venues.
-- Records when each host venue's on-screen creative was last remade, so
-- services/pipeline_service.get_hosts_needing_refresh() can surface what is
-- due on the 12-month cadence (docs/HOST_AD_REFRESH_PLAN.md).
--
-- NULL means the venue has never been refreshed. That reads as "due" — not
-- as an enormous overdue count — because the service checks for a missing
-- value before it does any date arithmetic.
--
-- DATE, not TIMESTAMPTZ, on purpose: PostgREST returns 'YYYY-MM-DD', which
-- keeps the plain ISO string comparisons in pipeline_service correct without
-- slicing. Same choice as next_action_date (scripts/008_pipeline_schema.sql).
--
-- Run via Supabase SQL Editor (all additive / nullable — safe on live data).

ALTER TABLE pipeline_opportunities
    ADD COLUMN IF NOT EXISTS last_creative_refresh DATE;

COMMENT ON COLUMN pipeline_opportunities.last_creative_refresh IS 'Host venues (deal_type=host, stage=live): date the on-screen creative was last remade. NULL = never refreshed. Set by hand on pages/20_HostPipeline.py; read by get_hosts_needing_refresh().';
