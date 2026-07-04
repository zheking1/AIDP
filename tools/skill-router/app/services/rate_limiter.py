import time
from typing import Optional, Dict, Any
from collections import defaultdict

from app.services.cache_service import get_redis

# P3优化：分级限流策略
QPS_LIMITS = {
    "admin": 50,       # Admin用户高频限制
    "user": 10,        # 普通用户标准限制
    "readonly": 5,     # 只读用户低频限制
}
DAILY_QUOTA = {
    "admin": 10000,    # Admin用户每日配额
    "user": 1000,      # 普通用户每日配额
    "readonly": 500,   # 只读用户每日配额
}

# P3优化：并发控制
MAX_CONCURRENT_REQUESTS = {
    "admin": 20,
    "user": 5,
    "readonly": 3,
}

# P3优化：全局并发计数器
concurrent_requests = defaultdict(int)  # {user_id: count}


async def check_rate_limit(user_id: str, user_role: str = "user") -> tuple[bool, Optional[str]]:
    """
    P3优化：分级限流策略
    根据用户角色应用不同的限流规则
    """
    try:
        r = await get_redis()
        now = int(time.time())
        
        # 1. QPS限制（分级）
        qps_limit = QPS_LIMITS.get(user_role, QPS_LIMITS["user"])
        qps_key = f"ratelimit:qps:{user_id}"
        qps_count = await r.incr(qps_key)
        if qps_count == 1:
            await r.expire(qps_key, 1)
        if qps_count > qps_limit:
            return False, f"qps_exceeded (limit: {qps_limit}/s)"
        
        # 2. 每日配额限制（分级）
        daily_limit = DAILY_QUOTA.get(user_role, DAILY_QUOTA["user"])
        daily_key = f"ratelimit:daily:{user_id}:{now // 86400}"
        daily_count = await r.incr(daily_key)
        if daily_count == 1:
            await r.expire(daily_key, 86400)
        if daily_count > daily_limit:
            return False, f"daily_quota_exceeded (limit: {daily_limit}/day)"
        
        # 3. 并发控制（新增）
        concurrent_limit = MAX_CONCURRENT_REQUESTS.get(user_role, MAX_CONCURRENT_REQUESTS["user"])
        if concurrent_requests[user_id] >= concurrent_limit:
            return False, f"concurrent_exceeded (limit: {concurrent_limit})"
        
        # 增加并发计数
        concurrent_requests[user_id] += 1
        
        return True, None
    except Exception:
        # 出错时允许请求，避免限流器成为瓶颈
        return True, None


def release_concurrent(user_id: str):
    """
    P3优化：释放并发计数
    在请求完成后调用
    """
    if concurrent_requests[user_id] > 0:
        concurrent_requests[user_id] -= 1


async def check_system_load() -> Dict[str, Any]:
    """
    P3优化：系统负载检测
    用于智能降级决策
    """
    try:
        r = await get_redis()
        
        # 1. 检测Redis连接数（proxy for系统负载）
        info = await r.info("clients")
        connected_clients = info.get("connected_clients", 0)
        
        # 2. 检测Redis内存使用
        memory_info = await r.info("memory")
        used_memory_mb = memory_info.get("used_memory", 0) / (1024 * 1024)
        
        # 3. 检测当前活跃用户数
        active_users = len(concurrent_requests)
        
        # 4. 计算负载评分
        load_score = (connected_clients * 0.3 + used_memory_mb * 0.4 + active_users * 0.3)
        
        # 5. 判断负载状态
        if load_score > 100:
            status = "high"
        elif load_score > 50:
            status = "medium"
        else:
            status = "low"
        
        return {
            "load_score": round(load_score, 2),
            "status": status,
            "connected_clients": connected_clients,
            "used_memory_mb": round(used_memory_mb, 2),
            "active_users": active_users,
        }
    except Exception as e:
        return {
            "load_score": 0,
            "status": "unknown",
            "error": str(e),
        }


async def should_throttle() -> bool:
    """
    P3优化：智能降级决策
    根据系统负载判断是否需要启用更严格的限流
    """
    load_info = await check_system_load()
    status = load_info.get("status", "low")
    
    # 高负载时启用更严格限流
    return status == "high"


async def get_rate_limit_stats(user_id: str) -> Dict[str, Any]:
    """
    P3优化：获取用户限流统计
    用于监控和调试
    """
    try:
        r = await get_redis()
        now = int(time.time())
        
        qps_key = f"ratelimit:qps:{user_id}"
        daily_key = f"ratelimit:daily:{user_id}:{now // 86400}"
        
        qps_count = await r.get(qps_key) or "0"
        daily_count = await r.get(daily_key) or "0"
        
        return {
            "current_qps": int(qps_count),
            "daily_requests": int(daily_count),
            "concurrent_requests": concurrent_requests[user_id],
        }
    except Exception as e:
        return {
            "error": str(e),
            "current_qps": 0,
            "daily_requests": 0,
            "concurrent_requests": 0,
        }
