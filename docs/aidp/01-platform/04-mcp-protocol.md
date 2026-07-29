# MCP 协议规范

## 概述

AIDP Controller 通过 FastMCP 对外暴露 13 个 MCP 工具，AI Agent 通过 Streamable-HTTP 协议连接并调用。

**源码**: `apps/controller/app/mcp/server.py`  
**传输协议**: Streamable-HTTP (`POST /mcp`)

## 工作流

```
Agent 连接 → aidp_context(project_name, task, api_key) → 认证+加载上下文
    │
    ├─ invoke_tool_mcp("sandbox-tool", "sandbox.execute", {...})
    ├─ invoke_tool_mcp("memory-tool", "memory.search", {...})
    │
    ├─ index_changes(task, changed_files, summary) → 增量索引
    │
    └─ promote_evolution(title, description) → 知识沉淀
```

## 13 个 MCP 工具

### 1. `aidp_context` — 5阶段上下文管线（必须第一步调用）

认证用户、绑定项目、执行 5 阶段管线。

| 参数 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `project_name` | str | ✅ | 项目名称 |
| `task` | str | ❌ | 任务描述 |
| `agent_type` | str | ❌ | Agent 类型, 默认 "main" |

**认证**: 从 HTTP Header `x-api-key` 读取 API Key，验证用户身份并绑定到 session。

### 2. `invoke_tool_mcp` — 通用工具调用

| 参数 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `tool_name` | str | ✅ | 工具名称 |
| `capability` | str | ✅ | 能力标识 |
| `arguments` | str | ❌ | JSON 参数字符串 |

**自动注入**: `project_id` 和 `project` 从 session 自动填充到 arguments。

### 3. `aidp_init` — 项目初始化

全量扫描代码、导入文档、创建记忆、注册资产。

| 参数 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `project_name` | str | ✅ | 项目名称 |
| `description` | str | ❌ | 项目描述 |
| `tech_stack` | str | ❌ | 技术栈描述 |
| `docs` | str | ❌ | JSON 文档数组 |
| `key_files` | str | ❌ | JSON 文件数组 |

### 4. `aidp_instructions` — Subagent 指令生成

### 5. `index_changes` — 增量索引 + 模式分析

完成开发任务后调用。索引代码变更、分析可复用模式、自动创建进化提案。

| 参数 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `task` | str | ❌ | 任务描述 |
| `changed_files` | str | ❌ | JSON 文件数组 |
| `summary` | str | ❌ | 变更总结 |
| `project_id` | str | ❌ | 项目 ID (自动从 session 获取) |

### 6. `install_local_scripts` — 安装本地脚本

返回 watcher.json 配置、git hook 脚本、file_watcher 启动命令。Agent 写入本地文件系统。

| 参数 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `project_dir` | str | ✅ | 项目根目录绝对路径 |
| `project_id` | int | ✅ | AIDP 项目 ID |
| `layers` | str | ❌ | all / git_hook / file_watcher / watcher_config |

### 7. `promote_evolution` — 进化提案

### 8. `list_evolutions` — 查看系统级最佳实践

### 9. `analyze_and_evolve` — LLM 模式分析

### 10. `manage_models` — 统一模型管理

### 11. `list_registered_tools` — 查看可用工具

### 12. `check_tool_health` — 健康检查

### 13. `sync_tool_capabilities` — 同步工具能力

## 会话认证

```
Agent 连接 → session 创建
  ├─ aidp_context(x-api-key) → 验证 API Key → session 绑定 (user_id, project_id)
  ├─ invoke_tool_mcp → 自动注入 project_id, user_id
  └─ index_changes → 自动从 session 获取 project_id
```

**免检工具 (无需先调 aidp_context)**:
`aidp_context`, `aidp_init`, `list_registered_tools`, `check_tool_health`, `sync_tool_capabilities`, `aidp_instructions`, `list_evolutions`, `index_changes`