# Agents Module — Agent 管理模块

## 1. 模块概述

Agent 管理模块是 AIDP 平台的核心编排层。**Agent = Instructions + Skills + Rules + Knowledge**，它将分散的能力单元组合为一个完整的 AI Agent 定义。Agent 可以拥有角色、指令、关联的技能/规则/知识库，支持模板派生和上下文汇编。

**模块注册** (`apps/controller/app/modules/agents/__init__.py`):

```python
@register_module(name='agents', enabled=True)
class AgentsModule(BaseModule):
    name = "agents"
    description = "Agent管理，组合 Instructions/Skills/Rules/Knowledge"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as agents_router
        app.include_router(agents_router, prefix="/api/agents")
```

**Agent 的组成**：
- **Instructions** — Agent 的角色定义和行为准则（自然语言提示词）
- **Skills** — 关联的技能定义（可复用的 AI 能力）
- **Rules** — 关联的规则约束（安全/风格/架构等边界）
- **Knowledge** — 关联的知识库（领域知识、文档等）

---

## 2. 数据模型

全部定义在 `apps/controller/app/modules/agents/models.py`。

### 多对多关联表

```python
# Agent <-> Skill 关联表
agent_skills = Table(
    "aidp_agent_skills", Base.metadata,
    Column("agent_id", String(36), ForeignKey("aidp_agents.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", String(36), ForeignKey("aidp_skills.id", ondelete="CASCADE"), primary_key=True),
)

# Agent <-> Rule 关联表
agent_rules = Table(
    "aidp_agent_rules", Base.metadata,
    Column("agent_id", String(36), ForeignKey("aidp_agents.id", ondelete="CASCADE"), primary_key=True),
    Column("rule_id", String(36), ForeignKey("aidp_rules.id", ondelete="CASCADE"), primary_key=True),
)

# Agent <-> KnowledgeBase 关联表
agent_knowledge = Table(
    "aidp_agent_knowledge", Base.metadata,
    Column("agent_id", String(36), ForeignKey("aidp_agents.id", ondelete="CASCADE"), primary_key=True),
    Column("knowledge_base_id", String(36), ForeignKey("aidp_knowledge_bases.id", ondelete="CASCADE"), primary_key=True),
)
```

三个关联表均使用复合主键 `(agent_id, resource_id)`，`ondelete="CASCADE"` 确保删除 Agent 时自动清理关联记录。

### Agent（Agent 定义）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(36)` | 主键，UUID |
| `name` | `String(200)` | Agent 名称，NOT NULL |
| `role` | `String(100)` | 角色描述（如"全栈工程师"） |
| `instructions` | `Text` | AI 指令（行为准则核心） |
| `scope` | `String(20)` | 作用域：`global` / `personal` / `project` |
| `parent_agent_id` | `String(36)` | FK 自引用（父子 Agent 关系） |
| `project_id` | `Integer` | FK -> `aidp_projects.id` |
| `user_id` | `String(100)` | 所有者 |
| `config` | `Text` | JSON 对象，额外配置 |
| `extra_data` | `Text` | JSON 扩展数据 |
| `sort_order` | `Integer` | 排序 |
| `is_active` | `Boolean` | 是否启用，默认 True |
| `is_template` | `Boolean` | 是否为模板，默认 False |
| `created_at` | `DateTime` | 创建时间 |
| `updated_at` | `DateTime` | 更新时间 |
| `deleted_at` | `DateTime` | 软删除时间 |

**多对多关系（使用 `selectin` 加载策略）**：

```python
skills = relationship("Skill", secondary=agent_skills, lazy="selectin")
rules = relationship("Rule", secondary=agent_rules, lazy="selectin")
knowledge_bases = relationship("KnowledgeBase", secondary=agent_knowledge, lazy="selectin")
```

**父子关系**：

```python
parent = relationship("Agent", remote_side="Agent.id", back_populates="children")
children = relationship("Agent", back_populates="parent", cascade="all, delete-orphan")
```

`to_dict(include_relations=False)` 方法在 `include_relations=True` 时返回关联的 skills/rules/knowledge_bases/children 列表。

---

## 3. API 端点

全部定义在 `apps/controller/app/modules/agents/routes.py`，前缀 `/api/agents`。

### 静态路由

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/agents/list` | Agent 列表，支持 scope/is_template/search 过滤 |
| `POST` | `/api/agents/create` | 创建 Agent（含关联资源） |
| `GET` | `/api/agents/templates/list` | 获取所有全局模板 |
| `POST` | `/api/agents/from-template/{template_id}` | 从模板创建 Agent |
| `GET` | `/api/agents/stats` | 统计信息（总数 + 按 scope 分布） |

### 参数化路由

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/agents/{agent_id}` | 获取详情（含关联资源） |
| `PUT` | `/api/agents/{agent_id}` | 更新 Agent |
| `DELETE` | `/api/agents/{agent_id}` | 软删除 Agent |
| `GET` | `/api/agents/{agent_id}/context` | **上下文汇编器** |
| `POST` | `/api/agents/{agent_id}/link-skill` | 关联技能 |
| `POST` | `/api/agents/{agent_id}/unlink-skill` | 解除技能关联 |
| `POST` | `/api/agents/{agent_id}/link-rule` | 关联规则 |
| `POST` | `/api/agents/{agent_id}/unlink-rule` | 解除规则关联 |
| `POST` | `/api/agents/{agent_id}/link-knowledge` | 关联知识库 |
| `POST` | `/api/agents/{agent_id}/unlink-knowledge` | 解除知识库关联 |

### 创建 Agent 流程

```python
@router.post("/create")
async def create_agent(data: AgentCreate, ...):
    agent = Agent(name=data.name, role=data.role, instructions=data.instructions, ...)
    db.add(agent)
    await db.flush()
    # 批量插入关联
    for sid in data.skill_ids:
        await db.execute(agent_skills.insert().values(agent_id=agent.id, skill_id=sid))
    for rid in data.rule_ids:
        await db.execute(agent_rules.insert().values(agent_id=agent.id, rule_id=rid))
    for kid in data.knowledge_base_ids:
        await db.execute(agent_knowledge.insert().values(agent_id=agent.id, knowledge_base_id=kid))
    await db.commit()
    await db.refresh(agent, ['skills', 'rules', 'knowledge_bases', 'children'])
    return agent.to_dict(include_relations=True)
```

---

## 4. 上下文汇编器

`GET /api/agents/{agent_id}/context` 是 Agent 模块的核心功能，它将 Agent 所有关联资源汇编为一个完整的上下文对象，供 AI 调用时使用。

**路由实现** (`routes.py:246-281`):

```python
@router.get("/{agent_id}/context")
async def get_agent_context(agent_id: str, ...):
    result = await db.execute(select(Agent).where(...))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 1. 初始化上下文容器
    context = {
        "instructions": agent.instructions or "",
        "role": agent.role or "",
        "skills": [], "rules": [], "knowledge": []
    }

    # 2. 加载关联的 Skills
    await db.refresh(agent, ['skills', 'rules', 'knowledge_bases'])
    for s in agent.skills:
        context["skills"].append({
            "id": s.id, "name": s.name, "instruction": s.instruction
        })

    # 3. 加载关联的 Rules
    for r in agent.rules:
        context["rules"].append({
            "id": r.id, "name": r.name, "content": r.content, "severity": r.severity
        })

    # 4. 加载关联的 Knowledge
    for k in agent.knowledge_bases:
        context["knowledge"].append({
            "id": k.id, "name": k.name, "description": k.description
        })

    # 5. 沿父链继承 Rules 和 Instructions
    parent = agent
    visited = {agent_id}
    while parent.parent_agent_id and parent.parent_agent_id not in visited:
        visited.add(parent.parent_agent_id)
        result = await db.execute(select(Agent).where(...))
        parent = result.scalar_one_or_none()
        if not parent: break
        await db.refresh(parent, ['rules'])
        for r in parent.rules:
            if not any(x['id'] == r.id for x in context["rules"]):
                context["rules"].append({...})
        if parent.instructions:
            context["instructions"] = (
                f"[Parent: {parent.name}]\n{parent.instructions}\n\n"
                f"[Current: {agent.name}]\n{context['instructions']}"
            )
    return context
```

### 汇编流程说明

1. **加载 Agent 的 Instructions** — 直接从 Agent 的 `instructions` 字段获取核心指令
2. **加载关联的 Skills** — 通过 `agent_skills` 关联表获取所有 Skill，提取 `name` 和 `instruction`
3. **加载关联的 Rules** — 通过 `agent_rules` 关联表获取所有 Rule，提取 `name`、`content`、`severity`
4. **加载关联的 Knowledge** — 通过 `agent_knowledge` 关联表获取所有 KnowledgeBase，提取 `name`、`description`
5. **沿父链继承** — 通过 `parent_agent_id` 向上遍历父 Agent：
   - 父 Agent 的 Rules 合并到当前上下文（去重）
   - 父 Agent 的 Instructions 以 `[Parent: name]` 前缀拼接在顶部

**返回示例**：

```json
{
    "instructions": "[Parent: 基础工程师]\n你是一个通用编码助手...\n\n[Current: 全栈工程师]\n你专注于 Python + React 开发...",
    "role": "全栈工程师",
    "skills": [{"id": "...", "name": "代码审查", "instruction": "审查代码质量..."}],
    "rules": [{"id": "...", "name": "禁止 eval", "content": "禁止使用 eval()", "severity": "critical"}],
    "knowledge": [{"id": "...", "name": "项目文档", "description": "项目架构说明"}]
}
```

---

## 5. 模板系统

Agent 模板是 `scope="global"` 且 `is_template=True` 的特殊 Agent，用于快速创建标准化 Agent。

### 模板路由

**列出模板** (`GET /api/agents/templates/list`):

```python
@router.get("/templates/list")
async def list_templates(...):
    result = await db.execute(
        select(Agent).where(and_(
            Agent.deleted_at.is_(None),
            Agent.is_template == True,
            Agent.scope == "global"
        )).order_by(Agent.sort_order)
    )
    return {"items": [a.to_dict() for a in result.scalars().all()]}
```

**从模板创建** (`POST /api/agents/from-template/{template_id}`):

```python
@router.post("/from-template/{template_id}")
async def create_from_template(template_id: str, name: Optional[str] = None, ...):
    template = await db.execute(select(Agent).where(
        and_(Agent.id == template_id, Agent.deleted_at.is_(None), Agent.is_template == True)
    ))
    template = template.scalar_one_or_none()
    await db.refresh(template, ['skills', 'rules', 'knowledge_bases'])

    # 创建新 Agent，scope 自动设为 personal 或 project
    agent = Agent(
        name=name or template.name,
        role=template.role, instructions=template.instructions,
        scope="personal" if not project_id else "project",
        config=template.config, user_id=user_id, project_id=project_id
    )
    db.add(agent)
    await db.flush()

    # 复制模板的关联资源
    for s in template.skills:
        await db.execute(agent_skills.insert().values(agent_id=agent.id, skill_id=s.id))
    for r in template.rules:
        await db.execute(agent_rules.insert().values(agent_id=agent.id, rule_id=r.id))
    for k in template.knowledge_bases:
        await db.execute(agent_knowledge.insert().values(agent_id=agent.id, knowledge_base_id=k.id))

    await db.commit()
    return agent.to_dict(include_relations=True)
```

模板机制支持企业级标准化：管理员定义全局模板（含角色定义、指令和关联资源），普通用户一键派生为自己的个人 Agent。

---

## 6. 前端

全部定义在 `apps/controller/app/web/templates/modules/agents/list_content.html`（141 行）。

### Alpine.js 函数

```javascript
window.agentsPage = function agentsPage() {
    return {
        agents: [], templates: [], searchQuery: '', scopeFilter: 'personal',
        loading: false, showCreateModal: false, showDetailModal: false,
        showTemplateModal: false, detail: null, detailTab: 'info', stats: {},
        form: { name: '', role: '', instructions: '', scope: 'personal' },

        async init() {
            await Promise.all([this.loadAgents(), this.loadStats(), this.loadTemplates()]);
            // 如果 URL 中有 ?templates=1，自动打开模板模态框
            if (window.location.search.includes('templates=1'))
                this.showTemplateModal = true;
        },

        async loadAgents() { /* GET /api/agents/list?scope=... */ },
        async loadStats() { /* GET /api/agents/stats */ },
        async createAgent() { /* POST /api/agents/create */ },
        async viewAgent(a) { /* GET /api/agents/{id} */ },
        async deleteAgent(a) { /* DELETE /api/agents/{id} */ },
        async loadTemplates() { /* GET /api/agents/templates/list */ },
        async createFromTemplate(t) { /* POST /api/agents/from-template/{id} */ },
    };
}
```

### UI 元素

**统计行**（4 列卡片）：
- Agent 总数
- 全局模板数（紫色）
- 个人 Agent 数（蓝色）
- 项目 Agent 数（绿色）

**搜索 + 过滤**：
- 搜索框（300ms debounce，搜索 name + role）
- 作用域下拉框：我的 Agent / 全局模板 / 项目

**操作按钮**：
- 「从模板创建」— 打开模板选择模态框
- 「创建 Agent」— 打开创建模态框

**Agent 卡片网格**（3 列）：
- 机器人图标 + 名称 + 类型徽章（模板/个人）
- 角色描述
- Instructions 预览（截取前 120 字符）

**创建模态框**：
- 名称（必填）
- 角色（如"全栈工程师"）
- Instructions（多行文本域）
- 作用域选择（个人/项目/全局）

**详情模态框**（4 个标签页）：
- **信息** — 名称、角色、作用域、是否为模板
- **Instructions** — 完整的指令内容（绿色等宽字体）
- **技能** — 关联的技能列表（带闪电图标）
- **规则** — 关联的规则列表（带盾牌图标）
- 底部有删除按钮和关闭按钮

**模板选择模态框**：
- 列出所有全局模板
- 每个模板显示名称 + 角色/指令预览
- 点击后自动调用 `POST /api/agents/from-template/{id}`