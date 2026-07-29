# 完整 API 参考

## 1. 概述

AIDP Controller 提供三类 API：
1. **REST API** — Web UI 和外部集成使用
2. **MCP API** — AI 客户端使用
3. **工具 API** — 工具服务间通信使用

基础 URL: `http://localhost:8883`

## 2. 认证 API

### 2.1 登录

```
POST /api/auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}

Response: 200
{
    "message": "Login successful",
    "user": {
        "id": "c296edb3-...",
        "username": "admin",
        "role": "super_admin"
    }
}
```

### 2.2 登出

```
POST /api/auth/logout

Response: 200
{"message": "Logged out"}
```

### 2.3 获取当前用户

```
GET /api/auth/me

Response: 200
{
    "id": "c296edb3-...",
    "username": "admin",
    "email": "admin@example.com",
    "role": "super_admin",
    "nickname": "Admin"
}
```

## 3. 工具管理 API

### 3.1 列出工具

```
GET /api/tools

Response: 200
{
    "tools": [
        {
            "id": "tool_001",
            "name": "sandbox-tool",
            "endpoint": "http://127.0.0.1:18083",
            "status": "healthy",
            "capabilities": [...],
            "last_health_check": "2026-07-23T10:00:00Z"
        }
    ]
}
```

### 3.2 注册工具

```
POST /api/tools
Content-Type: application/json

{
    "name": "my-tool",
    "endpoint": "http://127.0.0.1:18086",
    "displayName": "我的工具",
    "description": "工具描述",
    "version": "0.1.0"
}

Response: 201
{
    "id": "tool_002",
    "name": "my-tool",
    "status": "registered"
}
```

### 3.3 调用工具

```
POST /api/tools/{tool_name}/invoke
Content-Type: application/json

{
    "capability": "sandbox.execute",
    "arguments": {
        "code": "print('Hello, World!')",
        "language": "python"
    }
}

Response: 200
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
    "elapsed_ms": 142
}
```

### 3.4 健康检查

```
GET /api/tools/health/all

Response: 200
{
    "tools": {
        "sandbox-tool": {"status": "healthy", "last_check": "..."},
        "knowledge-tool": {"status": "healthy", "last_check": "..."}
    }
}
```

## 4. 项目管理 API

### 4.1 列出项目

```
GET /api/projects?limit=100

Response: 200
{
    "items": [
        {
            "id": "proj_001",
            "name": "my-project",
            "description": "项目描述",
            "visibility": "private",
            "owner_id": "user_001",
            "created_at": "2026-07-23T10:00:00Z"
        }
    ],
    "total": 1
}
```

### 4.2 创建项目

```
POST /api/projects
Content-Type: application/json

{
    "name": "new-project",
    "description": "新项目",
    "visibility": "private",
    "tech_stack": "Python + FastAPI"
}

Response: 201
{
    "id": "proj_002",
    "name": "new-project"
}
```

### 4.3 获取项目详情

```
GET /api/projects/{project_id}

Response: 200
{
    "id": "proj_001",
    "name": "my-project",
    "description": "项目描述",
    "visibility": "private",
    "owner_id": "user_001",
    "members": [...],
    "created_at": "2026-07-23T10:00:00Z"
}
```

## 5. 知识库 API

### 5.1 列出知识库

```
GET /api/knowledge/bases

Response: 200
{
    "items": [
        {
            "id": "kb_001",
            "name": "项目文档",
            "description": "项目技术文档",
            "document_count": 10,
            "chunk_count": 500
        }
    ]
}
```

### 5.2 创建知识库

```
POST /api/knowledge/bases
Content-Type: application/json

{
    "name": "新知识库",
    "description": "知识库描述",
    "chunking_strategy": "fixed",
    "chunk_size": 500
}

Response: 201
{
    "id": "kb_002",
    "name": "新知识库"
}
```

### 5.3 搜索知识

```
GET /api/knowledge/search?q=关键词&limit=10

Response: 200
{
    "results": [
        {
            "document_id": "doc_001",
            "chunk_id": "chunk_001",
            "content": "匹配的文本内容...",
            "score": 0.85,
            "metadata": {...}
        }
    ]
}
```

## 6. 记忆系统 API

### 6.1 列出记忆

```
GET /api/memory/entries?limit=100

Response: 200
{
    "items": [
        {
            "id": "mem_001",
            "content": "记忆内容",
            "type": "fact",
            "importance": 0.8,
            "created_at": "2026-07-23T10:00:00Z"
        }
    ]
}
```

### 6.2 创建记忆

```
POST /api/memory/entries
Content-Type: application/json

{
    "content": "新的记忆内容",
    "type": "fact",
    "importance": 0.7,
    "metadata": {"source": "user_input"}
}

Response: 201
{
    "id": "mem_002",
    "content": "新的记忆内容"
}
```

## 7. 菜单 API

### 7.1 获取菜单

```
GET /api/menu

Response: 200
{
    "sidebar": [
        {
            "group": "home",
            "title": "首页",
            "icon": "fas fa-home",
            "items": [
                {
                    "id": "home-dashboard",
                    "label": "仪表盘",
                    "icon": "chart-pie",
                    "route": "/home"
                }
            ]
        }
    ],
    "header": [...],
    "user": [...],
    "project_switcher": {
        "enabled": true,
        "show_create": true,
        "create_label": "创建新项目"
    }
}
```

## 8. MCP API

### 8.1 MCP 端点

```
POST /mcp/
Content-Type: application/json

{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
}
```

### 8.2 MCP 工具列表

```json
{
    "tools": [
        {
            "name": "aidp_context",
            "description": "执行 5 阶段上下文管道",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "task": {"type": "string"},
                    "agent_type": {"type": "string"}
                },
                "required": ["project_name"]
            }
        },
        {
            "name": "invoke_tool_mcp",
            "description": "通用工具调度器",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string"},
                    "capability": {"type": "string"},
                    "arguments": {"type": "string"},
                    "user_id": {"type": "integer"}
                },
                "required": ["tool_name", "capability"]
            }
        },
        {
            "name": "list_registered_tools",
            "description": "列出所有已注册的工具"
        },
        {
            "name": "check_tool_health",
            "description": "检查工具健康状态",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string"}
                }
            }
        },
        {
            "name": "sync_tool_capabilities",
            "description": "同步工具能力定义",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string"}
                },
                "required": ["tool_name"]
            }
        },
        {
            "name": "aidp_init",
            "description": "初始化项目到 AIDP",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "description": {"type": "string"},
                    "tech_stack": {"type": "string"},
                    "nas_path": {"type": "string"}
                },
                "required": ["project_name"]
            }
        },
        {
            "name": "aidp_instructions",
            "description": "生成 subagent 专用指令",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "task": {"type": "string"},
                    "agent_type": {"type": "string"}
                },
                "required": ["project_name", "task"]
            }
        }
    ]
}
```

## 9. 健康检查 API

### 9.1 系统健康

```
GET /health

Response: 200
{
    "status": "UP",
    "service": "AIDP Controller",
    "version": "0.1.0",
    "timestamp": "2026-07-23T10:00:00Z"
}
```

## 10. 错误响应格式

```json
{
    "error": {
        "code": "TOOL_UNAVAILABLE",
        "message": "工具 'sandbox-tool' 当前不可用",
        "details": {
            "status": "unhealthy",
            "last_check": "2026-07-23T10:00:00Z"
        }
    }
}
```

### 10.1 常见错误码

| 错误码 | HTTP 状态码 | 说明 |
|--------|-----------|------|
| UNAUTHORIZED | 401 | 未认证 |
| FORBIDDEN | 403 | 无权限 |
| NOT_FOUND | 404 | 资源不存在 |
| TOOL_UNAVAILABLE | 503 | 工具不可用 |
| CONTEXT_REQUIRED | 400 | 需要先调用 aidp_context |
| EXECUTION_ERROR | 500 | 执行错误 |
