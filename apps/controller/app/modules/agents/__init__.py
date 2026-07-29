"""
Agents Module
Agent管理模块 - AIDP Unified Platform

Agent = Instructions + Skills + Rules + Knowledge
三层作用域: global(模板) / personal / project
"""

from app.modules import BaseModule, register_module


@register_module(name='agents', enabled=True)
class AgentsModule(BaseModule):
    name = "agents"
    description = "Agent管理，组合 Instructions/Skills/Rules/Knowledge"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as agents_router
        app.include_router(agents_router, prefix="/api/agents")

    def on_startup(self):
        print(f"[AgentsModule] Agent模块已启动")

    def on_shutdown(self):
        print(f"[AgentsModule] Agent模块已停止")