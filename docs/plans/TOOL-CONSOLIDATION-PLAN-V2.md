# AIDP 工具整合方案 V2 —— 剩余 5 个工具

> **版本**: v1.0  
> **日期**: 2026-07-29  
> **状态**: 规划中  
> **前置**: Phase 1-3 已完成（8 个工具已整合）

---

## 1. 现状

| 工具 | 端口 | 数据库 | 类型 | 额外依赖 | 复杂度 |
|------|:---:|--------|------|----------|:---:|
| **code-index** | 18086 | SQLite (5表) | API 服务 | jinja2, aiofiles | ⭐⭐ |
| **doc-index** | 18087 | SQLite (4表) | API 服务 | markdown, bs4, lxml | ⭐⭐ |
| **file-watcher** | 18091 | SQLite (2表) | API + 后台进程 | watchdog>=5.0.0 | ⭐⭐⭐ |
| **importer-tool** | 18085 | PostgreSQL (5表) | API 服务 | asyncpg, bs4, markdown | ⭐⭐ |
| **project-importer** | 18090 | 无（无状态） | API 服务 | 仅 4 个包 | ⭐ |

---

## 2. 整合方案

### 2.1 code-index（最优先）

**被谁调用：**
- `project_init_service.py` Step 3: `create_project` + `scan_project`
- `project_init_service.py` Step 4: `index_file`（批量上传文件）
- `context_optimizer/staged_retriever.py`: `code.search`
- `projects_new.py`: `_run_code_index()`
- `skill_router/classification_service.py`: 代码相关任务路由

**改动清单：**

| 步骤 | 操作 | 工作量 |
|:---:|------|:---:|
| 1 | 复制 `tools/code-index/app/` → `apps/controller/app/tools/code_index/` | 1分钟 |
| 2 | 修复 import 路径（`from app.` → `from app.tools.code_index.`） | 1分钟 |
| 3 | `tool_invoker.py` 增加 `code-index` 本地调度 | 20行 |
| 4 | `tools/__init__.py` 挂载路由 | 3行 |
| 5 | 依赖：无新增（Controller 已有全部依赖） | — |

### 2.2 doc-index

**被谁调用：**
- `classification.py:228-255`: `_store_to_doc_index()` — 分类后将文档存入
- Controller 引用为 init 必需工具

**改动清单：**

| 步骤 | 操作 | 工作量 |
|:---:|------|:---:|
| 1 | 复制 `tools/doc-index/app/` → `apps/controller/app/tools/doc_index/` | 1分钟 |
| 2 | 修复 import 路径 | 1分钟 |
| 3 | `tools/__init__.py` 挂载路由 | 2行 |
| 4 | 依赖：`markdown` 不在 Controller 中，需加到 requirements.txt | 1行 |

### 2.3 project-importer（最简单）

**被谁调用：**
- `project_init_service.py` Step 2: `project.import`

**特点：** 无数据库、无配置、4 个依赖、纯 API 端点、不走 tool protocol

**改动清单：**

| 步骤 | 操作 | 工作量 |
|:---:|------|:---:|
| 1 | 复制 `tools/project-importer/app/` → `apps/controller/app/tools/project_importer/` | 1分钟 |
| 2 | 修改硬编码 URL（`localhost:18086` → 127.0.0.1:8883 或直接 import） | 5行 |
| 3 | `tools/__init__.py` 挂载路由 | 2行 |
| 4 | 依赖：无新增 | — |

### 2.4 importer-tool

**被谁调用：** Controller 通过 tool protocol `/tool/invoke` 调用，无直接硬编码

**特点：** 唯一用 PostgreSQL 的工具（5 表），但 Controller 已有 PostgreSQL

**改动清单：**

| 步骤 | 操作 | 工作量 |
|:---:|------|:---:|
| 1 | 复制 `tools/importer-tool/app/` → `apps/controller/app/tools/importer_tool/` | 1分钟 |
| 2 | 修复 import 路径 | 1分钟 |
| 3 | `tools/__init__.py` 挂载路由 | 2行 |
| 4 | 依赖：`asyncpg` 已有，`markdown` 需加 | 1行 |

### 2.5 file-watcher（特殊处理）

**特殊性：** 内含 background `watchdog` 线程，在 lifespan 中启动和停止

**被谁调用：**
- `projects_new.py`: `_run_local_setup()` 作为本地任务返回 shell 命令
- 其他工具通过 `/tool/invoke` 操作

**整合方式选项：**

| 选项 | 方式 | 优点 | 缺点 |
|------|------|------|------|
| A | 整合到 Controller | 统一管理 | watchdog 线程会随 Controller 生命周期变化 |
| B | 保持独立容器 | 独立启停 | 需要单独部署 |

**推荐 B**：file-watcher 的 watchdog 是长驻后台进程，整合后如果 Controller 重启会中断文件监控，反而不好。保持独立容器更合理。

**依赖：** `watchdog>=5.0.0` — 只此一个额外依赖

---

## 3. 需要保留的代码（不删除）

**skill-router 的 Web UI 模板**：保留在 `tools/skill-router/app/web/templates/` 目录下，git 中不删除。这些是 skill-router 的独立 Web 页面（登录、管理），虽然已整合到 Controller 但仍保留作为参考。

---

## 4. 执行顺序

```
Phase 1: code-index, doc-index, project-importer (3h)
  ├─ 依赖最少，无特殊处理
  └─ 占 Controller HTTP 调用量的 90%+

Phase 2: importer-tool (1h)
  └─ PostgreSQL 集成，需验证数据库连接

Phase 3: file-watcher (保持独立，不整合)
  └─ 只整理文档说明为何保持独立
```

## 5. 整合后效果

| 指标 | 整合前 | 整合后 |
|------|--------|--------|
| Controller 外部容器 | 6 个 | 1 个 (file-watcher) |
| HTTP 调用延迟 | 1-3ms × 每次 | 0ms (直接函数) |
| 依赖管理 | 5 个独立 requirements.txt | 1 个统一管理 |
| 新增依赖 | — | markdown (doc-index + importer-tool) |