-- Migration 013: Tasks + Daily Email Log
-- Drop into: mctv-bot/scripts/013_tasks.sql
-- Run in Supabase SQL Editor.
-- Author: Cowork + Creed, 2026-05-19

-- =============================================================================
-- 1. Tasks
-- =============================================================================

CREATE TABLE IF NOT EXISTS tasks (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title               TEXT NOT NULL,
  description         TEXT,
  assigned_to         TEXT,                  -- NULL = group/unassigned task
  priority            TEXT DEFAULT 'normal'
                      CHECK (priority IN ('low','normal','high','urgent')),
  due_date            DATE,
  status              TEXT DEFAULT 'pending'
                      CHECK (status IN ('pending','done','snoozed','cancelled')),
  source              TEXT DEFAULT 'manual',
  source_id           TEXT,
  related_customer_id TEXT,
  related_contract_id TEXT,
  created_by          TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  completed_at        TIMESTAMPTZ,
  snoozed_until       DATE,
  tags                TEXT[] DEFAULT ARRAY[]::TEXT[],
  UNIQUE (source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_tasks_customer ON tasks(related_customer_id);

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY tasks_service_all ON tasks
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY tasks_select_authenticated ON tasks
  FOR SELECT TO authenticated USING (true);  -- all team members see all tasks (own + group)

-- =============================================================================
-- 2. Daily email log (for debugging + analytics)
-- =============================================================================

CREATE TABLE IF NOT EXISTS daily_task_email_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_member_id  TEXT NOT NULL,
  sent_at         TIMESTAMPTZ DEFAULT NOW(),
  subject         TEXT,
  body_summary    TEXT,
  task_count      INTEGER,
  status          TEXT DEFAULT 'sent'
                  CHECK (status IN ('sent','failed','skipped')),
  error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_email_log_sent_at ON daily_task_email_log(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_log_member  ON daily_task_email_log(team_member_id);

ALTER TABLE daily_task_email_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY email_log_service_all ON daily_task_email_log
  FOR ALL TO service_role USING (true) WITH CHECK (true);
