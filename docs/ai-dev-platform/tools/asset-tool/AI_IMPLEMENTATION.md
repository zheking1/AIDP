# asset-tool AI 开发实施提示

## 1. 本轮目标

实现 `asset-tool` 的 MVP，包括：

- Python + FastAPI 工程骨架。
- PostgreSQL 数据库和迁移。
- 资产 CRUD API。
- 关键词检索。
- 模板渲染。
- 工具协议接口。
- 单元测试和集成测试。

## 2. 读取文档

- `docs/ai-dev-platform/DEVELOPMENT_PROMPT.md`
- `docs/ai-dev-platform/common/tool-contract.md`
- `docs/ai-dev-platform/common/engineering-standards.md`
- `docs/ai-dev-platform/tools/asset-tool/` 下全部文档

## 3. 实现范围

### 3.1 工程骨架

```text
tools/asset-tool/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   └── asset.py
│   ├── schemas/
│   │   └── asset.py
│   ├── api/
│   │   ├── health.py
│   │   ├── tool.py
│   │   └── assets.py
│   ├── services/
│   │   ├── asset_service.py
│   │   └── template_engine.py
│   ├── repositories/
│   │   └── asset_repo.py
│   └── db/
│       ├── database.py
│       └── init_db.py
├── tool.yaml
├── openapi.yaml
├── config.example.yaml
├── requirements.txt
├── Dockerfile
└── tests/
```

### 3.2 数据库

- `at_asset` 表。
- `at_asset_tag` 表。
- 全文检索索引。

### 3.3 API

- 资产 CRUD。
- 关键词检索。
- 模板渲染。
- 工具协议接口。

### 3.4 测试

- 单元测试。
- API 测试。
- 集成测试。

## 4. 不做范围

- 不做语义检索（向量检索）。
- 不做复杂模板逻辑。
- 不做管理后台。
- 不做批量导入。
- 不引入文档未要求的重型依赖。

## 5. 验收方式

- 工具可独立启动。
- 工具可被 controller 托管。
- `/tool/invoke` 可调用 `asset.search`。
- 跨项目隔离测试通过。
- 单元测试和集成测试通过。

## 6. 技术约束

- Python 3.13 + FastAPI。
- SQLAlchemy 2.0 (async)。
- PostgreSQL。
- Jinja2（模板渲染）。
- 不引入 TypeScript/Node.js。
- 不引入 Nacos/Kubernetes。
