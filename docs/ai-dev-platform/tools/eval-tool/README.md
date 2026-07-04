# eval-tool 文档索引

`eval-tool` 是 AIDP 的评测工具，用于评估 Prompt、Skill、工具链、Agent 流程在真实开发任务中的效果。它帮助开源用户和团队判断“这套工具到底有没有变好”。

## 必读文档

| 文档 | 内容 |
|---|---|
| [01-requirements.md](./01-requirements.md) | 需求、评测对象、指标 |
| [02-architecture.md](./02-architecture.md) | 架构、数据集、运行器、评分 |
| [03-module-design.md](./03-module-design.md) | 模块职责、评分器、报告 |
| [04-api-capabilities.md](./04-api-capabilities.md) | API 与 capability |
| [05-data-model.md](./05-data-model.md) | 数据集、用例、运行、结果模型 |
| [06-development-plan.md](./06-development-plan.md) | 开发计划 |
| [07-testing-acceptance.md](./07-testing-acceptance.md) | 测试验收 |
| [AI_IMPLEMENTATION.md](./AI_IMPLEMENTATION.md) | AI 编码提示 |

## MVP Capability

| capability | 权限 | 说明 |
|---|---|---|
| `eval.dataset_create` | `eval:write` | 创建评测集 |
| `eval.case_add` | `eval:write` | 添加评测用例 |
| `eval.run` | `eval:run` | 执行评测 |
| `eval.result_get` | `eval:read` | 获取结果 |
| `eval.report` | `eval:read` | 生成报告 |

## 完成定义

- 支持手工评测集。
- 支持 HTTP/tool capability 调用型评测。
- 支持规则评分和人工评分占位。
- 支持 markdown 报告。
