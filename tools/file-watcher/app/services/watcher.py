import os
import asyncio
import httpx
from typing import Dict, Set
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent, FileMovedEvent
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db.models import WatchedProject, WatchEvent
from app.services.project_mapper import ProjectMapper


CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".cpp", ".c", ".h", ".vue", ".kt"}


class DebouncedIndexer:
    def __init__(self, delay: float = None):
        self.delay = delay or settings.DEBOUNCE_SECONDS
        self._pending: Dict[int, Set[str]] = {}
        self._timers: Dict[int, asyncio.Timer] = {}
        self._lock = asyncio.Lock()

    async def add_event(self, project_id: int, file_path: str):
        async with self._lock:
            if project_id not in self._pending:
                self._pending[project_id] = set()
            self._pending[project_id].add(file_path)

            if project_id in self._timers:
                self._timers[project_id].cancel()

            timer = asyncio.Timer(self.delay, lambda pid=project_id: asyncio.create_task(self._process(pid)))
            self._timers[project_id] = timer
            timer.start()

    async def _process(self, project_id: int):
        async with self._lock:
            files = self._pending.pop(project_id, set())
            self._timers.pop(project_id, None)

        for file_path in files:
            await self._index_file(project_id, file_path)

    async def _index_file(self, project_id: int, file_path: str):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.CODE_INDEX_URL}/api/index/file",
                    json={"project_id": project_id, "file_path": file_path},
                )
                resp.raise_for_status()
        except Exception as e:
            print(f"[FileWatcher] Index error for {file_path}: {e}")


class FileWatcherHandler(FileSystemEventHandler):
    def __init__(self, project: WatchedProject, indexer: DebouncedIndexer, db_factory, loop):
        self.project = project
        self.indexer = indexer
        self.db_factory = db_factory
        self.loop = loop

    def _schedule(self, coro):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self.loop)

    def _get_relative_path(self, path: str) -> str:
        return os.path.relpath(path, self.project.local_path).replace("\\", "/")

    def _should_ignore(self, path: str) -> bool:
        parts = path.replace("\\", "/").split("/")
        ignored = set(self.project.ignored_dirs or []) | set(settings.IGNORED_DIRS)
        for part in parts:
            if part in ignored:
                return True
        return False

    def _is_code_file(self, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in CODE_EXTENSIONS

    def on_modified(self, event):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path) or not self._is_code_file(event.src_path):
            return
        rel_path = self._get_relative_path(event.src_path)
        self._schedule(self._queue_event("modified", rel_path))

    def on_created(self, event):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path) or not self._is_code_file(event.src_path):
            return
        rel_path = self._get_relative_path(event.src_path)
        self._schedule(self._queue_event("created", rel_path))

    def on_deleted(self, event):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path) or not self._is_code_file(event.src_path):
            return
        rel_path = self._get_relative_path(event.src_path)
        self._schedule(self._queue_event("deleted", rel_path))

    def on_moved(self, event):
        if event.is_directory:
            return
        if self._is_code_file(event.src_path):
            rel_path = self._get_relative_path(event.src_path)
            self._schedule(self._queue_event("deleted", rel_path))
        if self._is_code_file(event.dest_path):
            rel_path = self._get_relative_path(event.dest_path)
            self._schedule(self._queue_event("created", rel_path))

    async def _queue_event(self, event_type: str, file_path: str):
        try:
            async with self.db_factory() as db:
                event_record = WatchEvent(
                    project_id=self.project.id,
                    event_type=event_type,
                    file_path=file_path,
                )
                db.add(event_record)
                await db.commit()

            if event_type in ("modified", "created"):
                await self.indexer.add_event(self.project.code_index_project_id, file_path)
        except Exception as e:
            print(f"[FileWatcher] Queue event error: {e}")


class FileWatcherService:
    def __init__(self):
        self.observer = Observer()
        self.indexer = DebouncedIndexer()
        self.watched: Dict[int, str] = {}
        self.db_factory = None
        self._running = False
        self._loop = None

    def set_db_factory(self, db_factory):
        self.db_factory = db_factory

    async def start(self):
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_running_loop()
        self.observer.start()

    async def stop(self):
        if not self._running:
            return
        self._running = False
        self.observer.stop()
        self.observer.join()

    async def add_watched_project(self, project: WatchedProject):
        if project.id in self.watched:
            return

        if not os.path.exists(project.local_path):
            print(f"[FileWatcher] Path does not exist: {project.local_path}")
            return

        handler = FileWatcherHandler(project, self.indexer, self.db_factory, self._loop)
        self.observer.schedule(handler, project.local_path, recursive=True)
        self.watched[project.id] = project.local_path
        print(f"[FileWatcher] Watching: {project.local_path} -> {project.project_name}")

    async def remove_watched_project(self, project_id: int):
        if project_id not in self.watched:
            return

        path = self.watched.pop(project_id)
        for watch in self.observer.emitters:
            if watch.key and path in str(watch.key):
                watch.stop()
                break
        print(f"[FileWatcher] Stopped watching: {path}")

    async def rescan_project(self, project: WatchedProject):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{settings.CODE_INDEX_URL}/api/index/directory",
                    json={
                        "project_id": project.code_index_project_id,
                        "dir_path": project.local_path,
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            return {"error": str(e)}


watcher_service = FileWatcherService()
