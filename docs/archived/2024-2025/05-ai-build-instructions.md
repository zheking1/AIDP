# 给 AI 开发代理的执行指南

本文件用于直接交给 AI 编程代理。AI 必须按“主服务 + 可选工具”的架构开发本平台。

## 1. 开发目标

开发一套开源友好的 AI 编程基础设施：

```text
aidp-controller + N 个可选安装工具
```

第一阶段必须完成：

- `aidp-controller`
- 工具安装与注册机制
- MCP Skill 映射
- `knowledge-tool`
- `asset-tool`
- `sandbox-tool`
- `quality-tool`
- `memory-tool`
- 编程闭环演示

## 2. 强制架构约束

必须遵守：

1. 不把所有工具逻辑写死在 controller 中。
2. 每个工具必须有 `tool.yaml`。
3. 每个工具必须能独立运行。
4. 每个工具必须能被 controller 以 managed 或 remote 模式接管。
5. MCP Skill 必须来自 tool capability。
6. 工具调用必须记录 trace_id。
7. 沙箱执行必须放在 `sandbox-tool` 中，不能由 controller 直接执行宿主机命令。
8. 默认不引入 Nacos、Kubernetes、RabbitMQ。

## 3. 推荐仓库结构

```text
ai-dev-platform/
  controller/
  tools/
    mock-tool/
    knowledge-tool/
    asset-tool/
    sandbox-tool/
    quality-tool/
    memory-tool/
  sdk/
    tool-sdk-java/
    tool-sdk-python/
    tool-sdk-typescript/
  deploy/
    compose/
      core.yml
      knowledge.yml
      coding.yml
      full.yml
  docs/
  examples/
```

## 4. 第一阶段任务顺序

### Step 1：controller 基础工程

实现：

- 统一响应结构。
- 错误码。
- trace_id。
- workspace/project。
- 用户和基础权限。
- PostgreSQL 迁移。
- 管理后台基础页面。

验收：

- controller 可启动。
- 可创建 workspace/project。
- `/health` 正常。

### Step 2：工具协议

实现：

- `tool.yaml` schema。
- `GET /tool/manifest` 协议。
- `GET /tool/capabilities` 协议。
- `POST /tool/invoke` 协议。
- tool-sdk 基础类型。

验收：

- mock-tool 可暴露 manifest 和 capability。
- controller 能读取并校验 mock-tool。

### Step 3：工具注册与安装

实现 controller 表：

- `tool_registry`
- `tool_capability`
- `tool_invocation`

实现接口：

- `POST /api/tools/install`
- `GET /api/tools`
- `GET /api/tools/{name}/capabilities`
- `POST /api/tools/invoke`

验收：

- 可安装 mock-tool。
- 可启用、停用工具。
- 可调用 mock capability。

### Step 4：MCP 映射

实现：

- `/api/mcp/invoke`
- capability 到 MCP Skill 的映射。
- 权限检查。
- trace 和审计。

验收：

- MCP 可调用 mock-tool capability。
- 错误、超时、权限失败都返回结构化 JSON。

### Step 5：knowledge-tool

实现：

- `tool.yaml`。
- 文档上传。
- Markdown/TXT 解析。
- chunk splitter。
- embedding client 抽象。
- PGVector 检索。
- `knowledge.search` capability。

验收：

- knowledge-tool 可独立运行。
- controller 可安装 knowledge-tool。
- 上传文档后可检索。
- 检索结果包含 source、score、citation_id。

### Step 6：asset-tool

实现：

- `tool.yaml`。
- 代码片段 CRUD。
- 模板元数据管理。
- 历史方案管理。
- `asset.search` capability。

验收：

- asset-tool 可独立运行。
- controller 可安装 asset-tool。
- 可检索 TypeScript/Shell/SQL 代码片段。

### Step 7：sandbox-tool

实现：

- `tool.yaml`。
- Docker/Containerd 执行器。
- 镜像白名单。
- 资源限制。
- 网络隔离。
- stdout/stderr 日志。
- `sandbox.run`。
- `sandbox.build.node`。

验收：

- sandbox-tool 可独立运行。
- controller 可安装 sandbox-tool。
- Python hello world 可执行。
- Node/TypeScript 示例项目可测试。
- 超时任务会被终止。

### Step 8：quality-tool

实现：

- `tool.yaml`。
- ruleset 配置。
- TypeScript/Node/Python 测试日志解析。
- 测试失败解析。
- `quality.check`。

验收：

- quality-tool 可独立运行。
- controller 可安装 quality-tool。
- 构建失败返回结构化 issue。

### Step 9：memory-tool

实现：

- `tool.yaml`。
- 项目记忆。
- 会话摘要。
- 上下文包。
- `memory.get_context`。

验收：

- 项目上下文隔离。
- MCP 调用前可加载上下文包。

### Step 10：端到端编程闭环

演示：

```text
上传 ERP 规则文档
  -> knowledge.search
  -> asset.search
  -> AI 生成代码
  -> sandbox.build.node
  -> quality.check
  -> AI 修复
```

验收：

- 每一步都可通过 trace_id 追踪。
- 所有引用文档带 citation_id。
- 所有校验错误为结构化 issue。

## 5. 不允许的实现方式

- 不允许 controller 直接执行不可信代码。
- 不允许工具没有 manifest。
- 不允许工具只有内部函数而没有独立 API。
- 不允许 MCP Skill 写死在代码里。
- 不允许检索结果没有来源。
- 不允许沙箱默认开放网络。
- 不允许提交真实密钥。
- 不允许用户必须全量安装工具才能使用平台。

## 6. 输出要求

AI 每完成一个阶段必须输出：

```text
完成内容：
- ...

变更文件：
- ...

验证方式：
- ...

剩余风险：
- ...

下一步：
- ...
```

如果测试未运行，必须说明原因。

## 7. MVP 验收清单

MVP 完成必须满足：

- controller 可启动。
- mock-tool 可安装。
- knowledge-tool 可安装并检索文档。
- asset-tool 可安装并检索代码片段。
- sandbox-tool 可安装并执行代码。
- quality-tool 可安装并返回 issue。
- memory-tool 可安装并返回上下文。
- MCP 能调用所有已安装工具的 capability。
- 用户可以只安装 knowledge-tool 使用文档知识库。
- 用户可以安装 coding profile 使用完整编程闭环。
