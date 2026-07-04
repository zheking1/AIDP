# 安全开发计划

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术选型](#2-技术选型)
3. [Phase 1: 基础安全](#3-phase-1-基础安全)
4. [Phase 2: 并发控制](#4-phase-2-并发控制)
5. [Phase 3: 统计和管理](#5-phase-3-统计和管理)
6. [风险评估](#6-风险评估)
7. [资源需求](#7-资源需求)

---

## 1. 项目概述

### 1.1 项目范围

为 AIDP 系统提供基础安全保障。

### 1.2 项目目标

- 沙箱隔离：Docker 容器 + 资源限制
- 输入验证：参数校验 + 路径过滤
- API 鉴权：JWT token + 审计日志
- 并发控制：文件级锁 + 修改排队
- 密钥管理：环境变量
- 调用统计：Redis 计数

### 1.3 项目周期

- Phase 1: 1 周（基础安全）
- Phase 2: 0.5 周（并发控制）
- Phase 3: 0.5 周（统计和管理）
- **总计: 2 周**

---

## 2. 技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| **沙箱** | Docker | 成熟的容器化方案 |
| **输入验证** | Pydantic | FastAPI 内置 |
| **JWT** | PyJWT | 成熟的 JWT 库 |
| **审计日志** | SQLite | 轻量级 |
| **并发控制** | asyncio | Python 异步 |
| **密钥管理** | 环境变量 | 简单有效 |
| **调用统计** | Redis | 高性能 |

---

## 3. Phase 1: 基础安全（P0）

**周期**: 1 周（5 天）

### 3.1 目标

能执行代码、验证输入、认证用户、记录审计。

### 3.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 沙箱隔离（Docker） | 1.5 天 | 无 |
| 输入验证（参数校验） | 1 天 | 无 |
| API 鉴权（JWT） | 1.5 天 | 无 |
| 审计日志 | 1 天 | 鉴权 |

### 3.3 技术实现

**沙箱隔离**:
```python
# app/security/sandbox.py

class SandboxIsolation:
    """沙箱隔离"""
    
    def __init__(self):
        self.docker = docker.from_env()
    
    async def execute(self, code: str, language: str) -> ExecutionResult:
        """在沙箱中执行代码"""
        
        container_config = {
            "image": self.get_image(language),
            "command": self.get_command(code, language),
            "network_mode": "none",
            "mem_limit": "512m",
            "cpu_quota": 50000,
            "read_only": True,
            "tmpfs": {"/tmp": "size=100m"},
            "remove": True
        }
        
        container = self.docker.containers.run(**container_config)
        logs = container.logs().decode("utf-8")
        exit_code = container.attrs["State"]["ExitCode"]
        
        return ExecutionResult(
            stdout=logs,
            stderr="",
            exit_code=exit_code
        )
```

**输入验证**:
```python
# app/security/validation.py

class InputValidator:
    """输入验证器"""
    
    FORBIDDEN_COMMANDS = ["rm", "dd", "mkfs", "wget", "curl"]
    DANGEROUS_CHARS = [";", "&&", "||", "|", "`", "$", "(", ")"]
    
    def validate_path(self, path: str) -> bool:
        """验证路径安全"""
        if ".." in path:
            return False
        if path.startswith("/"):
            return False
        for char in self.DANGEROUS_CHARS:
            if char in path:
                return False
        return True
    
    def validate_command(self, cmd: str) -> bool:
        """验证命令安全"""
        for forbidden in self.FORBIDDEN_COMMANDS:
            if forbidden in cmd:
                return False
        for char in self.DANGEROUS_CHARS:
            if char in cmd:
                return False
        return True
```

**API 鉴权**:
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
```

**审计日志**:
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
```

### 3.4 验收标准

- [ ] 代码在 Docker 容器中执行
- [ ] 参数验证有效
- [ ] JWT 认证工作
- [ ] 审计日志记录

---

## 4. Phase 2: 并发控制（P1）

**周期**: 0.5 周（2-3 天）

### 4.1 目标

文件锁有效，修改排队工作，查询并行工作。

### 4.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 文件级锁 | 1 天 | Phase 1 |
| 修改排队 | 1 天 | 文件锁 |
| 查询并行 | 0.5 天 | Phase 1 |

### 4.3 技术实现

**并发控制**:
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

### 4.4 验收标准

- [ ] 文件锁有效
- [ ] 修改排队工作
- [ ] 查询并行工作

---

## 5. Phase 3: 统计和管理（P2）

**周期**: 0.5 周（2-3 天）

### 5.1 目标

调用统计准确，用户管理工作，密钥安全存储。

### 5.2 任务清单

| 任务 | 估时 | 依赖 |
|------|------|------|
| 调用统计 | 1 天 | Phase 1 |
| 用户管理 | 1 天 | Phase 1 |
| 密钥管理 | 0.5 天 | 无 |

### 5.3 技术实现

**调用统计**:
```python
# app/security/stats.py

class CallStats:
    """调用统计"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def record(self, tool: str, user_id: int, tokens: int = 0):
        """记录调用"""
        date = datetime.now().strftime("%Y-%m-%d")
        await self.redis.hincrby(f"stats:{tool}:calls:{date}", user_id, 1)
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
```

**用户管理**:
```python
# app/security/users.py

class UserManager:
    """用户管理"""
    
    def __init__(self, db):
        self.db = db
    
    async def create_user(self, username: str, password: str, role: str = "user"):
        """创建用户"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        await self.db.execute("""
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
        """, (username, password_hash, role))
    
    async def verify_user(self, username: str, password: str) -> dict:
        """验证用户"""
        user = await self.db.fetch_one("""
            SELECT * FROM users WHERE username = ?
        """, (username,))
        
        if not user:
            return None
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user["password_hash"] != password_hash:
            return None
        
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"]
        }
```

### 5.4 验收标准

- [ ] 调用统计准确
- [ ] 用户管理工作
- [ ] 密钥安全存储

---

## 6. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **Docker 未安装** | 中 | 高 | 提供安装文档 |
| **JWT 密钥泄露** | 低 | 高 | 环境变量存储 |
| **审计日志丢失** | 低 | 中 | 定期备份 |

---

## 7. 资源需求

### 7.1 开发资源

| 资源 | 数量 | 说明 |
|------|------|------|
| **开发人员** | 1 人 | Python + FastAPI |
| **开发环境** | 1 套 | 本地开发 |
| **测试环境** | 1 套 | NAS 部署 |

### 7.2 基础设施

| 资源 | 规格 | 说明 |
|------|------|------|
| **NAS** | 192.168.0.100 | 部署环境 |
| **Docker** | latest | 沙箱执行 |
| **Redis** | 192.168.0.100:6379 | 调用统计 |

### 7.3 依赖关系

| 依赖 | 版本 | 说明 |
|------|------|------|
| **Python** | 3.13 | 运行环境 |
| **FastAPI** | latest | Web 框架 |
| **Docker** | latest | 沙箱执行 |
| **PyJWT** | latest | JWT 认证 |
| **Redis** | latest | 调用统计 |
