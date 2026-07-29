"""
Quality Module
质量检查模块 - AIDP Unified Platform
"""
from fastapi import APIRouter
from app.modules import BaseModule, register_module

router = APIRouter()


@register_module(name='quality', enabled=True)
class QualityModule(BaseModule):
    name = "quality"
    description = "代码质量检查与安全扫描"
    version = "1.0.0"
    enabled = True
    dependencies = []

    def register_routes(self, app):
        from .routes import router as quality_router
        app.include_router(quality_router, prefix="/api/quality")

    def register_models(self):
        pass