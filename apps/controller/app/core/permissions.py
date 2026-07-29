"""
AIDP Permission System
权限检查系统
"""

from functools import wraps
from typing import List, Optional, Any, Dict
from fastapi import HTTPException, Depends, Request
import logging

from app.core.config_loader import get_permissions_config

logger = logging.getLogger(__name__)


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self, permissions: List[str]):
        """
        初始化权限检查器
        
        Args:
            permissions: 需要的权限列表
        """
        self.permissions = permissions
        self.config = get_permissions_config()
    
    async def __call__(self, request: Request) -> Any:
        """
        检查权限
        
        Args:
            request: FastAPI 请求对象
            
        Returns:
            用户对象（如果权限检查通过）
            
        Raises:
            HTTPException: 权限不足时抛出 403
        """
        # 从请求中获取当前用户
        user = await self._get_current_user(request)
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # 检查每个权限
        for permission in self.permissions:
            if not await self._check_permission(user, permission, request):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission}"
                )
        
        return user
    
    async def _get_current_user(self, request: Request) -> Optional[Any]:
        """从请求中获取当前用户"""
        # 从 session cookie 获取
        session_token = request.cookies.get("aidp_session")
        if not session_token:
            return None
        
        # 导入认证服务验证 session
        try:
            from app.services.auth_service import AuthService
            return await AuthService.validate_session(session_token)
        except Exception as e:
            logger.error(f"Failed to validate session: {e}")
            return None
    
    async def _check_permission(
        self, 
        user: Any, 
        permission: str,
        request: Request
    ) -> bool:
        """
        检查单个权限
        
        Args:
            user: 用户对象
            permission: 权限字符串（如 "knowledge:read"）
            request: 请求对象（用于获取项目上下文）
            
        Returns:
            是否有该权限
        """
        # 系统管理员拥有所有权限
        user_role = getattr(user, 'role', None)
        if user_role in ['admin', 'super_admin']:
            return True
        
        # 解析权限
        parts = permission.split(':')
        resource = parts[0]
        action = parts[1] if len(parts) > 1 else 'read'
        scope = parts[2] if len(parts) > 2 else None
        
        # 系统级权限检查
        if resource == 'admin':
            return user_role == 'admin'
        
        # 项目级权限检查
        project_id = request.path_params.get('project_id') or \
                     request.query_params.get('project_id')
        
        if project_id:
            return await self._check_project_permission(
                user, project_id, resource, action
            )
        
        # 检查用户角色默认权限（包含 personal/global/project 所有 scope）
        return self._check_role_permission(user_role, resource, action)
    
    async def _check_project_permission(
        self,
        user: Any,
        project_id: str,
        resource: str,
        action: str
    ) -> bool:
        """检查项目级权限"""
        # TODO: 实现项目成员权限检查
        # 1. 查询用户是否是项目成员
        # 2. 获取用户在项目中的角色
        # 3. 检查角色是否有该权限
        
        # 暂时简化处理：项目创建者和管理员有所有权限
        # 其他用户根据角色判断
        
        user_role = getattr(user, 'role', None)
        if user_role == 'admin':
            return True
        
        # 普通用户根据角色权限判断
        return self._check_role_permission(user_role, resource, action)
    
    def _check_role_permission(self, role: str, resource: str, action: str) -> bool:
        """
        根据角色检查权限
        
        Args:
            role: 角色名称
            resource: 资源类型
            action: 操作类型
            
        Returns:
            是否有权限
        """
        # 管理员拥有所有权限
        if role in ['admin', 'super_admin']:
            return True
        
        # 编辑者权限
        if role == 'editor':
            if action in ['read', 'write']:
                return True
            if resource in ['knowledge', 'memory'] and action == 'delete':
                return True
            return False
        
        # 查看者权限
        if role == 'viewer':
            return action == 'read'

        # 普通用户 — 只读 + 创建项目
        if role == 'user':
            return action in ('read', 'create')

        # 其他角色（developer/readonly 等）— 按照配置表判断
        config_roles = self.config.get('roles', {}).get('system', {})
        role_config = config_roles.get(role, {})
        perms = role_config.get('permissions', [])
        if '*' in perms:
            return True
        perm_str = f"{resource}:{action}"
        scope = None
        import re
        for p in perms:
            if p.startswith(perm_str) or p == perm_str:
                return True
            # 匹配带有 scope 的如 skills:read:global
            if p.startswith(f"{resource}:{action}:") or p.startswith(f"{resource}:"):
                return True
        return False

        return False


# 快捷装饰器
def require_permissions(*permissions: str):
    """
    权限检查装饰器
    
    用法:
        @router.get("/api/projects")
        async def list_projects(user=require_permissions("project:view"):
            return {"projects": []}
    """
    return Depends(PermissionChecker(list(permissions)))


class RolePermissionManager:
    """角色权限管理器"""
    
    def __init__(self):
        self.config = get_permissions_config()
    
    def get_role_permissions(self, role: str, role_type: str = 'project') -> List[str]:
        """
        获取角色的默认权限
        
        Args:
            role: 角色名称
            role_type: 角色类型（system 或 project）
            
        Returns:
            权限列表
        """
        roles_config = self.config.get('roles', {})
        
        if role_type == 'system':
            role_config = roles_config.get('system', {}).get(role, {})
        else:
            role_config = roles_config.get('project', {}).get(role, {})
        
        permissions = role_config.get('permissions', [])
        
        # 处理通配符
        if '*' in permissions:
            return ['*']  # 所有权限
        
        return permissions
    
    def check_permission_inheritance(self, permission: str) -> List[str]:
        """
        检查权限继承
        
        Args:
            permission: 权限字符串
            
        Returns:
            包含的底层权限列表
        """
        rules = self.config.get('rules', {})
        inheritance = rules.get('inheritance', {})
        
        return inheritance.get(permission, [])
    
    def has_permission(
        self, 
        user_permissions: List[str], 
        required_permission: str
    ) -> bool:
        """
        检查用户权限列表是否包含指定权限
        
        Args:
            user_permissions: 用户拥有的权限列表
            required_permission: 需要的权限
            
        Returns:
            是否有权限
        """
        # 拥有所有权限
        if '*' in user_permissions:
            return True
        
        # 直接拥有该权限
        if required_permission in user_permissions:
            return True
        
        # 检查权限继承
        # 例如：如果用户有 knowledge:write，则也有 knowledge:read
        manager = RolePermissionManager()
        for perm in user_permissions:
            inherited = manager.check_permission_inheritance(perm)
            if required_permission in inherited:
                return True
        
        return False


async def check_scope_read_access(
    user: Any,
    resource: str,
    scope: str,
):
    """
    Check if user can read the given resource at the given scope.
    Raises 401/403 if not allowed. Returns the user (or None for anonymous global access).
    """
    if not user:
        if scope != "global":
            raise HTTPException(status_code=401, detail="Authentication required for non-global scope")
        return None

    # user role check via _check_role_permission
    user_role = getattr(user, 'role', None)
    if user_role in ['admin', 'super_admin']:
        return user

    checker = PermissionChecker([f"{resource}:read"])
    if not checker._check_role_permission(user_role, resource, "read"):
        raise HTTPException(status_code=403, detail=f"Permission denied: {resource}:read")
    return user


# 快捷函数
def check_permission(user: Any, permission: str) -> bool:
    """
    检查用户是否有指定权限
    
    Args:
        user: 用户对象
        permission: 权限字符串
        
    Returns:
        是否有权限
    """
    # 系统管理员
    if getattr(user, 'role', None) in ['admin', 'super_admin']:
        return True
    
    # TODO: 从用户权限列表中检查
    return True


def get_user_permissions(user: Any) -> List[str]:
    """
    获取用户的所有权限
    
    Args:
        user: 用户对象
        
    Returns:
        权限列表
    """
    # 系统管理员
    if getattr(user, 'role', None) in ['admin', 'super_admin']:
        return ['*']  # 所有权限
    
    # TODO: 从数据库获取用户权限
    return []
