# AIDP Authentication & Authorization — 认证与权限系统

## 1. 认证流程

AIDP 采用基于 Session 的认证机制，整个流程如下：

```
用户提交 用户名+密码 → 服务端验证凭据 → 创建 UserSession → 设置 aidp_session Cookie → 后续请求携带 Cookie 验证
```

登录端点 `POST /api/auth/login` 接收 username 和 password 两个字段。`AuthService.authenticate_user()` 方法会先通过用户名或邮箱查找用户（支持 `User.username` 和 `User.email` 两种登录方式），然后检查用户状态是否为 ACTIVE，最后使用 `verify_password()` 验证密码哈希。全部通过后，调用 `create_session()` 创建 `UserSession` 记录并返回用户对象。

登出时，调用 `POST /api/auth/logout` 端点，服务端会删除对应的 `UserSession` 记录，使 Cookie 失效。支持 `logout_all_devices()` 方法，当管理员禁用用户账户时自动清除该用户的所有会话。

Session 验证通过 `AuthService.validate_session(session_token)` 完成。该方法查找未过期的 `UserSession`，更新 `last_activity_at` 时间戳，然后返回关联的 `User` 对象。如果 Session 已过期或用户状态不是 ACTIVE，则返回 None。

密码验证兼容两种哈希格式：
- **bcrypt**（新系统）：哈希以 `$2` 开头，使用 `bcrypt.checkpw()` 验证
- **pbkdf2_sha256**（旧系统兼容）：哈希以 `pbkdf2_sha256$` 开头，解析迭代次数、盐值和哈希值，使用 `hashlib.pbkdf2_hmac` 计算后通过 `hmac.compare_digest` 比对

```python
@staticmethod
def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith('$2'):
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    elif password_hash.startswith('pbkdf2_sha256$'):
        # 兼容旧系统哈希
        ...
    return False
```

## 2. Session 管理

`UserSession` 模型定义在 `auth_models.py:103`，字段如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID (FK) | 关联到 users 表，CASCADE 删除 |
| session_token | String(255) | 唯一，索引，随机生成的令牌 |
| refresh_token | String(255) | 可选，"记住我"功能使用 |
| ip_address | String(45) | 兼容 IPv6 的客户端 IP |
| user_agent | Text | 客户端 User-Agent |
| expires_at | DateTime | 过期时间 |
| created_at | DateTime | 创建时间 |
| last_activity_at | DateTime | 最后活动时间 |

Session 过期策略：
- 默认过期时间：24 小时（`SESSION_EXPIRE_HOURS = 24`）
- "记住我"模式：7 天（`SESSION_EXPIRE_HOURS * 7`）
- token 生成：`secrets.token_urlsafe(32)`，提供 256 位随机性

Session 存储位置为 HTTP-Only Cookie（`aidp_session`），前端不可通过 JavaScript 读取，降低 XSS 攻击风险。

## 3. AuthService 完整代码分析

`AuthService` 类（`auth_service.py:37-444`）提供完整的认证服务方法：

### hash_password / verify_password

```python
@staticmethod
def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
```

### generate_session_token

```python
@staticmethod
def generate_session_token() -> str:
    """生成安全的 Session Token"""
    return secrets.token_urlsafe(32)
```

### authenticate_user

这是核心认证方法。它打开数据库会话，查找用户，检查状态，验证密码，更新最后登录时间，记录登录日志。如果认证成功返回 User 对象，否则返回 None。

```python
@classmethod
async def authenticate_user(cls, username, password, ip_address=None, user_agent=None):
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(or_(User.username == username, User.email == username))
        )
        user = result.scalar_one_or_none()
        # ... 检查状态、验证密码、更新 last_login_at、记录日志
```

### validate_session

验证 Session Token 的有效性。首先检查 token 是否存在且未过期，然后更新 `last_activity_at`，最后获取并返回对应的 User 对象。此方法在 `PermissionChecker._get_current_user()` 中被调用。

### create_api_key

创建 API Key 用于程序化访问。生成的 key 格式为 `aidp_` + 32 字节 hex（共 66 字符）。服务端只存储 SHA256 哈希值，原始 key 仅在创建时返回一次。支持设置过期时间、作用域（scopes）和标签。

```python
@classmethod
async def create_api_key(cls, user_id, label=None, scopes=None, expires_days=None):
    raw_key = "aidp_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    # 存储 key_hash，返回 raw_key
```

## 4. PermissionChecker 权限检查器

`PermissionChecker` 类（`permissions.py:16-172`）实现完整的权限检查流水线：

```
Request → PermissionChecker.__call__() → _get_current_user() → _check_permission() → 返回 User 或抛出 403
```

### __call__ 方法

作为 FastAPI 依赖注入的执行入口：
1. 调用 `_get_current_user(request)` 从 Cookie 中提取用户
2. 如果用户为空，抛出 HTTPException(401)
3. 遍历 `self.permissions` 列表，逐个调用 `_check_permission()` 检查
4. 任一权限检查失败则抛出 HTTPException(403)
5. 全部通过后返回 User 对象

### _get_current_user 方法

从请求的 Cookie 中读取 `aidp_session`，然后交给 `AuthService.validate_session()` 验证。如果 Cookie 不存在或验证失败则返回 None。

```python
async def _get_current_user(self, request: Request):
    session_token = request.cookies.get("aidp_session")
    if not session_token:
        return None
    from app.services.auth_service import AuthService
    return await AuthService.validate_session(session_token)
```

### _check_permission 方法

权限检查的核心逻辑，支持多级权限判断：

1. **角色 bypass**：admin 和 super_admin 拥有所有权限，直接返回 True
2. **权限解析**：将 `resource:action:scope` 格式的权限字符串拆分为资源、操作和作用域
3. **系统级检查**：`admin` 资源需要 `admin` 角色
4. **项目级检查**：如果请求路径或查询参数中包含 `project_id`，调用 `_check_project_permission()`
5. **个人资源**：`scope=personal` 的资源默认允许
6. **角色默认权限**：根据用户角色（editor/viewer）检查默认权限

```python
async def _check_permission(self, user, permission, request):
    user_role = getattr(user, 'role', None)
    if user_role in ['admin', 'super_admin']:
        return True
    
    parts = permission.split(':')
    resource, action, scope = parts[0], parts[1] if len(parts) > 1 else 'read', parts[2] if len(parts) > 2 else None
    
    if resource == 'admin':
        return user_role == 'admin'
    
    project_id = request.path_params.get('project_id') or request.query_params.get('project_id')
    if project_id:
        return await self._check_project_permission(user, project_id, resource, action)
    if scope == 'personal':
        return True
    return self._check_role_permission(user_role, resource, action)
```

## 5. require_permissions 装饰器

`require_permissions` 是一个快捷函数，将权限列表包装为 FastAPI 的 `Depends`，简化路由定义：

```python
# 定义在 permissions.py:176
def require_permissions(*permissions: str):
    return Depends(PermissionChecker(list(permissions)))

# 使用方式
@router.get("/api/admin/users")
async def list_users(user = Depends(require_permissions("admin:users"))):
    return {"users": [...]}

@router.get("/api/knowledge/bases")
async def list_bases(user = Depends(require_permissions("knowledge:read"))):
    return {"items": [...]}
```

`PermissionChecker` 作为 FastAPI 的依赖类，其 `__call__` 方法自动被 FastAPI 调用，实现声明式权限控制。

## 6. RolePermissionManager

`RolePermissionManager` 类（`permissions.py:188-266`）管理角色与权限的映射关系，从 YAML 配置文件中加载角色权限定义：

```python
class RolePermissionManager:
    def __init__(self):
        self.config = get_permissions_config()
    
    def get_role_permissions(self, role, role_type='project'):
        # 从配置中获取角色的权限列表
        # 支持 system 和 project 两种角色类型
    
    def check_permission_inheritance(self, permission):
        # 检查权限继承关系，如 knowledge:write 继承 knowledge:read
    
    def has_permission(self, user_permissions, required_permission):
        # 检查用户权限列表中是否包含所需权限（支持通配符和继承）
```

## 7. 权限数据结构

权限配置存储在 YAML 文件中，`get_permissions_config()` 负责加载。系统定义了 5 个角色层级：

```yaml
# roles.yaml (概念结构)
roles:
  system:
    super_admin: { permissions: ["*"] }
    admin: { permissions: ["tool:*", "user:*", "model:*", "settings:*"] }
    developer: { permissions: ["tool:*", "model:read", "user:read"] }
    user: { permissions: ["tool:read", "tool:execute", "model:read", "user:read"] }
    readonly: { permissions: ["tool:read", "model:read"] }
  project:
    admin: { permissions: ["*"] }
    editor: { permissions: ["knowledge:*", "memory:*", "skills:*"] }
    viewer: { permissions: ["knowledge:read", "memory:read"] }
```

数据库层面，`Permission` 表存储所有权限定义，`RolePermission` 表作为多对多关联表。

## 8. 安全措施

| 措施 | 实现方式 | 位置 |
|------|----------|------|
| 密码哈希 | bcrypt + pbkdf2_sha256 兼容 | auth_service.py:41-63 |
| Session Token 随机性 | secrets.token_urlsafe(32) | auth_service.py:66 |
| API Key 安全 | SHA256 哈希存储，原始 key 仅创建时返回 | auth_service.py:343-368 |
| SQL 注入防护 | 全程使用 SQLAlchemy ORM 参数化查询 | 所有数据库操作 |
| Cookie 安全 | HTTP-Only Cookie，JavaScript 不可读 | 在响应头设置 |
| 角色层级 | SUPER_ADMIN > ADMIN > DEVELOPER > USER > READONLY | auth_models.py:24-30 |
| 审计日志 | LoginLog 记录所有登录尝试 | auth_service.py:428-444 |
| 会话管理 | 支持登出所有设备和禁用账户 | auth_service.py:184-226 |