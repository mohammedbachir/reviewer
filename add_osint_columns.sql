-- FindLeads v4.0 — OSINT Layer 2 columns
-- Run this in Supabase SQL Editor

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS firebase JSONB DEFAULT '{}'::jsonb;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS archive JSONB DEFAULT '{}'::jsonb;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS api_keys JSONB DEFAULT '{}'::jsonb;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS crtsh JSONB DEFAULT '{}'::jsonb;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS sherlock JSONB DEFAULT '{}'::jsonb;
