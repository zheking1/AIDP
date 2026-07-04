# memory-tool 测试与验收

## 1. 测试目标

验证 `memory-tool` 在独立运行和 controller 托管两种模式下，都能安全、稳定地保存记忆、检索记忆、生成上下文包，并且不会跨 workspace/project/session 泄露数据。

## 2. 单元测试

| 模块 | 测试点 |
|---|---|
| `ScopeGuard` | scope 与上下文匹配、跨项目拒绝、global 权限限制 |
| `MemoryRanker` | 相关度、重要度、时效性、scope 权重排序 |
| `TokenEstimateService` | 中英文 token 估算、超预算裁剪、空文本处理 |
| `MemoryService` | key upsert、content_hash 去重、默认状态 |
| `SummaryService` | version 递增、active 唯一 |
| `ContextPackageService` | section 顺序、omitted_items、source_refs |

关键用例：

- `source_type=ai_generated` 且未传 status，保存为 `pending_review`。
- `importance=-1` 或 `importance=101` 返回校验错误。
- `scope=project` 但缺少 `project_id` 返回校验错误。
- `max_tokens` 小于最小值返回校验错误。

## 3. 集成测试

使用 Testcontainers 或本地 PostgreSQL。

### 3.1 工具协议

- `GET /health` 返回 `UP`。
- `GET /tool/manifest` 返回工具元信息。
- `GET /tool/capabilities` 包含 6 个 MVP capability。
- `POST /tool/invoke` 调用未知 capability 返回 `VALIDATION_ERROR`。

### 3.2 upsert/search

步骤：

1. workspace A / project A 写入一条 approved 记忆。
2. workspace A / project B 写入另一条 approved 记忆。
3. 在 project A 上下文检索。

期望：

- 只返回 project A 的记忆。
- 不返回 project B 的记忆。
- 响应包含 `trace_id`。

### 3.3 审核状态

步骤：

1. 写入 `pending_review` 记忆。
2. 默认 search。
3. `include_pending=true` search。
4. review approve。
5. 默认 search。

期望：

- 第 2 步不返回。
- 第 3 步返回。
- approve 后默认返回。

### 3.4 过期过滤

步骤：

1. 写入 `expires_at` 为过去时间的记忆。
2. 写入 `expires_at` 为未来时间的记忆。
3. search。

期望：

- 只返回未来过期或无过期时间的记忆。

### 3.5 context package

步骤：

1. 保存 session summary。
2. 写入 coding_standard、business_rule、api_contract。
3. 调用 `memory.get_context`。

期望：

- 返回 sections。
- `session_summary` 在第一段。
- 返回 `rendered_markdown`。
- `token_estimate <= max_tokens`。
- 所有 section 的 source_refs 可追踪。

## 4. 端到端测试

模拟 controller：

1. 读取 `tool.yaml`。
2. 调用 `/tool/capabilities`。
3. 通过 `/tool/invoke` 写入项目规范。
4. 通过 `/tool/invoke` 保存会话摘要。
5. 通过 `/tool/invoke` 获取上下文包。

验收：

- 整个流程无人工干预。
- 错误响应符合统一错误模型。
- 日志包含同一个 `trace_id`。

## 5. 性能验收

测试数据：

- 10 个 workspace。
- 每个 workspace 20 个 project。
- 每个 project 500 条记忆。
- 总计 100000 条记忆。

指标：

| 操作 | 指标 |
|---|---:|
| memory.upsert P95 | < 200ms |
| memory.search P95 | < 500ms |
| memory.get_context P95 | < 800ms |
| context package 生成成功率 | > 99.5% |

## 6. 安全验收

- 普通 project 用户不能写 global memory。
- workspace A 用户不能读取 workspace B 的记忆。
- session 记忆必须匹配 session_id。
- `content` 中的敏感字段不写入日志。
- 错误信息不能泄露其他项目 memory id。

## 7. 文档验收

交付前必须存在：

- `tool.yaml`
- `openapi.yaml`
- `config.example.yaml`
- `examples/upsert.json`
- `examples/search.json`
- `examples/get_context.json`
- `examples/save_summary.json`
- README 中链接全部拆分文档。
