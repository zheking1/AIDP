# AIDP 快速参考

## 常用命令

### 部署

```bash
# 全量部署到 NAS
powershell deploy/deploy-nas.ps1

# 仅启动核心服务 (controller + sandbox + quality)
docker compose up -d

# 启动 skill-router (独立部署)
cd tools/skill-router
cp .env.example .env
docker compose up -d

# 启动 knowledge-tool
cd tools/knowledge-tool
docker compose up -d

# 启动 memory-tool
cd tools/memory-tool
docker compose up -d

# 启动 code-index
cd tools/code-index
docker compose up -d
```

### 服务管理

```bash
# 查看所有容器状态
docker ps --filter "name=aidp"

# 查看 controller 日志
docker logs -f aidp-controller

# 重启 controller
docker restart aidp-controller

# 停止所有 AIDP 服务
docker compose down

# 查看 docker compose 服务状态
docker compose ps
```

### 健康检查

```bash
# Controller 健康检查
curl http://127.0.0.1:8883/health

# 通过 Controller 检查所有工具健康
curl -X POST http://127.0.0.1:8883/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"check_tool_health","arguments":{}}}'

# 快速检查所有端口
for port in 8883 8788 18081 18082 18083 18084 18085 18086 18087 18088 18089 18090 18091; do
  curl -s http://127.0.0.1:$port/health | jq .
done
```

### API 调用

```bash
# 登录获取 session
curl -X POST http://127.0.0.1:8883/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  -c cookies.txt

# 查看已注册工具列表
curl http://127.0.0.1:8883/api/tools -b cookies.txt | jq .

# 代理调用 knowledge-tool 搜索
curl http://127.0.0.1:8883/api/proxy/knowledge-tool/api/search \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"query":"API设计规范","top_k":5}'

# 直接调用 memory-tool 搜索记忆
curl http://127.0.0.1:18085/api/memory/search \
  -H "Content-Type: application/json" \
  -d '{"project":"aidp","query":"登录问题"}'

# 直接调用 sandbox-tool 执行代码
curl -X POST http://127.0.0.1:18083/tool/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability":"sandbox.execute","input":{"code":"print(1+1)","language":"python"}}'

# 直接调用 quality-tool 检查代码
curl -X POST http://127.0.0.1:18084/tool/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability":"quality.check","input":{"code":"x=1","filename":"test.py"}}'
```

### 数据库

```bash
# 连接 PostgreSQL
psql -h 127.0.0.1 -U novel_os -d aidp

# 查看工具注册表
SELECT name, endpoint, status, updated_at FROM tool_registry;

# 查看项目列表
SELECT id, name, status, created_at FROM aidp_projects;

# 查看用户列表
SELECT id, username, nickname, role FROM users;

# 查看 Agent 指令
SELECT id, project_id, agent_type, role FROM agent_instructions;
```

### Docker 镜像管理

```bash
# 构建所有镜像
docker compose build

# 构建特定工具镜像
cd tools/knowledge-tool
docker build -t aidp/knowledge-tool:0.1.0 .

# 清理未使用的镜像
docker image prune -a
```

## MCP 工具调用顺序

AI Agent 必须遵循以下调用顺序:

```
1. aidp_context(project_name, task)       # 必须第一步，加载上下文
2. invoke_tool_mcp(tool_name, capability, arguments)  # 执行具体操作
3. invoke_tool_mcp("memory-tool", "memory.create", {...})  # 可选: 归档经验
```

**重要**: 未先调用 `aidp_context` 而直接调用 `invoke_tool_mcp` 会返回错误:
```json
{
  "success": false,
  "error": {
    "code": "CONTEXT_REQUIRED",
    "message": "必须先调用 aidp_context 加载上下文"
  }
}
```

## 常用 MCP 调用示例

```python
# 加载上下文 (必须第一步)
aidp_context(project_name="aidp", task="修复登录页cookie问题")

# 代码执行
invoke_tool_mcp("sandbox-tool", "sandbox.execute",
  '{"code": "print(1)", "language": "python"}')

# 质量检查
invoke_tool_mcp("quality-tool", "quality.check",
  '{"code": "x=1", "filename": "test.py"}')

# 检索记忆
invoke_tool_mcp("memory-tool", "memory.search",
  '{"project": "aidp", "query": "登录问题"}')

# 创建记忆
invoke_tool_mcp("memory-tool", "memory.create",
  '{"project": "aidp", "category": "bugfix", "title": "cookie修复", "content": "详细描述"}')

# 检索知识
invoke_tool_mcp("knowledge-tool", "knowledge.search",
  '{"query": "API设计规范", "top_k": 3}')

# 技能路由
invoke_tool_mcp("skill-router", "resolve_task",
  '{"task": "修复登录bug", "api_key": "sk-xxx"}')
```

## 项目导入

```bash
# 快速扫描项目
curl "http://127.0.0.1:18090/api/onboarding/scan?path=/path/to/project"

# 一键导入项目
curl -X POST http://127.0.0.1:18090/api/onboarding/import \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/path/to/project",
    "name": "my-project",
    "type": "python",
    "auto_import_docs": true
  }'
```

## 环境变量速查

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://novel_os:CHANGE_ME@127.0.0.1:5432/aidp` | 数据库连接 |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis 连接 |
| `ADMIN_USERNAME` | `admin` | 管理员用户名 |
| `ADMIN_PASSWORD` | `CHANGE_ME` | 管理员密码 |
| `CONTROLLER_SESSION_KEY` | `change-me-in-production` | 会话密钥 |
| `LLM_ENDPOINT` | `http://localhost:8000/v1` | LLM API 端点 |
| `LLM_API_KEY` | `sk-xxx` | LLM API Key |
| `LLM_MODEL` | `deepseek-v4-flash-free` | 默认 LLM 模型 |
| `EMBEDDING_ENDPOINT` | `http://localhost:8000/v1` | Embedding API 端点 |
| `EMBEDDING_API_KEY` | `sk-xxx` | Embedding API Key |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 默认 Embedding 模型 |

## 关键配置值

| 配置项 | 默认值 | 位置 |
|--------|--------|------|
| 会话超时 | 30 分钟 | `apps/controller/app/mcp/session_manager.py:111` |
| 上下文缓存 TTL | 300 秒 | `apps/controller/app/services/context_cache.py` |
| Token 预算上限 | 8000 | `apps/controller/app/services/context_assembly.py` |
| 工具调用重试 | 3 次 (指数退避) | `apps/controller/app/services/tool_retry.py` |
| 工具调用超时 | 30 秒 | `apps/controller/app/_config.py:17` |
| 文档分块大小 | 800 | `tools/knowledge-tool/app/config.py:30` |
| 分块重叠量 | 120 | `tools/knowledge-tool/app/config.py:31` |
| 检索 Top-K | 8 (knowledge) / 5 (skill-router) | 各服务 config |
| 代码执行超时 | 30 秒 | `tools/sandbox-tool/app/config.py:17` |
| 代码执行输出上限 | 10240 字节 | `tools/sandbox-tool/app/config.py:18` |
| Context Optimizer Token 预算 | 8000 (min=1000, max=32000) | `tools/context-optimizer/app/config.py:13-15` |
| File Watcher 防抖 | 1.0 秒 | `tools/file-watcher/app/config.py:11` |

## 文件路径速查

| 文件 | 用途 |
|------|------|
| `docker-compose.yml` | 顶层编排 (controller + sandbox + quality) |
| `deploy/deploy-nas.ps1` | NAS 全量部署脚本 |
| `.env.example` | 环境变量模板 |
| `apps/controller/app/mcp/server.py` | MCP Server 实现 |
| `apps/controller/app/services/context_pipeline.py` | 5 阶段上下文管线 |
| `apps/controller/app/services/tool_invoker.py` | 工具调用器 |
| `apps/controller/app/services/tool_registry.py` | 工具注册服务 |
| `apps/controller/WEB_UI_ARCHITECTURE.md` | Web UI 架构文档 |
| `tools/*/app/main.py` | 各工具入口 |
| `tools/*/app/config.py` | 各工具配置 |
| `tools/*/tool.yaml` | 各工具能力声明 |
| `tools/*/Dockerfile` | 各工具容器构建 |
| `tools/*/requirements.txt` | 各工具 Python 依赖 |

## 故障排查

```bash
# 1. 检查 PostgreSQL 连接
psql -h 127.0.0.1 -U novel_os -d aidp -c "SELECT 1"

# 2. 检查 Redis 连接
redis-cli -h 127.0.0.1 ping

# 3. 检查 pgvector 扩展
psql -h 127.0.0.1 -U novel_os -d aidp -c "SELECT * FROM pg_extension WHERE extname='vector'"

# 4. 查看 controller 完整日志
docker logs aidp-controller 2>&1 | tail -100

# 5. 重建并重启服务
docker compose down
docker compose build --no-cache
docker compose up -d
```