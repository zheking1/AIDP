# SkillRouter 部署与测试指南

---

## 一、环境要求

### 1.1 基础服务

| 服务 | 版本 | 用途 | 必需 |
|------|------|------|------|
| PostgreSQL | 14+ | 数据库 | 是 |
| pgvector | 0.5+ | 向量搜索 | 是 |
| Redis | 7+ | 缓存 + 限流 | 是 |
| Docker | 24+ | 部署 | 是 |

### 1.2 外部 API

| 服务 | 用途 | 必需 |
|------|------|------|
| LLM API（OpenAI 兼容） | 意图分析 + 重排序 | 可降级 |
| Embedding API | 向量生成 | 是 |

---

## 二、NAS 部署（生产环境）

### 2.1 服务器信息

| 项目 | 值 |
|------|-----|
| NAS IP | 192.168.0.100 |
| SSH | root，密钥 `~/.ssh/nas_temp` |
| PostgreSQL | 127.0.0.1:5432 (host networking) |
| Redis | 192.168.0.100:6379/0 |
| 端口 | 8788 |
| 容器名 | skillrouter-app-1 |
| 镜像加速 | docker.1ms.run/library/ |

### 2.2 操作目录约束

**所有文件操作必须在以下目录进行：**

```
# NAS 上的项目目录（唯一允许操作的路径）
/path/to/SkillRouter/

# 临时文件目录（SCP 中转用）
/tmp/
```

**禁止操作：**
- `/root/`、`/home/` 等非项目目录
- 容器内 `/app/` 目录（只能通过 `docker cp` 写入）
- 其他任意路径

**规则：**
1. 代码修改在本地 Windows 完成
2. 通过 SCP 传输到 NAS 的 `/tmp/` 目录
3. 通过 `docker cp` 复制到容器内 `/app/`
4. 不直接在 NAS 上编辑代码文件

### 2.3 首次部署

```bash
# 1. 上传项目到 NAS
scp -i ~/.ssh/nas_temp -r D:\Project\openCode\SkillRouter root@192.168.0.100:/path/to/SkillRouter/

# 2. SSH 进入 NAS
ssh -i ~/.ssh/nas_temp root@192.168.0.100

# 3. 进入项目目录
cd /path/to/SkillRouter

# 4. 配置环境变量
cp .env.example .env
vi .env  # 填入实际配置

# 5. 构建并启动
docker compose up -d --build
```

### 2.4 热更新（不重建镜像）

修改代码后，按以下流程操作：

```bash
# 本地 Windows 执行：
# 1. SCP 传文件到 NAS /tmp/
scp -i ~/.ssh/nas_temp app/main.py root@192.168.0.100:/tmp/main.py

# 2. SSH 执行 docker cp + restart
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker cp /tmp/main.py skillrouter-app-1:/app/app/main.py && docker restart skillrouter-app-1"
```

**Python 单行写法（避免 PowerShell 转义问题）：**

```powershell
scp -i "$env:USERPROFILE\.ssh\nas_temp" "app\main.py" root@192.168.0.100:/tmp/main.py; ssh -i "$env:USERPROFILE\.ssh\nas_temp" root@192.168.0.100 "docker cp /tmp/main.py skillrouter-app-1:/app/app/main.py && docker restart skillrouter-app-1"
```

### 2.5 数据库迁移

```bash
# init_db.py 只会 ADD COLUMN / CREATE TABLE，不会 DROP
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker exec skillrouter-app-1 python -c \"from app.db.init_db import init_database; import asyncio; asyncio.run(init_database())\""
```

### 2.6 常用运维

```bash
# 重启服务
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker restart skillrouter-app-1"

# 查看日志
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker logs -f skillrouter-app-1"

# 查看容器资源占用
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker stats skillrouter-app-1 --no-stream"

# 进入容器
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker exec -it skillrouter-app-1 bash"

# 清理旧镜像
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker image prune -f"
```

---

## 三、测试

### 3.1 集成测试

```bash
# 运行全部测试（需要数据库已初始化）
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker exec skillrouter-app-1 python -m pytest tests/ -v"

# 运行单个测试文件
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker exec skillrouter-app-1 python -m pytest tests/test_resolve.py -v"
```

**注意**：测试会创建数据，可能与 uniqueness 约束冲突。运行前建议清空数据库：

```bash
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker exec skillrouter-app-1 python -c \"
import asyncio
from app.db.database import async_session_factory
from sqlalchemy import text

async def clear():
    async with async_session_factory() as s:
        await s.execute(text('TRUNCATE skills, rules, llm_configs, projects, skill_groups, rule_groups, api_keys, evolutions, operation_logs, operation_log_details, review_patterns CASCADE'))
        await s.commit()
        print('Database cleared')

asyncio.run(clear())
\""
```

### 3.2 MCP 工具测试

```python
import asyncio
from fastmcp import Client

async def test():
    async with Client("http://192.168.0.100:8788/mcp/") as client:
        tools = await client.list_tools()
        print(f"Tools: {len(tools)}")

        result = await client.call_tool("resolve_task", {
            "task": "debug Python error",
            "api_key": "your-api-key",
        })
        print(result)

asyncio.run(test())
```

### 3.3 REST API 测试

```bash
# 登录获取 session
curl -c cookies.txt -X POST http://192.168.0.100:8788/login \
  -d "username=admin&password=admin123"

# 调用 API（带 session cookie）
curl -b cookies.txt http://192.168.0.100:8788/api/skills

# 或用 API Key
curl -H "X-API-Key: your-api-key" http://192.168.0.100:8788/api/skills
```

### 3.4 Web UI 手动测试

| 页面 | URL | 测试项 |
|------|-----|--------|
| 登录 | /login | 账密校验、session |
| 注册 | /register | 创建用户、自动登录 |
| 技能列表 | /skills | 搜索、分组、CRUD |
| 技能导入 | /skills/import | GitHub URL 预览、导入 |
| 规则列表 | /rules | 搜索、分组、CRUD |
| 模型列表 | /models | CRUD、角色切换 |
| 项目列表 | /projects | CRUD、技能/规则关联 |
| 解析测试 | /resolve | 执行 resolve、查看结果 |
| 缓存管理 | /cache | 查看、清空缓存 |
| API Key | /api-keys | 生成、撤销、复制 |
| 系统设置 | /settings | 注册开关（admin） |

### 3.5 CLI 测试

```bash
pip install -e cli/

srcli config set-server http://192.168.0.100:8788
srcli config set-api-key your-api-key

srcli list
srcli install <skill-name>
srcli run <skill-name> -- --param1 value1
```

---

## 四、故障排查

### 4.1 服务无法启动

```bash
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker logs skillrouter-app-1"

# 常见原因：
# 1. 数据库连接失败 → 检查 .env 中 DATABASE_URL
# 2. Redis 连接失败 → 检查 .env 中 REDIS_URL
# 3. 端口占用 → ssh root@192.168.0.100 "lsof -i :8788"
```

### 4.2 MCP 连接失败

```bash
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "curl -N http://127.0.0.1:8788/mcp/"

# 应返回 streamable-http 响应
# 500 错误 → 检查 lifespan 嵌套顺序是否正确
```

### 4.3 Embedding 维度不匹配

```bash
ssh -i ~/.ssh/nas_temp root@192.168.0.100 "docker exec skillrouter-app-1 python -c \"
import asyncio
from app.services.vector_service import detect_embedding_dim
print(asyncio.run(detect_embedding_dim()))
\""

# 维度不是 384 → 修改 .env 中 EMBEDDING_DIM → 重新迁移
```

### 4.4 权限错误

```bash
# MCP 工具返回 PERMISSION_DENIED
# → 检查 api_key 是否有效
# → 检查 ApiKey 表中是否有对应记录

# Web UI 返回 403
# → 检查 session 中 user_id 是否存在
# → 检查 user.role 是否为 admin
```

---

## 五、环境变量速查

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | — | PostgreSQL 连接串 |
| `REDIS_URL` | redis://localhost:6379/0 | Redis 地址 |
| `ADMIN_USERNAME` | admin | 初始管理员用户名 |
| `ADMIN_PASSWORD` | admin123 | 初始管理员密码 |
| `LLM_ENDPOINT` | http://localhost:8000/v1 | LLM API 地址 |
| `LLM_API_KEY` | sk-xxx | LLM API Key |
| `LLM_MODEL` | deepseek-v4-flash-free | LLM 模型名 |
| `EMBEDDING_ENDPOINT` | http://localhost:8000/v1 | Embedding API 地址 |
| `EMBEDDING_API_KEY` | sk-xxx | Embedding API Key |
| `EMBEDDING_MODEL` | text-embedding-3-small | Embedding 模型名 |
| `EMBEDDING_DIM` | 384 | 向量维度 |
| `LLM_TIMEOUT` | 30 | LLM 超时（秒） |
| `EMBEDDING_TIMEOUT` | 15 | Embedding 超时（秒） |
| `RESOLVE_TOP_K_DEFAULT` | 5 | 默认返回技能数 |
| `CACHE_TTL_SECONDS` | 3600 | 缓存过期时间 |
