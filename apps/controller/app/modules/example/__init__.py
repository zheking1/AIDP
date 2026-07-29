"""
示例模块 - 用于测试模块系统

此模块演示如何创建和注册一个 AIDP 模块
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.modules import BaseModule, register_module
from app.core.permissions import require_permissions

# 创建路由
router = APIRouter()


@register_module(name='example', enabled=True)
class ExampleModule(BaseModule):
    """
    示例模块
    
    演示模块系统的基本用法
    """
    name = "example"
    description = "示例模块，用于演示模块系统"
    version = "1.0.0"
    enabled = True
    dependencies = []  # 无依赖
    
    def register_routes(self, app):
        """注册路由到主应用"""
        app.include_router(router, prefix="/api/example")
    
    def register_models(self):
        """注册数据库模型（示例中不需要）"""
        pass
    
    def on_startup(self):
        """模块启动时调用"""
        print(f"[ExampleModule] Module started")
    
    def on_shutdown(self):
        """模块关闭时调用"""
        print(f"[ExampleModule] Module stopped")


@router.get("/info")
async def get_module_info() -> Dict[str, Any]:
    """
    获取模块信息
    
    不需要权限，公开访问
    """
    return {
        "name": "example",
        "description": "示例模块",
        "version": "1.0.0",
        "status": "running"
    }


@router.get("/protected")
async def protected_endpoint(
    user=require_permissions("project:view")
) -> Dict[str, Any]:
    """
    受保护的端点
    
    需要 project:view 权限
    """
    return {
        "message": "You have permission to access this endpoint",
        "user_id": getattr(user, 'id', None),
        "user_role": getattr(user, 'role', None)
    }


@router.get("/test-menu")
async def test_menu() -> Dict[str, Any]:
    """
    测试菜单系统
    
    返回示例菜单数据
    """
    from app.core.menu import get_menu_for_user
    
    # 使用 None 作为用户（匿名）
    menu = get_menu_for_user(None)
    
    return {
        "message": "Menu system test",
        "menu_groups": len(menu.get('sidebar', [])),
        "header_items": len(menu.get('header', [])),
        "user_items": len(menu.get('user', []))
    }
