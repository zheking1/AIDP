# Controller 通信机制

## 概览

Controller 是 AIDP 平台的中央调度器，通过 HTTP REST 调用与各工具通信。本文件描述 Controller 如何发现、注册、调用各工具的全过程。

## 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| Tool Registry | `app/services/tool_registry.py` | 工具注册、健康检查、能力同步、启用/禁用 |
| Tool Invoker | `app/services/tool_invoker.py` | HTTP 调用工具，端点缓存，调用历史记录 |
| Tool Registry DB | `app/db/models.py:7` | `tool_registry` 表，存储工具元数据 |
| Tool Invocation DB | `app/db/models.py:24` | `tool_invocation` 表，记录每次调用 |

## 工具注册流程

### 1. 注册工具 (`register_tool`)

```python
# app/services/tool_registry.py:15
async def register_tool(name, endpoint, display_name, description, version)
```

- 检查 `tool_registry` 表中是否已有同名工具
- 存在 → 更新 `endpoint`、`display_name`、`description`、`version`
- 不存在 → 创建新记录，`status` 初始化为 `"registered"`
- 工具注册可以是手动 API 调用，也可以由 `aidp_init` 流程触发

### 2. 工具注册表 (`ToolRegistry` 模型)

```python
# app/db/models.py:7
class ToolRegistry(Base):
    __tablename__ = "tool_registry"
    id: int (PK)
    name: str (unique)        # 工具唯一名称，如 "sandbox-tool"
    display_name: str
    description: str
    version: str
    endpoint: str             # 工具 HTTP 地址，如 "http://localhost:18083"
    status: str               # "registered" / "healthy" / "unhealthy" / "unreachable" / "disabled"
    last_health_check: datetime
    capabilities: JSON        # 工具能力列表
    created_at / updated_at: datetime
```

### 3. 健康检查

控制器通过 HTTP GET 访问 `{endpoint}/health` 定期检查工具健康状态：

```python
# app/services/tool_registry.py:69
async def health_check_tool(tool_name):
    health_url = f"{endpoint.rstrip('/')}/health"
    resp = await client.get(health_url)
    # 200 → "healthy"
    # 其他 → "unhealthy"
    # 异常 → "unreachable"
```

健康检查会更新 `tool_registry` 表中的 `status` 和 `last_health_check` 字段。

### 4. 能力同步

从工具的 manifest 端点 `{endpoint}/tool/capabilities` 拉取能力定义：

```python
# app/services/tool_registry.py:118
async def sync_capabilities(tool_name):
    caps_url = f"{endpoint.rstrip('/')}/tool/capabilities"
    resp = await client.get(caps_url)
    # 获取 capabilities 列表 → 更新 tool_registry.capabilities
```

## 工具调用流程

### 完整调用链

```
用户/AI Agent
    → MCP 调用 invoke_tool_mcp(tool_name, capability, arguments)
    → app/mcp/server.py:31
    → 会话检查 (SessionManager.can_call_tool)
    → tool_invoker.invoke_tool(tool_name, capability, arguments)
    → 查找端点 → 构造 HTTP POST 请求 → 发送到工具 → 记录调用日志
    → 返回 JSON 结果
```

### ToolInvoker 端点解析逻辑

```python
# app/services/tool_invoker.py:15
class ToolInvoker:
    def __init__(self):
        self._endpoint_cache = {}  # 内存缓存

    async def _get_tool_endpoint(self, tool_name):
        # 1. 优先从内存缓存查找
        if tool_name in self._endpoint_cache:
            return self._endpoint_cache[tool_name]

        # 2. 从数据库 tool_registry 表查找 (仅 status="healthy")
        if self.db:
            tool = await db.execute(
                select(ToolRegistry).where(
                    ToolRegistry.name == tool_name,
                    ToolRegistry.status == "healthy"
                )
            )

        # 3. 环境变量回退 (fallback URLs)
        endpoints = {
            "skill-router":   os.getenv("SKILLROUTER_URL",  "http://localhost:8788"),
            "knowledge-tool": os.getenv("KNOWLEDGE_URL",    "http://localhost:18081"),
            "memory-tool":    os.getenv("MEMORY_URL",       "http://localhost:18085"),
            "asset-tool":     os.getenv("ASSET_URL",        "http://localhost:18082"),
            "sandbox-tool":   os.getenv("SANDBOX_URL",      "http://localhost:18083"),
            "quality-tool":   os.getenv("QUALITY_URL",      "http://localhost:18084"),
        }
        # code-index / doc-index 等工具通过 DB 或直接配置
```

**查找优先级**: 内存缓存 → 数据库 registry (仅 healthy) → 环境变量硬编码回退

### HTTP 调用格式

所有工具的调用使用统一格式：

```
POST {endpoint}/tool/invoke
Content-Type: application/json

{
    "capability": "sandbox.execute",
    "input": {"code": "print(1)", "language": "python"},
    "trace_id": "a1b2c3d4"
}
```

### 调用历史记录

每次调用都记录到 `tool_invocation` 表：

```python
# app/services/tool_invoker.py:127
async def invoke_tool(tool_name, capability, arguments, user_id):
    # ... 执行调用 ...
    record = ToolInvocation(
        id=str(uuid.uuid4()),
        tool_name=tool_name,
        capability=capability,
        arguments=json.dumps(arguments),
        result=json.dumps(result),
        success=result.get("success", False),
        user_id=user_id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(record)
    await db.commit()
```

## 请求流程全景

```
                                用户请求
                                     |
                          ┌──────────v──────────┐
                          │   MCP Client (AI)    │
                          │ tool: invoke_tool_mcp│
                          └──────────┬──────────┘
                                     | POST /mcp
                          ┌──────────v──────────┐
                          │ FastMCP Server       │
                          │ app/mcp/server.py    │
                          └──────────┬──────────┘
                                     |
                          ┌──────────v──────────┐
                          │ SessionManager       │
                          │ can_call_tool()?     │
                          │ 检查 context_loaded   │
                          └──────────┬──────────┘
                                     | allowed
                          ┌──────────v──────────┐
                          │ tool_invoker.py      │
                          │ invoke_tool()         │
                          ├──────────────────────┤
                          │ 1. _get_endpoint()   │
                          │    cache → DB → env  │
                          │ 2. POST /tool/invoke │
                          │ 3. 记录 invocation   │
                          └──────────┬──────────┘
                                     | HTTP
                          ┌──────────v──────────┐
                          │ 目标工具              │
                          │ /tool/invoke endpoint│
                          │ 处理并返回 JSON       │
                          └─────────────────────┘
```

## 工具管理与监控

```python
# app/services/tool_registry.py
list_tools(status)      # 列出所有工具，可按 status 过滤
get_tool(tool_name)     # 获取单个工具详情
register_tool(...)      # 注册或更新工具
enable_tool(tool_name)  # status → "registered"
disable_tool(tool_name) # status → "disabled"
delete_tool(tool_name)  # 从表中删除
health_check_tool(name) # 执行健康检查并更新状态
health_check_all()      # 对所有工具执行健康检查
sync_capabilities(name) # 重新同步工具能力
```

## 工具必须实现的端点

每个工具必须实现以下端点以被 Controller 管理:

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 返回 200 表示服务正常 |
| `/tool/invoke` | POST | 接收 `{capability, input, trace_id}`，返回执行结果 |
| `/tool/capabilities` | GET | 返回 `{capabilities: [...]}` 声明支持的能力 |

端点地址通过 `tool.yaml` (如 `tools/code-index/tool.yaml`) 声明，然后注册到 Controller 的 `tool_registry` 表。