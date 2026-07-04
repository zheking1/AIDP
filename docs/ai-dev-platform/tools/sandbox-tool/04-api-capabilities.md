# sandbox-tool API 与 Capability 设计

## 1. API 原则

所有接口必须：

- 支持 `X-Trace-Id`。
- 返回统一响应。
- 任务创建必须校验策略。
- 查询日志和产物必须校验 workspace/project。
- 不返回宿主机真实路径。

## 2. 工具协议接口

```text
GET  /health
GET  /tool/manifest
GET  /tool/capabilities
POST /tool/invoke
```

## 3. Capability 清单

| Capability | 权限 | 说明 | MVP |
|---|---|---|---|
| `sandbox.run` | `sandbox:run` | 通用受控执行 | 是 |
| `sandbox.run.shell` | `sandbox:run` | Shell 片段执行 | 是 |
| `sandbox.run.python` | `sandbox:run` | Python 片段执行 | 是 |
| `sandbox.sql.validate` | `sandbox:run` | SQL 临时验证 | 是 |
| `sandbox.build.node` | `sandbox:build` | Node/TypeScript 构建和测试 | 是 |
| `sandbox.test.python` | `sandbox:build` | Python 项目测试 | 是 |
| `sandbox.job.get` | `sandbox:read` | 查询任务详情 | 是 |
| `sandbox.job.logs` | `sandbox:read` | 查询任务日志 | 是 |
| `sandbox.job.cancel` | `sandbox:run` | 取消任务 | 增强 |

## 4. 业务 API

### 4.1 创建任务

```text
POST /api/sandbox/jobs
```

请求：

```json
{
  "workspace_id": "ws_001",
  "project_id": "proj_erp",
  "job_type": "node_build",
  "image": "aidp/node:20",
  "command": ["pnpm", "test"],
  "input_object_key": "projects/demo.zip",
  "timeout_seconds": 600,
  "resource_limits": {
    "cpu": "2",
    "memory_mb": 4096,
    "disk_mb": 10240,
    "network": "none"
  },
  "artifact_rules": [
    "coverage/**",
    "test-results/**",
    "dist/**"
  ]
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

### 4.2 查询任务

```text
GET /api/sandbox/jobs/{job_id}
```

响应：

```json
{
  "success": true,
  "data": {
    "job_id": "job_001",
    "status": "failed",
    "job_type": "node_build",
    "exit_code": 1,
    "stdout_uri": "local://logs/job_001/stdout.log",
    "stderr_uri": "local://logs/job_001/stderr.log",
    "artifacts": [],
    "resource_usage": {
      "duration_ms": 18234,
      "max_memory_mb": 1200
    },
    "error_code": "EXECUTION_FAILED",
    "failure_summary": "TypeScript check failed in packages/controller/src/server.ts"
  }
}
```

### 4.3 查询日志

```text
GET /api/sandbox/jobs/{job_id}/logs?stream=stdout&tail=200
```

响应：

```json
{
  "success": true,
  "data": {
    "job_id": "job_001",
    "stream": "stdout",
    "truncated": false,
    "content": "...",
    "full_log_uri": "local://logs/job_001/stdout.log"
  }
}
```

### 4.4 查询产物

```text
GET /api/sandbox/jobs/{job_id}/artifacts
```

### 4.5 下载产物

```text
GET /api/sandbox/jobs/{job_id}/artifacts/{artifact_id}/download
```

必须校验权限，并且不能泄露本地绝对路径。

### 4.6 取消任务

```text
POST /api/sandbox/jobs/{job_id}/cancel
```

MVP 可不实现，但 API 设计预留。

## 5. Capability 输入输出

### 5.1 `sandbox.run.python`

输入：

```json
{
  "workspace_id": "ws_001",
  "project_id": "proj_erp",
  "code": "print('hello')",
  "timeout_seconds": 30
}
```

输出：

```json
{
  "job_id": "job_001",
  "status": "succeeded",
  "exit_code": 0,
  "stdout": "hello\n",
  "stderr": ""
}
```

### 5.2 `sandbox.build.node`

输入：

```json
{
  "workspace_id": "ws_001",
  "project_id": "proj_erp",
  "input_object_key": "projects/demo.zip",
  "package_manager": "pnpm",
  "commands": ["pnpm install --offline", "pnpm test", "pnpm build"],
  "timeout_seconds": 600
}
```

输出返回 job 结果，完整日志通过 URI 获取。

### 5.3 `sandbox.test.python`

输入：

```json
{
  "workspace_id": "ws_001",
  "project_id": "proj_erp",
  "input_object_key": "projects/rag-tool.zip",
  "commands": ["pytest"],
  "timeout_seconds": 600
}
```

输出返回 job 结果，完整日志通过 URI 获取。

### 5.4 `sandbox.sql.validate`

输入：

```json
{
  "workspace_id": "ws_001",
  "project_id": "proj_erp",
  "database": "postgres",
  "sql": "create table demo(id bigint primary key);"
}
```

输出：

```json
{
  "job_id": "job_001",
  "status": "succeeded",
  "exit_code": 0,
  "message": "SQL executed successfully"
}
```

## 6. `/tool/invoke` 映射

| capability | 内部服务 | API 等价 |
|---|---|---|
| `sandbox.run` | `SandboxJobService.createJob` | `POST /api/sandbox/jobs` |
| `sandbox.run.shell` | `SandboxInvokeService.runShell` | create shell job |
| `sandbox.run.python` | `SandboxInvokeService.runPython` | create python job |
| `sandbox.sql.validate` | `SandboxInvokeService.validateSql` | create sql job |
| `sandbox.build.node` | `SandboxInvokeService.buildNode` | create node build job |
| `sandbox.test.python` | `SandboxInvokeService.testPython` | create python test job |
| `sandbox.job.get` | `SandboxJobService.getJob` | `GET /api/sandbox/jobs/{id}` |
| `sandbox.job.logs` | `SandboxJobService.getLogs` | `GET /api/sandbox/jobs/{id}/logs` |

## 7. 错误码

| 错误码 | retryable | 说明 |
|---|---:|---|
| `VALIDATION_ERROR` | 否 | 参数错误 |
| `FORBIDDEN` | 否 | 无权限 |
| `IMAGE_NOT_ALLOWED` | 否 | 镜像不允许 |
| `COMMAND_NOT_ALLOWED` | 否 | 命令不允许 |
| `RESOURCE_LIMIT_EXCEEDED` | 否 | 资源请求超过上限 |
| `JOB_TIMEOUT` | 是 | 任务超时 |
| `EXECUTION_FAILED` | 否 | 任务执行失败 |
| `ARTIFACT_TOO_LARGE` | 否 | 产物过大 |
| `LOG_LIMIT_EXCEEDED` | 否 | 日志被截断 |
| `DEPENDENCY_UNAVAILABLE` | 是 | Docker 或数据库不可用 |
| `INTERNAL_ERROR` | 是 | 未预期错误 |
