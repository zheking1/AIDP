# 集成流程文档

## 1. 概述

AIDP 系统采用**微服务 + MCP**架构，Controller 作为中央调度器，通过 HTTP 协议与各工具服务通信。本文档描述组件间的完整集成流程。

### 1.1 组件关系图

```
┌──────────────────────────────────────────────────────────┐
│                    AI 客户端层                             │
│  Claude Desktop / Cursor / VS Code / 自定义 MCP Client   │
└─────────────────────────┬────────────────────────────────┘
                          │ MCP JSON-RPC over HTTP
                          ▼
┌──────────────────────────────────────────────────────────┐
│                 Controller (8883)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │ Web UI       │  │ REST API     │  │ MCP Server      │ │
│  │ (Alpine.js)  │  │ (FastAPI)    │  │ (FastMCP)       │ │
│  └──────┬──────┘  └──────┬───────┘  └────────┬────────┘ │
│         │                │                    │          │
│         └────────────────┼────────────────────┘          │
│                          │                               │
│  ┌───────────────────────┴────────────────────────────┐  │
│  │              工具调度器 (tool_invoker)               │  │
│  └───────────────────────┬────────────────────────────┘  │
└──────────────────────────┼───────────────────────────────┘
                           │ HTTP POST /tool/invoke
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ sandbox-tool │  │knowledge-tool│  │ memory-tool  │
│ :18083       │  │ :18081       │  │ :18085       │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                ┌────────▼────────┐
                │   PostgreSQL    │
                │   (共享数据库)   │
                └─────────────────┘
```

## 2. 工具注册流程

### 2.1 工具注册（启动时）

```python
# 工具服务启动后，通过 REST API 注册到 Controller
POST /api/tools
{
    "name": "sandbox-tool",
    "endpoint": "http://127.0.0.1:18083",
    "displayName": "代码沙箱",
    "description": "安全执行 Python/Node.js 代码",
    "version": "0.1.0"
}
```

### 2.2 能力同步（注册后）

```python
# Controller 从工具获取能力列表
GET http://127.0.0.1:18083/tool/capabilities
Response: [
    {
        "name": "sandbox.execute",
        "description": "执行代码",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string", "enum": ["python", "javascript"]}
            }
        }
    }
]
```

### 2.3 健康检查（定期）

```python
# Controller 定期检查工具健康状态
GET http://127.0.0.1:18083/health
Response: {"status": "ok", "tool": "sandbox-tool", "version": "0.1.0"}
```

## 3. 工具调用流程

### 3.1 REST API 调用

```
客户端 → POST /api/tools/{tool_name}/invoke
         Body: {"capability": "sandbox.execute", "arguments": {"code": "print(1)"}}
              │
              ▼
Controller: tool_invoker.invoke_tool()
         1. 查找 tool_registry 表
         2. 获取工具端点
         3. POST {endpoint}/tool/invoke
              │
              ▼
Tool Service: POST /tool/invoke
         1. 解析请求
         2. 路由到处理函数
         3. 执行业务逻辑
         4. 返回结果
              │
              ▼
Controller: 记录调用日志 → 返回结果给客户端
```

### 3.2 MCP 调用

```
AI 客户端 → MCP call: invoke_tool_mcp("sandbox-tool", "sandbox.execute", '{"code": "print(1)"}')
              │
              ▼
Controller MCP Server:
         1. 验证会话
         2. 检查上下文已加载
         3. 调用 tool_invoker.invoke_tool()
         4. 返回 JSON 结果
```

### 3.3 工具调用请求/响应格式

**请求**:
```json
{
    "trace_id": "tr_abc123",
    "capability": "sandbox.execute",
    "context": {"user_id": 1, "project_id": "proj_123"},
    "input": {
        "code": "print('Hello, World!')",
        "language": "python"
    }
}
```

**响应**:
```json
{
    "trace_id": "tr_abc123",
    "tool": "sandbox-tool",
    "capability": "sandbox.execute",
    "success": true,
    "output": {
        "stdout": "Hello, World!\n",
        "stderr": "",
        "exitCode": 0
    },
    "error": null,
    "elapsed_ms": 142
}
```

## 4. MCP 5 阶段上下文管道

### 4.1 流程图

```
aidp_context(project_name, task)
    │
    ▼
Stage 0: 加载 Agent Instructions
    │  从 DB 查询 project 的 agent_instructions
    │  返回角色定义、约束规则
    │
    ▼
Stage 1: 意图分析
    │  调用 skill-router: analyze_intent
    │  识别任务类型、所需工具、查询词
    │
    ▼
Stage 2: 知识检索（并行）
    │  ├── memory-tool: memory.search
    │  ├── knowledge-tool: knowledge.search
    │  └── asset-tool: asset.search
    │
    ▼
Stage 3: 技能匹配
    │  调用 skill-router: skill_run
    │  匹配最佳技能模板
    │
    ▼
Stage 4: 上下文组装
    │  合并所有阶段结果
    │  生成系统提示 + 用户消息
    │
    ▼
返回组装后的上下文
```

### 4.2 上下文输出格式

```json
{
    "system_prompt": "你是 AIDP 开发助手...",
    "user_message": "当前任务：修复登录页面的 cookie 问题",
    "tools": ["sandbox.execute", "knowledge.search", "memory.search"],
    "context": {
        "project": {"name": "my-app", "tech_stack": "Python + FastAPI"},
        "instructions": {"role": "全栈开发者", "constraints": ["..."]},
        "knowledge": [...],
        "memory": [...],
        "skills": [...]
    }
}
```

## 5. 数据流

### 5.1 用户认证流程

```
用户访问 Web UI
    │
    ▼
GET /login → 登录页面
    │
    ▼
POST /api/auth/login
    │  验证用户名/密码
    │  创建 session
    │
    ▼
Set-Cookie: aidp_session=xxx
    │
    ▼
后续请求自动携带 session cookie
    │
    ▼
get_current_user_from_request() 验证 session
```

### 5.2 知识库数据流

```
用户上传文档
    │
    ▼
POST /api/knowledge/bases/{id}/documents
    │
    ▼
Controller: 创建 KnowledgeDocument 记录
    │
    ▼
调用 knowledge-tool: knowledge.index
    │  分块 → 生成 Embedding → 存储到向量表
    │
    ▼
用户搜索知识
    │
    ▼
GET /api/knowledge/search?q=xxx
    │
    ▼
Controller: 调用 knowledge-tool: knowledge.search
    │  向量相似度搜索 → 返回相关文档
    │
    ▼
返回搜索结果
```

### 5.3 项目数据流

```
用户创建项目
    │
    ▼
POST /api/projects
    │  创建 Project 记录
    │  设置 owner_id, visibility
    │
    ▼
用户添加成员
    │
    ▼
POST /api/projects/{id}/members
    │  创建 ProjectMember 记录
    │  设置 role (admin/editor/viewer)
    │
    ▼
用户访问项目
    │
    ▼
_project_filter() 过滤
    │  owner_id == user_id
    │  OR user is member
    │  OR visibility == "public"
    │
    ▼
返回有权限的项目列表
```

## 6. 错误处理

### 6.1 工具调用错误

```json
{
    "trace_id": "tr_abc123",
    "tool": "sandbox-tool",
    "capability": "sandbox.execute",
    "success": false,
    "output": null,
    "error": {
        "code": "EXECUTION_ERROR",
        "message": "SyntaxError: invalid syntax",
        "details": {"line": 3, "column": 1}
    },
    "elapsed_ms": 45
}
```

### 6.2 MCP 会话错误

```json
{
    "error": {
        "code": "CONTEXT_REQUIRED",
        "message": "必须先调用 aidp_context 加载上下文",
        "hint": "调用 aidp_context(project_name, task)"
    }
}
```

### 6.3 工具不可用错误

```json
{
    "error": {
        "code": "TOOL_UNAVAILABLE",
        "message": "工具 'sandbox-tool' 当前不可用",
        "details": {"status": "unhealthy", "last_check": "2026-07-23T10:00:00Z"}
    }
}
```

## 7. 关键文件索引

| 文件 | 用途 |
|------|------|
| `apps/controller/app/mcp/server.py` | MCP Server 和工具函数 |
| `apps/controller/app/mcp/session_manager.py` | 会话管理和上下文强制 |
| `apps/controller/app/services/tool_invoker.py` | 工具调用 HTTP 客户端 |
| `apps/controller/app/services/tool_registry.py` | 工具注册表 CRUD |
| `apps/controller/app/api/tools.py` | REST API 管理工具 |
| `apps/controller/app/services/context_pipeline.py` | 5 阶段上下文管道 |
| `apps/controller/app/core/auth.py` | 认证和 session 管理 |
| `apps/controller/app/web/routes.py` | Web 路由和页面渲染 |
| `tools/*/app/api/tool.py` | 各工具的标准 API 契约 |
