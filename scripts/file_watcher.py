"""
AIDP File Watcher — 本地球文件监听，自动同步到 Controller
检测代码/文档变化 → 防抖3秒 → 增量索引到 code-index + knowledge

安装: pip install watchdog
启动: python scripts/file_watcher.py --project-dir . --project-id 42
"""

import os
import re
import sys
import json
import time
import hashlib
import argparse
import threading
import logging
import urllib.request
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

logging.basicConfig(level=logging.INFO, format="[file-watcher] %(message)s")
logger = logging.getLogger("file-watcher")

CONTROLLER_URL = os.environ.get("AIDP_CONTROLLER_URL", "http://192.168.0.100:8883")

CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb",
             ".php", ".c", ".cpp", ".cs", ".swift", ".kt", ".vue", ".scala", ".r"}
DOC_EXTS = {".md", ".txt", ".rst", ".adoc", ".rdoc"}
IGNORE_DIRS = {"node_modules", "__pycache__", ".git", ".venv", "venv", "env",
               ".env", "dist", "build", ".idea", ".vscode", ".next", "coverage",
               ".pytest_cache", ".mypy_cache", ".tox", "target", "bin", "obj"}
IGNORE_PREFIXES = {"."}

LANG_MAP = {".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
            ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
            ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".swift": "swift",
            ".kt": "kotlin", ".vue": "vue", ".scala": "scala", ".r": "r"}


def load_watcher_config(project_dir):
    """从 .opencode/watcher.json 读取项目配置"""
    config_path = Path(project_dir) / ".opencode" / "watcher.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


class ChangeBuffer:
    """去抖缓存：文件变化后等待 N 秒空闲再推送"""

    def __init__(self, delay=3.0):
        self.delay = delay
        self._changes = {}
        self._timer = None
        self._lock = threading.Lock()

    def add(self, path):
        with self._lock:
            self._changes[path] = time.time()
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.delay, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self):
        with self._lock:
            if not self._changes:
                return
            paths = list(self._changes.keys())
            self._changes.clear()
        if paths:
            sync_all(paths)


class SyncHandler(FileSystemEventHandler):
    def __init__(self, buffer, project_root):
        super().__init__()
        self.buffer = buffer
        self.project_root = str(project_root)

    def _should_ignore(self, path):
        path = path.replace("\\", "/")
        parts = path.split("/")
        for p in parts:
            if p in IGNORE_DIRS or p.startswith("."):
                return True
        return False

    def _is_syncable(self, path):
        ext = os.path.splitext(path)[1].lower()
        return ext in CODE_EXTS or ext in DOC_EXTS

    def on_modified(self, event):
        if not event.is_directory and self._is_syncable(event.src_path) and not self._should_ignore(event.src_path):
            self.buffer.add(event.src_path)

    def on_created(self, event):
        if not event.is_directory and self._is_syncable(event.src_path) and not self._should_ignore(event.src_path):
            self.buffer.add(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and self._is_syncable(event.dest_path) and not self._should_ignore(event.dest_path):
            self.buffer.add(event.dest_path)


# 全局状态，由 main() 设置
_project_root = None
_project_id = 0


def sync_all(file_paths):
    code_files, doc_files = [], []
    for fp in file_paths:
        ext = os.path.splitext(fp)[1].lower()
        if ext in CODE_EXTS:
            code_files.append(fp)
        elif ext in DOC_EXTS:
            doc_files.append(fp)
    if code_files:
        sync_code(code_files)
    if doc_files:
        sync_docs(doc_files)


def sync_code(file_paths):
    batch = []
    for fp in file_paths:
        if not os.path.exists(fp):
            continue
        rel = os.path.relpath(fp, _project_root).replace("\\", "/")
        ext = os.path.splitext(fp)[1].lower()
        lang = LANG_MAP.get(ext, "unknown")
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if content.strip():
                batch.append({"path": rel, "content": content, "language": lang})
        except Exception:
            pass
    if not batch:
        return
    try:
        payload = json.dumps({
            "capability": "code.index_files",
            "arguments": {"project_id": _project_id, "files": batch}
        })
        req = urllib.request.Request(
            f"{CONTROLLER_URL}/api/tools/code-index/invoke",
            data=payload.encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            urllib.request.urlopen(req, timeout=60)
            logger.info(f"code: indexed {len(batch)} files (project {_project_id})")
    except Exception as e:
        logger.warning(f"code sync error: {e}")


def sync_docs(file_paths):
    docs = []
    for fp in file_paths:
        if not os.path.exists(fp):
            continue
        rel = os.path.relpath(fp, _project_root).replace("\\", "/")
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if content.strip():
                title = os.path.splitext(os.path.basename(fp))[0]
                docs.append({"title": title, "content": content, "filename": rel, "source_uri": rel})
        except Exception:
            pass
    if not docs:
        return
    try:
        payload = json.dumps({"auto_classify": True, "auto_create_kb": True, "documents": docs})
        req = urllib.request.Request(
            f"{CONTROLLER_URL}/api/classification/import",
            data=payload.encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            logger.info(f"docs: imported {len(docs)} files")
    except Exception as e:
        logger.warning(f"doc sync error: {e}")


def main():
    global _project_root, _project_id

    parser = argparse.ArgumentParser(description="AIDP File Watcher - 本地文件监听自动同步")
    parser.add_argument("--project-dir", "-d", default=None, help="项目根目录 (默认: 当前目录)")
    parser.add_argument("--project-id", "-p", type=int, default=0, help="AIDP 项目 ID (必填)")
    parser.add_argument("--controller-url", default=None, help="Controller URL")
    args = parser.parse_args()

    project_dir = args.project_dir or "."
    _project_root = os.path.abspath(project_dir)
    _project_id = args.project_id

    if args.controller_url:
        global CONTROLLER_URL
        CONTROLLER_URL = args.controller_url

    # Try loading from .opencode/watcher.json if project_id not provided
    if not _project_id:
        config = load_watcher_config(_project_root)
        _project_id = config.get("project_id", 0)
        if not _project_id:
            logger.error("No project_id provided. Use --project-id or ensure .opencode/watcher.json exists")
            logger.error("  python scripts/file_watcher.py --project-dir . --project-id 42")
            sys.exit(1)

    if not HAS_WATCHDOG:
        logger.error("watchdog not installed. Run: pip install watchdog")
        sys.exit(1)

    buffer = ChangeBuffer(delay=3.0)
    handler = SyncHandler(buffer, _project_root)
    observer = Observer()
    observer.schedule(handler, _project_root, recursive=True)
    observer.start()

    logger.info(f"Project ID: {_project_id}")
    logger.info(f"Watching:   {_project_root}")
    logger.info(f"Controller: {CONTROLLER_URL}")
    logger.info(f"Extensions: code={len(CODE_EXTS)} doc={len(DOC_EXTS)}")
    print()
    print("  File changes detected automatically -> synced to AIDP")
    print("  Press Ctrl+C to stop")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    logger.info("stopped")


if __name__ == "__main__":
    main()