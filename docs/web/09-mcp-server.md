# MCP Server 架构与集成

## 1. 概述

AIDP Controller 内嵌一个 FastMCP 服务器，通过 **MCP (Model Context Protocol)** 为 AI Agent（如 Claude）提供标准化的工具调用接口。MCP 服务器是 Controller 与外部 AI 客户端之间的桥梁。

### 1.1 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| MCP 框架 | FastMCP (fastmcp-slim) | 3.4.4 |
| 传输协议 | Streamable HTTP (JSON-RPC 2.0 over HTTP) | — |
| 端点路径 | `/mcp` | — |
| 会话管理 | 内存会话（30 分钟超时） | — |

### 1.2 架构定位

```
AI 客户端 (Claude, etc.)
    │
    │  MCP JSON-RPC over HTTP
    ▼
Controller MCP Server (/mcp)
    │
    ├── aidp_context()      → 5 阶段上下文管道
    ├── invoke_tool_mcp()   → 通用工具调度器
    ├── list_registered_tools() → 查询工具注册表
    ├── check_tool_health() → 健康检查
    ├── sync_tool_capabilities() → 能力同步
    ├── aidp_init()         → 项目初始化
    └── aidp_instructions() → Subagent 指令生成
```

## 2. MCP Server 配置

### 2.1 Server 定义

**文件**: `apps/controller/app/mcp/server.py`

```python
from fastmcp import FastMCP

mcp = FastMCP("aidp-controller")
```

全局单例，所有 MCP 工具通过 `@mcp.tool()` 装饰器注册。

### 2.2 与 FastAPI 集成

**文件**: `apps/controller/app/main.py`

```python
from app.mcp.server import mcp

# 创建 MCP 子应用
_mcp_app = mcp.http_app(path="/", transport="streamable-http")

# 组合 lifespan
combined_lifespan = combine_lifespans(app.router.lifespan_context, _mcp_app.router.lifespan_context)

# 挂载到 /mcp
app.mount("/mcp", _mcp_app)
```

**端点**: `POST /mcp/` — 所有 MCP 通信通过此端点。

### 2.3 会话管理

**文件**: `apps/controller/app/mcp/session_manager.py`

```python
class MCPSessionManager:
    def __init__(self):
        self.sessions = {}  # session_id -> SessionState
    
    def check_context_loaded(self, session_id):
        """检查 aidp_context 是否已调用"""
        session = self.sessions.get(session_id)
        if not session or not session.context_loaded:
            return False, {"error": "CONTEXT_REQUIRED", "hint": "调用 aidp_context 加载上下文"}
        return True, None
```

**会话规则**：
- `aidp_context` 必须在任何工具调用之前执行
- 会话 30 分钟无活动后自动过期
- 以下工具无需上下文即可调用：`aidp_context`, `aidp_init`, `list_registered_tools`, `check_tool_health`, `sync_tool_capabilities`, `aidp_instructions`

## 3. MCP 工具列表

### 3.1 aidp_context（必需第一步调用）

**功能**: 执行 5 阶段上下文管道，为 AI Agent 组装开发上下文。

```
Stage 0: 加载 Agent Instructions (角色定义、约束规则)
Stage 1: 意图分析 (skill-router: analyze_intent)
Stage 2: 知识检索 (memory-tool, knowledge-tool, asset-tool 并行)
Stage 3: 技能匹配 (skill-router: skill_run)
Stage 4: 上下文组装 (系统提示 + 用户消息)
```

**参数**:
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| project_name | string | 是 | 项目名称 |
| task | string | 否 | 当前任务描述 |
| agent_type | string | 否 | Agent 类型，默认 "main" |

**返回**: 组装后的上下文对象（系统提示 + 用户消息 + 工具列表）

### 3.2 invoke_tool_mcp

**功能**: 通用工具调度器，调用任何已注册的 AIDP 工具。

**参数**:
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| tool_name | string | 是 | 工具名称（如 "sandbox-tool"） |
| capability | string | 是 | 能力标识（如 "sandbox.execute"） |
| arguments | string | 否 | JSON 格式参数 |
| user_id | integer | 否 | 用户 ID（默认 0） |

**调用链路**:
```
invoke_tool_mcp("sandbox-tool", "sandbox.execute", '{"code": "print(1)"}')
    → 查找 tool_registry 表 → HTTP POST {endpoint}/tool/invoke
    → sandbox-tool 执行 → 返回结果
```

### 3.3 list_registered_tools

**功能**: 列出所有已注册的工具及其状态。

**参数**: 无

**返回**: 工具列表，包含名称、端点、状态、能力列表

### 3.4 check_tool_health

**功能**: 验证工具是否正常运行。

**参数**:
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| tool_name | string | 否 | 工具名称（为空时检查所有） |

### 3.5 sync_tool_capabilities

**功能**: 从工具的 manifest 文件重新加载其能力定义。

**参数**:
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| tool_name | string | 是 | 工具名称 |

### 3.6 aidp_init

**功能**: 将新项目导入 AIDP 平台。

**参数**:
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| project_name | string | 是 | 项目唯一名称 |
| description | string | 否 | 项目描述 |
| tech_stack | string | 否 | 技术栈描述 |
| nas_path | string | 否 | 项目在 NAS 上的路径 |

### 3.7 aidp_instructions

**功能**: 为复杂任务创建独立的子代理指令集。

**参数**:
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| project_name | string | 是 | 项目名称 |
| task | string | 是 | 具体任务描述 |
| agent_type | string | 否 | Subagent 类型 |

## 4. 工具调用流程

### 4.1 完整调用链

```
┌─────────────────────┐
│  AI 客户端 (Claude)  │
└──────────┬──────────┘
           │ MCP JSON-RPC
           ▼
┌─────────────────────┐
│  Controller MCP      │
│  Server (/mcp)       │
│                      │
│  1. 验证会话          │
│  2. 检查上下文加载    │
│  3. 路由到工具函数    │
└──────────┬──────────┘
           │ HTTP POST
           ▼
┌─────────────────────┐
│  Tool Registry       │
│  (tool_registry 表)  │
│                      │
│  查找工具端点         │
└──────────┬──────────┘
           │ HTTP POST
           ▼
┌─────────────────────┐
│  外部工具服务         │
│  (如 sandbox-tool)   │
│                      │
│  POST /tool/invoke   │
│  执行业务逻辑         │
└──────────┬──────────┘
           │ JSON Response
           ▼
┌─────────────────────┐
│  Controller          │
│                      │
│  记录调用日志         │
│  返回结果给 MCP      │
└─────────────────────┘
```

### 4.2 端点解析（降级链）

1. **数据库查找**: `tool_registry` 表中 `status = "healthy"` 的记录
2. **内存缓存**: `_endpoint_cache` 字典
3. **环境变量降级**:
   - `SKILLROUTER_URL` → `http://localhost:8788`
   - `KNOWLEDGE_URL` → `http://localhost:18081`
   - `MEMORY_URL` → `http://localhost:18085`
   - `ASSET_URL` → `http://localhost:18082`
   - `SANDBOX_URL` → `http://localhost:18083`
   - `QUALITY_URL` → `http://localhost:18084`

## 5. 工具服务标准契约

每个外部工具服务必须实现以下端点：

### 5.1 健康检查

```
GET /health
Response: {"status": "ok", "tool": "sandbox-tool", "version": "0.1.0"}
```

### 5.2 工具清单

```
GET /tool/manifest
Response: {
    "name": "sandbox-tool",
    "version": "0.1.0",
    "description": "代码执行沙箱",
    "capabilities": [...]
}
```

### 5.3 能力列表

```
GET /tool/capabilities
Response: [
    {
        "name": "sandbox.execute",
        "description": "执行代码",
        "input_schema": {...},
        "output_schema": {...}
    }
]
```

### 5.4 通用调用

```
POST /tool/invoke
Request: {
    "trace_id": "tr_abc123",
    "capability": "sandbox.execute",
    "context": {"user_id": 1},
    "input": {"code": "print(1)", "language": "python"}
}
Response: {
    "trace_id": "tr_abc123",
    "tool": "sandbox-tool",
    "capability": "sandbox.execute",
    "success": true,
    "output": {"stdout": "1\n", "stderr": "", "exitCode": 0},
    "error": null,
    "elapsed_ms": 142
}
```

## 6. 关键文件索引

| 文件 | 用途 |
|------|------|
| `apps/controller/app/mcp/server.py` | MCP Server 定义，7 个工具函数 |
| `apps/controller/app/mcp/session_manager.py` | 会话跟踪和上下文加载强制 |
| `apps/controller/app/main.py:90,126-133,177` | FastAPI + MCP 集成 |
| `apps/controller/app/services/tool_registry.py` | 工具注册表 CRUD |
| `apps/controller/app/services/tool_invoker.py` | HTTP 客户端，调用外部工具 |
| `apps/controller/app/api/tools.py` | REST API 管理工具 |
| `apps/controller/app/db/models.py:7-21` | ToolRegistry 和 ToolInvocation 模型 |
| `tools/skill-router/app/main.py` | Skill-router（含独立 MCP Server） |
| `tools/skill-router/app/mcp/tools.py` | Skill-router 的 25+ MCP 工具 |
| `tools/*/app/api/tool.py` | 各工具的标准 API 契约 |
