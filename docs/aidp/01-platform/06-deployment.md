# 部署架构

## 总览

AIDP 采用 Docker + docker-compose 部署，所有服务使用 `network_mode: host` 共享主机网络栈。核心基础设施有 PostgreSQL 16 + pgvector 和 Redis 7。

**部署目标**: NAS 服务器 (192.168.0.100)

## Docker Compose 文件清单

| 文件 | 服务 | 说明 |
|------|------|------|
| `docker-compose.yml` (根) | controller, sandbox-tool, quality-tool | 顶层编排，3 个核心服务 |
| `apps/controller/docker-compose.yml` | controller | 独立构建和运行 |
| `tools/skill-router/docker-compose.yml` | skill-router | 技能路由引擎 |
| `tools/knowledge-tool/docker-compose.yml` | knowledge-tool | 知识库工具 |
| `tools/memory-tool/docker-compose.yml` | memory-tool | 记忆工具 |
| `tools/asset-tool/docker-compose.yml` | asset-tool | 资产管理 |
| `tools/sandbox-tool/docker-compose.yml` | sandbox-tool | 代码沙箱 |
| `tools/quality-tool/docker-compose.yml` | quality-tool | 质量检查 |
| `tools/code-index/docker-compose.yml` | code-index | 代码索引 |
| `tools/importer-tool/docker-compose.yml` | importer-tool | 项目导入器 |
| `tools/file-watcher/docker-compose.yml` | file-watcher | 文件监听 |

> 注: doc-index, context-optimizer, evolution-engine 无独立 docker-compose，使用 Dockerfile 直接构建。

## Dockerfile 清单

| 路径 | 镜像 | 端口 | 基础镜像 |
|------|------|------|---------|
| `apps/controller/Dockerfile` | `aidp/controller:0.1.0` | `8883` | `python:3.13-slim` |
| `tools/skill-router/Dockerfile` | 自定义 | `8788` | `python:3.13-slim` |
| `tools/knowledge-tool/Dockerfile` | 自定义 | `18081` | `python:3.13-slim` |
| `tools/asset-tool/Dockerfile` | 自定义 | `18082` | `python:3.13-slim` |
| `tools/sandbox-tool/Dockerfile` | `aidp/sandbox-tool:0.1.0` | `18083` | `python:3.13-slim` |
| `tools/quality-tool/Dockerfile` | `aidp/quality-tool:0.1.0` | `18084` | `python:3.13-slim` |
| `tools/memory-tool/Dockerfile` | 自定义 | `18085` | `python:3.13-slim` |
| `tools/code-index/Dockerfile` | 自定义 | `18086` | `python:3.13-slim` |
| `tools/doc-index/Dockerfile` | 自定义 | `18087` | `python:3.13-slim` |
| `tools/context-optimizer/Dockerfile` | 自定义 | `18088` | `python:3.13-slim` |
| `tools/evolution-engine/Dockerfile` | 自定义 | `18089` | `python:3.13-slim` |
| `tools/project-importer/Dockerfile` | 自定义 | `18090` | `python:3.13-slim` |
| `tools/file-watcher/Dockerfile` | 自定义 | `18091` | `python:3.13-slim` |
| `tools/importer-tool/Dockerfile` | `aidp/importer-tool:0.1.0` | `18085` | `python:3.13-slim` |

所有 Dockerfile 模式相同：`FROM python:3.13-slim` → `WORKDIR /app` → `pip install requirements.txt` → `COPY . .` → `EXPOSE {port}` → `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "{port}"]`

## 网络配置

### `network_mode: host`

**所有容器都使用 `network_mode: host`**（除 PostgreSQL/Redis 构造容器外）。这意味着容器直接共享主机的网络栈，不需要端口映射，各服务直接通过 `localhost:{port}` 互相访问。

### PostgreSQL 数据库

- **主机**: NAS 服务器 `192.168.0.100`
- **IP 段**: PostgreSQL 通过 Docker bridge 网络可能位于 `172.20.0.x`
- **端口**: `5432`
- **数据库名**: `aidp`
- **扩展**: pgvector
- **连接字符串示例**: `postgresql+asyncpg://novel_os:jygame_postgres_01@127.0.0.1:5432/aidp`

### Controller 特殊设置

Controller 使用 `network_mode: host` 并通过环境变量配置 DB IP：

```yaml
# docker-compose.yml (根目录)
controller:
  image: aidp/controller:0.1.0
  container_name: aidp-controller
  network_mode: host
  environment:
    DATABASE_URL: postgresql+asyncpg://novel_os:jygame_postgres_01@127.0.0.1:5432/aidp
    REDIS_URL: redis://127.0.0.1:6379/0
```

### Redis

- Redis 7，端口 `6379`
- 用于缓存 (ContextCache, TTL=300s)

### NAS 存储

NAS 路径: `/home/docker/AI-Code` (挂载到 code-index 容器)

## 各容器配置详情

### 1. Controller (端口 8883)

```yaml
services:
  controller:
    image: aidp/controller:0.1.0
    container_name: aidp-controller
    network_mode: host
    environment:
      DATABASE_URL: ${CONTROLLER_DB_URL}
      REDIS_URL: ${REDIS_URL}
      CONTROLLER_SESSION_KEY: ${CONTROLLER_SESSION_KEY}
    restart: unless-stopped
```

### 2. Sandbox Tool (端口 18083)

```yaml
services:
  sandbox-tool:
    image: aidp/sandbox-tool:0.1.0
    container_name: aidp-sandbox
    network_mode: host
    environment:
      DATABASE_URL: ${SANDBOX_DB_URL}
    restart: unless-stopped
```

### 3. Quality Tool (端口 18084)

```yaml
services:
  quality-tool:
    image: aidp/quality-tool:0.1.0
    container_name: aidp-quality
    network_mode: host
    environment:
      DATABASE_URL: ${QUALITY_DB_URL}
    restart: unless-stopped
```

### 4. Skill Router (端口 8788)

```yaml
services:
  app:
    build: .
    network_mode: host
    env_file: .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### 5. Knowledge Tool (端口 18081)

```yaml
services:
  knowledge-tool:
    build: .
    network_mode: host
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - STORAGE_LOCAL_ROOT=/app/data/knowledge
    volumes:
      - ./data/knowledge:/app/data/knowledge
    restart: unless-stopped
```

### 6. Memory Tool (端口 18085)

```yaml
services:
  memory-tool:
    build: .
    network_mode: host
    environment:
      - DATABASE_URL=${DATABASE_URL}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### 7. Asset Tool (端口 18082)

```yaml
services:
  asset-tool:
    build: .
    network_mode: host
    environment:
      - DATABASE_URL=${DATABASE_URL}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### 8. Code Index (端口 18086)

```yaml
services:
  code-index:
    build: .
    network_mode: host
    volumes:
      - /home/docker/AI-Code:/home/docker/AI-Code:ro  # NAS 挂载，只读
    restart: unless-stopped
```

### 9. Doc Index (端口 18087)

独立部署，无 docker-compose。直接构建 Dockerfile。

### 10. Context Optimizer (端口 18088)

独立部署，无 docker-compose。

### 11. Evolution Engine (端口 18089)

独立部署，无 docker-compose。

### 12. Project Importer (端口 18090)

独立部署，无 docker-compose。

### 13. File Watcher (端口 18091)

```yaml
# tools/file-watcher/docker-compose.yml
services: ...  # 独立 docker-compose
```

### 14. Importer Tool (端口 18085)

```yaml
services:
  importer-tool:
    build: .
    image: aidp/importer-tool:0.1.0
    network_mode: host
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/aidp_importer
      - CONTROLLER_URL=http://localhost:8883
    volumes:
      - ./data:/app/data
```

## Volume 挂载汇总

| 容器 | 主机路径 | 容器路径 | 权限 |
|------|----------|---------|------|
| skill-router | `./data` | `/app/data` | rw |
| knowledge-tool | `./data/knowledge` | `/app/data/knowledge` | rw |
| memory-tool | `./data` | `/app/data` | rw |
| asset-tool | `./data` | `/app/data` | rw |
| sandbox-tool | `./data` | `/app/data` | rw |
| quality-tool | `./data` | `/app/data` | rw |
| code-index | `/home/docker/AI-Code` | `/home/docker/AI-Code` | ro (只读) |
| importer-tool | `./data` | `/app/data` | rw |

## 完整端口映射

| 服务 | 端口 | 数据库 |
|------|------|--------|
| controller | `8883` | PostgreSQL aidp |
| skill-router | `8788` | PostgreSQL + Redis |
| knowledge-tool | `18081` | SQLite (`data/knowledge.db`) |
| asset-tool | `18082` | SQLite |
| sandbox-tool | `18083` | PostgreSQL aidp |
| quality-tool | `18084` | PostgreSQL aidp |
| memory-tool | `18085` | SQLite (`data/memory.db`) |
| code-index | `18086` | SQLite (`data/code_index.db`) |
| doc-index | `18087` | SQLite (`data/doc_index.db`) |
| context-optimizer | `18088` | SQLite |
| evolution-engine | `18089` | SQLite |
| project-importer | `18090` | — |
| file-watcher | `18091` | SQLite |
| importer-tool | `18085` | PostgreSQL aidp_importer |
| PostgreSQL | `5432` | `172.20.0.x` |
| Redis | `6379` | `127.0.0.1` |

## 部署步骤

```bash
# 1. 全量部署到 NAS
powershell deploy/deploy-nas.ps1

# 2. 或逐个服务启动
# Controller
cd apps/controller && docker compose up -d

# 工具
cd tools/skill-router && docker compose up -d
cd tools/knowledge-tool && docker compose up -d
cd tools/memory-tool && docker compose up -d
cd tools/asset-tool && docker compose up -d
cd tools/sandbox-tool && docker compose up -d
cd tools/quality-tool && docker compose up -d
cd tools/code-index && docker compose up -d

# 3. 验证
curl http://localhost:8883/health
curl http://localhost:8883/api/tools
```