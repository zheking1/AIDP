# sandbox-tool 需求说明

## 1. 背景

AI 生成代码后必须经过运行、编译或测试验证，否则很容易留下语法错误、依赖缺失、SQL 错误和构建失败。直接让 controller 或宿主机执行 AI 生成的命令风险极高，因此需要独立的 `sandbox-tool` 承担代码执行和编译验证。

`sandbox-tool` 是 AI 编程闭环中的安全执行层。它只接受结构化任务，使用白名单镜像和严格资源限制，在隔离环境中执行任务，并返回结构化结果。

## 2. 产品目标

### 2.1 核心目标

- 支持 Shell、Python、SQL 轻量执行。
- 支持 Node/TypeScript 项目构建和测试。
- 支持 Python 项目测试。
- 支持 Docker/Containerd 隔离执行。
- 默认禁止外网。
- 支持 CPU、内存、磁盘、进程数、超时限制。
- 支持 stdout、stderr、退出码、产物、资源使用统计。
- 支持 standalone 和 controller managed 两种运行方式。

### 2.2 非目标

MVP 不做：

- 不提供开放式远程终端。
- 不默认支持任意镜像。
- 不默认挂载 Docker socket。
- 不默认开放外网。
- 不执行 controller 传来的原始拼接 shell 字符串。
- 不做 Kubernetes 调度，后续可增强。
- 不做 Android/Flutter 重型构建镜像，后续扩展。

## 3. 用户场景

### 3.1 轻量脚本验证

AI 生成 Python 函数或 Shell 命令后，调用 `sandbox.run.python` 或 `sandbox.run.shell` 验证输出。

验收口径：

- 任务在容器内执行。
- 默认无网络。
- 返回 exit_code、stdout、stderr。
- 超时被终止。

### 3.2 Node/TypeScript 项目构建和测试

AI 修改 TypeScript/Fastify 代码后，把项目压缩包或工作区快照交给 `sandbox.build.node` 执行 `pnpm test`。

验收口径：

- 使用白名单 Node 镜像。
- 支持输入 zip 解压。
- 返回完整日志 URI。
- 返回测试报告和构建产物。

### 3.3 Python 项目测试

AI 修改 Python/FastAPI 或 RAG 工具代码后，调用 `sandbox.test.python` 执行 `pytest` 或配置的测试命令。

验收口径：

- 使用白名单 Python 镜像。
- 支持输入 zip 解压。
- 支持缓存目录作为只读或受控挂载，默认不允许联网下载依赖。
- 返回结构化失败摘要。

### 3.4 SQL 验证

AI 生成 DDL/DML 后，使用临时 PostgreSQL 或 MySQL 容器验证语法和基础约束。

验收口径：

- 临时数据库任务结束后销毁。
- 返回执行成功或失败位置。
- 禁止连接生产数据库。

## 4. 功能需求

### 4.1 创建执行任务

必须支持：

- job_type。
- image。
- command array。
- input artifact。
- environment。
- timeout_seconds。
- resource_limits。
- network_policy。
- output rules。

所有命令必须以数组形式传递，避免字符串拼接注入。

### 4.2 执行环境隔离

必须支持：

- 临时工作目录。
- 容器只挂载任务目录。
- 默认只读根文件系统，必要路径例外。
- 禁止特权容器。
- 禁止 host network。
- 禁止默认挂载宿主 Docker socket。
- 容器结束后清理。

### 4.3 资源限制

必须支持：

- CPU limit。
- memory limit。
- disk limit。
- timeout。
- stdout/stderr 最大大小。
- 最大产物大小。

超过限制必须终止任务，并返回明确错误码。

### 4.4 镜像策略

必须支持镜像白名单：

- `aidp/shell:ubuntu-22.04`
- `aidp/python:3.12`
- `aidp/node:20`
- `aidp/python:3.12`
- `aidp/postgres-test:16`

默认禁止 `latest` tag，开发模式可配置允许。

### 4.5 日志和产物

必须采集：

- stdout。
- stderr。
- exit_code。
- duration_ms。
- max_memory_mb。
- artifact list。
- failure summary。

完整日志写入对象存储，响应只返回摘要和 URI。

## 5. 安全需求

必须：

- 默认 `network=none`。
- 镜像白名单。
- 禁止 privileged。
- 禁止 hostPath 任意挂载。
- 禁止 command 字符串拼接。
- 超时强杀。
- 清理容器和临时目录。
- 限制日志和产物大小。

禁止：

- controller 直接执行命令。
- 默认开放外网。
- 默认挂载 Docker socket。
- 允许用户指定任意镜像。
- 允许任务访问平台数据库凭据。

## 6. 非功能需求

### 6.1 性能

- Shell/Python hello world P95 小于 5 秒。
- Node/TypeScript 示例项目测试结果完整返回。
- 任务查询 P95 小于 200ms。
- 日志下载支持大文件，不一次性加载进内存。

### 6.2 可靠性

- 任务失败不能影响服务进程。
- 服务重启后可查询历史任务。
- running 任务在服务重启后必须标记为 `lost` 或重新对账。
- 清理任务必须可重试。

### 6.3 可观测性

日志必须包含：

- `trace_id`
- `job_id`
- `workspace_id`
- `project_id`
- `job_type`
- `image`
- `status`
- `elapsed_ms`
- `error_code`

## 7. MVP 验收范围

- 工具协议接口可用。
- 创建和查询 sandbox job。
- Shell echo 可执行。
- Python hello world 可执行。
- Node/TypeScript 示例项目可测试。
- 超时任务被终止。
- 默认无网络。
- 日志可查询。
- controller 托管安装可用。
