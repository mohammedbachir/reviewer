-- FindLeads v9.0 — Crisis Predictor AI
-- Run this in Supabase SQL Editor

-- Add model_state column to system_state for ML model persistence
ALTER TABLE system_state ADD COLUMN IF NOT EXISTS model_state TEXT DEFAULT '';

-- Add crisis_prediction columns to businesses
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS crisis_probability REAL DEFAULT 0;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS crisis_risk_level TEXT DEFAULT 'UNKNOWN';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS crisis_recommendations JSONB DEFAULT '[]';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS cvss_severity TEXT DEFAULT 'NONE';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS cvss_max REAL DEFAULT 0;

-- Index for crisis predictions
CREATE INDEX IF NOT EXISTS idx_businesses_crisis ON businesses(crisis_risk_level);
CREATE INDEX IF NOT EXISTS idx_businesses_crisis_prob ON businesses(crisis_probability DESC);
