-- v007: Add promotion fields to skill, rule, knowledge_document tables
-- Run on controller database (aidp_controller)

ALTER TABLE aidp_skill
    ADD COLUMN IF NOT EXISTS promotion_status VARCHAR(20) DEFAULT 'none',
    ADD COLUMN IF NOT EXISTS promotion_report TEXT,
    ADD COLUMN IF NOT EXISTS promotion_source_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS promotion_source_scope VARCHAR(20),
    ADD COLUMN IF NOT EXISTS promotion_promoted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_skill_promotion_status ON aidp_skill (promotion_status);
CREATE INDEX IF NOT EXISTS idx_skill_promotion_source ON aidp_skill (promotion_source_id);

ALTER TABLE aidp_rule
    ADD COLUMN IF NOT EXISTS review_status VARCHAR(20) DEFAULT 'approved',
    ADD COLUMN IF NOT EXISTS review_report TEXT,
    ADD COLUMN IF NOT EXISTS review_log TEXT DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS promotion_status VARCHAR(20) DEFAULT 'none',
    ADD COLUMN IF NOT EXISTS promotion_report TEXT,
    ADD COLUMN IF NOT EXISTS promotion_source_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS promotion_source_scope VARCHAR(20),
    ADD COLUMN IF NOT EXISTS promotion_promoted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_rule_review_status ON aidp_rule (review_status);
CREATE INDEX IF NOT EXISTS idx_rule_promotion_status ON aidp_rule (promotion_status);
CREATE INDEX IF NOT EXISTS idx_rule_promotion_source ON aidp_rule (promotion_source_id);

ALTER TABLE aidp_knowledge_document
    ADD COLUMN IF NOT EXISTS promotion_status VARCHAR(20) DEFAULT 'none',
    ADD COLUMN IF NOT EXISTS promotion_report TEXT,
    ADD COLUMN IF NOT EXISTS promotion_source_id VARCHAR(36),
    ADD COLUMN IF NOT EXISTS promotion_source_scope VARCHAR(20),
    ADD COLUMN IF NOT EXISTS promotion_promoted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_kdoc_promotion_status ON aidp_knowledge_document (promotion_status);
CREATE INDEX IF NOT EXISTS idx_kdoc_promotion_source ON aidp_knowledge_document (promotion_source_id);
