# AIDP 统一 Web UI 平台 - 需求与设计文档

## 1. 项目概述

### 1.1 背景
当前 AIDP 的各个工具（knowledge-tool, memory-tool, sandbox-tool 等）都有自己的独立 Web UI，存在以下问题：
- 每个工具需要单独登录
- 用户管理、权限管理重复实现
- 界面风格不统一
- 模型配置、API密钥等通用功能重复

### 1.2 目标
构建一个**统一的 Web UI 平台**，实现：
1. **单点登录（SSO）**：一次登录，访问所有工具
2. **共享基础设施**：用户、权限、模型、密钥等通用功能统一
3. **统一风格**：所有工具使用一致的 UI/UX 设计
4. **工具插件化**：各工具作为插件接入，保留业务独立性

### 1.3 核心原则
- **Controller 作为入口**：统一 Web UI 集成在 Controller 中
- **共享服务**：认证、用户、权限、模型、密钥等服务下沉到 Controller
- **工具自治**：各工具保留业务功能，通过 API 与 Controller 交互
- **渐进式迁移**：逐步将工具功能迁移到统一平台

---

## 2. 功能需求

### 2.1 统一认证与授权（SSO）

#### 2.1.1 登录系统
- **统一登录页**：所有工具共享登录页面
- **Session 共享**：登录 Controller 后自动登录所有工具
- **Token 机制**：JWT Token 或 Session Cookie 跨工具传递
- **记住我**：支持长期登录
- **多因素认证（MFA）**：（可选）支持 Google Authenticator

#### 2.1.2 用户管理（管理员功能）
| 功能 | 描述 |
|------|------|
| 用户列表 | 查看所有用户，支持搜索、筛选 |
| 创建用户 | 用户名、密码、角色、昵称、备注 |
| 编辑用户 | 修改基本信息、重置密码 |
| 启用/禁用 | 控制用户访问权限 |
| 删除用户 | 软删除或硬删除 |
| 用户导入/导出 | 批量操作 |

#### 2.1.3 角色与权限
- **角色定义**：
  - `super_admin`：超级管理员，全部权限
  - `admin`：管理员，管理用户、配置
  - `developer`：开发者，创建/编辑技能
  - `user`：普通用户，使用工具
  - `readonly`：只读用户

- **权限粒度**：
  - 工具级别：能否访问某工具
  - 功能级别：读、写、删除、执行
  - 数据级别：个人数据、团队数据、公共数据

### 2.2 共享基础设施

#### 2.2.1 模型管理（LLM Config）
所有工具共享 LLM 配置，避免重复配置：

| 字段 | 说明 |
|------|------|
| 名称 | 配置标识（如"DeepSeek-V3"） |
| 提供商 | OpenAI、DeepSeek、本地等 |
| Endpoint | API 地址 |
| API Key | 加密存储 |
| 模型名称 | 具体模型（如"deepseek-v3"） |
| 角色 | 用途分类（embedding、completion、ranker等） |
| 参数 | temperature、max_tokens、timeout |
| 默认标记 | 是否设为默认 |

**功能**：
- 模型列表（查看健康状态）
- 添加/编辑/删除模型
- 设为默认
- 健康检查

#### 2.2.2 API 密钥管理
| 功能 | 描述 |
|------|------|
| 密钥列表 | 查看所有密钥，显示使用统计 |
| 创建密钥 | 生成新的 API Key（sk-xxx） |
| 撤销密钥 | 立即失效 |
| 使用限制 | 设置速率限制、过期时间 |
| 使用日志 | 查看密钥调用记录 |

#### 2.2.3 系统设置
全局配置，影响所有工具：

| 配置项 | 说明 |
|--------|------|
| 站点信息 | 名称、Logo、主题色 |
| 注册设置 | 是否开放注册、是否需要审核 |
| 安全设置 | 密码策略、登录失败锁定、Session 过期时间 |
| 通知设置 | 邮件 SMTP、Webhook |
| 存储设置 | 文件存储位置、备份策略 |
| 日志设置 | 日志级别、保留时间 |

### 2.3 工具管理

#### 2.3.1 工具发现与注册
- **自动发现**：工具启动时自动注册到 Controller
- **手动注册**：管理员手动添加工具
- **工具卡片**：显示名称、描述、状态、版本
- **健康监控**：实时显示工具健康状态

#### 2.3.2 工具配置
每个工具可以有自己的配置页面：
- 配置项定义（由 tool.yaml 提供）
- 表单自动生成
- 配置验证
- 配置下发到工具

#### 2.3.3 工具权限
- 谁能访问该工具
- 工具内的功能权限

### 2.4 业务功能（按工具）

#### 2.4.1 SkillRouter 功能
继承现有 SkillRouter 的全部功能：
- 技能管理（CRUD、导入导出、评审）
- 规则管理
- 项目管理
- 模型管理（使用共享模型）
- 权限管理
- 解析测试
- 统计分析

#### 2.4.2 Knowledge Tool 功能
- 文档管理（上传、索引、搜索）
- 知识库管理
- 文档分类

#### 2.4.3 Memory Tool 功能
- 记忆管理（CRUD）
- 项目记忆查看
- 上下文查询

#### 2.4.4 Sandbox Tool 功能
- 代码执行
- 执行历史
- 安全管理

#### 2.4.5 其他工具
- Asset Tool：代码片段、模板管理
- Quality Tool：代码质量检查
- Code Index：代码索引、搜索

### 2.5 统一界面元素

#### 2.5.1 导航结构
```
顶部导航栏
├── Logo + 平台名称
├── 全局搜索
├── 工具切换器（下拉菜单）
├── 通知中心
└── 用户菜单

侧边栏
├── 仪表盘（总览）
├── 工具列表
│   ├── SkillRouter
│   │   ├── 项目管理
│   │   ├── 技能管理
│   │   ├── 规则管理
│   │   └── ...
│   ├── Knowledge Tool
│   │   ├── 文档管理
│   │   └── 知识库
│   └── ...
├── 管理（管理员可见）
│   ├── 用户管理
│   ├── 角色权限
│   ├── 模型管理
│   ├── API密钥
│   └── 系统设置
└── 个人
    ├── 个人资料
    └── API密钥
```

#### 2.5.2 通用组件
- **数据表格**：排序、筛选、分页、批量操作
- **表单组件**：验证、自动保存
- **模态框**：确认、表单、详情
- **状态标签**：健康/错误/警告
- **加载状态**：骨架屏、加载动画
- **通知系统**：Toast、消息中心

---

## 3. 技术架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     统一 Web UI 平台                          │
│                     (Controller + Web)                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Auth       │  │  Shared     │  │  Tool Manager       │  │
│  │  Service    │  │  Services   │  │  (工具管理)          │  │
│  │             │  │             │  │                     │  │
│  │ • Login     │  │ • User      │  │ • Discovery         │  │
│  │ • Session   │  │ • Role      │  │ • Config            │  │
│  │ • SSO       │  │ • Permission│  │ • Proxy             │  │
│  │ • JWT       │  │ • Model     │  │                     │  │
│  │             │  │ • API Key   │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                      Tool Plugins (工具插件)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │SkillRouter│ │Knowledge │ │ Memory   │ │   Sandbox    │   │
│  │  Module   │ │  Module  │ │  Module  │ │   Module     │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌──────────────┐    ┌──────────────┐
            │   Tools      │    │   Tools      │
            │  (External)  │    │  (External)  │
            └──────────────┘    └──────────────┘
```

### 3.2 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Alpine.js 3 | 轻量级响应式框架 |
| CSS | Tailwind CSS | 原子化 CSS |
| 后端 | FastAPI | Python Web 框架 |
| 模板 | Jinja2 | HTML 模板引擎 |
| 数据库 | PostgreSQL | 主数据库 |
| 缓存 | Redis | Session、缓存 |
| 消息 | Redis Pub/Sub | 实时通知 |
| 前端构建 | 无 | 直接使用 CDN |

### 3.3 目录结构

```
apps/controller/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置
│   ├── db/
│   │   ├── models.py           # 数据库模型
│   │   ├── database.py         # 数据库连接
│   │   └── init_db.py          # 初始化
│   │
│   ├── api/                    # REST API
│   │   ├── auth.py             # 认证相关
│   │   ├── users.py            # 用户管理
│   │   ├── roles.py            # 角色权限
│   │   ├── models.py           # 模型管理
│   │   ├── api_keys.py         # API密钥
│   │   ├── tools.py            # 工具管理
│   │   └── settings.py         # 系统设置
│   │
│   ├── services/               # 业务服务
│   │   ├── auth_service.py     # 认证服务
│   │   ├── user_service.py     # 用户服务
│   │   ├── sso_service.py      # SSO服务
│   │   ├── model_service.py    # 模型服务
│   │   ├── tool_proxy.py       # 工具代理
│   │   └── permission_service.py # 权限服务
│   │
│   ├── web/                    # Web UI
│   │   ├── routes.py           # 页面路由
│   │   ├── auth.py             # 登录相关页面
│   │   ├── admin/              # 管理页面
│   │   │   ├── users.py
│   │   │   ├── roles.py
│   │   │   ├── models.py
│   │   │   └── settings.py
│   │   ├── tools/              # 工具页面
│   │   │   ├── base.py         # 工具基类
│   │   │   ├── skillrouter.py  # SkillRouter 页面
│   │   │   ├── knowledge.py    # Knowledge Tool 页面
│   │   │   └── ...
│   │   └── templates/          # HTML 模板
│   │       ├── base.html       # 基础布局
│   │       ├── login.html
│   │       ├── admin/
│   │       └── tools/
│   │
│   ├── shared/                 # 共享模块
│   │   ├── decorators.py       # 装饰器（登录检查等）
│   │   ├── pagination.py       # 分页工具
│   │   └── forms.py            # 表单验证
│   │
│   └── static/                 # 静态文件
│       ├── css/
│       ├── js/
│       └── components/
│
├── migrations/                 # 数据库迁移
└── requirements.txt
```

---

## 4. 数据库设计

### 4.1 核心表

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    nickname VARCHAR(128),
    avatar_url TEXT,
    role VARCHAR(32) DEFAULT 'user', -- super_admin, admin, developer, user, readonly
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 角色表（可扩展）
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(32) UNIQUE NOT NULL,
    display_name VARCHAR(128),
    description TEXT,
    permissions JSONB DEFAULT '[]', -- 权限列表
    is_system BOOLEAN DEFAULT FALSE, -- 系统角色不可删除
    created_at TIMESTAMP DEFAULT NOW()
);

-- 权限定义表
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(64) UNIQUE NOT NULL, -- 如：tool:read, tool:write
    name VARCHAR(128),
    description TEXT,
    resource_type VARCHAR(32), -- tool, user, model, etc.
    action VARCHAR(32) -- read, write, delete, execute
);

-- 用户角色关联（多对多）
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT NOW(),
    granted_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

-- 会话表（支持多设备登录）
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW()
);

-- 登录日志
CREATE TABLE login_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    username VARCHAR(64), -- 记录尝试登录的用户名
    action VARCHAR(32), -- login, logout, login_failed
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN,
    fail_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- LLM 模型配置表
CREATE TABLE llm_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL,
    provider VARCHAR(64) NOT NULL, -- openai, deepseek, local
    endpoint VARCHAR(512) NOT NULL,
    api_key_encrypted TEXT, -- 加密存储
    model_name VARCHAR(128),
    role VARCHAR(32), -- embedding, completion, ranker, intent, review
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2048,
    timeout_secs INTEGER DEFAULT 30,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    health_status VARCHAR(32) DEFAULT 'unknown', -- healthy, unhealthy, unknown
    last_health_check TIMESTAMP,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- API 密钥表
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    label VARCHAR(128),
    key_hash VARCHAR(255) UNIQUE NOT NULL, -- SHA256(key)
    key_preview VARCHAR(20), -- 显示前几位，如 "sk-abc..."
    scopes JSONB DEFAULT '["read"]', -- 权限范围
    rate_limit_req_per_min INTEGER DEFAULT 60,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 工具注册表
CREATE TABLE registered_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(128),
    description TEXT,
    version VARCHAR(32),
    endpoint VARCHAR(512) NOT NULL,
    icon VARCHAR(255),
    status VARCHAR(32) DEFAULT 'registered', -- registered, healthy, unhealthy, disabled
    capabilities JSONB DEFAULT '[]',
    config_schema JSONB, -- 配置项定义
    default_config JSONB, -- 默认配置
    required_permissions JSONB DEFAULT '["tool:read"]',
    is_active BOOLEAN DEFAULT TRUE,
    last_heartbeat_at TIMESTAMP,
    registered_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 工具权限配置
CREATE TABLE tool_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID REFERENCES registered_tools(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permissions JSONB DEFAULT '["read"]', -- read, write, execute, admin
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tool_id, role_id)
);

-- 系统设置表
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(128) UNIQUE NOT NULL,
    value JSONB,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE, -- 是否加密（如密码）
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 审计日志
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(64) NOT NULL, -- CREATE, UPDATE, DELETE, LOGIN, etc.
    resource_type VARCHAR(64), -- user, model, tool, etc.
    resource_id UUID,
    resource_name VARCHAR(255), -- 冗余存储，方便查询
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 通知表
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(32), -- info, success, warning, error
    title VARCHAR(255),
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    action_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.2 索引设计

```sql
-- 用户相关索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_email ON users(email);

-- 会话索引
CREATE INDEX idx_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);

-- API 密钥索引
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);

-- 审计日志索引
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- 工具索引
CREATE INDEX idx_tools_name ON registered_tools(name);
CREATE INDEX idx_tools_status ON registered_tools(status);
```

---

## 5. API 设计

### 5.1 认证相关

```yaml
# 登录
POST /api/auth/login
Request:
  username: string
  password: string
  remember_me: boolean
Response:
  success: boolean
  token: string      # JWT Token
  expires_at: timestamp
  user: UserInfo

# 登出
POST /api/auth/logout

# 刷新 Token
POST /api/auth/refresh

# 获取当前用户
GET /api/auth/me

# 修改密码
POST /api/auth/change-password
```

### 5.2 用户管理

```yaml
# 用户列表
GET /api/users?page=1&size=20&role=&search=
Response:
  items: [User]
  total: number
  page: number
  size: number

# 创建用户
POST /api/users
Request:
  username: string
  password: string
  email: string
  nickname: string
  role: string

# 更新用户
PUT /api/users/{id}

# 删除用户
DELETE /api/users/{id}

# 启用/禁用
POST /api/users/{id}/toggle-active
```

### 5.3 模型管理

```yaml
# 模型列表
GET /api/models

# 创建模型
POST /api/models
Request:
  name: string
  provider: string
  endpoint: string
  api_key: string
  model_name: string
  role: string
  temperature: float
  max_tokens: int

# 健康检查
POST /api/models/{id}/health-check

# 设为默认
POST /api/models/{id}/set-default
```

### 5.4 工具管理

```yaml
# 工具列表
GET /api/tools

# 工具详情
GET /api/tools/{name}

# 工具健康检查
POST /api/tools/{name}/health

# 工具配置
GET /api/tools/{name}/config
PUT /api/tools/{name}/config

# 代理到工具
GET /api/proxy/{tool_name}/{path}
POST /api/proxy/{tool_name}/{path}
```

---

## 6. 界面设计

### 6.1 页面列表

| 页面 | 路径 | 权限 |
|------|------|------|
| 登录页 | /login | 公开 |
| 仪表盘 | / | 登录用户 |
| 工具列表 | /tools | 登录用户 |
| 用户管理 | /admin/users | admin |
| 角色管理 | /admin/roles | admin |
| 模型管理 | /admin/models | admin |
| API密钥管理 | /admin/api-keys | admin |
| 系统设置 | /admin/settings | admin |
| SkillRouter 面板 | /tools/skillrouter | 有权限用户 |
| Knowledge Tool 面板 | /tools/knowledge | 有权限用户 |
| ... | ... | ... |

### 6.2 关键界面原型

#### 登录页
```
┌─────────────────────────────────────────┐
│              [Logo] AIDP                │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  用户名                         │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │  密码                           │   │
│  └─────────────────────────────────┘   │
│  [ ] 记住我                             │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │         登 录                   │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

#### 主界面布局
```
┌──────────────────────────────────────────────────────────────┐
│ [Logo] AIDP    [搜索...]     [通知] [工具▼] [用户▼]         │
├──────────┬───────────────────────────────────────────────────┤
│          │  页面标题                              [操作按钮] │
│  📊 总览  ├───────────────────────────────────────────────────┤
│  ────────│                                                   │
│  🛠️ 工具  │  内容区域                                         │
│  ├ Skill │                                                   │
│  ├ Know  │                                                   │
│  ├ Mem   │                                                   │
│  └ ...   │                                                   │
│  ────────│                                                   │
│  ⚙️ 管理  │                                                   │
│  ├ 用户  │                                                   │
│  ├ 角色  │                                                   │
│  ├ 模型  │                                                   │
│  └ 设置  │                                                   │
│          │                                                   │
└──────────┴───────────────────────────────────────────────────┘
```

---

## 7. 开发计划

### 阶段 1：基础设施（2 周）
- [ ] 数据库模型设计与迁移
- [ ] 认证系统（登录/登出/Session）
- [ ] 基础布局（导航栏、侧边栏）
- [ ] 用户管理 CRUD
- [ ] 角色权限框架

### 阶段 2：共享服务（2 周）
- [ ] 模型管理（LLM Config）
- [ ] API 密钥管理
- [ ] 系统设置
- [ ] 审计日志
- [ ] 通知系统

### 阶段 3：工具接入（2 周）
- [ ] 工具发现与注册机制
- [ ] 工具代理路由
- [ ] 工具权限控制
- [ ] SkillRouter 接入
- [ ] Knowledge Tool 接入

### 阶段 4：功能完善（2 周）
- [ ] 仪表盘设计
- [ ] 全局搜索
- [ ] 个人中心
- [ ] 主题/外观设置
- [ ] 性能优化

### 阶段 5：迁移与测试（1 周）
- [ ] 数据迁移脚本
- [ ] 集成测试
- [ ] 用户验收测试
- [ ] 文档完善

---

## 8. 关键技术方案

### 8.1 SSO 实现

**方案：JWT + Session 混合**

1. **登录 Controller** 时：
   - 验证用户名密码
   - 生成 JWT Token（长期有效，用于工具间传递）
   - 创建 Session（短期，用于 Web 页面）
   - 将 Token 同步到各工具（通过 Redis 或 API 调用）

2. **访问工具时**：
   - 携带 JWT Token（Cookie 或 Header）
   - 工具验证 Token（共享密钥）
   - 获取用户信息

3. **Token 刷新**：
   - 使用 Refresh Token 机制
   - 或自动续期 Session

### 8.2 工具接入标准

每个工具需要提供：

```yaml
# tool.yaml
apiVersion: aidp.dev/v1
kind: Tool

metadata:
  name: knowledge-tool
  displayName: Knowledge Tool
  description: 文档知识库管理
  icon: fa-book

web:
  # 工具是否需要自己的 Web UI
  enabled: true
  # 工具页面路径（相对）
  basePath: /
  # 是否支持嵌入到统一平台
  embeddable: true
  # 需要的路由
  routes:
    - path: /documents
      name: 文档管理
      icon: fa-file
    - path: /search
      name: 搜索测试
      icon: fa-search

# 工具需要的权限
permissions:
  - code: knowledge:read
    name: 查看文档
  - code: knowledge:write
    name: 管理文档

# 工具配置项
config:
  - key: storage.provider
    type: select
    options: [local, minio, s3]
    default: local
  - key: embedding.provider
    type: select
    options: [mock, openai]
    default: mock
```

### 8.3 数据隔离

- **用户数据**：按 user_id 隔离
- **团队数据**：支持团队/项目概念
- **公共数据**：所有用户可见

### 8.4 性能优化

- **数据库连接池**：SQLAlchemy 连接池
- **Redis 缓存**：用户信息、权限、工具状态
- **静态文件 CDN**：可考虑使用 CDN
- **分页加载**：所有列表默认分页

---

## 9. 安全考虑

### 9.1 认证安全
- 密码使用 bcrypt 加密
- JWT 使用 HS256 或 RS256
- Token 过期时间合理设置
- 支持强制重新登录

### 9.2 访问控制
- 基于角色的访问控制（RBAC）
- API 级别的权限检查
- 资源级别的权限检查（如只能编辑自己的数据）

### 9.3 数据安全
- 敏感配置加密存储（API Key、密码）
- 数据库连接使用 SSL（可选）
- 审计日志记录所有敏感操作

### 9.4 防护措施
- 登录失败锁定（防暴力破解）
- 速率限制（API 级别）
- CSRF 防护
- XSS 防护（模板转义）

---

## 10. 附录

### 10.1 术语表

| 术语 | 说明 |
|------|------|
| SSO | Single Sign-On，单点登录 |
| RBAC | Role-Based Access Control，基于角色的访问控制 |
| JWT | JSON Web Token |
| Controller | AIDP 主控制器 |
| Tool | 各个工具服务 |
| Module | 统一 Web UI 中的功能模块 |

### 10.2 参考文档
- SkillRouter 现有功能
- FastAPI 官方文档
- Alpine.js 文档
- Tailwind CSS 文档

---

**文档版本**: v1.0  
**编写日期**: 2026-07-05  
**状态**: 设计中
