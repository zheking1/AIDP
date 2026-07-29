"""
Rules Module
规则模块 - AIDP Unified Platform

三层架构: global/personal/project
定义 AI 必须遵守的约束和边界
"""

from app.modules import BaseModule, register_module


@register_module(name='rules', enabled=True)
class RulesModule(BaseModule):
    name = "rules"
    description = "规则管理，三层架构：全局/个人/项目"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as rules_router
        app.include_router(rules_router, prefix="/api/rules")

    def on_startup(self):
        print(f"[RulesModule] 规则模块已启动")

    def on_shutdown(self):
        print(f"[RulesModule] 规则模块已停止")