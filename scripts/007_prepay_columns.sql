-- Migration 007: Add prepay upfront columns to contracts table
-- Supports prepay bonus: 6-month = 1 free month, 12-month = 2 free months

ALTER TABLE contracts ADD COLUMN IF NOT EXISTS prepay_upfront BOOLEAN DEFAULT FALSE;
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS prepay_bonus_months INTEGER DEFAULT 0;
