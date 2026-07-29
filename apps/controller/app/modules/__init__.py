"""
AIDP Module System
模块注册和管理系统
"""

from typing import Dict, Type, List, Optional, Any
from fastapi import FastAPI, APIRouter
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseModule(ABC):
    """
    模块基类
    
    所有工具模块都需要继承此类
    
    示例:
        @register_module(name='knowledge')
        class KnowledgeModule(BaseModule):
            name = "knowledge"
            description = "文档知识库管理"
            
            def register_routes(self, app: FastAPI):
                from .routes import router
                app.include_router(router, prefix="/api/knowledge")
    """
    
    # 模块元数据
    name: str = ""  # 模块标识名
    description: str = ""  # 模块描述
    version: str = "1.0.0"  # 模块版本
    enabled: bool = True  # 是否启用
    
    # 依赖的其他模块
    dependencies: List[str] = []
    
    def __init__(self):
        self.router: Optional[APIRouter] = None
        self.app: Optional[FastAPI] = None
    
    @abstractmethod
    def register_routes(self, app: FastAPI):
        """
        注册路由
        
        Args:
            app: FastAPI 应用实例
        """
        pass
    
    def register_models(self):
        """注册数据库模型（可选）"""
        pass
    
    def register_events(self):
        """注册事件处理器（可选）"""
        pass
    
    def on_startup(self):
        """模块启动时调用（可选）"""
        logger.info(f"Module {self.name} started")
    
    def on_shutdown(self):
        """模块关闭时调用（可选）"""
        logger.info(f"Module {self.name} stopped")
    
    def get_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'enabled': self.enabled,
            'dependencies': self.dependencies
        }


# 模块注册表
_registered_modules: Dict[str, Type[BaseModule]] = {}
_module_instances: Dict[str, BaseModule] = {}


def register_module(name: str, enabled: bool = True):
    """
    模块注册装饰器
    
    用法:
        @register_module(name='knowledge')
        class KnowledgeModule(BaseModule):
            ...
    
    Args:
        name: 模块名称（唯一标识）
        enabled: 是否默认启用
        
    Returns:
        装饰器函数
    """
    def decorator(cls: Type[BaseModule]):
        if not issubclass(cls, BaseModule):
            raise TypeError(f"Module {name} must inherit from BaseModule")
        
        cls.name = name
        cls.enabled = enabled
        _registered_modules[name] = cls
        logger.debug(f"Registered module: {name}")
        return cls
    return decorator


def get_registered_modules() -> Dict[str, Type[BaseModule]]:
    """
    获取所有已注册的模块
    
    Returns:
        模块名称到模块类的映射
    """
    return _registered_modules.copy()


def get_module_class(name: str) -> Optional[Type[BaseModule]]:
    """
    获取模块类
    
    Args:
        name: 模块名称
        
    Returns:
        模块类或 None
    """
    return _registered_modules.get(name)


def get_module_instance(name: str) -> Optional[BaseModule]:
    """
    获取模块实例
    
    Args:
        name: 模块名称
        
    Returns:
        模块实例或 None
    """
    return _module_instances.get(name)


def init_module(name: str, app: FastAPI) -> Optional[BaseModule]:
    """
    初始化模块
    
    Args:
        name: 模块名称
        app: FastAPI 应用实例
        
    Returns:
        模块实例或 None
    """
    module_class = _registered_modules.get(name)
    if not module_class:
        logger.warning(f"Module not found: {name}")
        return None
    
    if not module_class.enabled:
        logger.info(f"Module {name} is disabled")
        return None
    
    # 检查依赖
    for dep in module_class.dependencies:
        if dep not in _module_instances:
            logger.error(f"Module {name} depends on {dep} which is not initialized")
            return None
    
    # 创建实例
    instance = module_class()
    instance.app = app
    _module_instances[name] = instance
    
    # 注册路由
    try:
        instance.register_routes(app)
        logger.info(f"Registered routes for module: {name}")
    except Exception as e:
        logger.error(f"Failed to register routes for module {name}: {e}")
        return None
    
    # 注册模型
    try:
        instance.register_models()
    except Exception as e:
        logger.error(f"Failed to register models for module {name}: {e}")
    
    # 注册事件
    try:
        instance.register_events()
    except Exception as e:
        logger.error(f"Failed to register events for module {name}: {e}")
    
    return instance


def init_all_modules(app: FastAPI, include: Optional[List[str]] = None) -> List[str]:
    """
    初始化所有模块
    
    Args:
        app: FastAPI 应用实例
        include: 指定要初始化的模块列表（None 表示全部）
        
    Returns:
        成功初始化的模块名称列表
    """
    initialized = []
    
    # 确定要初始化的模块
    modules_to_init = include if include else list(_registered_modules.keys())
    
    # 按依赖顺序初始化
    pending = set(modules_to_init)
    while pending:
        # 找到没有未初始化依赖的模块
        ready = set()
        for name in pending:
            module_class = _registered_modules.get(name)
            if not module_class:
                continue
            
            # 检查依赖是否都已初始化
            deps_satisfied = all(
                dep in _module_instances or dep not in modules_to_init
                for dep in module_class.dependencies
            )
            
            if deps_satisfied:
                ready.add(name)
        
        if not ready:
            # 存在循环依赖
            logger.error(f"Circular dependency detected: {pending}")
            break
        
        # 初始化准备好的模块
        for name in ready:
            instance = init_module(name, app)
            if instance:
                initialized.append(name)
            pending.remove(name)
    
    logger.info(f"Initialized {len(initialized)} modules: {initialized}")
    return initialized


def shutdown_all_modules():
    """关闭所有模块"""
    for name, instance in _module_instances.items():
        try:
            instance.on_shutdown()
        except Exception as e:
            logger.error(f"Error shutting down module {name}: {e}")
    
    _module_instances.clear()
    logger.info("All modules shut down")


def get_module_info() -> List[Dict[str, Any]]:
    """
    获取所有模块信息
    
    Returns:
        模块信息列表
    """
    info = []
    for name, module_class in _registered_modules.items():
        instance = _module_instances.get(name)
        info.append({
            'name': name,
            'description': module_class.description,
            'version': module_class.version,
            'enabled': module_class.enabled,
            'initialized': instance is not None,
            'dependencies': module_class.dependencies
        })
    return info


# 快捷函数
def require_module(name: str):
    """
    确保模块已初始化
    
    Args:
        name: 模块名称
        
    Raises:
        RuntimeError: 如果模块未初始化
    """
    if name not in _module_instances:
        raise RuntimeError(f"Module {name} is not initialized")
