# AIDP 综合开发计划

---

## 项目概述

AIDP (AI DevOps Platform) 是一个完整的 AI 编码基础设施，包含 11 个工具。当前已完成大部分核心功能，需要补充数据归属、权限控制、项目协作、环境配置、审核流程等能力。

**技术栈**: Python + FastAPI + FastMCP
**部署环境**: NAS (192.168.0.100)
**数据库**: PostgreSQL 16 + Redis 7

---

## 已完成模块

| 模块 | 状态 | 说明 |
|------|------|------|
| SkillRouter | ✅ | 路由引擎，端口 8788 |
| Knowledge Tool | ✅ | 知识库，端口 18081 |
| Asset Tool | ✅ | 资产管理，端口 18082 |
| Sandbox Tool | ✅ | 代码沙箱，端口 18083 |
| Quality Tool | ✅ | 质量检查，端口 18084 |
| Memory Tool | ✅ | 记忆工具，端口 18085 |
| Controller | ✅ | 控制器，端口 8883 |
| Web UI | ✅ | 所有工具的 Web 界面 |
| i18n | ✅ | 中英文切换 |
| MCP 集成 | ✅ | Streamable-HTTP |

---

## 待开发模块

### Phase 1: 数据归属和权限（P0）

**周期**: 1 周（5 天）

**目标**: 实现用户认证、数据归属、基础权限控制

#### 任务清单

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 创建 users 表 | P0 | 2h | - |
| 实现用户登录/登出 API | P0 | 4h | users 表 |
| 实现 session 中间件 | P0 | 4h | 登录 API |
| 创建项目表 (projects) | P0 | 2h | - |
| 创建项目成员表 (project_members) | P0 | 2h | - |
| 创建项目配置表 (project_configs) | P0 | 2h | - |
| 创建审核表 (review_queue) | P0 | 2h | - |
| 修改 documents 表增加归属字段 | P0 | 2h | - |
| 实现权限检查器 (PermissionChecker) | P0 | 4h | users 表 |
| 实现文档 API 权限过滤 | P0 | 4h | 权限检查器 |
| 修改 Web UI 支持登录 | P0 | 4h | 登录 API |
| 集成测试 | P0 | 4h | 所有任务 |

**验收标准**:
- [ ] 用户登录/登出工作
- [ ] 会话保持有效
- [ ] 文档按归属过滤
- [ ] 权限检查有效

**数据库迁移**:

```sql
-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 项目表
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT,
    owner_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 项目成员表
CREATE TABLE IF NOT EXISTS project_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    user_id INTEGER REFERENCES users(id),
    role TEXT NOT NULL DEFAULT 'member',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

-- 4. 项目配置表
CREATE TABLE IF NOT EXISTS project_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    env_type TEXT NOT NULL,
    config_key TEXT NOT NULL,
    config_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, env_type, config_key)
);

-- 5. 审核表
CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    content TEXT,
    status TEXT DEFAULT 'pending',
    review_comment TEXT,
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. 修改文档表
ALTER TABLE documents ADD COLUMN owner_type TEXT DEFAULT 'personal';
ALTER TABLE documents ADD COLUMN owner_id INTEGER;

-- 7. 创建默认管理员
INSERT INTO users (username, password_hash, role)
VALUES ('admin', 'admin123_hash', 'admin');
```

---

### Phase 2: 项目协作（P1）

**周期**: 1 周（5 天）

**目标**: 实现项目创建、成员管理、项目权限

#### 任务清单

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 实现项目 CRUD API | P1 | 4h | 项目表 |
| 实现成员邀请/移除 API | P1 | 4h | 项目成员表 |
| 实现项目权限控制 | P1 | 4h | 权限检查器 |
| 创建项目 Web UI | P1 | 4h | 项目 API |
| 项目代码存储到 NAS | P1 | 4h | - |
| 集成测试 | P1 | 4h | 所有任务 |

**验收标准**:
- [ ] 项目创建/列表/详情工作
- [ ] 成员邀请/移除工作
- [ ] 项目权限有效
- [ ] 项目代码存储到 NAS

---

### Phase 3: 环境配置（P1）

**周期**: 0.5 周（2-3 天）

**目标**: 实现项目环境配置管理、Agent 自动获取配置

#### 任务清单

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 实现配置 CRUD API | P1 | 4h | 配置表 |
| 实现配置解析器 | P1 | 2h | 配置 API |
| 实现 Agent 自动获取配置 | P1 | 2h | 配置解析器 |
| 创建配置 Web UI | P1 | 4h | 配置 API |
| 集成测试 | P1 | 2h | 所有任务 |

**验收标准**:
- [ ] 配置 CRUD 工作
- [ ] Agent 自动获取配置
- [ ] 配置 Web UI 工作

---

### Phase 4: 审核流程（P2）

**周期**: 0.5 周（2-3 天）

**目标**: 实现用户提交修改审核流程

#### 任务清单

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 实现提交审核 API | P2 | 4h | 审核表 |
| 实现审核列表 API | P2 | 2h | 审核表 |
| 实现审核通过/拒绝 API | P2 | 4h | 审核表 |
| 创建审核 Web UI | P2 | 4h | 审核 API |
| 集成测试 | P2 | 2h | 所有任务 |

**验收标准**:
- [ ] 提交审核工作
- [ ] 审核列表有效
- [ ] 审核通过/拒绝工作
- [ ] 审核 Web UI 工作

---

## 技术实现细节

### 1. 数据归属模型

```
数据分类:
├── System (公共)
│   ├── 技术文档: Vue、Spring Boot 等
│   ├── 公共 Skills: 通用技能、规则
│   └── 权限: 所有人只读，管理员维护
│
├── Personal (个人)
│   ├── 个人文档: 用户自己添加的文档
│   ├── 个人 Skills: 用户自定义技能
│   └── 权限: 用户完全控制
│
└── Project (项目)
    ├── 项目文档: 项目专属文档
    ├── 项目 Skills: 项目专属技能
    ├── 项目 Memory: 项目经验
    ├── Code Index: 项目代码索引
    ├── 环境配置: 项目环境配置
    └── 权限: 项目成员可查看/编辑
```

### 2. 权限模型

```
角色:
├── Admin (管理员)
│   ├── 管理公共数据（创建/修改/删除）
│   ├── 审核用户提交
│   ├── 管理用户
│   └── 管理所有项目
│
├── User (普通用户)
│   ├── 查看公共数据
│   ├── 管理个人数据
│   ├── 提交修改到公共
│   └── 创建项目
│
└── Project Roles
    ├── Owner: 项目创建者，管理项目
    ├── Member: 项目成员，编辑项目
    └── Viewer: 项目访客，只读
```

### 3. 环境配置

```
配置分类:
├── dev (开发环境)
│   ├── database_url: jdbc:mysql://dev:3306/db
│   ├── redis_url: redis://dev:6379
│   └── api_url: http://dev:8080
│
├── test (测试环境)
│   ├── database_url: jdbc:mysql://test:3306/db
│   ├── redis_url: redis://test:6379
│   └── api_url: http://test:8080
│
└── prod (生产环境)
    ├── database_url: jdbc:mysql://prod:3306/db
    ├── redis_url: redis://prod:6379
    └── api_url: http://prod:8080
```

### 4. 项目代码存储

```
NAS 路径: /home/docker/AI-Code/projects/
├── project-1/
│   ├── .git/
│   ├── src/
│   ├── docs/
│   ├── tests/
│   └── configs/
│       ├── dev.json
│       ├── test.json
│       └── prod.json
│
└── shared/
    ├── base-images/
    └── templates/
```

### 5. 审核流程

```
审核流程:
1. 用户提交修改
   ├── 个人文档 → 公共文档
   ├── 个人 Skill → 公共 Skill
   └── 个人修改 → 公共修改
        ↓
2. 进入审核队列
   ├── 状态: pending
   ├── 提交者: user_id
   └── 内容: 修改内容
        ↓
3. 管理员审核
   ├── 通过: 状态 → approved
   └── 拒绝: 状态 → rejected
        ↓
4. 应用修改
   ├── 通过: 更新公共数据
   └── 拒绝: 通知用户
```

---

## API 汇总

### 认证 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 登录 |
| POST | /api/auth/logout | 登出 |
| GET | /api/auth/me | 获取当前用户 |

### 项目 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects | 创建项目 |
| GET | /api/projects | 获取项目列表 |
| GET | /api/projects/{id} | 获取项目详情 |
| PUT | /api/projects/{id} | 更新项目 |
| DELETE | /api/projects/{id} | 删除项目 |

### 项目成员 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/projects/{id}/members | 获取项目成员 |
| POST | /api/projects/{id}/members | 邀请成员 |
| DELETE | /api/projects/{id}/members/{user_id} | 移除成员 |

### 项目配置 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/projects/{id}/configs | 获取项目配置 |
| POST | /api/projects/{id}/configs | 设置项目配置 |
| GET | /api/projects/{id}/configs/{env} | 获取特定环境配置 |
| POST | /api/projects/{id}/configs/resolve | Agent 自动获取配置 |

### 文档 API（修改）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/documents | 获取文档列表（支持 owner_type 过滤） |
| POST | /api/documents | 创建文档（自动设置 owner） |
| PUT | /api/documents/{id} | 更新文档（检查权限） |
| DELETE | /api/documents/{id} | 删除文档（检查权限） |

### 审核 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/reviews | 提交审核 |
| GET | /api/reviews | 获取审核列表 |
| POST | /api/reviews/{id}/approve | 审核通过 |
| POST | /api/reviews/{id}/reject | 审核拒绝 |

---

## 文件变更清单

### 新建文件

| 文件 | 说明 |
|------|------|
| `apps/controller/app/models/user.py` | 用户模型 |
| `apps/controller/app/models/project.py` | 项目模型 |
| `apps/controller/app/models/member.py` | 项目成员模型 |
| `apps/controller/app/models/config.py` | 项目配置模型 |
| `apps/controller/app/models/review.py` | 审核模型 |
| `apps/controller/app/services/auth_service.py` | 认证服务 |
| `apps/controller/app/services/project_service.py` | 项目服务 |
| `apps/controller/app/services/permission_service.py` | 权限服务 |
| `apps/controller/app/services/config_service.py` | 配置服务 |
| `apps/controller/app/services/review_service.py` | 审核服务 |
| `apps/controller/app/api/auth.py` | 认证 API |
| `apps/controller/app/api/projects.py` | 项目 API |
| `apps/controller/app/api/configs.py` | 配置 API |
| `apps/controller/app/api/reviews.py` | 审核 API |
| `apps/controller/app/web/auth.py` | 认证中间件 |
| `apps/controller/app/web/templates/login.html` | 登录页面 |
| `apps/controller/app/web/templates/projects.html` | 项目列表 |
| `apps/controller/app/web/templates/project_detail.html` | 项目详情 |
| `apps/controller/app/web/templates/project_form.html` | 项目表单 |
| `apps/controller/app/web/templates/configs.html` | 配置管理 |
| `apps/controller/app/web/templates/reviews.html` | 审核列表 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `apps/controller/app/models/document.py` | 添加 owner_type, owner_id 字段 |
| `apps/controller/app/api/documents.py` | 添加权限过滤 |
| `apps/controller/app/web/routes.py` | 添加认证中间件 |
| `apps/controller/app/main.py` | 注册新路由 |
| `apps/controller/app/db/init_db.py` | 添加新表迁移 |
| `apps/controller/requirements.txt` | 添加依赖 |

---

## 部署计划

### 开发环境

```bash
# 本地开发
cd D:\Project\openCode\apps\controller
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8883
```

### 生产环境

```bash
# 构建镜像
cd D:\Project\openCode\apps\controller
docker build -t aidp-controller:latest .

# 推送到 NAS
docker save aidp-controller:latest | ssh root@192.168.0.100 docker load

# 部署到 NAS
ssh root@192.168.0.100 "cd /home/docker/AI-Code && docker-compose up -d controller"
```

### 数据库迁移

```bash
# 执行迁移
python -m app.db.init_db
```

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 数据库迁移失败 | 数据丢失 | 备份数据库后再迁移 |
| 权限检查性能 | 响应变慢 | 缓存权限数据 |
| 会话管理 | 登录失效 | 使用 JWT token |
| 并发冲突 | 数据不一致 | 使用乐观锁 |
| NAS 存储不足 | 无法存储 | 监控存储使用 |

---

## 测试计划

### 单元测试

- 认证服务测试
- 权限服务测试
- 项目服务测试
- 配置服务测试
- 审核服务测试

### 集成测试

- 完整登录流程测试
- 项目创建/编辑测试
- 成员邀请/移除测试
- 配置管理测试
- 审核流程测试

### 性能测试

- 权限检查性能测试
- 数据库查询性能测试
- API 响应时间测试

---

## 里程碑

| 里程碑 | 日期 | 交付物 |
|------|------|------|
| M1 | Phase 1 完成 | 用户认证、数据归属、权限控制 |
| M2 | Phase 2 完成 | 项目协作、成员管理 |
| M3 | Phase 3 完成 | 环境配置、Agent 集成 |
| M4 | Phase 4 完成 | 审核流程 |

---

## 附录

### A. 配置文件

```python
# app/config.py

class PermissionConfig:
    # 角色定义
    ROLES = ["admin", "user"]
    
    # 项目角色
    PROJECT_ROLES = ["owner", "member", "viewer"]
    
    # 数据归属
    OWNER_TYPES = ["system", "personal", "project"]
    
    # 环境类型
    ENV_TYPES = ["dev", "test", "prod"]
```

### B. 数据库表结构

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 项目表
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT,
    owner_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 项目成员表
CREATE TABLE project_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    user_id INTEGER REFERENCES users(id),
    role TEXT NOT NULL DEFAULT 'member',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

-- 项目配置表
CREATE TABLE project_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    env_type TEXT NOT NULL,
    config_key TEXT NOT NULL,
    config_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, env_type, config_key)
);

-- 审核表
CREATE TABLE review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    content TEXT,
    status TEXT DEFAULT 'pending',
    review_comment TEXT,
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 修改文档表
ALTER TABLE documents ADD COLUMN owner_type TEXT DEFAULT 'personal';
ALTER TABLE documents ADD COLUMN owner_id INTEGER;
```
