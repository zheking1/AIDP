# Agent 模块重构方案 v2 — LLM 智能自动创建

> **版本**: v2.0  
> **日期**: 2026-07-29  
> **状态**: 规划中

---

## 1. 设计理念

**不预置模板，不手动创建。** 项目初始化时，系统自动分析技术栈，用 LLM 生成专属 Agent。

```
aidp_init(project_name, tech_stack, description)
  │
  ├─ 全量索引 (现有)
  │
  ├─ 技术栈分析 (现有: tech_scan.py)
  │
  ├─ Step N: 智能 Agent 生成 ──────────────────────┐
  │    │                                          │
  │    └─→ LLM: "根据 FastAPI+PostgreSQL+React     │
  │             生成 2-3 个领域专属 Agent"         │
  │                                               │
  │    ←─ LLM Response:                           │
  │        [                                      │
  │          {                                    │
  │            "agent_key": "fastapi-backend",     │
  │            "name": "FastAPI 后端专家",          │
  │            "role": "...",                      │
  │            "instructions": "1. 使用 async/await│
  │              模式处理所有数据库操作...",         │
  │            "domain_tags": ["backend","api",    │
  │              "database"]                       │
  │          },                                    │
  │          {                                    │
  │            "agent_key": "react-frontend",      │
  │            "name": "React 18 前端专家",         │
  │            ...                                 │
  │          }                                     │
  │        ]                                       │
  │                                               │
  └─ Step N+1: 保存到 aidp_agents 表 + sync       │
               到 agent_instructions 表            │
────────────────────────────────────────────────────
```

## 2. 数据模型（精简后）

```python
class Agent(Base):
    __tablename__ = "aidp_agents"

    id            = primary_key
    name          = Column(String(200))          # "FastAPI 后端开发专家"
    agent_key     = Column(String(100), unique)   # "fastapi-backend"
    role          = Column(Text)                  # 一句话角色
    instructions  = Column(Text)                  # 详细指令 (5-10条)
    domain_tags   = Column(Text, default="[]")    # ["backend","api","database"]
    
    scope         = Column(String(20), default="project")  # project(自动创建)
    project_id    = Column(Integer)               # 所属项目
    user_id       = Column(String(100))           # 个人时使用
    
    source        = Column(String(20), default="auto")  # auto/manual
    source_version = Column(String(20))            # 生成时记录技术栈摘要
    
    is_active     = Column(Boolean, default=True)
    created_at, updated_at
```

**删除的表**：
- `aidp_agent_skills` ❌
- `aidp_agent_rules` ❌  
- `aidp_agent_knowledge` ❌

**新增字段**：
- `agent_key` — 程序标识, 如 "fastapi-backend"
- `domain_tags` — 匹配 Stage 1 intent.domains
- `source` — "auto"(LLM生成) / "manual"(手动创建)
- `source_version` — 记录生成时的技术栈, 方便后续更新

## 3. LLM Prompt 设计（核心）

```python
AGENT_GENERATION_PROMPT = """你是一个开发配置专家。根据以下项目信息, 生成 2-3 个领域专属 Agent 配置。

项目信息:
  - 技术栈: {tech_stack}
  - 描述: {description}  
  - 架构概述: {architecture_summary}

要求:
1. 根据实际技术栈生成 Agent，不要生成项目不涉及的技术领域
2. 每个 Agent 的 instructions 必须包含该技术栈版本相关的具体最佳实践
3. 输出纯 JSON, 不要额外解释

JSON 格式:
[{{
    "agent_key": "英文标识 (如 fastapi-backend)",
    "name": "中文名称 (如 'FastAPI 后端开发专家')",
    "role": "一句话角色定义",
    "instructions": "5-10条最佳实践, 用\\n分隔, 要具体到技术栈版本",
    "domain_tags": ["从 backend/frontend/fullstack/testing/devops/
                      database/security/ai_ml/docs/code_indexing 中选择1-3个"]
}}]

示例 (输入: Python 3.13+FastAPI+PostgreSQL):
[{{
    "agent_key": "fastapi-backend",
    "name": "FastAPI 后端开发专家",
    "role": "精通 Python 3.13 + FastAPI + PostgreSQL 后端开发",
    "instructions": "1. 所有数据库操作用 SQLAlchemy 2.0 async 模式\\n"
                   "2. 路由用 FastAPI 装饰器, 参数用 Pydantic v2 验证\\n"
                   "3. 错误处理统一用 HTTPException + 自定义 exception handler\\n"
                   "4. 数据库迁移用 Alembic, 不要手动改表结构\\n"
                   "5. 异步操作用 async/await, 不要用同步阻塞函数\\n"
                   "6. API 响应用 Pydantic response_model 做类型安全\\n"
                   "7. 依赖注入用 Depends(), 避免全局状态",
    "domain_tags": ["backend", "api", "database"]
}}]"""
```

### 技术栈 → Agent 类型推导（规则层）

```
技术栈项 → 推导 → Agent 类型

Python/FastAPI/Django/Flask/SpringBoot → {backend agent}
React/Vue/Angular/Next.js/Nuxt         → {frontend agent}
PostgreSQL/MySQL/MongoDB/Redis         → 合并到 backend agent
Docker/K8s/Nginx/GitHub Actions        → {devops agent}
pytest/jest/playwright/cypress         → {testing agent}
PyTorch/TensorFlow/scikit-learn       → {ai_ml agent}
TypeScript/Babel/Webpack              → 合并到 frontend agent
```

### Agent 生成数量逻辑

```python
def decide_agent_count(tech_stack: list) -> int:
    """根据技术栈决定生成几个 Agent"""
    has_backend = any(t in tech_lower for t in BACKEND_TECH)
    has_frontend = any(t in tech_lower for t in FRONTEND_TECH)
    has_testing = any(t in tech_lower for t in TESTING_TECH)
    has_devops = any(t in tech_lower for t in DEVOPS_TECH)
    has_ai = any(t in tech_lower for t in AI_TECH)
    
    count = 0
    if has_backend: count += 1
    if has_frontend: count += 1
    if has_testing: count += 1
    if has_devops: count += 1
    if has_ai: count += 1
    
    # 最少 1 个, 最多 3 个
    return max(1, min(3, count))
```

## 4. 集成到 aidp_init 流程

```python
# project_init_service.py 新增步骤

# Step 9: 智能生成 Agent
async def _generate_agents(project_id: int, tech_stack: str, description: str, 
                           architecture_summary: str):
    """用 LLM 分析技术栈, 自动生成 2-3 个领域 Agent"""
    
    # 1. 调用 LLM
    llm = LLMClient()
    await llm._ensure_config()
    prompt = AGENT_GENERATION_PROMPT.format(
        tech_stack=tech_stack,
        description=description,
        architecture_summary=architecture_summary
    )
    response = await llm.call(prompt, max_tokens=2000)
    
    # 2. 解析 JSON
    agents = json.loads(response)
    
    # 3. 保存
    for agent in agents:
        # 去重检查
        existing = await db.execute(
            select(Agent).where(
                Agent.project_id == project_id,
                Agent.agent_key == agent["agent_key"]
            )
        )
        if existing.scalar_one_or_none():
            continue
        
        # 创建 Agent
        new_agent = Agent(
            name=agent["name"],
            agent_key=agent["agent_key"],
            role=agent["role"],
            instructions=agent["instructions"],
            domain_tags=json.dumps(agent["domain_tags"]),
            scope="project",
            project_id=project_id,
            source="auto",
            source_version=tech_stack,
        )
        db.add(new_agent)
        
        # 同步到 agent_instructions 表
        await _sync_to_instructions(new_agent)
    
    await db.commit()
    return {"agents_created": len(agents)}
```

## 5. 管线集成（Agent 匹配引擎）

```python
# context_pipeline.py Stage 0 改造

async def _match_agent_by_domain(self, project_id: int, domains: list) -> Optional[Agent]:
    """根据意图领域自动匹配最合适的 Agent"""
    
    # 1. 查询项目所有 Agent
    agents = await self.db.execute(
        select(Agent).where(
            Agent.project_id == project_id,
            Agent.is_active == True
        )
    )
    agents = agents.scalars().all()
    
    # 2. 如果项目没有 Agent, fallback 到全局 Agent
    if not agents:
        return None
    
    # 3. 按 domain 匹配度排序
    scored = []
    for agent in agents:
        agent_domains = json.loads(agent.domain_tags)
        score = len(set(agent_domains) & set(domains))
        if score > 0:
            scored.append((score, agent))
    
    if not scored:
        return None  # 没有匹配, 管线用默认
    
    # 4. 返回最高分
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]
```

## 6. 开发计划

### Phase 1: 模型改造 (0.5h)

- [ ] 修改 Agent 模型: 删除关联表, 增加 agent_key/domain_tags/source/source_version
- [ ] 删除三张关联表
- [ ] `seed_data.py`: 移除旧 Agent 模板

### Phase 2: LLM 生成逻辑 (1h)

- [ ] 在 `project_init_service.py` 新增 `_generate_agents()` 步骤
- [ ] 技术栈 → Agent 类型推导规则
- [ ] Agent 数量决策逻辑 (最少1, 最多3)
- [ ] 去重检查 (按 agent_key)
- [ ] 同步到 agent_instructions 表

### Phase 3: 管线集成 (0.5h)

- [ ] `context_pipeline.py` Stage 0: `_match_agent_by_domain()`
- [ ] domain 匹配 + 评分

### Phase 4: UI 简化 (0.5h)

- [ ] 简化 Agent 管理页面
- [ ] 显示 source=`auto`/`manual` 标识
- [ ] 一键"重新生成 Agent"按钮

### Phase 5: 测试部署 (0.5h)

- [ ] 全量 CRUD 测试
- [ ] `aidp_init` 测试: 验证 Agent 自动创建
- [ ] `aidp_context` 测试: 验证 domain 匹配

**总计**: 约 3 小时, 5 个文件

---

## 7. Evolution 系统是否应进化 Agent

### 分析

| 维度 | 当前进化系统 | 是否应扩展到 Agent |
|------|------------|:---:|
| 进化对象 | 代码模式、bug修复方案、架构决策 | Agent 的 instructions |
| 触发器 | `analyze_and_evolve` / `index_changes` | Agent 使用反馈 |
| 范围 | 项目级 → 审核 → 系统级 | 项目级 → 审核 → 系统级 |
| 具体效果 | 系统级最佳实践 | 系统级 Agent 指令优化 |

### 必要性分析

**不需要进化 Agent 的理由**：
1. Agent 的 instructions 由 LLM 在初始化时生成，已经充分考虑了技术栈
2. Agent 只是一个过路角色——管线使用的 instructions 来自 `agent_instructions` 表
3. 技术栈变了 → 再跑一次 `aidp_init` → LLM 重新生成 Agent → 比"进化"更准确
4. 当前进化系统跟踪的是代码模式，跟踪 Agent 使用效果需要完全不同的度量体系

**需要进化 Agent 的理由**：
1. 跨项目学习——"A 项目的 FastAPI Agent 用得很成功，promote 到系统级给 B 项目用"
2. 当技术栈相似的项目多了，可以提炼出通用最佳实践

### 结论：不需要，也不需要刻意排除

**当前不接入**：Agent 的 instructions 质量由 LLM 保证，进化系统处理的是代码模式积累，这两个是**不同层面的问题**。

**预留接口**：Agent 模型保留 `source` 字段（auto/manual），如果将来出现（例如 Agent 使用反馈数据），通过 promote 按钮手动提交 Agent 配置到系统级即可——和现在的 promote_evolution 一脉相承。

最简单的方式：Agent 通过现有进化系统的 `promote_evolution` 提交。用户觉得某个 Agent 的 instructions 特别好 → 自然语言提交提案 → 管理员审核 → 系统级 Agent 模板。