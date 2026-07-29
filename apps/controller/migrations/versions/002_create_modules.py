"""
数据库迁移脚本

创建所有模块的数据库表 (Knowledge, Memory, Skills, Assets, Sandbox, Quality)

Revision ID: 002_create_modules
Revises: 001_create_projects
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa

revision = '002_create_modules'
down_revision = '001_create_projects'
branch_labels = None
depends_on = None


def upgrade():
    # ==================== Knowledge Module ====================
    op.create_table(
        'aidp_knowledge_bases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('aidp_projects.id'), nullable=True, index=True),
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('chunking_strategy', sa.String(50), default='fixed'),
        sa.Column('chunk_size', sa.Integer(), default=500),
        sa.Column('chunk_overlap', sa.Integer(), default=50),
        sa.Column('embedding_model', sa.String(128), default='text-embedding-3-small'),
        sa.Column('document_count', sa.Integer(), default=0),
        sa.Column('total_chunks', sa.Integer(), default=0),
        sa.Column('extra_data', sa.Text(), default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'aidp_knowledge_documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('base_id', sa.String(36), sa.ForeignKey('aidp_knowledge_bases.id'), nullable=False, index=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('aidp_projects.id'), nullable=True, index=True),
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('source_type', sa.String(50), default='manual'),
        sa.Column('source_uri', sa.String(1000), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('file_size', sa.Integer(), default=0),
        sa.Column('chunk_count', sa.Integer(), default=0),
        sa.Column('processing_status', sa.String(20), default='pending', index=True),
        sa.Column('extra_data', sa.Text(), default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'aidp_document_chunks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('aidp_knowledge_documents.id'), nullable=False, index=True),
        sa.Column('base_id', sa.String(36), sa.ForeignKey('aidp_knowledge_bases.id'), nullable=False, index=True),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.Text(), nullable=True),
        sa.Column('token_count', sa.Integer(), default=0),
        sa.Column('extra_data', sa.Text(), default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'aidp_knowledge_search_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('base_id', sa.String(36), nullable=True, index=True),
        sa.Column('project_id', sa.Integer(), nullable=True, index=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('results_count', sa.Integer(), default=0),
        sa.Column('top_score', sa.Float(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ==================== Memory Module ====================
    op.create_table(
        'aidp_memory_entries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('aidp_projects.id'), nullable=True, index=True),
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('category', sa.String(50), nullable=False, index=True),
        sa.Column('memory_tier', sa.String(20), default='semantic', index=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.Text(), nullable=True),
        sa.Column('embedding_model', sa.String(128), default='text-embedding-3-small'),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('aidp_memory_entries.id'), nullable=True, index=True),
        sa.Column('confidence_score', sa.Float(), default=1.0),
        sa.Column('ai_suggested', sa.Boolean(), default=False, index=True),
        sa.Column('ai_review_status', sa.String(20), default='approved'),
        sa.Column('ai_review_comment', sa.Text(), nullable=True),
        sa.Column('merged_from', sa.Text(), nullable=True),
        sa.Column('access_count', sa.Integer(), default=0),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_type', sa.String(50), default='manual'),
        sa.Column('source_uri', sa.String(500), nullable=True),
        sa.Column('extra_data', sa.Text(), default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'aidp_memory_relations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('source_id', sa.String(36), sa.ForeignKey('aidp_memory_entries.id'), nullable=False, index=True),
        sa.Column('target_id', sa.String(36), sa.ForeignKey('aidp_memory_entries.id'), nullable=False, index=True),
        sa.Column('relation_type', sa.String(50), nullable=False, index=True),
        sa.Column('strength', sa.Float(), default=1.0),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.Text(), default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'aidp_memory_access_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('memory_id', sa.String(36), sa.ForeignKey('aidp_memory_entries.id'), nullable=False, index=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('aidp_projects.id'), nullable=True, index=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # ==================== Skills Module ====================
    op.create_table(
        'aidp_skill_groups',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scope', sa.String(20), nullable=False, index=True),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('aidp_skill_groups.id'), nullable=True, index=True),
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('aidp_projects.id'), nullable=True, index=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'aidp_skills',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scope', sa.String(20), nullable=False, index=True),
        sa.Column('instruction', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), default='[]'),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('dependencies', sa.Text(), default='[]'),
        sa.Column('exec_config', sa.Text(), default='{}'),
        sa.Column('embedding', sa.Text(), nullable=True),
        sa.Column('embedding_model', sa.String(128), default='text-embedding-3-small'),
        sa.Column('review_status', sa.String(20), default='approved', index=True),
        sa.Column('allowed_roles', sa.Text(), default='[]'),
        sa.Column('sensitive', sa.Boolean(), default=False),
        sa.Column('weight_config', sa.Text(), default='{}'),
        sa.Column('examples', sa.Text(), default='[]'),
        sa.Column('source_url', sa.String(500), nullable=True),
        sa.Column('source_type', sa.String(50), default='manual'),
        sa.Column('group_id', sa.String(36), sa.ForeignKey('aidp_skill_groups.id'), nullable=True, index=True),
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('aidp_projects.id'), nullable=True, index=True),
        sa.Column('extra_data', sa.Text(), default='{}'),
        sa.Column('access_count', sa.Integer(), default=0),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'aidp_skill_files',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('skill_id', sa.String(36), sa.ForeignKey('aidp_skills.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('path', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('is_entry', sa.Boolean(), default=False),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'aidp_skill_evolutions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('skill_id', sa.String(36), sa.ForeignKey('aidp_skills.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('old_version', sa.Integer(), nullable=True),
        sa.Column('old_content', sa.Text(), nullable=True),
        sa.Column('new_content', sa.Text(), nullable=False),
        sa.Column('diff_summary', sa.Text(), nullable=True),
        sa.Column('trigger_reason', sa.String(100), default='manual'),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('rollback_to', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ==================== Assets Module ====================
    op.create_table(
        'aidp_assets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('aidp_projects.id'), nullable=True, index=True),
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('title', sa.String(200), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('asset_type', sa.String(50), nullable=False, index=True),
        sa.Column('language', sa.String(50), nullable=True, index=True),
        sa.Column('format', sa.String(50), nullable=True),
        sa.Column('visibility', sa.String(20), default='project', index=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('variables', sa.Text(), default='{}'),
        sa.Column('extra_data', sa.Text(), default='{}'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('access_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'aidp_asset_tags',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('asset_id', sa.String(36), sa.ForeignKey('aidp_assets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('tag', sa.String(100), nullable=False, index=True),
    )

    # ==================== Sandbox Module ====================
    op.create_table(
        'aidp_executions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.Integer(), nullable=True, index=True),
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('language', sa.String(20), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('stdin', sa.Text(), nullable=True),
        sa.Column('stdout', sa.Text(), nullable=True),
        sa.Column('stderr', sa.Text(), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('timed_out', sa.Boolean(), default=False),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), default='pending', index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # ==================== Quality Module ====================
    op.create_table(
        'aidp_check_results',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.Integer(), nullable=True, index=True),
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('filename', sa.String(500), nullable=True),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('check_type', sa.String(20), nullable=False, index=True),
        sa.Column('issues', sa.Text(), default='[]'),
        sa.Column('issue_count', sa.Integer(), default=0),
        sa.Column('code_snippet', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )


def downgrade():
    tables = [
        'aidp_check_results',
        'aidp_executions',
        'aidp_asset_tags',
        'aidp_assets',
        'aidp_skill_evolutions',
        'aidp_skill_files',
        'aidp_skills',
        'aidp_skill_groups',
        'aidp_memory_access_logs',
        'aidp_memory_relations',
        'aidp_memory_entries',
        'aidp_knowledge_search_logs',
        'aidp_document_chunks',
        'aidp_knowledge_documents',
        'aidp_knowledge_bases',
    ]
    for table in tables:
        op.drop_table(table)
