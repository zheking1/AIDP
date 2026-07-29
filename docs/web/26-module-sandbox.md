# Sandbox Module — 代码沙箱模块

## 1. 模块概述

Sandbox（代码沙箱）模块提供**安全的代码执行环境**，支持 Python、Bash、Shell 三种语言的代码在线执行。用户可以在浏览器中编写和运行代码，查看标准输出、标准错误和退出码，适用于代码测试、快速原型验证和教学演示。

模块定义文件位于 `apps/controller/app/modules/sandbox/__init__.py`：

```python
@register_module(name='sandbox', enabled=True)
class SandboxModule(BaseModule):
    """
    代码沙箱模块
    提供安全的代码执行环境，支持 Python/Bash/Shell
    注意: 沙箱执行应保持独立容器部署（安全隔离）
    """
    name = "sandbox"
    description = "代码沙箱执行，支持 Python/Bash/Shell"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as sandbox_router
        app.include_router(sandbox_router, prefix="/api/sandbox")
```

模块没有外部依赖（`dependencies = []`），可以独立部署运行。

## 2. 数据模型

只有一个模型 `Execution`，定义在 `apps/controller/app/modules/sandbox/models.py`：

```python
class Execution(Base):
    """代码执行记录模型"""
    __tablename__ = "aidp_executions"

    id           = Column(String(36), primary_key=True, default=gen_uuid)
    project_id   = Column(Integer, nullable=True, index=True)
    user_id      = Column(String(100), nullable=True, index=True)
    language     = Column(String(20), nullable=False, default="python")
    # python, bash, sh
    code         = Column(Text, nullable=False)
    stdin        = Column(Text, nullable=True)
    stdout       = Column(Text, nullable=True)
    stderr       = Column(Text, nullable=True)
    exit_code    = Column(Integer, nullable=True)
    timed_out    = Column(Boolean, default=False)
    duration_ms  = Column(Float, nullable=True)
    status       = Column(String(20), default="pending", index=True)
    # pending, running, completed, failed, timeout
    created_at   = Column(DateTime(timezone=True), default=utcnow, index=True)
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| project_id | Integer | 所属项目 ID（可选） |
| user_id | String(100) | 执行用户 ID |
| language | String(20) | 语言：python / bash / sh |
| code | Text | 执行的源代码 |
| stdin | Text | 标准输入 |
| stdout | Text | 标准输出 |
| stderr | Text | 标准错误 |
| exit_code | Integer | 进程退出码 |
| timed_out | Boolean | 是否超时 |
| duration_ms | Float | 执行耗时（毫秒） |
| status | String(20) | 状态：pending / running / completed / failed / timeout |
| created_at | DateTime | 创建时间 |

`to_dict()` 方法提供可选的 `include_code` 参数（默认 `True`），在返回历史列表时通常设为 `False` 以保护代码内容隐私。

## 3. API 端点

所有路由定义在 `apps/controller/app/modules/sandbox/routes.py` 中，前缀为 `/api/sandbox`。

### 核心端点

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | `/api/sandbox/execute` | 执行代码 | sandbox:execute |
| GET | `/api/sandbox/history` | 执行历史 | 登录用户 |
| GET | `/api/sandbox/stats` | 执行统计 | 登录用户 |

### 请求/响应模型

```python
class ExecutionRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = Field("python", description="python, bash, sh")
    stdin: Optional[str] = None
    timeout: int = Field(EXECUTION_TIMEOUT, ge=1, le=120)
```

### POST /api/sandbox/execute 响应示例

```json
{
    "id": "uuid-string",
    "project_id": null,
    "user_id": "user-123",
    "language": "python",
    "code": "print('hello')\n",
    "stdin": null,
    "stdout": "hello\n",
    "stderr": "",
    "exit_code": 0,
    "timed_out": false,
    "duration_ms": 45.2,
    "status": "completed",
    "created_at": "2026-07-13T10:00:00+00:00"
}
```

## 4. 执行流程

执行逻辑在 `_execute_code` 协程函数中实现，完整流程如下：

### 4.1 语言验证

```python
LANGUAGE_MAP = {
    "python": {"ext": ".py", "cmd": "python3", "flag": "-u"},
    "bash":   {"ext": ".sh", "cmd": "bash",   "flag": ""},
    "sh":     {"ext": ".sh", "cmd": "sh",     "flag": ""},
}
EXECUTION_TIMEOUT = 30
EXECUTION_MAX_OUTPUT = 10240    # 10KB
```

### 4.2 执行入口

```python
@router.post("/execute")
async def execute_code(data: ExecutionRequest, ...):
    # 1. 创建执行记录（status = "running"）
    execution = Execution(project_id=project_id, user_id=user_id,
        language=data.language, code=data.code,
        stdin=data.stdin, status="running")
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # 2. 执行代码
    start = time.time()
    result = await _execute_code(data.code, data.language, data.stdin, data.timeout)
    duration_ms = (time.time() - start) * 1000

    # 3. 更新结果
    execution.stdout = result["stdout"]
    execution.stderr = result["stderr"]
    execution.exit_code = result["exit_code"]
    execution.timed_out = result["timed_out"]
    execution.duration_ms = duration_ms
    execution.status = "timeout" if result["timed_out"] \
        else ("completed" if result["exit_code"] == 0 else "failed")

    await db.commit()
    return execution.to_dict()
```

### 4.3 核心执行函数

```python
async def _execute_code(code, language, stdin_data=None, timeout=EXECUTION_TIMEOUT):
    # 1. 写入临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix=lang_config["ext"],
                                     delete=False, encoding='utf-8') as f:
        f.write(code)
        temp_path = f.name

    try:
        # 2. 构建命令
        cmd = [lang_config["cmd"]]
        if lang_config["flag"]:
            cmd.append(lang_config["flag"])
        cmd.append(temp_path)

        # 3. 启动子进程
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        # 4. 执行并等待（超时控制）
        try:
            stdin_bytes = stdin_data.encode() if stdin_data else None
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin_bytes), timeout=timeout)
            timed_out = False
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            stdout = b""
            stderr = f"Execution timed out after {timeout}s".encode()
            timed_out = True

        # 5. 截断输出（防止过大数据）
        stdout_str = stdout.decode('utf-8', errors='replace')[:EXECUTION_MAX_OUTPUT]
        stderr_str = stderr.decode('utf-8', errors='replace')[:EXECUTION_MAX_OUTPUT]

        return {
            "stdout": stdout_str, "stderr": stderr_str,
            "exit_code": process.returncode if not timed_out else -1,
            "timed_out": timed_out, "duration_ms": 0
        }
    finally:
        os.unlink(temp_path)  # 清理临时文件
```

**执行流程总结：**

```
用户代码 → 写入临时文件 → asyncio.create_subprocess_exec → 子进程执行
    → 捕获 stdout/stderr → 超时控制（asyncio.wait_for）
    → 更新数据库记录 → 返回结果给前端
```

## 5. 安全措施

### 5.1 超时控制

- 默认超时：**30 秒**
- 最大超时：**120 秒**
- 超时后强制 `process.kill()`，设置 `timed_out = True`
- 超时的 `exit_code` 设为 `-1`

```python
EXECUTION_TIMEOUT = 30
# 请求体中 timeout 字段范围: ge=1, le=120
```

### 5.2 语言白名单

仅支持三种语言，通过 `LANGUAGE_MAP` 严格限定：

```python
LANGUAGE_MAP = {
    "python": {"ext": ".py", "cmd": "python3", "flag": "-u"},
    "bash":   {"ext": ".sh", "cmd": "bash",    "flag": ""},
    "sh":     {"ext": ".sh", "cmd": "sh",      "flag": ""},
}
```

不支持的 language 返回 400 错误：`"Unsupported language: {language}"`

### 5.3 输出截断

标准输出和标准错误均截断为 **10,240 字节**（约 10KB），防止恶意代码产生海量输出：

```python
EXECUTION_MAX_OUTPUT = 10240
stdout_str = stdout.decode('utf-8', errors='replace')[:EXECUTION_MAX_OUTPUT]
```

### 5.4 临时文件安全

- 使用 `tempfile.NamedTemporaryFile` 创建临时文件
- `finally` 块中调用 `os.unlink()` 确保删除
- 临时文件路径不暴露给用户

### 5.5 备注

模块注释中指出：**沙箱执行应保持独立容器部署（安全隔离）**。当前的实现是应用层隔离，生产环境建议配合 Docker/k8s 容器隔离使用。

## 6. 前端

前端模板位于 `apps/controller/app/web/templates/modules/sandbox/index_content.html`，使用 Alpine.js 管理状态。

### 核心 Alpine 组件：`sandboxPage()`

```javascript
window.sandboxPage = function sandboxPage() {
    return {
        code: '',                 // 代码内容
        language: 'python',       // 语言选择
        stdin: '',                // 标准输入
        running: false,           // 是否正在执行
        lastResult: null,         // 上次执行结果
        history: [],              // 执行历史

        async init() { await this.loadHistory(); },

        async runCode() {
            if (!this.code.trim() || this.running) return;
            this.running = true;
            try {
                const res = await fetch('/api/sandbox/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        code: this.code,
                        language: this.language,
                        stdin: this.stdin || null
                    })
                });
                if (res.ok) {
                    this.lastResult = await res.json();
                    await this.loadHistory();
                }
            } catch(e) { console.error(e); }
            finally { this.running = false; }
        },

        async loadHistory() {
            const res = await fetch('/api/sandbox/history?limit=10');
            if (res.ok) { const data = await res.json(); this.history = data.items || []; }
        }
    };
};
```

### 关键 UI 元素

| UI 元素 | 说明 |
|---------|------|
| **语言下拉框** | 选择 Python / Bash / Shell |
| **运行按钮** | 执行代码，运行时显示旋转图标和"执行中..." |
| **代码编辑器** | 等宽字体、绿色文字、支持 Ctrl+Enter 快捷键 |
| **标准输入** | 可选的标准输入文本框 |
| **输出面板** | 分 stdout（绿色）和 stderr（红色）显示 |
| **执行信息** | 显示耗时（ms）和超时警告 |
| **执行历史** | 最近 10 条执行记录的简化列表 |

### 交互特性

- `Ctrl+Enter` 快捷键快速运行
- 运行时按钮 disabled 防止重复提交
- 输出面板自动区分 stdout（绿色）和 stderr（红色）
- 执行历史按时间倒序排列，每条显示语言、耗时、退出码