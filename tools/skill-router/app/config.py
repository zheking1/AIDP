from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """
    P5改进：增强配置类型安全和校验
    """
    # Database配置
    db_password: str = Field(default="change_me", description="Database password")
    database_url: str = Field(default="", description="Full database URL (optional)")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    
    # Admin配置
    admin_username: str = Field(default="admin", min_length=3, description="Admin username")
    admin_password: str = Field(default="", min_length=6, description="Admin password")
    skill_manager_api_key: str = Field(default="", description="Default API key for skill manager")
    
    # LLM配置
    llm_endpoint: str = Field(default="http://localhost:8000/v1", description="LLM API endpoint")
    llm_api_key: str = Field(default="sk-xxx", description="LLM API key")
    llm_model: str = Field(default="deepseek-v4-flash-free", description="LLM model name")
    
    # Embedding配置
    embedding_endpoint: str = Field(default="http://localhost:8000/v1", description="Embedding API endpoint")
    embedding_api_key: str = Field(default="sk-xxx", description="Embedding API key")
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model name")
    embedding_dim: int = Field(default=1024, gt=0, le=1536, description="Embedding dimension")
    
    # Timeout配置
    llm_timeout: int = Field(default=30, gt=0, le=300, description="LLM timeout in seconds")
    embedding_timeout: int = Field(default=15, gt=0, le=60, description="Embedding timeout in seconds")
    
    # Resolve配置
    resolve_top_k_default: int = Field(default=5, gt=0, le=10, description="Default top_k for resolve")
    cache_ttl_seconds: int = Field(default=3600, gt=0, le=86400, description="Cache TTL in seconds")
    
    # GitHub配置
    github_token: str = Field(default="", description="GitHub API token for higher rate limits (5000/hr vs 60/hr)")
    
    # P5改进：环境变量校验
    @validator("redis_url")
    def validate_redis_url(cls, v):
        if not v.startswith("redis://"):
            raise ValueError("Redis URL must start with 'redis://'")
        return v
    
    @validator("llm_endpoint", "embedding_endpoint")
    def validate_endpoint(cls, v):
        if not v.startswith("http://") and not v.startswith("https://"):
            raise ValueError("Endpoint must start with 'http://' or 'https://'")
        return v
    
    @validator("admin_password")
    def validate_admin_password(cls, v):
        if v == "admin123":
            # 生产环境警告（但不阻止）
            import warnings
            warnings.warn("Using default admin password 'admin123' is not recommended for production")
        return v
    
    @property
    def db_url(self) -> str:
        """
        P5改进：类型安全的属性访问
        """
        if self.database_url:
            return self.database_url
        return f"postgresql+asyncpg://app:{self.db_password}@localhost:5432/skill-manager"
    
    model_config = {"env_file": ".env", "extra": "ignore"}
    
    def validate_production_safety(self) -> list[str]:
        """
        P5改进：生产环境安全检查
        返回不安全的配置项列表
        """
        warnings = []
        
        if self.db_password == "change_me":
            warnings.append("Database password is default ('change_me')")
        
        if self.admin_password == "admin123":
            warnings.append("Admin password is default ('admin123')")
        
        if self.llm_api_key == "sk-xxx":
            warnings.append("LLM API key is placeholder ('sk-xxx')")
        
        if self.embedding_api_key == "sk-xxx":
            warnings.append("Embedding API key is placeholder ('sk-xxx')")
        
        return warnings


# P5改进：全局配置实例，带校验
try:
    settings = Settings()
    # 生产环境警告（仅在启动时显示）
    safety_warnings = settings.validate_production_safety()
    if safety_warnings:
        import logging
        logger = logging.getLogger(__name__)
        for warning in safety_warnings:
            logger.warning(f"Configuration safety warning: {warning}")
except Exception as e:
    # 配置加载失败时的处理
    import sys
    print(f"Configuration validation failed: {e}")
    sys.exit(1)
