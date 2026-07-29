# AIDP Config Package
"""
AIDP 配置包

包含:
- menu.yaml: 菜单配置
- permissions.yaml: 权限配置
- Settings: 应用配置
"""

from app._config import Settings, settings

__all__ = ["Settings", "settings"]
