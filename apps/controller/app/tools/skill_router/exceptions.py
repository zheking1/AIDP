"""
P5改进：项目特定异常类型和错误处理策略
用于细化错误处理，替换宽泛的Exception捕获
"""
from typing import Optional, Dict, Any


class SkillRouterException(Exception):
    """
    基础异常类
    """
    def __init__(self, message: str, error_code: str = "UNKNOWN", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# 配置相关异常
class ConfigurationError(SkillRouterException):
    """配置错误"""
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message, "CONFIG_ERROR", {"config_key": config_key})


class ValidationError(SkillRouterException):
    """数据校验错误"""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, "VALIDATION_ERROR", {"field": field})


# 数据库相关异常
class DatabaseError(SkillRouterException):
    """数据库错误"""
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(message, "DB_ERROR", {"operation": operation})


class NotFoundError(SkillRouterException):
    """资源不存在"""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} not found: {resource_id}",
            "NOT_FOUND",
            {"resource_type": resource_type, "resource_id": resource_id}
        )


class DuplicateError(SkillRouterException):
    """资源重复"""
    def __init__(self, resource_type: str, field: str, value: str):
        super().__init__(
            f"{resource_type} with {field}='{value}' already exists",
            "DUPLICATE",
            {"resource_type": resource_type, "field": field, "value": value}
        )


# 权限相关异常
class PermissionDeniedError(SkillRouterException):
    """权限不足"""
    def __init__(self, message: str = "Permission denied", user_role: Optional[str] = None):
        super().__init__(message, "PERMISSION_DENIED", {"user_role": user_role})


class AuthenticationError(SkillRouterException):
    """认证失败"""
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, "AUTH_ERROR")


# LLM相关异常
class LLMError(SkillRouterException):
    """LLM调用错误"""
    def __init__(self, message: str, llm_endpoint: Optional[str] = None):
        super().__init__(message, "LLM_ERROR", {"llm_endpoint": llm_endpoint})


class LLMTimeoutError(LLMError):
    """LLM超时"""
    def __init__(self, timeout_secs: int):
        super().__init__(f"LLM request timed out after {timeout_secs}s")
        self.error_code = "LLM_TIMEOUT"


class EmbeddingError(LLMError):
    """Embedding生成错误"""
    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = "EMBEDDING_ERROR"


# 缓存相关异常
class CacheError(SkillRouterException):
    """缓存错误"""
    def __init__(self, message: str, cache_key: Optional[str] = None):
        super().__init__(message, "CACHE_ERROR", {"cache_key": cache_key})


# 限流相关异常
class RateLimitError(SkillRouterException):
    """限流错误"""
    def __init__(self, message: str, limit_type: str, current_value: int, limit: int):
        super().__init__(
            message,
            "RATE_LIMIT",
            {"limit_type": limit_type, "current": current_value, "limit": limit}
        )


class QPSExceededError(RateLimitError):
    """QPS超限"""
    def __init__(self, current_qps: int, limit: int):
        super().__init__(
            f"QPS exceeded (current: {current_qps}, limit: {limit})",
            "qps", current_qps, limit
        )


class QuotaExceededError(RateLimitError):
    """配额超限"""
    def __init__(self, current: int, limit: int):
        super().__init__(
            f"Daily quota exceeded (current: {current}, limit: {limit})",
            "quota", current, limit
        )


# P5改进：错误处理辅助函数
def handle_exception(exc: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一异常处理
    将异常转换为结构化的错误响应
    """
    if isinstance(exc, SkillRouterException):
        result = exc.to_dict()
        if context:
            result["context"] = context
        return result
    
    # 对于未预期的异常，记录详细信息
    import traceback
    return {
        "error_code": "UNEXPECTED",
        "message": str(exc),
        "exception_type": type(exc).__name__,
        "traceback": traceback.format_exc(),
        "context": context or {},
    }


def safe_execute(func, *args, default=None, **kwargs):
    """
    安全执行函数
    出错时返回默认值而不是抛出异常
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        # 记录错误但不抛出
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Safe execute failed: {e}", exc_info=True)
        return default


async def safe_execute_async(func, *args, default=None, **kwargs):
    """
    异步安全执行函数
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Safe execute async failed: {e}", exc_info=True)
        return default


# P5改进：异常装饰器
def catch_and_log(func):
    """
    异常捕获装饰器
    自动记录异常但不中断执行
    """
    import functools
    import logging
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SkillRouterException as e:
            logger = logging.getLogger(func.__module__)
            logger.warning(f"{func.__name__} raised {e.error_code}: {e.message}")
            raise
        except Exception as e:
            logger = logging.getLogger(func.__module__)
            logger.error(f"{func.__name__} unexpected error: {e}", exc_info=True)
            raise SkillRouterException(str(e))
    
    return wrapper


def catch_and_log_async(func):
    """
    异步异常捕获装饰器
    """
    import functools
    import logging
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except SkillRouterException as e:
            logger = logging.getLogger(func.__module__)
            logger.warning(f"{func.__name__} raised {e.error_code}: {e.message}")
            raise
        except Exception as e:
            logger = logging.getLogger(func.__module__)
            logger.error(f"{func.__name__} unexpected error: {e}", exc_info=True)
            raise SkillRouterException(str(e))
    
    return wrapper