-- Pipeline editability + true-data migration
-- Additive only: every new column is nullable or defaulted, so every existing
-- row and every existing INSERT keeps working untouched.

-- ── 1. Real close date ───────────────────────────────────────────────────────
-- Today "won this month" is computed from updated_at, so merely EDITING an old
-- won deal re-dates the win into the current month. closed_date is the actual
-- date the deal was won or lost, set explicitly and never moved by an edit.
alter table pipeline_opportunities
  add column if not exists closed_date date;

-- ── 2. Custom / non-tier pricing ─────────────────────────────────────────────
-- Pricing was locked to 4 fixed tiers. Real submitted proposals are $3,850,
-- $4,950/mo, $2,000 flat, $21,000 flight — none of which fit a tier.
alter table pipeline_opportunities
  add column if not exists pricing_mode   text    not null default 'tier',
  add column if not exists one_time_value numeric not null default 0,
  add column if not exists term_months    integer;

alter table pipeline_opportunities
  drop constraint if exists pipeline_opportunities_pricing_mode_check;
alter table pipeline_opportunities
  add constraint pipeline_opportunities_pricing_mode_check
  check (pricing_mode in ('tier', 'custom'));

-- ── 3. Keep the record, drop it from the math ────────────────────────────────
-- Middle ground between "delete" and "let it skew the stats": partnerships,
-- barters and $0 placeholders stay visible but stop distorting win rate,
-- average deal size and pipeline value.
alter table pipeline_opportunities
  add column if not exists excluded_from_stats boolean not null default false,
  add column if not exists exclusion_reason    text;

-- ── 4. Deletion archive (so a hard delete stays recoverable) ─────────────────
-- pipeline_activity cascades on delete, so the activity trail is snapshotted
-- here too and restored with the deal.
create table if not exists pipeline_deleted (
  id              uuid primary key default gen_random_uuid(),
  opportunity_id  uuid        not null,
  business_name   text        not null,
  deal_type       text,
  stage           text,
  monthly_value   numeric,
  deal_data       jsonb       not null,
  activity_data   jsonb       not null default '[]'::jsonb,
  deleted_by      text,
  deleted_reason  text,
  merged_into     uuid,
  deleted_at      timestamptz not null default now()
);

create index if not exists pipeline_deleted_deleted_at_idx
  on pipeline_deleted (deleted_at desc);
create index if not exists pipeline_deleted_opportunity_id_idx
  on pipeline_deleted (opportunity_id);

-- Matches the house pattern used by screen_loops / dark_content:
-- RLS on with NO policies = service-role only.
alter table pipeline_deleted enable row level security;

-- ── 4b. Allow the new activity verbs ─────────────────────────────────────────
-- pipeline_activity.action is CHECK-constrained to a fixed vocabulary. Merging
-- and restoring log 'merged' and 'restored'; without this the audit trail for
-- exactly the operations that destroy data would be silently rejected.
alter table pipeline_activity
  drop constraint if exists pipeline_activity_action_check;
alter table pipeline_activity
  add constraint pipeline_activity_action_check
  check (action in (
    'created', 'stage_change', 'note_added', 'email_sent', 'sms_sent',
    'call_logged', 'proposal_generated', 'contract_sent', 'value_updated',
    'nurture_sent', 'follow_up_set', 'assigned',
    'merged', 'restored', 'deleted', 'pricing_changed', 'backdated'
  ));

-- ── 5. Backfill closed_date for deals already won/lost ───────────────────────
-- Best available signal for historical rows is updated_at (the timestamp of the
-- move into won/lost). Creed can correct any of these in the Edit form.
update pipeline_opportunities
   set closed_date = coalesce(updated_at, created_at)::date
 where stage in ('won', 'lost')
   and closed_date is null;

-- ── 6. Query support ─────────────────────────────────────────────────────────
create index if not exists pipeline_opportunities_closed_date_idx
  on pipeline_opportunities (closed_date desc)
  where stage in ('won', 'lost');
