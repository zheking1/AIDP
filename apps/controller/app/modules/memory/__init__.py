"""
Memory Module
记忆模块 - AIDP Unified Platform

提供项目记忆管理、向量搜索、记忆图谱等功能
"""

from fastapi import APIRouter
from app.modules import BaseModule, register_module

# 创建路由
router = APIRouter()


@register_module(name='memory', enabled=True)
class MemoryModule(BaseModule):
    """
    记忆模块
    
    提供项目记忆存储、语义检索、记忆图谱等功能
    """
    name = "memory"
    description = "项目记忆管理，支持向量搜索和记忆图谱"
    version = "1.0.0"
    enabled = True
    dependencies = []
    
    def register_routes(self, app):
        """注册路由到主应用"""
        from .routes import router as memory_router
        app.include_router(memory_router, prefix="/api/memory")
    
    def on_startup(self):
        """模块启动时调用"""
        print(f"[MemoryModule] 记忆模块已启动")
    
    def on_shutdown(self):
        """模块关闭时调用"""
        print(f"[MemoryModule] 记忆模块已停止")
