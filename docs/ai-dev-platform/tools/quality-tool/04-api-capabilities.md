# quality-tool API 与 Capability 设计

## 1. 工具协议接口

```text
GET  /health
GET  /tool/manifest
GET  /tool/capabilities
POST /tool/invoke
```

## 2. Capability 清单

| Capability | 权限 | 说明 | MVP |
|---|---|---|---|
| `quality.check` | `quality:check` | 执行完整质量检查 | 是 |
| `quality.parse_build_log` | `quality:parse` | 解析构建日志 | 是 |
| `quality.parse_test_log` | `quality:parse` | 解析测试日志 | 是 |
| `quality.result.get` | `quality:read` | 获取检查结果 | 是 |
| `quality.ruleset.get` | `quality:read` | 获取规则集 | 是 |
| `quality.ruleset.validate` | `quality:write` | 校验规则集 | 是 |

## 3. 执行质量检查

```text
POST /api/quality/check
```

请求：

```json
{
  "workspace_id": "ws_001",
  "project_id": "proj_erp",
  "ruleset_id": "typescript-node-default",
  "input_object_key": "projects/demo.zip",
  "checks": ["build", "test", "lint"],
  "sandbox_profile": "default"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "result_id": "qr_001",
    "passed": false,
    "summary": {
      "total": 2,
      "errors": 1,
      "warnings": 1
    },
    "issues": [
      {
        "severity": "error",
        "check_type": "build",
        "file": "src/services/order-service.ts",
        "line": 42,
        "column": 18,
        "message": "TS2339: Property 'status' does not exist on type 'OrderDto'",
        "suggested_fix": "检查 DTO 字段是否已重命名，并同步调用方。",
        "source": "typescript"
      }
    ]
  }
}
```

## 4. 解析构建日志

```text
POST /api/quality/parse-build-log
```

请求：

```json
{
  "workspace_id": "ws_001",
  "project_id": "proj_erp",
  "parser": "typescript",
  "raw_log": "TS2339: Property 'status' does not exist...",
  "check_type": "build"
}
```

## 5. 查询结果

```text
GET /api/quality/results/{result_id}
```

必须校验 workspace/project。

## 6. 规则集接口

```text
GET  /api/quality/rulesets
GET  /api/quality/rulesets/{ruleset_id}
POST /api/quality/rulesets/validate
```

## 7. `/tool/invoke` 映射

| capability | 内部服务 | API 等价 |
|---|---|---|
| `quality.check` | `QualityCheckService.check` | `POST /api/quality/check` |
| `quality.parse_build_log` | `QualityCheckService.parseBuildLog` | `POST /api/quality/parse-build-log` |
| `quality.parse_test_log` | `QualityCheckService.parseTestLog` | parse test log |
| `quality.result.get` | `QualityResultService.getResult` | `GET /api/quality/results/{id}` |
| `quality.ruleset.get` | `RulesetService.getRuleset` | `GET /api/quality/rulesets/{id}` |
| `quality.ruleset.validate` | `RulesetService.validate` | `POST /api/quality/rulesets/validate` |

## 8. 错误码

| 错误码 | retryable | 说明 |
|---|---:|---|
| `VALIDATION_ERROR` | 否 | 参数错误 |
| `RULESET_NOT_FOUND` | 否 | 规则集不存在 |
| `RULESET_INVALID` | 否 | 规则集非法 |
| `PARSER_NOT_FOUND` | 否 | 解析器不存在 |
| `PARSE_FAILED` | 否 | 解析失败 |
| `SANDBOX_UNAVAILABLE` | 是 | sandbox 不可用 |
| `QUALITY_CHECK_FAILED` | 否 | 检查失败 |
