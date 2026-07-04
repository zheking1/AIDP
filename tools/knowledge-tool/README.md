# knowledge-tool

AI 编程平台的文档知识库工具。负责文档上传、解析、切片、向量化、索引和检索。

## 快速开始

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 18081 --reload
```

## Docker

```bash
docker compose up -d
```

## API

- 健康检查: `GET /health`
- 工具清单: `GET /tool/manifest`
- 工具能力: `GET /tool/capabilities`
- 工具调用: `POST /tool/invoke`
- 文档管理: `POST /api/documents`
- 检索: `POST /api/knowledge/search`

## 技术栈

- Python 3.13
- FastAPI
- SQLAlchemy 2.0 (async)
- PostgreSQL
- Mock Embedding
