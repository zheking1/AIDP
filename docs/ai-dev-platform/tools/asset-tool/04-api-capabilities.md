# asset-tool API 设计

## 1. 工具协议接口

### GET /health

```json
{
  "status": "UP",
  "tool": "asset-tool",
  "version": "0.1.0",
  "time": "2026-06-30T00:00:00Z"
}
```

### GET /tool/manifest

返回 `tool.yaml` 解析后的 JSON。

### GET /tool/capabilities

返回 capability 列表。

### POST /tool/invoke

统一调用入口。

请求：

```json
{
  "trace_id": "tr_01",
  "capability": "asset.search",
  "context": {
    "workspace_id": "ws_01",
    "project_id": "prj_01",
    "user_id": "usr_01"
  },
  "input": {
    "query": "FastAPI 路由",
    "asset_type": "snippet",
    "language": "python",
    "top_k": 8
  }
}
```

响应：

```json
{
  "trace_id": "tr_01",
  "tool": "asset-tool",
  "capability": "asset.search",
  "success": true,
  "output": {
    "items": [
      {
        "id": "ast_001",
        "title": "FastAPI 路由模板",
        "asset_type": "snippet",
        "language": "python",
        "content": "from fastapi import APIRouter\nrouter = APIRouter()\n\n@router.get('/items')\nasync def list_items():\n    return []",
        "tags": ["fastapi", "router"],
        "score": 0.95
      }
    ],
    "total": 1
  },
  "elapsed_ms": 45
}
```

## 2. Capability 定义

### 2.1 asset.create

创建资产。

输入：

```json
{
  "title": "FastAPI 路由模板",
  "asset_type": "snippet",
  "language": "python",
  "content": "from fastapi import APIRouter\nrouter = APIRouter()",
  "tags": ["fastapi", "router"],
  "visibility": "workspace",
  "project_id": "prj_01",
  "variables": {}
}
```

输出：

```json
{
  "id": "ast_001",
  "title": "FastAPI 路由模板",
  "created_at": "2026-06-30T00:00:00Z"
}
```

### 2.2 asset.update

更新资产。

输入：

```json
{
  "id": "ast_001",
  "title": "FastAPI 路由模板 v2",
  "content": "from fastapi import APIRouter\nrouter = APIRouter(prefix='/api')"
}
```

### 2.3 asset.delete

删除资产（软删除）。

输入：

```json
{
  "id": "ast_001"
}
```

### 2.4 asset.get

查询资产详情。

输入：

```json
{
  "id": "ast_001"
}
```

### 2.5 asset.search

检索资产。

输入：

```json
{
  "query": "FastAPI 路由",
  "asset_type": "snippet",
  "language": "python",
  "tags": ["fastapi"],
  "search_mode": "keyword",
  "top_k": 8
}
```

输出：

```json
{
  "items": [
    {
      "id": "ast_001",
      "title": "FastAPI 路由模板",
      "asset_type": "snippet",
      "language": "python",
      "content": "...",
      "tags": ["fastapi", "router"],
      "score": 0.95
    }
  ],
  "total": 1
}
```

### 2.6 asset.list

列出资产。

输入：

```json
{
  "asset_type": "snippet",
  "language": "python",
  "page": 1,
  "page_size": 20
}
```

### 2.7 asset.render

渲染模板。

输入：

```json
{
  "id": "ast_001",
  "variables": {
    "prefix": "/api/v1",
    "table_name": "users"
  }
}
```

输出：

```json
{
  "rendered": "from fastapi import APIRouter\nrouter = APIRouter(prefix='/api/v1')\n\n@router.get('/users')\nasync def list_users():\n    return []"
}
```

## 3. 错误码

| 错误码 | 场景 |
|---|---|
| `VALIDATION_ERROR` | 参数或 schema 错误 |
| `UNAUTHORIZED` | 未登录 |
| `FORBIDDEN` | 无权限或跨项目访问 |
| `NOT_FOUND` | 资产不存在 |
| `INTERNAL_ERROR` | 未预期异常 |
