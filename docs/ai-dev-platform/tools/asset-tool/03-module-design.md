# asset-tool 模块设计

## 1. 模块划分

```text
asset-tool/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置加载
│   ├── models/
│   │   ├── __init__.py
│   │   └── asset.py         # SQLAlchemy 模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── asset.py         # Pydantic 模型
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py        # 健康检查
│   │   ├── tool.py          # 工具协议接口
│   │   └── assets.py        # 资产 API
│   ├── services/
│   │   ├── __init__.py
│   │   ├── asset_service.py # 资产业务逻辑
│   │   └── template_engine.py # 模板渲染
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── asset_repo.py    # 数据访问
│   └── db/
│       ├── __init__.py
│       ├── database.py      # 数据库连接
│       └── init_db.py       # 迁移
├── tool.yaml
├── openapi.yaml
├── config.example.yaml
├── requirements.txt
├── Dockerfile
└── tests/
```

## 2. 服务职责

### 2.1 AssetService

- 资产 CRUD。
- 资产检索（关键词）。
- 权限校验。
- trace_id 透传。

### 2.2 TemplateEngine

- 模板变量解析。
- 模板渲染。
- 变量替换。

### 2.3 AssetRepository

- 数据库 CRUD。
- 关键词检索。
- scope 过滤。

## 3. 配置项

| 配置 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `database.url` | string | - | PostgreSQL 连接 |
| `asset.storage.provider` | string | `local` | 存储提供者 |
| `asset.storage.localRoot` | string | `./data/asset` | 本地存储路径 |
| `asset.search.defaultTopK` | int | `8` | 默认返回数量 |
| `asset.search.maxTopK` | int | `50` | 最大返回数量 |
| `asset.upload.maxContentSizeMb` | int | `10` | 最大内容大小 |

## 4. 异常处理

| 异常 | HTTP 码 | 错误码 |
|---|---|---|
| 资产不存在 | 404 | `NOT_FOUND` |
| 权限不足 | 403 | `FORBIDDEN` |
| 参数校验失败 | 400 | `VALIDATION_ERROR` |
| 数据库错误 | 500 | `INTERNAL_ERROR` |
