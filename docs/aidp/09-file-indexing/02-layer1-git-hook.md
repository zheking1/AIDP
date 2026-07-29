# Layer 1 — Git Post-Commit Hook

> 最可靠的一层。每次 `git commit` 触发，差量同步变更文件。

---

## 1. 触发机制

```bash
git commit -m "fix: ..."
    │
    ▼
.git/hooks/post-commit  (由 aidp_init.py 自动安装)
    │
    ▼
python scripts/sync_changes.py
    │
    ├─ git diff HEAD~1 HEAD --name-only  → 获取变更文件列表
    │
    ├─ 过滤：排除 node_modules/__pycache__/.git 等目录
    ├─ 分类：代码文件 (.py/.js/.ts...) vs 文档文件 (.md/.txt...)
    │
    ├─ 代码 → POST /api/tools/code-index/invoke
    │         capability: "code.index_files"
    │         arguments: { project_id: 42, files: [...] }
    │
    └─ 文档 → POST /api/classification/import
              { auto_classify: true, documents: [...] }
```

## 2. 文件位置

- **Hook 脚本**: `.git/hooks/post-commit`（batch 文件，Windows）
- **执行脚本**: `scripts/sync_changes.py`

## 3. 安装方式

由 `aidp_init.py` 在执行完整初始化时自动安装（第 6 阶段 "install_local"），写入内容：

```bat
@echo off
python "%~dp0\..\..\scripts\sync_changes.py"
```

## 4. CLI 参数

```bash
python scripts/sync_changes.py [--project-id 42]
```

`--project-id`: AIDP 项目 ID。不提供时从 `.opencode/watcher.json` 自动读取。

## 5. 执行逻辑（伪代码）

```python
def main():
    project_id = args.project_id or load_from_watcher_json()

    # 1. 获取变更文件
    files = run("git diff HEAD~1 HEAD --name-only")

    # 2. 分类
    code_files = [f for f in files if ext(f) in CODE_EXTS]
    doc_files  = [f for f in files if ext(f) in DOC_EXTS]

    # 3. 差量索引
    if code_files:
        batch = read_files(code_files)  # [{path, content, language}]
        POST /api/tools/code-index/invoke {
            capability: "code.index_files",
            arguments: { project_id, files: batch }
        }

    # 4. 差量文档
    if doc_files:
        docs = read_docs(doc_files)  # [{title, content, filename}]
        POST /api/classification/import {
            auto_classify: true,
            documents: docs
        }
```

## 6. 文件过滤规则

**代码扩展名**：`.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.java`, `.go`, `.rs`, `.c`, `.cpp`, `.h`, `.cs`, `.rb`, `.php`, `.swift`, `.kt`

**文档扩展名**：`.md`, `.txt`, `.rst`, `.adoc`

**跳过目录**：`node_modules`, `__pycache__`, `.git`, `.venv`, `venv`, `dist`, `build`, `.idea`

## 7. 设计要点

### 7.1 project_id 来源
1. CLI `--project-id` 参数（优先）
2. `.opencode/watcher.json` 中的 `project_id` 字段

### 7.2 链式 commit 处理
不支持。仅同步最近一个 commit 的变更（`HEAD~1..HEAD`）。连续多次 commit 会每次触发一次同步。

### 7.3 首次 commit 处理
如果没有 `HEAD~1`（首次提交），`sync_changes.py` 返回空、不报错。完整索引由 `aidp_init.py` 的 Step 4 批量上传完成。

### 7.4 跨平台适配
当前产生的 hook 是 Windows `.bat` 格式。如需 Mac/Linux 支持，`aidp_init.py` 需根据平台生成不同格式。

### 7.5 代码片段大小限制
每文件最大 200KB，超过不上传。批量上传时每批最多 10 个文件。