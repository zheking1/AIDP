"""
AIDP Menu Engine
动态菜单生成引擎
"""

from typing import List, Dict, Any, Optional
from app.core.config_loader import get_menu_config
import logging

logger = logging.getLogger(__name__)


class MenuEngine:
    """菜单引擎 - 根据用户和项目动态生成菜单"""
    
    def __init__(self):
        self.config = get_menu_config()
    
    def get_sidebar_menu(
        self, 
        user: Optional[Any] = None, 
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取侧边栏菜单
        
        Args:
            user: 当前用户对象
            project_id: 当前项目ID（可选）
        
        Returns:
            过滤后的菜单列表
        """
        menu = []
        
        for group in self.config.get('sidebar', []):
            # 项目专区：只有选了项目才显示
            if group.get('is_project_section'):
                if not project_id:
                    continue
            
            if not group.get('visible', True):
                continue
            
            needs_project = group.get('requires_project', False) and not group.get('is_project_section')
            
            if group.get('requires_role'):
                if not self._has_role(user, group['requires_role']):
                    continue
            if group.get('requires_permission'):
                if not self._has_permissions(user, [group['requires_permission']]):
                    continue
            
            # Hub 类型：一级入口，点击后在内容区显示二级导航
            if group.get('is_hub'):
                hub_items = []
                for item in group.get('hub_items', []):
                    if not item.get('visible', True):
                        continue
                    if item.get('permissions'):
                        if not self._has_permissions(user, item['permissions']):
                            continue
                    if item.get('requires_role'):
                        if not self._has_role(user, item['requires_role']):
                            continue
                    hub_items.append({
                        'id': item['id'],
                        'label': item['label'],
                        'icon': item['icon'],
                        'route': item['route'],
                    })
                if hub_items:
                    menu.append({
                        'group': group['group'],
                        'title': group['title'],
                        'icon': group.get('icon', 'circle'),
                        'order': group.get('order', 100),
                        'is_hub': True,
                        'hub_route': group['hub_route'],
                        'hub_items': hub_items
                    })
                continue
            
            # 普通菜单项
            items = []
            for item in group.get('items', []):
                if not item.get('visible', True):
                    continue
                if item.get('permissions'):
                    if not self._has_permissions(user, item['permissions']):
                        continue
                if item.get('requires_project') and not project_id:
                    continue
                if item.get('requires_role'):
                    if not self._has_role(user, item['requires_role']):
                        continue
                route = item.get('route', '')
                if project_id and '{project_id}' in route:
                    route = route.replace('{project_id}', str(project_id))
                items.append({
                    'id': item['id'], 'label': item['label'], 'icon': item['icon'],
                    'route': route, 'description': item.get('description', ''),
                    'badge': item.get('badge'), 'disabled': needs_project and not project_id
                })
            
            if items:
                group_data = {
                    'group': group['group'], 'title': group['title'],
                    'icon': group.get('icon', 'circle'), 'order': group.get('order', 100),
                    'items': items
                }
                if group.get('is_project_section'):
                    group_data['is_project_section'] = True
                menu.append(group_data)
        
        # 按 order 排序
        menu.sort(key=lambda x: x['order'])
        
        return menu
    
    def get_header_menu(self, user: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        获取顶部导航菜单
        
        Args:
            user: 当前用户对象
            
        Returns:
            顶部菜单列表
        """
        menu = []
        
        for item in self.config.get('header', []):
            # 检查权限
            if item.get('permissions'):
                if not self._has_permissions(user, item['permissions']):
                    continue
            
            menu.append({
                'id': item['id'],
                'label': item['label'],
                'icon': item['icon'],
                'route': item.get('route'),
                'href': item.get('href'),
                'target': item.get('target'),
                'action': item.get('action'),
                'badge': item.get('badge')
            })
        
        return menu
    
    def get_user_menu(self, user: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        获取用户下拉菜单
        
        Args:
            user: 当前用户对象
            
        Returns:
            用户菜单列表
        """
        menu = []
        
        for item in self.config.get('user_menu', []):
            if item.get('separator'):
                menu.append({'separator': True})
            else:
                menu.append({
                    'id': item['id'],
                    'label': item['label'],
                    'icon': item['icon'],
                    'route': item.get('route'),
                    'action': item.get('action')
                })
        
        return menu
    
    def get_project_switcher_config(self) -> Dict[str, Any]:
        """获取项目切换器配置"""
        return self.config.get('project_switcher', {
            'enabled': True,
            'show_recent': True,
            'recent_count': 5,
            'show_create': True,
            'create_label': '创建新项目'
        })
    
    def _has_role(self, user: Optional[Any], required_role: str) -> bool:
        """
        检查用户是否有指定角色
        
        Args:
            user: 用户对象
            required_role: 需要的角色
            
        Returns:
            是否有该角色
        """
        if not user:
            return False
        
        # 系统管理员拥有所有角色
        user_role = getattr(user, 'role', None)
        if user_role in ['admin', 'super_admin']:
            return True
        
        return user_role == required_role
    
    def _has_permissions(self, user: Optional[Any], permissions: List[str]) -> bool:
        """
        检查用户是否有指定权限
        
        Args:
            user: 用户对象
            permissions: 权限列表
            
        Returns:
            是否有所有权限
        """
        if not user:
            return False
        
        # 系统管理员拥有所有权限
        user_role = getattr(user, 'role', None)
        if user_role in ['admin', 'super_admin']:
            return True
        
        # TODO: 实现细粒度权限检查
        # 暂时简化处理：普通用户只有基本权限
        # 后续可以从用户的权限列表中检查
        return True


# 快捷函数
def get_menu_for_user(
    user: Optional[Any] = None, 
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取用户的完整菜单
    
    Args:
        user: 当前用户对象
        project_id: 当前项目ID
        
    Returns:
        包含 sidebar、header、user 菜单的字典
    """
    engine = MenuEngine()
    return {
        'sidebar': engine.get_sidebar_menu(user, project_id),
        'header': engine.get_header_menu(user),
        'user': engine.get_user_menu(user),
        'project_switcher': engine.get_project_switcher_config()
    }
