# 数据归属、权限与项目协作设计文档

---

## 目录

1. [定位与目标](#1-定位与目标)
2. [数据归属模型](#2-数据归属模型)
3. [权限模型](#3-权限模型)
4. [项目协作](#4-项目协作)
5. [环境配置](#5-环境配置)
6. [审核流程](#6-审核流程)
7. [数据模型](#7-数据模型)
8. [API 设计](#8-api-设计)
9. [实施计划](#9-实施计划)

---

## 1. 定位与目标

### 1.1 核心问题

当前系统缺乏数据归属和权限控制：
- 所有数据都是公共的，无个人空间
- 无项目协作能力
- 无环境配置管理
- 无审核流程

### 1.2 解决方案

- **数据归属**: 区分公共、个人、项目数据
- **权限控制**: admin/user + 项目角色
- **项目协作**: 创建项目 + 邀请成员
- **环境配置**: 项目环境配置管理
- **审核流程**: 用户提交 → 管理员审核

### 1.3 设计原则

| 原则 | 描述 |
|------|------|
| **最小权限** | 只给必要的权限 |
| **数据隔离** | 公共/个人/项目数据分离 |
| **协作友好** | 支持多人协作 |
| **配置集中** | 环境配置统一管理 |

---

## 2. 数据归属模型

### 2.1 数据分类

```
┌─────────────────────────────────────────────────────────────┐
│                    数据分类                                  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  System (公共)                                          │ │
│  │  - 技术文档: Vue、Spring Boot 等                        │ │
│  │  - 公共 Skills: 通用技能、规则                          │ │
│  │  - 权限: 所有人只读，管理员维护                        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Personal (个人)                                        │ │
│  │  - 个人文档: 用户自己添加的文档                        │ │
│  │  - 个人 Skills: 用户自定义技能                         │ │
│  │  - 权限: 用户完全控制，可提交到公共                    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Project (项目)                                         │ │
│  │  - 项目文档: 项目专属文档                              │ │
│  │  - 项目 Skills: 项目专属技能                           │ │
│  │  - 项目 Memory: 项目经验                               │ │
│  │  - Code Index: 项目代码索引                            │ │
│  │  - 环境配置: 项目环境配置                              │ │
│  │  - 权限: 项目成员可查看/编辑                           │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据归属表

| 数据类型 | 归属 | owner_type | owner_id | 说明 |
|----------|------|------------|----------|------|
| **技术文档** | System | system | NULL | Vue、Spring Boot 等 |
| **个人文档** | User | personal | user_id | 用户自己添加 |
| **项目文档** | Project | project | project_id | 项目专属 |
| **公共 Skills** | System | system | NULL | 通用技能 |
| **个人 Skills** | User | personal | user_id | 用户自定义 |
| **项目 Skills** | Project | project | project_id | 项目专属 |
| **Memory** | Project | project | project_id | 项目经验 |
| **Code Index** | Project | project | project_id | 项目代码索引 |
| **环境配置** | Project | project | project_id | 项目环境配置 |

### 2.3 数据操作权限

| 操作 | System | Personal | Project (成员) |
|------|--------|----------|----------------|
| **查看** | ✅ 所有人 | ✅ 所有人 | ✅ 项目成员 |
| **创建** | ❌ 仅管理员 | ✅ 用户 | ✅ 项目成员 |
| **修改** | ❌ 仅管理员 | ✅ 所有人 | ✅ 项目成员 |
| **删除** | ❌ 仅管理员 | ✅ 所有人 | ✅ 项目成员 |
| **提交到公共** | - | ✅ 用户 | - |

---

## 3. 权限模型

### 3.1 角色定义

```
┌─────────────────────────────────────────────────────────────┐
│                    角色定义                                  │
│                                                               │
│  Admin (管理员)                                              │
│  ├── 管理公共数据（创建/修改/删除）                          │
│  ├── 审核用户提交                                            │
│  ├── 管理用户                                                │
│  └── 管理所有项目                                            │
│                                                               │
│  User (普通用户)                                             │
│  ├── 查看公共数据                                            │
│  ├── 管理个人数据                                            │
│  ├── 提交修改到公共                                          │
│  └── 创建项目                                                │
│                                                               │
│  Project Owner (项目创建者)                                  │
│  ├── 管理项目成员                                            │
│  ├── 管理项目设置                                            │
│  ├── 管理环境配置                                            │
│  └── 删除项目                                                │
│                                                               │
│  Project Member (项目成员)                                   │
│  ├── 查看项目数据                                            │
│  ├── 编辑项目数据                                            │
│  └── 查看环境配置                                            │
│                                                               │
│  Project Viewer (项目访客)                                   │
│  ├── 查看项目数据                                            │
│  └── 查看环境配置                                            │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 权限矩阵

| 操作 | Admin | User | Project Owner | Project Member | Project Viewer |
|------|-------|------|---------------|----------------|----------------|
| **公共数据** | | | | | |
| 查看 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 创建 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 修改 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 删除 | ✅ | ❌ | ❌ | ❌ | ❌ |
| **个人数据** | | | | | |
| 查看 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 创建 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 修改 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 删除 | ✅ | ✅ | ✅ | ✅ | ✅ |
| **项目数据** | | | | | |
| 查看 | ✅ | ❌ | ✅ | ✅ | ✅ |
| 创建 | ✅ | ❌ | ✅ | ✅ | ❌ |
| 修改 | ✅ | ❌ | ✅ | ✅ | ❌ |
| 删除 | ✅ | ❌ | ✅ | ❌ | ❌ |
| **项目管理** | | | | | |
| 邀请成员 | ✅ | ❌ | ✅ | ❌ | ❌ |
| 移除成员 | ✅ | ❌ | ✅ | ❌ | ❌ |
| 修改设置 | ✅ | ❌ | ✅ | ❌ | ❌ |
| 删除项目 | ✅ | ❌ | ✅ | ❌ | ❌ |
| **审核** | | | | | |
| 提交审核 | ❌ | ✅ | ✅ | ✅ | ❌ |
| 审核通过 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 审核拒绝 | ✅ | ❌ | ❌ | ❌ | ❌ |

### 3.3 权限检查代码

```python
# app/security/permissions.py

class PermissionChecker:
    """权限检查器"""
    
    async def check_document_permission(self, user: dict, document: dict, action: str) -> bool:
        """检查文档权限"""
        
        # 管理员有所有权限
        if user["role"] == "admin":
            return True
        
        owner_type = document["owner_type"]
        owner_id = document["owner_id"]
        
        # 公共数据：所有人可查看，仅管理员可修改
        if owner_type == "system":
            return action == "read"
        
        # 个人数据：所有者可操作
        if owner_type == "personal":
            return owner_id == user["id"]
        
        # 项目数据：项目成员可操作
        if owner_type == "project":
            return await self.is_project_member(user["id"], owner_id)
        
        return False
    
    async def check_project_permission(self, user: dict, project_id: int, action: str) -> bool:
        """检查项目权限"""
        
        # 管理员有所有权限
        if user["role"] == "admin":
            return True
        
        # 获取项目成员角色
        role = await self.get_project_role(user["id"], project_id)
        
        if not role:
            return False
        
        # Owner 可执行所有操作
        if role == "owner":
            return True
        
        # Member 可查看和编辑
        if role == "member":
            return action in ["read", "create", "update"]
        
        # Viewer 只能查看
        if role == "viewer":
            return action == "read"
        
        return False
    
    async def is_project_member(self, user_id: int, project_id: int) -> bool:
        """检查是否是项目成员"""
        member = await db.fetch_one("""
            SELECT * FROM project_members
            WHERE user_id = ? AND project_id = ?
        """, (user_id, project_id))
        return member is not None
    
    async def get_project_role(self, user_id: int, project_id: int) -> str:
        """获取项目角色"""
        member = await db.fetch_one("""
            SELECT role FROM project_members
            WHERE user_id = ? AND project_id = ?
        """, (user_id, project_id))
        return member["role"] if member else None
```

---

## 4. 项目协作

### 4.1 项目模型

```
┌─────────────────────────────────────────────────────────────┐
│                    项目模型                                  │
│                                                               │
│  项目 (Project)                                              │
│  ├── 基本信息                                                │
│  │   ├── 项目名称                                            │
│  │   ├── 项目描述                                            │
│  │   ├── 项目类型                                            │
│  │   └── 创建时间                                            │
│  │                                                           │
│  ├── 成员 (Members)                                          │
│  │   ├── Owner: 项目创建者                                   │
│  │   ├── Member: 被邀请的成员                                │
│  │   └── Viewer: 只读成员                                    │
│  │                                                           │
│  ├── 数据                                                    │
│  │   ├── 项目文档                                            │
│  │   ├── 项目 Skills                                         │
│  │   ├── 项目 Memory                                        │
│  │   ├── Code Index                                         │
│  │   └── 环境配置                                            │
│  │                                                           │
│  └── 设置                                                    │
│      ├── 项目设置                                            │
│      └── 环境配置                                            │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 项目 API

```
# 创建项目
POST /api/projects
{
    "name": "ruoyi-cloud-plus",
    "description": "微服务项目",
    "type": "java"
}

Response:
{
    "id": 1,
    "name": "ruoyi-cloud-plus",
    "owner_id": 1,
    "created_at": "2024-01-15T10:30:00Z"
}

# 获取项目列表
GET /api/projects

Response:
{
    "projects": [
        {
            "id": 1,
            "name": "ruoyi-cloud-plus",
            "role": "owner",
            "members": 5
        }
    ]
}

# 邀请成员
POST /api/projects/1/members
{
    "user_id": 2,
    "role": "member"
}

Response:
{
    "success": true,
    "member": {
        "user_id": 2,
        "role": "member"
    }
}

# 移除成员
DELETE /api/projects/1/members/2

Response:
{
    "success": true
}

# 获取项目成员
GET /api/projects/1/members

Response:
{
    "members": [
        {
            "user_id": 1,
            "username": "admin",
            "role": "owner"
        },
        {
            "user_id": 2,
            "username": "user1",
            "role": "member"
        }
    ]
}
```

---

## 5. 环境配置

### 5.1 配置模型

```
┌─────────────────────────────────────────────────────────────┐
│                    环境配置模型                              │
│                                                               │
│  项目配置 (ProjectConfig)                                    │
│  ├── 开发环境 (dev)                                          │
│  │   ├── database_url: jdbc:mysql://dev:3306/db             │
│  │   ├── redis_url: redis://dev:6379                        │
│  │   ├── api_url: http://dev:8080                           │
│  │   └── ...                                                 │
│  │                                                           │
│  ├── 测试环境 (test)                                         │
│  │   ├── database_url: jdbc:mysql://test:3306/db            │
│  │   ├── redis_url: redis://test:6379                       │
│  │   ├── api_url: http://test:8080                          │
│  │   └── ...                                                 │
│  │                                                           │
│  └── 生产环境 (prod)                                         │
│      ├── database_url: jdbc:mysql://prod:3306/db            │
│      ├── redis_url: redis://prod:6379                       │
│      ├── api_url: http://prod:8080                          │
│      └── ...                                                 │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 配置 API

```
# 获取项目配置
GET /api/projects/1/configs

Response:
{
    "dev": {
        "database_url": "jdbc:mysql://dev:3306/db",
        "redis_url": "redis://dev:6379",
        "api_url": "http://dev:8080"
    },
    "test": {
        "database_url": "jdbc:mysql://test:3306/db",
        "redis_url": "redis://test:6379",
        "api_url": "http://test:8080"
    }
}

# 设置项目配置
POST /api/projects/1/configs
{
    "env_type": "dev",
    "config_key": "database_url",
    "config_value": "jdbc:mysql://dev:3306/db"
}

Response:
{
    "success": true
}

# 获取特定环境配置
GET /api/projects/1/configs/dev

Response:
{
    "database_url": "jdbc:mysql://dev:3306/db",
    "redis_url": "redis://dev:6379",
    "api_url": "http://dev:8080"
}

# Agent 自动获取配置
POST /api/projects/1/configs/resolve
{
    "env_type": "dev",
    "keys": ["database_url", "redis_url"]
}

Response:
{
    "database_url": "jdbc:mysql://dev:3306/db",
    "redis_url": "redis://dev:6379"
}
```

### 5.3 项目代码存储（NAS）

```
┌─────────────────────────────────────────────────────────────┐
│                    项目代码存储                              │
│                                                               │
│  NAS 路径: /home/docker/AI-Code/projects/                   │
│                                                               │
│  ├── project-1/                                              │
│  │   ├── .git/                                               │
│  │   ├── src/                                                │
│  │   ├── docs/                                               │
│  │   ├── tests/                                              │
│  │   └── configs/                                            │
│  │       ├── dev.json                                        │
│  │       ├── test.json                                       │
│  │       └── prod.json                                       │
│  │                                                           │
│  ├── project-2/                                              │
│  │   └── ...                                                 │
│  │                                                           │
│  └── shared/                                                 │
│      ├── base-images/                                        │
│      └── templates/                                          │
└─────────────────────────────────────────────────────────────┘
```

**配置项**:

| 配置 | 说明 | 示例 |
|------|------|------|
| `projects_root` | 项目根目录 | `/home/docker/AI-Code/projects` |
| `shared_root` | 共享资源目录 | `/home/docker/AI-Code/shared` |
| `auto_sync` | 自动同步代码 | `true/false` |
| `max_project_size` | 单项目最大空间 | `10GB` |
| `retention_days` | 未活跃项目保留天数 | `90` |

**API**:

```
# 获取项目代码路径
GET /api/projects/1/code-path

Response:
{
    "path": "/home/docker/AI-Code/projects/project-1",
    "exists": true
}

# 同步项目代码到 NAS
POST /api/projects/1/sync-code
{
    "source": "https://github.com/user/project.git",
    "branch": "main"
}

Response:
{
    "success": true,
    "path": "/home/docker/AI-Code/projects/project-1"
}
```

### 5.4 Agent 自动获取配置

```python
# Agent 执行测试/部署前自动获取环境配置

class ProjectConfigFetcher:
    """项目配置自动获取器"""
    
    async def fetch_for_testing(self, project_id: int) -> dict:
        """测试前自动获取配置"""
        
        config = await self.fetch_project_config(project_id, "test")
        
        # Agent 拿到配置后自动执行：
        # 1. 连接测试数据库
        # 2. 执行测试用例
        # 3. 返回测试结果
        return config
    
    async def fetch_for_deployment(self, project_id: int) -> dict:
        """部署前自动获取配置"""
        
        config = await self.fetch_project_config(project_id, "prod")
        
        # Agent 拿到配置后自动执行：
        # 1. 连接生产数据库
        # 2. 执行部署脚本
        # 3. 健康检查
        return config
    
    async def fetch_project_config(self, project_id: int, env_type: str) -> dict:
        """获取项目配置"""
        
        # 从数据库获取
        configs = await self.get_configs_from_db(project_id, env_type)
        
        # 从 NAS 文件获取补充配置
        nas_configs = await self.get_configs_from_nas(project_id, env_type)
        
        # 合并配置
        return {**configs, **nas_configs}
```

### 5.5 Agent 集成

```python
# Agent 自动获取环境配置
class ProjectConfigResolver:
    """项目配置解析器"""
    
    async def resolve(self, project_id: int, env_type: str, keys: List[str]) -> dict:
        """解析项目配置"""
        
        # 获取项目配置
        configs = await self.get_project_config(project_id, env_type)
        
        # 返回请求的配置
        result = {}
        for key in keys:
            if key in configs:
                result[key] = configs[key]
            else:
                result[key] = None
        
        return result
    
    async def get_database_url(self, project_id: int, env_type: str = "dev") -> str:
        """获取数据库连接"""
        config = await self.resolve(project_id, env_type, ["database_url"])
        return config.get("database_url")
    
    async def get_redis_url(self, project_id: int, env_type: str = "dev") -> str:
        """获取 Redis 连接"""
        config = await self.resolve(project_id, env_type, ["redis_url"])
        return config.get("redis_url")
```

---

## 6. 审核流程

### 6.1 审核模型

```
┌─────────────────────────────────────────────────────────────┐
│                    审核流程                                  │
│                                                               │
│  1. 用户提交修改                                             │
│     │                                                        │
│     │  - 个人文档 → 公共文档                                 │
│     │  - 个人 Skill → 公共 Skill                            │
│     │  - 个人修改 → 公共修改                                 │
│     │                                                        │
│     ▼                                                        │
│  2. 进入审核队列                                             │
│     │                                                        │
│     │  - 状态: pending                                       │
│     │  - 提交者: user_id                                     │
│     │  - 内容: 修改内容                                      │
│     │                                                        │
│     ▼                                                        │
│  3. 管理员审核                                               │
│     │                                                        │
│     │  - 通过: 状态 → approved                               │
│     │  - 拒绝: 状态 → rejected                               │
│     │                                                        │
│     ▼                                                        │
│  4. 应用修改                                                 │
│                                                               │
│     - 通过: 更新公共数据                                     │
│     - 拒绝: 通知用户                                         │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 审核 API

```
# 提交审核
POST /api/reviews
{
    "document_id": 100,
    "action": "promote_to_public",
    "content": "修改后的内容"
}

Response:
{
    "id": 1,
    "status": "pending",
    "created_at": "2024-01-15T10:30:00Z"
}

# 获取审核列表（管理员）
GET /api/reviews?status=pending

Response:
{
    "reviews": [
        {
            "id": 1,
            "document_id": 100,
            "user_id": 2,
            "action": "promote_to_public",
            "status": "pending",
            "created_at": "2024-01-15T10:30:00Z"
        }
    ]
}

# 审核通过
POST /api/reviews/1/approve

Response:
{
    "success": true,
    "document_id": 100
}

# 审核拒绝
POST /api/reviews/1/reject
{
    "reason": "内容不符合规范"
}

Response:
{
    "success": true
}
```

---

## 7. 数据模型

### 7.1 用户表

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',  -- admin, user
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 7.2 项目表

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT,  -- java, python, vue, etc.
    owner_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 7.3 项目成员表

```sql
CREATE TABLE project_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    user_id INTEGER REFERENCES users(id),
    role TEXT NOT NULL DEFAULT 'member',  -- owner, member, viewer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);
```

### 7.4 项目配置表

```sql
CREATE TABLE project_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    env_type TEXT NOT NULL,  -- dev, test, prod
    config_key TEXT NOT NULL,
    config_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, env_type, config_key)
);
```

### 7.5 文档表（修改）

```sql
-- 增加归属字段
ALTER TABLE documents ADD COLUMN owner_type TEXT DEFAULT 'personal';
-- owner_type: system, personal, project

ALTER TABLE documents ADD COLUMN owner_id INTEGER;
-- owner_type=system: NULL
-- owner_type=personal: user_id
-- owner_type=project: project_id
```

### 7.6 审核表

```sql
CREATE TABLE review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,  -- promote_to_public, update_public
    content TEXT,  -- 修改后的内容
    status TEXT DEFAULT 'pending',  -- pending, approved, rejected
    review_comment TEXT,
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 8. API 设计

### 8.1 认证 API

```
# 登录
POST /api/auth/login
{
    "username": "admin",
    "password": "admin123"
}

Response:
{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
        "id": 1,
        "username": "admin",
        "role": "admin"
    }
}
```

### 8.2 文档 API（修改）

```
# 获取文档列表（根据归属过滤）
GET /api/documents?owner_type=personal

Response:
{
    "documents": [
        {
            "id": 1,
            "title": "我的笔记",
            "owner_type": "personal",
            "owner_id": 1
        }
    ]
}

# 获取公共文档
GET /api/documents?owner_type=system

Response:
{
    "documents": [
        {
            "id": 100,
            "title": "Vue 使用指南",
            "owner_type": "system",
            "owner_id": null
        }
    ]
}

# 获取项目文档
GET /api/documents?owner_type=project&owner_id=1

Response:
{
    "documents": [
        {
            "id": 200,
            "title": "项目架构文档",
            "owner_type": "project",
            "owner_id": 1
        }
    ]
}
```

### 8.3 审核 API

```
# 提交审核
POST /api/reviews
{
    "document_id": 100,
    "action": "promote_to_public",
    "content": "修改后的内容"
}

# 获取审核列表（管理员）
GET /api/reviews?status=pending

# 审核通过
POST /api/reviews/1/approve

# 审核拒绝
POST /api/reviews/1/reject
{
    "reason": "内容不符合规范"
}
```

### 8.4 项目 API

```
# 创建项目
POST /api/projects
{
    "name": "ruoyi-cloud-plus",
    "description": "微服务项目",
    "type": "java"
}

# 获取项目列表
GET /api/projects

# 邀请成员
POST /api/projects/1/members
{
    "user_id": 2,
    "role": "member"
}

# 移除成员
DELETE /api/projects/1/members/2

# 获取项目成员
GET /api/projects/1/members
```

### 8.5 配置 API

```
# 获取项目配置
GET /api/projects/1/configs

# 设置项目配置
POST /api/projects/1/configs
{
    "env_type": "dev",
    "config_key": "database_url",
    "config_value": "jdbc:mysql://dev:3306/db"
}

# 获取特定环境配置
GET /api/projects/1/configs/dev

# Agent 自动获取配置
POST /api/projects/1/configs/resolve
{
    "env_type": "dev",
    "keys": ["database_url", "redis_url"]
}
```

---

## 9. 实施计划

### 9.1 Phase 1: 数据归属和权限（P0）

**周期**: 1 周（5 天）

**任务**:
- 用户表和认证
- 项目表和成员表
- 文档归属字段
- 权限检查器

**验收标准**:
- [ ] 用户登录工作
- [ ] 文档归属区分
- [ ] 权限检查有效

### 9.2 Phase 2: 项目协作（P1）

**周期**: 1 周（5 天）

**任务**:
- 项目创建/列表
- 成员邀请/移除
- 项目权限控制

**验收标准**:
- [ ] 项目创建工作
- [ ] 成员邀请工作
- [ ] 项目权限有效

### 9.3 Phase 3: 环境配置（P1）

**周期**: 0.5 周（2-3 天）

**任务**:
- 配置 CRUD
- 配置解析器
- Agent 集成

**验收标准**:
- [ ] 配置管理有效
- [ ] Agent 自动获取配置

### 9.4 Phase 4: 审核流程（P2）

**周期**: 0.5 周（2-3 天）

**任务**:
- 提交审核
- 审核列表
- 审核通过/拒绝

**验收标准**:
- [ ] 提交审核工作
- [ ] 审核流程有效

---

## 附录

### A. 配置项

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

### B. 数据库迁移

```sql
-- 迁移脚本

-- 1. 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 创建项目表
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    type TEXT,
    owner_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 创建项目成员表
CREATE TABLE IF NOT EXISTS project_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    user_id INTEGER REFERENCES users(id),
    role TEXT NOT NULL DEFAULT 'member',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

-- 4. 创建项目配置表
CREATE TABLE IF NOT EXISTS project_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    env_type TEXT NOT NULL,
    config_key TEXT NOT NULL,
    config_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, env_type, config_key)
);

-- 5. 创建审核表
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
