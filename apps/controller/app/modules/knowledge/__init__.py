"""
Knowledge Module
知识库模块 - AIDP Unified Platform

集成了原有的 Knowledge Tool 功能
"""

from fastapi import APIRouter
from app.modules import BaseModule, register_module

# 创建路由
router = APIRouter()


@register_module(name='knowledge', enabled=True)
class KnowledgeModule(BaseModule):
    """
    知识库模块
    
    提供文档管理、知识库、语义搜索等功能
    """
    name = "knowledge"
    description = "文档知识库管理，支持语义搜索和智能分块"
    version = "1.0.0"
    enabled = True
    dependencies = []  # 无依赖，但推荐项目模块先加载
    
    def register_routes(self, app):
        """注册路由到主应用"""
        from .routes import router as knowledge_router
        app.include_router(knowledge_router, prefix="/api/knowledge")
        from .templates_routes import router as templates_router
        app.include_router(templates_router, prefix="/api/knowledge")
    
    def register_models(self):
        """注册数据库模型"""
        # 模型已在 app.models 中定义，SQLAlchemy 会自动识别
        pass
    
    def on_startup(self):
        """模块启动时调用"""
        print(f"[KnowledgeModule] 知识库模块已启动")
    
    def on_shutdown(self):
        """模块关闭时调用"""
        print(f"[KnowledgeModule] 知识库模块已停止")
