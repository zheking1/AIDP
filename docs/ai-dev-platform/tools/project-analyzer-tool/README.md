# project-analyzer-tool 文档索引

`project-analyzer-tool` 负责扫描代码仓库、依赖、模块、API、数据库迁移、配置文件和测试结构，生成项目结构摘要。它让 AI 在开发前快速理解项目边界，减少反复读取全仓库的 token 浪费。

## 必读文档

| 文档 | 内容 |
|---|---|
| [01-requirements.md](./01-requirements.md) | 需求、扫描范围、场景、边界 |
| [02-architecture.md](./02-architecture.md) | 架构、扫描流程、增量分析、缓存 |
| [03-module-design.md](./03-module-design.md) | 模块职责、语言分析器、摘要生成 |
| [04-api-capabilities.md](./04-api-capabilities.md) | API、capability、请求响应 |
| [05-data-model.md](./05-data-model.md) | 项目快照、文件索引、符号、依赖模型 |
| [06-development-plan.md](./06-development-plan.md) | 开发计划、任务拆分、风险 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 测试和验收标准 |
| [AI_IMPLEMENTATION.md](./AI_IMPLEMENTATION.md) | AI 编码实现提示 |

## MVP Capability

| capability | 权限 | 说明 |
|---|---|---|
| `project.scan` | `project:read` | 扫描项目并生成快照 |
| `project.summary` | `project:read` | 获取项目摘要 |
| `project.find_symbol` | `project:read` | 查找类、函数、接口、配置项 |
| `project.find_files` | `project:read` | 按路径、语言、模块查找文件 |
| `project.dependency_graph` | `project:read` | 获取依赖关系 |
| `project.export_memory` | `memory:write` | 将稳定摘要写入 memory-tool |

## 完成定义

- 能扫描 TypeScript/Node、Python、Flutter/Dart 的基础结构。
- 能生成模块、入口、依赖、API、数据库迁移、测试摘要。
- 能按 `workspace_id/project_id` 保存扫描快照。
- 能增量扫描变更文件。
- 能输出给 AI 直接使用的 markdown 项目概要。
