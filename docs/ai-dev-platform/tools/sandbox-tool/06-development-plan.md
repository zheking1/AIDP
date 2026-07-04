# sandbox-tool 开发计划

## 1. 总体策略

`sandbox-tool` 必须安全优先。开发顺序不能先追求支持更多语言，而要先把工具协议、任务状态、镜像白名单、资源限制、日志采集和清理闭环打牢。

## 2. 里程碑

| 里程碑 | 目标 | 交付物 |
|---|---|---|
| M0 | 工程骨架 | TypeScript + Fastify 或 Go、配置、健康检查、统一错误 |
| M1 | 工具协议 | `tool.yaml`、manifest、capabilities、invoke |
| M2 | Job 模型 | job/log/artifact 表、状态机、查询接口 |
| M3 | Docker 执行 | 容器创建、资源限制、日志采集、清理 |
| M4 | 轻量执行 | shell、python capability |
| M5 | 项目验证 | Node/TypeScript build capability、Python test capability |
| M6 | SQL 验证 | 临时数据库验证 |
| M7 | 安全和联调 | 无网络、超时、白名单、controller 联调 |

## 3. M0 工程骨架

任务：

- 创建项目。
- 配置 TypeScript + Fastify 或 Go HTTP 服务、PostgreSQL migration、OpenAPI。
- 增加统一响应和错误模型。
- 增加 trace filter。
- 增加配置模型。

验收：

- `/health` 可用。
- Docker 不可用时健康检查能体现依赖状态。
- 日志包含 trace_id。

## 4. M1 工具协议

任务：

- 编写 `tool.yaml`。
- 编写 `config.example.yaml`。
- 实现 `/tool/manifest`。
- 实现 `/tool/capabilities`。
- 实现 `/tool/invoke` 分发。

验收：

- capability 包含 `sandbox.run.python`、`sandbox.build.node` 和 `sandbox.test.python`。
- unknown capability 返回结构化错误。

## 5. M2 Job 模型

任务：

- 创建 `st_sandbox_job`。
- 创建 `st_sandbox_log`。
- 创建 `st_sandbox_artifact`。
- 实现 job 创建和查询。
- 实现状态机。

验收：

- 可创建 pending job。
- 状态流转合法。
- 终态不可修改。

## 6. M3 Docker 执行

任务：

- 实现 DockerExecutionService。
- 实现 ImagePolicyService。
- 实现 ResourceLimitService。
- 实现 NetworkPolicyService。
- 实现 WorkspaceMaterializer。
- 实现 LogCollector。
- 实现 CleanupService。

验收：

- 白名单外镜像被拒绝。
- 默认 network none。
- 超时 kill。
- 容器和临时目录被清理。

## 7. M4 轻量执行

任务：

- 实现 ShellRunner。
- 实现 PythonRunner。
- 实现 `sandbox.run.shell`。
- 实现 `sandbox.run.python`。

验收：

- shell echo 成功。
- python hello world 成功。
- 无限 sleep 超时终止。

## 8. M5 项目验证

任务：

- 实现 NodeBuildRunner。
- 实现 PythonTestRunner。
- 支持 input zip 解压。
- 支持 artifact rules。
- 收集 coverage、test-results、dist、reports 等产物。

验收：

- Node/TypeScript 示例项目可执行 `pnpm test`。
- Python 示例项目可执行 `pytest`。
- 编译失败返回日志和 failure_summary。

## 9. M6 SQL 验证

任务：

- 实现 SqlValidateRunner。
- 创建临时 PostgreSQL 容器。
- 执行 init sql 和 target sql。
- 捕获错误。
- 清理容器和 volume。

验收：

- 正确 DDL 成功。
- 错误 SQL 返回失败位置或错误 message。
- 不允许连接外部生产数据库。

## 10. M7 安全和联调

任务：

- controller 安装联调。
- MCP capability 调用。
- 安全测试。
- 性能基线。
- OpenAPI、examples、Dockerfile。

验收：

- controller 显示工具 UP。
- MCP 调用 `sandbox.run.python` 成功。
- 默认无网络测试通过。
- 清理任务测试通过。

## 11. AI 编码任务拆分

1. 创建工程骨架和公共错误模型。
2. 实现工具协议接口。
3. 创建 job/log/artifact 表。
4. 实现 job 创建、查询、状态机。
5. 实现策略服务。
6. 实现 DockerExecutionService。
7. 实现日志和产物采集。
8. 实现 shell/python runner。
9. 实现 node/python project runner。
10. 实现 sql validate runner。
11. 实现 `/tool/invoke` capability 映射。
12. 补齐测试、OpenAPI、examples、Dockerfile。

## 12. 风险控制

| 风险 | 控制方式 |
|---|---|
| 容器逃逸风险 | 禁止 privileged、host network、任意挂载 |
| 命令注入 | command array，禁止字符串拼接 |
| 外网访问 | 默认 network none |
| 资源耗尽 | CPU、内存、磁盘、日志、产物限制 |
| 清理失败 | CleanupService 可重试 |
| Docker 不可用 | 健康检查和结构化错误 |
