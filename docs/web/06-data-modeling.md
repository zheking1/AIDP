# AIDP Data Model — 数据模型设计

## 1. 数据库配置

AIDP 使用 SQLAlchemy 异步引擎连接数据库，支持 PostgreSQL 和 SQLite 两种后端：

```python
# database.py
engine = create_async_engine(
    settings.DATABASE_URL,  # 从配置读取，如 postgresql+asyncpg://user:pass@host/db
    echo=settings.DATABASE_ECHO,
    pool_size=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

`Base = DeclarativeBase()` 是所有模型的基类。`get_db()` 是 FastAPI 的依赖注入函数，每个请求获取一个数据库会话，请求结束时自动提交或回滚。

数据库 URL 由 `settings.DATABASE_URL` 控制。使用 `postgresql+asyncpg://...` 连接 PostgreSQL，使用 `sqlite+aiosqlite:///./test.db` 连接 SQLite。这种兼容性设计方便本地开发和 CI 测试。

## 2. 模型注册

所有模型通过 `Base` 继承自动注册到 SQLAlchemy 元数据中。在 `main.py` 启动时，通过导入各个模块的 `models.py` 确保模型被加载：

```python
# main.py
from app.modules.knowledge.models import KnowledgeBase, KnowledgeDocument
from app.modules.memory.models import MemoryEntry, MemoryRelation
from app.modules.skills.models import Skill, SkillGroup
from app.modules.rules.models import Rule, RuleGroup
from app.modules.agents.models import Agent, agent_skills, agent_rules, agent_knowledge
from app.modules.workflows.models import Workflow, WorkflowStep
from app.modules.sandbox.models import Execution
from app.modules.quality.models import CheckResult
from app.modules.assets.models import Asset
```

启动时调用 `Base.metadata.create_all(engine)` 创建所有表。

## 3. 表命名规范

| 类型 | 模式 | 示例 |
|------|------|------|
| 系统核心表 | 简洁名称 | `users`, `user_sessions`, `audit_logs`, `permissions` |
| 模块业务表 | `aidp_{module}_{entity}` | `aidp_knowledge_bases`, `aidp_memory_entries`, `aidp_skills` |
| 关联表 | `aidp_{module1}_{module2}` | `aidp_agent_skills`, `aidp_agent_rules` |
| 项目表 | `aidp_{entity}` | `aidp_projects`, `aidp_project_members` |

## 4. 核心模型

### User（auth_models.py:54）

```python
class User(Base):
    __tablename__ = "users"
    id          = Column(UUID, primary_key=True, default=uuid.uuid4)
    username    = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email       = Column(String(255), unique=True, nullable=True, index=True)
    nickname    = Column(String(128), nullable=True)
    avatar_url  = Column(Text, nullable=True)
    role        = Column(String(32), default="user")  # super_admin/admin/developer/user/readonly
    status      = Column(String(32), default="active")  # active/inactive/suspended/pending
    is_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### AuditLog（auth_models.py:275）

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id          = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID, ForeignKey("users.id"), nullable=True, index=True)
    action      = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(64), nullable=True, index=True)
    resource_id = Column(String(64), nullable=True, index=True)
    resource_name = Column(String(255), nullable=True)
    old_values  = Column(JSON, nullable=True)
    new_values  = Column(JSON, nullable=True)
    ip_address  = Column(String(45), nullable=True)
    user_agent  = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, index=True)
```

### SystemSetting（auth_models.py:321）

```python
class SystemSetting(Base):
    __tablename__ = "system_settings"
    id          = Column(UUID, primary_key=True, default=uuid.uuid4)
    key         = Column(String(128), unique=True, nullable=False, index=True)
    value       = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False)
    updated_by  = Column(UUID, ForeignKey("users.id"), nullable=True)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## 5. 模块模型（9 个模块）

### Knowledge 模块 — 知识库管理

| 模型 | 表名 | 关键字段 |
|------|------|----------|
| KnowledgeBase | aidp_knowledge_bases | `id(String36)`, `project_id`, `name`, `description`, `category`, `chunking_strategy`, `chunk_size`, `chunk_overlap`, `embedding_model`, `document_count`, `total_chunks` |
| KnowledgeDocument | aidp_knowledge_documents | `id`, `base_id(FK)`, `title`, `source_type`, `source_uri`, `content(Text)`, `mime_type`, `file_size`, `chunk_count`, `processing_status` |
| DocumentChunk | aidp_document_chunks | `id`, `document_id(FK)`, `base_id(FK)`, `chunk_index`, `content`, `embedding(Text)`, `token_count` |
| KnowledgeSearchLog | aidp_knowledge_search_logs | `id`, `base_id`, `query`, `results_count`, `top_score`, `duration_ms` |
| DocumentTemplate | aidp_document_templates | `id`, `name`, `category`, `content`, `variables(JSON)`, `scope(global/personal/project)` |

### Memory 模块 — 记忆管理

| 模型 | 表名 | 关键字段 |
|------|------|----------|
| MemoryEntry | aidp_memory_entries | `id`, `project_id`, `category`, `memory_tier(semantic/episodic)`, `title`, `content`, `embedding`, `parent_id(FK自引用)`, `confidence_score`, `ai_suggested`, `ai_review_status`, `access_count` |
| MemoryRelation | aidp_memory_relations | `id`, `source_id(FK)`, `target_id(FK)`, `relation_type`, `strength(Float)` |
| MemoryAccessLog | aidp_memory_access_logs | `id`, `memory_id(FK)`, `action`, `query`, `user_id` |

### Skills 模块 — 技能管理（三层架构：global/personal/project）

| 模型 | 表名 | 关键字段 |
|------|------|----------|
| SkillGroup | aidp_skill_groups | `id`, `name`, `scope`, `parent_id(FK自引用)`, `user_id`, `project_id`, `sort_order` |
| Skill | aidp_skills | `id`, `name`, `description`, `scope`, `instruction`, `content`, `tags(JSON)`, `version`, `dependencies(JSON)`, `exec_config(JSON)`, `review_status`, `allowed_roles(JSON)`, `group_id(FK)`, `access_count` |
| SkillFile | aidp_skill_files | `id`, `skill_id(FK)`, `path`, `content`, `language`, `is_entry`, `sort_order` |
| SkillEvolution | aidp_skill_evolutions | `id`, `skill_id(FK)`, `old_version`, `old_content`, `new_content`, `diff_summary`, `trigger_reason`, `status`, `rollback_to` |

### Rules 模块 — 规则管理

| 模型 | 表名 | 关键字段 |
|------|------|----------|
| RuleGroup | aidp_rule_groups | `id`, `name`, `description`, `scope`, `parent_id(FK自引用)`, `sort_order` |
| Rule | aidp_rules | `id`, `name`, `content`, `category(security/code_style/architecture/testing)`, `severity(critical/high/medium/low)`, `scope`, `pattern`, `auto_fix`, `allowed_roles`, `tags`, `group_id(FK)`, `is_active` |

### Agents 模块 — Agent 管理

| 模型 | 表名 | 关键字段 |
|------|------|----------|
| Agent | aidp_agents | `id`, `name`, `role`, `instructions`, `scope`, `parent_agent_id(FK自引用)`, `config(JSON)`, `sort_order`, `is_active`, `is_template` |
| agent_skills | aidp_agent_skills | `agent_id(FK)`, `skill_id(FK)` — 多对多关联表 |
| agent_rules | aidp_agent_rules | `agent_id(FK)`, `rule_id(FK)` — 多对多关联表 |
| agent_knowledge | aidp_agent_knowledge | `agent_id(FK)`, `knowledge_base_id(FK)` — 多对多关联表 |

Agent 的设计理念是 "Agent = Instructions + Skills + Rules + Knowledge"，即 Agent 由指令集、技能集合、规则集合和知识库组合而成。

### Workflows 模块 — 流程引擎

| 模型 | 表名 | 关键字段 |
|------|------|----------|
| Workflow | aidp_workflows | `id`, `name`, `description`, `category`, `trigger(manual/webhook/schedule/event)`, `trigger_config`, `variables`, `is_active`, `is_template`, `version` |
| WorkflowStep | aidp_workflow_steps | `id`, `workflow_id(FK)`, `name`, `order`, `agent_id(FK)`, `skill_ids(JSON)`, `rule_ids(JSON)`, `conditions`, `input_mapping`, `output_mapping`, `timeout`, `on_success`, `on_fail` |
| WorkflowExecution | aidp_workflow_executions | `id`, `workflow_id(FK)`, `status(running/completed/failed/cancelled)`, `trigger_type`, `current_step`, `variables` |
| WorkflowExecutionStep | aidp_workflow_execution_steps | `id`, `execution_id(FK)`, `step_id(FK)`, `step_name`, `step_order`, `status`, `started_at`, `duration_ms`, `input_data`, `output_data`, `error`, `retry_count` |

### Sandbox 模块 — 代码沙箱

| 模型 | 表名 | 关键字段 |
|------|------|----------|
| Execution | aidp_executions | `id`, `project_id`, `user_id`, `language(python/bash/sh)`, `code`, `stdin`, `stdout`, `stderr`, `exit_code`, `timed_out`, `duration_ms`, `status` |

### Quality 模块 — 质量检查

| 模型 | 表名 | 关键字段 |
|------|------|----------|
| CheckResult | aidp_check_results | `id`, `project_id`, `user_id`, `filename`, `language`, `check_type`, `issues(JSON)`, `issue_count`, `code_snippet`, `score(Float)` |

### Assets 模块 — 代码资产

| 模型 | 表名 | 关键字段 |
|------|------|----------|
| Asset | aidp_assets | `id`, `project_id`, `user_id`, `title`, `description`, `asset_type(snippet/script/config)`, `language`, `format`, `visibility`, `content`, `variables(JSON)`, `access_count` |
| AssetTag | aidp_asset_tags | `id`, `asset_id(FK)`, `tag` |

## 6. 关系图

```
Agent ──── agent_skills ──── Skill
Agent ──── agent_rules ──── Rule
Agent ──── agent_knowledge ──── KnowledgeBase
Agent ──── parent ──── Agent (self-referential)

Workflow ──── 1:N ──── WorkflowStep
WorkflowExecution ──── 1:N ──── WorkflowExecutionStep

Project ──── 1:N ──── ProjectMember
Project ──── 1:1 ──── ProjectSettings
Project ──── 1:N ──── ProjectAccessLog

User ──── 1:N ──── UserSession
User ──── 1:N ──── ApiKey
User ──── 1:N ──── AuditLog

MemoryEntry ──── self-ref(parent_id) ──── MemoryEntry
MemoryEntry ──── 1:N ──── MemoryRelation(source/target)
MemoryEntry ──── 1:N ──── MemoryAccessLog

SkillGroup ──── self-ref(parent_id) ──── SkillGroup
SkillGroup ──── 1:N ──── Skill
Skill ──── 1:N ──── SkillFile
Skill ──── 1:N ──── SkillEvolution

KnowledgeBase ──── 1:N ──── KnowledgeDocument
KnowledgeDocument ──── 1:N ──── DocumentChunk

Asset ──── 1:N ──── AssetTag
```

## 7. 索引策略

所有模型遵循以下索引策略：

- **主键索引**：每个模型的 `id` 字段自动为主键索引
- **外键索引**：所有 `ForeignKey` 字段显式设置 `index=True`，加速 JOIN 查询
- **业务查询索引**：频繁查询的字段加索引：
  - `user_id`, `project_id`, `scope` — 多租户隔离查询
  - `status`, `is_active`, `is_template` — 状态过滤
  - `category`, `check_type`, `trigger` — 分类筛选
  - `created_at` — 排序和分页
- **唯一索引**：`username`, `email`, `session_token`, `key_hash`, `code`(permissions)
- **复合索引**：审计日志表的 `(user_id, action)`、`(resource_type, resource_id)`

## 8. 初始化数据

`init_database()` 函数（`init_db.py:19-120`）在首次启动时插入种子数据：

1. **默认权限**：10 个基础权限（tool:read/write/execute, user:read/write, model:read/write, settings:read/write, admin:full）
2. **角色-权限分配**：5 个角色的默认权限集合
3. **默认管理员**：用户名 `admin`，密码 `admin123`，角色 `super_admin`
4. **默认系统设置**：6 个系统配置项（站点名称、描述、注册开关、Session 超时、登录次数限制、锁定时间）

```python
async def init_database():
    # 创建默认权限
    default_permissions = [
        ("tool:read", "View Tools", ...),
        ("tool:write", "Manage Tools", ...),
        # ... 10 个权限
    ]
    # 分配角色权限
    role_perms = {
        "super_admin": ["admin:full"],
        "admin": ["tool:read", "tool:write", ...],
        "developer": ["tool:read", "tool:write", "tool:execute", ...],
        "user": ["tool:read", "tool:execute", ...],
        "readonly": ["tool:read", "model:read"],
    }
    # 创建 admin 用户
    password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt())
    # 创建系统设置
```

## 9. 种子数据

系统配置了多套模板作为种子数据：

**Agent 模板（5 个）**：通用助手、代码审查员、架构师、测试工程师、运维工程师。每个模板预设了角色定义、指令集和关联的技能/规则。

**Workflow 模板（2 个）**：开发流程（代码编写→审查→测试→部署）、文档生成流程。

**Document 模板（3 个）**：PRD 模板、架构设计模板、技术方案模板，预设了文档结构和变量占位符。

这些模板通过 `seed_templates()` 函数在初始化时插入 `aidp_document_templates` 表，用户可以直接基于模板创建内容。