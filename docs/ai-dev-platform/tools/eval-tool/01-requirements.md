# eval-tool 需求说明

## 1. 背景

Prompt、Skill、工具文档和 Agent 流程会持续变化。如果没有评测，系统是否变好只能靠感觉。`eval-tool` 用固定数据集和指标评估工具调用准确性、输出质量、耗时、成功率和回归风险。

## 2. 评测对象

- 单个工具 capability。
- controller 路由策略。
- Skill/Prompt。
- 多工具工作流。
- 文档检索效果。

## 3. 指标

| 指标 | 说明 |
|---|---|
| success_rate | 是否完成任务 |
| tool_call_accuracy | 工具选择是否正确 |
| schema_validity | 输出是否符合 schema |
| latency_ms | 执行耗时 |
| cost_estimate | token/执行成本 |
| quality_score | 规则或人工质量分 |

## 4. 功能需求

- 创建 dataset。
- 添加 eval case。
- 执行 eval run。
- 保存输入、输出、工具调用、评分。
- 生成 markdown/html 报告。
- 对比两次 run。

## 5. 非目标

MVP 不直接调用商业 LLM SaaS，不实现复杂自动判卷模型，不做大规模并发压测。

## 6. 验收范围

- 能创建数据集。
- 能添加用例。
- 能调用目标 HTTP/tool。
- 能按规则评分。
- 能生成报告。
