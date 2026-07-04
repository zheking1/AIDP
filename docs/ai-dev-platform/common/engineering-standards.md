# 工程开发规范

## 1. 技术栈约定

默认技术栈：

- Python 3.13
- FastAPI + FastMCP
- PostgreSQL + pgvector
- Redis
- SQLAlchemy 2.0 (async)
- OpenAPI

全栈统一 Python + FastAPI。所有工具和 controller 使用相同技术栈，降低维护成本。

## 2. 目录约定

```text
ai-dev-platform/
  apps/
    controller/
    admin-console/
    cli/
  packages/
    sdk/
    schemas/
  tools/
    <tool-name>/
      tool.yaml
      README.md
      openapi.yaml
      config.example.yaml
      src/
      tests/
      examples/
  deploy/
  docs/
```

## 3. API 约定

所有 API 返回：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {},
  "trace_id": "uuid"
}
```

异常返回：

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "query is required",
  "details": {},
  "trace_id": "uuid"
}
```

## 4. 数据库约定

- 所有表必须有 `id`。
- 所有项目数据必须有 `workspace_id` 和 `project_id`，除非是全局配置。
- 所有时间使用 `timestamptz`。
- JSON 扩展字段使用 `jsonb`。
- 数据迁移使用 migration 脚本；TypeScript 工程优先 Drizzle migration 或纯 SQL migration，Python 工程可用 Alembic。
- 禁止直接在代码中拼接 SQL。

## 5. 日志约定

日志必须包含：

- service/tool name
- trace_id
- workspace_id
- project_id
- capability
- elapsed_ms
- error_code

## 6. 测试要求

每个工具至少包含：

- manifest 解析测试。
- capability schema 测试。
- API controller 测试。
- service 单元测试。
- repository 集成测试。
- controller 安装联调测试。

## 7. AI 开发代理输出格式

每个阶段完成后必须输出：

```text
完成内容：
- ...

变更文件：
- ...

验证命令：
- ...

测试结果：
- ...

剩余风险：
- ...
```

## 8. 禁止事项

- 禁止绕过 controller 直接暴露不受控能力。
- 禁止工具返回无结构纯文本错误。
- 禁止跨项目读取数据。
- 禁止提交真实密钥。
- 禁止 sandbox 外的服务执行不可信代码。
- 禁止默认引入 Nacos、Kubernetes 等重型分布式组件。
