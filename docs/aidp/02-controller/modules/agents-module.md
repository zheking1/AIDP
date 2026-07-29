# Agents Module (Agent 模块)

## 概述

Agent = Instructions + Skills + Rules + Knowledge。Agent 模块定义了 AI Agent 的身份、行为指令和资源组合。支持三层 scope 架构、模板复制（from-template）、父子继承（context 合并）。

**源码**: `apps/controller/app/modules/agents/`
**路由前缀**: `/api/agents`
**模型表**: `aidp_agents`, `aidp_agent_skills`, `aidp_agent_rules`, `aidp_agent_knowledge`

## 数据模型

### Agent (Agent 定义)

**表**: `aidp_agents`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| name | String(200) | Agent 名称 (可索引) |
| role | String(100) | 角色，如 `"developer"` |
| instructions | Text | 指令文本 |
| scope | String(20) | `"global"` / `"personal"` / `"project"` |
| parent_agent_id | String(36) FK | 父 Agent (自引用) |
| project_id | Integer FK | 关联项目 |
| user_id | String(100) | 创建者 |
| config | Text (JSON) | 配置 |
| extra_data | Text (JSON) | 扩展数据 |
| sort_order | Integer | 排序 |
| is_active | Boolean | 是否启用 (可索引) |
| is_template | Boolean | 是否模板 (可索引) |
| deleted_at | DateTime | 软删除时间 |

### 关联表

**aidp_agent_skills** (Agent ↔ Skill):
- `agent_id` (FK → `aidp_agents.id`, CASCADE)
- `skill_id` (FK → `aidp_skills.id`, CASCADE)

**aidp_agent_rules** (Agent ↔ Rule):
- `agent_id` (FK → `aidp_agents.id`, CASCADE)
- `rule_id` (FK → `aidp_rules.id`, CASCADE)

**aidp_agent_knowledge** (Agent ↔ KnowledgeBase):
- `agent_id` (FK → `aidp_agents.id`, CASCADE)
- `knowledge_base_id` (FK → `aidp_knowledge_bases.id`, CASCADE)

**关系** (ORM):
```python
skills = relationship("Skill", secondary=agent_skills, lazy="selectin")
rules = relationship("Rule", secondary=agent_rules, lazy="selectin")
knowledge_bases = relationship("KnowledgeBase", secondary=agent_knowledge, lazy="selectin")
parent / children: 自引用
```

## API 端点

### Agent CRUD

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/agents/list` | GET | - | 列出 Agent (scope, project_id, is_template, search) |
| `/api/agents/create` | POST | `skills:write:personal` | 创建 Agent (含 skills/rules/knowledge 绑定) |
| `/api/agents/templates/list` | GET | - | 列出全局模板 (scope=global, is_template=true) |
| `/api/agents/from-template/{template_id}` | POST | `skills:write:personal` | 从模板复制创建 Agent |
| `/api/agents/stats` | GET | - | 统计 (total, by_scope) |
| `/api/agents/{agent_id}` | GET | - | 获取 Agent (含关联 skills/rules/knowledge) |
| `/api/agents/{agent_id}` | PUT | `skills:write:personal` | 更新 Agent |
| `/api/agents/{agent_id}` | DELETE | `skills:write:personal` | 软删除 Agent |

### Agent Context

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/agents/{agent_id}/context` | GET | - | 获取 Agent 完整上下文 (含父 Agent 继承的 instructions + rules) |

Context 继承逻辑:
1. 收集本 Agent 的 skills, rules, knowledge_bases
2. 沿 `parent_agent_id` 链向上遍历
3. 合并父 Agent 的 rules（去重）和 instructions（追加为前缀）
4. 循环检测: 跳过已访问的 agent_id

### 关联管理

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/agents/{agent_id}/link-skill` | POST | `skills:write:personal` | 绑定 Skill (skill_id 参数) |
| `/api/agents/{agent_id}/unlink-skill` | POST | `skills:write:personal` | 解绑 Skill |
| `/api/agents/{agent_id}/link-rule` | POST | `skills:write:personal` | 绑定 Rule (rule_id 参数) |
| `/api/agents/{agent_id}/unlink-rule` | POST | `skills:write:personal` | 解绑 Rule |
| `/api/agents/{agent_id}/link-knowledge` | POST | `skills:write:personal` | 绑定 KnowledgeBase (knowledge_base_id 参数) |
| `/api/agents/{agent_id}/unlink-knowledge` | POST | `skills:write:personal` | 解绑 KnowledgeBase |

## 模板机制

Agent 可作为模板（`is_template=true`, `scope=global`）供复制使用:

```
POST /api/agents/from-template/{template_id}
  → 复制 template 的 name, role, instructions, config
  → 复制所有关联的 skills, rules, knowledge_bases
  → 设置 scope 为 personal 或 project
  → 创建新 Agent 并返回
```

## Context 输出格式

`GET /api/agents/{agent_id}/context` 返回:

```json
{
    "instructions": "[Parent: P]\n...\n\n[Current: C]\n...",
    "role": "developer",
    "skills": [{"id": "...", "name": "...", "instruction": "..."}],
    "rules": [{"id": "...", "name": "...", "content": "...", "severity": "..."}],
    "knowledge": [{"id": "...", "name": "...", "description": "..."}]
}
```

## 数据关系图

```
aidp_agents ----< aidp_agent_skills >---- aidp_skills
aidp_agents ----< aidp_agent_rules >---- aidp_rules
aidp_agents ----< aidp_agent_knowledge >---- aidp_knowledge_bases
aidp_agents (parent)  --< aidp_agents (children, 自引用)
aidp_projects (1) ----< aidp_agents (N)
```