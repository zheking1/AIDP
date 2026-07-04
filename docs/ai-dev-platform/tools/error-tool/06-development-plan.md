# error-tool 开发计划

## 1. 里程碑

| 里程碑 | 周期 | 交付 |
|---|---:|---|
| M1 工具骨架 | 1 天 | tool.yaml、健康检查、capability 路由 |
| M2 错误记录 | 2 天 | record API、脱敏、raw log 存储、error_case |
| M3 错误归一化 | 2 天 | TypeScript/Python/Node/Test normalizer |
| M4 相似检索 | 2 天 | fingerprint、关键词检索、排序 |
| M5 解决方案闭环 | 2 天 | link_solution、resolve、质量统计 |
| M6 联动和测试 | 1-2 天 | sandbox/quality 示例、集成测试 |

## 2. AI 编码任务

### Task 1：工具协议实现

- 实现 `/health`、`/tool/manifest`、`/tool/capabilities`、`/tool/invoke`。
- `tool.yaml` 注册 5 个 capability。
- 统一错误模型。

### Task 2：数据模型和迁移

- 按 `05-data-model.md` 创建表。
- 实现 repository。
- 增加 scope 查询方法。

### Task 3：raw log 存储与脱敏

- 实现 `SecretRedactor`。
- 实现 `RawLogStorage` 本地文件版本。
- 超过限制返回 `VALIDATION_ERROR`。

### Task 4：错误归一化

- 实现 normalizer registry。
- 实现 TypeScript compile、Python exception、Node runtime、test failure 四个 normalizer。
- fallback normalizer 保证未知错误可保存。

### Task 5：record 和 search

- `error.record` 完成归一化、fingerprint、入库。
- `error.search` 完成 fingerprint 优先、关键词检索、结构化排序。

### Task 6：solution 和 resolve

- 实现解决方案绑定。
- 实现验证回写。
- resolved 后提升检索排序。

### Task 7：工具联动

- 提供 sandbox 失败日志示例。
- 提供 quality 检查失败示例。
- 实现 `error.export_pattern` 的 asset-tool client 接口，可先 mock。

## 3. 风险控制

| 风险 | 控制 |
|---|---|
| 日志泄露敏感信息 | 保存前强制脱敏，测试覆盖 token/password |
| 归一化误判 | fallback 保留原始摘要，normalizer 可迭代 |
| 检索噪声大 | fingerprint + structured fields 优先 |
| 工具耦合过重 | asset/sandbox/quality 通过 HTTP client 可选接入 |

## 4. 交付清单

- `tool.yaml`
- `openapi.yaml`
- `config.example.yaml`
- SQL/Drizzle migration 脚本
- normalizer 单元测试
- API 集成测试
- `examples/record-typescript.json`
- `examples/search-similar.json`
- `examples/link-solution.json`
