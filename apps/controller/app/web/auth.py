from functools import wraps
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse


def require_login(func):
    """登录认证装饰器"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login")
        request.state.user_id = user_id
        request.state.username = request.session.get("username")
        request.state.role = request.session.get("role")
        return await func(request, *args, **kwargs)
    return wrapper


def require_admin(func):
    """管理员认证装饰器"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login")
        if request.session.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        request.state.user_id = user_id
        request.state.username = request.session.get("username")
        request.state.role = request.session.get("role")
        return await func(request, *args, **kwargs)
    return wrapper
