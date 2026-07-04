# memory-tool API 与 Capability 设计

## 1. 通用约定

所有 API 必须遵守 [工具协议](../../common/tool-contract.md)：

- 提供 `/health`、`/tool/manifest`、`/tool/capabilities`、`/tool/invoke`。
- 所有 `/tool/invoke` 请求必须包含 `trace_id`、`capability`、`context`、`input`。
- controller 调用前做权限检查，工具内部仍必须做 scope 二次校验。

## 2. Capability 列表

| capability | 权限 | REST 映射 | 说明 |
|---|---|---|---|
| `memory.upsert` | `memory:write` | `POST /api/memories` | 新增或更新记忆 |
| `memory.search` | `memory:read` | `POST /api/memories/search` | 检索记忆 |
| `memory.get_context` | `memory:read` | `POST /api/context-packages` | 生成上下文包 |
| `memory.save_summary` | `memory:write` | `POST /api/session-summaries` | 保存会话摘要 |
| `memory.expire` | `memory:write` | `POST /api/memories/{id}/expire` | 标记过期 |
| `memory.review` | `memory:write` | `POST /api/memories/{id}/review` | 审核记忆 |

## 3. POST /api/memories

### 请求

```json
{
  "scope": "project",
  "memory_type": "coding_standard",
  "key": "api-response-wrapper",
  "title": "接口统一返回 ApiResponse",
  "content": "所有 Fastify route handler 必须返回 ApiResponse<T>，禁止直接返回实体对象。",
  "summary": "接口必须统一使用 ApiResponse<T>。",
  "tags": ["fastify", "api", "standard"],
  "importance": 90,
  "confidence": 0.95,
  "status": "approved",
  "source_type": "user",
  "source_ref": "manual://project-rule",
  "expires_at": null
}
```

### 响应

```json
{
  "id": "mem_01HXX",
  "scope": "project",
  "memory_type": "coding_standard",
  "key": "api-response-wrapper",
  "title": "接口统一返回 ApiResponse",
  "status": "approved",
  "created_at": "2026-06-28T10:00:00Z",
  "updated_at": "2026-06-28T10:00:00Z"
}
```

### 校验规则

- `scope` 必须是 `global/workspace/project/session`。
- `memory_type` 必须在允许枚举内。
- `content` 必填且不超过配置 `memory.maxContentBytes`。
- `importance` 范围为 0-100。
- `confidence` 范围为 0-1。
- `source_type=ai_generated` 时如果未传 status，默认 `pending_review`。

## 4. POST /api/memories/search

### 请求

```json
{
  "query": "新增订单审批接口时需要遵守哪些项目规范",
  "scopes": ["session", "project", "workspace", "global"],
  "memory_types": ["coding_standard", "business_rule", "api_contract"],
  "tags": ["order"],
  "status": ["approved"],
  "importance_min": 50,
  "top_k": 10
}
```

### 响应

```json
{
  "items": [
    {
      "id": "mem_01HXX",
      "scope": "project",
      "memory_type": "api_contract",
      "title": "订单接口返回格式",
      "summary": "订单接口统一返回 ApiResponse<T>。",
      "content": "所有订单接口必须返回 ApiResponse<T>。",
      "score": 0.91,
      "importance": 90,
      "source_ref": "manual://project-rule",
      "updated_at": "2026-06-28T10:00:00Z"
    }
  ],
  "total": 1
}
```

## 5. POST /api/context-packages

### 请求

```json
{
  "task": "为 ERP 项目新增销售订单审批接口",
  "max_tokens": 3000,
  "include_pending": false,
  "memory_types": [
    "coding_standard",
    "business_rule",
    "database_rule",
    "api_contract",
    "architecture_decision"
  ],
  "output_format": "markdown"
}
```

### 响应

```json
{
  "package_id": "ctx_01HXX",
  "task": "为 ERP 项目新增销售订单审批接口",
  "token_estimate": 1280,
  "max_tokens": 3000,
  "sections": [
    {
      "name": "project_rules",
      "title": "项目规范",
      "content": "- 所有接口必须返回 ApiResponse<T>。",
      "source_refs": ["memory://mem_01HXX"],
      "token_estimate": 120
    }
  ],
  "rendered_markdown": "## 项目规范\n- 所有接口必须返回 ApiResponse<T>。",
  "source_refs": [
    {
      "id": "mem_01HXX",
      "type": "memory",
      "title": "接口统一返回 ApiResponse"
    }
  ],
  "omitted_items": []
}
```

## 6. POST /api/session-summaries

### 请求

```json
{
  "session_id": "ses_01HXX",
  "title": "订单审批接口开发会话摘要",
  "summary": "本轮决定新增 order_approval 表，接口统一使用 ApiResponse。",
  "decisions": [
    "审批状态使用 PENDING/APPROVED/REJECTED",
    "Controller 返回 ApiResponse<T>"
  ],
  "changed_files": [
    "src/routes/order-approval.routes.ts"
  ],
  "next_steps": [
    "补充审批流单元测试"
  ],
  "active": true
}
```

### 响应

```json
{
  "id": "sum_01HXX",
  "session_id": "ses_01HXX",
  "version": 3,
  "active": true,
  "created_at": "2026-06-28T10:00:00Z"
}
```

## 7. POST /api/memories/{id}/expire

请求：

```json
{
  "reason": "规则已被新版接口规范替代"
}
```

响应：

```json
{
  "id": "mem_01HXX",
  "status": "expired",
  "expired_at": "2026-06-28T10:00:00Z"
}
```

## 8. POST /api/memories/{id}/review

请求：

```json
{
  "action": "approve",
  "comment": "规则确认有效",
  "importance": 85,
  "confidence": 0.9
}
```

响应：

```json
{
  "id": "mem_01HXX",
  "status": "approved",
  "reviewed_at": "2026-06-28T10:00:00Z"
}
```

## 9. /tool/invoke 示例

```json
{
  "trace_id": "tr_01HXX",
  "capability": "memory.get_context",
  "context": {
    "tenant_id": "ten_01",
    "workspace_id": "ws_01",
    "project_id": "prj_erp",
    "session_id": "ses_01",
    "user_id": "usr_01"
  },
  "input": {
    "task": "新增销售订单审批接口",
    "max_tokens": 3000
  }
}
```

## 10. 错误码

| 错误码 | 场景 | retryable |
|---|---|---|
| `VALIDATION_ERROR` | 缺少 task、content、scope 不合法 | false |
| `FORBIDDEN` | 跨 workspace/project 访问 | false |
| `NOT_FOUND` | memory 或 summary 不存在 | false |
| `CONFLICT` | 同一 key 并发写冲突 | true |
| `DEPENDENCY_UNAVAILABLE` | PostgreSQL 不可用 | true |
| `TIMEOUT` | 检索或上下文生成超时 | true |
| `INTERNAL_ERROR` | 未预期异常 | false |
