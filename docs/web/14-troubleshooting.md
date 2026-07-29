# 故障排查指南

## 1. 常见问题

### 1.1 Controller 无法启动

**症状**: 容器启动后立即退出

**排查步骤**:
```bash
# 查看容器日志
docker logs aidp-controller

# 常见错误
# 1. 端口被占用
docker ps | grep 8883
netstat -tlnp | grep 8883

# 2. 数据库连接失败
docker exec aidp-controller python -c "import asyncpg; print('asyncpg ok')"

# 3. 环境变量缺失
docker inspect aidp-controller | grep -A 5 Environment
```

**解决方案**:
| 原因 | 解决方案 |
|------|---------|
| 端口占用 | 停止占用进程或修改端口 |
| 数据库不可用 | 启动 PostgreSQL 容器 |
| 环境变量缺失 | 检查 `.env` 文件 |

### 1.2 数据库连接失败

**症状**: API 返回 500 错误，日志显示 `connection refused`

**排查步骤**:
```bash
# 检查 PostgreSQL 容器
docker ps | grep postgres

# 检查数据库连接
docker exec novel-postgres psql -U novel_os -d novel_os -c "SELECT 1"

# 检查 DATABASE_URL
echo $DATABASE_URL
```

**解决方案**:
```bash
# 启动 PostgreSQL
docker start novel-postgres

# 重建数据库
docker exec novel-postgres psql -U novel_os -d novel_os -f /docker-entrypoint-initdb.d/init.sql
```

### 1.3 工具服务不可用

**症状**: MCP 调用返回 `TOOL_UNAVAILABLE`

**排查步骤**:
```bash
# 检查工具服务状态
curl http://localhost:18083/health
curl http://localhost:18081/health

# 检查工具注册
curl http://localhost:8883/api/tools | jq .

# 检查工具健康状态
curl http://localhost:8883/api/tools/health/all
```

**解决方案**:
```bash
# 重启工具服务
docker restart aidp-sandbox-tool

# 重新注册工具
curl -X POST http://localhost:8883/api/tools \
  -H "Content-Type: application/json" \
  -d '{"name": "sandbox-tool", "endpoint": "http://127.0.0.1:18083"}'
```

### 1.4 MCP 调用失败

**症状**: AI 客户端调用工具返回错误

**排查步骤**:
```bash
# 检查 MCP 端点
curl -X POST http://localhost:8883/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# 检查会话状态（MCP 会话在内存中，无法直接查看）
# 尝试重新调用 aidp_context
```

**常见错误**:
| 错误 | 原因 | 解决方案 |
|------|------|---------|
| CONTEXT_REQUIRED | 未调用 aidp_context | 先调用 aidp_context |
| SESSION_EXPIRED | 会话超时 | 重新建立连接 |
| TOOL_NOT_FOUND | 工具未注册 | 注册工具 |

### 1.5 Web UI 无法加载

**症状**: 浏览器显示空白或错误页面

**排查步骤**:
```bash
# 检查 Controller 是否运行
curl http://localhost:8883/health

# 检查静态文件
curl http://localhost:8883/static/css/app.css

# 检查模板文件
docker exec aidp-controller ls -la /app/app/web/templates/
```

**解决方案**:
| 原因 | 解决方案 |
|------|---------|
| Controller 未运行 | 启动容器 |
| 模板文件缺失 | 重新构建镜像 |
| 静态文件缺失 | 检查 Dockerfile COPY 指令 |

### 1.6 数据丢失

**症状**: 重启容器后数据消失

**排查步骤**:
```bash
# 检查 volume 挂载
docker inspect aidp-controller | grep -A 5 Mounts

# 检查数据目录
ls -la /home/docker/AI-Code/controller/data/
```

**解决方案**:
```bash
# 确保使用 volume 挂载
docker run -d \
  --name aidp-controller \
  -v /home/docker/AI-Code/controller/data:/app/data \
  ...

# 检查备份
ls -la /home/docker/AI-Code/backups/
```

## 2. 性能问题

### 2.1 API 响应慢

**排查步骤**:
```bash
# 检查数据库查询时间
docker exec aidp-controller python -c "
import time
from app.db.database import engine
import asyncio

async def test():
    start = time.time()
    async with engine.connect() as conn:
        await conn.execute('SELECT 1')
    print(f'Query time: {time.time() - start:.3f}s')

asyncio.run(test())
"

# 检查数据库连接池
docker exec aidp-controller python -c "
from app.db.database import engine
print(f'Pool size: {engine.pool.size()}')
print(f'Checked out: {engine.pool.checkedout()}')
"
```

**解决方案**:
| 原因 | 解决方案 |
|------|---------|
| 数据库慢 | 优化查询，添加索引 |
| 连接池耗尽 | 增加 pool_size |
| 内存不足 | 增加容器内存限制 |

### 2.2 MCP 上下文管道慢

**排查步骤**:
```bash
# 检查各阶段耗时
# Stage 1: 意图分析（skill-router）
curl http://localhost:8788/health

# Stage 2: 知识检索（并行）
curl http://localhost:18081/health
curl http://localhost:18085/health
```

**解决方案**:
| 原因 | 解决方案 |
|------|---------|
| skill-router 慢 | 检查 skill-router 服务状态 |
| 知识检索慢 | 优化向量索引 |
| 网络延迟 | 使用 localhost 通信 |

## 3. 开发问题

### 3.1 模块未加载

**症状**: 新添加的模块 API 返回 404

**排查步骤**:
```bash
# 检查模块注册
docker exec aidp-controller python -c "
from app.modules import init_all_modules
from app.core.module_registry import _registered_modules
print('Registered modules:', list(_registered_modules.keys()))
"

# 检查路由注册
curl http://localhost:8883/openapi.json | jq '.paths | keys'
```

**解决方案**:
```python
# 确保模块在 __init__.py 中导入
# apps/controller/app/modules/__init__.py
from app.modules.my_module import MyModule
```

### 3.2 菜单项不显示

**症状**: 侧边栏不显示新添加的菜单项

**排查步骤**:
```bash
# 检查菜单配置
docker exec aidp-controller cat /app/app/config/menu.yaml

# 检查菜单 API
curl http://localhost:8883/api/menu | jq .
```

**解决方案**:
```yaml
# 确保菜单配置格式正确
groups:
  - group: "my-module"
    title: "我的模块"
    icon: "fas fa-cube"
    order: 50
    items:
      - id: "my-item"
        label: "我的项目"
        icon: "fas fa-list"
        route: "/my-module/items"
```

### 3.3 权限检查失败

**症状**: API 返回 403 Forbidden

**排查步骤**:
```bash
# 检查用户角色
curl http://localhost:8883/api/auth/me

# 检查权限配置
docker exec aidp-controller cat /app/app/config/permissions.yaml
```

**解决方案**:
```yaml
# 确保权限配置包含新模块
permissions:
  my_module:
    read:
      default_roles: [admin, editor, viewer]
    write:
      default_roles: [admin, editor]
```

## 4. Docker 问题

### 4.1 构建失败

**症状**: `docker build` 报错

**排查步骤**:
```bash
# 检查 Dockerfile
cat apps/controller/Dockerfile

# 检查依赖
cat apps/controller/requirements.txt
```

**常见错误**:
| 错误 | 原因 | 解决方案 |
|------|------|---------|
| pip install 失败 | 网络问题 | 使用镜像源 |
| COPY 失败 | 文件不存在 | 检查 .dockerignore |
| 端口冲突 | 端口已占用 | 修改 EXPOSE |

### 4.2 容器无法启动

**症状**: `docker start` 失败

**排查步骤**:
```bash
# 查看容器状态
docker ps -a | grep aidp-controller

# 查看容器日志
docker logs aidp-controller

# 检查容器配置
docker inspect aidp-controller
```

**解决方案**:
```bash
# 删除并重新创建容器
docker rm aidp-controller
docker run -d --name aidp-controller ...
```

## 5. 网络问题

### 5.1 服务间通信失败

**症状**: Controller 无法调用工具服务

**排查步骤**:
```bash
# 检查网络模式
docker inspect aidp-controller | grep NetworkMode

# 检查端口监听
netstat -tlnp | grep 18083

# 测试连接
curl http://localhost:18083/health
```

**解决方案**:
```bash
# 确保所有服务使用 host 网络模式
docker run --network host ...

# 或确保端口可达
curl http://127.0.0.1:18083/health
```

## 6. 日志分析

### 6.1 查看日志

```bash
# 实时日志
docker logs -f aidp-controller

# 最近 100 行
docker logs --tail 100 aidp-controller

# 按时间筛选
docker logs --since 2026-07-23T10:00:00 aidp-controller
```

### 6.2 日志级别

```python
# 在代码中添加日志
import logging
logger = logging.getLogger(__name__)

logger.info("操作成功")
logger.warning("警告信息")
logger.error("错误信息", exc_info=True)
```

## 7. 关键文件索引

| 文件 | 用途 |
|------|------|
| `deploy/health-monitor.sh` | 健康监控脚本 |
| `deploy/backup-db.sh` | 数据库备份脚本 |
| `apps/controller/app/main.py` | 应用入口和错误处理 |
| `apps/controller/app/core/auth.py` | 认证和 session 管理 |
| `apps/controller/app/services/tool_registry.py` | 工具注册表 |
