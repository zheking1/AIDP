"""
AIDP Configuration Loader
加载和管理 YAML 配置文件
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器 - 加载和验证 YAML 配置文件"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置文件目录，默认使用 app/config
        """
        if config_dir is None:
            # 获取当前文件所在目录的上级目录中的 config
            config_dir = Path(__file__).parent.parent / "config"
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Any] = {}
    
    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        加载 YAML 文件
        
        Args:
            filename: 文件名（如 'menu.yaml'）
            
        Returns:
            解析后的配置字典
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: YAML 格式错误
        """
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            logger.debug(f"Loaded config: {filename}")
            return data or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {filename}: {e}")
    
    def load_menu_config(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        加载菜单配置
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            菜单配置字典
        """
        if not use_cache or 'menu' not in self._cache:
            self._cache['menu'] = self.load_yaml('menu.yaml')
        return self._cache['menu']
    
    def load_permissions_config(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        加载权限配置
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            权限配置字典
        """
        if not use_cache or 'permissions' not in self._cache:
            self._cache['permissions'] = self.load_yaml('permissions.yaml')
        return self._cache['permissions']
    
    def clear_cache(self):
        """清除配置缓存（用于热重载）"""
        self._cache.clear()
        logger.info("Config cache cleared")
    
    def reload_all(self):
        """重新加载所有配置"""
        self.clear_cache()
        self.load_menu_config(use_cache=False)
        self.load_permissions_config(use_cache=False)
        logger.info("All configs reloaded")


# 全局配置加载器实例
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """获取全局配置加载器实例（单例模式）"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def get_menu_config(use_cache: bool = True) -> Dict[str, Any]:
    """获取菜单配置的快捷函数"""
    return get_config_loader().load_menu_config(use_cache)


def get_permissions_config(use_cache: bool = True) -> Dict[str, Any]:
    """获取权限配置的快捷函数"""
    return get_config_loader().load_permissions_config(use_cache)


def reload_configs():
    """重新加载所有配置的快捷函数"""
    get_config_loader().reload_all()
