# knowledge-tool API 与 Capability 设计

## 1. API 设计原则

`knowledge-tool` 同时提供两类接口：

- 工具协议接口：供 `aidp-controller` 安装、发现、调用工具。
- 业务接口：供 standalone 模式或管理后台直接操作文档和索引。

所有接口必须：

- 支持 `X-Trace-Id` 请求头。
- 响应包含 `trace_id`。
- 使用统一错误模型。
- 校验 `workspace_id` 和 `project_id`。
- 不返回未授权数据。

## 2. 工具协议接口

### 2.1 `GET /health`

用途：健康检查。

响应：

```json
{
  "status": "UP",
  "tool": "knowledge-tool",
  "version": "0.1.0",
  "time": "2026-06-28T00:00:00Z",
  "dependencies": {
    "postgres": "UP",
    "vector_store": "UP",
    "storage": "UP",
    "embedding": "UP"
  }
}
```

### 2.2 `GET /tool/manifest`

用途：返回 `tool.yaml` 解析结果。

必须包含：

- metadata。
- runtime。
- dependencies。
- configSchema。
- capabilities。
- ui。

### 2.3 `GET /tool/capabilities`

用途：返回可调用 capability 列表。

响应示例：

```json
{
  "tool": "knowledge-tool",
  "version": "0.1.0",
  "capabilities": [
    {
      "name": "knowledge.search",
      "description": "Search indexed knowledge chunks.",
      "permission": "knowledge:search",
      "endpoint": "POST /api/knowledge/search",
      "timeout_ms": 3000,
      "input_schema": {},
      "output_schema": {}
    }
  ]
}
```

### 2.4 `POST /tool/invoke`

用途：统一 capability 调用入口。

请求：

```json
{
  "trace_id": "0190f6b7-0e24-7d3f-8c8a-5c3a9b6a1111",
  "capability": "knowledge.search",
  "context": {
    "tenant_id": "default",
    "workspace_id": "ws_001",
    "project_id": "proj_erp",
    "session_id": "sess_001",
    "user_id": "user_001"
  },
  "input": {
    "query": "销售订单审批接口字段规则",
    "top_k": 8,
    "search_mode": "hybrid"
  }
}
```

成功响应：

```json
{
  "trace_id": "0190f6b7-0e24-7d3f-8c8a-5c3a9b6a1111",
  "tool": "knowledge-tool",
  "capability": "knowledge.search",
  "success": true,
  "output": {
    "items": [],
    "degraded": false
  },
  "source_refs": [],
  "elapsed_ms": 120
}
```

失败响应：

```json
{
  "trace_id": "0190f6b7-0e24-7d3f-8c8a-5c3a9b6a1111",
  "tool": "knowledge-tool",
  "capability": "knowledge.search",
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "query is required",
    "details": {
      "field": "query"
    },
    "retryable": false
  },
  "elapsed_ms": 8
}
```

## 3. Capability 清单

| Capability | 权限 | 说明 | MVP |
|---|---|---|---|
| `document.create` | `knowledge:write` | 创建文档元数据 | 是 |
| `document.upload` | `knowledge:write` | 上传文件并创建文档 | 是 |
| `document.index` | `knowledge:index` | 创建索引任务 | 是 |
| `document.reindex` | `knowledge:index` | 重建索引 | 是 |
| `document.delete` | `knowledge:delete` | 删除文档 | 是 |
| `document.get` | `knowledge:read` | 查询文档详情 | 是 |
| `knowledge.search` | `knowledge:search` | 检索知识片段 | 是 |
| `knowledge.get_chunk` | `knowledge:read` | 获取 chunk 详情 | 是 |
| `knowledge.import_batch` | `knowledge:write` | 批量导入目录或 Git 文档 | 否 |

## 4. 业务 API

### 4.1 创建文档

```text
POST /api/documents
```

请求：

```json
{
  "workspace_id": "ws_001",
  "project_id": "proj_erp",
  "title": "销售订单审批规则",
  "doc_type": "business_flow",
  "visibility": "project",
  "version": "v1.0",
  "tags": ["erp", "order", "approval"],
  "source_uri": "local://imports/order-approval.md",
  "content": "# 销售订单审批规则\n...",
  "metadata": {
    "owner": "erp-team",
    "language": "zh-CN"
  }
}
```

响应：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "trace_id": "trace-id",
  "data": {
    "id": "doc_001",
    "index_status": "created",
    "checksum": "sha256:..."
  }
}
```

规则：

- `workspace_id` 必填。
- `visibility=project` 时 `project_id` 必填。
- `content`、`source_uri`、multipart file 至少提供一种。
- `doc_type` 必须属于允许枚举或配置白名单。

### 4.2 上传文档文件

```text
POST /api/documents/upload
Content-Type: multipart/form-data
```

表单字段：

| 字段 | 必填 | 说明 |
|---|---:|---|
| `file` | 是 | 文件 |
| `workspace_id` | 是 | 工作区 |
| `project_id` | 否 | 项目 |
| `title` | 否 | 不传则使用文件名 |
| `doc_type` | 是 | 文档类型 |
| `visibility` | 是 | 可见性 |
| `version` | 否 | 默认 `v1` |
| `tags` | 否 | 逗号分隔或 JSON |

### 4.3 查询文档

```text
GET /api/documents/{document_id}
```

查询参数：

- `workspace_id`
- `project_id`

返回文档元数据，不默认返回全文。

### 4.4 查询文档列表

```text
GET /api/documents
```

查询参数：

| 参数 | 说明 |
|---|---|
| `workspace_id` | 必填 |
| `project_id` | 可选 |
| `doc_type` | 可选 |
| `visibility` | 可选 |
| `tag` | 可选 |
| `index_status` | 可选 |
| `keyword` | 标题关键词 |
| `page` | 默认 1 |
| `page_size` | 默认 20，最大 100 |

### 4.5 索引文档

```text
POST /api/documents/{document_id}/index
```

请求：

```json
{
  "workspace_id": "ws_001",
  "project_id": "proj_erp",
  "force": false,
  "chunk_size": 800,
  "overlap": 120,
  "embedding_model": "mock-embedding-v1"
}
```

响应：

```json
{
  "success": true,
  "code": "OK",
  "trace_id": "trace-id",
  "data": {
    "job_id": "job_001",
    "status": "pending"
  }
}
```

### 4.6 查询索引任务

```text
GET /api/index-jobs/{job_id}
```

返回：

```json
{
  "success": true,
  "data": {
    "id": "job_001",
    "document_id": "doc_001",
    "status": "succeeded",
    "chunk_count": 12,
    "error_code": null,
    "error_message": null,
    "started_at": "2026-06-28T10:00:00Z",
    "finished_at": "2026-06-28T10:00:03Z"
  }
}
```

### 4.7 检索知识

```text
POST /api/knowledge/search
```

请求：

```json
{
  "workspace_id": "ws_001",
  "project_id": "proj_erp",
  "query": "销售订单审批接口字段规则",
  "doc_types": ["business_flow", "api_spec"],
  "tags": ["order"],
  "visibility": ["project", "workspace"],
  "top_k": 8,
  "search_mode": "hybrid",
  "min_score": 0.2,
  "include_content": true
}
```

响应：

```json
{
  "success": true,
  "code": "OK",
  "trace_id": "trace-id",
  "data": {
    "items": [
      {
        "chunk_id": "chunk_001",
        "document_id": "doc_001",
        "title": "销售订单审批规则",
        "content": "订单状态为 SUBMITTED 时可以发起审批...",
        "score": 0.86,
        "keyword_score": 0.72,
        "vector_score": 0.91,
        "version": "v1.0",
        "citation_id": "doc:doc_001:v:v1.0:chunk:3",
        "source_uri": "local://imports/order-approval.md",
        "heading_path": ["销售订单", "审批规则"],
        "source_start_line": 12,
        "source_end_line": 30,
        "metadata": {}
      }
    ],
    "degraded": false,
    "degrade_reason": null
  }
}
```

### 4.8 获取 chunk

```text
GET /api/knowledge/chunks/{chunk_id}
```

查询参数：

- `workspace_id`
- `project_id`

返回 chunk 详情。必须做权限校验。

### 4.9 删除文档

```text
DELETE /api/documents/{document_id}
```

请求参数：

- `workspace_id`
- `project_id`
- `purge=false`

默认软删除。`purge=true` 需要管理员权限。

## 5. `/tool/invoke` 映射规则

| capability | 内部服务方法 | 业务 API 等价 |
|---|---|---|
| `document.create` | `DocumentService.createDocument` | `POST /api/documents` |
| `document.upload` | `DocumentService.uploadDocument` | `POST /api/documents/upload` |
| `document.index` | `IndexingService.createIndexJob` | `POST /api/documents/{id}/index` |
| `document.reindex` | `IndexingService.reindexDocument` | `POST /api/documents/{id}/index force=true` |
| `document.delete` | `DocumentService.deleteDocument` | `DELETE /api/documents/{id}` |
| `document.get` | `DocumentService.getDocument` | `GET /api/documents/{id}` |
| `knowledge.search` | `SearchService.search` | `POST /api/knowledge/search` |
| `knowledge.get_chunk` | `SearchService.getChunk` | `GET /api/knowledge/chunks/{id}` |

## 6. tool.yaml capability 示例

```yaml
capabilities:
  - name: knowledge.search
    description: Search indexed document chunks.
    endpoint: POST /api/knowledge/search
    timeoutMs: 3000
    permission: knowledge:search
    inputSchema:
      type: object
      required: [query]
      properties:
        query:
          type: string
          minLength: 1
        workspace_id:
          type: string
        project_id:
          type: string
        top_k:
          type: integer
          default: 8
          minimum: 1
          maximum: 50
        search_mode:
          type: string
          enum: [keyword, vector, hybrid]
          default: hybrid
    outputSchema:
      type: object
      properties:
        items:
          type: array
        degraded:
          type: boolean
```

## 7. 错误码

| 错误码 | retryable | 说明 |
|---|---:|---|
| `VALIDATION_ERROR` | 否 | 参数错误 |
| `UNAUTHORIZED` | 否 | 未认证 |
| `FORBIDDEN` | 否 | 无权限 |
| `NOT_FOUND` | 否 | 资源不存在 |
| `CONFLICT` | 否 | 状态冲突或重复任务 |
| `SOURCE_NOT_FOUND` | 否 | 原始文件不存在 |
| `UNSUPPORTED_DOCUMENT_TYPE` | 否 | 不支持的文件类型 |
| `PARSE_FAILED` | 否 | 解析失败 |
| `EMBEDDING_FAILED` | 是 | embedding provider 失败 |
| `VECTOR_STORE_FAILED` | 是 | 向量库失败 |
| `DEPENDENCY_UNAVAILABLE` | 是 | 依赖不可用 |
| `TIMEOUT` | 是 | 调用超时 |
| `INTERNAL_ERROR` | 是 | 未预期错误 |

## 8. OpenAPI 生成要求

AI 编码工具实现时必须根据本文件生成 `openapi.yaml`，并至少覆盖：

- 所有业务 API。
- 所有工具协议 API。
- DTO schema。
- 错误响应 schema。
- 鉴权 header。
- trace header。

