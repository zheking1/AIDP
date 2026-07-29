"""Add new fields to KnowledgeBase, KnowledgeDocument and create ProjectKnowledgeBinding table"""
from app.db.database import engine
from sqlalchemy import text
import asyncio

SQL_NO_UNIQUE = """
ALTER TABLE aidp_knowledge_bases ADD COLUMN slug VARCHAR(128);
CREATE INDEX IF NOT EXISTS idx_kb_slug ON aidp_knowledge_bases (slug);
ALTER TABLE aidp_knowledge_bases ADD COLUMN kb_level VARCHAR(32) NOT NULL DEFAULT 'project';
ALTER TABLE aidp_knowledge_bases ADD COLUMN parent_id VARCHAR(36) REFERENCES aidp_knowledge_bases(id);
ALTER TABLE aidp_knowledge_bases ADD COLUMN domains TEXT NOT NULL DEFAULT '[]';
ALTER TABLE aidp_knowledge_bases ADD COLUMN keywords TEXT NOT NULL DEFAULT '[]';
ALTER TABLE aidp_knowledge_bases ADD COLUMN tech_stack TEXT NOT NULL DEFAULT '[]';
ALTER TABLE aidp_knowledge_bases ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'private';
CREATE INDEX IF NOT EXISTS idx_kb_level ON aidp_knowledge_bases (kb_level);
CREATE INDEX IF NOT EXISTS idx_kb_parent ON aidp_knowledge_bases (parent_id);

ALTER TABLE aidp_knowledge_documents ADD COLUMN tags TEXT NOT NULL DEFAULT '[]';
ALTER TABLE aidp_knowledge_documents ADD COLUMN checksum VARCHAR(128);
ALTER TABLE aidp_knowledge_documents ADD COLUMN version VARCHAR(128) NOT NULL DEFAULT 'v1';
ALTER TABLE aidp_knowledge_documents ADD COLUMN index_status VARCHAR(20) NOT NULL DEFAULT 'pending';
ALTER TABLE aidp_knowledge_documents ADD COLUMN summary TEXT;
ALTER TABLE aidp_knowledge_documents ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'private';
ALTER TABLE aidp_knowledge_documents ADD COLUMN owner_type VARCHAR(32) NOT NULL DEFAULT 'personal';
ALTER TABLE aidp_knowledge_documents ADD COLUMN created_by VARCHAR(100);
ALTER TABLE aidp_knowledge_documents ADD COLUMN updated_by VARCHAR(100);
CREATE INDEX IF NOT EXISTS idx_doc_index_status ON aidp_knowledge_documents (index_status);

CREATE TABLE IF NOT EXISTS aidp_project_knowledge_bindings (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(128) NOT NULL,
    knowledge_base_id VARCHAR(36) NOT NULL REFERENCES aidp_knowledge_bases(id),
    binding_type VARCHAR(32) NOT NULL DEFAULT 'auto_matched',
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_binding_project ON aidp_project_knowledge_bindings (project_id);
CREATE INDEX IF NOT EXISTS idx_binding_kb ON aidp_project_knowledge_bindings (knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_binding_project_kb ON aidp_project_knowledge_bindings (project_id, knowledge_base_id);
"""

async def migrate():
    async with engine.begin() as conn:
        for stmt in SQL_NO_UNIQUE.strip().split(";"):
            s = stmt.strip()
            if s:
                try:
                    await conn.execute(text(s))
                    print(f"OK: {s[:80]}...")
                except Exception as e:
                    if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                        print(f"SKIP: {s[:60]}...")
                    else:
                        print(f"ERR: {s[:80]}... -> {str(e)[:100]}")

if __name__ == "__main__":
    asyncio.run(migrate())