# 本地脚本自动安装 —— 零手动操作

> **状态**: 设计完成，待开发  
> **依赖**: `06-auto-install.md` MCP 工具

---

## 1. 设计目标

开发者不需要在本地打开终端执行任何命令。所有安装操作由 Agent（MCP 客户端）在开发机上自动完成。

## 2. 架构

```
┌─────────────────────────────────────────────────────┐
│  开发机                                              │
│                                                     │
│  Agent (MCP Client)                                 │
│    │                                                │
│    ├─ 1. 扫描项目文件 → aidp_init(key_files, docs)  │
│    │                                                │
│    ├─ 2. install_local_scripts(project_dir, id)     │
│    │     └─ 返回三个产物                              │
│    │        ├─ watcher.json → Agent 写入本地文件     │
│    │        ├─ git_hook.sh  → Agent 写入 .git/hooks/ │
│    │        └─ start_cmd   → Agent 后台启动进程      │
│    │                                                │
│    └─ 3. 工作: index_changes(task, files, summary)  │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  NAS — AIDP Controller (:8883)                       │
│                                                     │
│  aidp_init()         → 全量索引初始化                │
│  install_local_scripts() → 返回本地安装脚本          │
│  index_changes()     → 增量索引                      │
└─────────────────────────────────────────────────────┘
```

## 3. MCP 工具 `install_local_scripts`

```python
@mcp.tool()
async def install_local_scripts(
    ctx: Context,
    project_dir: str,
    project_id: int,
    layers: str = "all",
) -> str:
    """安装本地索引脚本 — 返回 Agent 写入本地的配置和脚本。

    Args:
        project_dir: 项目根目录绝对路径，如 "/home/dev/projects/my-app"
        project_id: AIDP 项目 ID
        layers: 要安装哪些层，all / git_hook / file_watcher / watcher_config

    Returns:
        JSON 包含三个产物:
        - watcher_config: 写入 .opencode/watcher.json 的 JSON 对象
        - git_hook_script: 写入 .git/hooks/post-commit 的 Shell/Batch 脚本
        - file_watcher_cmd: 启动 file_watcher 的命令行
    """
```

### 返回的 JSON 结构

```json
{
    "success": true,
    "project_id": 42,
    "project_dir": "/home/dev/projects/my-app",
    "controller_url": "http://192.168.0.100:8883",
    "files": {
        "watcher_config": {
            "path": "/home/dev/projects/my-app/.opencode/watcher.json",
            "content": {
                "project_id": 42,
                "project_name": "my-app",
                "project_root": "/home/dev/projects/my-app",
                "controller_url": "http://192.168.0.100:8883",
                "created_at": "2026-07-29T10:00:00Z",
                "layers": { "git_hook": true, "file_watcher": true, "agent": true }
            }
        },
        "git_hook_script": {
            "path": "/home/dev/projects/my-app/.git/hooks/post-commit",
            "content": "@echo off\npython \"%~dp0\\..\\..\\scripts\\sync_changes.py\"",
            "os": "windows",
            "note": "Agent 需要创建此文件并 chmod +x (Linux/Mac)"
        },
        "file_watcher_cmd": {
            "command": "python scripts/file_watcher.py -d /home/dev/projects/my-app -p 42",
            "os": "cross-platform",
            "note": "Agent 将其作为后台进程启动。Windows 用 Start-Process, Linux/Mac 用 nohup &"
        }
    },
    "agent_actions": [
        "创建 .opencode/watcher.json",
        "创建 .git/hooks/post-commit",
        "启动 file_watcher.py 后台进程"
    ]
}
```

## 4. Agent 执行指令（文给 Agent 看）

Agent 收到 `install_local_scripts` 的返回后，按以下步骤执行：

```
1. 读取 response.files.watcher_config
   └─ 确保 .opencode/ 目录存在
   └─ 写入 watcher.json

2. 读取 response.files.git_hook_script
   └─ 确保 .git/hooks/ 目录存在
   └─ 使用 Execute工具写入脚本:
        bash -c 'echo "...content..." > .git/hooks/post-commit'
        chmod +x .git/hooks/post-commit  (Linux/Mac)

3. 读取 response.files.file_watcher_cmd
   └─ 使用 Execute工具凌晨启动:
        nohup python scripts/file_watcher.py -d {dir} -p {id} &
        (Windows: Start-Process -WindowStyle Hidden)

4. 验证安装:
   └─ cat .opencode/watcher.json → 检查 project_id 正确
   └─ ls -la .git/hooks/post-commit → 检查文件存在
   └─ pgrep file_watcher → 检查进程运行
```

## 5. 完整零手动流程

```
Agent 初始化一个新项目:

Step 1: 扫描目录
  bash: find /project -type f -name "*.py" -o -name "*.ts" | head -30

Step 2: 读取文件内容
  bash: cat /project/src/main.py
  bash: cat /project/src/auth/login.py
  ... (批量读取)

Step 3: 服务端全量索引
  aidp_init(
    project_name="my-app",
    tech_stack="Python 3.13 + FastAPI",
    key_files=[...],       ← 从 Step 2 获取
    docs=[
      {"title":"README","content":"..."},
      {"title":"ARCHITECTURE","content":"..."}
    ]
  )
  → 返回 project_id: 42

Step 4: 安装本地脚本
  install_local_scripts(
    project_dir="/home/dev/projects/my-app",
    project_id=42,
    layers="all"
  )
  → 返回 watcher.json + git hook + watcher cmd

Step 5: Agent 执行安装指令
  write_file(".opencode/watcher.json", response.files.watcher_config)
  write_file(".git/hooks/post-commit", response.files.git_hook_script)
  execute("nohup python scripts/file_watcher.py -d . -p 42 &")

Step 6: 验证
  aidp_context(project_name="my-app", task="test")
  → 确认上下文加载正常，所有索引可用

完成！后续开发:
  - git commit → git hook → 自动同步
  - 文件保存 → file_watcher → 自动同步
  - Agent 调用 index_changes → 增量索引 + 模式分析
```

## 6. 与现有工具的关系

| MCP 工具 | 作用 | 是否需要本地文件 |
|------|------|:---:|
| `aidp_init` | 全量初始化（服务端） | 提供文件内容即可 |
| `install_local_scripts` | 生成本地安装产物 | ❌ |
| `index_changes` | 增量索引 | 提供变更内容即可 |
| `aidp_context` | 加载项目上下文 | ❌ |

Agent 全程只需调用 MCP 工具 + 写入本地文件，不需要开发者手动打开终端。