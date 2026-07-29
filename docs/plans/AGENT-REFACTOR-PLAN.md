# Agent 模块重构方案

> **版本**: v1.0  
> **日期**: 2026-07-29  
> **状态**: 规划中

---

## 1. 现状分析

### 1.1 当前 Agent 模型

```python
class Agent(Base):
    id, name, role, instructions
    scope: global/personal/project
    parent_agent_id, is_template
    config, extra_data

    # 多对多关联（冗余——管线自己会匹配）
    skills           # ← Stage 3 SkillRouter 实时匹配, 不需要预先绑定
    rules            # ← Stage 0 instructions 已包含, 不需要单独关联
    knowledge_bases  # ← Stage 2 意图检索, 不需要预先绑定
```

### 1.2 问题

| 问题 | 说明 |
|------|------|
| **三张关联表冗余** | skills/rules/knowledge 的绑定管线自己会动态检索, 静态绑定反而局限 |
| **未被管线使用** | Agent 模块只在 `seed_data.py` 创建默认数据, 不被任何执行流程引用 |
| **scope 默认 personal** | "后端开发助手"应该对所有项目可用, 不限于个人 |
| **与 `agent_instructions` 表功能重叠** | 两张表都在存 role+instructions, 但只有 instructions 表被管线加载 |

### 1.3 对比 `agent_instructions` 表

| 字段 | Agent | agent_instructions | 谁被管线用 |
|------|:---:|:---:|:---:|
| role | ✅ | ✅ | agent_instructions |
| instructions/constraints | ✅ | ✅ | agent_instructions |
| 规则列表 | ❌ (关联表) | ✅ (JSON字段) | agent_instructions |
| 作用域 | global/personal/project | project_id + agent_type | agent_instructions |

`agent_instructions` 是 Stage 0 真正加载的表。Agent 可以做 UI 配置界面，但应该最终写入 `agent_instructions`。

---

## 2. 重构目标

### 2.1 Agent 的新角色

Agent = 一个**领域专家身份模板**，用来告诉管线"这次任务是什么类型的"

```
Agent "backend-dev":
  │
  ├─ role: "你是一个FastAPI后端开发专家"
  ├─ instructions: "遵循RESTful规范, 使用Pydantic验证, 
  │                 错误统一处理, 数据库操作用SQLAlchemy async"
  ├─ domain_tags: ["backend", "api", "database"]
  └─ scope: global  (全平台可用)

管线使用方式:
  aidp_context(task="修复登录bug")
  → Stage 1: intent.domains = ["auth", "backend"]
  → Stage 0: 匹配 domain_tags → 选中 "backend-dev"
  → 加载该 Agent 的 role + instructions
  → 管线用"后端专家身份"运行
```

### 2.2 不做什么

- ❌ 不绑定 skills（管线动态匹配）
- ❌ 不绑定 rules（instructions 里已经有规则）
- ❌ 不绑定 knowledge_bases（管线按意图检索）
- ❌ 不和现有 `agent_instructions` 表冲突（Agent 新增/编辑后写入该表）

---

## 3. 详细设计

### 3.1 数据模型（精简后）

```python
class Agent(Base):
    __tablename__ = "aidp_agents"

    id          = Column(String(36), primary_key=True)
    name        = Column(String(200), nullable=False)     # "后端开发专家"
    agent_key   = Column(String(100), unique=True)         # "backend-dev" (程序标识)
    role        = Column(Text)                            # "你是一个FastAPI后端开发专家"
    instructions = Column(Text)                           # 专用指令
    domain_tags = Column(Text, default="[]")               # '["backend","api","database"]'
    scope       = Column(String(20), default="global")     # global / personal / project
    project_id  = Column(Integer, nullable=True)           # project scope 时使用
    user_id     = Column(String(100), nullable=True)       # personal scope 时使用
    is_active   = Column(Boolean, default=True)
    is_template = Column(Boolean, default=False)           # 是否作为模板
    sort_order  = Column(Integer, default=0)
    config      = Column(Text, default="{}")              # 保留, 扩展用
```

**删除**：
- ❌ `parent_agent_id` — 模板体系不需要继承链
- ❌ `extra_data` — 未使用的字段
- ❌ `skills` 关联表 `aidp_agent_skills`
- ❌ `rules` 关联表 `aidp_agent_rules`
- ❌ `knowledge_bases` 关联表 `aidp_agent_knowledge`

**删除的表**：
- `aidp_agent_skills`
- `aidp_agent_rules`
- `aidp_agent_knowledge`

### 3.2 domain_tags 设计

```python
# 支持的领域标签
DOMAIN_TAGS = {
    "backend":   "后端开发 (API, 数据库, 服务端逻辑)",
    "frontend":  "前端开发 (UI, 组件, 交互)",
    "fullstack": "全栈开发",
    "testing":   "测试和调试",
    "devops":    "部署和运维 (Docker, CI/CD)",
    "database":  "数据库 (SQL, ORM, 迁移)",
    "security":  "安全 (认证, 授权, 加密)",
    "ai_ml":     "AI/ML (模型训练, 推理, 嵌入)",
    "code_indexing":  "代码索引和搜索",
    "documentation":   "文档编写和管理",
    "general":   "通用开发助手"       # 默认值
}
```

### 3.3 预置 Agent 模板

```python
DEFAULT_AGENTS = [
    {
        "name": "通用开发助手",
        "agent_key": "main",
        "role": "你是一个全栈开发助手，精通多种编程语言和框架。",
        "instructions": "提供清晰的代码示例，解释设计决策，遵循项目已有的编码风格。",
        "domain_tags": ["general"],
        "scope": "global",
        "is_template": True,
    },
    {
        "name": "后端开发专家",
        "agent_key": "backend-dev",
        "role": "你是一个FastAPI/Python后端开发专家，精通RESTful API设计和数据库优化。",
        "instructions": 
            "1. API设计遵循RESTful规范, 使用Pydantic模型验证\n"
            "2. 数据库操作用SQLAlchemy async, 避免N+1查询\n"
            "3. 错误统一用异常处理, 返回结构化响应\n"
            "4. 敏感数据不暴露在URL或日志中\n"
            "5. 所有异步操作设置超时和重试",
        "domain_tags": ["backend", "api", "database"],
        "scope": "global",
        "is_template": True,
    },
    {
        "name": "前端开发专家",
        "agent_key": "frontend-dev",
        "role": "你是一个前端开发专家，精通React/Vue和现代CSS。",
        "instructions": 
            "1. 组件设计遵循单一职责原则\n"
            "2. 状态管理清晰, 避免prop-drilling\n"
            "3. 使用TypeScript类型定义\n"
            "4. 关注性能和可访问性",
        "domain_tags": ["frontend"],
        "scope": "global",
        "is_template": True,
    },
    {
        "name": "测试专家",
        "agent_key": "testing-dev",
        "role": "你是一个软件测试专家，精通单元测试、集成测试和E2E测试。",
        "instructions": 
            "1. 测试覆盖率优先核心逻辑\n"
            "2. 使用pytest/playwright等工具\n"
            "3. 测试边界条件和错误路径\n"
            "4. mock外部依赖",
        "domain_tags": ["testing"],
        "scope": "global",
        "is_template": True,
    },
]
```

### 3.4 管线集成（Stage 0 改造）

```python
# context_pipeline.py _stage_0_load_instructions 改造

async def _stage_0_load_instructions(self, ctx: PipelineContext):
    """Stage 0: 根据意图领域匹配 Agent, 加载对应指令"""
    
    # 1. 先尝试用 intent 的 domains 匹配 Agent
    agent = await self._match_agent_by_domain(
        project_id=int(ctx.project_id),
        domains=ctx.intent.get("domains", [])
    )
    
    # 2. 如果没有匹配, fallback 到 agent_type="main"
    if not agent:
        agent = await self._load_agent_by_key("main")
    
    # 3. 加载 Agent 的 instructions
    if agent:
        ctx.instructions = {
            "role": agent.role,
            "constraints": ...,
            "rules": ...,
            "agent_name": agent.name,
            "agent_key": agent.agent_key,
        }

async def _match_agent_by_domain(self, project_id: int, domains: list) -> Optional[Agent]:
    """根据意图领域匹配最合适的 Agent"""
    # 1. 先查项目特有的 Agent
    agents = await query_project_agents(project_id)
    
    # 2. 对每个 Agent 的 domain_tags 与 intent domains 做交集
    best_agent = None
    best_score = 0
    for agent in agents:
        agent_domains = json.loads(agent.domain_tags)
        score = len(set(agent_domains) & set(domains))
        if score > best_score:
            best_score = score
            best_agent = agent
    
    # 3. 有匹配 → 返回; 无匹配 → None (管线 fallback 到 "main")
    return best_agent if best_score > 0 else None
```

### 3.5 domain → agent 匹配规则

```
intent.domains                    匹配 Agent          匹配得分
────────────────────────────────────────────────────────────
["backend", "api"]               backend-dev         2
["backend", "database"]          backend-dev         2
["frontend", "ui"]               frontend-dev        2
["testing"]                      testing-dev         1
["backend", "security"]          backend-dev (1)     (无security agent)
["unknown"]                      → fallback main
[]                               → fallback main
```

### 3.6 API 端点（简化后）

```
GET    /api/agents/list          列出 Agent (按scope筛选)
POST   /api/agents/create        创建 Agent
GET    /api/agents/{id}          详情
PUT    /api/agents/{id}          更新
DELETE /api/agents/{id}          删除

GET    /api/agents/templates     列出模板 (is_template=True)
POST   /api/agents/from-template/{id}  从模板创建

POST   /api/agents/{id}/sync-to-instructions  同步到 agent_instructions 表
```

### 3.7 Agent 与 `agent_instructions` 的双向同步

```
Agent UI 创建/编辑 → 保存到 aidp_agents 表
                         │
                         └─ 同时写入 agent_instructions 表
                            (project_id, agent_type=agent_key, role, constraints, rules)

管线加载:
  Stage 0 → 先查 aidp_agents 做 domain 匹配
          → 再读 agent_instructions 加载内容
```

---

## 4. 开发计划

### Phase 1: 模型精简 (1h)

- [ ] 修改 `Agent` 模型：删除关联表字段, 增加 `agent_key`, `domain_tags`
- [ ] 删除三张关联表: `aidp_agent_skills`, `aidp_agent_rules`, `aidp_agent_knowledge`
- [ ] 更新 `seed_data.py`: 用新的 4 个预置 Agent 模板替换
- [ ] 数据库迁移: 创建新字段, 删除旧表

### Phase 2: UI 简化 (1h)

- [ ] 重写 `agents/list.html`: 移除 skills/rules/knowledge 标签页
- [ ] 简化创建/编辑表单: 只保留 name, agent_key, role, instructions, domain_tags, scope
- [ ] 添加 domain_tags 多选组件
- [ ] 简化详情弹窗: 只显示基本信息, 移除关联管理

### Phase 3: 管线集成 (0.5h)

- [ ] `context_pipeline.py` Stage 0: 增加 `_match_agent_by_domain()`
- [ ] `context_pipeline.py` Stage 0: 用 domain 匹配替换固定 `agent_type="main"`
- [ ] Agent 更新时自动同步到 `agent_instructions` 表

### Phase 4: 测试部署 (0.5h)

- [ ] 单元测试: Agent CRUD, domain 匹配逻辑
- [ ] 集成测试: `aidp_context` 验证不同 task 匹配不同 Agent
- [ ] 全量 CRUD 测试验证不报错

---

## 5. 改动清单

| 文件 | 操作 | 工作量 |
|------|:---:|:---:|
| `modules/agents/models.py` | 重写 | 30行 → 50行 |
| `modules/agents/routes.py` | 简化 + 加 domain 匹配 | 删 30行 |
| `modules/agents/__init__.py` | 更新描述 | 1行 |
| `web/templates/modules/agents/list.html` | 重写 UI | 200行 |
| `services/context_pipeline.py` | 加 `_match_agent_by_domain` | 20行 |
| `services/seed_data.py` | 更新预置数据 | 10行 |
| `db/init_db.py` | 删除三张关联表 | 删 10行 |

**总计**: 约 3 小时, 7 个文件, 净增约 50 行代码