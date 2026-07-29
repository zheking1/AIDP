"""
AIDP Project Context
项目上下文管理
"""

from typing import Optional, Any, Dict
from fastapi import Request, HTTPException
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Project:
    """项目数据类"""
    id: int
    name: str
    description: Optional[str] = None
    owner_id: Optional[str] = None
    visibility: str = "private"  # private, internal, public
    tech_stack: Optional[list] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'owner_id': self.owner_id,
            'visibility': self.visibility,
            'tech_stack': self.tech_stack or [],
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class ProjectContext:
    """项目上下文 - 管理当前项目状态"""
    
    def __init__(self):
        self.current_project: Optional[Project] = None
        self.user: Optional[Any] = None
    
    async def set_project(self, project_id: int) -> bool:
        """
        设置当前项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            是否成功设置
        """
        try:
            # TODO: 从数据库查询项目
            # 暂时使用模拟数据
            self.current_project = await self._get_project_from_db(project_id)
            return True
        except Exception as e:
            logger.error(f"Failed to set project {project_id}: {e}")
            return False
    
    async def _get_project_from_db(self, project_id: int) -> Optional[Project]:
        """从数据库获取项目"""
        # TODO: 实现数据库查询
        # 暂时返回模拟数据
        return Project(
            id=project_id,
            name=f"Project {project_id}",
            description="Test project",
            owner_id="user_1"
        )
    
    @property
    def is_project_selected(self) -> bool:
        """是否已选择项目"""
        return self.current_project is not None
    
    @property
    def project_id(self) -> Optional[int]:
        """获取当前项目ID"""
        return self.current_project.id if self.current_project else None
    
    def require_project(self):
        """
        要求必须有项目上下文
        
        Raises:
            HTTPException: 如果没有选择项目
        """
        if not self.is_project_selected:
            raise HTTPException(
                status_code=400,
                detail="Project context required"
            )
    
    def check_project_access(self, project_id: int) -> bool:
        """
        检查当前用户是否有权限访问指定项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            是否有权限
        """
        # TODO: 实现项目权限检查
        # 1. 检查用户是否是项目成员
        # 2. 检查项目可见性
        return True


async def get_project_context(
    request: Request,
    project_id: Optional[int] = None
) -> ProjectContext:
    """
    获取项目上下文依赖
    
    用法:
        @router.get("/api/projects/{project_id}/documents")
        async def list_documents(
            context: ProjectContext = Depends(get_project_context)
        ):
            context.require_project()
            ...
    
    Args:
        request: FastAPI 请求对象
        project_id: 项目ID（可选，从路径参数或查询参数获取）
        
    Returns:
        项目上下文对象
    """
    context = ProjectContext()
    
    # 从各种来源获取项目ID
    if project_id is None:
        # 从路径参数获取
        project_id = request.path_params.get('project_id')
        if project_id:
            project_id = int(project_id)
    
    if project_id is None:
        # 从查询参数获取
        project_id_str = request.query_params.get('project_id')
        if project_id_str:
            project_id = int(project_id_str)
    
    if project_id is None:
        # 从请求体获取（POST/PUT）
        try:
            body = await request.json()
            project_id = body.get('project_id')
        except:
            pass
    
    # 设置项目
    if project_id:
        await context.set_project(project_id)
    
    return context


class ProjectContextMiddleware:
    """项目上下文中间件 - 自动注入项目上下文"""
    
    async def __call__(self, request: Request, call_next):
        """
        中间件处理
        
        自动从请求中提取 project_id 并设置上下文
        """
        # 创建上下文
        context = ProjectContext()
        
        # 尝试获取项目ID
        project_id = request.path_params.get('project_id')
        if project_id:
            try:
                await context.set_project(int(project_id))
            except:
                pass
        
        # 将上下文附加到请求状态
        request.state.project_context = context
        
        # 继续处理请求
        response = await call_next(request)
        return response


# 快捷函数
def get_current_project(request: Request) -> Optional[Project]:
    """
    从请求中获取当前项目
    
    Args:
        request: FastAPI 请求对象
        
    Returns:
        当前项目对象或 None
    """
    context = getattr(request.state, 'project_context', None)
    if context:
        return context.current_project
    return None
