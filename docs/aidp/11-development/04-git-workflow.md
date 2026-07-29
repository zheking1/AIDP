# Git 工作流

## 仓库信息

| 属性 | 值 |
|------|-----|
| 远程仓库 | `https://github.com/zheking1/AIDP` |
| 部署目标 | NAS: `192.168.0.100` |
| SSH 密钥 | `~/.ssh/nas_temp` |

## 提交流程

### 分支策略

项目使用标准 Git 工作流:
- `main` / `master` 分支为稳定版本
- 功能开发在分支上进行
- 不强制特定的 Git Flow 命名约定

### Commit 规范

项目未强制规定 commit message 格式 (无 `commitlint` 或 husky 配置)。建议:
- 使用清晰的描述性提交信息
- 中文或英文均可

## 部署到 NAS 的完整流程

**源文件**: `.opencode/AGENTS.md:84-87`

```
1. 打包源码:
   tar czf deploy.tar.gz <changed_files>

2. 上传到 NAS:
   scp deploy.tar.gz root@192.168.0.100:/opt/aidp/

3. 重新构建 Docker 镜像:
   ssh -i ~/.ssh/nas_temp root@192.168.0.100 \
     "cd /opt/aidp && docker build --no-cache"

4. 重启容器:
   ssh -i ~/.ssh/nas_temp root@192.168.0.100 \
     "docker restart <container_name>"
```

### NAS 信息

| 属性 | 值 |
|------|-----|
| NAS IP | `192.168.0.100` |
| SSH 用户 | `root` |
| SSH 密钥 | `~/.ssh/nas_temp` |
| 部署路径 | `/opt/aidp/` |

### 服务容器名映射

| 服务 | 容器名 | 部署方式 |
|------|--------|---------|
| controller | `aidp-controller` | Docker |
| sandbox-tool | `aidp-sandbox` | Docker |
| quality-tool | `aidp-quality` | Docker |
| skill-router | 无 (host network) | 独立部署 |
| knowledge-tool | 无 (host network) | 独立部署 |
| memory-tool | 无 (host network) | 独立部署 |
| code-index | 无 (host network) | 独立部署 |
| doc-index | 无 (host network) | 独立部署 |
| context-optimizer | 无 (host network) | 独立部署 |
| asset-tool | 无 (host network) | 独立部署 |
| evolution-engine | 无 (host network) | 独立部署 |
| project-importer | 无 (host network) | 独立部署 |
| file-watcher | 无 (host network) | 独立部署 |

## 部署脚本

**源文件**: `deploy/deploy-nas.ps1`

项目提供 PowerShell 自动化部署脚本，执行完整部署流程。

### Docker Compose 服务分组

顶层 `docker-compose.yml` 仅编排 3 个核心服务:

| 服务 | Docker 容器 |
|------|------------|
| controller | ✅ Docker |
| sandbox-tool | ✅ Docker |
| quality-tool | ✅ Docker |

其他服务使用各自独立的 `tools/{tool_name}/docker-compose.yml` 或直接 host network 运行。

### Docker Compose 命令

```bash
# 启动核心服务
docker compose up -d

# 启动 skill-router (独立)
cd tools/skill-router && docker compose up -d

# 启动 knowledge-tool (独立)
cd tools/knowledge-tool && docker compose up -d

# 启动 memory-tool (独立)
cd tools/memory-tool && docker compose up -d

# 启动 code-index (独立)
cd tools/code-index && docker compose up -d

# 构建所有镜像
docker compose build

# 构建特定工具
cd tools/knowledge-tool && docker build -t aidp/knowledge-tool:0.1.0 .
```

## 网络拓扑

所有 docker-compose 服务使用 `network_mode: host`:

```
宿主机 (NAS: 192.168.0.100)
├── Docker 容器
│   ├── aidp-controller  (:8883)
│   ├── aidp-sandbox     (:18083)
│   └── aidp-quality     (:18084)
├── Host Network 进程
│   ├── skill-router     (:8788)
│   ├── knowledge-tool   (:18081)
│   ├── asset-tool        (:18082)
│   ├── memory-tool       (:18085)
│   ├── code-index        (:18086)
│   ├── doc-index         (:18087)
│   ├── context-optimizer (:18088)
│   ├── evolution-engine  (:18089)
│   ├── project-importer  (:18090)
│   └── file-watcher      (:18091)
└── 基础设施
    ├── PostgreSQL       (:5432)
    └── Redis            (:6379)
```

服务间通信使用 `127.0.0.1:<port>`，无需 Docker 内部 DNS 解析。

## 本地开发工作流

### 推荐步骤

```
1. 修改代码 → 本地验证
2. git add & git commit
3. git push (可选: 先推送到 GitHub)
4. 部署到 NAS:
   - 方式 A: powershell deploy/deploy-nas.ps1 (全量)
   - 方式 B: 手动 tar + scp + docker build + docker restart
```

### 代码审查

```
git log --oneline      # 查看最近提交
git diff main          # 查看与主分支差异
git status             # 查看当前状态
```

## 注意事项

1. **镜像构建**: 使用 `--no-cache` 确保完整重建，避免旧层缓存
2. **SSH 密钥权限**: 确保 `~/.ssh/nas_temp` 权限正确 (600)
3. **多服务部署**: 不是所有服务都容器化；host network 服务需手动在 NAS 上管理
4. **配置同步**: 部署后确保 `.env` 文件在目标环境中的配置正确
5. **数据库迁移**: 需要时手动执行 `init_db.py` 或在启动时通过 `lifespan` 自动初始化