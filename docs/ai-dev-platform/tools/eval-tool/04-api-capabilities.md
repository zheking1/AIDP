# eval-tool API 与 Capability

## 1. Capability

| capability | REST |
|---|---|
| `eval.dataset_create` | `POST /api/eval/datasets` |
| `eval.case_add` | `POST /api/eval/datasets/{id}/cases` |
| `eval.run` | `POST /api/eval/runs` |
| `eval.result_get` | `GET /api/eval/runs/{id}` |
| `eval.report` | `GET /api/eval/runs/{id}/report` |

## 2. dataset_create

```json
{
  "name": "knowledge-search-basic",
  "description": "知识库检索基础评测",
  "tags": ["knowledge", "rag"]
}
```

## 3. case_add

```json
{
  "name": "搜索订单审批规则",
  "target_type": "tool_invoke",
  "target_config": {
    "tool": "knowledge-tool",
    "capability": "knowledge.search"
  },
  "input": {
    "query": "订单审批规则"
  },
  "expected": {
    "contains": ["审批"]
  },
  "scorers": [
    {
      "type": "json_schema"
    },
    {
      "type": "contains_text",
      "field": "$.items[*].content",
      "text": "审批"
    }
  ]
}
```

## 4. eval.run

```json
{
  "dataset_id": "ds_01",
  "case_tags": ["knowledge"],
  "parallelism": 1,
  "timeout_ms": 30000
}
```

## 5. eval.report

返回 markdown 报告和结构化指标。

## 6. 错误码

`VALIDATION_ERROR`、`NOT_FOUND`、`FORBIDDEN`、`TIMEOUT`、`EXECUTION_FAILED`。
