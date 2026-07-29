# 初始化自检机制 (Verify Flow)

## 概述

项目初始化完成后，可通过 Verify 端点逐项检查各初始化任务的执行结果。Verify 是一个只读检查，不触发任何新操作。

**源码**: `apps/controller/app/routers/projects_new.py:617-772`
**端点**: `GET /api/projects/{project_id}/verify`

## 检查项定义 (VERIFY_CHECKS)

```python
# app/routers/projects_new.py:617
VERIFY_CHECKS = [
    {"id": "code_index",    "name": "代码索引校验"},
    {"id": "doc_import",    "name": "文档导入校验"},
    {"id": "tech_analysis", "name": "技术栈分析校验"},
    {"id": "official_docs", "name": "官方文档校验"},
    {"id": "rules_extract", "name": "规则提取校验"},
    {"id": "agent_setup",   "name": "Agent 创建校验"},
    {"id": "mcp_register",  "name": "MCP 注册校验"},
]
```

## 各检查项详解

### 1. code_index - 代码索引校验

**检查内容**: code-index 的 SQLite 数据库中是否有该项目的代码节点。

1. 通过 httpx 访问 `http://localhost:18086/health` (timeout=3s)
2. 如果 code-index 健康检查通过，直接连接 SQLite:
   - `sqlite3.connect("/app/data/code_index.db", timeout=5)`
   - `SELECT COUNT(*) FROM nodes WHERE project_id=?`
3. 如果 code-index 不可达，catch 异常，ci_nodes = 0

**通过条件**: `ci_nodes > 0`

**严重级别**:
- `ci_nodes == 0` -> `"error"`
- `ci_nodes < 50` -> `"warn"`
- 其他 -> `"ok"`

### 2. doc_import - 文档导入校验

**检查内容**: `aidp_knowledge_documents` 表中是否有该项目的文档。

```sql
SELECT COUNT(*) FROM aidp_knowledge_documents
WHERE project_id = ? AND deleted_at IS NULL
```

**通过条件**: `kd_count > 0`
**严重级别**: `kd_count == 0` -> `"error"`, 否则 `"ok"`

### 3. tech_analysis - 技术栈分析校验

**检查内容**: 项目是否有 `tech_stack` 数据。

```python
tech_stack = json.loads(project.tech_stack) if project.tech_stack else []
```

**通过条件**: `len(ts) > 0`
**严重级别**: 无技术栈 -> `"warn"`, 有技术栈 -> `"ok"`
**detail**: `"检测到技术栈: Python, FastAPI, ..."`

### 4. official_docs - 官方文档校验

**检查内容**: 是否有 framework 级别的知识库。

```sql
SELECT COUNT(*) FROM aidp_knowledge_bases
WHERE project_id = ?
  AND kb_level = 'framework'
  AND deleted_at IS NULL
```

**通过条件**: `fw_kb > 0`
**严重级别**: `fw_kb == 0` -> `"warn"`, 其他 -> `"ok"`

### 5. rules_extract - 规则提取校验

**检查内容**: `aidp_rules` 表中是否有该项目的规则。

```sql
SELECT COUNT(*) FROM aidp_rules WHERE project_id = ?
```

**通过条件**: `rc > 0`
**严重级别**: `rc == 0` -> `"warn"`, 其他 -> `"ok"`

### 6. agent_setup - Agent 创建校验

**检查内容**: `aidp_agents` 表中是否有活跃的 Agent。

```sql
SELECT COUNT(*) FROM aidp_agents
WHERE project_id = ? AND is_active = true
```

**通过条件**: `ac > 0`
**严重级别**: `ac == 0` -> `"warn"`, 其他 -> `"ok"`

### 7. mcp_register - MCP 注册校验

**检查内容**: 所有必需工具是否已注册且健康。

```python
from app.services.tool_registry import list_tools
tools = await list_tools()
healthy = sum(1 for t in tools if t.get("status") == "healthy")
required = {"code-index", "doc-index", "skillrouter", "memory-tool", "knowledge-tool"}
registered = {t.get("name") for t in tools if t.get("status") == "healthy"}
missing = required - registered
```

**通过条件**: `len(missing) == 0`
**严重级别**: 有缺失 -> `"error"`, 其他 -> `"ok"`
**detail**: `"3/5 工具 healthy，缺失: {skillrouter}"`

## 检查结果格式

每个检查项返回统一格式：

```json
{
    "task_id": "code_index",
    "name": "代码索引校验",
    "passed": true,
    "detail": "code-index 中 342 个节点",
    "severity": "ok"
}
```

## 严重级别 (severity)

| 级别 | 含义 | 示例 |
|------|------|------|
| `"ok"` | 检查通过，状态良好 | `"检测到技术栈: Python"` |
| `"warn"` | 检查已执行但结果不理想 | `"系统中 0 条规则"` |
| `"error"` | 检查失败，关键步骤未完成 | `"工具缺失: {skillrouter}"` |

## 汇总输出

```json
{
    "project_id": 1,
    "project_name": "my-app",
    "owner_id": "uuid",
    "checks": [
        {"task_id": "code_index", "passed": true, "severity": "ok", ...},
        {"task_id": "doc_import", "passed": false, "severity": "error", ...},
        ...
    ],
    "mappings": [
        {"controller_project_id": 1, "tool_name": "code-index", "tool_project_id": "abc123"}
    ],
    "summary": "5/7 检查通过",
    "all_passed": false
}
```

**mappings** 字段包含 `aidp_project_mappings` 表的内容，显示 controller 项目 ID 到各工具内部项目 ID 的映射关系。

## 与 Init Flow 的关系

Verify 是 Init Flow 的校验步骤 (`aidp_init_detail.md`)，在初始化任务执行后调用：

```
1. 用户调用 GET /api/projects/{id}/verify
2. 逐项检查各任务的执行结果
3. 不触发任何新操作，只读检查
4. 返回检查报告，帮助用户了解哪些步骤需要关注
```

典型的检查内容来源：
- **DB 查询**: doc_import, tech_analysis, official_docs, rules_extract, agent_setup
- **外部工具调用**: code_index (查 SQLite), mcp_register (查 tool_registry 表)
- **数据解析**: tech_analysis (读取 project.tech_stack JSON)