import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class PooledContainer:
    container_id: str
    image: str
    status: str = "ready"
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    memory_limit: int = 128 * 1024 * 1024
    cpu_limit: float = 0.5


class ContainerPool:
    """容器池管理器"""

    def __init__(self, min_size: int = 5, max_size: int = 20, idle_timeout: int = 300):
        self.min_size = min_size
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        self.pool: Dict[str, PooledContainer] = {}
        self._initialized = False

    async def initialize(self):
        for i in range(self.min_size):
            cid = f"pooled-{i}-{int(datetime.now().timestamp())}"
            self.pool[cid] = PooledContainer(container_id=cid, image="sandbox-python:latest")
        self._initialized = True

    async def acquire(self, requirements: Dict = None) -> PooledContainer:
        for container in self.pool.values():
            if container.status == "ready":
                container.status = "busy"
                container.last_used = datetime.now()
                return container
        if len(self.pool) < self.max_size:
            cid = f"pooled-{len(self.pool)}-{int(datetime.now().timestamp())}"
            c = PooledContainer(container_id=cid, image="sandbox-python:latest", status="busy")
            self.pool[cid] = c
            return c
        for _ in range(30):
            for container in self.pool.values():
                if container.status == "ready":
                    container.status = "busy"
                    return container
            await asyncio.sleep(0.1)
        raise TimeoutError("No container available")

    async def release(self, container_id: str):
        if container_id in self.pool:
            self.pool[container_id].status = "ready"
            self.pool[container_id].last_used = datetime.now()

    async def cleanup_loop(self):
        while True:
            await asyncio.sleep(60)
            now = datetime.now()
            to_remove = []
            for cid, c in self.pool.items():
                if c.status == "ready" and (now - c.last_used).seconds > self.idle_timeout:
                    to_remove.append(cid)
            for cid in to_remove:
                del self.pool[cid]
            while len(self.pool) < self.min_size:
                cid = f"pooled-replenish-{len(self.pool)}"
                self.pool[cid] = PooledContainer(container_id=cid, image="sandbox-python:latest")

    def get_stats(self) -> Dict:
        return {
            "total": len(self.pool),
            "ready": sum(1 for c in self.pool.values() if c.status == "ready"),
            "busy": sum(1 for c in self.pool.values() if c.status == "busy"),
        }


class SecurityEngine:
    """安全检查引擎"""

    DANGEROUS = {
        "python": ["exec", "eval", "compile", "__import__", "open", "os.system", "subprocess.call", "socket", "urllib"],
        "javascript": ["eval", "Function", "setTimeout", "setInterval", "require", "fetch"],
    }

    DANGEROUS_PATTERNS = [
        r"__.*__", r"import\s+os", r"os\.system\(", r"subprocess\.", r"exec\(", r"eval\(",
    ]

    def check(self, code: str, language: str = "python") -> Dict:
        violations = []
        import re
        for func in self.DANGEROUS.get(language, []):
            if func in code:
                violations.append({"type": "dangerous_function", "function": func, "severity": "high",
                                   "message": f"使用了危险函数: {func}"})
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                violations.append({"type": "dangerous_pattern", "pattern": pattern, "severity": "medium",
                                   "message": f"匹配到危险模式: {pattern}"})
        lines = code.split("\n")
        if len(lines) > 1000:
            violations.append({"type": "resource_limit", "severity": "low", "message": "代码行数超过1000"})

        high = sum(1 for v in violations if v["severity"] == "high")
        threat = "critical" if high > 0 else ("medium" if violations else "none")
        return {"passed": len(violations) == 0, "threat_level": threat, "violations": violations,
                "recommendations": [f"避免使用 {v['function']}" for v in violations if v["type"] == "dangerous_function"]}


class TimeoutManager:
    """超时管理器"""

    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.timeout_history = []

    async def execute(self, func, task_id: str, timeout: int = 30) -> Dict:
        task = asyncio.create_task(func())
        self.active_tasks[task_id] = task
        try:
            result = await asyncio.wait_for(task, timeout=timeout)
            self.timeout_history.append({"task_id": task_id, "status": "completed"})
            return {"status": "completed", "result": result}
        except asyncio.TimeoutError:
            task.cancel()
            self.timeout_history.append({"task_id": task_id, "status": "timeout"})
            return {"status": "timeout", "error": f"Execution timed out after {timeout}s"}
        finally:
            self.active_tasks.pop(task_id, None)

    async def cancel(self, task_id: str):
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            self.active_tasks.pop(task_id, None)


class ContextManager:
    """执行上下文管理器"""

    def __init__(self):
        self.contexts: Dict[str, dict] = {}

    def create(self, task_id: str, user_id: str, project_id: str, language: str) -> Dict:
        ctx = {"task_id": task_id, "user_id": user_id, "project_id": project_id,
               "language": language, "variables": {}, "imports": [], "output": [], "errors": [], "status": "created"}
        self.contexts[task_id] = ctx
        return ctx

    def get(self, task_id: str) -> Optional[Dict]:
        return self.contexts.get(task_id)

    def add_variable(self, task_id: str, name: str, value) -> bool:
        if task_id in self.contexts:
            self.contexts[task_id]["variables"][name] = value
            return True
        return False

    def close(self, task_id: str) -> bool:
        if task_id in self.contexts:
            self.contexts[task_id]["status"] = "closed"
            del self.contexts[task_id]
            return True
        return False