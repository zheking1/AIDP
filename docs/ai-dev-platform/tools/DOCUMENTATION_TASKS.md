# 工具详细文档拆分任务清单

本文档用于跟踪 `aidp-controller + N 个可选安装工具` 架构下，各工具开发文档的完善进度。

## 1. 文档拆分标准

每个工具目录必须至少包含以下文档：

| 文档 | 目标 |
|---|---|
| `README.md` | 工具定位、文档索引、快速开发入口 |
| `01-requirements.md` | 需求说明、用户场景、功能范围、非功能需求、边界 |
| `02-architecture.md` | 工具内部架构、外部依赖、运行模式、部署形态、关键流程 |
| `03-module-design.md` | 模块划分、类/服务职责、状态机、异常处理、扩展点 |
| `04-api-capabilities.md` | HTTP API、tool capability、`/tool/invoke` 映射、请求响应、错误码 |
| `05-data-model.md` | 数据库表、索引、对象存储路径、配置模型、迁移策略 |
| `06-development-plan.md` | 里程碑、任务拆分、开发顺序、交付物、风险控制 |
| `07-testing-acceptance.md` | 单元测试、集成测试、端到端测试、验收标准、性能指标 |
| `AI_IMPLEMENTATION.md` | 给 AI 编码工具的实施提示、文件结构、关键注意事项 |

所有工具文档都必须遵守：

- 工具可独立运行。
- 工具可被 `aidp-controller` 安装和统一调用。
- 工具必须符合 `docs/ai-dev-platform/common/tool-contract.md`。
- 工具必须符合 `docs/ai-dev-platform/common/engineering-standards.md`。
- 文档必须写清楚 MVP 范围和后续增强范围。
- 文档必须写清楚能力名称、权限名称、输入输出 schema 和错误模型。
- 文档必须写清楚数据隔离策略，尤其是 `workspace_id` 和 `project_id`。

## 2. 工具文档进度

| 工具 | 优先级 | 状态 | 说明 |
|---|---:|---|---|
| `knowledge-tool` | P0 | 已完成拆分 | 文档入库、切片、向量化、检索 |
| `asset-tool` | P0 | 已完成拆分 | 代码资产、片段、模板、历史方案 |
| `sandbox-tool` | P0 | 已完成拆分 | 脚本执行、项目编译、SQL 临时验证 |
| `quality-tool` | P0 | 已完成拆分 | Lint、测试、规则校验、构建日志解析 |
| `memory-tool` | P0 | 已完成拆分 | 长期记忆、会话摘要、上下文包 |
| `error-tool` | P1 | 已完成拆分 | 报错知识库、相似错误检索 |
| `project-analyzer-tool` | P1 | 已完成拆分 | 项目结构、依赖、接口、数据库扫描 |
| `template-tool` | P1 | 已完成拆分 | 脚手架、模块模板、变量渲染 |
| `git-tool` | P2 | 已完成拆分 | Git/Gitea 同步、提交分析、历史上下文 |
| `eval-tool` | P2 | 已完成拆分 | Prompt、Skill、工具效果评测 |

## 3. 推荐完善顺序

第一批必须先完成：

1. `knowledge-tool`
2. `asset-tool`
3. `sandbox-tool`
4. `quality-tool`
5. `memory-tool`

第二批完成：

1. `error-tool`
2. `project-analyzer-tool`
3. `template-tool`

第三批完成：

1. `git-tool`
2. `eval-tool`

## 4. 单工具完成定义

某个工具只有同时满足以下条件，才算文档完成：

- 已存在 7 份拆分文档。
- `README.md` 已链接所有拆分文档。
- API 文档足够生成 `openapi.yaml`。
- capability 文档足够生成 `tool.yaml`。
- 数据模型足够生成 SQL/Drizzle/Alembic 等迁移脚本。
- 开发计划足够拆分为 AI 编码任务。
- 测试验收足够直接生成测试用例。
- 明确说明独立运行模式和 controller 托管模式。
