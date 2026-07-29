# Knowledge Tool - Overview

## Purpose

Knowledge Tool 是 AIDP 平台的知识管理核心组件，提供文档摄取、索引构建和检索能力。

## Configuration (`app/config.py`)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | `knowledge-tool` | 应用名称 |
| `APP_VERSION` | `0.1.0` | 版本号 |
| `HOST` / `PORT` | `0.0.0.0:18081` | 服务监听地址 |
| `DATABASE_URL` | `""` | 数据库连接串（PostgreSQL） |
| `STORAGE_PROVIDER` | `local` | 文件存储后端（`local`/`minio`/`s3`） |
| `STORAGE_LOCAL_ROOT` | `./data/knowledge` | 本地存储根目录 |
| `EMBEDDING_PROVIDER` | `mock` | 嵌入模型（`mock`/`openai`/`local`） |
| `EMBEDDING_MODEL` | `mock-embedding-v1` | 默认模型名 |
| `EMBEDDING_DIMENSION` | `384` | 嵌入向量维度 |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | - | OpenAI 配置 |
| `LOCAL_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | 本地模型名 |
| `CHUNK_DEFAULT_SIZE` | `800` | 默认分块大小 |
| `CHUNK_DEFAULT_OVERLAP` | `120` | 分块重叠字数 |
| `CHUNK_MAX_SIZE` | `1600` | 最大分块大小 |
| `SEARCH_DEFAULT_TOP_K` | `8` | 默认检索结果数 |
| `SEARCH_MAX_TOP_K` | `50` | 最大检索结果数 |
| `SEARCH_DEFAULT_MODE` | `hybrid` | 默认搜索模式 |
| `UPLOAD_MAX_FILE_SIZE_MB` | `50` | 上传文件大小上限 |

## Manifest (`tool.yaml`)

- **API 版本**: `aidp.dev/v1`
- **运行时模式**: `standalone`、`managed`
- **Docker 镜像**: `aidp/knowledge-tool:0.1.0`
- **本地启动**: `uvicorn app.main:app --host 0.0.0.0 --port 18081`
- **健康检查**: `GET http://127.0.0.1:18081/health`

## Dependencies

- **必需**: PostgreSQL
- **可选**: pgvector（向量扩展）

## Capabilities

| Capability | 说明 | 端点 | 权限 |
|------------|------|------|------|
| `knowledge.search` | 搜索已索引的文档块 | `POST /api/knowledge/search` | `knowledge:search` |
| `knowledge.create_document` | 创建并索引文档 | `POST /api/documents` | `knowledge:write` |
| `document.index` | 为文档创建索引任务 | `POST /api/documents/{id}/index` | `knowledge:index` |

## Architecture

```
用户/Agent → API Layer (FastAPI)
    ├── /api/documents   → document_service (CRUD)
    ├── /api/knowledge   → search_service (检索)
    └── /tool/invoke     → capability 调度
         ↓
    Services: document_service / indexing_service / search_service
         ↓
    Storage: PostgreSQL + 本地文件存储
```

嵌入提供者支持 mock（测试）、OpenAI、本地 three 种模式，可配置切换。