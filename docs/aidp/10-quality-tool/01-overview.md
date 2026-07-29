# Quality Tool 概述

## 基本信息

| 属性 | 值 |
|------|-----|
| 服务名 | `quality-tool` |
| 端口 | `18084` (配置: `tools/quality-tool/app/config.py:10`) |
| 框架 | FastAPI (async) |
| 数据库 | PostgreSQL (SQLAlchemy 2.0 async) |
| 表名 | `ql_check_result` |
| 容器名 | `aidp-quality` |
| 容器镜像 | `aidp/quality-tool:0.1.0` |
| Dockerfile | `tools/quality-tool/Dockerfile` |

## 目录结构

```
tools/quality-tool/app/
├── __init__.py
├── main.py                         # FastAPI 应用入口
├── config.py                       # 配置 (Pydantic Settings)
├── api/
│   ├── __init__.py
│   ├── health.py                   # /health 健康检查
│   ├── check.py                    # /api/check 代码检查
│   └── tool.py                     # /tool/manifest, /tool/capabilities, /tool/invoke
├── services/
│   ├── __init__.py
│   └── quality_service.py          # 检查核心逻辑 (lint + security)
├── analyzers/
│   ├── semantic_duplication.py     # 语义重复检测
│   ├── rule_engine.py              # 增量分析器
│   └── language_adapter.py         # 语言适配器 (Python/JavaScript)
├── db/
│   ├── __init__.py
│   ├── models.py                   # CheckResult 模型
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
QualityService.run_check() (services/quality_service.py)
    ├── lint_code()                  → 代码规范检查
    └── security_scan()              → 安全检查
    ↓
PostgreSQL (ql_check_result 表) → 记录检查历史
    ↓
返回 {id, checkType, issues, issueCount, createdAt}
```

## 检查类型

**源文件**: `tools/quality-tool/app/services/quality_service.py:99-113`

通过 `check_type` 参数选择:

| checkType | 说明 | 执行的检查 |
|-----------|------|----------|
| `lint` | 仅代码规范 | `lint_code()` |
| `security` | 仅安全扫描 | `security_scan()` |
| `all` | 全部检查 (默认) | `lint_code()` + `security_scan()` |

### 请求参数 (`api/check.py:9-15`)

```json
{
    "code": "def foo():\n  pass",
    "checkType": "all",
    "filename": "foo.py",
    "language": "python",
    "userId": 123
}
```

### 响应格式

```json
{
    "id": 1,
    "checkType": "all",
    "issues": [
        {
            "line": 2,
            "rule": "trailing-whitespace",
            "message": "Trailing whitespace",
            "severity": "warning"
        },
        {
            "line": 5,
            "rule": "hardcoded-secret",
            "message": "Hardcoded password",
            "severity": "critical"
        }
    ],
    "issueCount": 2,
    "createdAt": "2025-07-28T10:30:00"
}
```

## Lint 规则详细

**源文件**: `tools/quality-tool/app/services/quality_service.py:8-36`

### line-length (行长度检查)

| 配置项 | 默认值 | 源码 |
|--------|--------|------|
| `LINT_MAX_LINE_LENGTH` | `120` | `config.py:17` |

检查每一行的字符长度。超过 120 字符时报告:

```json
{"line": N, "rule": "line-length", "message": "Line too long (N > 120)", "severity": "warning"}
```

### trailing-whitespace (尾部空格检查)

| 配置项 | 默认值 | 源码 |
|--------|--------|------|
| `LINT_CHECK_TRAILING_WHITESPACE` | `True` | `config.py:18` |

检查每行是否以空格结尾 (`line != line.rstrip()`)：

```json
{"line": N, "rule": "trailing-whitespace", "message": "Trailing whitespace", "severity": "warning"}
```

### missing-newline (文件末尾换行符)

| 配置项 | 默认值 | 源码 |
|--------|--------|------|
| `LINT_CHECK_MISSING_NEWLINE` | `True` | `config.py:19` |

检查文件是否以 `\n` 结尾:

```json
{"line": N, "rule": "missing-newline", "message": "File does not end with newline", "severity": "info"}
```

## Security 规则详细

**源文件**: `tools/quality-tool/app/services/quality_service.py:39-96`

### hardcoded-secret (硬编码密钥)

| 配置项 | 默认值 | 源码 |
|--------|--------|------|
| `SECURITY_CHECK_HARDCODED_SECRETS` | `True` | `config.py:21` |

检测模式 (不区分大小写):

| 正则表达式 | 描述 | 严重级别 |
|-----------|------|---------|
| `(?:password\|passwd\|pwd)\s*=\s*['"][^'"]+['"]` | 硬编码密码 | `critical` |
| `(?:api_key\|apikey\|api-key)\s*=\s*['"][^'"]+['"]` | 硬编码 API Key | `critical` |
| `(?:secret\|token)\s*=\s*['"][^'"]+['"]` | 硬编码 secret/token | `critical` |
| `-----BEGIN (?:RSA )?PRIVATE KEY-----` | 私钥明文 | `critical` |

### sql-injection (SQL 注入风险)

| 配置项 | 默认值 | 源码 |
|--------|--------|------|
| `SECURITY_CHECK_SQL_INJECTION` | `True` | `config.py:22` |

检测模式:

| 正则表达式 | 描述 | 严重级别 |
|-----------|------|---------|
| `(?:execute\|cursor\.execute)\s*\(\s*['"].*%s` | SQL 字符串格式化 (可能的注入) | `high` |
| `(?:execute\|cursor\.execute)\s*\(\s*f['"]` | SQL f-string (可能的注入) | `high` |
| `(?:execute\|cursor\.execute)\s*\(\s*['"].*\+` | SQL 字符串拼接 (可能的注入) | `high` |

### dangerous-function (危险函数)

| 配置项 | 默认值 | 源码 |
|--------|--------|------|
| `SECURITY_CHECK_DANGEROUS_FUNCTIONS` | `True` | `config.py:23` |

检测模式:

| 正则表达式 | 描述 | 严重级别 |
|-----------|------|---------|
| `\beval\s*\(` | 使用 eval() | `medium` |
| `\bexec\s*\(` | 使用 exec() | `medium` |
| `\bos\.system\s*\(` | 使用 os.system() | `medium` |
| `\bsubprocess\.call\s*\(\s*['"]` | Subprocess shell=True 风险 | `medium` |
| `\bpickle\.loads?\s*\(` | Pickle 反序列化漏洞 | `medium` |

### 严重级别体系

| 级别 | 含义 | 颜色 (Web UI) |
|------|------|--------------|
| `critical` | 严重安全问题 | 红色 `bg-red-900/50 text-red-300` |
| `high` | 高风险 | 橙色 `bg-orange-900/50 text-orange-300` |
| `medium` | 中等风险 | 黄色 `bg-yellow-900/50 text-yellow-300` |
| `warning` | 代码规范警告 | - |
| `info` | 提示信息 | 灰色 `bg-gray-700 text-gray-300` |

## 配置参数

**源文件**: `tools/quality-tool/app/config.py`

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LINT_MAX_LINE_LENGTH` | `120` | 最大行长度 |
| `LINT_CHECK_TRAILING_WHITESPACE` | `True` | 检查尾部空格 |
| `LINT_CHECK_MISSING_NEWLINE` | `True` | 检查文件末尾换行 |
| `SECURITY_CHECK_HARDCODED_SECRETS` | `True` | 检查硬编码密钥 |
| `SECURITY_CHECK_SQL_INJECTION` | `True` | 检查 SQL 注入 |
| `SECURITY_CHECK_DANGEROUS_FUNCTIONS` | `True` | 检查危险函数 |
| `APP_NAME` | `quality-tool` | 服务名 |
| `APP_VERSION` | `0.1.0` | 服务版本 |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `18084` | 监听端口 |

## 分析器模块

### 1. 语义重复检测 (SemanticDuplicationDetector)

**源文件**: `tools/quality-tool/app/analyzers/semantic_duplication.py`

```python
class SemanticDuplicationDetector:
    def __init__(self, similarity_threshold: float = 0.85):
```

基于余弦相似度的代码重复检测:

1. **文本向量化** (`_text_to_vector`): 将代码分词为 `{word: count}` 字典
2. **余弦相似度**: `dot_product(v1, v2) / (|v1| * |v2| + 1e-10)`
3. **聚类**: 相似度 >= 0.85 的代码块归为同一簇
4. **建议**: "考虑将重复代码提取为公共函数"

输出:
```json
{
    "blocks": [...],        // 重复的代码块列表
    "similarity": 0.92,     // 平均相似度
    "count": 3,             // 重复块数量
    "suggestion": "考虑将重复代码提取为公共函数"
}
```

### 2. 增量分析器 (IncrementalAnalyzer)

**源文件**: `tools/quality-tool/app/analyzers/rule_engine.py`

```python
class IncrementalAnalyzer:
    def __init__(self):
        self.cache: Dict[str, dict] = {}  # file_path → {hash, result, timestamp}

    def analyze(self, files, force_full=False) -> Dict:
```

功能:
- **增量分析**: 仅分析变更文件 (基于 MD5 hash)
- **全量分析**: `force_full=True` 时重新分析所有文件
- **变更检测**: `_detect_changes()` 对比文件 hash
- **缓存**: 文件路径 → hash → 分析结果 → 时间戳

输出:
```json
{
    "files_analyzed": 5,     // 实际分析的文件数
    "files_cached": 12,      // 缓存命中的文件数
    "results": [...],        // 分析结果列表
    "analysis_type": "incremental"  // 或 "full"
}
```

**注意**: `_analyze_file()` 方法当前返回空结果 (`{"issues": [], "metrics": {}}`)，是预留扩展接口。

### 3. 语言适配器 (Language Adapters)

**源文件**: `tools/quality-tool/app/analyzers/language_adapter.py`

抽象基类:
```python
class LanguageAdapter(ABC):
    def parse(self, code: str) -> Dict          # 解析代码结构
    def calculate_complexity(self, ast) -> float # 计算复杂度
    def detect_issues(self, ast) -> List[Dict]   # 检测问题
    def get_metrics(self, ast) -> Dict           # 获取度量指标
```

#### PythonAdapter

| 属性 | 值 |
|------|-----|
| 扩展名 | `.py` |
| 解析器 | `ast.parse()` |
| 最大函数数 | 50 |
| 最大参数数 | 5 |

指标:
```python
{
    "type": "module",
    "functions": N,        # FunctionDef 节点计数
    "classes": N,          # ClassDef 节点计数
    "lines": N             # 总行数
}
```

复杂度公式: `1.0 + functions * 0.1 + classes * 0.2`

问题检测: 函数数 > 50 → `too_many_functions` 警告

#### JavaScriptAdapter

| 属性 | 值 |
|------|-----|
| 扩展名 | `.js`, `.ts`, `.jsx`, `.tsx` |
| 解析器 | 正则表达式 (非 AST) |
| 最大回调深度 | 3 |

指标:
```python
{
    "type": "program",
    "functions": N,        # function 声明 + 箭头函数 计数
    "classes": N,          # class 声明计数
    "lines": N
}
```

复杂度公式: `1.0 + functions * 0.1`

问题检测: 当前不报告 (返回空列表)

#### LanguageManager

```python
class LanguageManager:
    adapters = {
        "python": PythonAdapter(),
        "javascript": JavaScriptAdapter(),
        "typescript": JavaScriptAdapter(),  # 使用 JS 适配器
    }

    def get_adapter(file_path) → Optional[LanguageAdapter]
    def get_supported_languages() → List[str]
```

**注意**: 语言适配器模块目前**未集成**到 `quality_service.py` 的检查流程中。`run_check()` 直接调用 `lint_code()` 和 `security_scan()`，不经过 `LanguageManager`。

## 数据库模型

**源文件**: `tools/quality-tool/app/db/models.py:14-28`

### CheckResult 表 (`ql_check_result`)

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | Integer PK | 自增主键 |
| `user_id` | Integer (索引) | 用户 ID |
| `filename` | String(512) | 文件名 |
| `language` | String(32) | 编程语言 |
| `check_type` | String(32) | 检查类型 (lint/security/all) |
| `issues` | JSON | 检查问题列表 |
| `issue_count` | Integer (默认 0) | 问题总数 |
| `created_at` | DateTime | 检查时间 |

## API 端点

### Tool MCP 接口 (`api/tool.py`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/tool/manifest` | GET | 工具元数据 |
| `/tool/capabilities` | GET | 能力列表 (含 input/output schema) |
| `/tool/invoke` | POST | MCP 标准调用入口 |

### 能力列表

| 能力名 | 端点 | 权限 | 超时 |
|--------|------|------|------|
| `quality.lint` | `POST /api/check` | `quality:lint` | 5000ms |
| `quality.security` | `POST /api/check` | `quality:security` | 5000ms |
| `quality.check` | `POST /api/check` | `quality:check` | 5000ms |

**能力选择逻辑** (`api/tool.py:160-168`):
```python
if req.capability == "quality.lint":      check_type = "lint"
elif req.capability == "quality.security": check_type = "security"
else:                                      check_type = "all"  # quality.check
```

### 检查 API (`api/check.py`)

| 端点 | 方法 | 请求体 | 说明 |
|------|------|--------|------|
| `/api/check` | POST | `{code, checkType?, filename?, language?, userId?}` | 运行检查 |
| `/api/check/history` | GET | `?userId=&limit=20` | 获取检查历史 |

### 健康检查 (`api/health.py`)

```
GET /health
→ {"status": "ok", "tool": "quality-tool", "version": "0.1.0"}
```

## Web UI (通过 Controller 代理查看)

使用方式: 在 Controller Web UI 中访问 `/quality`

**模板源文件**: `apps/controller/app/web/templates/modules/quality/index.html`

功能:
- 文件名输入框 (可选)
- 代码编辑区 (12 行 textarea, 暗色主题, 蓝色字体)
- 检查按钮 (显示 "检查中..." 加载状态)
- 结果面板: 问题列表按严重度着色，显示行号 + 规则名
- 通过时显示 ✅ "未发现问题"
- 历史记录弹窗 (表格: 文件名/类型/问题数/时间)
- 前端调用 `/api/quality/check` 和 `/api/quality/history`

## 调用示例

### 通过 MCP 调用

```python
# Lint 检查
invoke_tool_mcp("quality-tool", "quality.lint",
    '{"code": "x=1\\ny=2  ", "filename": "test.py"}')

# 安全检查
invoke_tool_mcp("quality-tool", "quality.security",
    '{"code": "password=\\"secret\\"", "filename": "test.py"}')

# 全量检查 (lint + security)
invoke_tool_mcp("quality-tool", "quality.check",
    '{"code": "eval(input())", "filename": "test.py"}')
```

### 直接 HTTP 调用 (开发)

```bash
# Lint 检查
curl -X POST http://127.0.0.1:18084/tool/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "quality.lint",
    "input": {"code": "x=1\ny = 2  "}
  }'

# 安全检查
curl -X POST http://127.0.0.1:18084/tool/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "quality.security",
    "input": {"code": "password = \"mysecret123\"", "filename": "config.py"}
  }'

# 全量检查
curl -X POST http://127.0.0.1:18084/tool/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "quality.check",
    "input": {"code": "eval(input())", "filename": "dangerous.py"}
  }'

# 查看检查历史
curl "http://127.0.0.1:18084/api/check/history?limit=10"
```

## 已知限制

1. **语言适配器未集成**: `LanguageManager` 和各个 `LanguageAdapter` 实现在 `analyzers/` 目录下，但 `quality_service.py` 中的 `run_check()` 不调用它们
2. **JavaScriptAdapter 使用正则解析**: 非 AST 解析，精确度受限
3. **增量分析器 `_analyze_file` 为空**: 返回 `{"issues": [], "metrics": {}}`
4. **语义重复检测未集成**: `SemanticDuplicationDetector` 在 `analyzers/` 下但未在检查流中调用
5. **无 Pre-commit Hook 集成**: 当前仅作为 API 服务使用，无 git hook 集成
6. **规则不可动态配置**: Lint/security 规则硬编码在代码中，无规则文件/数据库化

## 关键文件索引

| 文件 | 行数 | 职责 |
|------|------|------|
| `main.py` | 37 | FastAPI 应用入口 |
| `config.py` | 28 | 配置参数 (含各开关) |
| `api/tool.py` | 201 | MCP 调用接口, manifest |
| `api/check.py` | 30 | 检查 + 历史 API |
| `services/quality_service.py` | 153 | Lint + Security 核心逻辑 |
| `analyzers/semantic_duplication.py` | 55 | 重复代码检测 |
| `analyzers/rule_engine.py` | 56 | 增量分析缓存 |
| `analyzers/language_adapter.py` | 95 | 按语言分析的结构体 |
| `db/models.py` | 33 | CheckResult 模型 + Database engine |