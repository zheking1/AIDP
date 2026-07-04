# eval-tool 模块设计

| 模块 | 职责 |
|---|---|
| `EvalInvokeController` | capability 路由 |
| `DatasetService` | 数据集管理 |
| `CaseService` | 用例管理 |
| `EvalRunner` | 执行评测 |
| `TargetClient` | 调用 tool/http/manual target |
| `ScorerRegistry` | 管理评分器 |
| `ResultService` | 保存结果 |
| `ReportService` | 生成报告 |

## EvalCase 结构

包括：

- `name`
- `input`
- `expected`
- `target_type`
- `target_config`
- `scorers`
- `tags`

## Run 状态

`queued`、`running`、`succeeded`、`failed`、`cancelled`。

## 报告内容

- 总成功率。
- 指标均值和分位数。
- 失败用例列表。
- 回归用例。
- 慢请求列表。
- 建议修复方向。
