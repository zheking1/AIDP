# AIDP V3 开发计划 — Instructions-First 分段上下文引擎

---

## 开发阶段总览

| Phase | 内容 | 优先级 | 状态 |
|-------|------|--------|------|
| **Phase 1** | 修复现有断链 | P0 | ✅ 完成 |
| **Phase 2** | Agent Instructions 存储与加载 | P0 | ✅ 完成 |
| **Phase 3** | 意图分析扩展 | P0 | ✅ 完成 |
| **Phase 4** | 分段检索管线 | P0 | ✅ 完成 |
| **Phase 5** | 上下文组装 + Subagent 指令生成 | P0 | ✅ 完成 |
| **Phase 6** | MCP 集成 | P0 | ✅ 完成 |
| **Phase 7** | 部署与测试 | P1 | ✅ 完成 |

---

## Phase 1: 修复现有断链

> 目标：确保现有工具的基础功能可用，为后续分段管线提供可靠的底层能力。

### 1.1 修复 aidp_init 两个 bug

**文件**: `apps/controller/app/services/project_init_service.py`

| Bug | 当前代码 | 修复后 |
|-----|---------|--------|
| Doc 导入传错参数 | `invoke_tool("knowledge-tool", "document.index", {"document_id":..., "project_id":...})` | 改为直接调用 knowledge-tool 的 HTTP API POST `/api/documents`，或修正确保 content 正确传入 |
| Asset 注册用了 search 而非 create | `invoke_tool("asset-tool", "asset.search", {...})` | 改为 `invoke_tool("asset-tool", "asset.create", {...})` |

### 1.2 修复 context-optimizer 工具调用管线

**文件**: `tools/context-optimizer/app/api/optimize.py`

当前 `POST /api/tools/{tool}/invoke` 返回 `{"results": []}` —— 空壳。

**修复**：通过 HTTP 客户端真实调用对应工具（如 knowledge-tool:18081、code-index:18086 等）获取数据。

**文件**: `tools/context-optimizer/app/services/adaptive_budget.py`

修复 `json` 导入放在文件顶部（当前放在底部 `_llm_enhance` 方法中，导致运行时 NameError）。

### 1.3 修复 code-index Edge 图

**文件**: `tools/code-index/app/services/indexer.py`

当前 `Indexer` 只创建 `Node` 记录（文件、类、函数），从不创建 `Edge` 记录。

**修复**：在索引过程中：
- 解析类继承关系 → 创建 `EXTENDS` edge
- 解析函数调用关系 → 创建 `CALLS` edge  
- 解析文件导入关系 → 创建 `IMPORTS` edge

**影响**：修复后 `CallTracer` 和 `ImpactAnalyzer` 能返回真实数据。

### 1.4 修复 context-optimizer 去重 bug

**文件**: `tools/context-optimizer/app/services/context_tracker.py`

当前 `is_duplicate` 用 `content[:50]` 作为字典 key，不是 session_id。改为用 session_id 索引。

---

## Phase 2: Agent Instructions 存储与加载 (Stage 0)

### 2.1 新增数据模型

**文件**: `apps/controller/app/db/models.py`

```python
class AgentInstruction(Base):
    __tablename__ = "agent_instructions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer)
    agent_type = Column(String(100))        # "main" / "subagent:sandbox" / ...
    role = Column(Text)                     # 角色定义
    constraints = Column(JSON)              # 工具偏好、文件作用域
    rules = Column(JSON)                    # [{id, category, content, priority}]
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

**文件**: `apps/controller/app/db/init_db.py`

添加 `agent_instructions` 表的自动创建逻辑。

### 2.2 新增 API

**文件**: `apps/controller/app/api/instructions.py`（新建）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/instructions` | 创建/更新 Agent instructions |
| GET | `/api/instructions?project_id=X&agent_type=main` | 获取指定 Agent 的 instructions |
| GET | `/api/instructions/list?project_id=X` | 列出项目的所有 Agent instructions |
| DELETE | `/api/instructions/{id}` | 删除 |

### 2.3 Stage 0 加载逻辑

**文件**: `apps/controller/app/services/project_init_service.py`

新增函数：
```python
async def load_agent_instructions(project_name: str, agent_type: str) -> dict:
    """Stage 0: 从数据库加载 Agent Instructions"""
```

返回结构：
```json
{
  "agent_type": "main",
  "role": "全栈 Python 开发者",
  "constraints": { "preferred_tools": ["quality-tool", "sandbox-tool"] },
  "rules": [
    { "id": "r1", "category": "coding", "content": "修改代码前先运行 quality-check", "priority": 10 },
    ...
  ]
}
```

---

## Phase 3: 意图分析扩展 (Stage 1)

### 3.1 skill-router 扩展

**文件**: `tools/skill-router/app/services/classification_service.py`

扩展 `analyze_intent` 方法，新增输出字段：

```python
async def analyze_intent(task: str, instructions: dict) -> dict:
    """
    现有: { intent, entities, domain, complexity }
    新增: { required_tools, search_queries, relevant_rules, budget_hints }
    """
```

**模型来源**：从模型库获取 `"intent_analysis"` 模型。

```python
model = await ModelLibrary.get_model("intent_analysis")
```

### 3.2 意图分析 API

**文件**: `tools/skill-router/app/api/tool.py`（已有 tool 协议端点）

新增 capability：
```python
{
    "name": "analyze_intent",
    "description": "Analyze user task intent and identify required tools, queries, and relevant rules.",
    "permission": "skill:resolve",
    "endpoint": "POST /api/analyze-intent",
    "timeout_ms": 3000,
    "input_schema": {
        "type": "object",
        "required": ["task"],
        "properties": {
            "task": {"type": "string"},
            "instructions": {"type": "object"}
        }
    }
}
```

### 3.3 Prompt 优化

意图分析模型的 prompt 只包含 instructions 的 `role` 和 `constraints`，不包含完整 `rules` 列表：

```
你是 {instructions.role}。
你的约束: {instructions.constraints}。

分析以下用户任务，返回 JSON：
{ "intent": {...}, "entities": {...}, "required_tools": [...], "search_queries": {...}, "relevant_rules": [...], "budget_hints": {...} }
```

---

## Phase 4: 分段检索管线 (Stage 2)

### 4.1 StagedRetriever 服务

**文件**: `tools/context-optimizer/app/services/staged_retriever.py`（新建）

```python
class StagedRetriever:
    def __init__(self):
        self.tool_endpoints = {
            "memory-tool": "http://127.0.0.1:18085",
            "knowledge-tool": "http://127.0.0.1:18081",
            "code-index": "http://127.0.0.1:18086",
            "asset-tool": "http://127.0.0.1:18082",
        }

    async def retrieve(self, required_tools: list, search_queries: dict, budget_hints: dict) -> dict:
        """Stage 2: 根据 Stage 1 的输出并行调用各工具"""
```

调用方式：
```python
tasks = []
if "memory-tool" in required_tools:
    tasks.append(self._call_tool("memory-tool", "memory.search", queries, budget))
if "knowledge-tool" in required_tools:
    tasks.append(self._call_tool("knowledge-tool", "knowledge.search", queries, budget))
...
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 4.2 更新 tool invoker 端点

**文件**: `tools/context-optimizer/app/api/optimize.py`

重写 `/api/tools/{tool}/invoke` 端点，从空壳改为真实调用：

```python
@router.post("/api/staged-retrieve")
async def staged_retrieve(request: StagedRetrieveRequest):
    """Stage 2: 分段检索"""
    retriever = StagedRetriever()
    results = await retriever.retrieve(
        request.required_tools,
        request.search_queries,
        request.budget_hints,
    )
    return results
```

---

## Phase 5: 上下文组装 (Stage 3-4)

### 5.1 技能匹配集成到 context-optimizer

**文件**: `tools/context-optimizer/app/services/skill_matcher.py`（新建）

```python
class SkillMatcher:
    async def match(self, task: str, domain: str, knowledge_context: dict) -> list:
        """Stage 3: 调用 skill-router 匹配技能"""
        # POST http://127.0.0.1:8788/tool/invoke
        # { capability: "resolve_task", input: { task, ... } }
```

### 5.2 ContextAssembler 服务

**文件**: `tools/context-optimizer/app/services/context_assembler.py`（新建）

```python
class ContextAssembler:
    def __init__(self):
        self.max_context_tokens = 3000
        self.priority_order = [
            "instructions",       # 最高优先级
            "code_index",
            "skills",
            "knowledge",
            "memories",
        ]

    async def assemble(self, stage0, stage1, stage2, stage3) -> dict:
        """Stage 4: 组装最终 context package"""
        # 1. 去重
        # 2. 按优先级排序
        # 3. LLM 摘要（调用模型库 summarization 模型）
        # 4. Token 计数和裁剪
        # 5. 组装为 Agent 可用的 format
```

### 5.3 InstructionAssembler 服务

**文件**: `tools/context-optimizer/app/services/instruction_assembler.py`（新建）

```python
class InstructionAssembler:
    async def generate_subagent_instructions(
        self,
        task: str,
        parent_instructions: dict,
        domain: str,
        context: dict,
        skills: list,
    ) -> dict:
        """Stage 4: 生成 Subagent 专属 Instructions"""

    async def build_agent_context(
        self,
        instructions: dict,
        intent: dict,
        results: dict,
        skills: list,
    ) -> dict:
        """组装给 Agent 的完整 context package"""
```

### 5.4 context-optimizer API 新增

**文件**: `tools/context-optimizer/app/api/optimize.py`

```python
@router.post("/api/assemble-context")
async def assemble_context(request: AssembleRequest):
    """Stage 4: 组装最终上下文"""

@router.post("/api/assemble-subagent")
async def assemble_subagent(request: SubagentRequest):
    """Stage 4: 生成 Subagent Instructions"""
```

---

## Phase 6: MCP 集成

### 6.1 aidp_context 重构

**文件**: `apps/controller/app/mcp/server.py`

当前 `aidp_context` 手动并行调用 4 个工具，改为调用 context-optimizer 的分段管线：

```python
@mcp.tool()
async def aidp_context(project_name: str, task: str = "", agent_type: str = "main") -> str:
    """Instructions-First 分段上下文引擎"""
    # Stage 0: 加载 Instructions
    instructions = await load_agent_instructions(project_name, agent_type)

    # Stage 1: 意图分析
    intent = await call_skillrouter_analyze_intent(task, instructions)

    # Stage 2: 分段检索
    results = await call_context_optimizer_staged_retrieve(intent)

    # Stage 3: 技能匹配
    skills = await call_skillrouter_resolve(task, intent.get("domain"))

    # Stage 4: 上下文组装
    context = await call_context_optimizer_assemble(instructions, intent, results, skills)

    return json.dumps(context, indent=2)
```

### 6.2 aidp_instructions 新增

**文件**: `apps/controller/app/mcp/server.py`

```python
@mcp.tool()
async def aidp_instructions(project_name: str, agent_type: str, task: str = "") -> str:
    """为创建 Subagent 生成专属 Instructions。

    Agent 使用此工具时流程：
    1. 调用 aidp_instructions 获取 subagent 配置
    2. 用返回的 instructions 创建 subagent
    3. Subagent 执行任务时也会调用 aidp_context 加载自己的上下文
    """
    # 加载主 Agent instructions
    main_instructions = await load_agent_instructions(project_name, "main")

    # Stage 1: 意图分析
    intent = await call_skillrouter_analyze_intent(task, main_instructions)

    # Stage 2: 检索
    results = await call_context_optimizer_staged_retrieve(intent)

    # Stage 3: 技能匹配
    skills = await call_skillrouter_resolve(task, intent.get("domain"))

    # Stage 4: 生成 subagent instructions
    subagent = await call_context_optimizer_assemble_subagent(
        task=task,
        parent_instructions=main_instructions,
        domain=intent.get("domain", ""),
        context=results,
        skills=skills,
    )

    return json.dumps(subagent, indent=2)
```

---

## Phase 7: 部署与测试

### 7.1 部署流程

```bash
# Phase 2-5 涉及的工具需要重新构建 Docker 镜像并推到 NAS
# controller:     apps/controller/
# skill-router:   tools/skill-router/
# context-optimizer: tools/context-optimizer/
# code-index:     tools/code-index/

# 部署命令（每次修改后执行）
powershell deploy/deploy-nas.ps1
# 或手动:
# 1. tar + scp 源码到 NAS
# 2. docker build --no-cache on NAS
# 3. docker restart
```

### 7.2 测试场景

| 场景 | 输入 | 预期输出 |
|------|------|---------|
| **单文件修改** | "修复 sandbox-tool 的 tool.py bug" | Stage 1: intent=bugfix, tools=[code-index,quality]; Stage 2: 只返回 tool.py；Stage 4: context ≤ 800 tokens |
| **新功能开发** | "为 sandbox-tool 添加 Node.js 支持" | Stage 1: intent=new_feature, tools=[code-index,memory,knowledge]; Stage 4: context ≤ 2000 tokens |
| **Subagent 生成** | aidp_instructions("sandbox-tool", task) | 返回完整的 subagent instructions JSON，含 role/task/context/allowed_tools |
| **Subagent 执行** | aidp_context("aidp", task, "subagent:sandbox") | 只检索 sandbox 相关内容，不加载无关工具 |

### 7.3 验收清单

- [ ] `aidp_init` bug 修复后，doc 和 asset 正确导入
- [ ] code-index Edge 图修复后，调用链返回真实数据
- [ ] context-optimizer 工具调用管线返回真实结果
- [ ] Agent instructions CRUD API 可用
- [ ] `aidp_context` 走完整 Staged Pipeline
- [ ] `aidp_instructions` 返回合法的 subagent instructions JSON
- [ ] 分段检索确实减少了返回量（对比修复前的全量检索）
- [ ] 模型库接口在代码中使用，但实现由用户后续配置

---

## 文件清单总览

### 新建文件

| # | 文件 | Phase | 说明 |
|---|------|-------|------|
| 1 | `apps/controller/app/api/instructions.py` | Phase 2 | Agent Instructions CRUD API |
| 2 | `apps/controller/app/models/instructions.py` | Phase 2 | AgentInstruction ORM 模型 |
| 3 | `tools/context-optimizer/app/services/staged_retriever.py` | Phase 4 | Stage 2 分段检索器 |
| 4 | `tools/context-optimizer/app/services/skill_matcher.py` | Phase 5 | Stage 3 技能匹配代理 |
| 5 | `tools/context-optimizer/app/services/context_assembler.py` | Phase 5 | Stage 4 上下文组装器 |
| 6 | `tools/context-optimizer/app/services/instruction_assembler.py` | Phase 5 | Subagent 指令生成器 |

### 修改文件

| # | 文件 | Phase | 改动 |
|---|------|-------|------|
| 7 | `apps/controller/app/services/project_init_service.py` | Phase 1 | 修复 2 个 bug + 新增 `load_agent_instructions` |
| 8 | `apps/controller/app/mcp/server.py` | Phase 6 | 重构 `aidp_context` + 新增 `aidp_instructions` |
| 9 | `apps/controller/app/db/models.py` | Phase 2 | 新增 AgentInstruction 模型 |
| 10 | `apps/controller/app/db/init_db.py` | Phase 2 | 自动创建 agent_instructions 表 |
| 11 | `apps/controller/app/main.py` | Phase 2 | 注册 instructions API 路由 |
| 12 | `tools/context-optimizer/app/api/optimize.py` | Phase 4-5 | 重写工具调用端点 + 新增 assemble API |
| 13 | `tools/context-optimizer/app/services/adaptive_budget.py` | Phase 1 | 修复 json import 位置 |
| 14 | `tools/context-optimizer/app/services/context_tracker.py` | Phase 1 | 修复去重索引 bug |
| 15 | `tools/code-index/app/services/indexer.py` | Phase 1 | 索引时创建 Edge 记录 |
| 16 | `tools/skill-router/app/api/tool.py` | Phase 3 | 新增 analyze_intent capability |
| 17 | `tools/skill-router/app/services/classification_service.py` | Phase 3 | 扩展 `analyze_intent` 输出 |

---

## 模型库约定

本开发计划中所有模型调用使用统一接口约定：

```python
# 约定：后续由用户实现的模型库接口
async def get_model(purpose: str) -> 'Model':
    """从模型库获取指定用途的模型"""

class Model:
    async def generate(self, prompt: str, max_tokens: int = 200) -> str:
        """调用模型生成"""
```

各工具按需调用：
```python
model = await get_model("intent_analysis")      # Stage 1
result = await model.generate(prompt, max_tokens=300)

model = await get_model("summarization")         # Stage 4
summary = await model.generate(content, max_tokens=200)
```

模型库的**具体实现**（模型选择、API Key 管理、负载均衡）由用户后续统一配置，不在本次开发范围内。