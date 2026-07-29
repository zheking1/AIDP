"""
数据库迁移脚本

创建项目相关的数据库表

Revision ID: 001_create_projects
Revises: 
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_create_projects'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库 - 创建项目相关表"""
    
    # 1. 创建项目表
    op.create_table(
        'aidp_projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.String(length=128), nullable=False),
        sa.Column('visibility', sa.Enum('private', 'internal', 'public', name='projectvisibility'), 
                  nullable=False, server_default='private'),
        sa.Column('tech_stack', sa.String(length=1024), server_default='[]'),
        sa.Column('cover_url', sa.String(length=512), nullable=True),
        sa.Column('settings', sa.Text(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_deleted', sa.Integer(), server_default='0'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('idx_projects_owner', 'aidp_projects', ['owner_id'])
    op.create_index('idx_projects_visibility', 'aidp_projects', ['visibility'])
    op.create_index('idx_projects_deleted', 'aidp_projects', ['is_deleted'])
    
    # 2. 创建项目成员表
    op.create_table(
        'aidp_project_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('role', sa.Enum('admin', 'editor', 'viewer', name='projectrole'),
                  nullable=False, server_default='editor'),
        sa.Column('invited_by', sa.String(length=128), nullable=True),
        sa.Column('joined_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'user_id', name='uq_project_member'),
        sa.ForeignKeyConstraint(['project_id'], ['aidp_projects.id'], ondelete='CASCADE')
    )
    
    # 创建索引
    op.create_index('idx_project_members_project', 'aidp_project_members', ['project_id'])
    op.create_index('idx_project_members_user', 'aidp_project_members', ['user_id'])
    op.create_index('idx_project_members_role', 'aidp_project_members', ['role'])
    
    # 3. 创建项目设置表
    op.create_table(
        'aidp_project_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_by', sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'category', 'key', name='uq_project_setting'),
        sa.ForeignKeyConstraint(['project_id'], ['aidp_projects.id'], ondelete='CASCADE')
    )
    
    op.create_index('idx_project_settings_project', 'aidp_project_settings', ['project_id'])
    op.create_index('idx_project_settings_category', 'aidp_project_settings', ['category'])
    
    # 4. 创建项目访问日志表
    op.create_table(
        'aidp_project_access_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=True),
        sa.Column('resource_id', sa.String(length=128), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['aidp_projects.id'])
    )
    
    op.create_index('idx_access_logs_project', 'aidp_project_access_logs', ['project_id'])
    op.create_index('idx_access_logs_user', 'aidp_project_access_logs', ['user_id'])
    op.create_index('idx_access_logs_created', 'aidp_project_access_logs', ['created_at'])
    
    # 5. 修改现有表 - 添加 project_id 字段
    # 注意：使用 nullable=True 允许空值，避免影响现有数据
    
    # 检查表是否存在（避免报错）
    try:
        op.add_column('kt_document', 
                      sa.Column('project_id', sa.Integer(), nullable=True))
        op.add_column('kt_document',
                      sa.Column('created_by', sa.String(128), nullable=True))
        op.add_column('kt_document',
                      sa.Column('updated_by', sa.String(128), nullable=True))
        op.create_index('idx_kt_document_project', 'kt_document', ['project_id'])
    except Exception as e:
        print(f"Note: kt_document table modification skipped: {e}")
    
    try:
        op.add_column('memories',
                      sa.Column('project_id', sa.Integer(), nullable=True))
        op.add_column('memories',
                      sa.Column('created_by', sa.String(128), nullable=True))
        op.create_index('idx_memories_project', 'memories', ['project_id'])
    except Exception as e:
        print(f"Note: memories table modification skipped: {e}")
    
    print("Migration 001_create_projects completed successfully!")


def downgrade():
    """降级数据库 - 删除项目相关表"""
    
    # 删除索引和字段（现有表）
    try:
        op.drop_index('idx_kt_document_project', table_name='kt_document')
        op.drop_column('kt_document', 'project_id')
        op.drop_column('kt_document', 'created_by')
        op.drop_column('kt_document', 'updated_by')
    except Exception as e:
        print(f"Note: kt_document cleanup skipped: {e}")
    
    try:
        op.drop_index('idx_memories_project', table_name='memories')
        op.drop_column('memories', 'project_id')
        op.drop_column('memories', 'created_by')
    except Exception as e:
        print(f"Note: memories cleanup skipped: {e}")
    
    # 删除项目相关表（反向顺序）
    op.drop_index('idx_access_logs_created', table_name='aidp_project_access_logs')
    op.drop_index('idx_access_logs_user', table_name='aidp_project_access_logs')
    op.drop_index('idx_access_logs_project', table_name='aidp_project_access_logs')
    op.drop_table('aidp_project_access_logs')
    
    op.drop_index('idx_project_settings_category', table_name='aidp_project_settings')
    op.drop_index('idx_project_settings_project', table_name='aidp_project_settings')
    op.drop_table('aidp_project_settings')
    
    op.drop_index('idx_project_members_role', table_name='aidp_project_members')
    op.drop_index('idx_project_members_user', table_name='aidp_project_members')
    op.drop_index('idx_project_members_project', table_name='aidp_project_members')
    op.drop_table('aidp_project_members')
    
    op.drop_index('idx_projects_deleted', table_name='aidp_projects')
    op.drop_index('idx_projects_visibility', table_name='aidp_projects')
    op.drop_index('idx_projects_owner', table_name='aidp_projects')
    op.drop_table('aidp_projects')
    
    # 删除枚举类型（PostgreSQL）
    op.execute("DROP TYPE IF EXISTS projectvisibility")
    op.execute("DROP TYPE IF EXISTS projectrole")
    
    print("Migration 001_create_projects downgraded successfully!")
