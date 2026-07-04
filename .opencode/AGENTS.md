## AIDP 集成规则 — Agent 自动协作指南

本文件定义了 Agent 与 AIDP (AI DevOps Platform) 的协作规则。
Agent 在执行任务前应加载此文件，理解 AIDP 工作流。

### 开发前：加载上下文

在开始任何开发任务前，先调用 `aidp_context` 加载项目上下文：
```
aidp_context(project_name="aidp", task="<当前任务描述>")
```
这会触发 Staged Pipeline：加载 Instructions → 意图分析 → 知识检索 → 技能匹配 → 上下文组装。

### 开发中：使用工具

| 场景 | 工具调用 |
|------|---------|
| 代码执行验证 | `invoke_tool_mcp("sandbox-tool", "sandbox.execute", {code, language})` |
| 代码质量检查 | `invoke_tool_mcp("quality-tool", "quality.check", {code, filename})` |
| 检索项目记忆 | `invoke_tool_mcp("memory-tool", "memory.search", {project, query})` |
| 检索知识文档 | `invoke_tool_mcp("knowledge-tool", "knowledge.search", {query, top_k})` |
| 技能路由 | `invoke_tool_mcp("skillrouter", "resolve_task", {task, api_key})` |

### 开发后：归档经验

将学到的经验存入 memory-tool：
```
invoke_tool_mcp("memory-tool", "memory.create", {
    project: "aidp",
    category: "architecture|bugfix|lesson|pattern",
    title: "简短标题",
    content: "详细描述",
    tags: "关键词"
})
```

### 创建 Subagent

当任务复杂需要拆分时：
1. 调用 `aidp_instructions(project_name, task, agent_type)` 生成 subagent 专属 instructions
2. 用返回的 instructions 创建 subagent
3. Subagent 也会调用 `aidp_context` 加载自己需要的信息

### 初始化新项目

当需要将一个项目导入 AIDP 时：
1. 自动扫描项目目录，读取 README.md、关键配置文件、工具定义文件
2. 识别项目技术栈、架构信息
3. 调用 `aidp_init` 初始化：
```
aidp_init(
  project_name="项目名",
  tech_stack="Python 3.13 + FastAPI",
  architecture_summary="架构概述...",
  docs=[{title, content}, ...],
  key_files=[{path, content, type}, ...]
)
```

### 工具健康检查

定期检查所有工具状态：
```
check_tool_health()  # 检查所有
check_tool_health(tool_name="sandbox-tool")  # 检查单个
```