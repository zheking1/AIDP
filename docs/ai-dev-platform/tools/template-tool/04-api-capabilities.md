# template-tool API 与 Capability

## 1. Capability

| capability | 权限 | REST |
|---|---|---|
| `template.create` | `template:write` | `POST /api/templates` |
| `template.search` | `template:read` | `POST /api/templates/search` |
| `template.validate` | `template:read` | `POST /api/templates/{id}/validate` |
| `template.preview` | `template:read` | `POST /api/templates/{id}/preview` |
| `template.render` | `template:write` | `POST /api/templates/{id}/render` |
| `template.publish` | `template:write` | `POST /api/templates/{id}/publish` |

## 2. POST /api/templates

```json
{
  "name": "fastify-module",
  "display_name": "Fastify Module",
  "template_type": "module",
  "version": "1.0.0",
  "package_object_key": "templates/ws_01/fastify-module-1.0.0.zip",
  "visibility": "workspace",
  "tags": ["fastify", "typescript"],
  "frameworks": ["fastify"],
  "variables": [
    {
      "name": "packageName",
      "type": "string",
      "required": true,
      "regex": "^[a-z][a-z0-9_.]+$"
    }
  ]
}
```

响应：

```json
{
  "id": "tpl_01",
  "version_id": "tplv_01",
  "status": "draft"
}
```

## 3. POST /api/templates/search

请求支持 `query/template_type/frameworks/tags/top_k`。响应返回模板、版本、score 和变量 schema。

## 4. POST /api/templates/{id}/validate

返回：

```json
{
  "valid": true,
  "errors": [],
  "resolved_variables": {
    "packageName": "com.example.order",
    "moduleName": "order-service"
  }
}
```

## 5. POST /api/templates/{id}/preview

返回文件树、有限文本预览、warnings，不生成正式产物。

## 6. POST /api/templates/{id}/render

```json
{
  "version": "1.0.0",
  "variables": {
    "packageName": "com.example.order",
    "moduleName": "order-service"
  },
  "output_mode": "artifact_zip",
  "overwrite": false
}
```

响应：

```json
{
  "job_id": "rjob_01",
  "status": "succeeded",
  "output_uri": "renders/ws_01/prj_01/rjob_01.zip",
  "file_count": 24,
  "warnings": []
}
```

## 7. 错误码

| 错误码 | 场景 |
|---|---|
| `VALIDATION_ERROR` | 变量不合法、模板类型不合法 |
| `NOT_FOUND` | 模板或版本不存在 |
| `CONFLICT` | 模板版本已存在 |
| `FORBIDDEN` | 无权访问模板 |
| `EXECUTION_FAILED` | 渲染失败 |
| `DEPENDENCY_UNAVAILABLE` | 存储不可用 |
