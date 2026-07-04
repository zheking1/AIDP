# 安全架构设计文档

---

## 目录

1. [定位与目标](#1-定位与目标)
2. [架构设计](#2-架构设计)
3. [核心组件](#3-核心组件)
4. [数据流](#4-数据流)
5. [API 设计](#5-api-设计)
6. [实施计划](#6-实施计划)

---

## 1. 定位与目标

### 1.1 核心问题

当前系统缺乏安全机制：
- 沙箱无隔离，可入侵宿主机
- 输入无验证，可注入攻击
- API 无鉴权，可未授权访问
- 密钥明文存储，可泄露
- 并发无控制，可数据竞争

### 1.2 解决方案

提供基础安全保障：
- 沙箱隔离：Docker 容器 + 资源限制
- 输入验证：参数校验 + 路径过滤
- API 鉴权：JWT token + 审计日志
- 并发控制：文件级锁 + 修改排队
- 密钥管理：环境变量
- 调用统计：Redis 计数

### 1.3 设计原则

| 原则 | 描述 |
|------|------|
| **最小权限** | 只给必要的权限 |
| **纵深防御** | 多层安全措施 |
| **简单有效** | 避免过度设计 |
| **可观测** | 记录安全事件 |

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         安全架构                                                 │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    沙箱隔离层                                               │ │
│  │                                                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                        │ │
│  │  │  Docker     │  │  资源限制   │  │  网络隔离   │                        │ │
│  │  │  容器       │  │  CPU/内存   │  │  无网络     │                        │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                        │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                         │
│                                         ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    输入验证层                                               │ │
│  │                                                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                        │ │
│  │  │  参数校验   │  │  路径过滤   │  │  命令过滤   │                        │ │
│  │  │  Pydantic   │  │  禁止 ..    │  │  禁止危险   │                        │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                        │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                         │
│                                         ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    API 鉴权层                                               │ │
│  │                                                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                        │ │
│  │  │  JWT        │  │  审计日志   │  │  用户身份   │                        │ │
│  │  │  token      │  │  操作记录   │  │  角色控制   │                        │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                        │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                         │
│                                         ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    并发控制层                                               │ │
│  │                                                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                        │ │
│  │  │  文件级锁   │  │  修改排队   │  │  查询并行   │                        │ │
│  │  │  Lock       │  │  Queue      │  │  无限制     │                        │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                        │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                         │                                         │
│                                         ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    基础设施层                                               │ │
│  │                                                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                        │ │
│  │  │  密钥管理   │  │  调用统计   │  │  监控告警   │                        │ │
│  │  │  环境变量   │  │  Redis      │  │  基础监控   │                        │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                        │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 组件交互

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         组件交互图                                               │
│                                                                                   │
│  AI Agent                                                                        │
│     │                                                                            │
│     │  1. 提交任务                                                               │
│     ▼                                                                            │
│  API 鉴权层                                                                      │
│     │                                                                            │
│     │  2. 验证 JWT token                                                        │
│     │  3. 记录审计日志                                                          │
│     │                                                                            │
│     ▼                                                                            │
│  输入验证层                                                                      │
│     │                                                                            │
│     │  4. 验证参数                                                               │
│     │  5. 过滤路径                                                               │
│     │  6. 过滤命令                                                               │
│     │                                                                            │
│     ▼                                                                            │
│  并发控制层                                                                      │
│     │                                                                            │
│     │  7. 查询：并行执行                                                        │
│     │  8. 修改：排队执行                                                        │
│     │                                                                            │
│     ▼                                                                            │
│  沙箱隔离层                                                                      │
│     │                                                                            │
│     │  9. Docker 容器执行                                                       │
│     │  10. 资源限制                                                              │
│     │  11. 网络隔离                                                              │
│     │                                                                            │
│     ▼                                                                            │
│  工具执行                                                                        │
│     │                                                                            │
│     │  12. 返回结果                                                              │
│     │                                                                            │
│     ▼                                                                            │
│  AI Agent                                                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心组件

### 3.1 沙箱隔离

```python
# app/security/sandbox.py

class SandboxIsolation:
    """沙箱隔离"""
    
    def __init__(self):
        self.docker = docker.from_env()
    
    async def execute(self, code: str, language: str) -> ExecutionResult:
        """在沙箱中执行代码"""
        
        # 构建容器配置
        container_config = {
            "image": self.get_image(language),
            "command": self.get_command(code, language),
            "network_mode": "none",  # 无网络
            "mem_limit": "512m",     # 内存限制
            "cpu_quota": 50000,      # CPU 限制
            "read_only": True,       # 只读文件系统
            "tmpfs": {"/tmp": "size=100m"},  # 临时目录
            "remove": True           # 执行后删除
        }
        
        # 执行容器
        container = self.docker.containers.run(**container_config)
        
        # 获取结果
        logs = container.logs().decode("utf-8")
        exit_code = container.attrs["State"]["ExitCode"]
        
        return ExecutionResult(
            stdout=logs,
            stderr="",
            exit_code=exit_code
        )
    
    def get_image(self, language: str) -> str:
        """获取镜像"""
        images = {
            "python": "python:3.13-slim",
            "node": "node:20-slim",
            "bash": "bash:5"
        }
        return images.get(language, "python:3.13-slim")
    
    def get_command(self, code: str, language: str) -> str:
        """获取执行命令"""
        if language == "python":
            return f"python -c '{code}'"
        elif language == "node":
            return f"node -e '{code}'"
        elif language == "bash":
            return f"bash -c '{code}'"
        return f"python -c '{code}'"
```

### 3.2 输入验证

```python
# app/security/validation.py

class InputValidator:
    """输入验证器"""
    
    # 危险命令
    FORBIDDEN_COMMANDS = ["rm", "dd", "mkfs", "wget", "curl", "nc", "netcat"]
    
    # 危险字符
    DANGEROUS_CHARS = [";", "&&", "||", "|", "`", "$", "(", ")"]
    
    def validate_path(self, path: str) -> bool:
        """验证路径安全"""
        # 禁止 ..
        if ".." in path:
            return False
        # 禁止绝对路径
        if path.startswith("/"):
            return False
        # 禁止危险字符
        for char in self.DANGEROUS_CHARS:
            if char in path:
                return False
        return True
    
    def validate_command(self, cmd: str) -> bool:
        """验证命令安全"""
        # 检查危险命令
        for forbidden in self.FORBIDDEN_COMMANDS:
            if forbidden in cmd:
                return False
        # 检查危险字符
        for char in self.DANGEROUS_CHARS:
            if char in cmd:
                return False
        return True
    
    def validate_code(self, code: str) -> bool:
        """验证代码安全"""
        # 检查危险导入
        dangerous_imports = ["os.system", "subprocess", "eval", "exec"]
        for imp in dangerous_imports:
            if imp in code:
                return False
        return True
```

### 3.3 API 鉴权

```python
# app/security/auth.py

class APIAuth:
    """API 鉴权"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    def create_token(self, user_id: int, role: str) -> str:
        """创建 token"""
        payload = {
            "user_id": user_id,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_token(self, token: str) -> dict:
        """验证 token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def require_role(self, role: str):
        """要求角色"""
        def decorator(func):
            async def wrapper(request: Request, *args, **kwargs):
                user = request.state.user
                if user["role"] != role and user["role"] != "admin":
                    return JSONResponse(
                        status_code=403,
                        content={"error": "权限不足"}
                    )
                return await func(request, *args, **kwargs)
            return wrapper
        return decorator
```

### 3.4 审计日志

```python
# app/security/audit.py

class AuditLogger:
    """审计日志"""
    
    def __init__(self, db):
        self.db = db
    
    async def log(self, event: AuditEvent):
        """记录审计事件"""
        await self.db.execute("""
            INSERT INTO audit_logs (user_id, action, resource, details, ip, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            event.user_id,
            event.action,
            event.resource,
            event.details,
            event.ip,
            datetime.now()
        ))
    
    async def query(self, filters: dict) -> List[AuditEvent]:
        """查询审计日志"""
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        
        if "user_id" in filters:
            query += " AND user_id = ?"
            params.append(filters["user_id"])
        
        if "action" in filters:
            query += " AND action = ?"
            params.append(filters["action"])
        
        if "start_time" in filters:
            query += " AND created_at >= ?"
            params.append(filters["start_time"])
        
        if "end_time" in filters:
            query += " AND created_at <= ?"
            params.append(filters["end_time"])
        
        return await self.db.fetch_all(query, params)
```

### 3.5 并发控制

```python
# app/security/concurrency.py

class ConcurrencyController:
    """并发控制器"""
    
    def __init__(self):
        self.file_locks: Dict[str, asyncio.Lock] = {}
        self.modification_queue = asyncio.Queue()
    
    async def acquire_lock(self, file_path: str):
        """获取文件锁"""
        if file_path not in self.file_locks:
            self.file_locks[file_path] = asyncio.Lock()
        await self.file_locks[file_path].acquire()
    
    async def release_lock(self, file_path: str):
        """释放文件锁"""
        if file_path in self.file_locks:
            self.file_locks[file_path].release()
    
    async def submit_modification(self, task: Callable, file_path: str):
        """提交修改任务"""
        await self.acquire_lock(file_path)
        try:
            await task()
        finally:
            await self.release_lock(file_path)
    
    async def query_parallel(self, tasks: List[Callable]) -> List:
        """并行查询"""
        results = await asyncio.gather(*[task() for task in tasks])
        return results
```

### 3.6 密钥管理

```python
# app/security/secrets.py

class SecretManager:
    """密钥管理"""
    
    def __init__(self):
        self.secrets = {}
    
    def load_from_env(self):
        """从环境变量加载"""
        self.secrets = {
            "LLM_API_KEY": os.getenv("LLM_API_KEY"),
            "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN"),
            "DB_PASSWORD": os.getenv("DB_PASSWORD"),
            "JWT_SECRET": os.getenv("JWT_SECRET")
        }
    
    def get(self, key: str) -> str:
        """获取密钥"""
        return self.secrets.get(key)
    
    def set(self, key: str, value: str):
        """设置密钥"""
        self.secrets[key] = value
```

### 3.7 调用统计

```python
# app/security/stats.py

class CallStats:
    """调用统计"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def record(self, tool: str, user_id: int, tokens: int = 0):
        """记录调用"""
        date = datetime.now().strftime("%Y-%m-%d")
        
        # 调用次数
        await self.redis.hincrby(f"stats:{tool}:calls:{date}", user_id, 1)
        
        # Token 用量
        if tokens > 0:
            await self.redis.hincrby(f"stats:{tool}:tokens:{date}", user_id, tokens)
    
    async def get_tool_stats(self, tool: str, date: str = None) -> dict:
        """获取工具统计"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        calls = await self.redis.hgetall(f"stats:{tool}:calls:{date}")
        tokens = await self.redis.hgetall(f"stats:{tool}:tokens:{date}")
        
        return {
            "calls": {k: int(v) for k, v in calls.items()},
            "tokens": {k: int(v) for k, v in tokens.items()}
        }
    
    async def get_all_stats(self, date: str = None) -> dict:
        """获取所有统计"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        tools = ["knowledge", "code-index", "sandbox", "quality", "memory"]
        stats = {}
        
        for tool in tools:
            stats[tool] = await self.get_tool_stats(tool, date)
        
        return stats
```

---

## 4. 数据流

### 4.1 请求流

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         请求流                                                   │
│                                                                                   │
│  1. AI Agent 提交任务                                                            │
│     │                                                                            │
│     ▼                                                                            │
│  2. API 鉴权层                                                                   │
│     │                                                                            │
│     │  验证 JWT token                                                            │
│     │  记录审计日志                                                              │
│     │                                                                            │
│     ▼                                                                            │
│  3. 输入验证层                                                                   │
│     │                                                                            │
│     │  验证参数                                                                  │
│     │  过滤路径                                                                  │
│     │  过滤命令                                                                  │
│     │                                                                            │
│     ▼                                                                            │
│  4. 并发控制层                                                                   │
│     │                                                                            │
│     │  查询：并行执行                                                            │
│     │  修改：排队执行                                                            │
│     │                                                                            │
│     ▼                                                                            │
│  5. 沙箱隔离层                                                                   │
│     │                                                                            │
│     │  Docker 容器执行                                                           │
│     │  资源限制                                                                  │
│     │  网络隔离                                                                  │
│     │                                                                            │
│     ▼                                                                            │
│  6. 工具执行                                                                     │
│     │                                                                            │
│     │  返回结果                                                                  │
│     │                                                                            │
│     ▼                                                                            │
│  7. 调用统计                                                                     │
│     │                                                                            │
│     │  记录调用次数                                                              │
│     │  记录 Token 用量                                                          │
│     │                                                                            │
│     ▼                                                                            │
│  8. AI Agent                                                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. API 设计

### 5.1 认证 API

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

# 刷新 token
POST /api/auth/refresh
{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

Response:
{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 5.2 审计日志 API

```
# 查询审计日志
GET /api/audit?user_id=1&action=execute&start_time=2024-01-01&end_time=2024-01-31

Response:
{
    "logs": [
        {
            "id": 1,
            "user_id": 1,
            "action": "execute",
            "resource": "sandbox",
            "details": "执行 Python 代码",
            "ip": "192.168.0.100",
            "created_at": "2024-01-15T10:30:00Z"
        }
    ],
    "total": 100
}
```

### 5.3 调用统计 API

```
# 获取调用统计
GET /api/stats?date=2024-01-15

Response:
{
    "knowledge": {
        "calls": {"1": 10, "2": 5},
        "tokens": {"1": 5000, "2": 2500}
    },
    "code-index": {
        "calls": {"1": 8, "2": 3},
        "tokens": {"1": 4000, "2": 1500}
    }
}
```

### 5.4 用户管理 API

```
# 用户列表
GET /api/users

Response:
{
    "users": [
        {
            "id": 1,
            "username": "admin",
            "role": "admin",
            "created_at": "2024-01-01T00:00:00Z"
        }
    ]
}

# 创建用户
POST /api/users
{
    "username": "user1",
    "password": "password123",
    "role": "user"
}

Response:
{
    "id": 2,
    "username": "user1",
    "role": "user"
}
```

---

## 6. 实施计划

### 6.1 Phase 1: 基础安全（P0）

**周期**: 1 周（5 天）

**任务**:
- 沙箱隔离（Docker）
- 输入验证（参数校验）
- API 鉴权（JWT）
- 审计日志

**验收标准**:
- [ ] 代码在 Docker 容器中执行
- [ ] 参数验证有效
- [ ] JWT 认证工作
- [ ] 审计日志记录

### 6.2 Phase 2: 并发控制（P1）

**周期**: 0.5 周（2-3 天）

**任务**:
- 文件级锁
- 修改排队
- 查询并行

**验收标准**:
- [ ] 文件锁有效
- [ ] 修改排队工作
- [ ] 查询并行工作

### 6.3 Phase 3: 统计和管理（P2）

**周期**: 0.5 周（2-3 天）

**任务**:
- 调用统计
- 用户管理
- 密钥管理

**验收标准**:
- [ ] 调用统计准确
- [ ] 用户管理工作
- [ ] 密钥安全存储

---

## 附录

### A. 配置项

```python
# app/config.py

class SecurityConfig:
    # JWT 配置
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key")
    JWT_EXPIRATION: int = 24 * 60 * 60  # 24 小时
    
    # 沙箱配置
    SANDBOX_IMAGE: str = "python:3.13-slim"
    SANDBOX_MEMORY_LIMIT: str = "512m"
    SANDBOX_CPU_QUOTA: int = 50000
    SANDBOX_NETWORK_MODE: str = "none"
    
    # 输入验证
    FORBIDDEN_COMMANDS: list = ["rm", "dd", "mkfs", "wget", "curl"]
    DANGEROUS_CHARS: list = [";", "&&", "||", "|", "`", "$", "(", ")"]
    
    # 调用统计
    STATS_RETENTION_DAYS: int = 30
```

### B. 数据模型

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 审计日志表
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    resource TEXT,
    details TEXT,
    ip TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 调用统计表
CREATE TABLE call_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool TEXT NOT NULL,
    user_id INTEGER,
    tokens INTEGER DEFAULT 0,
    date TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
