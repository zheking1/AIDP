# sandbox-tool 模块设计

## 1. 推荐代码结构

```text
sandbox-tool/
  tool.yaml
  openapi.yaml
  config.example.yaml
  migrations/
  src/
    server.ts
    api/
      health.routes.ts
      tool-protocol.routes.ts
      sandbox-job.routes.ts
      sandbox-log.routes.ts
      sandbox-artifact.routes.ts
    services/
      sandbox-job.service.ts
      sandbox-invoke.service.ts
      job-dispatcher.ts
      job-state.service.ts
      permission-scope.service.ts
    execution/
      execution-runner.ts
      shell-runner.ts
      python-runner.ts
      node-build-runner.ts
      python-test-runner.ts
      sql-validate-runner.ts
      docker-execution.service.ts
      execution-result.ts
    policy/
      image-policy.service.ts
      command-policy.service.ts
      resource-limit.service.ts
      network-policy.service.ts
      environment-policy.service.ts
    io/
      workspace-materializer.ts
      log-collector.ts
      artifact-collector.ts
      object-storage.ts
      local-object-storage.ts
      cleanup.service.ts
    domain/
      models.ts
      enums.ts
    repository/
      sandbox-job.repository.ts
      sandbox-artifact.repository.ts
      sandbox-log.repository.ts
```

## 2. 模块职责

### 2.1 `api`

- 接收创建任务请求。
- 查询任务、日志和产物。
- 暴露工具协议接口。
- 做 DTO 校验。

### 2.2 `application`

- 创建任务。
- 状态流转。
- 调度执行。
- `/tool/invoke` capability 映射。

### 2.3 `execution`

- 根据 job_type 执行任务。
- 对接 Docker/Containerd。
- 捕获 exit_code。
- 判断 succeeded/failed/timeout。

### 2.4 `policy`

所有任务执行前必须经过策略校验：

- image allowlist。
- command allowlist 或 denylist。
- resource limits。
- network policy。
- env allowlist。

### 2.5 `io`

- 准备工作目录。
- 解压输入 zip。
- 写入脚本文件。
- 采集日志。
- 收集产物。
- 清理临时文件。

## 3. 领域对象

### 3.1 SandboxJob

字段职责：

- `id`：任务 ID。
- `workspaceId`：工作区。
- `projectId`：项目。
- `jobType`：shell、python、node_build、python_test、sql_validate。
- `image`：执行镜像。
- `command`：命令数组。
- `status`：任务状态。
- `exitCode`：退出码。
- `timeoutSeconds`：超时。
- `resourceLimits`：资源限制。
- `networkMode`：网络模式。
- `stdoutObjectKey`、`stderrObjectKey`：日志。
- `resourceUsage`：资源使用。

### 3.2 SandboxArtifact

- `jobId`。
- `artifactType`。
- `fileName`。
- `objectKey`。
- `fileSize`。
- `checksum`。

### 3.3 SandboxLog

- 保存日志摘要。
- 保存 stdout/stderr object key。
- 保存截断状态。

## 4. 状态机

```text
pending -> running -> succeeded
pending -> running -> failed
pending -> running -> timeout
pending -> canceled
running -> canceled
running -> lost
```

规则：

- 终态不可修改。
- timeout 必须有 started_at 和 finished_at。
- lost 用于服务重启后无法对账的 running 任务。

## 5. 执行器设计

### 5.1 ShellRunner

- 将脚本写入工作目录文件。
- command 固定为白名单 shell 入口。
- 禁止直接拼接用户字符串执行。

### 5.2 PythonRunner

- 将 Python 片段写入 `main.py`。
- 使用 Python 白名单镜像。
- 默认只允许本地标准库。

### 5.3 NodeBuildRunner

- 解压项目 zip。
- 根据策略执行 `pnpm install --offline`、`pnpm test`、`pnpm build` 或配置命令。
- 收集 `coverage`、`test-results`、`dist`、`reports` 等产物。

### 5.4 PythonTestRunner

- 解压项目 zip。
- 根据策略执行 `pytest`、`ruff`、`mypy` 或配置命令。
- 是否允许联网安装依赖由策略决定，默认使用预构建镜像或只读缓存。
- 收集 `coverage.xml`、`htmlcov`、`reports` 等产物。

### 5.5 SqlValidateRunner

- 创建临时数据库容器。
- 执行 SQL。
- 捕获错误位置和 message。
- 销毁数据库容器和 volume。

## 6. 策略服务

### 6.1 ImagePolicyService

必须校验：

- 镜像在 allowlist。
- tag 不为 latest，除非开发模式。
- capability 和镜像匹配。

### 6.2 ResourceLimitService

必须校验：

- timeout 不超过最大值。
- memory 不超过最大值。
- disk 不超过最大值。
- cpu 不超过最大值。

### 6.3 NetworkPolicyService

默认：

```text
network = none
```

只有策略 profile 允许时才可设置 `limited` 或 `default`。

## 7. 错误码

| 错误码 | 场景 |
|---|---|
| `IMAGE_NOT_ALLOWED` | 镜像不在白名单 |
| `COMMAND_NOT_ALLOWED` | 命令不允许 |
| `RESOURCE_LIMIT_EXCEEDED` | 请求资源超过上限 |
| `JOB_TIMEOUT` | 执行超时 |
| `EXECUTION_FAILED` | 容器执行失败 |
| `LOG_LIMIT_EXCEEDED` | 日志超限被截断 |
| `ARTIFACT_TOO_LARGE` | 产物过大 |
| `CLEANUP_FAILED` | 清理失败 |
| `DEPENDENCY_UNAVAILABLE` | Docker/数据库不可用 |

## 8. 可测试性要求

- DockerExecutionService 可用 fake runner 测试。
- 策略服务必须纯函数化，方便单测。
- LogCollector 使用临时文件测试。
- CleanupService 可重复执行。
