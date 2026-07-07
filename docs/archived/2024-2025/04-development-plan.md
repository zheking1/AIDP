# AI 编程基础设施平台开发规划

## 1. 开发策略

本项目采用“主服务 + 可选工具”的开发策略。

优先级：

1. 先完成 `aidp-controller`。
2. 再完成工具安装、注册、调用协议。
3. 然后按工具逐个交付能力。
4. 最后做完整 AI 编程闭环。

不要一开始拆成多个强依赖服务，也不要把所有工具逻辑写死进 controller。

## 2. 里程碑

### M0：基础工程

目标：

- 建立 monorepo。
- 建立 controller 基础工程。
- 建立 PostgreSQL 数据库迁移。
- 建立统一 API 响应、错误码、trace_id。
- 建立基础管理后台。

交付物：

- `controller/`
- `deploy/compose/core.yml`
- `tool_registry` 表。
- `tool_capability` 表。
- 健康检查接口。

验收：

- 能启动 controller + postgres。
- 能创建 workspace/project。
- 能查看空工具列表。

### M1：工具协议与安装机制

目标：

- controller 能读取 `tool.yaml`。
- controller 能登记工具。
- controller 能调用工具标准接口。
- 工具 capability 能映射为 MCP Skill。

任务：

- 定义 `tool.yaml` schema。
- 实现 ToolManifestParser。
- 实现 ToolRegistry。
- 实现 ToolInstaller。
- 实现 ToolInvoker。
- 实现 `/api/tools/install`。
- 实现 `/api/tools/invoke`。
- 实现 `/api/mcp/invoke` 到 tool capability 的映射。

验收：

- 可安装一个 mock-tool。
- mock-tool 的 capability 出现在 controller 中。
- 可通过 MCP invoke 调用 mock capability。
- 调用日志有 trace_id。

### M2：knowledge-tool

目标：

- 完成文档知识库工具。

任务：

- 实现 `tools/knowledge-tool/tool.yaml`。
- 实现文档上传。
- 实现 Markdown/TXT 解析。
- 实现切片。
- 实现 embedding 抽象。
- 实现 PGVector 检索。
- 实现 `knowledge.search`。

验收：

- knowledge-tool 可独立启动。
- controller 可安装 knowledge-tool。
- 上传 Markdown 后可检索到片段。
- MCP 可调用 `knowledge.search`。
- 返回结果包含 source、score、citation_id。

### M3：asset-tool

目标：

- 完成代码资产工具。

任务：

- 实现 `tools/asset-tool/tool.yaml`。
- 实现代码片段 CRUD。
- 实现模板元数据管理。
- 实现历史方案管理。
- 实现 `asset.search`。

验收：

- asset-tool 可独立启动。
- controller 可安装 asset-tool。
- 可保存 TypeScript/Fastify Controller 片段。
- 可自然语言检索代码片段。
- MCP 可调用 `asset.search`。

### M4：sandbox-tool

目标：

- 完成沙箱执行工具。

任务：

- 实现 `tools/sandbox-tool/tool.yaml`。
- 实现 Docker/Containerd 执行器。
- 实现镜像白名单。
- 实现 CPU/内存/超时限制。
- 实现 stdout/stderr 采集。
- 实现 `sandbox.run`。
- 实现 `sandbox.build.node`。

验收：

- sandbox-tool 可独立启动。
- controller 可安装 sandbox-tool。
- 可执行 Python hello world。
- 可测试 Node/TypeScript 示例项目。
- 超时任务会被终止。
- 默认网络隔离。

### M5：quality-tool

目标：

- 完成质量校验工具。

任务：

- 实现 `tools/quality-tool/tool.yaml`。
- 实现规则集配置。
- 实现 TypeScript/Node/Python 测试日志解析。
- 实现测试失败解析。
- 实现 `quality.check`。
- 支持调用 sandbox-tool 执行校验命令。

验收：

- quality-tool 可独立启动。
- controller 可安装 quality-tool。
- 编译失败能返回结构化 issue。
- issue 包含 severity、file、line、message、suggested_fix。

### M6：memory-tool

目标：

- 完成上下文记忆工具。

任务：

- 实现项目长期记忆。
- 实现会话摘要。
- 实现上下文包生成。
- 实现 `memory.get_context`。

验收：

- 不同项目记忆隔离。
- MCP 调用前可加载项目上下文。
- 会话摘要能被后续任务引用。

### M7：编程闭环

目标：

- controller 编排 knowledge、asset、sandbox、quality、memory。

端到端流程：

```text
用户需求
  -> memory.get_context
  -> knowledge.search
  -> asset.search
  -> AI 生成代码
  -> sandbox.build
  -> quality.check
  -> AI 修复
```

验收：

- 上传 ERP 示例文档。
- 检索接口规范。
- 检索代码片段。
- 生成 TypeScript/Fastify 示例接口。
- 沙箱编译。
- 质量工具返回 issue。
- 修复后再次验证。

### M8：扩展工具

后续工具：

- error-tool。
- project-analyzer-tool。
- template-tool。
- git-tool。
- eval-tool。

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

## 4. 开发节奏

| 阶段 | 内容 |
|---|---|
| 第 1 周 | M0 controller 基础工程 |
| 第 2 周 | M1 工具协议、安装、调用 |
| 第 3-4 周 | M2 knowledge-tool |
| 第 5 周 | M3 asset-tool |
| 第 6-7 周 | M4 sandbox-tool |
| 第 8 周 | M5 quality-tool |
| 第 9 周 | M6 memory-tool |
| 第 10 周 | M7 编程闭环 |
| 第 11 周以后 | 扩展工具和管理后台增强 |

## 5. 风险与控制

| 风险 | 控制方式 |
|---|---|
| 工具协议过早复杂 | 先支持 `tool.yaml`、capability、invoke、health 四件事 |
| controller 变成大单体 | 工具业务放在 tools 目录和独立 API 中 |
| 工具安装过度自动化 | MVP 先支持本地目录和 compose profiles |
| 沙箱安全风险 | sandbox-tool 独立部署，默认网络隔离 |
| 用户部署门槛高 | 提供 core、knowledge、coding、full 四种 compose profile |

## 6. MVP 完成定义

MVP 完成时必须具备：

1. controller 可启动。
2. 工具可安装、启用、停用。
3. MCP Skill 来自工具 capability。
4. knowledge-tool 可检索文档。
5. asset-tool 可检索代码片段。
6. sandbox-tool 可执行和编译代码。
7. quality-tool 可返回结构化 issue。
8. memory-tool 可提供上下文包。
9. controller 能编排完整 AI 编程闭环。
