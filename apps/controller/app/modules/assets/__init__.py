"""
Assets Module
代码资产模块 - AIDP Unified Platform

提供代码片段、模板、配置等资产管理
"""

from app.modules import BaseModule, register_module
@register_module(name='assets', enabled=True)
class AssetsModule(BaseModule):
    """
    代码资产模块

    提供代码片段、模板、配置等资产的存储、搜索和渲染
    """
    name = "assets"
    description = "代码资产管理，支持搜索和模板渲染"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as assets_router
        app.include_router(assets_router, prefix="/api/assets")

    def on_startup(self):
        print(f"[AssetsModule] 资产模块已启动")

    def on_shutdown(self):
        print(f"[AssetsModule] 资产模块已停止")

