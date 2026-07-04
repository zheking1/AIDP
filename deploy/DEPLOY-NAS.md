# AIDP 部署说明

## 已部署的服务

| 服务 | 端口 | 说明 |
|------|------|------|
| knowledge-tool | 18081 | 文档知识库 |
| asset-tool | 18082 | 代码资产管理 |
| sandbox-tool | 18083 | 代码执行沙箱 |
| quality-tool | 18084 | 代码质量检查 |
| memory-tool | 18085 | 项目记忆存储 |
| controller | 8883 | 工具控制器 |
| SkillRouter | 8788 | 核心路由引擎 |

## Web UI

- Controller 管理界面：`http://192.168.0.100:8883/`
- Controller 调用日志：`http://192.168.0.100:8883/logs`
- SkillRouter 管理界面：`http://192.168.0.100:8788/`

## 快速命令

```bash
# 健康检查
/home/docker/AI-Code/health-monitor.sh

# 手动备份数据库
/home/docker/AI-Code/backup-db.sh

# 设置 GitHub Token（提升 API 限额到 5000/hr）
/home/docker/AI-Code/set-github-token.sh YOUR_TOKEN

# 查看日志
docker logs <container-name>
docker logs -f <container-name>  # 实时查看
```

## GitHub Token 配置

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 选择权限：`repo`（私有仓库）或 `public_repo`（仅公开仓库）
4. 复制 token
5. 运行：
   ```bash
   /home/docker/AI-Code/set-github-token.sh ghp_xxxxxxxxxxxx
   ```

## 定时任务

- 每 5 分钟：健康检查
- 每 10 分钟：告警检查
- 每天凌晨 2 点：数据库备份

## 日志位置

- 健康日志：`/home/docker/AI-Code/logs/health.log`
- 告警日志：`/home/docker/AI-Code/logs/alerts.log`
- 备份日志：`/home/docker/AI-Code/logs/backup.log`
- 定时任务日志：`/home/docker/AI-Code/logs/health-cron.log`

## 容器管理

```bash
# 查看所有 AIDP 容器
docker ps -a | grep -E '(knowledge|asset|sandbox|quality|memory|controller|skillrouter)'

# 重启单个容器
docker restart <container-name>

# 查看容器日志
docker logs <container-name>

# 停止容器
docker stop <container-name>

# 启动容器
docker start <container-name>
```

## 端到端演示

```bash
/home/docker/AI-Code/demo-e2e.sh
```

## 测试

```bash
# 清理测试数据（避免唯一性冲突）
/home/docker/AI-Code/clear-test-data.sh --confirm

# 运行测试（自动清理 + 健康检查）
/home/docker/AI-Code/run-tests.sh
```

## 数据库连接

- 主机：127.0.0.1:5432
- 数据库：novel_os
- 用户：novel_os
