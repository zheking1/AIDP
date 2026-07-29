# importer-tool API 与 Capability 设计

## 1. 工具协议接口

```text
GET  /health
GET  /tool/manifest
GET  /tool/capabilities
POST /tool/invoke
```

## 2. Capability 清单

| Capability | 权限 | 说明 | MVP |
|------------|------|------|-----|
| `importer.import` | `importer:write` | 单次导入（自动全流程） | 是 |
| `importer.import_batch` | `importer:write` | 批量导入目录 | 是 |
| `importer.classify` | `importer:read` | 仅分类，不导入 | 是 |
| `importer.preview` | `importer:read` | 预览导入清单 | 是 |
| `importer.status` | `importer:read` | 查询导入任务状态 | 是 |
| `importer.history` | `importer:read` | 查询导入历史 | 是 |

## 3. `/tool/invoke` 调用协议

```text
POST /tool/invoke
Content-Type: application/json
X-Trace-Id: trace_xxx
```

### 3.1 `importer.import` — 单次导入

请求：

```json
{
  "capability": "importer.import",
  "parameters": {
    "source": {
      "type": "text",
      "content": "# 架构总览\n\n系统采用微服务架构..."
    },
    "user_id": "u_001",
    "project_id": 1,
    "scope": "personal",
    "auto_confirm": false
  }
}
```

或 URL 来源：

```json
{
  "capability": "importer.import",
  "parameters": {
    "source": {
      "type": "url",
      "url": "https://example.com/docs/architecture.md",
      "name": "architecture-overview"
    }
  }
}
```

或文件来源：

```json
{
  "capability": "importer.import",
  "parameters": {
    "source": {
      "type": "file",
      "path": "D:/Project/docs/architecture-overview.md"
    }
  }
}
```

响应（auto_confirm=false 时返回需要确认的信息）：

```json
{
  "success": true,
  "data": {
    "session_id": "imp_001",
    "status": "awaiting_confirmation",
    "classification": {
      "type": "knowledge",
      "confidence": "high",
      "title": "架构总览",
      "suggested_tags": ["architecture", "topology"],
      "suggested_category": "architecture/overview"
    },
    "quality_check": {
      "passed": true,
      "issues": [],
      "summary": { "total": 0, "errors": 0, "warnings": 0 }
    }
  }
}
```

用户确认后调用同一接口，带上 `confirm` 参数：

```json
{
  "capability": "importer.import",
  "parameters": {
    "session_id": "imp_001",
    "confirm": {
      "type": "knowledge",
      "tags": ["architecture", "topology"],
      "category": "architecture/overview",
      "skip_quality_warnings": true
    }
  }
}
```

最终响应：

```json
{
  "success": true,
  "data": {
    "session_id": "imp_001",
    "status": "completed",
    "result": {
      "target_type": "knowledge",
      "target_id": "doc_abc123",
      "target_url": "/knowledge/documents/doc_abc123",
      "checksum": "sha256:xxx",
      "version": "v1"
    },
    "summary": "已导入知识文档「架构总览」"
  }
}
```

### 3.2 `importer.import_batch` — 批量导入

请求：

```json
{
  "capability": "importer.import_batch",
  "parameters": {
    "source": {
      "type": "directory",
      "path": "D:/Project/RuoYi-Cloud-Plus/docs",
      "pattern": "**/*.md",
      "ignore": ["**/node_modules/**", "**/.git/**"]
    }
  }
}
```

响应（首批返回分类结果清单）：

```json
{
  "success": true,
  "data": {
    "session_id": "imp_batch_002",
    "status": "awaiting_confirmation",
    "items": [
      {
        "path": "architecture-overview.md",
        "classification": { "type": "knowledge", "title": "架构总览", "confidence": "high" },
        "quality": { "passed": true, "issues": [] }
      },
      {
        "path": "coding-standards.md",
        "classification": { "type": "rule", "title": "编码标准", "confidence": "medium" },
        "quality": { "passed": true, "issues": [{"severity": "warning", "message": "行过长"}] }
      }
    ],
    "summary": {
      "total": 42,
      "knowledge": 30,
      "rule": 8,
      "plan": 4,
      "with_warnings": 3,
      "blocked": 0
    }
  }
}
```

### 3.3 `importer.classify` — 仅分类

```json
{
  "capability": "importer.classify",
  "parameters": {
    "content": "# 架构总览..."
  }
}
```

```json
{
  "success": true,
  "data": {
    "type": "knowledge",
    "confidence": "high",
    "title": "架构总览",
    "suggested_tags": ["architecture", "topology"],
    "suggested_category": "architecture/overview"
  }
}
```

### 3.4 `importer.preview` — 预览导入清单

```json
{
  "capability": "importer.preview",
  "parameters": {
    "session_id": "imp_batch_002",
    "filter": {
      "types": ["knowledge"],
      "status": "ready"
    }
  }
}
```

```json
{
  "success": true,
  "data": {
    "items": [...],
    "summary": { "total": 30, "confirmed": 0 }
  }
}
```

### 3.5 `importer.status` — 查询导入任务状态

```json
{
  "capability": "importer.status",
  "parameters": {
    "session_id": "imp_batch_002"
  }
}
```

### 3.6 `importer.history` — 查询导入历史

```json
{
  "capability": "importer.history",
  "parameters": {
    "user_id": "u_001",
    "limit": 20
  }
}
```

## 4. 错误码

| 错误码 | retryable | 说明 |
|--------|:---------:|------|
| `INVALID_SOURCE` | 否 | 来源参数错误 |
| `SOURCE_FETCH_FAILED` | 是 | URL/文件读取失败 |
| `CLASSIFY_FAILED` | 否 | 无法识别内容类型 |
| `QUALITY_BLOCKED` | 否 | 质量检查未通过 |
| `PERSIST_FAILED` | 是 | 存储失败 |
| `SESSION_NOT_FOUND` | 否 | 导入会话不存在 |
| `DUPLICATE_SKIPPED` | 否 | 内容已存在且无变更 |
