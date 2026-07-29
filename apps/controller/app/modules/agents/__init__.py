"""
Agents Module
Agent 领域专家身份模板 — LLM 根据技术栈自动生成
管线匹配: intent.domains → agent.domain_tags → 加载专用 instructions
"""

from app.modules import BaseModule, register_module


@register_module(name='agents', enabled=True)
class AgentsModule(BaseModule):
    name = "agents"
    description = "领域Agent管理 — 技术栈自动生成 + domain匹配"
    version = "2.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as agents_router
        app.include_router(agents_router, prefix="/api/agents")

    def on_startup(self):
        print(f"[AgentsModule] Agent模块已启动 v2.0")

    def on_shutdown(self):
        print(f"[AgentsModule] Agent模块已停止")