# 部署指南

## 1. 概述

AIDP 系统部署在 NAS（192.168.0.100）上，采用 Docker 容器化部署。所有服务使用 `network_mode: host`，数据通过 bind-mount 持久化到 NAS 本地目录。

### 1.1 部署架构

```
NAS (192.168.0.100)
├── Controller:8883      (Web UI + API + MCP)
├── sandbox-tool:18083   (代码沙箱)
├── knowledge-tool:18081 (知识库)
├── memory-tool:18085    (记忆系统)
├── quality-tool:18084   (质量检查)
├── asset-tool:18082     (资产库)
├── skill-router:8788    (技能路由)
├── PostgreSQL:5432      (数据库)
└── Redis:6379           (缓存)

部署路径: /home/docker/AI-Code/
数据目录: /home/docker/AI-Code/*/data/
```

### 1.2 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Controller | 8883 | Web UI + API + MCP |
| knowledge-tool | 18081 | 知识库服务 |
| asset-tool | 18082 | 资产库服务 |
| sandbox-tool | 18083 | 代码沙箱 |
| quality-tool | 18084 | 质量检查 |
| memory-tool | 18085 | 记忆系统 |
| skill-router | 8788 | 技能路由 |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存 |

## 2. 环境配置

### 2.1 必需环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://user:pass@127.0.0.1:5432/novel_os` |
| `REDIS_URL` | Redis 连接串 | `redis://127.0.0.1:6379/0` |
| `ADMIN_USERNAME` | 默认管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 默认管理员密码 | `admin123` |

### 2.2 可选环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_ENDPOINT` | LLM API 端点 | — |
| `LLM_API_KEY` | LLM API 密钥 | — |
| `LLM_MODEL` | LLM 模型名称 | — |
| `EMBEDDING_ENDPOINT` | Embedding API 端点 | — |
| `EMBEDDING_API_KEY` | Embedding API 密钥 | — |
| `EMBEDDING_MODEL` | Embedding 模型 | `text-embedding-3-small` |
| `EMBEDDING_DIM` | Embedding 维度 | `384` |

### 2.3 工具服务环境变量

每个工具服务支持独立的数据库 URL 覆盖：

| 变量 | 说明 |
|------|------|
| `SANDBOX_DB_URL` | 沙箱工具数据库 URL |
| `QUALITY_DB_URL` | 质量检查数据库 URL |
| `KNOWLEDGE_DB_URL` | 知识库数据库 URL |
| `MEMORY_DB_URL` | 记忆系统数据库 URL |
| `ASSET_DB_URL` | 资产库数据库 URL |

## 3. Docker 配置

### 3.1 Controller Dockerfile

**文件**: `apps/controller/Dockerfile`

```dockerfile
FROM docker.1ms.run/library/python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8883
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8883"]
```

### 3.2 工具 Dockerfile 模板

所有工具 Dockerfile 遵循相同模式：

```dockerfile
FROM docker.1ms.run/library/python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {PORT}
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "{PORT}"]
```

### 3.3 docker-compose.yml

**文件**: `docker-compose.yml`

```yaml
version: '3.8'
services:
  controller:
    image: aidp/controller:0.1.0
    network_mode: host
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=${DATABASE_URL}
    restart: unless-stopped

  sandbox-tool:
    image: aidp/sandbox-tool:0.1.0
    network_mode: host
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=${DATABASE_URL}
    restart: unless-stopped

  quality-tool:
    image: aidp/quality-tool:0.1.0
    network_mode: host
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=${DATABASE_URL}
    restart: unless-stopped
```

## 4. 部署流程

### 4.1 首次部署

```bash
# 1. SSH 到 NAS
ssh -i ~/.ssh/nas_temp root@192.168.0.100

# 2. 创建部署目录
mkdir -p /home/docker/AI-Code/controller/data
mkdir -p /home/docker/AI-Code/sandbox-tool/data
mkdir -p /home/docker/AI-Code/knowledge-tool/data/knowledge
mkdir -p /home/docker/AI-Code/memory-tool/data
mkdir -p /home/docker/AI-Code/quality-tool/data
mkdir -p /home/docker/AI-Code/asset-tool/data

# 3. 上传源代码
scp -i ~/.ssh/nas_temp -r apps/controller/ root@192.168.0.100:/home/docker/AI-Code/controller/
scp -i ~/.ssh/nas_temp -r tools/sandbox-tool/ root@192.168.0.100:/home/docker/AI-Code/sandbox-tool/
# ... 其他工具类似

# 4. 构建镜像
cd /home/docker/AI-Code/controller
docker build -t aidp/controller:0.1.0 .

# 5. 启动容器
docker run -d \
  --name aidp-controller \
  --network host \
  -v /home/docker/AI-Code/controller/data:/app/data \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@127.0.0.1:5432/novel_os \
  --restart unless-stopped \
  aidp/controller:0.1.0
```

### 4.2 更新部署

```bash
# 1. 上传更新的源代码
scp -i ~/.ssh/nas_temp apps/controller/app/web/routes.py root@192.168.0.100:/home/docker/AI-Code/controller/app/web/routes.py

# 2. 触发 Docker 缓存失效
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "touch /home/docker/AI-Code/controller/app/web/routes.py"

# 3. 重新构建（必须 --no-cache）
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "cd /home/docker/AI-Code/controller && docker build --no-cache -t aidp/controller:0.1.0 ."

# 4. 重启容器
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker stop aidp-controller && docker rm aidp-controller && docker run -d --name aidp-controller --network host -v /home/docker/AI-Code/controller/data:/app/data -e DATABASE_URL=... --restart unless-stopped aidp/controller:0.1.0"
```

### 4.3 使用部署脚本

**文件**: `deploy/deploy-nas.ps1`

```powershell
# PowerShell 脚本：上传源代码到 NAS 并构建
.\deploy\deploy-nas.ps1
```

**文件**: `deploy/deploy-now.ps1`

```powershell
# PowerShell 脚本：上传源代码 + 构建 + 启动所有服务
.\deploy\deploy-now.ps1
```

## 5. 数据持久化

### 5.1 数据目录结构

```
/home/docker/AI-Code/
├── controller/
│   └── data/
│       └── controller.db      # SQLite 数据库（如果使用 SQLite）
├── sandbox-tool/
│   └── data/                  # 执行记录
├── knowledge-tool/
│   └── data/
│       └── knowledge/         # 知识文件存储
├── memory-tool/
│   └── data/                  # 记忆条目
├── quality-tool/
│   └── data/                  # 检查结果
└── asset-tool/
    └── data/                  # 资产文件
```

### 5.2 数据库备份

**文件**: `deploy/backup-db.sh`

```bash
#!/bin/bash
# 每天凌晨 2 点执行
docker exec novel-postgres pg_dump -U novel_os novel_os | gzip > /home/docker/AI-Code/backups/backup_$(date +%Y%m%d).sql.gz
# 保留最近 7 个备份
ls -t /home/docker/AI-Code/backups/backup_*.sql.gz | tail -n +8 | xargs rm -f
```

### 5.3 健康监控

**文件**: `deploy/health-monitor.sh`

```bash
#!/bin/bash
# 每 5 分钟执行
# 检查所有服务健康状态
services=("controller:8883" "sandbox-tool:18083" "knowledge-tool:18081" ...)
for svc in "${services[@]}"; do
    name=${svc%%:*}
    port=${svc##*:}
    if ! curl -sf http://localhost:$port/health > /dev/null; then
        echo "DOWN: $name"
    fi
done
```

## 6. 故障排查

### 6.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 容器启动失败 | 端口被占用 | `netstat -tlnp \| grep 8883` 检查端口 |
| 数据库连接失败 | PostgreSQL 未运行 | `docker ps \| grep postgres` 检查 |
| 工具不可用 | 未注册到 Controller | `POST /api/tools` 注册工具 |
| MCP 调用失败 | 会话未加载上下文 | 先调用 `aidp_context` |
| 数据丢失 | 未挂载 volume | 检查 `-v` 参数 |

### 6.2 日志查看

```bash
# 查看容器日志
docker logs -f aidp-controller

# 查看最近 100 行
docker logs --tail 100 aidp-controller
```

### 6.3 进入容器调试

```bash
docker exec -it aidp-controller bash
```

## 7. 关键文件索引

| 文件 | 用途 |
|------|------|
| `apps/controller/Dockerfile` | Controller Docker 配置 |
| `docker-compose.yml` | 根 docker-compose |
| `tools/*/Dockerfile` | 各工具 Docker 配置 |
| `deploy/deploy.ps1` | 本地构建 + 远程部署脚本 |
| `deploy/deploy-nas.ps1` | NAS 部署脚本 |
| `deploy/deploy-now.ps1` | 一键部署脚本 |
| `deploy/backup-db.sh` | 数据库备份脚本 |
| `deploy/health-monitor.sh` | 健康监控脚本 |
| `deploy/init-db.sql` | 数据库初始化 SQL |
| `.env.example` | 环境变量模板 |
