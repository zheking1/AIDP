# 系统级需求文档

## 1. 功能需求

### 1.1 核心功能

| 模块 | 功能 | 优先级 | 状态 |
|------|------|--------|------|
| Web UI | 工作台标签页系统 | P0 | ✅ 已实现 |
| Web UI | 动态菜单系统 | P0 | ✅ 已实现 |
| Web UI | 项目切换器 | P0 | ✅ 已实现 |
| 认证 | Cookie-based session | P0 | ✅ 已实现 |
| 认证 | 角色权限控制 | P0 | ✅ 已实现 |
| MCP | 工具调用接口 | P0 | ✅ 已实现 |
| MCP | 5 阶段上下文管道 | P0 | ✅ 已实现 |
| 工具 | 代码沙箱 | P0 | ✅ 已实现 |
| 工具 | 知识库管理 | P0 | ✅ 已实现 |
| 工具 | 记忆系统 | P1 | ✅ 已实现 |
| 工具 | 质量检查 | P1 | ✅ 已实现 |
| 工具 | 资产库 | P1 | ✅ 已实现 |
| 工具 | 技能路由 | P1 | ✅ 已实现 |
| 工具 | Agent 编排 | P2 | ✅ 已实现 |
| 工具 | 工作流引擎 | P2 | ✅ 已实现 |
| 项目 | 项目管理 | P0 | ✅ 已实现 |
| 项目 | 成员管理 | P1 | ✅ 已实现 |
| 项目 | 数据隔离 | P0 | ✅ 已实现 |

### 1.2 用户角色

| 角色 | 权限 | 说明 |
|------|------|------|
| super_admin | 所有权限 | 超级管理员 |
| admin | 除系统配置外的所有权限 | 管理员 |
| developer | 读写知识库、记忆、技能、资产 | 开发者 |
| user | 只读 + 创建个人资源 | 普通用户 |
| readonly | 只读 | 只读用户 |

### 1.3 数据隔离规则

```
项目级数据:
  owner_id == user_id        → 完全访问
  user is member             → 根据角色权限
  visibility == "public"     → 只读访问

个人级数据:
  scope == "personal"        → 仅自己可见
  scope == "global"          → 所有人可见
```

## 2. 非功能需求

### 2.1 性能需求

| 指标 | 目标 | 说明 |
|------|------|------|
| API 响应时间 | < 200ms | 95th percentile |
| MCP 上下文管道 | < 5s | 5 阶段总耗时 |
| 工具调用延迟 | < 1s | 单次工具调用 |
| 并发用户数 | 10+ | 同时在线用户 |
| 数据库连接池 | 5-15 | pool_size + max_overflow |

### 2.2 可用性需求

| 指标 | 目标 | 说明 |
|------|------|------|
| 系统可用性 | 99.9% | 月度停机时间 < 43 分钟 |
| 故障恢复 | < 5 分钟 | 自动重启 + 手动干预 |
| 数据备份 | 每天 | 自动 pg_dump |
| 数据保留 | 7 天 | 备份文件保留天数 |

### 2.3 安全需求

| 需求 | 实现方式 |
|------|---------|
| 认证 | Cookie-based session + bcrypt 密码哈希 |
| 授权 | RBAC 角色权限 + YAML 配置 |
| 数据隔离 | 项目级 owner/member/visibility 三层过滤 |
| 审计 | 所有操作记录到 audit_logs 表 |
| HTTPS | 通过反向代理（nginx/caddy） |
| 密钥管理 | 环境变量，不硬编码 |

### 2.4 可维护性需求

| 需求 | 实现方式 |
|------|---------|
| 模块化 | 9 个独立模块，BaseModule 抽象类 |
| 可配置 | YAML 菜单 + 权限配置 |
| 可扩展 | 新工具通过 REST API 注册 |
| 可监控 | 健康检查端点 + 定时监控脚本 |
| 可备份 | 自动数据库备份 + 数据目录 |

## 3. 技术约束

### 3.1 技术栈约束

| 层 | 技术 | 版本要求 |
|----|------|---------|
| 后端 | Python | 3.13+ |
| Web 框架 | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ |
| 数据库 | PostgreSQL | 14+ |
| 缓存 | Redis | 7+ |
| 前端 | Alpine.js | 3.x |
| CSS | Tailwind CSS | 4.x (CDN) |
| 容器 | Docker | 24+ |
| MCP | FastMCP | 3.4+ |

### 3.2 部署约束

| 约束 | 说明 |
|------|------|
| 网络模式 | 所有服务使用 `network_mode: host` |
| 数据持久化 | 所有数据目录 bind-mount 到 NAS |
| 数据库 | 所有服务共享同一个 PostgreSQL 实例 |
| 端口分配 | Controller:8883, 工具:18081-18085, Router:8788 |

### 3.3 兼容性约束

| 约束 | 说明 |
|------|------|
| 浏览器 | Chrome 90+, Firefox 88+, Safari 14+ |
| MCP 客户端 | Claude Desktop, Cursor, VS Code |
| API 版本 | REST API v1 (当前) |
| 数据库迁移 | SQLAlchemy create_all + 手动迁移 |

## 4. 接口需求

### 4.1 外部接口

| 接口 | 协议 | 用途 |
|------|------|------|
| MCP | JSON-RPC over HTTP | AI 客户端调用工具 |
| REST API | HTTP/JSON | Web UI 和外部集成 |
| WebSocket | ws:// | 实时日志流 |

### 4.2 内部接口

| 接口 | 协议 | 用途 |
|------|------|------|
| 工具调用 | HTTP POST /tool/invoke | Controller → 工具服务 |
| 健康检查 | HTTP GET /health | Controller → 工具服务 |
| 能力同步 | HTTP GET /tool/capabilities | Controller → 工具服务 |

## 5. 数据需求

### 5.1 数据模型

| 实体 | 存储 | 说明 |
|------|------|------|
| User | PostgreSQL | 用户账户 |
| Session | 内存/Redis | Web 登录会话 |
| MCP Session | 内存 | MCP 调用会话 |
| Project | PostgreSQL | 项目定义 |
| KnowledgeBase | PostgreSQL | 知识库 |
| KnowledgeDocument | PostgreSQL | 知识文档 |
| DocumentChunk | PostgreSQL (pgvector) | 向量化文档块 |
| MemoryEntry | PostgreSQL | 记忆条目 |
| Skill | PostgreSQL | 技能定义 |
| Asset | PostgreSQL | 代码资产 |
| ToolRegistry | PostgreSQL | 工具注册表 |
| ToolInvocation | PostgreSQL | 调用日志 |
| AuditLog | PostgreSQL | 审计日志 |

### 5.2 数据量预估

| 数据 | 预估量 | 增长速度 |
|------|--------|---------|
| 用户 | 10-50 | 低 |
| 项目 | 10-100 | 中 |
| 知识文档 | 100-1000 | 高 |
| 文档块 | 10K-100K | 高 |
| 记忆条目 | 1K-10K | 中 |
| 工具调用日志 | 10K-100K | 高 |
| 审计日志 | 10K-100K | 高 |
