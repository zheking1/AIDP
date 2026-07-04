# memory-tool 开发计划

## 1. 开发目标

交付一个可独立运行、可被 controller 托管、支持长期记忆和上下文包生成的工具。MVP 不追求复杂向量记忆，先保证结构化记忆、隔离、安全、稳定和可测试。

## 2. 里程碑

| 里程碑 | 周期 | 目标 | 交付物 |
|---|---:|---|---|
| M1 基础工具骨架 | 1-2 天 | 工具协议、配置、健康检查 | `tool.yaml`、`/health`、`/tool/*` |
| M2 记忆写入与检索 | 2-3 天 | upsert、search、隔离、审计 | memory 表、REST API、capability |
| M3 会话摘要与上下文包 | 2-3 天 | summary、get_context、token 裁剪 | context package 服务 |
| M4 审核和过期治理 | 1-2 天 | review、expire、状态过滤 | 审核 API、过期任务 |
| M5 测试与文档 | 1-2 天 | 完整测试和示例 | 单测、集成测试、示例请求 |

## 3. AI 编码任务拆分

### Task 1：生成项目骨架

输入文档：

- `README.md`
- `04-api-capabilities.md`
- `../../common/tool-contract.md`

要求：

- 创建标准 Web 服务项目。
- 提供 `/health`。
- 提供 `/tool/manifest`、`/tool/capabilities`。
- 读取 `tool.yaml`。
- 统一响应格式和错误模型。

验收：

- 本地启动后访问 `/health` 返回 `UP`。
- `/tool/capabilities` 返回 6 个 MVP capability。

### Task 2：实现数据库迁移

输入文档：

- `05-data-model.md`

要求：

- 编写 SQL/Drizzle migration 脚本。
- 创建实体、Repository、基础查询。
- 增加更新时间自动维护。

验收：

- 空库启动自动建表。
- 重复启动不报错。
- 索引存在。

### Task 3：实现 memory.upsert

输入文档：

- `01-requirements.md`
- `03-module-design.md`
- `04-api-capabilities.md`

要求：

- 校验 scope。
- 生成 content_hash。
- 支持 key upsert。
- AI 写入默认 pending_review。
- 写入 memory_event。

验收：

- 同 key 第二次写入更新原记录。
- 跨 project 写入被拒绝。
- `source_type=ai_generated` 默认 pending_review。

### Task 4：实现 memory.search

要求：

- 支持 query、scope、type、tag、status、importance_min、top_k。
- 实现关键词检索。
- 实现排序公式。
- 默认排除 expired/rejected/pending_review。

验收：

- 能按关键词返回相关记忆。
- 不返回其他项目记忆。
- 过期记忆不返回。

### Task 5：实现 session summary

要求：

- 保存摘要版本。
- 新摘要保存时旧 active 自动失效。
- 支持按 session 读取最新 active 摘要。

验收：

- 同 session 连续保存 3 次，version 为 1/2/3。
- 只有 version=3 active=true。

### Task 6：实现 memory.get_context

要求：

- 加载 session summary。
- 检索相关记忆。
- 按章节组织。
- 估算 token。
- 超预算时裁剪并记录 omitted_items。
- 返回结构化结果和 markdown。

验收：

- `max_tokens=800` 时输出不超过预算估算。
- 返回 `source_refs`。
- section 顺序稳定。

### Task 7：实现 review/expire

要求：

- approve/reject/archive。
- expire 设置状态和事件。
- pending_review 只有 include_pending=true 才能进入检索。

验收：

- approve 后可被 context 选中。
- expire 后不可被 search/context 返回。

### Task 8：补齐测试和示例

要求：

- 单元测试覆盖 ranker、token estimate、scope guard。
- 集成测试覆盖全部 capability。
- 提供 `examples/*.json`。
- 提供 `config.example.yaml`。

验收：

- CI 可一键运行。
- 示例请求可直接调用本地服务。

## 4. 推荐目录结构

```text
memory-tool/
  src/
    main/
      java/.../memory/
        api/
        capability/
        config/
        domain/
        repository/
        service/
        support/
    test/
  db/migration/
  examples/
  tool.yaml
  openapi.yaml
  config.example.yaml
  Dockerfile
```

## 5. 风险与控制

| 风险 | 表现 | 控制 |
|---|---|---|
| 记忆污染 | AI 写入错误规则 | AI 写入默认 pending_review |
| 跨项目泄露 | context 返回其他项目记忆 | ScopeGuard 强制校验 |
| token 预算失效 | 上下文过长 | 保守估算和 section 裁剪 |
| 重复记忆过多 | 同一规则多版本混杂 | key upsert + content_hash |
| 检索质量差 | 关键词召回不足 | MVP 保守可用，后续 pgvector |

## 6. 后续增强

- pgvector 混合检索。
- 记忆合并建议。
- 自动从项目扫描结果生成候选记忆。
- 记忆有效性定期复查。
- 多模型 tokenizer。
