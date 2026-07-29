# Quality Module — 质量检查模块

## 1. 模块概述

Quality（质量检查）模块提供**代码质量和安全扫描**能力，支持 Lint 检查、安全漏洞扫描和质量评分。用户提交代码后，模块通过正则表达式匹配和规则库进行静态分析，返回包含严重级别、位置和修复建议的检查报告。

模块定义文件位于 `apps/controller/app/modules/quality/__init__.py`：

```python
@register_module(name='quality', enabled=True)
class QualityModule(BaseModule):
    """
    代码质量检查模块
    提供代码 Lint 检查和安全扫描功能
    """
    name = "quality"
    description = "代码质量检查，支持 Lint 和安全扫描"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as quality_router
        app.include_router(quality_router, prefix="/api/quality")
```

模块没有外部依赖（`dependencies = []`），内置了规则引擎，无需调用外部服务。

## 2. 数据模型

只有一个模型 `CheckResult`，定义在 `apps/controller/app/modules/quality/models.py`：

```python
class CheckResult(Base):
    """质量检查结果模型"""
    __tablename__ = "aidp_check_results"

    id           = Column(String(36), primary_key=True, default=gen_uuid)
    project_id   = Column(Integer, nullable=True, index=True)
    user_id      = Column(String(100), nullable=True, index=True)
    filename     = Column(String(500), nullable=True)
    language     = Column(String(50), nullable=True)
    check_type   = Column(String(20), nullable=False, index=True)
    # lint / security / all
    issues       = Column(Text, default="[]")       # JSON 格式的问题列表
    issue_count  = Column(Integer, default=0)
    code_snippet = Column(Text, nullable=True)
    score        = Column(Float, nullable=True)
    created_at   = Column(DateTime(timezone=True), default=utcnow, index=True)
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| project_id | Integer | 所属项目 ID |
| user_id | String(100) | 用户 ID |
| filename | String(500) | 被检查的文件名 |
| language | String(50) | 代码语言 |
| check_type | String(20) | 检查类型：lint / security / all |
| issues | Text | JSON 数组，每个 issue 包含 type/severity/line/message/rule |
| issue_count | Integer | 问题总数 |
| code_snippet | Text | 代码片段（最多 5000 字符） |
| score | Float | 质量评分（0-100） |
| created_at | DateTime | 创建时间 |

`to_dict()` 方法提供可选的 `include_code` 参数（默认 `False`），控制是否返回代码片段。

## 3. API 端点

所有路由定义在 `apps/controller/app/modules/quality/routes.py` 中，前缀为 `/api/quality`。

### 端点列表

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | `/api/quality/check` | 执行代码检查（lint/security/all） | quality:check |
| GET | `/api/quality/history` | 检查历史 | 登录用户 |
| GET | `/api/quality/stats` | 检查统计 | 登录用户 |

### 请求模型

```python
class CheckRequest(BaseModel):
    code: str = Field(..., min_length=1)
    check_type: str = Field("all", description="lint, security, all")
    filename: Optional[str] = None
    language: Optional[str] = None
```

### POST /api/quality/check 响应示例

```json
{
    "id": "uuid-string",
    "project_id": null,
    "user_id": "user-123",
    "filename": "test.py",
    "language": "python",
    "check_type": "all",
    "issues": [
        {"type": "trailing_whitespace", "severity": "warning",
         "line": 5, "message": "Trailing whitespace detected",
         "rule": "no-trailing-whitespace"},
        {"type": "hardcoded_secrets", "severity": "critical",
         "line": 10, "message": "Hardcoded password detected",
         "rule": "hardcoded_secrets"}
    ],
    "issue_count": 2,
    "score": 73.0,
    "created_at": "2026-07-13T10:00:00+00:00"
}
```

## 4. 检查流程

### 4.1 统一入口

```python
@router.post("/check")
async def run_check(data: CheckRequest, ...):
    user_id = get_current_user_id(user)
    all_issues = []

    if data.check_type in ("lint", "all"):
        all_issues.extend(lint_code(data.code, data.filename))

    if data.check_type in ("security", "all"):
        all_issues.extend(security_scan(data.code, data.filename))

    score = calculate_score(all_issues)

    result = CheckResult(
        project_id=project_id, user_id=user_id,
        filename=data.filename, language=data.language,
        check_type=data.check_type,
        issues=json.dumps(all_issues),
        issue_count=len(all_issues),
        code_snippet=data.code[:5000],
        score=score)
    db.add(result)
    await db.commit()
    return result.to_dict()
```

### 4.2 Lint 检查

Lint 检查通过 `lint_code()` 函数实现，使用简单的逐行分析：

```python
def lint_code(code: str, filename: str = None) -> List[dict]:
    issues = []
    lines = code.split('\n')

    for i, line in enumerate(lines, 1):
        # 检查行长度
        if len(line) > LINT_MAX_LINE_LENGTH:  # 120 chars
            issues.append({
                "type": "line_too_long",
                "severity": "warning",
                "line": i,
                "message": f"Line exceeds {LINT_MAX_LINE_LENGTH} characters ({len(line)} chars)",
                "rule": "max-line-length"
            })

        # 检查尾部空格
        if line.rstrip() != line:
            issues.append({
                "type": "trailing_whitespace",
                "severity": "warning",
                "line": i,
                "message": "Trailing whitespace detected",
                "rule": "no-trailing-whitespace"
            })

    # 检查文件末尾换行
    if code and not code.endswith('\n'):
        issues.append({
            "type": "missing_newline",
            "severity": "info",
            "line": len(lines),
            "message": "Missing newline at end of file",
            "rule": "final-newline"
        })

    return issues
```

**Lint 规则清单：**

| 规则 ID | 检查内容 | 严重级别 |
|---------|---------|---------|
| `max-line-length` | 行超过 120 字符 | warning |
| `no-trailing-whitespace` | 行尾有多余空格 | warning |
| `final-newline` | 文件末尾缺少换行符 | info |

### 4.3 安全扫描

安全扫描通过 `security_scan()` 函数实现，使用正则表达式匹配预定义的安全模式：

```python
SECURITY_PATTERNS = {
    "hardcoded_secrets": [
        (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', "critical", "Hardcoded password detected"),
        (r'(?i)(api_key|apikey|api-key)\s*=\s*["\'][^"\']+["\']', "critical", "Hardcoded API key detected"),
        (r'(?i)(secret|token)\s*=\s*["\'][^"\']+["\']', "critical", "Hardcoded secret/token detected"),
        (r'-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----', "critical", "Hardcoded private key detected"),
    ],
    "sql_injection": [
        (r'execute\s*\(\s*["\'].*%s.*["\'].*%', "high", "Potential SQL injection via string formatting"),
        (r'execute\s*\(\s*f["\']', "high", "Potential SQL injection via f-string"),
        (r'execute\s*\(\s*["\'].*\+\s*\w+', "high", "Potential SQL injection via string concatenation"),
    ],
    "dangerous_functions": [
        (r'\beval\s*\(', "medium", "Use of eval() is dangerous"),
        (r'\bexec\s*\(', "medium", "Use of exec() is dangerous"),
        (r'\bos\.system\s*\(', "medium", "Use of os.system() is dangerous"),
        (r'\bsubprocess\.call\s*\([^)]*shell\s*=\s*True', "medium", "subprocess.call with shell=True is dangerous"),
        (r'\bpickle\.loads\s*\(', "medium", "Use of pickle.loads() is dangerous"),
    ]
}

def security_scan(code: str, filename: str = None) -> List[dict]:
    issues = []
    lines = code.split('\n')
    for category, patterns in SECURITY_PATTERNS.items():
        for pattern, severity, message in patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    issues.append({
                        "type": category,
                        "severity": severity,
                        "line": i,
                        "message": message,
                        "rule": category
                    })
    return issues
```

**安全规则清单（3 大类 12 条模式）：**

| 类别 | 严重级别 | 检测模式 |
|------|---------|---------|
| hardcoded_secrets | critical | 硬编码密码/API Key/Token/私钥 |
| sql_injection | high | SQL 注入（%s 格式化/f-string/字符串拼接）|
| dangerous_functions | medium | eval/exec/os.system/subprocess shell=True/pickle.loads |

### 4.4 质量评分

```python
def calculate_score(issues: List[dict]) -> float:
    severity_weights = {
        "critical": 25,
        "high": 15,
        "medium": 5,
        "warning": 2,
        "info": 0.5
    }
    total_deduction = sum(
        severity_weights.get(i.get("severity", "info"), 1) for i in issues)
    return max(0, min(100, 100 - total_deduction))
```

**评分逻辑：** 基础分 100 分，每个问题根据严重级别扣分，最低 0 分，最高 100 分。

| 严重级别 | 权重（扣分） | 含义 |
|---------|------------|------|
| critical | 25 | 严重安全问题 |
| high | 15 | 高危漏洞 |
| medium | 5 | 危险函数使用 |
| warning | 2 | 代码风格问题 |
| info | 0.5 | 信息提示 |

### 4.5 完整检查流程

```
用户提交代码 + check_type
    │
    ├── check_type 包含 "lint" → lint_code(code)
    │       └── 逐行检查长度、尾部空格、文件结尾
    │
    ├── check_type 包含 "security" → security_scan(code)
    │       └── 正则匹配 3 大类 12 条安全模式
    │
    ├── calculate_score(issues) → 0~100 分
    │
    └── 保存 CheckResult 到数据库 → 返回结果
```

## 5. 严重级别

系统定义了 5 个严重级别，从高到低排列：

| 级别 | CSS 样式 | 颜色 | 含义 |
|------|---------|------|------|
| `critical` | `border-red-800 bg-red-900/20` | 红色 | 严重安全问题（硬编码密码、密钥等）|
| `high` | `border-orange-800 bg-orange-900/20` | 橙色 | 高危漏洞（SQL 注入等）|
| `medium` | `border-yellow-800 bg-yellow-900/20` | 黄色 | 危险函数使用 |
| `warning` | `border-blue-800 bg-blue-900/20` | 蓝色 | 代码风格问题 |
| `info` | `border-gray-700 bg-gray-800/50` | 灰色 | 信息提示 |

## 6. 前端

前端模板位于 `apps/controller/app/web/templates/modules/quality/index_content.html`，使用 Alpine.js 管理状态。

### 核心 Alpine 组件：`qualityPage()`

```javascript
window.qualityPage = function qualityPage() {
    return {
        code: '',              // 代码输入
        filename: '',          // 文件名
        checkLint: true,       // 是否执行 Lint
        checkSecurity: true,   // 是否执行安全扫描
        running: false,        // 是否正在检查
        lastResult: null,      // 上次检查结果
        history: [],           // 检查历史

        // 计算属性：按严重级别统计问题数
        get criticalCount() {
            return (this.lastResult?.issues || [])
                .filter(i => i.severity === 'critical').length;
        },
        get highCount() {
            return (this.lastResult?.issues || [])
                .filter(i => i.severity === 'high').length;
        },
        get mediumCount() {
            return (this.lastResult?.issues || [])
                .filter(i => i.severity === 'medium').length;
        },
        get warningCount() {
            return (this.lastResult?.issues || [])
                .filter(i => i.severity === 'warning').length;
        },

        async init() { await this.loadHistory(); },

        async runCheck() {
            if (!this.code.trim() || this.running) return;
            this.running = true;
            const ct = this.checkLint && this.checkSecurity ? 'all'
                     : this.checkLint ? 'lint' : 'security';
            try {
                const r = await fetch('/api/quality/check', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        code: this.code,
                        check_type: ct,
                        filename: this.filename || null
                    })
                });
                if (r.ok) { this.lastResult = await r.json(); await this.loadHistory(); }
            } catch(e) { console.error(e); }
            finally { this.running = false; }
        },

        async loadHistory() {
            const r = await fetch('/api/quality/history?limit=10');
            if (r.ok) { const d = await r.json(); this.history = d.items || []; }
        }
    };
};
```

### 关键 UI 元素

| UI 元素 | 说明 |
|---------|------|
| **代码编辑器** | 等宽字体、绿色文字、80 行高 |
| **Lint / 安全复选框** | 选择检查类型 |
| **文件名输入** | 可选的文件名 |
| **检查按钮** | 执行检查，运行时显示旋转图标 |
| **质量评分** | 大号数字显示，绿色(>=80) / 黄色(>=50) / 红色(<50) |
| **严重级别统计** | 4 种颜色标签显示各级别问题数 |
| **问题列表** | 按严重级别颜色区分，显示行号、类型、消息 |
| **检查历史** | 最近 10 条检查记录，显示评分和问题数 |