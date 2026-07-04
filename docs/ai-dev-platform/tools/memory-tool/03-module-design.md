# memory-tool 模块设计

## 1. 模块划分

`memory-tool` 内部按“写入、检索、上下文组装、治理”拆分，避免把所有逻辑堆到单个 service。

| 模块 | 主要职责 | 输入 | 输出 |
|---|---|---|---|
| `ToolInvokeController` | 处理 `/tool/invoke`，做 capability 路由 | tool 协议请求 | tool 协议响应 |
| `MemoryController` | 提供 REST API，便于独立使用 | HTTP 请求 | 业务响应 |
| `MemoryService` | 记忆 upsert、读取、状态变更 | 记忆 DTO | `MemoryItem` |
| `MemorySearchService` | 关键词/向量检索、过滤、排序 | query、scope、filters | 候选记忆列表 |
| `SummaryService` | 会话摘要保存、读取、版本化 | session summary | `SessionSummary` |
| `ContextPackageService` | 按任务生成上下文包 | task、scope、max_tokens | `ContextPackage` |
| `MemoryRanker` | 相关度、重要度、时效性排序 | 候选记忆 | 排序后记忆 |
| `TokenEstimateService` | token 估算与裁剪 | 文本、预算 | token estimate、裁剪结果 |
| `ScopeGuard` | workspace/project/session 隔离校验 | 请求上下文、实体 scope | allow/deny |
| `ReviewService` | 审核 AI 写入记忆 | review action | 状态变更 |
| `ExpiryJob` | 定期标记过期记忆 | 当前时间 | expired 状态 |

## 2. 核心领域对象

### 2.1 MemoryItem

表示一条可复用记忆。字段必须覆盖：

- `id`
- `tenant_id`
- `workspace_id`
- `project_id`
- `session_id`
- `scope`
- `memory_type`
- `key`
- `title`
- `content`
- `summary`
- `tags`
- `importance`
- `confidence`
- `status`
- `source_type`
- `source_ref`
- `expires_at`
- `created_by`
- `updated_by`

约束：

- `scope=global` 时 `workspace_id/project_id/session_id` 可为空。
- `scope=workspace` 时必须有 `workspace_id`。
- `scope=project` 时必须有 `workspace_id/project_id`。
- `scope=session` 时必须有 `workspace_id/project_id/session_id`。
- AI 自动写入默认 `status=pending_review`。
- 人工确认或可信规则写入可直接 `status=approved`。

### 2.2 SessionSummary

保存会话摘要，不保存完整聊天记录。它应该包含：

- 本轮任务目标。
- 已完成事项。
- 关键决策。
- 文件或模块变更摘要。
- 后续待办。
- 风险和未确认问题。

同一个 `session_id` 可保存多个版本，默认只有最新 `active=true` 的摘要进入上下文包。

### 2.3 ContextPackage

上下文包是给 controller/Agent 的最终产物，不是数据库实体的简单转储。结构包含：

- `package_id`
- `task`
- `scope`
- `max_tokens`
- `token_estimate`
- `sections`
- `source_refs`
- `omitted_items`
- `created_at`

`sections` 推荐固定为：

1. `session_summary`
2. `project_rules`
3. `architecture_decisions`
4. `business_rules`
5. `database_rules`
6. `api_contracts`
7. `workspace_global_rules`

## 3. 写入流程设计

### 3.1 memory.upsert

流程：

1. 校验 capability 权限 `memory:write`。
2. 校验请求上下文必须包含 `workspace_id`，除非写入 `global` scope。
3. 校验 `scope` 与 `workspace_id/project_id/session_id` 的匹配关系。
4. 规范化 `memory_type`、`tags`、`key`。
5. 对 `content` 做长度限制，MVP 单条不超过 16KB。
6. 如果调用方是 AI 或 `source_type=ai_generated`，默认状态为 `pending_review`。
7. 如果传入 `key`，按 `(workspace_id, project_id, session_id, scope, key)` 做 upsert。
8. 写入 `memory_item`。
9. 写入 `memory_event` 审计日志。
10. 可选刷新全文索引或向量索引。

去重规则：

- 有 `key`：同 scope 内同 key 更新已有记录。
- 无 `key`：计算 `content_hash`，同 scope 内 hash 相同则返回已有记录。
- 内容相似但 hash 不同不自动合并，只在后续增强中提供 merge 建议。

## 4. 检索流程设计

### 4.1 memory.search

检索步骤：

1. 根据请求上下文构造允许访问的 scope 列表。
2. 过滤 `status in allowed_statuses`，默认只返回 `approved`。
3. 过滤 `expires_at is null or expires_at > now()`。
4. 根据 `memory_type`、`tags`、`importance_min` 做结构化过滤。
5. MVP 使用 PostgreSQL `tsvector` 或 `ILIKE` 关键词检索。
6. 可选启用 pgvector 后混合召回。
7. 调用 `MemoryRanker` 排序。
8. 返回简要信息和 `source_refs`。

排序公式建议：

```text
score = text_relevance * 0.45
      + importance_score * 0.25
      + recency_score * 0.15
      + scope_score * 0.10
      + confidence_score * 0.05
```

`scope_score` 建议：

- session: 1.0
- project: 0.9
- workspace: 0.65
- global: 0.5

## 5. 上下文包设计

### 5.1 memory.get_context

输入：

- `task`：当前任务描述，必填。
- `workspace_id`：必填。
- `project_id`：建议必填。
- `session_id`：可选。
- `max_tokens`：默认 3000，最大值由配置控制。
- `include_pending`：默认 false。
- `memory_types`：可选。

流程：

1. 加载最新 active 会话摘要。
2. 按 task 检索项目和会话相关记忆。
3. 加载高重要度的 workspace/global 规范。
4. 合并候选项并去重。
5. 按章节分类。
6. 对每个章节做 token 预算分配。
7. 超预算时先保留高重要度和高相关项。
8. 生成 `omitted_items`，说明哪些内容因预算不足被省略。
9. 返回可直接拼入 Prompt 的 markdown 版本和结构化版本。

预算分配建议：

| section | 默认预算比例 |
|---|---:|
| session_summary | 20% |
| project_rules | 20% |
| architecture_decisions | 15% |
| business_rules | 15% |
| database_rules | 10% |
| api_contracts | 10% |
| workspace_global_rules | 10% |

## 6. 审核与过期

记忆状态：

| 状态 | 说明 | 是否默认进入上下文 |
|---|---|---|
| `pending_review` | AI 或自动流程写入，待确认 | 否 |
| `approved` | 已确认可用 | 是 |
| `rejected` | 错误或过时 | 否 |
| `expired` | 到期失效 | 否 |
| `archived` | 历史保留 | 否 |

`memory.review` 支持：

- approve
- reject
- archive
- update_importance
- update_confidence

## 7. 异常处理

| 场景 | 错误码 | 处理 |
|---|---|---|
| scope 与上下文不匹配 | `VALIDATION_ERROR` | 返回字段级错误 |
| 跨项目访问 | `FORBIDDEN` | 不暴露目标数据是否存在 |
| 记忆不存在 | `NOT_FOUND` | 返回标准错误 |
| token 预算小于最小值 | `VALIDATION_ERROR` | 提示合法范围 |
| 检索索引不可用 | `DEPENDENCY_UNAVAILABLE` | 降级关键词检索 |
| 数据库不可用 | `DEPENDENCY_UNAVAILABLE` | 返回 retryable=true |

## 8. 扩展点

- `EmbeddingProvider`：后续接入本地 embedding 模型。
- `TokenizerProvider`：按目标大模型估算 token。
- `MemoryMergePolicy`：相似记忆合并策略。
- `ReviewPolicy`：自动审核规则。
- `ContextRenderer`：输出 markdown、json、xml 等格式。
