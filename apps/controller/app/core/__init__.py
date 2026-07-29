"""
AIDP Core Module
核心模块
"""

from app.core.config_loader import (
    ConfigLoader,
    get_config_loader,
    get_menu_config,
    get_permissions_config,
    reload_configs
)

from app.core.menu import (
    MenuEngine,
    get_menu_for_user
)

from app.core.permissions import (
    PermissionChecker,
    require_permissions,
    RolePermissionManager,
    check_permission,
    get_user_permissions
)

from app.core.context import (
    Project,
    ProjectContext,
    get_project_context,
    get_current_project,
    ProjectContextMiddleware
)

__all__ = [
    # Config
    'ConfigLoader',
    'get_config_loader',
    'get_menu_config',
    'get_permissions_config',
    'reload_configs',
    
    # Menu
    'MenuEngine',
    'get_menu_for_user',
    
    # Permissions
    'PermissionChecker',
    'require_permissions',
    'RolePermissionManager',
    'check_permission',
    'get_user_permissions',
    
    # Context
    'Project',
    'ProjectContext',
    'get_project_context',
    'get_current_project',
    'ProjectContextMiddleware'
]
