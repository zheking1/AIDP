# eval-tool AI 实施包

## 1. 目标交付

实现评测工具，支持创建评测用例、运行评测、记录结果、生成报告和对比不同版本。

## 2. 推荐模块结构

```text
eval-tool/
  src/
    server.ts
    api/
      tool-protocol.routes.ts
      health.routes.ts
      eval-case.routes.ts
      eval-run.routes.ts
      eval-report.routes.ts
    services/
      eval-case.service.ts
      eval-run.service.ts
      eval-scoring.service.ts
      eval-compare.service.ts
      controller.client.ts
    repository/
      eval-case.repository.ts
      eval-run.repository.ts
      eval-result.repository.ts
```

## 3. 数据库迁移

必须创建：

- `eval_case`
- `eval_run`
- `eval_result`

## 4. API

- `POST /api/eval/cases`
- `GET /api/eval/cases/{id}`
- `POST /api/eval/runs`
- `GET /api/eval/runs/{id}`
- `GET /api/eval/runs/{id}/report`
- `POST /api/eval/compare`

## 5. 核心实现

### EvalRunService

流程：

```text
读取 eval_case
  -> 调用 controller MCP/task API
  -> 采集工具调用轨迹
  -> 判断 expected
  -> 写入 eval_result
```

### EvalScoringService

MVP 评分：

- 是否调用正确工具。
- 是否引用文档。
- 是否通过编译。
- 是否通过 quality.check。
- 输出是否结构化。

## 6. 测试

- eval_case CRUD。
- eval_run 状态流转。
- scoring 规则。
- compare 结果。

## 7. Definition of Done

- 可独立启动。
- 可被 controller 安装。
- 可创建评测用例。
- 可运行评测。
- 可生成报告。
- 可比较两次评测。
