-- FindLeads v3.0 — Add new columns to businesses table
-- Go to: https://supabase.com/dashboard → SQL Editor → New Query → Paste → Run

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS lead_temperature TEXT DEFAULT 'COLD';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS outreach_hook TEXT DEFAULT '';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS email_confidence INTEGER DEFAULT 0;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS email_source TEXT DEFAULT '';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS sentiment TEXT DEFAULT 'neutral';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS responds_to_reviews BOOLEAN DEFAULT FALSE;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS owner_name TEXT DEFAULT '';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS instagram TEXT DEFAULT '';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS facebook TEXT DEFAULT '';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS twitter TEXT DEFAULT '';

-- FindLeads v5.0 — Multi-Source Intelligence columns
-- Run this AFTER the columns above

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS vulnerabilities JSONB DEFAULT '[]';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS open_ports JSONB DEFAULT '[]';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS breaches INTEGER DEFAULT 0;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS security_warnings JSONB DEFAULT '[]';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS breach_count INTEGER DEFAULT 0;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS breach_names JSONB DEFAULT '[]';
