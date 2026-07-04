import asyncio
from typing import Dict, Callable, List


class ConcurrencyController:
    def __init__(self):
        self.file_locks: Dict[str, asyncio.Lock] = {}
        self.modification_queue: asyncio.Queue = asyncio.Queue()

    async def acquire_lock(self, file_path: str):
        if file_path not in self.file_locks:
            self.file_locks[file_path] = asyncio.Lock()
        await self.file_locks[file_path].acquire()

    async def release_lock(self, file_path: str):
        if file_path in self.file_locks:
            self.file_locks[file_path].release()

    async def submit_modification(self, task: Callable, file_path: str):
        await self.acquire_lock(file_path)
        try:
            if asyncio.iscoroutinefunction(task):
                await task()
            else:
                task()
        finally:
            await self.release_lock(file_path)

    async def query_parallel(self, tasks: List[Callable]) -> List:
        coros = []
        for t in tasks:
            if asyncio.iscoroutinefunction(t):
                coros.append(t())
            else:
                coros.append(asyncio.to_thread(t))
        return await asyncio.gather(*coros)
