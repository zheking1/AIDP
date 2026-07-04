# error-tool 需求说明

## 1. 背景

AI 编程闭环中，最消耗时间的不是首次生成代码，而是编译失败、依赖冲突、测试失败、运行异常后的反复排查。很多错误会在同一技术栈、同一项目或同一团队内重复出现。如果每次都让 AI 从零分析日志，会浪费上下文和执行时间。

`error-tool` 的目标是把错误变成可检索资产：记录原始日志，抽取稳定特征，沉淀根因和修复方案，下次出现相似错误时自动召回。

## 2. 用户角色

| 角色 | 诉求 |
|---|---|
| 个人开发者 | 本地保存常见编译/运行错误，快速复用修复方法 |
| 团队开发者 | 在团队项目中共享排坑经验 |
| AI Agent | 执行失败后自动检索相似错误和历史修复方案 |
| 工具维护者 | 增加新的错误解析器和相似度策略 |

## 3. 核心场景

### 3.1 编译失败自动归档

`sandbox-tool` 执行 Node/TypeScript 构建、Python 测试或 SQL 验证失败后，把日志传给 `error.record`。`error-tool` 解析出主错误、模块、文件、行号、符号、依赖版本，并保存原始日志对象路径。

### 3.2 AI 修复前检索历史方案

controller 在重新让 AI 修复前调用 `error.search`，输入本次错误摘要，返回相似错误、历史根因、修复方案、适用版本和关联提交。

### 3.3 修复后绑定方案

AI 或用户确认修复后调用 `error.link_solution`，记录修复步骤、变更文件、补充依赖、注意事项。之后 `error.resolve` 将案例标记为已解决。

### 3.4 高价值错误导出

重复出现且解决方案稳定的错误，可以通过 `error.export_pattern` 导出到 `asset-tool`，作为“历史代码方案/排坑日志”长期复用。

## 4. MVP 错误类型

| error_type | 示例 | 必须抽取字段 |
|---|---|---|
| `typescript_compile` | `TS2339 Property does not exist` | package、file、line、symbol |
| `python_exception` | Python/FastAPI/RAG 工具异常 | exception_class、file、line、stack_top |
| `runtime_exception` | Node/Python/服务启动异常 | exception_class、root_cause、stack_top |
| `test_failure` | Vitest/pytest 失败 | test_name、assertion、expected、actual |
| `dependency_conflict` | 版本冲突、包缺失 | package_name、version、missing_module |

## 5. 功能需求

### 5.1 错误记录

必须支持：

- 原始日志写入。
- 日志过大时保存到对象存储或本地文件。
- 错误归一化。
- 记录环境信息。
- 记录来源工具。
- 记录 workspace/project/session。

### 5.2 错误检索

必须支持：

- query 文本检索。
- error_type 过滤。
- tags 过滤。
- environment 过滤。
- project 内检索和 workspace 范围检索。
- top_k。

检索结果必须包含：

- 相似度。
- 归一化主错误。
- 根因。
- 修复方案。
- 适用环境。
- 关联提交或文档引用。

### 5.3 解决方案管理

解决方案必须包含：

- `root_cause`
- `fix_steps`
- `changed_files`
- `patch_summary`
- `verified_by`
- `applicable_versions`
- `risk_notes`

### 5.4 生命周期

状态：

- `open`：已记录，未确认根因。
- `analyzed`：已分析，有候选根因。
- `resolved`：已验证解决。
- `ignored`：噪声或无价值。
- `archived`：历史保留。

## 6. 非目标

MVP 不做：

- 不替代日志平台。
- 不保存完整 CI 构建历史。
- 不自动修改代码。
- 不做跨团队公开共享。
- 不要求一开始就有向量数据库；可先关键词 + 归一化字段匹配。

## 7. 非功能需求

- `error.record` P95 小于 500ms，不包括大日志上传。
- `error.search` P95 小于 800ms。
- 原始日志最大支持 10MB。
- 所有错误按 `workspace_id/project_id` 隔离。
- 日志中的 token、password、secret 必须脱敏。

## 8. MVP 验收范围

- 记录四类基础错误。
- 归一化主错误字段。
- 关键词检索相似错误。
- 绑定解决方案。
- 标记 resolved。
- 从 sandbox/quality 失败结果调用。
