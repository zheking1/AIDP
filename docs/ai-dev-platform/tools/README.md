# 工具详细设计文档索引

本目录用于描述 `aidp-controller + N 个可选安装工具` 架构下，每个工具的详细设计、开发计划、接口能力、数据模型和验收标准。

详细拆分任务见 [DOCUMENTATION_TASKS.md](./DOCUMENTATION_TASKS.md)。每个工具最终都必须拆分为需求说明、架构设计、模块设计、API/capability、数据模型、开发计划、测试验收等独立文档，而不是只写一个概要 README。

## 工具清单

| 工具 | 优先级 | 用途 |
|---|---:|---|
| [importer-tool](./importer-tool/README.md) | P0 | 对话式内容导入，自动分类/检查/持久化 |
| [knowledge-tool](./knowledge-tool/README.md) / [AI实施包](./knowledge-tool/AI_IMPLEMENTATION.md) | P0 | 文档入库、切片、向量化、检索 |
| [asset-tool](./asset-tool/README.md) / [AI实施包](./asset-tool/AI_IMPLEMENTATION.md) | P0 | 代码片段、模板、历史方案检索 |
| [sandbox-tool](./sandbox-tool/README.md) / [AI实施包](./sandbox-tool/AI_IMPLEMENTATION.md) | P0 | 代码执行、项目编译、SQL 验证 |
| [quality-tool](./quality-tool/README.md) / [AI实施包](./quality-tool/AI_IMPLEMENTATION.md) | P0 | 构建日志解析、Lint、测试、规则校验 |
| [memory-tool](./memory-tool/README.md) / [AI实施包](./memory-tool/AI_IMPLEMENTATION.md) | P0 | 项目记忆、会话摘要、上下文包 |
| [error-tool](./error-tool/README.md) / [AI实施包](./error-tool/AI_IMPLEMENTATION.md) | P1 | 报错知识库、相似错误检索 |
| [project-analyzer-tool](./project-analyzer-tool/README.md) / [AI实施包](./project-analyzer-tool/AI_IMPLEMENTATION.md) | P1 | 项目结构、依赖、接口、数据库扫描 |
| [template-tool](./template-tool/README.md) / [AI实施包](./template-tool/AI_IMPLEMENTATION.md) | P1 | 脚手架、模块模板、变量渲染 |
| [git-tool](./git-tool/README.md) / [AI实施包](./git-tool/AI_IMPLEMENTATION.md) | P2 | Git/Gitea 同步、提交分析、代码历史上下文 |
| [eval-tool](./eval-tool/README.md) / [AI实施包](./eval-tool/AI_IMPLEMENTATION.md) | P2 | Prompt、Skill、工具效果评测 |

## 单工具标准文档包

每个工具目录必须包含：

```text
README.md
01-requirements.md
02-architecture.md
03-module-design.md
04-api-capabilities.md
05-data-model.md
06-development-plan.md
07-testing-acceptance.md
AI_IMPLEMENTATION.md
```

当前 10 个工具目录均已按上述标准补齐文档包。后续进入实现阶段时，可以按单个工具目录交给 AI 编码工具逐项生成 `tool.yaml`、`openapi.yaml`、数据库迁移、服务代码和测试用例。

## 通用工具约束

每个工具必须满足：

- 可以独立运行。
- 可以被 `aidp-controller` 安装和接管。
- 必须提供 `tool.yaml`。
- 必须提供 `/health`。
- 必须提供 `/tool/manifest`。
- 必须提供 `/tool/capabilities`。
- 必须提供 `/tool/invoke`。
- 必须有 OpenAPI 文档。
- 必须有最小可运行示例。
- 必须记录 trace_id。
- 必须返回结构化错误。

## 开发顺序

建议按以下顺序开发：

```text
mock-tool
  -> knowledge-tool
  -> asset-tool
  -> sandbox-tool
  -> quality-tool
  -> memory-tool
  -> error-tool
  -> project-analyzer-tool
  -> template-tool
  -> git-tool
  -> eval-tool
```

`mock-tool` 不单独建文档，它用于验证 controller 的安装、注册、调用机制。
