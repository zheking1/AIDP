import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class ContextCache:
    """上下文缓存管理器"""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, dict] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    def _generate_key(self, stage: str, params: Dict[str, Any]) -> str:
        param_str = json.dumps(params, sort_keys=True, default=str)
        hash_obj = hashlib.md5(f"{stage}:{param_str}".encode())
        return hash_obj.hexdigest()

    def get(self, stage: str, params: Dict[str, Any]) -> Optional[Dict]:
        key = self._generate_key(stage, params)

        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry["timestamp"] < timedelta(seconds=self.ttl_seconds):
                self.stats["hits"] += 1
                return entry["data"]
            else:
                del self.cache[key]
                self.stats["evictions"] += 1

        self.stats["misses"] += 1
        return None

    def set(self, stage: str, params: Dict[str, Any], data: Any):
        key = self._generate_key(stage, params)
        self.cache[key] = {
            "data": data,
            "timestamp": datetime.now(),
        }

        if len(self.cache) > 1000:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]
            self.stats["evictions"] += 1

    def invalidate(self, stage: Optional[str] = None):
        if stage:
            keys_to_delete = [k for k in self.cache if k.startswith(stage)]
            for key in keys_to_delete:
                del self.cache[key]
        else:
            self.cache.clear()

    def get_stats(self) -> Dict:
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0
        return {
            **self.stats,
            "hit_rate": round(hit_rate, 2),
            "size": len(self.cache),
        }