# asset-tool 开发计划

## 1. 里程碑

| 里程碑 | 周期 | 交付 |
|---|---|---|
| M1 工程骨架 | 1 天 | Python + FastAPI + PostgreSQL + OpenAPI |
| M2 资产 CRUD | 2 天 | snippet/config/command/pattern CRUD |
| M3 资产检索 | 1 天 | keyword search + scope 过滤 |
| M4 模板渲染 | 1 天 | Jinja2 模板渲染 |
| M5 工具协议 | 1 天 | /tool/invoke + trace_id + 审计 |
| M6 测试验收 | 1 天 | 单元测试 + 集成测试 |

总周期：7 天。

## 2. AI 编码任务

1. 创建 Python + FastAPI 工程骨架。
2. 实现 PostgreSQL migration。
3. 实现资产 CRUD API。
4. 实现关键词检索。
5. 实现模板渲染。
6. 实现工具协议接口。
7. 实现单元测试和集成测试。

## 3. 风险控制

| 风险 | 控制 |
|---|---|
| 检索性能不足 | 全文检索索引 + scope 过滤 |
| 模板注入风险 | Jinja2 沙箱模式 |
| 数据量增长 | 软删除 + 定期清理 |

## 4. MVP 交付清单

- `tools/asset-tool/`
- `tool.yaml`
- `openapi.yaml`
- `config.example.yaml`
- Dockerfile
- docker-compose.yml
- 测试集
