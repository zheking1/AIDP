# memory-tool 需求说明

## 1. 背景

长项目开发中，AI 经常需要重复读取项目技术栈、编码规范、数据库约束、业务决策和历史会话摘要。如果每次都把这些内容塞进 prompt，会浪费 token，也容易遗漏关键信息。`memory-tool` 用结构化记忆和上下文包解决这个问题。

## 2. 产品目标

- 管理 global、workspace、project、session 四级记忆。
- 保存会话摘要。
- 根据任务生成 context package。
- 支持重要度、过期时间、审核状态。
- 支持 token 预算。
- 严格隔离 workspace/project/session。

## 3. 非目标

MVP 不做：

- 不替代 `knowledge-tool` 的文档检索。
- 不存放大文档全文。
- 不自动相信所有 AI 写入的记忆。
- 不跨项目共享私有记忆。
- 不做复杂人格化长期记忆。

## 4. 记忆层级

| scope | 说明 | 示例 |
|---|---|---|
| `global` | 平台级通用规范 | 默认 Node/Python 版本、通用安全规则 |
| `workspace` | 团队级规范 | 团队接口返回格式 |
| `project` | 项目长期记忆 | ERP 数据库命名规则 |
| `session` | 当前会话短期记忆 | 本轮已决定字段名 |

## 5. 记忆类型

| memory_type | 说明 |
|---|---|
| `coding_standard` | 编码规范 |
| `architecture_decision` | 架构决策 |
| `business_rule` | 业务规则 |
| `database_rule` | 数据库约束 |
| `api_contract` | 接口约定 |
| `dependency_info` | 依赖版本 |
| `session_summary` | 会话摘要 |
| `task_preference` | 当前任务偏好 |

## 6. 使用场景

### 6.1 保存项目规范

用户写入“所有接口必须返回 ApiResponse<T>”。后续 AI 生成接口前调用 `memory.get_context` 自动带出该规范。

### 6.2 保存会话摘要

长会话结束前，AI 调用 `memory.save_summary` 保存本轮关键决策，下一轮继续开发时加载。

### 6.3 生成上下文包

用户提出“新增销售订单审批接口”，controller 调用 `memory.get_context`，返回相关项目规范、会话摘要和业务决策。

## 7. 功能需求

### 7.1 记忆写入

必须支持：

- upsert。
- scope。
- type。
- title。
- content。
- importance。
- status。
- expires_at。
- source。

AI 写入的记忆默认 status=`pending_review`，人工或规则确认后变为 `approved`。

### 7.2 记忆检索

必须支持：

- query。
- scope filter。
- memory_type filter。
- status filter。
- importance range。
- top_k。

MVP 可用关键词检索，后续接 PGVector。

### 7.3 上下文包

输入：

- workspace_id。
- project_id。
- session_id。
- task。
- max_tokens。

输出：

- session summary。
- selected memories。
- token_estimate。
- omitted items。

排序优先级：

1. 当前会话摘要。
2. 与 task 相关的项目记忆。
3. 高重要度项目规范。
4. 最近更新的业务决策。
5. workspace/global 规范。

### 7.4 过期和审核

- expires_at 早于当前时间的记忆不返回。
- `pending_review` 默认不进入正式上下文。
- `rejected` 永不进入上下文。
- 支持手动 expire。

## 8. 非功能需求

- context package 生成 P95 小于 500ms。
- max_tokens 必须生效。
- project 私有记忆不能跨项目返回。
- 所有写入必须记录 trace_id 和 created_by。

## 9. MVP 验收范围

- 工具协议接口。
- memory.upsert。
- memory.search。
- memory.save_summary。
- memory.get_context。
- 过期过滤。
- 审核状态过滤。
- project 隔离。
