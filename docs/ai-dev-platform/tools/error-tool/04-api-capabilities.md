# error-tool API 与 Capability 设计

## 1. Capability 列表

| capability | 权限 | REST 映射 |
|---|---|---|
| `error.record` | `error:write` | `POST /api/errors` |
| `error.search` | `error:read` | `POST /api/errors/search` |
| `error.link_solution` | `error:write` | `POST /api/errors/{id}/solution` |
| `error.resolve` | `error:write` | `POST /api/errors/{id}/resolve` |
| `error.export_pattern` | `asset:write` | `POST /api/errors/{id}/export-pattern` |

## 2. POST /api/errors

请求：

```json
{
  "source_tool": "sandbox-tool",
  "source_run_id": "run_01",
  "error_type": "auto",
  "title": "TypeScript compilation failure",
  "raw_log": "TS2339: Property 'status' does not exist...",
  "environment": {
    "node": "20",
    "pnpm": "9",
    "os": "linux"
  },
  "metadata": {
    "package": "aidp-controller",
    "command": "pnpm test"
  },
  "tags": ["typescript", "compile"]
}
```

响应：

```json
{
  "id": "err_01",
  "error_type": "typescript_compile",
  "status": "open",
  "fingerprint": "sha256:...",
  "normalized": {
    "main_message": "TS2339: Property 'status' does not exist on type 'OrderDto'",
    "file_path": "src/services/order.ts",
    "line_number": 42,
    "symbol": "status"
  },
  "raw_log_uri": "logs/ws_01/prj_01/err_01.log"
}
```

## 3. POST /api/errors/search

请求：

```json
{
  "query": "TS2339 Property status does not exist on type OrderDto",
  "raw_log": "TS2339: Property 'status' does not exist...",
  "error_type": "typescript_compile",
  "include_workspace": true,
  "include_archived": false,
  "top_k": 5
}
```

响应：

```json
{
  "items": [
    {
      "id": "err_old_01",
      "score": 0.93,
      "error_type": "typescript_compile",
      "title": "DTO 字段重命名导致属性不存在",
      "normalized_message": "TS2339: Property 'status' does not exist on type 'OrderDto'",
      "root_cause": "OrderDto 字段 status 改名为 approvalStatus 后调用方未同步修改。",
      "solution": {
        "fix_steps": [
          "将 status 替换为 approvalStatus",
          "补充 DTO 映射测试"
        ],
        "verified_count": 3
      },
      "source_refs": ["error://err_old_01", "git://commit/abc123"]
    }
  ]
}
```

## 4. POST /api/errors/{id}/solution

请求：

```json
{
  "root_cause": "DTO 类型字段已重命名，但 service 层仍引用旧字段。",
  "fix_steps": [
    "同步更新 service 层字段访问",
    "重新执行 pnpm test"
  ],
  "changed_files": ["packages/controller/src/services/order.service.ts"],
  "patch_summary": "同步 DTO 字段名",
  "applicable_versions": {
    "node": "20",
    "typescript": "5.x"
  },
  "risk_notes": "需要确认接口响应字段是否也同步调整。"
}
```

响应：

```json
{
  "id": "sol_01",
  "error_case_id": "err_01",
  "status": "analyzed",
  "created_at": "2026-06-28T10:00:00Z"
}
```

## 5. POST /api/errors/{id}/resolve

请求：

```json
{
  "solution_id": "sol_01",
  "verified_by": "sandbox-tool",
  "verification_ref": "sandbox://run_02",
  "comment": "pnpm test passed"
}
```

响应：

```json
{
  "id": "err_01",
  "status": "resolved",
  "resolved_at": "2026-06-28T10:00:00Z"
}
```

## 6. POST /api/errors/{id}/export-pattern

请求：

```json
{
  "asset_title": "TypeScript DTO 字段重命名修复方案",
  "asset_tags": ["typescript", "dto", "compile"],
  "visibility": "workspace"
}
```

响应：

```json
{
  "asset_id": "asset_01",
  "source_error_id": "err_01"
}
```

## 7. /tool/invoke 输入输出

`/tool/invoke` 的 `input` 与上述 REST body 相同。响应必须包装为工具协议：

```json
{
  "trace_id": "tr_01",
  "tool": "error-tool",
  "capability": "error.search",
  "success": true,
  "output": {
    "items": []
  },
  "elapsed_ms": 120
}
```

## 8. 错误码

| 错误码 | 场景 | retryable |
|---|---|---|
| `VALIDATION_ERROR` | raw_log/query 缺失、参数越界 | false |
| `FORBIDDEN` | 跨项目访问 | false |
| `NOT_FOUND` | error case 不存在 | false |
| `DEPENDENCY_UNAVAILABLE` | 数据库或存储不可用 | true |
| `TIMEOUT` | 检索超时 | true |
| `INTERNAL_ERROR` | 未预期异常 | false |
