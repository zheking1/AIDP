# Layer 3 — File Watcher (watchdog 实时监控)

> 最实时的一层。文件保存即触发，3 秒防抖后增量推送。

---

## 1. 触发机制

```
开发者保存文件 (Ctrl+S)
    │
    ▼
watchdog Observer 检测到 FileModifiedEvent
    │
    ▼
ChangeBuffer.add(path)  → 重新计时 3 秒
    │
    ▼
3 秒内无新变化 → flush()
    │
    ▼
sync_all(paths)  → 分类为 code/docs → 批量 POST Controller
```

## 2. 启动方式

```bash
python scripts/file_watcher.py \
    --project-dir /path/to/project \
    --project-id 42 \
    [--controller-url http://192.168.0.100:8883]
```

**参数**：
| 参数 | 必填 | 默认 | 说明 |
|------|:---:|------|------|
| `--project-dir` (`-d`) | 否 | `.` | 项目根目录 |
| `--project-id` (`-p`) | 否* | 从 json 读取 | AIDP 项目 ID |
| `--controller-url` | 否 | 环境变量 | Controller 地址 |

\* 若未提供且 `.opencode/watcher.json` 不存在则报错退出

## 3. 执行逻辑（伪代码）

```python
def main():
    project_dir = args.project_dir or "."
    project_id  = args.project_id or load_from_watcher_json()

    # 1. 启动 watchdog
    buffer = ChangeBuffer(delay=3.0)
    handler = SyncHandler(buffer, project_dir)
    observer = Observer()
    observer.schedule(handler, project_dir, recursive=True)
    observer.start()

    # 2. 死循环监听
    while True:
        time.sleep(1)

def on_modified(event):
    if is_syncable(event.src_path) and not ignored(event.src_path):
        buffer.add(event.src_path)  # 重新计时 3 秒
```

## 4. ChangeBuffer 设计

```python
class ChangeBuffer:
    def __init__(self, delay=3.0):
        self._changes = {}   # path → timestamp
        self._timer = None   # threading.Timer
        self._lock = threading.Lock()

    def add(self, path):
        # 线程安全：加锁写入，取消旧计时器，启动新计时器
        with self._lock:
            self._changes[path] = time.time()
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.delay, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self):
        with self._lock:
            paths = list(self._changes.keys())
            self._changes.clear()
        if paths:
            sync_all(paths)  # 在锁外执行网络请求
```

### 为什么用 `threading.Timer` 而不是 `asyncio`

- watchdog 的回调在线程中运行，不是 asyncio 事件循环
- `threading.Timer` 天然适合"延迟 N 秒执行"场景
- 线程安全问题：ChangeBuffer 的所有操作加锁，防抖计时器取消和重启是原子的
- `_flush()` 的网络请求在锁外执行，避免阻塞新的 change 入队

### 为什么设为 3 秒

在 IDE 中连续编辑时，`on_modified` 在每次保存（或自动保存）触发。3 秒窗口内多次保存会被合并为一次批量推送，避免大量细碎 API 调用。

## 5. 同步逻辑

```python
def sync_code(file_paths, project_id):
    batch = []
    for fp in file_paths:
        rel = os.path.relpath(fp, project_root)
        lang = detect_language(fp)          # .py→python, .js→javascript
        content = read_file(fp)             # UTF-8, errors=ignore
        batch.append({"path": rel, "content": content, "language": lang})

    POST /api/tools/code-index/invoke {
        capability: "code.index_files",
        arguments: { project_id: project_id, files: batch }
    }

def sync_docs(file_paths):
    docs = []
    for fp in file_paths:
        rel = os.path.relpath(fp, project_root)
        title = path_to_title(fp)           # README.md → "README"
        content = read_file(fp)
        docs.append({
            "title": title,
            "content": content,
            "filename": rel,
            "source_uri": rel
        })

    POST /api/classification/import {
        auto_classify: true,
        auto_create_kb: true,
        documents: docs
    }
```

## 6. 文件过滤规则

与 Layer 1 相同——代码扩展名、文档扩展名、跳过目录。详见 Layer 1 文档。

## 7. 启动管理

### 手动启动
```bash
python scripts/file_watcher.py -d /my-project -p 42
```

### 后台运行（Windows）
```powershell
Start-Process python -ArgumentList "scripts\file_watcher.py -d . -p 42" -WindowStyle Hidden
```

### 开机自启（TODO）
未来可以集成到系统服务或 IDE 插件中。当前需手动启动。

## 8. 日志输出

```
[file-watcher] Project ID: 42
[file-watcher] Watching:   /home/dev/projects/my-project
[file-watcher] Controller: http://192.168.0.100:8883
[file-watcher] Extensions: code=14 doc=4

  File changes detected automatically -> synced to AIDP
  Press Ctrl+C to stop

[file-watcher] code: indexed 3 files (project 42)
[file-watcher] docs: imported 1 files
```