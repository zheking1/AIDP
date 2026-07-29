# Sandbox Tool 概述

## 基本信息

| 属性 | 值 |
|------|-----|
| 服务名 | `sandbox-tool` |
| 端口 | `18083` (配置: `tools/sandbox-tool/app/config.py:10`) |
| 框架 | FastAPI (async) |
| 数据库 | PostgreSQL (SQLAlchemy 2.0 async) |
| 表名 | `sb_execution` |
| 容器名 | `aidp-sandbox` |
| 容器镜像 | `aidp/sandbox-tool:0.1.0` |
| Dockerfile | `tools/sandbox-tool/Dockerfile` |

## 目录结构

```
tools/sandbox-tool/app/
├── __init__.py
├── main.py                         # FastAPI 应用入口
├── config.py                       # 配置 (Pydantic Settings)
├── api/
│   ├── __init__.py
│   ├── health.py                   # /health 健康检查
│   ├── execute.py                  # /api/execute 执行代码
│   └── tool.py                     # /tool/manifest, /tool/capabilities, /tool/invoke
├── services/
│   ├── __init__.py
│   ├── execution_service.py        # 代码执行核心逻辑
│   └── sandbox_modules.py          # 辅助模块 (容器池/安全/超时/上下文)
├── db/
│   ├── __init__.py
│   ├── models.py                   # Execution 模型
│   └── init_db.py                  # 数据库初始化
└── web/
    ├── __init__.py
    └── routes.py                   # Web UI 路由 (通过 Controller 代理)
```

## 架构概览

```
POST /tool/invoke
    ↓
ApiRouter (api/tool.py)
    ↓
ExecutionService (services/execution_service.py)
    ├── SecurityEngine.check()     → 安全检查 (sandbox_modules.py:80-110)
    ├── 写入 /tmp 文件
    ├── asyncio.create_subprocess_exec() → 子进程执行
    ├── TimeoutManager (asyncio.wait_for)
    └── ContainerPool (容器资源管理)
    ↓
PostgreSQL (sb_execution 表) → 记录执行历史
    ↓
返回 {stdout, stderr, exitCode, timedOut, durationMs}
```

## 支持的语言

**源文件**: `tools/sandbox-tool/app/services/execution_service.py:12-16`

| 语言 | 文件扩展 | 执行命令 |
|------|---------|---------|
| `python` | `.py` | `python3 -u` (无缓冲模式) |
| `bash` | `.sh` | `bash` |
| `sh` | `.sh` | `sh` |

### 请求参数

```json
{
    "code": "print('Hello, World!')",
    "language": "python",
    "stdin": "optional standard input",
    "userId": 123
}
```

### 响应格式

```json
{
    "id": 1,
    "language": "python",
    "stdout": "Hello, World!\n",
    "stderr": "",
    "exitCode": 0,
    "timedOut": false,
    "durationMs": 42
}
```

## 核心安全机制

### SecurityEngine (`sandbox_modules.py:80-110`)

在代码执行前进行安全扫描，检测危险函数和模式:

#### 危险函数列表 (`sandbox_modules.py:83-85`)

**Python**:
```
exec, eval, compile, __import__, open, os.system, subprocess.call, socket, urllib
```

**JavaScript** (预留):
```
eval, Function, setTimeout, setInterval, require, fetch
```

#### 危险模式检测 (`sandbox_modules.py:88-90`)

```
__.*__              # 双下划线属性
import\s+os         # 导入 os 模块
os\.system\(        # os.system() 调用
subprocess\.        # subprocess 调用
exec\(              # exec() 调用
eval\(              # eval() 调用
```

#### 资源限制检测

- 代码行数超过 1000 行 → `severity: low` 警告

#### 威胁等级判定

| 高危函数数 | 威胁等级 |
|-----------|---------|
| > 0 | `critical` |
| 0 (有警告) | `medium` |
| 无问题 | `none` |

**重要**: 当前安全扫描仅做检测和报告，**不阻止代码执行**。发现危险函数时返回 `passed: false` 的报告，但代码仍然会被执行。

## 执行流程详解

**源文件**: `tools/sandbox-tool/app/services/execution_service.py:19-91`

```
1. 语言验证: 检查是否在 SUPPORTED_LANGUAGES 中
2. 文件写入: 写入代码到 /tmp/sandbox_exec.{ext}
3. 子进程创建: asyncio.create_subprocess_exec(cmd, tmp_file)
   - stdin: 如果提供了 stdin, 使用 PIPE; 否则 DEVNULL
   - stdout: PIPE
   - stderr: PIPE
4. 超时控制: asyncio.wait_for(proc.communicate(), timeout=30s)
5. 超时处理: proc.kill() → 返回 "Execution timed out"
6. 输出截断: stdout/stderr 限制到 10240 字节
7. 结果存储: 写入 PostgreSQL sb_execution 表
8. 返回结果: {id, language, stdout, stderr, exitCode, timedOut, durationMs}
```

## 配置参数

**源文件**: `tools/sandbox-tool/app/config.py`

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `EXECUTION_TIMEOUT` | `30` | 执行超时 (秒) |
| `EXECUTION_MAX_OUTPUT` | `10240` | 输出最大字节数 (10KB) |
| `APP_NAME` | `sandbox-tool` | 服务名 |
| `APP_VERSION` | `0.1.0` | 服务版本 |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `18083` | 监听端口 |

## 超时管理 (TimeoutManager)

**源文件**: `tools/sandbox-tool/app/services/sandbox_modules.py:113-137`

```python
class TimeoutManager:
    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.timeout_history = []

    async def execute(self, func, task_id: str, timeout: int = 30) -> Dict:
        # 创建 asyncio.Task → wait_for(timeout) → 超时则 cancel
        # 记录到 timeout_history
```

## 容器池管理 (ContainerPool)

**源文件**: `tools/sandbox-tool/app/services/sandbox_modules.py:18-78`

模拟的容器池管理器 (当前不使用真实 Docker 容器):

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `min_size` | 5 | 最小容器数 |
| `max_size` | 20 | 最大容器数 |
| `idle_timeout` | 300 | 空闲超时 (秒) |

核心方法:
- `initialize()`: 创建 min_size 个容器 (当前使用模拟 ID: `pooled-{i}-{timestamp}`)
- `acquire()`: 获取空闲容器，标记为 busy; 无可用时等待最多 3 秒
- `release()`: 释放容器，标记为 ready
- `cleanup_loop()`: 每 60 秒清理超时空闲容器并补充
- `get_stats()`: 返回 `{total, ready, busy}`

**注意**: `ContainerPool` 当前使用模拟的容器 ID，并未实际连接 Docker daemon。容器参数 (memory_limit=128MB, cpu_limit=0.5) 是预留配置。

## 执行上下文管理 (ContextManager)

**源文件**: `tools/sandbox-tool/app/services/sandbox_modules.py:140-166`

```python
contexts: Dict[str, dict]  # task_id → context

create(task_id, user_id, project_id, language) → Dict  # 创建上下文
get(task_id) → Optional[Dict]                             # 获取上下文
add_variable(task_id, name, value) → bool                 # 添加变量
close(task_id) → bool                                     # 关闭上下文
```

上下文结构:
```python
{
    "task_id": str,
    "user_id": str,
    "project_id": str,
    "language": str,
    "variables": {},
    "imports": [],
    "output": [],
    "errors": [],
    "status": "created"  # → "closed"
}
```

## 数据库模型

**源文件**: `tools/sandbox-tool/app/db/models.py:14-28`

### Execution 表 (`sb_execution`)

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | Integer PK | 自增主键 |
| `user_id` | Integer (索引) | 用户 ID |
| `language` | String(32) (索引) | 编程语言 |
| `code` | Text | 原始代码 |
| `stdin` | Text (可空) | 标准输入 |
| `stdout` | Text (可空) | 标准输出 |
| `stderr` | Text (可空) | 标准错误 |
| `exit_code` | Integer (可空) | 退出码 |
| `timed_out` | Boolean | 是否超时 |
| `created_at` | DateTime | 执行时间 |
| `duration_ms` | Integer (可空) | 执行耗时 (毫秒) |

## API 端点

### Tool MCP 接口 (`api/tool.py`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/tool/manifest` | GET | 工具元数据 (名称、描述、Docker 镜像) |
| `/tool/capabilities` | GET | 能力列表 (含 input/output schema) |
| `/tool/invoke` | POST | MCP 标准调用入口 |

### 能力列表

| 能力名 | 端点 | 权限 | 超时 |
|--------|------|------|------|
| `sandbox.execute` | `POST /api/execute` | `sandbox:execute` | 35000ms |
| `sandbox.history` | `GET /api/execute/history` | `sandbox:read` | 3000ms |

### 执行 API (`api/execute.py`)

| 端点 | 方法 | 请求体 | 说明 |
|------|------|--------|------|
| `/api/execute` | POST | `{code, language, stdin?, userId?}` | 执行代码 |
| `/api/execute/history` | GET | `?userId=&limit=20` | 获取执行历史 |

### 健康检查 (`api/health.py`)

```
GET /health
→ {"status": "ok", "tool": "sandbox-tool", "version": "0.1.0"}
```

## Web UI (通过 Controller 代理查看)

使用方式: 在 Coach Host Web UI 中访问 `/sandbox`

**模板源文件**: `apps/controller/app/web/templates/modules/sandbox/index.html`

功能:
- 代码编辑器 (textarea, 15 行, 暗色主题, 绿色等宽字体)
- 语言选择: Python / Bash
- 标准输入折叠区
- 执行按钮 (显示 "执行中..." 加载状态)
- 输出面板: 分别显示 stdout (绿色) 和 stderr (红色)，显示 exit code 和耗时
- 执行历史弹窗 (表格: ID/语言/代码/退出码/耗时/时间)
- 历史详情弹窗 (完整代码 + stdout + stderr)

前端直接调用 `/api/sandbox/execute` 和 `/api/sandbox/history` (通过 Controller 转发)。

## 调用示例

### 通过 MCP 调用

```python
invoke_tool_mcp("sandbox-tool", "sandbox.execute",
    '{"code": "print(sum(range(100)))", "language": "python"}')
```

### 直接 HTTP 调用 (开发)

```bash
# Python 代码执行
curl -X POST http://127.0.0.1:18083/tool/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "sandbox.execute",
    "input": {"code": "print(1+1)", "language": "python"}
  }'

# Bash 代码执行
curl -X POST http://127.0.0.1:18083/tool/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "sandbox.execute",
    "input": {"code": "echo hello; ls -la /", "language": "bash"}
  }'

# 查看执行历史
curl -X POST http://127.0.0.1:18083/tool/invoke \
  -H "Content-Type: application/json" \
  -d '{"capability":"sandbox.history","input":{"limit":10}}'
```

### 通过 Controller 代理

```bash
curl http://127.0.0.1:8883/api/proxy/sandbox-tool/api/execute/history?limit=5 \
  -b cookies.txt
```

## 已知限制

1. **/tmp 路径依赖**: 代码写入 `/tmp/sandbox_exec.{ext}`，在 Windows 环境下不适用
2. **容器池为模拟**: `ContainerPool` 使用虚拟容器 ID，未集成 Docker daemon
3. **安全扫描不阻止执行**: `SecurityEngine.check()` 仅返回报告，不阻止危险代码执行
4. **输出截断**: stdout/stderr 被硬截断到 10240 字节，大输出会丢失
5. **无文件系统隔离**: 代码在宿主机进程环境中执行，无容器/Docker 隔离
6. **Python 命令**: 使用 `python3` 而非 `python`，在某些系统上可能不存在

## 关键文件索引

| 文件 | 行数 | 职责 |
|------|------|------|
| `main.py` | 37 | FastAPI 应用入口, 路由注册 |
| `config.py` | 23 | 配置参数 |
| `api/tool.py` | 169 | MCP 调用接口, manifest |
| `api/execute.py` | 28 | 执行代码 + 历史 API |
| `services/execution_service.py` | 112 | 代码执行核心逻辑 |
| `services/sandbox_modules.py` | 166 | 安全/容器/超时/上下文辅助模块 |
| `db/models.py` | 36 | Execution 模型 + Database engine |
| `web/routes.py` | - | Web UI 路由 |