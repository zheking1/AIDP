"""
AIDP File Watcher — 本地文件监听，自动同步到 NAS
监听项目目录的代码/文档变化，调用 NAS API 增量同步

安装: pip install watchdog
启动: python scripts/file_watcher.py
"""

import os
import sys
import json
import time
import hashlib
import logging
import urllib.request
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent, FileMovedEvent
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

logging.basicConfig(level=logging.INFO, format="[file-watcher] %(message)s")
logger = logging.getLogger("file-watcher")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTROLLER_URL = os.environ.get("AIDP_CONTROLLER_URL", "http://192.168.0.100:8883")

CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb", ".php", ".c", ".cpp", ".cs", ".swift", ".kt", ".vue"}
DOC_EXTS = {".md", ".txt", ".rst", ".adoc"}
IGNORE_DIRS = {"node_modules", "__pycache__", ".git", ".venv", "venv", "env", ".env", "dist", "build", ".idea", ".vscode", ".next", "coverage", ".pytest_cache", ".mypy_cache", ".tox", "target", "bin", "obj"}
IGNORE_PREFIXES = {"."}


class ChangeBuffer:
    """去抖缓存：文件变化后等待 3 秒空闲再推送"""

    def __init__(self, delay=3.0):
        self.delay = delay
        self._changes = {}  # path -> timestamp
        self._timer = None

    def add(self, path):
        self._changes[path] = time.time()
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self.delay, self.flush)
        self._timer.daemon = True
        self._timer.start()

    def flush(self):
        if not self._changes:
            return
        paths = list(self._changes.keys())
        self._changes.clear()
        sync_all(paths)


class SyncHandler(FileSystemEventHandler):
    def __init__(self, buffer: ChangeBuffer):
        self.buffer = buffer

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
            logger.debug(f"modified: {os.path.basename(event.src_path)}")
            self.buffer.add(event.src_path)

    def on_created(self, event):
        if not event.is_directory and self._is_syncable(event.src_path) and not self._should_ignore(event.src_path):
            logger.debug(f"created: {os.path.basename(event.src_path)}")
            self.buffer.add(event.src_path)

    def on_deleted(self, event):
        pass  # 删除暂不处理

    def on_moved(self, event):
        if not event.is_directory and self._is_syncable(event.dest_path) and not self._should_ignore(event.dest_path):
            logger.debug(f"moved: {os.path.basename(event.dest_path)}")
            self.buffer.add(event.dest_path)


def sync_all(file_paths):
    """推送变更到 NAS"""
    code_files = []
    doc_files = []
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
    """增量索引代码文件到 code-index"""
    batch = []
    for fp in file_paths:
        if not os.path.exists(fp):
            continue
        rel = os.path.relpath(fp, str(PROJECT_ROOT)).replace("\\", "/")
        ext = os.path.splitext(fp)[1].lower()
        lang_map = {".py": "python", ".js": "javascript", ".ts": "typescript", ".jsx": "javascript",
                     ".tsx": "typescript", ".java": "java", ".go": "go", ".rs": "rust", ".rb": "ruby",
                     ".php": "php", ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".swift": "swift",
                     ".kt": "kotlin", ".vue": "vue"}
        lang = lang_map.get(ext, "unknown")
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if content.strip():
                batch.append({"path": rel, "content": content, "language": lang})
        except:
            pass
    if not batch:
        return
    try:
        payload = json.dumps({"capability": "code.index_files", "arguments": {"project_id": 3, "files": batch}})
        req = urllib.request.Request(f"{CONTROLLER_URL}/api/tools/code-index/invoke",
                                     data=payload.encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            r = json.loads(resp.read().decode())
            logger.info(f"code: indexed {len(batch)} files")
    except Exception as e:
        logger.warning(f"code sync error: {e}")


def sync_docs(file_paths):
    """增量导入文档到 knowledge + doc-index"""
    docs = []
    for fp in file_paths:
        if not os.path.exists(fp):
            continue
        rel = os.path.relpath(fp, str(PROJECT_ROOT)).replace("\\", "/")
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if content.strip():
                title = os.path.splitext(os.path.basename(fp))[0]
                docs.append({"title": title, "content": content, "filename": rel, "source_uri": rel})
        except:
            pass
    if not docs:
        return
    try:
        payload = json.dumps({"auto_classify": True, "auto_create_kb": True, "documents": docs})
        req = urllib.request.Request(f"{CONTROLLER_URL}/api/classification/import",
                                     data=payload.encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            r = json.loads(resp.read().decode())
            s = r.get("stored", {})
            logger.info(f"docs: imported {len(docs)} files (+{s.get('knowledge',0)}kb +{s.get('rule',0)}rule)")
    except Exception as e:
        logger.warning(f"doc sync error: {e}")


def main():
    if not HAS_WATCHDOG:
        logger.error("watchdog not installed. Run: pip install watchdog")
        sys.exit(1)

    import threading

    buffer = ChangeBuffer(delay=3.0)
    handler = SyncHandler(buffer)
    observer = Observer()
    observer.schedule(handler, str(PROJECT_ROOT), recursive=True)
    observer.start()

    logger.info(f"Watching: {PROJECT_ROOT}")
    logger.info(f"Controller: {CONTROLLER_URL}")
    print()
    print("  File changes detected automatically → synced to AIDP")
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