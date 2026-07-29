# 已知问题清单

## 架构/文档不一致

### 1. 前端技术栈与文档不符

| 问题 | 系统索引 (`00-INDEX.md`) 声明前端使用 "Vue 3 + Element Plus + Pinia" |
|------|------|
| 实际 | 使用 "Jinja2 + Alpine.js + Tailwind CSS (CDN)" 实现 |
| 影响 | 开发者根据文档安装 Vue 依赖会失败 |
| 状态 | **未修复** - 需同步更新索引文档 |

### 2. 系统索引的 Web UI 章节与实现不符

| 问题 | `00-INDEX.md` 列出的 `03-pages/`, `06-state.md`, `07-styles.md` 对应 Vue 架构 |
|------|------|
| 实际 | 状态管理在 `store.js`, 样式在 `base.html` 内联, 页面在 `templates/` |
| 状态 | **未修复** |

### 3. WEB_UI_ARCHITECTURE.md 目录树与实际文件有差异

| 问题 | 文档描述的前端目录 (`apps/controller/WEB_UI_ARCHITECTURE.md:33-59`) 与实际不一致 |
|------|------|
| 差异 | 文档提到 `static/css/` 目录, 实际不存在; 文档目录树过于简化 |
| 状态 | **未修复** - 文档需更新为当前文件列表 |

## 安全相关

### 4. Sandbox 安全扫描不阻止执行

| 问题 | `SecurityEngine.check()` 仅返回报告, 不阻止危险代码执行 |
|------|------|
| 位置 | `tools/sandbox-tool/app/services/sandbox_modules.py:92-110` |
| 严重性 | 高 - 用户可执行 `eval()`/`os.system()` 等危险函数 |
| 状态 | **未修复** - 需在 execute 前加入拦截逻辑 |

### 5. Sandbox 无容器隔离

| 问题 | `ContainerPool` 使用模拟容器 ID, 代码在宿主机进程环境中运行 |
|------|------|
| 位置 | `tools/sandbox-tool/app/services/sandbox_modules.py:18-78` |
| 严重性 | 高 - 无文件系统/网络/进程隔离 |
| 状态 | **未修复** - 需集成 Docker SDK 或类似方案 |

### 6. Sandbox 使用 /tmp 硬编码路径

| 问题 | 代码执行将文件写入 `/tmp/sandbox_exec.{ext}` |
|------|------|
| 位置 | `tools/sandbox-tool/app/services/execution_service.py:32` |
| 影响 | Windows 环境下不存在 `/tmp` 路径 |
| 状态 | **未修复** - 需使用 `tempfile` 模块或可配置路径 |

### 7. Sandbox 输出截断硬编码

| 问题 | stdout/stderr 被硬截断到 10240 字节 |
|------|------|
| 位置 | `tools/sandbox-tool/app/services/execution_service.py:59-60` |
| 影响 | 大输出被静默丢弃, 无用户提示 |
| 状态 | **部分修复** - `EXECUTION_MAX_OUTPUT` 可从配置修改 |

### 8. Sandbox Python 命令不可跨平台

| 问题 | 使用 `python3` 而非 `python` |
|------|------|
| 位置 | `tools/sandbox-tool/app/services/execution_service.py:13` |
| 影响 | 某些系统上 `python3` 不存在 (如 Windows python.org 安装) |
| 状态 | **未修复** - 需自动检测或可配置 |

### 9. Quality Tool 语言适配器未集成

| 问题 | `LanguageManager` 和各个 `LanguageAdapter` 定义在 `analyzers/` 下但 `quality_service.py` 未调用 |
|------|------|
| 位置 | `analyzers/{language_adapter,rule_engine,semantic_duplication}.py` |
| 影响 | 代码结构未纳入检查流程, 这些模块为死代码 |
| 状态 | **未修复** - 需在 `run_check()` 中集成 |

### 10. Quality Tool 增量分析器核心方法为空

| 问题 | `IncrementalAnalyzer._analyze_file()` 返回空结果 |
|------|------|
| 位置 | `tools/quality-tool/app/analyzers/rule_engine.py:55-56` |
| 影响 | 增量分析不影响检查结果 |
| 状态 | **未修复** - 预留扩展接口 |

### 11. Quality Tool JavaScriptAdapter 使用正则解析

| 问题 | `JavaScriptAdapter.parse()` 使用正则而非 AST 解析 |
|------|------|
| 位置 | `tools/quality-tool/app/analyzers/language_adapter.py:64-68` |
| 影响 | 解析精确认度有限, 无法检测语法错误 |
| 状态 | **未修复** - 可考虑集成 ESLint 或 Babel |

## 配置/部署相关

### 12. opencode.jsonc 缺少 aidp.api_key

| 问题 | AGENTS.md 要求从 `opencode.jsonc` 的 `aidp.api_key` 读取 API Key, 但文件未包含该字段 |
|------|------|
| 位置 | `.opencode/opencode.jsonc` |
| 影响 | 调用 `invoke_tool_mcp` 时需手动传入或降级为 admin 用户 |
| 状态 | **未修复** - 需添加 `"aidp": {"api_key": "your_key"}` |

### 13. 端口冲突: memory-tool 与 importer-tool 共用 18085

| 问题 | `tools/memory-tool/app/config.py` 和 `tools/importer-tool/` 都声明端口 18085 |
|------|------|
| 位置 | `docs/aidp/12-appendix/03-port-mapping.md:21` |
| 影响 | 两个工具不能同时运行 |
| 状态 | **已知** - 文档标注冲突, 不同时启动 |

### 14. 多服务的 Docker Compose 不统一

| 问题 | 3 个服务在根 `docker-compose.yml`, 其余在各自 `tools/{name}/docker-compose.yml` |
|------|------|
| 影响 | 无法通过单一命令启动全部服务; 无统一的编排文件 |
| 状态 | **未修复** - 需整合为顶层 docker-compose |

## 功能缺失

### 15. Quality Tool 规则不可动态配置

| 问题 | Lint/Security 规则硬编码在 `quality_service.py` 和 `config.py` 中 |
|------|------|
| 影响 | 用户无法在运行时添加、修改或禁用规则 |
| 状态 | **未修复** - 需规则文件/数据库化 |

### 16. Quality Tool 无 Pre-commit Hook 集成

| 问题 | 仅作为 API 服务使用, 无 Git hook 集成方案 |
|------|------|
| 状态 | **未修复** - 可考虑提供 `.pre-commit-hooks.yaml` |

### 17. Sandbox 不支持 JavaScript 执行

| 问题 | `sandbox_modules.py:85` 定义了 JavaScript 危险函数列表, 但 `execution_service.py` 不支持 JavaScript |
|------|------|
| 位置 | `execution_service.py:12-16` 仅支持 python/bash/sh |
| 状态 | **未修复** - 预留了 JS 安全检查但未实现执行 |

### 18. Web UI 的 components/ 模板目录为空

| 问题 | `templates/components/` 目录存在但无文件 |
|------|------|
| 影响 | 模板级可复用组件 (导航栏、侧栏、通知等) 散落在各页面中 |
| 状态 | **未修复** - 可提取公共模板片段到此目录 |

## 代码质量

### 19. 无统一代码格式化配置

| 问题 | 项目未配置 `.editorconfig`, `.flake8`, `.pre-commit-config.yaml`, `eslint.config.*` |
|------|------|
| 影响 | 不同开发者的代码风格不一致 |
| 状态 | **未修复** - 需添加格式化配置 |

### 20. 未配置 CI/CD

| 问题 | 项目无 `.github/workflows/` 或 CI 配置文件 |
|------|------|
| 影响 | 无法自动化测试和部署 |
| 状态 | **未修复** |

### 21. Python 文件混合 exists

| 问题 | 部分 `__init__.py` 为空文件, 但目录结构非标准 Python package |
|------|------|
| 位置 | `apps/controller/app/web/__init__.py` (0 字节) |
| 状态 | 低优先级 |