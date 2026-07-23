-- Quality Gate QG-02: Human Review Queue
-- Adds requires_review flag + review_flags for consistency validator output

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS requires_review BOOLEAN DEFAULT FALSE;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS review_flags JSONB DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_businesses_requires_review ON businesses(requires_review) WHERE requires_review = TRUE;
