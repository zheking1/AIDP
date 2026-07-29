"""
Workflows Module
流程引擎模块 - AIDP Unified Platform

多步骤、多 Agent 协作的流程定义与执行
"""

from app.modules import BaseModule, register_module


@register_module(name='workflows', enabled=True)
class WorkflowsModule(BaseModule):
    name = "workflows"
    description = "流程引擎，多步骤多 Agent 协作"
    version = "1.0.0"
    enabled = True
    dependencies = ['agents']

    def register_routes(self, app):
        from .routes import router as workflows_router
        app.include_router(workflows_router, prefix="/api/workflows")

    def on_startup(self):
        print(f"[WorkflowsModule] 流程模块已启动")

    def on_shutdown(self):
        print(f"[WorkflowsModule] 流程模块已停止")