# AIDP 三层文件索引 —— 集成开发指南

> **目标受众**: AI Agent / 开发者  
> **前置知识**: AIDP 系统架构、MCP 协议、git 工作流

---

## 1. 快速开始

### 1.1 安装三层索引（项目初始化时自动完成）

```bash
# 在项目目录执行
python scripts/aidp_init.py \
    --project-dir /path/to/project \
    --project-name my-project
```

**自动执行**：
1. 创建 AIDP 项目记录
2. 全量扫描并索引所有代码文件
3. 写入 `.opencode/watcher.json` 配置文件
4. 安装 `.git/hooks/post-commit` hook

**手动补充**：
```bash
# 启动文件监控（终端保持运行）
python scripts/file_watcher.py -d . -p 42
```

### 1.2 验证安装

```bash
# 检查 hook 是否安装
ls -la .git/hooks/post-commit

# 检查配置
cat .opencode/watcher.json

# 测试 hook
python scripts/sync_changes.py -p 42

# 测试 file watcher
python scripts/file_watcher.py -d . -p 42
```

---

## 2. 开发工作流

### 2.1 日常开发流程

```
1. 编辑代码
   └─ file_watcher 自动检测变动 → 3秒后推送到 Controller

2. git commit
   └─ post-commit hook → sync_changes.py → 差量索引

3. Agent 完成任务后
   └─ index_changes(task, files, summary) → 增量索引 + 模式分析
```

### 2.2 Agent 最佳实践

```python
# Agent 完成开发任务后务必调用
result = await index_changes(
    task="修复了登录页面的 cookie 失效问题",
    changed_files='[
        {"path":"src/auth/login.py","content":"...","language":"python"},
        {"path":"src/auth/cookie.py","content":"...","language":"python"}
    ]',
    summary="移除了 cookie 中的硬编码过期时间，改为从配置读取"
)
```

---

## 3. 故障处理

### 3.1 file_watcher 没有反应

```bash
# 检查 watchdog 是否安装
pip install watchdog

# 手动运行看日志
python scripts/file_watcher.py -d . -p 42

# 日志中应有 "Watching: /path/to/project"
```

### 3.2 git hook 没有触发

```bash
# 确认 hook 文件存在
cat .git/hooks/post-commit

# 手动执行同步
python scripts/sync_changes.py -p 42

# 重新安装 hook
python scripts/aidp_init.py --project-dir . --project-name my-project
```

### 3.3 Controller 返回错误

```bash
# 检查 Controller 是否运行
curl http://192.168.0.100:8883/health

# 检查 code-index 是否运行
curl http://192.168.0.100:18086/health

# 网络检查
ping 192.168.0.100
```

---

## 4. 配置文件详解

### 4.1 watcher.json 各层开关

```json
{
    "layers": {
        "git_hook": true,      // 设为 false 停用 git hook
        "file_watcher": true,   // 设为 false 停用后台监控
        "agent": true            // 设为 false 停用 Agent 自动索引
    }
}
```

### 4.2 忽略额外目录

```json
{
    "ignore_dirs": ["vendor", "bower_components"],
    "ignore_patterns": ["*.generated.*"]
}
```

---

## 5. 性能考虑

| 操作 | 耗时 | 说明 |
|------|:---:|------|
| file_watcher 检测 | < 10ms | 文件系统事件，几乎无开销 |
| sync_changes 差量 | 1-3s | 取决于变更文件数量和大小 |
| aidp_init 全量 | 10-60s | 取决于项目文件数量 |
| MCP index_changes | 1-5s | 取决于 Agent 工作产物数量 |

文件内容限制：每文件 ≤ 200KB，批量推送每批 ≤ 10 文件。

---

## 6. 文件清单

| 文件 | 用途 | 位置 |
|------|------|------|
| `aidp_init.py` | 项目初始化（含 hook 安装） | `scripts/` |
| `sync_changes.py` | Git hook 辅助脚本 | `scripts/` |
| `file_watcher.py` | 后台文件监控守护进程 | `scripts/` |
| `tech_scan.py` | 技术栈扫描器 | `scripts/` |
| `watcher.json` | 项目配置 | `.opencode/`（本地） |
| `post-commit` | Git hook 入口 | `.git/hooks/`（本地） |

---

## 7. 待开发项

- [ ] **Agent MCP `index_changes` 工具** — 当前只有 Layer 1 (git hook) 和 Layer 3 (file watcher) 完整实现，Layer 2 待开发
- [ ] **跨平台 Git Hook** — 当前仅生成 Windows `.bat`，需支持 Bash/Shell 脚本
- [ ] **file_watcher 系统服务化** — 当前需手动启动，可封装为 systemd/Windows Service
- [ ] **IDE 插件集成** — VS Code / IntelliJ 插件自动管理 file_watcher 生命周期