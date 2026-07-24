-- combo_exhaustion_status table
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS combo_exhaustion_status (
    city TEXT NOT NULL,
    sector TEXT NOT NULL,
    freshness_rate FLOAT DEFAULT 1.0,
    total_discovered INT DEFAULT 0,
    classification TEXT DEFAULT 'insufficient_data',
    cooldown_seconds INT DEFAULT 21600,
    last_checked_at TIMESTAMPTZ,
    cooldown_expires_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active',
    PRIMARY KEY (city, sector)
);

-- Index for fast lookup of active combos
CREATE INDEX IF NOT EXISTS idx_combo_status ON combo_exhaustion_status(status);
CREATE INDEX IF NOT EXISTS idx_combo_expires ON combo_exhaustion_status(cooldown_expires_at);

-- Add new columns to businesses table for new data sources
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS social_presence_score INT DEFAULT 0;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS social_platforms_found JSONB DEFAULT '[]';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS linkedin_url TEXT;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS facebook_url TEXT;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS yelp_url TEXT;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS bbb_url TEXT;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS bbb_rating TEXT;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS bbb_accredited BOOLEAN;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS bbb_complaints INT DEFAULT 0;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS census_data JSONB DEFAULT '{}';
