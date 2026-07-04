# aidp-controller 文档索引

`aidp-controller` 是 AIDP 的主服务，负责用户、工作区、项目、会话、工具安装、capability 路由、MCP 暴露、工作流编排、审批、权限、密钥、审计和管理台 API。

controller 不实现具体工具业务，而是通过统一工具协议调用可选安装工具。

默认实现技术栈：

```text
TypeScript + Fastify + PostgreSQL + Drizzle ORM + Vitest
```

## 必读文档

| 文档 | 内容 |
|---|---|
| [01-requirements.md](./01-requirements.md) | 主服务需求、用户场景、功能边界、个人/团队模式 |
| [02-architecture.md](./02-architecture.md) | 总体架构、模块关系、调用链路、部署形态 |
| [03-module-design.md](./03-module-design.md) | tool-manager、router、workflow、approval、secrets 等模块设计 |
| [04-api-capabilities.md](./04-api-capabilities.md) | controller HTTP API、MCP API、内部 capability 路由 |
| [05-data-model.md](./05-data-model.md) | workspace、project、tool、workflow、approval、secret、audit 数据模型 |
| [06-development-plan.md](./06-development-plan.md) | 里程碑、AI 编码任务拆分、交付物 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 单元、集成、端到端、验收标准 |
| [AI_IMPLEMENTATION.md](./AI_IMPLEMENTATION.md) | 给 AI 编码工具的实施入口 |

## controller 核心模块

| 模块 | 职责 |
|---|---|
| `workspace` | tenant、workspace、project、session 管理 |
| `auth` | 用户、角色、权限、API token |
| `tool-manager` | 工具安装、卸载、启停、健康检查、版本管理 |
| `capability-router` | 校验权限、选择工具、调用 `/tool/invoke` |
| `mcp-adapter` | 将工具 capability 暴露为 MCP Skill |
| `workflow-runner` | 编排多工具 AI 编程流程 |
| `context-builder` | 聚合 memory/knowledge/asset/project-analyzer 结果 |
| `approval-center` | 高风险动作人工确认 |
| `secrets-manager` | Git token、数据库密码、模型密钥等敏感配置 |
| `audit-log` | 工具调用、审批、配置变更审计 |
| `admin-api` | 管理台和 CLI 调用 API |

## 完成定义

- 可通过 CLI 或 API 安装 mock-tool。
- 可读取 tool.yaml 并登记 capability。
- 可通过 `/api/tools/invoke` 调用任意已启用 capability。
- 可将 capability 映射为 MCP Skill。
- 可执行内置 AI 编程 workflow。
- 高风险动作进入 approval-center。
- 密钥不进入日志、Prompt 和普通响应。
- 所有调用具备 trace_id 和审计记录。
