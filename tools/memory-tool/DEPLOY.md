# Memory Tool 部署说明

## 部署前准备

确保可以通过 SSH 连接到 NAS:
```bash
ssh -i ~/.ssh/nas_temp admin@192.168.0.100
```

## 部署步骤

### 方法 1: 手动部署 (推荐)

1. **复制文件到 NAS**

在本地 PowerShell 执行:
```powershell
# 压缩项目文件
Compress-Archive -Path "app", "requirements.txt", "Dockerfile", "docker-compose.yml" -DestinationPath "memory-tool-deploy.zip" -Force

# 复制到 NAS
scp -i $env:USERPROFILE\.ssh\nas_temp memory-tool-deploy.zip admin@192.168.0.100:/volume1/docker/memory-tool/
```

2. **在 NAS 上解压并部署**

SSH 到 NAS 后执行:
```bash
cd /volume1/docker/memory-tool

# 备份现有数据
cp -r data data.backup.$(date +%Y%m%d)

# 解压新版本
unzip -o memory-tool-deploy.zip

# 重建并启动容器
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 查看日志
docker-compose logs -f
```

3. **验证部署**

```bash
# 健康检查
curl http://localhost:18085/health

# 查看容器状态
docker-compose ps
```

### 方法 2: 直接同步 (需要配置好 rsync)

```bash
# 从本地直接同步到 NAS
rsync -avz --exclude='data' --exclude='__pycache__' \
  -e "ssh -i ~/.ssh/nas_temp" \
  ./ admin@192.168.0.100:/volume1/docker/memory-tool/
```

## 部署后验证

访问以下 URL 验证功能:

- **仪表盘**: http://192.168.0.100:18085/
- **记忆列表**: http://192.168.0.100:18085/memories
- **记忆图谱**: http://192.168.0.100:18085/memories/graph
- **上下文包**: http://192.168.0.100:18085/context
- **审核队列**: http://192.168.0.100:18085/review

## 新增功能清单

### ✅ Web UI 页面
1. **仪表盘** (`/`) - 统计概览、最近记忆、快速操作
2. **记忆列表** (`/memories`) - 搜索筛选、分页、新建
3. **记忆详情** (`/memories/{id}`) - 完整内容、元数据、相关记忆
4. **记忆编辑** (`/memories/{id}/edit`) - 表单编辑
5. **图谱可视化** (`/memories/graph`) - D3.js 力导向图
6. **上下文包** (`/context`) - 构建和预览上下文
7. **审核队列** (`/review`) - AI生成记忆的审核

### ✅ UI/UX 优化
- Toast 通知系统
- 确认对话框
- API 错误处理
- 分类颜色和图标
- 响应式布局
- 加载状态指示器

### ✅ 测试数据
- 27 条测试记忆
- 跨分类关系连接
- 上下文包示例

## 故障排查

### 容器无法启动
```bash
# 查看详细日志
docker-compose logs --tail=100

# 检查端口占用
netstat -tlnp | grep 18085

# 重启容器
docker-compose restart
```

### 数据库连接问题
```bash
# 检查 PostgreSQL 容器
docker ps | grep postgres

# 检查网络连接
docker network ls
docker network inspect memory-tool_default
```

### 静态文件 404
确保 `app/web/static` 目录已正确复制到容器内。

## 回滚方案

如需回滚:
```bash
cd /volume1/docker/memory-tool

# 停止容器
docker-compose down

# 恢复备份
cp -r data.backup.YYYYMMDD data

# 重新部署旧版本
# (需要手动替换为旧版本文件)

docker-compose up -d
```

## 下一步建议

1. **配置 HTTPS** - 使用 Traefik 或 Nginx 反向代理
2. **设置自动备份** - 定时备份 PostgreSQL 数据
3. **添加监控** - 集成 Prometheus/Grafana
4. **性能优化** - 根据使用情况调整缓存策略
