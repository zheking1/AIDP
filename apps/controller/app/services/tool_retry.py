import asyncio
import logging
from typing import Any, Callable, Dict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_exceptions: tuple = (Exception,)


class ToolRetryManager:
    """工具重试管理器"""

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
        }

    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    self.stats["successful_retries"] += 1
                return result
            except self.config.retryable_exceptions as e:
                last_exception = e

                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt)
                    self.stats["total_retries"] += 1
                    logger.warning(
                        "Retry %d/%d after %.1fs for error: %s",
                        attempt + 1, self.config.max_retries, delay, e
                    )
                    await asyncio.sleep(delay)

        self.stats["failed_retries"] += 1
        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** attempt)
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = self.config.base_delay * self._fibonacci(attempt + 1)
        else:
            delay = self.config.base_delay

        return min(delay, self.config.max_delay)

    def _fibonacci(self, n: int) -> int:
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    def get_stats(self) -> Dict:
        return self.stats


class FallbackManager:
    """降级管理器"""

    class DegradationLevel:
        FULL = 0
        PARTIAL = 1
        MINIMAL = 2
        EMERGENCY = 3

    LEVEL_NAMES = {0: "FULL", 1: "PARTIAL", 2: "MINIMAL", 3: "EMERGENCY"}

    def __init__(self):
        self.degradation_level = self.DegradationLevel.FULL
        self.failed_tools = set()

    def handle_tool_failure(self, tool_name: str, error: Exception) -> str:
        self.failed_tools.add(tool_name)
        self._update_degradation_level()
        logger.warning(
            "Tool %s failed, degradation level: %s (%d tools failed: %s)",
            tool_name, self.LEVEL_NAMES[self.degradation_level],
            len(self.failed_tools), ", ".join(sorted(self.failed_tools))
        )

        if tool_name == "memory-tool":
            return "Memory tool temporarily unavailable, using cached memories."
        elif tool_name == "knowledge-tool":
            return "Knowledge base temporarily unavailable, using basic knowledge."
        elif tool_name == "code-index":
            return "Code index temporarily unavailable, using project structure info."
        elif tool_name == "quality-tool":
            return "Quality check temporarily unavailable, skipping quality scoring."
        else:
            return f"Tool {tool_name} temporarily unavailable."

    def _update_degradation_level(self):
        count = len(self.failed_tools)
        if count == 0:
            self.degradation_level = self.DegradationLevel.FULL
        elif count == 1:
            self.degradation_level = self.DegradationLevel.PARTIAL
        elif count <= 3:
            self.degradation_level = self.DegradationLevel.MINIMAL
        else:
            self.degradation_level = self.DegradationLevel.EMERGENCY

    def get_status(self) -> Dict:
        return {
            "level": self.degradation_level,
            "level_name": self.LEVEL_NAMES[self.degradation_level],
            "failed_tools": list(self.failed_tools),
            "is_degraded": self.degradation_level != self.DegradationLevel.FULL,
        }