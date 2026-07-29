"""
Skills Module
技能模块 - AIDP Unified Platform

提供三层技能管理: 全局/个人/项目
"""

from app.modules import BaseModule, register_module
@register_module(name='skills', enabled=True)
class SkillsModule(BaseModule):
    """
    技能模块
    
    提供三层技能管理: 全局技能、个人技能、项目技能
    支持技能解析、分组、导入导出
    """
    name = "skills"
    description = "三层技能管理，支持全局/个人/项目技能"
    version = "1.0.0"
    enabled = True
    dependencies = []
    
    def register_routes(self, app):
        """注册路由到主应用"""
        from .routes import router as skills_router
        app.include_router(skills_router, prefix="/api/skills")
    
    def on_startup(self):
        """模块启动时调用"""
        print(f"[SkillsModule] 技能模块已启动")
    
    def on_shutdown(self):
        """模块关闭时调用"""
        print(f"[SkillsModule] 技能模块已停止")

