# asset-tool

AI 编程平台的代码资产管理工具。负责代码片段、配置模板、命令模板、设计模式的存储和检索。

## 快速开始

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 18082 --reload
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
- 资产管理: `POST /api/assets`
- 检索: `POST /api/assets/search`
- 渲染: `POST /api/assets/render`

## 技术栈

- Python 3.13
- FastAPI
- SQLAlchemy 2.0 (async)
- PostgreSQL
- Jinja2 (模板渲染)
