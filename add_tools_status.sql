ALTER TABLE businesses ADD COLUMN IF NOT EXISTS tools_status JSONB DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_businesses_tools_status ON businesses USING GIN (tools_status);
