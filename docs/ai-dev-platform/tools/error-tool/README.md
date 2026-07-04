# error-tool 文档索引

`error-tool` 是 AIDP 的报错知识库和相似错误检索工具。它把 `sandbox-tool`、`quality-tool`、人工录入或 CI 日志中的错误归档为结构化案例，并绑定根因、修复方案、适用环境和关联提交，帮助 AI 在遇到相似问题时优先参考历史解决方案。

工具必须支持：

- 独立运行：个人只安装本工具，用于保存和检索本地报错经验。
- controller 托管：由 `aidp-controller` 调用，作为“执行失败后自动检索修复方案”的后置工具。

## 必读文档

| 文档 | 内容 |
|---|---|
| [01-requirements.md](./01-requirements.md) | 需求、使用场景、边界、错误类型、验收范围 |
| [02-architecture.md](./02-architecture.md) | 架构、错误采集、归一化、检索、解决方案闭环 |
| [03-module-design.md](./03-module-design.md) | 模块职责、归一化器、相似度排序、生命周期 |
| [04-api-capabilities.md](./04-api-capabilities.md) | API、capability、请求响应、错误码 |
| [05-data-model.md](./05-data-model.md) | 表结构、索引、对象存储路径、向量扩展 |
| [06-development-plan.md](./06-development-plan.md) | 里程碑、AI 编码任务、风险控制 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 测试用例、端到端流程、验收指标 |
| [AI_IMPLEMENTATION.md](./AI_IMPLEMENTATION.md) | AI 编码实现提示 |

## MVP Capability

| capability | 权限 | 说明 |
|---|---|---|
| `error.record` | `error:write` | 记录错误案例和原始日志 |
| `error.search` | `error:read` | 检索相似错误 |
| `error.link_solution` | `error:write` | 绑定修复方案 |
| `error.resolve` | `error:write` | 标记错误已解决 |
| `error.export_pattern` | `asset:write` | 将高价值解决方案导出到 asset-tool |

## 完成定义

- 可记录 TypeScript 构建错误、Python 运行异常、测试失败、依赖冲突四类 MVP 错误。
- 能从原始日志中提取主错误、文件、行号、异常类、包名/模块名等关键字段。
- 能按 `workspace_id/project_id` 隔离检索。
- 能返回相似度、根因、解决方案和 source_refs。
- 能被 sandbox/quality 的失败结果自动调用。
