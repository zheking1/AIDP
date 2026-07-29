"""
Sandbox Module
代码沙箱模块 - AIDP Unified Platform
"""
from fastapi import APIRouter
from app.modules import BaseModule, register_module

router = APIRouter()


@register_module(name='sandbox', enabled=True)
class SandboxModule(BaseModule):
    name = "sandbox"
    description = "在线代码执行沙箱"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as sandbox_router
        app.include_router(sandbox_router, prefix="/api/sandbox")

    def register_models(self):
        pass