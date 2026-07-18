-- ════════════════════════════════════════════════════════════════
-- FindLeads — Supabase Schema
-- Run this in Supabase SQL Editor
-- ════════════════════════════════════════════════════════════════

-- 1. Businesses table
CREATE TABLE IF NOT EXISTS businesses (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    sector TEXT NOT NULL,
    country TEXT DEFAULT '',
    rating REAL DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    website TEXT DEFAULT '',
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    address TEXT DEFAULT '',
    google_url TEXT DEFAULT '',
    category TEXT DEFAULT '',
    response_rate INTEGER DEFAULT 0,
    unanswered_reviews INTEGER DEFAULT 0,
    target_priority TEXT DEFAULT 'low',
    health_score INTEGER DEFAULT 50,
    ssl_grade TEXT DEFAULT '',
    tech_stack TEXT DEFAULT '[]',
    dns_data TEXT DEFAULT '{}',
    page_speed TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, city, sector)
);

-- 2. Snapshots table (temporal tracking)
CREATE TABLE IF NOT EXISTS snapshots (
    id BIGSERIAL PRIMARY KEY,
    business_id BIGINT REFERENCES businesses(id) ON DELETE CASCADE,
    scan_date DATE DEFAULT CURRENT_DATE,
    rating REAL,
    review_count INTEGER,
    health_score INTEGER,
    sentiment_score REAL DEFAULT 0,
    replied_to_reviews INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Scan runs table
CREATE TABLE IF NOT EXISTS scan_runs (
    id BIGSERIAL PRIMARY KEY,
    run_date TIMESTAMPTZ DEFAULT NOW(),
    city TEXT,
    sector TEXT,
    businesses_found INTEGER DEFAULT 0,
    emails_found INTEGER DEFAULT 0,
    osint_scanned INTEGER DEFAULT 0,
    duration_seconds REAL DEFAULT 0,
    status TEXT DEFAULT 'running'
);

-- 4. System state (for Vercel serverless rotation)
CREATE TABLE IF NOT EXISTS system_state (
    id BIGINT PRIMARY KEY DEFAULT 1,
    current_index INTEGER DEFAULT 0,
    last_run_at TIMESTAMPTZ,
    total_runs INTEGER DEFAULT 0,
    total_businesses INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Initialize system state
INSERT INTO system_state (id, current_index) VALUES (1, 0)
ON CONFLICT (id) DO NOTHING;

-- 5. Indexes
CREATE INDEX IF NOT EXISTS idx_businesses_city ON businesses(city);
CREATE INDEX IF NOT EXISTS idx_businesses_sector ON businesses(sector);
CREATE INDEX IF NOT EXISTS idx_businesses_health ON businesses(health_score);
CREATE INDEX IF NOT EXISTS idx_businesses_name_city ON businesses(name, city);
CREATE INDEX IF NOT EXISTS idx_snapshots_business ON snapshots(business_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON snapshots(scan_date);
