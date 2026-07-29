# Layer 2 — Agent MCP 工具 `index_changes`

> 最智能的一层。Agent 完成工作后主动调用，分析变更并更新索引，同时提取可复用的模式。

**状态**: 待开发

---

## 1. 设计动机

Agent 可能因为各种原因忘记调用此工具。但作为三层防御中的 Layer 2，它在 Agent **主动且成功调用**时提供额外价值——不仅索引代码，还分析变更、提取模式。

Agent 的工作流程应该封装为：
```
aidp_context → 开发任务 → invoke_tool_mcp → ... → index_changes → promote_evolution
```

## 2. MCP 工具定义

### 工具名: `index_changes`

```python
@mcp.tool()
async def index_changes(
    ctx: Context,
    task: str,
    changed_files: str = "[]",
    summary: str = "",
    project_id: Optional[str] = None,
) -> str:
    """索引代码变更并分析——完成一个开发任务后调用。

    将本次任务中修改的文件提交到 code-index 进行增量索引，
    同时分析变更内容，发现可复用模式。

    Args:
        task: 本次完成的任务描述
        changed_files: JSON 数组，修改的文件列表
                      格式: '[{"path":"src/main.py","content":"...","language":"python"}]'
                      为空时使用 session 中的 project_id 查找
        summary: 变更总结（做了什么、为什么）
        project_id: 项目 ID，为空时从 session 自动获取

    Returns:
        JSON 包含索引和模式分析结果

    使用场景:
        - 完成一个功能开发后立即调用，保持索引最新
        - 修复 Bug 后调用，让 AIDP 学到修复模式
        - 重构后调用，更新代码结构信息
    """
```

## 3. 执行逻辑

```
Agent 调用 index_changes(task, changed_files, summary)
    │
    ├── 1. 获取 project_id
    │     │ from session (aidp_context 绑定的)
    │     │ from .opencode/watcher.json (本地 hooks)
    │     │ from CLI 参数
    │
    ├── 2. 索引代码文件
    │     │ if changed_files 不为空:
    │     │     → tool_invoker.invoke("code-index", "code.index_files", ...)
    │     │ else:
    │     │     → 运行 git diff 获取变更文件
    │     │     → 读取每个文件内容
    │     │     → tool_invoker.invoke("code-index", "code.index_files", ...)
    │
    ├── 3. 索引文档文件
    │     │ POST /api/classification/import
    │
    ├── 4. 模式分析（可选）
    │     │ 调用 evolution-engine 分析变更
    │     │ if 发现可复用模式 & confidence > 0.6:
    │     │     → 自动创建进化提案
    │     │     → 返回提案链接
    │
    └── 5. 返回结果摘要
          │ indexed_files: N
          │ indexed_lines: M
          │ patterns_found: [...]
          │ evolution_proposed: bool
```

## 4. 实现位置

**文件**: `apps/controller/app/mcp/server.py`

**新增函数**: `index_changes`

**依赖**:
- `session_manager` — 读取 session 绑定的 `project_id`
- `tool_invoker` — 调用 code-index、memory-tool 等
- `evolution-engine` — 模式分析（可选）

## 5. 完整实现代码（待开发）

```python
# 位置: apps/controller/app/mcp/server.py

@mcp.tool()
async def index_changes(
    ctx: Context,
    task: str = "",
    changed_files: str = "[]",
    summary: str = "",
    project_id: str = "",
) -> str:
    """索引代码变更并分析——完成开发任务后调用。"""
    import json as _json

    result = {
        "success": True,
        "indexed_files": 0,
        "doc_files": 0,
        "patterns_found": [],
        "evolution_proposed": False,
    }

    # 1. 解析 project_id
    session = session_manager.sessions.get(ctx.session_id or "default")
    pid = project_id or (session.project_id if session else "")

    if not pid:
        return _json.dumps({
            "success": False,
            "error": "No project_id. Call aidp_context first or provide project_id."
        }, ensure_ascii=False, indent=2)

    # 2. 解析 changed_files
    files = []
    try:
        files = _json.loads(changed_files) if isinstance(changed_files, str) else changed_files
    except _json.JSONDecodeError:
        files = []

    # 3. 索引代码
    code_files = [f for f in files if not f.get("path", "").endswith((".md", ".txt", ".rst"))]
    if code_files:
        from app.services.tool_invoker import invoke_tool
        index_result = await invoke_tool(
            "code-index",
            "code.index_files",
            {"project_id": int(pid), "files": code_files, "user_id": session.user_id if session else 0}
        )
        if index_result.get("success"):
            result["indexed_files"] = len(code_files)

    # 4. 索引文档
    doc_files = [f for f in files if f.get("path", "").endswith((".md", ".txt", ".rst"))]
    if doc_files:
        # await classification_import(doc_files)
        result["doc_files"] = len(doc_files)

    # 5. 模式分析
    if task and summary:
        try:
            # 调用 evolution-engine 分析是否有可复用模式
            from app.tools.evolution_engine.db.database import async_session_factory as evo_session
            from app.tools.evolution_engine.services.event_collector import EventCollector
            # ... (调用 evolution-engine 分析逻辑)
            # 若 confidence > 0.6，自动创建 EvolutionVersion
        except Exception:
            pass

    return _json.dumps(result, ensure_ascii=False, indent=2)
```

## 6. 与 `promote_evolution` 的关系

| 工具 | 触发时机 | 谁调用 |
|------|----------|--------|
| `index_changes` | 每次完成开发任务后 | Agent 自动调用 |
| `promote_evolution` | 发现可复用模式后 | `index_changes` 内部自动调用 |

Agent 只需调用 `index_changes`，系统自动决定是否需要创建进化提案。

## 7. 与 aidp_context 的关系

建议的 Agent 工作流模板：

```
1. aidp_context(project_name, task)        ← 加载上下文
2. invoke_tool_mcp(...)                    ← 执行开发任务
   ... (多次调用)
3. index_changes(task, changed_files, summary)  ← 索引变更 + 分析模式
4. promote_evolution(task, result)         ← 可选: 手动提交进化提案
```

## 8. Session 免检工具列表更新

```python
# session_manager.py can_call_tool 白名单
ALLOWED_WITHOUT_CONTEXT = {
    "aidp_context",
    "aidp_init",
    "list_registered_tools",
    "check_tool_health",
    "sync_tool_capabilities",
    "aidp_instructions",
    "list_evolutions",
    "index_changes",      # 新增: 允许在 context 之前调用 (fallback)
}
```