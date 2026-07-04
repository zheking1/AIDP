import json
import hashlib
from typing import Optional, Dict, Any
from uuid import UUID
import time
from collections import defaultdict

import redis.asyncio as aioredis

from app.config import settings

redis_client: Optional[aioredis.Redis] = None

# P3优化：缓存命中率统计
cache_stats = defaultdict(int)  # {"hits": 0, "misses": 0, "session_hits": 0}


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return redis_client


def make_cache_key(task_profile: str, user_id: UUID, mode: str) -> str:
    raw = f"{task_profile}:{user_id}:{mode}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_cached(key_hash: str) -> Optional[dict]:
    """
    P3优化：添加缓存命中率统计
    """
    try:
        r = await get_redis()
        data = await r.get(key_hash)
        if data:
            cache_stats["hits"] += 1
            return json.loads(data)
        else:
            cache_stats["misses"] += 1
            return None
    except Exception:
        cache_stats["misses"] += 1
        return None


async def set_cache(key_hash: str, data: dict, ttl: int = None):
    """
    P3优化：添加数据大小限制，避免缓存过大数据
    """
    try:
        serialized = json.dumps(data)
        # 限制缓存数据大小（不超过1MB）
        if len(serialized) > 1024 * 1024:
            # 如果数据过大，只缓存关键信息
            mini_data = {
                "skills": [{"id": s["id"], "name": s["name"], "score": s["score"]} for s in data.get("skills", [])],
                "rules": [{"id": r["id"], "name": r["name"]} for r in data.get("rules", [])],
                "intent_analysis": data.get("intent_analysis"),
                "degrade_info": data.get("degrade_info"),
            }
            serialized = json.dumps(mini_data)
        
        r = await get_redis()
        await r.setex(key_hash, ttl or settings.cache_ttl_seconds, serialized)
    except Exception:
        pass


import math

SESSION_CACHE_TTL = 1800  # 30 min


async def delete_cache(key_hash: str = None, pattern: str = None):
    try:
        r = await get_redis()
        if key_hash:
            await r.delete(key_hash)
        elif pattern:
            cursor, keys = await r.scan(match=pattern)
            if keys:
                await r.delete(*keys)
    except Exception:
        pass


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na * nb else 0.0


async def get_session_cache(user_id: str, query_emb: list[float]) -> Optional[dict]:
    """
    P3优化：添加会话缓存命中率统计
    """
    try:
        r = await get_redis()
        key = f"session_cache:{user_id}"
        entries = await r.lrange(key, 0, -1)
        for entry in entries:
            data = json.loads(entry)
            if _cosine_sim(query_emb, data["embedding"]) >= 0.7:
                cache_stats["session_hits"] += 1
                return data["result"]
        return None
    except Exception:
        return None


async def set_session_cache(user_id: str, query_emb: list[float], result: dict):
    """
    P3优化：添加数据大小限制和智能清理
    """
    try:
        r = await get_redis()
        key = f"session_cache:{user_id}"
        
        # P3优化：数据压缩，只保存必要信息
        compressed_result = {
            "skills": [{"id": s["id"], "name": s["name"], "score": s.get("score", 0)} for s in result.get("skills", [])],
            "rules": [{"id": r["id"], "name": r["name"]} for r in result.get("rules", [])],
            "intent_analysis": result.get("intent_analysis"),
        }
        
        entry = json.dumps({"embedding": query_emb, "result": compressed_result, "ts": time.time()})
        await r.lpush(key, entry)
        await r.ltrim(key, 0, 19)  # keep last 20
        await r.expire(key, SESSION_CACHE_TTL)
    except Exception:
        pass


async def clear_session_cache(user_id: str):
    try:
        r = await get_redis()
        await r.delete(f"session_cache:{user_id}")
    except Exception:
        pass


# P3优化：新增缓存预热功能
async def warmup_cache(user_id: UUID, common_tasks: list[str], mode: str = "auto"):
    """
    缓存预热：提前加载常见任务到缓存
    用于提升首次访问速度
    """
    from app.services.resolve_service import resolve_skills
    from app.db.init_db import get_session
    
    try:
        async with get_session() as session:
            for task in common_tasks:
                # 不使用缓存，强制计算结果
                result = await resolve_skills(
                    session=session,
                    task=task,
                    user_id=user_id,
                    mode=mode,
                    top_k=5,
                )
                # 结果会自动缓存
        return {"warmed_tasks": len(common_tasks)}
    except Exception as e:
        return {"error": str(e)}


# P3优化：新增缓存清理策略
async def cleanup_expired_caches():
    """
    定期清理过期缓存（虽然Redis有TTL，但可以主动清理无效缓存）
    """
    try:
        r = await get_redis()
        # 扫描所有缓存键
        cursor, keys = await r.scan(match="*")
        
        deleted_count = 0
        for key in keys:
            ttl = await r.ttl(key)
            # 删除即将过期或已过期的键
            if ttl == -1:  # 无TTL的键，可能是错误设置的
                await r.delete(key)
                deleted_count += 1
            elif ttl == -2:  # 已过期但未被清理
                await r.delete(key)
                deleted_count += 1
        
        return {"deleted": deleted_count}
    except Exception:
        return {"deleted": 0}


# P3优化：新增缓存统计功能
async def get_cache_statistics() -> Dict[str, Any]:
    """
    获取缓存统计数据，用于监控和优化
    """
    try:
        r = await get_redis()
        
        # 1. 基础统计
        total_requests = cache_stats["hits"] + cache_stats["misses"] + cache_stats["session_hits"]
        hit_rate = cache_stats["hits"] / total_requests if total_requests > 0 else 0
        session_hit_rate = cache_stats["session_hits"] / total_requests if total_requests > 0 else 0
        
        # 2. Redis键统计
        cursor, keys = await r.scan(match="*")
        session_keys = len([k for k in keys if k.startswith("session_cache:")])
        regular_keys = len(keys) - session_keys
        
        # 3. 内存使用（如果Redis支持）
        try:
            info = await r.info("memory")
            used_memory = info.get("used_memory_human", "unknown")
        except Exception:
            used_memory = "unknown"
        
        return {
            "total_requests": total_requests,
            "cache_hits": cache_stats["hits"],
            "cache_misses": cache_stats["misses"],
            "session_hits": cache_stats["session_hits"],
            "hit_rate": round(hit_rate, 4),
            "session_hit_rate": round(session_hit_rate, 4),
            "total_keys": len(keys),
            "regular_keys": regular_keys,
            "session_keys": session_keys,
            "used_memory": used_memory,
        }
    except Exception as e:
        return {
            "error": str(e),
            "total_requests": 0,
            "hit_rate": 0,
        }
