# AIDP 工具协议详细规范

## 1. 目标

本规范定义 `aidp-controller` 与所有可选工具之间的通信协议。任何工具只有满足本规范，才能被 controller 安装、发现、调用并映射为 MCP Skill。

## 2. 工具必须提供的文件

每个工具根目录必须包含：

```text
tool.yaml
README.md
openapi.yaml
config.example.yaml
Dockerfile
examples/
tests/
```

其中：

- `tool.yaml`：工具清单，controller 安装时读取。
- `openapi.yaml`：工具 HTTP API 文档。
- `config.example.yaml`：工具独立运行配置样例。
- `examples/`：最小可运行示例。
- `tests/`：工具自身测试。

## 3. tool.yaml 完整字段

```yaml
apiVersion: aidp.dev/v1
kind: Tool

metadata:
  name: knowledge-tool
  displayName: Knowledge Tool
  version: 0.1.0
  description: Document ingestion, indexing and retrieval.
  license: Apache-2.0
  homepage: https://example.com

runtime:
  modes:
    - standalone
    - managed
    - remote
  docker:
    image: aidp/knowledge-tool:0.1.0
    port: 8080
    healthPath: /health
  local:
    command: aidp-knowledge serve
    healthUrl: http://127.0.0.1:18081/health

dependencies:
  required:
    - postgresql
  optional:
    - pgvector
    - minio
    - qdrant

configSchema:
  type: object
  properties:
    databaseUrl:
      type: string
      required: true
    storageProvider:
      type: string
      enum: [local, minio, s3]
      default: local

capabilities:
  - name: knowledge.search
    description: Search indexed documents.
    endpoint: POST /api/knowledge/search
    timeoutMs: 3000
    permission: knowledge:search
    inputSchema:
      type: object
      required: [query]
      properties:
        query:
          type: string
        topK:
          type: integer
          default: 8
    outputSchema:
      type: object
      properties:
        items:
          type: array

ui:
  enabled: true
  entry: /ui/knowledge
```

## 4. 工具 HTTP 基础接口

### GET /health

必须返回：

```json
{
  "status": "UP",
  "tool": "knowledge-tool",
  "version": "0.1.0",
  "time": "2026-06-28T00:00:00Z"
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
  "trace_id": "uuid",
  "capability": "knowledge.search",
  "context": {
    "tenant_id": "uuid",
    "workspace_id": "uuid",
    "project_id": "uuid",
    "session_id": "uuid",
    "user_id": "uuid"
  },
  "input": {
    "query": "订单审批规则",
    "topK": 8
  }
}
```

响应：

```json
{
  "trace_id": "uuid",
  "tool": "knowledge-tool",
  "capability": "knowledge.search",
  "success": true,
  "output": {},
  "source_refs": [],
  "elapsed_ms": 120
}
```

## 5. 错误模型

错误响应必须统一：

```json
{
  "trace_id": "uuid",
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
  "elapsed_ms": 12
}
```

通用错误码：

- `VALIDATION_ERROR`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `NOT_FOUND`
- `CONFLICT`
- `DEPENDENCY_MISSING`
- `DEPENDENCY_UNAVAILABLE`
- `TIMEOUT`
- `EXECUTION_FAILED`
- `INTERNAL_ERROR`

## 6. 权限模型

permission 命名格式：

```text
<domain>:<action>
```

示例：

- `knowledge:search`
- `knowledge:index`
- `asset:search`
- `sandbox:run`
- `quality:check`
- `memory:read`

controller 在调用工具前做权限检查，工具内部也必须二次校验 workspace_id/project_id。

## 7. Trace 规范

所有请求必须携带 `trace_id`。如果外部没有传入，controller 生成。

工具必须：

- 日志打印 trace_id。
- 响应返回 trace_id。
- 调用下游工具时透传 trace_id。

## 8. 兼容性要求

工具版本升级必须遵守：

- patch 版本不得破坏 input/output schema。
- minor 版本可新增 capability。
- major 版本允许破坏性变更，但 controller 必须提示用户迁移。

