# SkillRouter — 开发交接文档

> 供 AI 工具或新开发者接手项目。包含架构、功能、部署、已知坑、当前状态。

---

## 一、项目简介

SkillRouter 是 MCP 服务，解决 AI Agent 上下文窗口膨胀问题。

**核心逻辑**：Agent 发来任务 → SkillRouter 从技能库匹配 2-6 个相关技能 → 返回给 Agent 注入上下文。避免 LLM 看到全部工具导致幻觉。

**技术栈**：Python 3.13 + FastAPI + FastMCP 3.4.2 + PostgreSQL (pgvector) + Redis + Jinja2/Alpine.js/Tailwind CSS

**端口**：8788

---

## 二、目录结构

```
SkillRouter/
├── app/
│   ├── main.py                    # FastAPI 入口 + MCP 挂载
│   ├── config.py                  # Pydantic Settings（从 .env 读取）
│   ├── i18n/
│   │   ├── __init__.py            # get_translator() 工厂
│   │   └── zh.json                # 中文翻译（270+ key）
│   ├── db/
│   │   ├── database.py            # SQLAlchemy async engine + session
│   │   ├── models.py              # 所有 ORM 模型
│   │   └── init_db.py             # 建表 + 迁移（只增不删）
│   ├── mcp/
│   │   └── tools.py               # 45+ 个 MCP 工具
│   ├── api/
│   │   └── routes.py              # REST API 路由
│   ├── services/
│   │   ├── resolve_service.py     # 核心路由引擎
│   │   ├── vector_service.py      # Embedding + 向量搜索 + 重排
│   │   ├── cache_service.py       # Redis 缓存（hash + session）
│   │   ├── review_service.py      # 技能审核
│   │   ├── validation_service.py  # 参数校验 + 敏感词检测
│   │   ├── import_service.py      # GitHub/ClawHub 技能导入
│   │   ├── rate_limiter.py        # 限流（Redis QPS + daily）
│   │   ├── skill_service.py       # 技能 CRUD
│   │   ├── rule_service.py        # 规则 CRUD
│   │   ├── evolution_service.py   # 版本演化
│   │   ├── model_service.py       # LLM 模型管理
│   │   ├── ranker_service.py     # LLM 重排序（独立服务）
│   │   └── classification_service.py  # 自动分类服务
│   └── web/
│       ├── auth.py                # 登录/注册/登出
│       ├── routes.py              # Web UI 路由
│       ├── i18n_utils.py          # i18n 工具函数
│       └── templates/             # Jinja2 模板（25+ 页面）
├── cli/
│   └── srcli.py                   # CLI 工具（522 行）
├── docs/
│   ├── dev-plan.md                # 开发计划
│   ├── DEV_PLAN.md                # 架构设计文档
│   └── HANDOFF.md                 # 本文档
├── data/                          # 运行时数据（gitignore）
│   └── system_settings.json       # 系统设置
├── .env.example                   # 环境变量模板
├── docker-compose.yml             # Docker 编排
├── Dockerfile                     # 镜像构建
└── requirements.txt               # Python 依赖
```

---

## 三、架构

```
┌─────────────────┐    MCP (Streamable-HTTP)    ┌──────────────────────┐
│   AI Agent      │ ──────────────────────────→  │    SkillRouter       │
│  (Claude等)     │                              │  FastAPI + FastMCP   │
│                 │ ←──────────────────────────  │                      │
│                 │   2-6 matched skills         │  ┌────────────────┐  │
└─────────────────┘                              │  │ PostgreSQL     │  │
                                                 │  │ (pgvector)     │  │
                                                 │  └────────────────┘  │
┌─────────────────┐    REST API                  │  ┌────────────────┐  │
│   Web UI        │ ──────────────────────────→  │  │ Redis          │  │
│  (Jinja2等)     │                              │  │ (缓存+限流)    │  │
│                 │ ←──────────────────────────  │  └────────────────┘  │
└─────────────────┘                              │  ┌────────────────┐  │
                                                 │  │ LLM / Embedding│  │
┌─────────────────┐    REST API                  │  │ (外部服务)      │  │
│   CLI (srcli)   │ ──────────────────────────→  │  └────────────────┘  │
└─────────────────┘                              └──────────────────────┘
```

### MCP 传输层挂载

```python
# app/main.py
_mcp = FastMCP("SkillRouter")
_mcp_app = _mcp.http_app(path="/", transport="streamable-http")

@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    async with app_lifespan(app):
        async with _mcp_app.lifespan(app):
            yield

app = FastAPI(lifespan=combined_lifespan)
app.mount("/mcp", _mcp_app)
```

**MCP 端点**：`http://<host>:8788/mcp/`

---

## 四、数据库 Schema

### 4.1 用户与权限

```sql
users
├── id: UUID PK
├── username: VARCHAR(100) UNIQUE NOT NULL
├── password: VARCHAR(255) NOT NULL (bcrypt)
├── nickname: VARCHAR(100) DEFAULT ''
├── remark: TEXT DEFAULT ''
├── role: VARCHAR(20) DEFAULT 'admin'  -- 'admin' | 'user'
├── is_active: BOOLEAN DEFAULT TRUE
└── created_at: DATETIME

api_keys
├── id: UUID PK
├── user_id: UUID FK→users.id ON DELETE CASCADE
├── key_hash: VARCHAR(64) UNIQUE NOT NULL (SHA256)
├── label: VARCHAR(100)
├── last_used: DATETIME
├── is_active: BOOLEAN DEFAULT TRUE
└── created_at: DATETIME
```

### 4.2 项目

```sql
projects
├── id: UUID PK
├── user_id: UUID FK→users.id (nullable)
├── name: VARCHAR(255) NOT NULL
├── slug: VARCHAR(255) UNIQUE NOT NULL
├── title: VARCHAR(255) NOT NULL
├── status: VARCHAR(50) DEFAULT 'active'
├── description: TEXT
├── instruction: TEXT (项目级指令)
├── config: JSON DEFAULT {}
├── settings: JSONB DEFAULT {}
├── is_active: BOOLEAN DEFAULT TRUE
├── created_at: DATETIME
└── updated_at: DATETIME
```

### 4.3 技能

```sql
skills
├── id: UUID PK
├── name: VARCHAR(255) NOT NULL
├── description: TEXT
├── instruction: TEXT (技能级指令，匹配时返回)
├── content: TEXT NOT NULL
├── tags: VARCHAR[] DEFAULT '{}'
├── examples: TEXT[] DEFAULT '{}'  -- 使用示例，如 ["将Excel转换为CSV格式"]
├── user_id: UUID FK→users.id NOT NULL
├── version: INT DEFAULT 1
├── dependencies: UUID[] DEFAULT '{}'
├── exec_config: JSON (runtime/cmd_template/timeout_secs/entry/params)
├── embedding: Vector(384)
├── review_status: VARCHAR(20) DEFAULT 'pending'
├── review_report: TEXT
├── review_log: TEXT[] DEFAULT '{}'
├── allow_risk_patterns: TEXT[] DEFAULT '{}'
├── scope: VARCHAR(20) DEFAULT 'private'  -- 'public' | 'private'
├── allowed_roles: VARCHAR[] (nullable)
├── sensitive: BOOLEAN DEFAULT FALSE
├── weight_config: JSONB (nullable)
├── is_active: BOOLEAN DEFAULT TRUE
├── project_id: UUID FK→projects.id (nullable)
├── group_id: UUID FK→skill_groups.id (nullable)
├── source_url: VARCHAR(500) (nullable)
├── source_type: VARCHAR(20) (nullable)  -- 'github' | 'clawhub'
├── source_id: VARCHAR(255) (nullable)
├── created_at: DATETIME
└── updated_at: DATETIME

skill_permissions  (技能权限配置)
├── id: UUID PK
├── skill_id: UUID FK→skills.id ON DELETE CASCADE
├── allowed_roles: VARCHAR[] (nullable)  -- ['admin', 'user', ...]
├── denied_roles: VARCHAR[] (nullable)
└── created_at: DATETIME

skill_files
├── id: UUID PK
├── skill_id: UUID FK→skills.id ON DELETE CASCADE
├── path: VARCHAR(500) NOT NULL
├── content: TEXT NOT NULL
├── language: VARCHAR(20) DEFAULT 'text'
├── is_entry: BOOLEAN DEFAULT FALSE
├── sort_order: INT DEFAULT 0
└── created_at: DATETIME

skill_groups  (自引用树形)
├── id: UUID PK
├── name: VARCHAR(255) NOT NULL
├── parent_id: UUID FK→skill_groups.id (nullable)
├── user_id: UUID FK→users.id NOT NULL
├── sort_order: INT DEFAULT 0
├── created_at / updated_at: DATETIME
```

### 4.4 规则

```sql
rules
├── id: UUID PK
├── name: VARCHAR(255) NOT NULL
├── content: TEXT NOT NULL
├── tags: VARCHAR[] DEFAULT '{}'
├── priority: INT DEFAULT 0
├── user_id: UUID FK→users.id NOT NULL
├── embedding: Vector(384)
├── is_active: BOOLEAN DEFAULT TRUE
├── project_id: UUID FK→projects.id (nullable)
├── group_id: UUID FK→rule_groups.id (nullable)
├── allowed_roles: VARCHAR[] (nullable)
├── scope: VARCHAR(20) DEFAULT 'private'
├── created_at / updated_at: DATETIME

rule_groups  (结构同 skill_groups)
```

### 4.5 LLM 模型

```sql
llm_configs
├── id: UUID PK
├── name: VARCHAR(255) NOT NULL
├── provider: VARCHAR(50) DEFAULT 'openai'
├── model_name: VARCHAR(255) NOT NULL
├── api_key: TEXT
├── api_base: TEXT
├── role: VARCHAR(50) DEFAULT 'Intent Analyzer'
│   -- 'Intent Analyzer' | 'Embedding' | 'Review' | 'Ranker'
├── is_default: BOOLEAN DEFAULT FALSE
├── user_id: UUID FK→users.id NOT NULL
├── project_id: UUID FK→projects.id (nullable)
├── created_at / updated_at: DATETIME
```

### 4.6 其他表

```sql
evolutions          -- 技能版本演化记录 (skill_id, old_content, new_content, trigger_reason)
operation_logs      -- 操作日志 (user_id, action, target_type, target_id, detail)
operation_log_details
review_patterns     -- 审核规则模式
```

### 4.7 系统设置（文件存储）

```
/app/data/system_settings.json
├── allow_registration: bool  # 控制是否允许注册
```

---

## 五、核心流程

### 5.1 Resolve（技能匹配）

```
resolve_service.py: resolve_skills()
│
├── 1. 会话缓存检查
│   └── session_id + task embedding → cosine ≥ 0.7 → 直接返回缓存
│
├── 2. Embedding 向量粗筛
│   └── task → embedding → pgvector cosine_distance → Top N*3 候选
│
├── 3. 角色权限过滤
│   └── user.role + skill.allowed_roles → 过滤无权限技能
│
├── 4. 意图分析（LLM，可降级）
│   └── analyze_intent() → 主意图 + 次意图
│
├── 5. 标签加权
│   └── 关键词映射 (10组) → tag_score 加权 +0.08~0.15
│
├── 6. 小模型重排序（LLMConfig.role='Ranker'，可降级）
│   └── 0.4向量 + 0.2标签 + 0.1关键词 + 0.3重排
│   └── 四维度评分：直接相关性(40%)、指令匹配(30%)、标签匹配(20%)、示例匹配(10%)
│
├── 7. 业务规则加权
│   └── Rule.priority → skill.score 修正
│
├── 8. Top 2-6 收敛
│   └── clamp(2, top_k, 6)
│
├── 9. 写入会话缓存
│
├── 10. 并行检索优化
│   └── 技能和规则向量检索使用 asyncio.create_task() 并行执行
│
└── 11. 后置校验
    └── validate_resolve_result() → 参数/权限/敏感数据/危险操作检测
```

**降级链路**：LLM 超时 → embedding_only → tag_only → 全部跳过

### 5.2 MCP 认证

```python
# 每个 MCP 工具都执行：
api_key → SHA256 hash → 查 ApiKey 表 → 得到 User → user_id
# 无效 key → return fail("PERMISSION_DENIED", "invalid api_key")
```

### 5.3 Web 认证

```
Session 中间件（cookie-based）
├── 登录: POST /login → bcrypt 校验 → session["user_id"] = ...
├── 注册: POST /register → 创建用户 → 自动登录
├── 登出: GET /logout → 清除 session
└── 权限: admin 页面检查 session user.role == "admin"
```

---

## 六、MCP 工具完整列表（45+ 个）

### 核心路由
| 工具 | 参数 | 说明 |
|------|------|------|
| `resolve_task` | task, mode, hint_tags, top_k, no_cache, exclude_skill_ids, exclude_tags, role, session_id, api_key | 核心路由 |
| `skill_run` | task, mode, hint_tags, top_k, role, session_id, api_key | resolve + 返回完整技能+指令 |

### 技能管理
| 工具 | 参数 | 说明 |
|------|------|------|
| `skill_register` | name, content, tags, dependencies, description, group_name, auto_classify, api_key | 创建技能（自动分类） |
| `skill_update` | id, api_key, name, description, content, tags, review_status, review_report, is_active, dependencies | 更新技能 |
| `skill_delete` | id, api_key | 删除技能 |
| `skill_get` | id, api_key | 获取技能详情（含 files） |
| `skill_get_script` | id, api_key | 获取入口脚本内容 |
| `skill_list` | user_id, tags, status, query, limit, offset, api_key | 列表查询 |

### 规则管理
| 工具 | 参数 | 说明 |
|------|------|------|
| `rule_create` | name, content, tags, priority, group_name, auto_classify, api_key | 创建规则（自动分类） |
| `rule_update` | id, api_key, name, content, tags, priority, is_active | 更新规则 |
| `rule_delete` | id, api_key | 删除规则 |
| `rule_list` | user_id, tags, query, limit, offset, api_key | 列表查询 |

### 审核
| 工具 | 参数 | 说明 |
|------|------|------|
| `skill_review` | id, api_key | 提交审核 |
| `skill_approve` | id, api_key | 审批通过 |
| `skill_reject` | id, reason, api_key | 审批拒绝 |
| `skill_pre_review` | content, allow_risk_patterns, api_key | 预审核 |
| `skill_batch_review` | ids, action, reason, api_key | 批量审核 |

### 演化
| 工具 | 参数 | 说明 |
|------|------|------|
| `evolution_submit` | skill_id, content, trigger_reason, api_key | 提交演化 |
| `evolution_rollback` | evolution_id, trigger_reason, api_key | 回滚版本 |
| `evolution_list` | skill_id, limit, offset, api_key | 演化历史 |

### 批量操作
| 工具 | 参数 | 说明 |
|------|------|------|
| `skill_batch_ops` | ids, action, api_key | 批量激活/停用/删除 |

### 缓存
| 工具 | 参数 | 说明 |
|------|------|------|
| `cache_flush` | key_hash, api_key | 按 hash 清缓存 |
| `cache_flush_by_target` | resource_type, resource_id, api_key | 按资源清缓存 |

### 模型
| 工具 | 参数 | 说明 |
|------|------|------|
| `model_add` | name, provider, model_name, api_key, api_base, role, is_default, user_id, api_key | 添加模型 |
| `model_list` | role, mcp_api_key | 列表查询 |
| `embedding_model_detect` | api_key | 检测 embedding 维度 |

### 其他
| 工具 | 参数 | 说明 |
|------|------|------|
| `tag_global_manage` | action, tag, api_key | 标签管理 |
| `review_pattern_manage` | action, pattern_id, pattern, risk_level, action, api_key | 审核模式管理 |
| `stats_get` | metric, range_hours, api_key | 统计数据 |
| `operation_log_list` | user_id, action, target_type, limit, offset, api_key | 操作日志 |
| `validate_skill_params` | skill_id, params, api_key | 参数校验 |
| `resource_export` | resource_type, resource_id, format, mcp_api_key | 资源导出 |

---

## 七、REST API 路由

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/login` | 登录 |
| POST | `/register` | 注册（受 system_settings.allow_registration 控制） |
| GET | `/logout` | 登出 |

### 技能
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/skills` | 列表/创建 |
| GET/PUT/DELETE | `/skills/{id}` | 详情/更新/删除 |
| POST | `/skills/{id}/embed` | 生成 embedding |
| POST | `/skills/{id}/review` | 提交审核 |
| POST | `/skills/{id}/approve` | 审批通过 |
| POST | `/skills/{id}/reject` | 审批拒绝 |
| GET | `/skills/import` | 导入页面 |
| POST | `/api/skills/import/preview` | 预览导入内容 |
| POST | `/api/skills/import/search` | 搜索 GitHub 技能 |
| POST | `/api/skills/import` | 执行导入 |

### 技能分组
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/skill-groups` | 创建分组 |
| PUT | `/api/skill-groups/{id}` | 更新分组 |
| DELETE | `/api/skill-groups/{id}` | 删除分组（自动 ungroup 技能） |

### 规则
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/rules` | 列表/创建 |
| GET/PUT/DELETE | `/rules/{id}` | 详情/更新/删除 |
| POST | `/rules/{id}/embed` | 生成 embedding |

### 规则分组
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rule-groups` | 创建分组 |
| PUT | `/api/rule-groups/{id}` | 更新分组 |
| DELETE | `/api/rule-groups/{id}` | 删除分组 |

### 模型
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/models` | 列表/创建 |
| GET/PUT/DELETE | `/models/{id}` | 详情/更新/删除 |

### 项目
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/projects` | 列表/创建 |
| GET/PUT/DELETE | `/projects/{id}` | 详情/更新/删除 |
| POST | `/projects/{id}/skills/link` | 关联技能 |
| POST | `/projects/{id}/skills/unlink` | 解除关联 |
| POST | `/projects/{id}/rules/link` | 关联规则 |
| POST | `/projects/{id}/rules/unlink` | 解除关联 |

### 其他
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/resolve` | 解析页面 |
| POST | `/api/resolve` | 执行解析 |
| GET | `/evolutions` | 演化列表 |
| GET | `/logs` | 操作日志 |
| GET | `/stats` | 统计 |
| GET | `/cache` | 缓存管理 |
| POST | `/api/cache/flush` | 清缓存 |
| GET | `/api-keys` | API Key 管理 |
| POST | `/api/api-keys` | 生成 API Key |
| DELETE | `/api/api-keys/{id}` | 撤销 API Key |
| GET | `/profile` | 个人资料 |
| GET/POST | `/settings` | 系统设置（admin only） |

---

## 八、Web UI 页面

| 路径 | 模板 | 说明 |
|------|------|------|
| `/login` | login.html | 登录页 |
| `/register` | register.html | 注册页 |
| `/profile` | profile.html | 个人资料 |
| `/skills` | skills/list.html | 技能列表（Alpine.js x-for） |
| `/skills/create` | skills/form.html | 技能创建/编辑 |
| `/skills/{id}` | skills/detail.html | 技能详情 |
| `/skills/import` | skills/import.html | 技能导入（GitHub/ClawHub） |
| `/skills/{id}/review` | skills/review.html | 技能审核 |
| `/rules` | rules/list.html | 规则列表（Alpine.js x-for） |
| `/rules/create` | rules/form.html | 规则创建/编辑 |
| `/rules/{id}` | rules/detail.html | 规则详情 |
| `/models` | models/list.html | 模型列表 |
| `/models/create` | models/form.html | 模型创建/编辑 |
| `/projects` | projects/list.html | 项目列表 |
| `/projects/create` | projects/form.html | 项目创建/编辑 |
| `/projects/{id}` | projects/detail.html | 项目详情（技能/规则关联） |
| `/resolve` | resolve/index.html | 解析测试页 |
| `/evolutions` | evolutions/list.html | 演化列表 |
| `/logs` | logs/list.html | 操作日志 |
| `/stats` | stats/index.html | 统计 |
| `/cache` | cache/index.html | 缓存管理 |
| `/api-keys` | api_keys/list.html | API Key 管理 |
| `/users` | users/list.html | 用户管理（admin） |
| `/users/create` | users/form.html | 用户创建/编辑 |
| `/settings` | settings/index.html | 系统设置（admin） |
| `/permissions` | permissions/list.html | 技能权限管理（admin） |
| `/permissions/{skill_id}/edit` | permissions/form.html | 权限编辑 |

---

## 九、配置

### .env 变量

```ini
# 数据库
DB_PASSWORD=change_me
DATABASE_URL=postgresql+asyncpg://app:change_me@localhost:5432/skill-manager

# Redis
REDIS_URL=redis://localhost:6379/0

# 管理员
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# API Key（MCP 工具默认认证）
SKILL_MANAGER_API_KEY=

# LLM（意图分析/重排序）
LLM_ENDPOINT=http://localhost:8000/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-v4-flash-free

# Embedding
EMBEDDING_ENDPOINT=http://localhost:8000/v1
EMBEDDING_API_KEY=sk-xxx
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=384

# 超时与限制
LLM_TIMEOUT=30
EMBEDDING_TIMEOUT=15
RESOLVE_TOP_K_DEFAULT=5
CACHE_TTL_SECONDS=3600
```

### config.py 结构

```python
class Settings(BaseSettings):
    # 所有 .env 变量映射到此
    # db_url 属性：优先用 database_url，否则拼接
    # model_config = {"env_file": ".env", "extra": "ignore"}
```

---

## 十、部署

### Docker Compose

```yaml
services:
  app:
    build: .
    network_mode: host        # 直接用宿主机网络
    env_file: .env
    volumes:
      - ./data:/app/data      # 持久化 system_settings.json
    restart: unless-stopped
```

### Dockerfile

```dockerfile
FROM docker.1ms.run/library/python:3.13-slim  # 镜像加速
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8788
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8788"]
```

### 部署命令

```bash
# 构建并启动
docker compose up -d --build

# 查看日志
docker logs -f skillrouter-app-1

# 热更新（不重建镜像）
scp app/main.py root@192.168.0.100:/tmp/main.py
ssh root@192.168.0.100 "docker cp /tmp/main.py skillrouter-app-1:/app/app/main.py && docker restart skillrouter-app-1"

# 数据库迁移（在容器内执行）
docker exec -it skillrouter-app-1 python -c "from app.db.init_db import init_database; import asyncio; asyncio.run(init_database())"
```

### 外部依赖

| 服务 | 用途 | 必需 |
|------|------|------|
| PostgreSQL + pgvector | 技能/规则存储 + 向量搜索 | 是 |
| Redis | 缓存 + 限流 | 是 |
| LLM API (OpenAI兼容) | 意图分析 + 重排序 | 可降级 |
| Embedding API | 向量生成 | 是 |

---

## 十一、已知坑（重要）

### 11.1 PowerShell 转义

PowerShell 双引号内不能直接嵌套双引号。SSH 命令中的 Python 代码用单引号包裹，内部用转义：

```powershell
# 错误
ssh ... "docker exec ... python -c 'print("hello")'"

# 正确
ssh ... "docker exec ... python -c 'print(\"hello\")'"
```

### 11.2 write 工具不能写 Jinja2 模板

`write` 工具解析 JSON 内容时，Jinja2 的 `{{ }}` `{% %}` 会破坏 JSON 解析。

**解决方案**：先写到本地临时文件，再 SCP + docker cp 到容器。

### 11.3 `{{ u | tojson }}` 在 Alpine.js @click 中

Jinja2 的 `{{ }}` 与 Alpine.js 的 `{{ }}` 冲突，且 `tojson` 输出的引号会破坏 `@click` 属性。

**解决方案**：用 `window.__data[idx]` + `<script>` 标签，不在 `@click` 中使用 `tojson`。

### 11.4 TestClient + asyncpg 冲突

`httpx.AsyncClient`（TestClient）与 asyncpg 不兼容，报 `InterfaceError: another operation is in progress`。

**解决方案**：集成测试不用 TestClient，直接测试服务函数。生产环境无此问题。

### 11.5 `is_active` 布尔值

PostgreSQL BOOLEAN 可能返回 `None`（老数据）。查询时用 `is_active is not True` 而不是 `is_active is False`。

### 11.6 MCP lifespan 嵌套

FastMCP 的 StreamableHTTP 需要自己的 lifespan。必须用 `combined_lifespan` 嵌套：

```python
@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    async with app_lifespan(app):        # 外层：app 初始化
        async with _mcp_app.lifespan(app):  # 内层：MCP session manager
            yield
```

**顺序不能反**。MCP lifespan 必须是内层（后初始化，先销毁）。

### 11.7 GitHub 导入速率限制

GitHub API 无 token 限制 60 req/hr。用 `raw.githubusercontent.com` 下载文件无限制。

### 11.8 ClawHub 导入不可靠

ClawHub 是 SPA，API 返回 503。解决方案：在 GitHub 搜索源码。

### 11.9 路由顺序

`/skills/import` 必须在 `/skills/{skill_id}` 之前注册，否则 UUID 解析冲突返回 400。

### 11.10 姓名唯一性作用域

技能、规则、模型、分组的名称唯一性按 `user_id` 隔离。分组还按 `parent_id` 隔离（同父分组下不重名）。

### 11.11 clipboard API

`navigator.clipboard.writeText` 需要 HTTPS。HTTP 环境用隐藏 textarea + `document.execCommand('copy')` 兜底。

### 11.12 Alpine.js 动态列表

Jinja2 渲染的静态表格无法响应客户端搜索。必须用 Alpine.js `x-for` + `filteredXxx` getter 实现客户端过滤。

---

## 十二、i18n

### 翻译文件

- `app/i18n/zh.json` — 300+ 翻译 key
- 默认英文（key 即英文文本）

### i18n 完善内容

- ✅ 用户管理：super_admin、developer、readonly 角色翻译
- ✅ 权限管理：Allowed/Denied Roles、Reset to Default 等
- ✅ 统计页面：Session Cache、Cache Hit Rate、System Load 等
- ✅ 技能表单：Examples、语言选项占位符
- ✅ 分组管理：Group Name、Parent Group 等
- ✅ 设置页面：Allow Registration、Save Changes 等
- ✅ 权限页面：所有角色名称和操作文本

### 使用方式

```python
# Python
from app.i18n import get_translator
_ = get_translator(session)  # 从 session["lang"] 读取
_("Delete")  # → "删除" 或 "Delete"
```

```html
<!-- Jinja2 模板 -->
{{ _('Delete') }}
```

### 语言切换

`/login?lang=zh` 或 `/login?lang=en`，写入 session。

---

## 十三、当前状态

### 已完成

| Phase | 内容 | 状态 |
|-------|------|------|
| P0 | 登录/登出/用户CRUD/Skills/Rules/Models CRUD | ✅ |
| P1 | 项目隔离/角色权限/公共私有 | ✅ |
| P2 | 会话缓存/规则加权/小模型重排/Top 2-6 | ✅ |
| P3 | 项目指令/技能指令/指令注入 | ✅ |
| P4 | 参数校验/业务规则校验 | ✅ |
| P5 | 注册/限流/API Key | ✅ |
| P6 | MCP工具增强/Web UI完善/测试 | ✅ |
| P7.1 | i18n 中英完善 | ✅ |
| P7.2 | 技能分组 | ✅ |
| P7.3 | 项目技能/规则关联 | ✅ |
| P7.5 | 规则分组 | ✅ |
| P7.6 | LLM列表i18n/密钥复制 | ✅ |
| — | MCP Streamable-HTTP 挂载 | ✅ |
| — | GitHub/ClawHub 技能导入 | ✅ |
| — | 系统设置（注册开关） | ✅ |
| P8.1 | 自动分类服务 | ✅ |
| P8.2 | 并行检索优化 | ✅ |
| P8.3 | Ranker Prompt 优化 | ✅ |
| P8.4 | Embedding 序列化修复 | ✅ |
| P8.5 | README 中英文档完善 | ✅ |

### 测试数据

当前数据库只有 admin 用户，其他数据已清空。

### 测试

31 个集成测试（`tests/`），但每次运行前需清空数据库（ uniqueness 约束冲突）。

---

## 十四、待开发 / 下一步

| 优先级 | 内容 | 说明 |
|--------|------|------|
| 高 | Skill进化反馈循环 | 追踪技能实际使用率，数据驱动权重调优 |
| 高 | 监控告警 | 生产环境需要 |
| 中 | Precision@k监控 | 量化推荐的精准度指标 |
| 中 | 备份策略 | 数据库定期备份 |
| 中 | GitHub Token 配置 | 提升 API 速率限制到 5000/hr |
| 中 | CLI规则管理命令 | srcli rule list/create/update/delete |
| 低 | 多语言支持 | 日语等更多语言 |
| 低 | 技能市场/公共注册表 | 公开技能分享平台 |
| 低 | 技能组合(链式调用) | 多个技能协同工作 |
| 低 | Agent记忆集成 | 与外部记忆系统对接 |
| 低 | 技能实时热重载 | 无需重启更新技能 |

---

## 十五、开发约定

1. **迁移只增不删** — `init_db.py` 只 ADD COLUMN/CREATE TABLE，不 DROP
2. **热更新用 SCP** — 不重建镜像，`docker cp` + `docker restart`
3. **前端不用构建工具** — Jinja2 + Alpine.js + Tailwind CSS CDN
4. **API Key 认证** — MCP 工具通过 `api_key` 参数，REST API 通过 `X-API-Key` header
5. **用户隔离** — 所有查询按 `user_id` 过滤（admin 可查看所有）
6. **分组删除自动 ungroup** — 子项 group_id 设为 NULL
7. **LLM 调用必须降级** — 超时/报错不能阻断主流程
