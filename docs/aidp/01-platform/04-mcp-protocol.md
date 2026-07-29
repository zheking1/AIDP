# MCP 协议规范

## 概述

AIDP Controller 通过 FastMCP 对外暴露 MCP (Model Context Protocol) 服务，AI Agent 通过 Streamable-HTTP 协议连接并调用平台能力。

**源码**: `apps/controller/app/mcp/server.py`

## MCP Server 实例

```python
# app/mcp/server.py:8
mcp = FastMCP(
    "aidp-controller",
    instructions="""AIDP 工作流指引:
    【必须第一步调用】aidp_context ...
    工具调用顺序:
    1. aidp_context(project_name, task) → 获取上下文
    2. invoke_tool_mcp(tool_name, capability, arguments) → 执行具体操作
    3. 完成后可选: invoke_tool_mcp("memory-tool", "memory.create", {...}) → 归档经验
    """,
)
```

Server 名称: `"aidp-controller"`
传输协议: Streamable-HTTP (`POST /mcp`)

## 注册的 MCP 工具

### 1. `aidp_context` — 上下文管线（必须第一步调用）

```
参数:
  ctx: Context              # FastMCP 上下文对象（含 session_id, headers）
  project_name: str         # 项目名称
  task: str = ""            # 任务描述
  agent_type: str = "main"  # Agent 类型

执行:
  1. 从 aidp_projects 表查找 project_id
  2. ContextPipeline.execute(task, project_id, session_id)
  3. 触发 5 阶段管线 (Stage 0-4)
  4. 调用 session_manager.mark_context_loaded(session_id, result)
  5. 返回 context + stages 详细结果 + token_estimate
```

### 2. `invoke_tool_mcp` — 通用工具调用器

```
参数:
  ctx: Context       # 用于读取 headers 中的 x-api-key
  tool_name: str     # 工具名: "sandbox-tool", "memory-tool" 等
  capability: str    # 能力标识: "sandbox.execute", "memory.search"
  arguments: str     # JSON 参数字符串，默认 "{}"
  user_id: int = 0   # 用户 ID
  api_key: str = ""  # API Key（从 headers x-api-key 获取）

执行:
  1. 从 ctx.request.headers 读取 x-api-key（如参数未提供）
  2. session_manager.can_call_tool(session_id, tool_name)
     → 检查会话是否存在、context_loaded 是否为 True
     → 未通过返回 {"success": false, "error": {"code": "CONTEXT_REQUIRED"}}
  3. session_manager.record_tool_call(session_id, f"{tool_name}:{capability}")
  4. invoke_tool(tool_name, capability, args, user_id)
  5. 返回 JSON 结果
```

### 3. `list_registered_tools` — 列出已注册工具

```
参数:
  status: str = ""  # 可选筛选: "healthy", "unhealthy", "unknown"

执行:
  list_tools(status=status or None)
  返回: [{name, capabilities, status, lastHealthCheck, ...}, ...]
```

### 4. `check_tool_health` — 健康检查

```
参数:
  tool_name: str = ""  # 为空则检查所有工具

执行:
  tool_name 不为空 → health_check_tool(tool_name)
  tool_name 为空   → health_check_all()
  返回: {tool, status, durationMs}
```

### 5. `sync_tool_capabilities` — 同步工具能力

```
参数:
  tool_name: str

执行:
  GET {endpoint}/tool/capabilities → 更新 tool_registry.capabilities
```

### 6. `aidp_init` — 项目初始化

```
参数:
  project_name, description, tech_stack, nas_path,
  docs (JSON数组), key_files (JSON数组), architecture_summary

执行:
  1. 在 aidp_projects 表中创建或更新项目记录
  2. 调用 init_project() 执行 9 阶段初始化任务
  3. 返回 {project_id, ...}
```

### 7. `aidp_instructions` — 生成 Subagent 指令

```
参数:
  project_name, task, agent_type

执行:
  1. 查找 project_id
  2. ContextPipeline.execute(task, project_id) 获取上下文
  3. 组装 subagent_instructions (role, task, context, allowed_tools, parent_trace_id)
  4. 返回给调用者创建 subagent
```

### 8. `manage_models` — 模型管理（CRUD）

```
参数:
  action:        "list" | "get" | "get_best" | "create" | "update" | "delete"
  task_type:     按任务类型过滤
  model_id:      模型 ID
  name, provider, model_name, api_base, task_types, priority

执行:
  委托给 ModelService 的对应方法
```

## 会话管理

**源码**: `app/mcp/session_manager.py`

### MCPSessionManager

```python
class MCPSessionManager:
    def __init__(self, timeout_minutes=30):
        self.sessions: Dict[str, MCPSession] = {}
        self.timeout_minutes = 30

    # 获取或创建会话
    def get_or_create_session(session_id) -> MCPSession

    # 标记上下文已加载（在 aidp_context 调用后）
    def mark_context_loaded(session_id, context_result=None)

    # 检查是否已加载上下文
    def is_context_loaded(session_id) -> bool

    # 记录工具调用
    def record_tool_call(session_id, tool_name)

    # 检查是否允许调用某工具
    def can_call_tool(session_id, tool_name) -> (bool, str)
```

### MCPSession 数据结构

```python
@dataclass
class MCPSession:
    session_id: str
    context_loaded: bool = False        # 是否已调用 aidp_context
    created_at: datetime
    last_activity: datetime
    tools_called: list                  # [{tool, time}, ...]
    context_result: Optional[dict]      # aidp_context 的返回结果
```

### 上下文强制规则

**先调用 aidp_context 的强制规则** (`can_call_tool`):

```python
# 免检工具列表 — 这些工具不需要 aidp_context 前置
ALLOWED_WITHOUT_CONTEXT = {
    "aidp_context",
    "aidp_init",
    "list_registered_tools",
    "check_tool_health",
    "sync_tool_capabilities",
    "aidp_instructions",
}

# 其他工具 (如 invoke_tool_mcp) 必须经过检查:
# 1. 会话不存在 → 返回 False, "必须先调用 aidp_context"
# 2. context_loaded == False → 返回 False, "必须先调用 aidp_context 加载上下文"
# 3. 否则 → 返回 True
```

### 会话清理

```python
# 清理超过 30 分钟无活动的会话
def cleanup_expired():
    for sid, s in sessions.items():
        if (now - s.last_activity) > timedelta(minutes=30):
            del sessions[sid]
```

## 完整调用流程示例

```
1. MCP Client 连接 Controller
   POST /mcp
   tool: "aidp_context"
   args: {project_name: "my-app", task: "修复登录bug"}

2. Controller 处理:
   2a. FastMCP 解析请求 → SessionManager 创建会话 (session_id)
   2b. 执行 5 阶段 ContextPipeline
   2c. SessionManager.mark_context_loaded(session_id, result)
   2d. SessionManager.record_tool_call(session_id, "aidp_context")
   2e. 返回: {context, stages, estimated_tokens, ...}

3. MCP Client 调用工具:
   POST /mcp
   tool: "invoke_tool_mcp"
   args: {tool_name: "sandbox-tool", capability: "sandbox.execute", arguments: "{...}"}

4. Controller 处理:
   4a. SessionManager.can_call_tool(session_id, "invoke_tool_mcp")
   4b. 检查: context_loaded=True → 允许
   4c. ToolInvoker.invoke("sandbox-tool", "sandbox.execute", args)
   4d. POST http://localhost:18083/tool/invoke
   4e. SessionManager.record_tool_call(session_id, "sandbox-tool:sandbox.execute")
   4f. 返回结果

5. 可选: 归档记忆
   POST /mcp
   tool: "invoke_tool_mcp"
   args: {tool_name: "memory-tool", capability: "memory.create", arguments: "{...}"}
```

## 工具发现与调用

Controller 通过以下方式暴露可用工具:

1. **MCP 工具列表**: `list_registered_tools()` MCP 工具 — 返回所有已注册工具及其状态
2. **工具能力**: 每个工具的 `capabilities` 字段包含其支持的能力列表
3. **能力同步**: `sync_tool_capabilities(tool_name)` → 从工具的 `/tool/capabilities` 端点重新拉取

工具调用通过统一的 `invoke_tool_mcp` MCP 工具，内部委托给 `ToolInvoker` → HTTP POST `{endpoint}/tool/invoke`。