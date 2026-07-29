# importer-tool 模块设计

## 1. 模块划分

| 模块 | 职责 |
|------|------|
| `ImportOrchestrator` | 编排整个导入流程，管理状态机，协调各子模块 |
| `ContentAcquirer` | 从 text/url/file/directory 获取内容 |
| `ContentClassifier` | 基于规则+AI 判断内容类型 |
| `ContentCategorizer` | 推荐标签、category、severity |
| `QualityGate` | 调用 quality check 并解析结果 |
| `ContentPersister` | 调用对应模块 API 写入数据 |
| `ConversationManager` | 管理与用户的对话上下文和确认流程 |

## 2. ContentAcquirer

### 来源类型

| source_type | 参数 | 返回 |
|------------|------|------|
| `text` | `content: str` | `{content, filename: null}` |
| `url` | `url: str` | `{content, filename: from URL, source_uri}` |
| `file` | `path: str` | `{content, filename, size, mime_type}` |
| `directory` | `path: str, pattern: str` | `[{path, filename, size, ext}]` |

### URL 抓取

```text
GET url
  -> 检查协议（仅 http/https）
  -> 检查目标 IP（拒绝内网/回环）
  -> 下载（15s 超时）
  -> HTML → Markdown 转换（去除 script/style/nav/footer）
  -> 截断 50000 字符
```

### 文件读取

- 白名单扩展名：.md, .txt, .yaml, .yml, .json, .xml, .sql, .py, .js, .ts, .sh, .properties, .env, .cfg, .ini, .toml, .csv。
- 文件大小限制：单文件最大 5MB。
- 编码：优先 UTF-8，自动检测 fallback。

### 目录扫描

- 递归遍历。
- 忽略 `.git/`、`node_modules/`、`__pycache__/`、`venv/`、`dist/`、`build/`。
- 返回文件列表，按扩展名过滤。

## 3. ContentClassifier

### 分类规则

| 特征 | → type | 置信度 |
|------|--------|--------|
| 内容包含 `instruction` + `content` 字段 | `skill` | high |
| 内容包含 `severity` + `约束`/`禁止`/`必须` | `rule` | high |
| 文件名含 `plan`/`蓝图`/`方案`/`路线图` | `plan` | medium |
| 文件名含 `ADR` | `knowledge` | high |
| 文件名含 `README`/`架构`/`设计`/`指南`/`规范` | `knowledge` | medium |
| 文件名含 `.md` 且首行为 H1 标题 | `knowledge` | low |
| 无匹配特征 | 询问用户 | — |

### 确认流程

```text
分类结果 → 展示给用户:
  "识别为「knowledge」类型，标签建议: architecture/topology"
  用户可选择:
  1. 确认
  2. 修改类型（knowledge/skill/rule/plan）
  3. 修改标签
```

## 4. ContentCategorizer

### 标签推荐

基于以下维度推荐：

- 文件名关键词 → domain 标签。
- 内容中的技术栈关键词 → tech_stack。
- 文件路径中的目录名 → category 层级。
- 规则类内容 → 自动推断 severity（critical/high/medium/low）。

### category 层级

```text
knowledge → architecture/overview
          → architecture/adr
          → api/auth
          → api/controller
          → erp/design
          → erp/business
          → devops/infrastructure
          → test/admin-web
          → test/plus-ui

rule → code_style
     → architecture
     → security
     → other

plan → erp/blueprint
     → erp/frontend
     → catering/prd
     → infrastructure
```

## 5. QualityGate

### 检查流程

```text
quality_check(content, type):
  1. 调用 POST /api/quality/check
     - code=content, filename=filename, language=auto detect
  2. 解析返回的 issues
  3. 额外规则:
     - rule 类型: 必须包含 severity 字段
     - skill 类型: 必须有 instruction 或 content
     - 通用: 文件末必须有换行
  4. 分类:
     - 有 critical 级别 issue → BLOCKED，必须修复
     - 有 warning → 询问用户是否跳过
     - 无 issue → PASS
```

### 结果处理

| 状态 | 操作 |
|------|------|
| PASS | 继续导入流程 |
| WARNING | 展示 issue 列表，问用户"继续导入/修复/取消" |
| BLOCKED | 展示 critical 问题，退回修改 |

## 6. ContentPersister

### 存储映射

| type | API | 请求体 |
|------|-----|--------|
| knowledge | `POST /api/knowledge/documents` | `{title, content, category, tags, source_uri, source_type}` |
| skill | `POST /api/skills` | `{name, description, instruction, content, scope, tags, group_id}` |
| rule | `POST /api/rules` | `{name, description, content, category, severity, scope, tags}` |
| plan | `POST /api/knowledge/documents` | `{title, content, category, tags:["plan",...], source_type}` |

### 幂等逻辑

```text
checksum = SHA256(content)
if type=knowledge:
  查询同 title + user_id 的文档
  若存在:
    checksum 一致 → skip (已是最新)
    checksum 不一致 → 问用户: "已存在旧版本，是否更新？"
  若不存在 → create
```

## 7. ConversationManager

管理导入会话的上下文：

- 当前状态（pending/classifying/checking/...）。
- 已确认的元数据（type/tags/category）。
- 待用户决策的队列（批量导入时）。
- 支持会话回溯（用户可要求"上一步"）。

## 8. 扩展点

- 支持通过 AI 模型增强分类准确率。
- 支持导入后自动触发 knowledge chunking。
- 支持导入后自动绑定到项目。
- 支持自定义分类规则。
