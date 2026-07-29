"""
Evolution Module
两级进化系统：项目级进化 → 管理员审核 → 系统级进化
"""

from app.modules import BaseModule, register_module


@register_module(name='evolution', enabled=True)
class EvolutionModule(BaseModule):
    name = "evolution"
    description = "两级进化系统 — 项目级经验 → 审核 → 系统级最佳实践"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as evolution_router
        app.include_router(evolution_router, prefix="/api/evolution")

    def on_startup(self):
        print(f"[EvolutionModule] 进化模块已启动")

    def on_shutdown(self):
        print(f"[EvolutionModule] 进化模块已停止")