# 认证体系

## 概述

AIDP 使用统一的 Cookie + API Key + JWT 混合认证体系。Controller 负责管理用户、角色、权限、API Key 和审计日志。

**源码**:
- 路由: `apps/controller/app/api/auth.py`
- 模型: `apps/controller/app/db/auth_models.py`
- 服务: `apps/controller/app/services/auth_service.py`
- 权限: `apps/controller/app/services/permission_service.py`
- JWT: `apps/controller/app/security/jwt_auth.py`

## 数据模型

### User (用户)

```python
# app/db/auth_models.py:58
class User(Base):
    __tablename__ = "users"
    id: str (UUID)
    username: str (unique)
    password_hash: str
    email: str (unique, optional)
    nickname: str
    avatar_url: str
    role: str       # "super_admin" | "admin" | "developer" | "user" | "readonly"
    status: str     # "active" | "inactive" | "suspended" | "pending"
    is_verified: bool
    last_login_at: datetime
    created_at / updated_at: datetime
```

### UserRole (角色)

```python
class UserRole(str, PyEnum):
    SUPER_ADMIN = "super_admin"  # 全系统访问
    ADMIN = "admin"              # 管理用户、设置
    DEVELOPER = "developer"      # 创建/编辑 skills/tools
    USER = "user"                # 使用工具
    READONLY = "readonly"        # 只读
```

### UserStatus (状态)

```python
class UserStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
```

### UserSession (会话)

```python
# app/db/auth_models.py:107
class UserSession(Base):
    __tablename__ = "user_sessions"
    id: str (UUID)
    user_id: str (FK users.id)
    session_token: str (unique, 255)
    refresh_token: str
    ip_address: str (IPv6 兼容)
    user_agent: str
    expires_at: datetime
    last_activity_at: datetime
```

- 支持多设备同时登录 (每个设备一个独立 session)
- `remember_me=True` 时过期时间 7 天，否则 1 天
- Cookie 名: `aidp_session`

### LoginLog (登录日志)

```python
# app/db/auth_models.py:146
class LoginLog(Base):
    __tablename__ = "login_logs"
    user_id: str (FK users.id)
    username: str       # 尝试登录的用户名
    action: str         # "login" | "logout" | "login_failed" | "token_refresh" | "password_changed"
    ip_address: str
    user_agent: str
    success: bool
    fail_reason: str
```

### Permission (权限定义)

```python
# app/db/auth_models.py:187
class Permission(Base):
    __tablename__ = "permissions"
    code: str (unique)      # e.g., "tool:read", "user:write"
    name: str
    description: str
    resource_type: str      # tool, user, model, etc.
    action: str             # read, write, delete, execute
```

### RolePermission (角色-权限关联)

```python
# app/db/auth_models.py:217
class RolePermission(Base):
    __tablename__ = "role_permissions"
    role: str (PK)          # UserRole value
    permission_id: str (PK) # FK permissions.id
```

这是多对多关联表: 角色可以有多个权限，每个权限可以分配给多个角色。

### ApiKey (API Key)

```python
# app/db/auth_models.py:233
class ApiKey(Base):
    __tablename__ = "api_keys"
    user_id: str (FK users.id)
    label: str
    key_hash: str (SHA256, unique)
    key_preview: str         # 前几个字符用于显示
    raw_key: str             # 加密存储的原始 key (内部可用)
    scopes: JSON             # ["read", "write"]
    rate_limit_req_per_min: int (default 60)
    expires_at: datetime
    last_used_at: datetime
    is_active: bool
```

### AuditLog (审计日志)

```python
# app/db/auth_models.py:280
class AuditLog(Base):
    __tablename__ = "audit_logs"
    user_id: str (FK users.id)
    action: str             # CREATE, UPDATE, DELETE, LOGIN
    resource_type: str      # user, model, tool, etc.
    resource_id: str
    resource_name: str
    old_values: JSON
    new_values: JSON
    ip_address: str
    user_agent: str
```

### SystemSetting (系统配置)

```python
# app/db/auth_models.py:326
class SystemSetting(Base):
    __tablename__ = "system_settings"
    key: str (unique)
    value: JSON
    description: str
    is_encrypted: bool
    updated_by: str (FK users.id)
```

## 认证流程

### Web UI 登录

```
POST /api/auth/login              (API)
POST /api/auth/login/form         (Form, 重定向到 /)
POST /api/auth/logout             (API)
POST /api/auth/logout/form        (Form, 重定向到 /login)

流程:
1. 用户提交 username + password
2. AuthService.authenticate_user(username, password, ip, ua)
   - 查找 User，验证密码
   - 检查 status == "active"
   - 记录 LoginLog (action="login" 或 "login_failed")
3. AuthService.create_session(user_id, ip, ua, remember_me)
   - 创建 UserSession，生成 session_token (UUID-based)
   - 设置 expires_at (1天 或 7天)
4. Set-Cookie: aidp_session=<token>; HttpOnly; SameSite=Lax
5. 返回 User 信息
```

### API Key 认证

MCP Server 通过 `x-api-key` header 传递 API Key:

```python
# app/mcp/server.py:66
api_key = request.headers.get("x-api-key", "")
```

API Key 管理端点:
- `GET /api/auth/api-keys` — 列出当前用户的 API Keys
- `POST /api/auth/api-keys` — 创建新 Key (返回 raw_key，仅此一次)
- `DELETE /api/auth/api-keys/{key_id}` — 撤销 Key
- `GET /api/auth/api-keys/{key_id}/reveal` — 查看 raw_key (内部系统)

### 会话验证 (Dependency)

```python
# app/api/auth.py:515
async def get_current_user(request: Request) -> Optional[User]:
    session_token = request.cookies.get("aidp_session")
    return await AuthService.validate_session(session_token)

# app/api/auth.py:523
async def require_auth(request: Request) -> User:
    user = await get_current_user(request)
    if not user: raise HTTPException(401)
    return user

# app/api/auth.py:531
async def require_admin(request: Request) -> User:
    user = await require_auth(request)
    if not PermissionService.is_admin(user): raise HTTPException(403)
    return user
```

## 权限系统

### 基于角色的访问控制 (RBAC)

```python
class PermissionService:
    @staticmethod
    def is_admin(user):
        return user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)

    @staticmethod
    def is_super_admin(user):
        return user.role == UserRole.SUPER_ADMIN
```

### 基于 Scopes 的访问控制

API Key 支持 scopes 字段限制访问范围:

```python
scopes = ["read", "write"]
```

### 权限依赖注入

各路由使用 `require_permissions` 进行权限保护:

```python
# app/core/permissions.py
def require_permissions(permission_code: str):
    """FastAPI dependency that checks user has required permission"""
    # 示例:
    # require_permissions("knowledge:write")
    # require_permissions("memory:write")
    # require_permissions("project:create")
    # require_permissions("skills:write:personal")
    # require_permissions("asset:write")
```

### Scope Read Access

```python
# app/core/permissions.py
async def check_scope_read_access(user, module: str, scope: str):
    """Check if user has read access to module at given scope level"""
    # 模块: "knowledge", "skills", "memory"
    # scope: "global", "personal", "project"
```

### 路由保护示例

| 路由 | 权限要求 |
|------|---------|
| `POST /api/knowledge/bases` | `knowledge:write` |
| `DELETE /api/knowledge/bases/{id}` | `knowledge:delete` |
| `POST /api/memory/memories` | `memory:write` |
| `DELETE /api/memory/memories/{id}` | `memory:delete` |
| `POST /api/projects` | `project:create` |
| `PUT /api/projects/{id}` | `project:create` |
| `POST /api/skills/create` | `skills:write:personal` |
| `POST /api/rules/create` | `skills:write:personal` |
| `POST /api/agents/create` | `skills:write:personal` |
| `POST /api/assets/create` | `asset:write` |
| `DELETE /api/assets/{id}` | `asset:delete` |
| `POST /api/workflows/create` | `skills:write:personal` |

## 用户管理 API (Admin)

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/auth/users` | GET | Admin | 分页列表用户 |
| `/api/auth/users` | POST | Admin | 创建用户 (username, password, role) |
| `/api/auth/users/{id}` | PUT | Admin | 更新用户 |
| `/api/auth/users/{id}` | DELETE | Super Admin | 删除用户 |
| `/api/auth/users/{id}/toggle` | POST | Admin | 启用/禁用用户 |

## 用户自助 API

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/auth/me` | GET | Authenticated | 获取当前用户信息 |
| `/api/auth/change-password` | POST | Authenticated | 修改密码 |
| `/api/auth/profile` | PUT | Authenticated | 更新个人信息 |

## 安全特性

1. **密码**: bcrypt 哈希存储 (`password_hash`)
2. **会话**: HttpOnly Cookie, SameSite=Lax
3. **API Key**: SHA256 哈希存储, raw_key 加密存储用于内部查看
4. **审计**: 所有重要操作记录到 audit_logs (CREATE/UPDATE/DELETE/LOGIN)
5. **登录保护**: 记录登录失败日志, fail_reason 字段
6. **自保护**: 不能禁用/删除自己 (`user_id == current_user.id` 检查)

## 初始化

系统启动时自动创建默认管理员账户 (通过 seed_data 或 init_db):

```python
# app/services/auth_service.py
await AuthService.create_user(
    username="admin",
    password="admin123",
    role=UserRole.SUPER_ADMIN,
)
```

## 与其他系统的集成

Controller 内部模块使用 `get_current_user` dependency 从 Cookie 获取用户:

```python
@router.get("/bases")
async def list_bases(
    user=Depends(get_current_user),  # 从 Cookie 读取 session
    db: AsyncSession = Depends(get_db)
):
```

MCP Server 通过 `x-api-key` header 传递认证信息:

```python
@mcp.tool()
async def invoke_tool_mcp(ctx: Context, api_key: str = ""):
    if not api_key:
        api_key = ctx.request.headers.get("x-api-key", "")
```

## 数据表关系

```
users (1) ----< user_sessions
users (1) ----< api_keys
users (1) ----< login_logs
users (1) ----< audit_logs
permissions (1) ----< role_permissions >---- users.role
projects <-- 通过 owner_id 关联 users
```