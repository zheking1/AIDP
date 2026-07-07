# AIDP V3 需求规格 — Instructions-First 分段上下文引擎

---

## 1. 业务目标

AIDP 定位为 **AI 编程基础设施平台**。用户在 AIDP 中提前配置好所有 Agent 所需的 Instructions、Rules、Skills、Documents、Memories、Code Assets。当用户向 Agent 提出开发任务时，AIDP 自动完成：

1. **加载 Agent Instructions**（Agent 的身份、职责、约束）
2. **分析用户意图**（做什么？涉及哪些模块？）
3. **分段检索上下文**（不盲目全量检索，按需收敛）
4. **匹配技能和规则**（精确匹配，不污染上下文）
5. **组装最终 context**（含 subagent instructions，如需要）
6. **返回给 Agent**（Agent 带上下文执行开发）

核心价值：**用户只管提需求，AIDP 自动组装最优上下文。**

---

## 2. 架构原则

### 2.1 Instructions-First

```
传统方案（错误）:
  Task → 检索全部知识/技能/代码 → 组装 → Agent
          ↑ 盲目检索，不懂 Agent 是谁

本方案（正确）:
  Task → 加载 Instructions → Instructions 驱动检索 → 组装 → Agent
          ↑ Instructions 定义检索什么、不检索什么
```

### 2.2 Staged Pipeline（分段批处理）

```
Stage 0: 加载 Instructions    — Controller
Stage 1: 意图分析 + 规则筛选   — skill-router + 模型库模型
Stage 2: 分段知识检索          — context-optimizer
Stage 3: 技能匹配              — skill-router
Stage 4: 上下文组装            — context-optimizer
```

每一阶段都是"过滤器"：输入 > 输出，信息量逐级收敛。

### 2.3 模型库共享

所有 AIDP 工具需要模型能力（意图分析、检索排序、结果摘要）时，都从统一的 **模型库** 获取模型实例，不各自集成。

| 工具 | 需要的模型能力 | 使用场景 |
|------|---------------|---------|
| skill-router | 意图分析、重排序 | Stage 1 意图分析、技能匹配 |
| context-optimizer | 意图分析、摘要 | Stage 1 意图分析、Stage 4 结果精简 |
| knowledge-tool | Embedding | 语义搜索 |
| code-index | Embedding（可选） | 语义代码搜索 |

**模型库由用户自行配置**（后续开发）。当前开发以"调用模型库接口"为约定，不依赖具体模型实现。

---

## 3. Staged Pipeline 详细规格

### 3.1 Stage 0: Agent Instructions 加载

| 项目 | 说明 |
|------|------|
| **负责工具** | Controller |
| **输入** | agent_type ("main" / 具体 subagent type)、project_name |
| **处理** | 从 `agent_instructions` 表查询对应 agent_type 的 instructions 文本 |
| **输出** | `{ agent_type, role, constraints, tool_preferences, rules }` 约 500 tokens |
| **作用** | 不被直接传给 Agent。作为 Stage 1 意图分析模型的 system prompt 和角色上下文 |
| **收敛** | 50 条 rules → 不下发，仅作为 Stage 1 的约束条件 |

#### 数据模型

```yaml
agent_instructions:
  id: int
  project_id: int
  agent_type: str           # "main" / "subagent:sandbox" / "subagent:deploy" / ...
  role: str                 # "你是一个全栈 Python 开发者..."
  constraints: json         # { "max_files_per_change": 3, "preferred_tools": [...] }
  rules: json               # [{ id, category, content, priority }]
  created_at: datetime
  updated_at: datetime
```

### 3.2 Stage 1: 意图分析 + 规则筛选

| 项目 | 说明 |
|------|------|
| **负责工具** | skill-router（调用模型库的意图分析模型） |
| **输入** | `task`（用户任务描述）+ `instructions`（Stage 0 输出的角色定义和约束，不含完整 rules） |
| **模型** | 从模型库获取意图分析模型（小模型，快速） |
| **输出** | 结构化意图 JSON，约 300 tokens |

#### 输出结构

```json
{
  "intent": {
    "primary": "new_feature",       // new_feature / bugfix / optimize / understand / refactor
    "secondary": "code_generation",
    "domain": "sandbox-tool",
    "complexity": "medium",
    "is_compound": false
  },
  "entities": {
    "modules": ["execution_service.py", "SUPPORTED_LANGUAGES"],
    "concepts": ["Node.js", "subprocess", "sandbox"],
    "keywords": ["Node.js", "runtime", "language support"]
  },
  "relevant_rules": [               // 从 instructions.rules 中筛选出的相关规则 ID
    "rule_sandbox_lang_pattern",
    "rule_code_quality_check"
  ],
  "required_tools": [               // 需要哪些工具参与检索
    "code-index",
    "memory-tool",
    "knowledge-tool"
  ],
  "search_queries": {               // 各工具的检索查询
    "code-index": ["execution_service.py", "SUPPORTED_LANGUAGES"],
    "memory-tool": ["sandbox 架构", "语言支持模式"],
    "knowledge-tool": ["Node.js child_process", "Docker sandbox"]
  },
  "budget_hints": {
    "total": 6000,
    "code-index": 2500,
    "memory-tool": 1500,
    "knowledge-tool": 2000
  }
}
```

#### 约束

- 意图分析模型**只接收角色定义和约束**，不接收完整 rules 列表（避免 50 条 rules 撑爆模型输入）
- 输出必须包含 `required_tools`，明确哪些工具参与检索
- `search_queries` 不是原始 task 照搬，而是分析后的**精准查询**

### 3.3 Stage 2: 分段知识检索

| 项目 | 说明 |
|------|------|
| **负责工具** | context-optimizer |
| **输入** | Stage 1 的输出（`required_tools`、`search_queries`、`budget_hints`） |
| **处理** | 根据 `required_tools` 并行调用对应工具，使用 `search_queries` 中的查询词 |
| **输出** | 各工具返回的检索结果，按 budget 裁剪 |

#### 调用规则

```text
if "memory-tool" in required_tools:
    memory.search(project=project_name, query=search_queries["memory-tool"], limit=5)

if "knowledge-tool" in required_tools:
    knowledge.search(query=search_queries["knowledge-tool"], top_k=5)

if "code-index" in required_tools:
    code-index.search(symbols=entities["modules"])          # 精确查代码
    code-index.explore(function="execution_service.py")     # 调用链

if "asset-tool" in required_tools:   # 仅在需要代码模板时
    asset.search(query=search_queries["asset-tool"], top_k=3)
```

#### 约束

- 并行调用，不串行等待
- 每个工具的返回量由 `budget_hints` 限制
- 不做工具内二次分析（那是工具自己的事）
- 如果某个工具不存在或无结果，静默跳过

### 3.4 Stage 3: 技能匹配

| 项目 | 说明 |
|------|------|
| **负责工具** | skill-router |
| **输入** | `task` + Stage 2 检索到的主要知识领域 |
| **处理** | 调用 skill-router 的 `resolve` 能力，根据 task 和已知知识域匹配技能 |
| **输出** | 1-3 个最匹配技能，各含 instructions 文本 |

#### 为什么在 Stage 3 而非 Stage 1？

- Stage 1 只知道"用户要做什么"，不知道"项目里有什么"
- Stage 2 检索后，已明确涉及的模块、概念
- 此时匹配技能**更精准**：从 20 个候选收敛到 2 个

#### 输出

```json
{
  "matched_skills": [
    {
      "name": "新功能开发技能",
      "description": "为工具模块添加新功能的标准流程",
      "instruction": "1. 阅读现有类似实现... 2. 遵循模块模式...",
      "project_instruction": "AIDP 工具必须实现 /tool/manifest, /tool/capabilities, /tool/invoke",
      "score": 0.92
    }
  ]
}
```

### 3.5 Stage 4: 上下文组装 + Subagent 指令生成

| 项目 | 说明 |
|------|------|
| **负责工具** | context-optimizer |
| **输入** | Stage 0-3 的全部输出 |
| **处理** | 去重 → 优先级排序 → 摘要压缩 → 组装为最终 context package |
| **输出** | `{ instructions, context, skills, subagent? }` 约 2000-3000 tokens |

#### 组装策略

```text
优先级排序:
  1. Instructions 中的约束 (Stage 0)         — 最高优先级
  2. 关键代码结构 (Stage 2 code-index)        — 直接涉及的文件
  3. 匹配的技能指令 (Stage 3)                  — 执行指导
  4. 相关知识文档 (Stage 2 knowledge-tool)     — 参考信息
  5. 历史经验 (Stage 2 memory-tool)            — 辅助参考

压缩策略:
  - 代码片段的注释和空行可省略
  - 文档摘要到 200 字/篇
  - 记忆内容只保留关键决策记录
  - 技能指令不压缩（核心执行指导）
```

#### Subagent 指令生成

当任务需要拆分为 subagent 时，Stage 4 输出中包含 `subagent_instructions`：

```json
{
  "needs_subagent": true,
  "subagent": {
    "agent_type": "subagent:sandbox-tool",
    "instructions": {
      "role": "你是 sandbox-tool 模块的专属开发者",
      "task": "为 sandbox-tool 添加 Node.js 运行时支持",
      "context": {
        "relevant_files": ["app/services/execution_service.py"],
        "patterns": ["参考现有的 Python/Bash SUPPORTED_LANGUAGES 实现"],
        "constraints": ["保持与现有代码风格一致", "必须添加单元测试"]
      },
      "allowed_tools": ["code-index", "sandbox-tool", "quality-tool"],
      "forbidden_tools": ["knowledge-tool", "memory-tool"]
    }
  }
}
```

---

## 4. Subagent 生命周期

### 4.1 Subagent 遵循相同的分段流程

```text
Main Agent 创建 Subagent
  → Subagent 启动时:
      Stage 0: 加载 Subagent Instructions（Main Agent 在 Stage 4 生成）
      Stage 1: 意图分析（更窄范围，只看 subagent 的 task）
      Stage 2: 知识检索（只检索 allowed_tools）
      Stage 3: 技能匹配（限于 subagent 的领域）
      Stage 4: 子上下文组装（更精简，≤ 1500 tokens）
  → Subagent 执行任务
  → Subagent 返回结果给 Main Agent
  → Main Agent 验证 + 归档
```

### 4.2 Subagent Instructions 数据流

```
Main Agent Stage 4:
  instruction_assembler.generate_subagent_instructions(
    task="添加 Node.js 支持",          ← 用户任务子集
    parent_instructions=main_agent,     ← 主 Agent 的 instructions
    domain="sandbox-tool",              ← Stage 1 分析的领域
    context=stage2_results,             ← Stage 2 检索的上下文
    skills=stage3_results               ← Stage 3 匹配的技能
  )
  → 输出: subagent_instructions (JSON)
  → Agent 用这个 JSON 作为 subagent 的 system prompt
```

---

## 5. 上下文预算模型

### 5.1 Token 预算约束

| 阶段 | 最大输入 | 最大输出 | 说明 |
|------|---------|---------|------|
| Stage 0 | N/A | 500 tokens | Instructions 文本 |
| Stage 1 | 600 tokens | 300 tokens | 意图分析模型输入输出 |
| Stage 2 | 300 tokens | 4000 tokens | 工具检索原始结果（未压缩） |
| Stage 3 | 500 tokens | 300 tokens | 技能匹配 |
| Stage 4 | 5000 tokens | 3000 tokens | 最终 context package |

### 5.2 收敛曲线

```
Stage 0:  5000t (全部 instructions)
   │  筛选后 → 500t (只取角色定义和约束)
Stage 1:  600t (task + role)
   │  分析后 → 300t (结构化意图)
Stage 2:  300t (意图 queries)
   │  检索后 → 4000t (原始结果)
Stage 3:  500t (task + 知识域)
   │  匹配后 → 300t (技能列表)
Stage 4:  5000t (全部输入)
   │  精简后 → 3000t (最终 context) → Agent
```

---

## 6. 模型库接口约定（V3 不实现，仅定义接口）

```python
# 模型库的统一调用接口（后续开发）
class ModelLibrary:
    async def get_model(self, purpose: str) -> Model:
        """
        purpose: "intent_analysis" | "embedding" | "reranking" | "summarization"
        返回对应用途的模型实例
        """

class Model:
    async def generate(self, prompt: str, max_tokens: int = 200) -> str:
        """调用模型生成文本"""
```

各工具调用方式：
```python
model = await model_library.get_model("intent_analysis")
result = await model.generate(prompt, max_tokens=200)
```

---

## 7. API 设计

### 7.1 MCP Tools（Controller 暴露给 Agent）

| Tool | 输入 | 输出 | 说明 |
|------|------|------|------|
| `aidp_init` | project_name, description, tech_stack, architecture_summary, docs, key_files | project_id + 步骤摘要 | 项目初始化（已有，需修 bug） |
| `aidp_context` | project_name, task, agent_type | 完整 context package | Instructions-First 分段上下文（重构） |
| `aidp_instructions` | project_name, agent_type, task | subagent instructions JSON | 为创建 subagent 生成专属 instructions |

### 7.2 内部 API（工具间调用）

| 端点 | 工具 | 说明 |
|------|------|------|
| `POST /api/analyze-intent` | skill-router | Stage 1: 意图分析 |
| `POST /api/resolve` | skill-router | Stage 3: 技能匹配 |
| `POST /api/staged-retrieve` | context-optimizer | Stage 2: 分段检索 |
| `POST /api/assemble-context` | context-optimizer | Stage 4: 上下文组装 |
| `POST /api/assemble-subagent` | context-optimizer | Stage 4: Subagent 指令生成 |

---

## 8. 验收标准

### 8.1 Stage 0

- [ ] Controller 能根据 agent_type 从数据库加载 instructions
- [ ] instructions 包含 role、constraints、rules 字段
- [ ] API 支持 CRUD agent instructions

### 8.2 Stage 1

- [ ] 意图分析模型能识别 new_feature / bugfix / optimize / understand / refactor 五种意图
- [ ] 能提取关键实体（模块名、函数名、概念词）
- [ ] 能根据 intent 推荐 required_tools 并生成 search_queries
- [ ] 能识别 compound intent（复合任务）

### 8.3 Stage 2

- [ ] 根据 required_tools 并行调用对应工具
- [ ] 结果按 budget_hints 限制返回量
- [ ] 工具不存在或无结果时静默跳过

### 8.4 Stage 3

- [ ] 在知识检索后进行技能匹配
- [ ] 匹配结果附带 instruction 和 project_instruction
- [ ] 2-3 个最匹配技能

### 8.5 Stage 4

- [ ] 上下文去重、优先级排序生效
- [ ] 最终 context ≤ 3000 tokens
- [ ] Subagent instructions 包含 role、task、context、allowed_tools
- [ ] Subagent instructions 可被 Agent 直接用作 subagent 的 system prompt