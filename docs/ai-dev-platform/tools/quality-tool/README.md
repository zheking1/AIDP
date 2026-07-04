# quality-tool 文档索引

`quality-tool` 负责质量校验、规则集执行、构建/测试/Lint 日志解析和结构化 issue 输出。它不直接在宿主机执行构建命令，而是调用 `sandbox-tool` 或解析已有日志，把结果转换成 AI 可以继续修复的反馈。

## 1. 必读文档

| 文档 | 内容 |
|---|---|
| [01-requirements.md](./01-requirements.md) | 需求说明、检查类型、规则集、issue 输出要求 |
| [02-architecture.md](./02-architecture.md) | 工具架构、sandbox 联动、检查流程、日志解析流程 |
| [03-module-design.md](./03-module-design.md) | 模块职责、规则集服务、日志解析器、issue normalizer |
| [04-api-capabilities.md](./04-api-capabilities.md) | HTTP API、capability、请求响应、错误码 |
| [05-data-model.md](./05-data-model.md) | 规则集、质量结果、issue、日志引用数据模型 |
| [06-development-plan.md](./06-development-plan.md) | 里程碑、AI 编码任务拆分、风险控制 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 单元、集成、端到端和验收标准 |
| [AI_IMPLEMENTATION.md](./AI_IMPLEMENTATION.md) | 给 AI 编码工具的实施入口 |

## 2. 工具定位

核心职责：

- 管理项目质量规则集。
- 调用 `sandbox-tool` 执行 build/test/lint 命令。
- 解析 TypeScript、Python、测试框架、Lint 输出。
- 输出标准化 issue：severity、file、line、column、message、suggested_fix。
- 保存质量检查结果和原始日志引用。
- 为 AI 自动修复提供稳定反馈。

## 3. MVP Capability

| capability | 权限 | 说明 |
|---|---|---|
| `quality.check` | `quality:check` | 执行完整质量检查 |
| `quality.parse_build_log` | `quality:parse` | 解析构建日志 |
| `quality.parse_test_log` | `quality:parse` | 解析测试日志 |
| `quality.result.get` | `quality:read` | 获取检查结果 |
| `quality.ruleset.get` | `quality:read` | 获取规则集 |
| `quality.ruleset.validate` | `quality:write` | 校验规则集 |

## 4. 完成定义

- 可 standalone 启动。
- 可被 controller 托管安装。
- 可解析 TypeScript/Python 构建和测试错误。
- issue 包含 severity、file、line、message。
- `quality.check` 可调用 `sandbox-tool`。
- 质量结果可作为 AI 修复输入。
