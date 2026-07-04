# memory-tool 文档索引

`memory-tool` 是 AIDP 的长期记忆、会话摘要和上下文包生成工具。它保存“小而关键、可直接进入 Prompt 的事实”，例如项目规范、架构决策、业务规则、数据库约束、依赖版本、当前会话决策等，避免 AI 在长项目中反复读取同一批背景信息。

它必须同时支持两种运行方式：

- 独立运行：个人用户只安装 `memory-tool`，通过 HTTP API 或 CLI 管理项目记忆。
- controller 托管：由 `aidp-controller` 安装、发现、授权、调用，并映射为 MCP Skill。

## 必读文档

| 文档 | 内容 |
|---|---|
| [01-requirements.md](./01-requirements.md) | 需求说明、记忆层级、使用场景、功能边界、验收范围 |
| [02-architecture.md](./02-architecture.md) | 工具架构、写入流程、检索流程、上下文包流程、降级策略 |
| [03-module-design.md](./03-module-design.md) | 模块职责、排序策略、token 裁剪、审核与过期、异常处理 |
| [04-api-capabilities.md](./04-api-capabilities.md) | HTTP API、tool capability、输入输出 schema、错误码 |
| [05-data-model.md](./05-data-model.md) | PostgreSQL 表结构、索引、配置模型、迁移策略 |
| [06-development-plan.md](./06-development-plan.md) | 里程碑、AI 编码任务拆分、交付物、风险控制 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 单元测试、集成测试、端到端测试、性能与安全验收 |
| [AI_IMPLEMENTATION.md](./AI_IMPLEMENTATION.md) | 给 AI 编码工具的实现入口和注意事项 |

## MVP Capability

| capability | 权限 | 说明 |
|---|---|---|
| `memory.upsert` | `memory:write` | 新增或更新结构化记忆 |
| `memory.search` | `memory:read` | 按任务、类型、层级检索记忆 |
| `memory.get_context` | `memory:read` | 生成可直接拼入 Prompt 的上下文包 |
| `memory.save_summary` | `memory:write` | 保存会话摘要 |
| `memory.expire` | `memory:write` | 设置记忆过期 |
| `memory.review` | `memory:write` | 审核 AI 写入的待确认记忆 |

## 完成定义

- 可通过 `tool.yaml` 被 controller 安装和发现。
- `/tool/invoke` 可以调用全部 MVP capability。
- 所有数据按 `workspace_id`、`project_id`、`session_id` 严格隔离。
- `pending_review` 记忆默认不进入正式上下文。
- 过期记忆不参与检索和上下文组装。
- `max_tokens` 对 `memory.get_context` 必须生效。
- 生成的 context package 返回引用来源，方便 controller 审计。
