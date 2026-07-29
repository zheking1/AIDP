# AIDP 三层文件索引系统 —— 概述

> **版本**: v1.0  
> **日期**: 2026-07-29  
> **状态**: 规划完成，Layer 1/3 已修复，Layer 2 待开发

---

## 1. 设计目标

当开发者在项目中修改代码后，AIDP 系统能在**最短时间内**获取最新代码变更，更新 code-index 索引和知识库，使 Agent 和 5 阶段管线能始终基于最新代码进行分析和决策。

单一机制不可靠——Agent 可能忘记调用、git commit 频率低、后台进程可能崩溃。**三层防御**保证代码变更一定会被索引：

```
可靠性: Layer 1 > Layer 2 > Layer 3
实时性: Layer 3 > Layer 2 > Layer 1
```

---

## 2. 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│                    开发者本地机器                             │
│                                                             │
│  Layer 3（最实时——保存即触发）                                │
│  ┌──────────────────────────────────┐                       │
│  │  file_watcher.py (watchdog)      │                       │
│  │  检测文件修改/创建/移动           │                       │
│  │  → 3秒防抖 → POST Controller     │                       │
│  └──────────────┬───────────────────┘                       │
│                 │                                           │
│  Layer 1（最可靠——commit 即触发）                             │
│  ┌──────────────────────────────────┐                       │
│  │  .git/hooks/post-commit          │                       │
│  │  每次 commit → sync_changes.py   │                       │
│  │  → git diff → POST Controller    │                       │
│  └──────────────┬───────────────────┘                       │
│                 │                                           │
│  Layer 2（最智能——Agent 主动调用）                            │
│  ┌──────────────────────────────────┐                       │
│  │  MCP index_changes()             │                       │
│  │  Agent 工作后 → 分析变更文件     │                       │
│  │  → 增量索引 + 知识沉淀建议       │                       │
│  └──────────────┬───────────────────┘                       │
│                 │                                           │
└─────────────────┼───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              NAS — AIDP Controller (:8883)                    │
│                                                             │
│  POST /api/tools/code-index/invoke                          │
│    └─→ tool_invoker → code-index:18086/index/project         │
│                                                             │
│  POST /api/classification/import                            │
│    └─→ 文档分类 → knowledge-tool 知识库                      │
│                                                             │
│  MCP index_changes()                                        │
│    └─→ tool_invoker → code-index + evolution 分析            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 配置文件 `.opencode/watcher.json`

由 `aidp_init.py` 自动创建在项目根目录下的 `.opencode/` 目录中。

### 数据模型

```json
{
    "project_id": 42,
    "project_name": "my-project",
    "project_root": "/home/dev/projects/my-project",
    "controller_url": "http://192.168.0.100:8883",
    "created_at": "2026-07-29T10:00:00Z",
    "updated_at": "2026-07-29T10:00:00Z",
    "ignore_dirs": ["node_modules", "__pycache__", ".git"],
    "ignore_patterns": ["*.log", "*.tmp"],
    "sync_enabled": true,
    "layers": {
        "git_hook": true,
        "file_watcher": true,
        "agent": true
    }
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `project_id` | int | ✅ | AIDP Controller 中的项目 ID |
| `project_name` | str | ✅ | 项目名称 |
| `project_root` | str | ✅ | 项目根目录绝对路径 |
| `controller_url` | str | ✅ | Controller 地址 |
| `ignore_dirs` | list | ❌ | 额外忽略目录 |
| `ignore_patterns` | list | ❌ | 额外忽略文件模式 |
| `sync_enabled` | bool | ❌ | 是否启用同步（默认 true） |
| `layers.git_hook` | bool | ❌ | 是否安装 git hook |
| `layers.file_watcher` | bool | ❌ | 是否启用文件监控 |
| `layers.agent` | bool | ❌ | Agent 是否自动索引 |