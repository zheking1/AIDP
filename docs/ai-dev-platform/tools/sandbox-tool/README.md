# sandbox-tool 文档索引

`sandbox-tool` 负责执行不可信代码、编译项目、验证 SQL、收集日志和产物。它必须作为独立工具运行，`aidp-controller` 只能通过工具协议调用它，不能直接在 controller 宿主机执行命令。

## 1. 必读文档

| 文档 | 内容 |
|---|---|
| [01-requirements.md](./01-requirements.md) | 需求说明、执行类型、安全边界、非功能需求 |
| [02-architecture.md](./02-architecture.md) | 沙箱架构、运行模式、执行流程、隔离策略 |
| [03-module-design.md](./03-module-design.md) | 模块职责、状态机、执行器、策略服务、清理服务 |
| [04-api-capabilities.md](./04-api-capabilities.md) | HTTP API、capability、请求响应、错误码 |
| [05-data-model.md](./05-data-model.md) | 任务表、日志表、产物表、策略配置、对象存储路径 |
| [06-development-plan.md](./06-development-plan.md) | 里程碑、任务拆分、风险控制 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 单元、集成、端到端、安全和性能验收 |
| [AI_IMPLEMENTATION.md](./AI_IMPLEMENTATION.md) | 给 AI 编码工具的实施入口 |

## 2. 工具定位

核心职责：

- 执行 Shell/Python/SQL 等轻量任务。
- 构建和测试 Node/TypeScript 项目。
- 执行 Python 测试任务。
- 在隔离容器内运行不可信代码。
- 限制 CPU、内存、磁盘、网络和运行时长。
- 采集 stdout、stderr、退出码、资源使用和产物。
- 为 `quality-tool` 提供编译和测试执行底座。

## 3. MVP Capability

| capability | 权限 | 说明 |
|---|---|---|
| `sandbox.run` | `sandbox:run` | 执行受控通用任务 |
| `sandbox.run.shell` | `sandbox:run` | 执行 Shell 片段 |
| `sandbox.run.python` | `sandbox:run` | 执行 Python 片段 |
| `sandbox.sql.validate` | `sandbox:run` | 在临时数据库验证 SQL |
| `sandbox.build.node` | `sandbox:build` | 构建或测试 Node/TypeScript 项目 |
| `sandbox.test.python` | `sandbox:build` | 执行 Python 项目测试 |
| `sandbox.job.get` | `sandbox:read` | 查询任务详情 |
| `sandbox.job.logs` | `sandbox:read` | 查询任务日志 |

## 4. 完成定义

实现完成后必须满足：

- 可 standalone 启动。
- 可被 `aidp-controller` 托管安装。
- 默认禁用外网。
- 只允许白名单镜像。
- Python hello world 可执行。
- Node/TypeScript 示例项目可测试。
- 超时任务被强制终止。
- 任务结束后容器和临时目录被清理。
- 日志和产物可查询。
