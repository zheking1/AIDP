from typing import Dict, Optional
from datetime import datetime
import redis


class CallStats:
    def __init__(self, redis_url: str = "redis://127.0.0.1:6379/0"):
        try:
            self.redis = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
            self.redis.ping()
            self._available = True
        except Exception:
            self._available = False

    async def record(self, tool: str, user_id: int, tokens: int = 0):
        if not self._available:
            return
        date = datetime.now().strftime("%Y-%m-%d")
        self.redis.hincrby(f"stats:{tool}:calls:{date}", str(user_id), 1)
        if tokens > 0:
            self.redis.hincrby(f"stats:{tool}:tokens:{date}", str(user_id), tokens)

    def get_tool_stats(self, tool: str, date: str = None) -> Dict:
        if not self._available:
            return {"calls": {}, "tokens": {}}
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        calls = self.redis.hgetall(f"stats:{tool}:calls:{date}")
        tokens = self.redis.hgetall(f"stats:{tool}:tokens:{date}")
        return {
            "calls": {k: int(v) for k, v in calls.items()},
            "tokens": {k: int(v) for k, v in tokens.items()},
        }

    def get_all_stats(self, date: str = None) -> Dict:
        if not self._available:
            return {}
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        tools = ["knowledge", "code-index", "sandbox", "quality", "memory", "asset", "context-optimizer", "evolution-engine"]
        stats = {}
        for tool in tools:
            stats[tool] = self.get_tool_stats(tool, date)
        return stats
