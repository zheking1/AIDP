"""
P5改进：认证辅助模块
消除Web路由中的重复用户验证逻辑
"""
import uuid
from typing import Optional, Tuple
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import settings
from app.web.i18n_utils import render_template, get_translator

ROLE_LEVELS = {
    "super_admin": 5,
    "admin": 4,
    "developer": 3,
    "user": 2,
    "readonly": 1,
}


def get_role_level(role: str) -> int:
    return ROLE_LEVELS.get(role, 1)


def is_super_admin(user: dict) -> bool:
    return user.get("role") == "super_admin"


def has_role(user: dict, required_role: str) -> bool:
    user_role = user.get("role", "user")
    return get_role_level(user_role) >= get_role_level(required_role)


def can_access(user: dict, allowed_roles: list = None) -> bool:
    if not allowed_roles or not user:
        return False
    user_role = user.get("role", "user")
    return user_role in allowed_roles


def require_login(request: Request) -> Optional[RedirectResponse]:
    """
    P5改进：统一登录检查
    返回None表示已登录，返回RedirectResponse表示需要跳转登录页
    """
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)
    return None


def is_admin(user: dict) -> bool:
    """
    P5改进：管理员角色检查（包括super_admin）
    """
    role = user.get("role", "user")
    return get_role_level(role) >= 4 or user.get("username") == settings.admin_username


def require_admin(request: Request) -> Optional[HTMLResponse]:
    """
    P5改进：管理员权限检查
    返回None表示是管理员，返回HTMLResponse表示权限不足
    """
    user = request.session.get("user")
    if not user:
        return HTMLResponse("Unauthorized", status_code=401)
    if not is_admin(user):
        return HTMLResponse("Forbidden", status_code=403)
    return None


async def get_current_user_id(request: Request, db=None) -> uuid.UUID:
    """
    P5改进：统一获取当前用户ID
    如果session中没有，返回默认admin用户ID
    """
    user = request.session.get("user")
    if user and user.get("id"):
        try:
            return uuid.UUID(user["id"])
        except (ValueError, AttributeError):
            pass
    
    # 如果提供了db，尝试从admin用户获取
    if db:
        from sqlalchemy import select
        from app.db.models import User
        result = await db.execute(
            select(User).where(User.username == settings.admin_username)
        )
        admin = result.scalar_one_or_none()
        if admin:
            return admin.id
    
    # 默认返回UUID(int=1)
    return uuid.UUID(int=1)


async def get_user_id_from_session(request: Request) -> uuid.UUID:
    """
    P5改进：快速获取用户ID（不需要db）
    """
    user = request.session.get("user", {})
    try:
        return uuid.UUID(user.get("id", ""))
    except (ValueError, AttributeError):
        return uuid.UUID(int=1)


def get_user_role(request: Request) -> str:
    """
    P5改进：获取当前用户角色
    """
    user = request.session.get("user", {})
    return user.get("role", "user")


def create_auth_response(request: Request, check_result: Optional[HTMLResponse]) -> Optional[HTMLResponse]:
    """
    P5改进：统一处理认证响应
    如果check_result不为None，返回相应的错误响应
    """
    return check_result


class AuthMiddleware:
    """
    P5改进：认证中间件类（可选）
    用于路由级别的认证控制
    """
    
    @staticmethod
    def check_login(request: Request) -> Tuple[bool, Optional[RedirectResponse]]:
        """检查是否登录"""
        if request.session.get("user"):
            return True, None
        return False, RedirectResponse(url="/login", status_code=302)
    
    @staticmethod
    def check_admin(request: Request) -> Tuple[bool, Optional[HTMLResponse]]:
        """检查是否是管理员"""
        user = request.session.get("user")
        if not user:
            return False, HTMLResponse("Unauthorized", status_code=401)
        if not is_admin(user):
            return False, HTMLResponse("Forbidden", status_code=403)
        return True, None


# P5改进：错误消息辅助函数
def get_error_message(request: Request, key: str) -> str:
    """
    获取本地化错误消息
    """
    t = get_translator(request.session.get("lang", "zh"))
    return t(key)