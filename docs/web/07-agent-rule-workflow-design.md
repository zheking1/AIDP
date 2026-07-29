# AIDP AI 编程平台架构设计 v2.0

> Agent · Rule · Workflow · 知识· 记忆 · 技能 · 资产
> 面向 AI 辅助软件全生命周期的统一平台

---

## 目录

1. [设计理念](#1-设计理念)
2. [核心概念与关系](#2-核心概念与关系)
3. [Agent 体系](#3-agent-体系)
4. [Rule 体系](#4-rule-体系)
5. [Workflow 体系](#5-workflow-体系)
6. [知识/文档体系](#6-知识文档体系)
7. [现有工具对照](#7-现有工具对照)
8. [数据模型总览](#8-数据模型总览)
9. [API 设计](#9-api-设计)
10. [AI 运行时上下文组装](#10-ai-运行时上下文组装)
11. [实现路线图](#11-实现路线图)

---

## 1. 设计理念

### 1.1 核心原则

- **Agent 是一等公民**：AI 编程以 Agent 为中心，所有工具为 Agent 服务
- **文档归知识库，决策归记忆，能力归技能，约束归规则，流程归工作流**
- **组合优于继承**：Agent 组合 Instructions + Skills + Rules + Knowledge
- **全生命周期覆盖**：从需求到部署，每个环节都有对应的工具和规范

### 1.2 AI 编程五层模型

```
┌─────────────────────────────────────────┐
│              Layer 5: 流程编排           │
│         Workflow（全流程自动化）          │
├─────────────────────────────────────────┤
│              Layer 4: Agent 层           │
│     Agent（ Instructions + Skills +      │
│           + Rules + Knowledge ）         │
├─────────────────────────────────────────┤
│   Layer 3: 行为定义   │  Layer 3': 知识   │
│  Skills（能力）       │  Knowledge（事实）│
│  Rules（约束）        │  Memory（经验）   │
│                       │  Assets（模板）   │
├───────────────────────┴─────────────────┤
│              Layer 2: 执行层             │
│        Sandbox（执行）· Quality（验证）    │
├─────────────────────────────────────────┤
│              Layer 1: 管理层             │
│    Project · User · Role · Permission   │
└─────────────────────────────────────────┘
```

---

## 2. 核心概念与关系

### 2.1 概念总览

| 概念 | 定义 | 类比 |
|------|------|------|
| **Agent** | AI 角色的完整定义，包含 instructions + skills + rules + knowledge | 员工工位手册 |
| **Instruction** | Agent 的角色描述、行为指引、思维方式 | 岗位职责 |
| **Skill** | Agent 可执行的原子能力 | 专业技能证书 |
| **Rule** | Agent 必须遵守的约束和边界 | 规章制度 |
| **Knowledge** | Agent 需要参考的事实性文档 | 参考书 |
| **Memory** | Agent 在项目中积累的经验和决策 | 工作笔记 |
| **Asset** | 可复用的代码片段和模板 | 工具包 |
| **Workflow** | 多 Agent 协作的流程定义 | SOP |
| **Project** | 一次软件项目的完整载体 | 项目文件夹 |

### 2.2 核心关系图

```
                    Project
                       │
                ┌──────┴──────┐
                │             │
             Agent(s)     Workflow(s)
             /  │  \          │
         Skill Rule Knowledge  steps[]
           /     │     \       └── step: { agent, condition, on_fail }
       category category category
          │        │        │
    [coding]  [security]  [prd/arch/plan]
    [deploy]  [style]     [research/report]
    [testing] [arch]
```

### 2.3 数据流（AI 编程时）

```
用户输入任务
     │
     ▼
┌─────────────┐
│  Workflow   │ ← 匹配流程（如有）
│  解析器     │
└──────┬──────┘
       │ 按步骤分派
       ▼
┌─────────────┐
│  Agent      │ ← 匹配 Agent
│  解析器     │
└──────┬──────┘
       │ 组装上下文
       ▼
┌─────────────────────┐
│  Context Assembler  │
│  ┌─────────────────┐│
│  │ instructions    ││ ← 角色定义
│  │ skills[]        ││ ← 可用能力
│  │ rules[]         ││ ← 必须遵守
│  │ knowledge[]     ││ ← 参考文档
│  │ memory[]        ││ ← 历史经验
│  │ assets[]        ││ ← 可复用模板
│  └─────────────────┘│
└──────────┬──────────┘
           │ 注入到 LLM
           ▼
    ┌──────────┐
    │  LLM     │
    │  Response│
    └──────────┘
           │
           ▼
    ┌──────────┐
    │ Sandbox  │ ← 执行代码（可选）
    │ Quality  │ ← 验证输出（可选）
    └──────────┘
           │
           ▼
    ┌──────────┐
    │ Memory   │ ← 记录决策/经验
    └──────────┘
```

---

## 3. Agent 体系

### 3.1 定义

Agent 是 AI 编程的最小角色单元。每个 Agent 包含：

```
Agent
├── name                  # 唯一名称
├── role                  # 角色标签（前端/后端/DevOps）
├── instructions          # 角色定义文本
├── project_id            # 所属项目（可选）
├── parent_agent_id       # 父 Agent（子Agent继承）
├── skills[]              # 关联的技能
├── rules[]               # 关联的规则
├── knowledge_bases[]     # 关联的知识库
├── assets[]              # 关联的资产
├── config               # exec_config, temperature, model 等
└── metadata             # 扩展属性
```

### 3.2 Agent 层级

```
Project Agent (默认)
├── Instructions: "你是全栈工程师，负责完整项目开发"
├── Skills: [代码生成, 测试编写, API设计]
├── Rules: [安全规则, 代码规范]
├── Knowledge: [项目PRD, 架构文档]
│
├── Subagent: 前端专家
│   ├── Inherits: Project Agent 的 Rules + Knowledge
│   ├── Instructions: "你专注 Vue3 + TailwindCSS"
│   └── Skills: [组件开发, 状态管理]
│
├── Subagent: 后端专家
│   ├── Inherits: Project Agent 的 Rules + Knowledge
│   ├── Instructions: "你专注 FastAPI + PostgreSQL"
│   └── Skills: [ORM设计, API开发]
│
└── Subagent: DevOps
    ├── Inherits: Project Agent 的 Rules
    ├── Instructions: "你负责 CI/CD 和部署"
    ├── Skills: [Docker, K8s, 监控]
    └── Knowledge: [运维手册]
```

### 3.3 继承规则

- 子 Agent **继承**父 Agent 的 Rules
- 子 Agent **继承**父 Agent 的 Knowledge（可追加）
- 子 Agent **不自动继承**父 Agent 的 Skills（按需分配）
- Instructions **完全覆盖**（子 Agent 用自己的 instructions + 父的作为上下文）

### 3.4 预置 Agent 模板

| 模板名称 | 适用场景 |
|---------|---------|
| 全栈工程师 | 完整项目开发 |
| 前端工程师 | 纯前端项目 |
| 后端工程师 | 纯后端/API 项目 |
| DevOps 工程师 | 部署/运维 |
| 代码审查员 | Code Review |
| 测试工程师 | 自动化测试 |
| 架构师 | 系统设计 |

### 3.5 Agent 生命周期

```
创建 → 配置 Instructions
     → 关联 Skills
     → 关联 Rules
     → 关联 Knowledge
     → 配置 Subagents
     → 激活 → 使用 → 停用/归档
```

---

## 4. Rule 体系

### 4.1 定义

Rule 是 Agent 必须遵守的约束条件。三层架构（同 Skills）：

| 层级 | 范围 | 维护者 |
|------|------|--------|
| global | 所有项目和用户 | 管理员 |
| personal | 当前用户的所有项目 | 个人 |
| project | 特定项目 | 项目成员 |

### 4.2 规则分类

| 分类 | 子类 | 示例 |
|------|------|------|
| **security** | code_injection | "禁止使用 eval() / exec()" |
| | secret_management | "密码必须通过环境变量传入" |
| | sql_injection | "所有 SQL 必须参数化" |
| | xss_prevention | "输出 HTML 必须转义" |
| | dependency | "禁止使用已知漏洞的依赖版本" |
| **code_style** | naming | "变量名必须 camelCase / snake_case" |
| | structure | "每个文件不超过 300 行" |
| | comment | "公开方法必须有 docstring" |
| | import | "禁止通配符 import" |
| **architecture** | layering | "Controller 不能直接调用 DAO" |
| | dependency | "模块 A 不能依赖模块 B" |
| | pattern | "必须使用 Repository 模式" |
| **testing** | coverage | "新代码测试覆盖率 ≥ 80%" |
| | naming | "测试方法名必须 test_xxx" |
| | structure | "每个测试类只测一个类" |
| **deployment** | docker | "必须使用多阶段构建" |
| | security_scan | "部署前必须通过安全扫描" |
| | canary | "生产环境必须灰度发布" |
| | rollback | "必须有回滚方案" |
| **business** | compliance | "GDPR 数据保护规范" |
| | logging | "所有操作必须记录审计日志" |
| | error_handling | "所有外部调用必须有超时和重试" |

### 4.3 Rule 模型

```python
Rule
├── name                   # 规则名称
├── description            # 规则描述
├── content                # 规则内容（自然语言描述）
├── category               # security / code_style / architecture / testing / deployment / business
├── severity               # critical / high / medium / low / info
├── scope                  # global / personal / project
├── pattern                # 可选：正则表达式（用于自动检测违规）
├── auto_fix               # 可选：自动修复方案
├── allowed_roles[]        # 允许的角色
├── tags[]                 # 标签
└── embedding              # 向量嵌入（用于语义匹配）
```

### 4.4 Rule 与 Skill 的区别

| 维度 | Skill | Rule |
|------|-------|------|
| 语义 | "怎么做" | "不准怎么做" |
| 匹配方式 | 语义相似度匹配 | 精确匹配 + 语义匹配 |
| 使用方式 | 注入到 AI 作为可用工具 | 注入到 AI 作为约束条件 |
| 违反后果 | 不可用 | 拦截/告警/降级 |
| 自动检测 | 不支持 | 支持（pattern 正则） |

---

## 5. Workflow 体系

### 5.1 定义

Workflow 是多步骤、多 Agent 协作的流程定义。每个步骤指定：

```
Workflow
├── name            # 流程名称
├── description     # 流程描述
├── category        # development / testing / deployment / review
├── trigger         # manual / webhook / schedule / event
├── variables[]     # 流程变量
├── steps[]         # 步骤列表
└── on_complete     # 完成时 hook
```

### 5.2 Step 模型

```python
Step
├── name              # 步骤名称
├── order             # 步骤序号
├── agent_id          # 执行的 Agent
├── skill_ids[]       # 本步骤使用的技能（覆盖 Agent 的默认技能）
├── rule_ids[]        # 本步骤应用的规则（追加到 Agent 的规则）
├── conditions        # 执行条件
│   ├── require_approval   # 是否需要人工审批
│   ├── required_checks[]  # 前置检查
│   └── skip_if            # 跳过条件
├── input             # 输入映射（从前序步骤获取变量）
├── output            # 输出定义（传递给后续步骤）
├── timeout           # 超时时间
├── on_success        # 成功处理
│   ├── next_step     # 下一步
│   └── notify[]      # 通知列表
├── on_fail           # 失败处理
│   ├── action        # stop / warn / retry / rollback
│   ├── retry_count   # 重试次数
│   ├── retry_delay   # 重试间隔
│   └── rollback_step # 回滚到哪个步骤
└── metadata          # 扩展属性
```

### 5.3 预置流程模板

| 流程 | 步骤 | 适用场景 |
|------|------|---------|
| 全栈开发 | 需求分析 → 架构设计 → 任务拆分 → 编码 → 测试 → Code Review → 部署 | 完整项目 |
| 前端开发 | 设计稿分析 → 组件拆分 → 编码 → 测试 → 构建 | 前端任务 |
| 后端 API 开发 | API 设计 → 模型设计 → 实现 → 测试 → 文档生成 | 后端任务 |
| Bug 修复 | 复现 → 定位 → 修复 → 测试 → Review → 部署 | Bug 处理 |
| 部署上线 | 构建 → 安全扫描 → 灰度 → 全量 → 监控 | 生产部署 |
| Code Review | 获取差异 → 静态分析 → 逐行审查 → 生成报告 | 代码审查 |
| 安全审计 | 依赖扫描 → 代码扫描 → 渗透测试 → 报告 | 安全审计 |

### 5.4 Workflow 执行

```
触发（手动/事件）
  │
  ▼
┌─────────────────────┐
│  Parse Workflow     │ ← 加载流程定义
│  Resolve Variables  │ ← 解析变量
└──────────┬──────────┘
           │
           ▼
    ┌─────────────┐     ┌─────────────┐
    │ Step 1      │────▶│ Approval    │──▶ 批准 → Step 2
    │ Run Agent A │     │ Gate       │    拒绝 → 终止
    └─────────────┘     └─────────────┘
           │
           ▼
    ┌─────────────┐
    │ Step 2      │
    │ Run Agent B │
    └──────┬──────┘
     失败  │  成功
     │     │
     ▼     ▼
  重试/回滚  Step 3...
```

### 5.5 Workflow 状态

```
draft → pending_approval → active
                              │
                    trigger ──┘
                              │
                              ▼
                     ┌──────────────┐
                     │  running     │
                     │  ├ step_1    │── 完成 → step_2
                     │  ├ step_2    │── 失败 → on_fail
                     │  └ ...       │
                     └──────┬───────┘
                            │
                    ┌───────┴────────┐
                    │                │
               completed          failed
                    │                │
                    ▼                ▼
               completed         failed
```

---

## 6. 知识/文档体系

### 6.1 文档分类（Knowledge 扩展）

现有知识库加 `category` 字段，覆盖全生命周期文档：

| Category | 子类型 | 用途 |
|----------|--------|------|
| **research** | market_report / competitor / user_survey | 市场调研 |
| **prd** | requirements / user_story / use_case | 需求文档 |
| **arch** | system_design / adr / data_model / api_spec | 架构设计 |
| **plan** | task_plan / sprint / milestone | 任务计划 |
| **dev** | coding_guide / api_doc / migration | 开发文档 |
| **test** | test_plan / test_case / test_report | 测试文档 |
| **ops** | deploy_guide / runbook / monitoring | 运维文档 |
| **meeting** | meeting_minutes / decision_log | 会议记录 |

### 6.2 文档模板（新增概念）

每种文档类型预置模板，Agent 生成文档时使用：

```
PRD 模板
├── 1. 背景与目标
├── 2. 用户故事
├── 3. 功能需求
├── 4. 非功能需求
├── 5. 验收标准
└── 6. 排期

ADR 模板
├── 1. 上下文
├── 2. 决策
├── 3. 备选方案
├── 4. 理由
└── 5. 影响
```

---

## 7. 现有工具对照

### 7.1 全景工具矩阵

```
                         ┌─────────────┐
                         │   Agent     │  ← NEW
                         │  管理层     │
                         └──────┬──────┘
                                │ 组合
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
   ┌────┴────┐          ┌──────┴──────┐          ┌─────┴─────┐
   │ 行为层   │          │   知识层     │          │  执行层    │
   ├─────────┤          ├─────────────┤          ├───────────┤
   │ Skill   │          │ Knowledge   │          │ Sandbox   │
   │ Rule    │ ← NEW    │ Memory      │          │ Quality   │
   │ Workflow│ ← NEW    │ Asset       │          │           │
   └─────────┘          └─────────────┘          └───────────┘
```

### 7.2 各工具变更清单

| 工具 | 变更 | 工作量 |
|------|------|--------|
| Knowledge | 加 `category` 字段 + 文档模板概念 | 小 |
| Memory | **不变**（`category: decision` 已有） | 无 |
| Skills | **不变**（已有三层架构） | 无 |
| Assets | **不变** | 无 |
| Sandbox | **不变** | 无 |
| Quality | **不变** | 无 |
| **Rules** | **新建模块**（三层：global/personal/project） | 中 |
| **Agent** | **新建模块**（组合 instructions/skills/rules/knowledge） | 大 |
| **Workflow** | **新建模块**（多步骤流程引擎） | 大 |
| Instructions | 从 project settings 提升为 Agent 的属性 | 小 |

---

## 8. 数据模型总览

### 8.1 新建表

```sql
-- Agent 定义
aidp_agents
├── id VARCHAR(36) PK
├── name VARCHAR(200) NOT NULL
├── role VARCHAR(100)          -- 角色标签
├── instructions TEXT          -- 角色定义
├── project_id INT FK         -- 所属项目（可选）
├── parent_agent_id VARCHAR(36) FK  -- 父 Agent
├── config TEXT (JSON)         -- exec_config, temperature, model
├── sort_order INT
├── is_active BOOLEAN
├── created_at / updated_at / deleted_at

-- Agent ↔ Skill 关联
aidp_agent_skills
├── agent_id VARCHAR(36) FK
├── skill_id VARCHAR(36) FK
├── PRIMARY KEY (agent_id, skill_id)

-- Agent ↔ Rule 关联
aidp_agent_rules
├── agent_id VARCHAR(36) FK
├── rule_id VARCHAR(36) FK
├── PRIMARY KEY (agent_id, rule_id)

-- Agent ↔ Knowledge 关联
aidp_agent_knowledge
├── agent_id VARCHAR(36) FK
├── knowledge_base_id VARCHAR(36) FK
├── PRIMARY KEY (agent_id, knowledge_base_id)

-- Rule 定义
aidp_rules
├── id VARCHAR(36) PK
├── name VARCHAR(200) NOT NULL
├── description TEXT
├── content TEXT NOT NULL
├── category VARCHAR(50) NOT NULL  -- security/style/architecture/testing/deployment/business
├── severity VARCHAR(20) NOT NULL  -- critical/high/medium/low/info
├── scope VARCHAR(20) NOT NULL     -- global/personal/project
├── pattern TEXT                    -- 正则表达式
├── auto_fix TEXT                   -- 自动修复方案
├── allowed_roles TEXT (JSON)
├── tags TEXT (JSON)
├── embedding TEXT                  -- 向量嵌入
├── project_id INT FK (scope=project)
├── user_id VARCHAR(100) (scope=personal)
├── access_count INT
├── is_active BOOLEAN
├── created_at / updated_at / deleted_at

-- Rule Group（分组）
aidp_rule_groups
├── id VARCHAR(36) PK
├── name VARCHAR(100) NOT NULL
├── description TEXT
├── scope VARCHAR(20)
├── parent_id VARCHAR(36) FK
├── sort_order INT
├── created_at / updated_at

-- Workflow 定义
aidp_workflows
├── id VARCHAR(36) PK
├── name VARCHAR(200) NOT NULL
├── description TEXT
├── category VARCHAR(50)           -- development/testing/deployment/review
├── trigger VARCHAR(50)            -- manual/webhook/schedule/event
├── trigger_config TEXT (JSON)     -- webhook URL, cron 表达式
├── variables TEXT (JSON)          -- 流程变量定义
├── project_id INT FK
├── is_active BOOLEAN
├── version INT
├── created_at / updated_at / deleted_at

-- Workflow Step
aidp_workflow_steps
├── id VARCHAR(36) PK
├── workflow_id VARCHAR(36) FK
├── name VARCHAR(200) NOT NULL
├── order INT NOT NULL
├── agent_id VARCHAR(36) FK
├── skill_ids TEXT (JSON)
├── rule_ids TEXT (JSON)
├── conditions TEXT (JSON)
├── input_mapping TEXT (JSON)
├── output_mapping TEXT (JSON)
├── timeout INT
├── on_success TEXT (JSON)
├── on_fail TEXT (JSON)
├── metadata TEXT (JSON)
├── created_at / updated_at

-- Workflow Execution（运行记录）
aidp_workflow_executions
├── id VARCHAR(36) PK
├── workflow_id VARCHAR(36) FK
├── status VARCHAR(20)             -- running/completed/failed/cancelled
├── trigger_type VARCHAR(50)
├── trigger_data TEXT (JSON)
├── current_step INT
├── variables TEXT (JSON)          -- 运行时变量
├── started_at / completed_at
├── created_at

-- Workflow Execution Step（步骤记录）
aidp_workflow_execution_steps
├── id VARCHAR(36) PK
├── execution_id VARCHAR(36) FK
├── step_id VARCHAR(36) FK
├── status VARCHAR(20)
├── started_at / completed_at
├── duration_ms INT
├── input TEXT (JSON)
├── output TEXT (JSON)
├── error TEXT
├── retry_count INT
```

### 8.2 知识库扩展

```sql
-- 知识库加 category 字段（已有模型上扩展）
ALTER TABLE aidp_knowledge_bases ADD COLUMN category VARCHAR(50) DEFAULT 'general';
-- general / research / prd / arch / plan / dev / test / ops / meeting

-- 文档模板
aidp_document_templates
├── id VARCHAR(36) PK
├── name VARCHAR(200) NOT NULL
├── category VARCHAR(50) NOT NULL
├── content TEXT NOT NULL          -- 模板内容（含 {{variable}} 占位符）
├── variables TEXT (JSON)          -- 变量定义
├── scope VARCHAR(20)              -- global / personal / project
├── project_id INT FK
├── created_at / updated_at
```

---

## 9. API 设计

### 9.1 Agent API

```
GET    /api/agents                  列表（可过滤 scope/project_id）
POST   /api/agents/create           创建
GET    /api/agents/{id}             详情（含关联的 skills/rules/knowledge）
PUT    /api/agents/{id}             更新
DELETE /api/agents/{id}             删除
POST   /api/agents/{id}/link-skill  关联技能
POST   /api/agents/{id}/link-rule   关联规则
POST   /api/agents/{id}/link-knowledge 关联知识库
POST   /api/agents/{id}/unlink-{type}  解除关联
GET    /api/agents/{id}/context     获取完整上下文（AI 注入用）
```

### 9.2 Rule API

```
GET    /api/rules/list              列表（可过滤 scope/category/severity）
POST   /api/rules/create            创建
GET    /api/rules/{id}              详情
PUT    /api/rules/{id}              更新
DELETE /api/rules/{id}              删除
POST   /api/rules/search            搜索
GET    /api/rules/stats             统计
GET    /api/rules/groups/list       分组列表
POST   /api/rules/groups/create     创建分组
DELETE /api/rules/groups/{id}       删除分组
```

### 9.3 Workflow API

```
GET    /api/workflows/list          列表
POST   /api/workflows/create        创建
GET    /api/workflows/{id}          详情（含 steps）
PUT    /api/workflows/{id}          更新
DELETE /api/workflows/{id}          删除
POST   /api/workflows/{id}/steps    添加步骤
PUT    /api/workflows/{id}/steps/{step_id}  更新步骤
DELETE /api/workflows/{id}/steps/{step_id}  删除步骤
POST   /api/workflows/{id}/execute  执行流程
GET    /api/workflows/executions    执行记录
GET    /api/workflows/executions/{id} 执行详情
POST   /api/workflows/executions/{id}/cancel 取消
```

---

## 10. AI 运行时上下文组装

### 10.1 Context Assembler

当 AI 需要处理任务时，`Context Assembler` 组装最终上下文：

```
Input: { project_id, task_description, workflow_step? }

1. 确定 Agent
   ├── 如果 workflow_step，使用 step.agent
   └── 否则 use project.default_agent

2. 合并 Instructions
   ├── agent.instructions
   ├── 如果有 parent: parent.instructions（作为背景）
   └── project.instructions（项目级补充）

3. 收集 Skills
   ├── agent.skills
   ├── 追加 project.skills（项目技能）
   └── 按 task_description 语义匹配 top_k

4. 收集 Rules
   ├── agent.rules
   ├── 继承 parent.rules（如有）
   ├── 追加 workflow_step.rules（临时追加）
   └── 按 task_description 语义匹配相关规则

5. 收集 Knowledge
   ├── agent.knowledge_bases
   ├── 继承 parent.knowledge（如有）
   ├── 追加 project.knowledge
   └── 按 task_description 语义检索 top_k 文档块

6. 收集 Memory
   └── 按 project_id 检索相关记忆

7. 收集 Assets（可选）
   └── 按语言/类型匹配相关资产

8. 组装最终 Context
   ┌──────────────────────────────────────┐
   │ SYSTEM_PROMPT = agent.instructions    │
   │ AVAILABLE_SKILLS = [技能列表]         │
   │ CONSTRAINTS = [规则列表]              │
   │ REFERENCES = [知识文档摘要]           │
   │ HISTORY = [相关记忆]                  │
   │ TEMPLATES = [相关资产]                │
   └──────────────────────────────────────┘
```

### 10.2 匹配策略

| 类型 | 匹配方式 | Top K |
|------|---------|-------|
| Skills | 向量语义匹配 + 标签过滤 | 10 |
| Rules | 精确匹配(scope) + 语义匹配 | 20 |
| Knowledge | 向量语义检索 | 5 |
| Memory | 向量语义检索 | 10 |
| Assets | 标签 + 语言匹配 | 5 |

---

## 11. 实现路线图

### Phase 1: Foundation（Week 1-2）

| 任务 | 产出 | 优先级 |
|------|------|--------|
| Rule 模块：模型 + API | `app/modules/rules/` | P0 |
| Rule 模块：前端页面 | `templates/modules/rules/` | P0 |
| Rule 分组管理 | 分组 CRUD | P0 |
| Knowledge 扩展 category | 迁移 + 前端筛选 | P1 |

### Phase 2: Agent（Week 3-4）

| 任务 | 产出 | 优先级 |
|------|------|--------|
| Agent 模型 | `aidp_agents` + 关联表 | P0 |
| Agent CRUD API | 完整 REST API | P0 |
| Agent 关联管理 | link/unlink skills/rules/knowledge | P0 |
| Agent 前端页面 | Agent 设计器 | P0 |
| Agent 继承实现 | parent_agent 合并逻辑 | P1 |
| Context Assembler | API 端点 `GET /agents/{id}/context` | P1 |

### Phase 3: Workflow（Week 5-6）

| 任务 | 产出 | 优先级 |
|------|------|--------|
| Workflow 模型 | `aidp_workflows` + `aidp_workflow_steps` | P0 |
| Workflow CRUD API | 完整 REST API | P0 |
| Workflow 前端页面 | 流程设计器 | P0 |
| Workflow 执行引擎 | step 执行 + 状态机 | P1 |
| 执行记录 + 回滚 | execution tracking | P1 |
| 预置流程模板 | 5+ 流程模板 | P1 |

### Phase 4: Integration（Week 7-8）

| 任务 | 产出 | 优先级 |
|------|------|--------|
| Context Assembler 集成 | 对接 SkillRouter | P0 |
| 文档模板系统 | 模板 CRUD + 渲染 | P1 |
| 菜单/导航更新 | 全局/项目菜单 | P1 |
| 集成测试 | E2E 流程测试 | P1 |
| 部署文档 | NAS 部署指南 | P2 |

---

## 附录

### A. 菜单结构（更新后）

```
知识中心              → knowledge/*
技能库                → skills/*
  ├ 全局技能          → /skills/global
  ├ 我的技能          → /skills/personal
  └ 项目技能          → /skills/project/{id} [项目]
记忆中心              → memory/*
代码资产              → assets/*
规 则 库              → rules/*              ← NEW
  ├ 全局规则          → /rules/global         ← NEW
  ├ 我的规则          → /rules/personal       ← NEW
  └ 项目规则          → /rules/project/{id}  ← NEW [项目]
开发工具              → sandbox / quality

── 当前项目 ──        [项目]
  ├ 项目仪表盘        → /project/{id}/dashboard
  ├ Agent 配置        → /project/{id}/agents  ← NEW
  ├ 项目知识          → /project/{id}/knowledge
  ├ 项目技能          → /skills/project/{id}
  ├ 项目规则          → /rules/project/{id}  ← NEW
  ├ 项目流程          → /project/{id}/workflows ← NEW
  └ 项目设置          → /project/{id}/settings

系统管理              → admin/*
  ├ 用户管理          → /admin/users
  ├ 项目管理          → /admin/projects
  ├ 全局技能          → /admin/skills
  ├ 全局规则          → /admin/rules          ← NEW
  ├ 流程模板          → /admin/workflows      ← NEW
  ├ 审计日志          → /admin/audit-logs
  └ 系统设置          → /admin/settings
```

### B. 文件命名规范

```
app/modules/
├── rules/
│   ├── __init__.py
│   ├── models.py
│   └── routes.py
├── agents/
│   ├── __init__.py
│   ├── models.py
│   └── routes.py
├── workflows/
│   ├── __init__.py
│   ├── models.py
│   └── routes.py

app/web/templates/modules/
├── rules/
│   ├── global.html
│   ├── personal.html
│   └── project.html
├── agents/
│   ├── list.html
│   └── designer.html
├── workflows/
│   ├── list.html
│   ├── designer.html
│   └── execution.html
```

### C. 数据库命名规范

- 所有表前缀 `aidp_`
- 关联表使用双主键 `(aidp_agents + aidp_skills)`
- 时间戳统一 `created_at` / `updated_at` / `deleted_at`
- JSON 字段统一 `TEXT` 类型 + Python `json.dumps/loads`

---

> 文档版本: 2.0
> 最后更新: 2026-07-11
> 状态: 设计稿，待评审