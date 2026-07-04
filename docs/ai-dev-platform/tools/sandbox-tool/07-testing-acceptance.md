# sandbox-tool 测试与验收

## 1. 测试目标

测试必须证明：

- 工具协议兼容 controller。
- 任务创建、执行、查询、日志、产物可用。
- 默认无网络。
- 镜像白名单、资源限制和超时生效。
- 容器和临时目录可清理。
- Node/TypeScript、Python、SQL 验证基础能力可用。

## 2. 测试分层

| 类型 | 覆盖 | 必须 |
|---|---|---|
| 单元测试 | 策略、状态机、资源限制转换 | 是 |
| Repository 测试 | job/log/artifact 表 | 是 |
| API 测试 | job 创建、查询、日志、产物 | 是 |
| 集成测试 | Docker 执行 shell/python | 是 |
| 端到端测试 | Node build、Python test、SQL validate | 是 |
| 安全测试 | 无网络、白名单、超时、清理 | 是 |
| 性能测试 | hello world 和查询延迟 | MVP 基线 |

## 3. 单元测试

### 3.1 ImagePolicyService

- 白名单镜像允许。
- 非白名单镜像拒绝。
- latest tag 默认拒绝。
- job_type 和 image 不匹配拒绝。

### 3.2 ResourceLimitService

- timeout 超上限拒绝。
- memory 超上限拒绝。
- cpu 超上限拒绝。
- 默认值正确填充。

### 3.3 JobStateService

- pending 可进入 running。
- running 可进入 succeeded/failed/timeout。
- 终态不可修改。
- lost 状态可由恢复流程设置。

### 3.4 LogCollector

- stdout 写入对象存储。
- stderr 写入对象存储。
- 超过大小被截断。
- summary 正确生成。

## 4. API 测试

### 4.1 创建任务

- 缺少 workspace_id 返回 400。
- 白名单外 image 返回 `IMAGE_NOT_ALLOWED`。
- network 不允许返回 `VALIDATION_ERROR`。
- 成功创建返回 job_id。

### 4.2 查询任务

- 已存在 job 返回详情。
- 其它项目 job 返回 403 或 404。
- 不存在 job 返回 404。

### 4.3 查询日志

- tail 参数生效。
- stdout/stderr 区分。
- 无权限不能读日志。

### 4.4 查询产物

- 构建产物可列出。
- 下载产物需权限校验。

## 5. 集成测试

### 5.1 Shell echo

步骤：

1. 创建 shell job，命令输出 `hello`。
2. 等待任务完成。
3. 查询日志。

期望：

- status=succeeded。
- exit_code=0。
- stdout 包含 hello。

### 5.2 Python hello world

步骤：

1. 调用 `sandbox.run.python`。
2. 输入 `print("hello")`。

期望：

- status=succeeded。
- stdout 包含 hello。

### 5.3 Timeout

步骤：

1. 创建 sleep 任务。
2. timeout_seconds=1。

期望：

- status=timeout。
- error_code=`JOB_TIMEOUT`。
- 容器被清理。

### 5.4 默认无网络

步骤：

1. 创建尝试访问外网的任务。
2. 默认 network none。

期望：

- 外网访问失败。
- 任务不突破网络限制。

## 6. 端到端测试

### 6.1 Node/TypeScript build

步骤：

1. 上传 Node/TypeScript 示例项目 zip。
2. 调用 `sandbox.build.node`。
3. 查询任务。
4. 查询日志和产物。

期望：

- 成功项目 status=succeeded。
- 失败项目 status=failed 且有 failure_summary。
- coverage、test-results 或 dist 产物按规则采集。

### 6.2 Python test

步骤：

1. 上传 Python/FastAPI 示例项目 zip。
2. 调用 `sandbox.test.python`。
3. 查询任务。
4. 查询日志和产物。

期望：

- 成功项目 status=succeeded。
- 失败项目 status=failed 且有 failure_summary。
- coverage 或 reports 产物按规则采集。

### 6.3 SQL validate

步骤：

1. 调用 `sandbox.sql.validate` 执行正确 DDL。
2. 再执行错误 SQL。

期望：

- 正确 SQL succeeded。
- 错误 SQL failed，返回数据库错误 message。
- 临时数据库容器清理。

## 7. 安全验收

必须覆盖：

- 非白名单镜像拒绝。
- latest tag 默认拒绝。
- privileged 不允许。
- host network 不允许。
- Docker socket 不挂载。
- 超时强杀。
- 临时目录清理。
- 日志大小限制。
- 产物大小限制。

## 8. 性能验收

| 指标 | 目标 |
|---|---:|
| Python hello world P95 | < 5s |
| Shell echo P95 | < 5s |
| job 查询 P95 | < 200ms |
| 10 个并发轻量任务 | 无服务崩溃 |

## 9. 最终验收清单

- [ ] `tool.yaml` 合法。
- [ ] `openapi.yaml` 覆盖全部 API。
- [ ] `/health` 可用。
- [ ] `/tool/manifest` 可用。
- [ ] `/tool/capabilities` 可用。
- [ ] Python hello world 可执行。
- [ ] Node/TypeScript 示例可测试。
- [ ] 超时任务被终止。
- [ ] 默认无网络测试通过。
- [ ] 白名单镜像测试通过。
- [ ] 容器和临时目录清理通过。
- [ ] controller managed 联调通过。
