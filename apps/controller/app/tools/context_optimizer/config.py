from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Context Optimizer"
    APP_VERSION: str = "0.1.0"
    PORT: int = 18088
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/context_optimizer.db"
    _echo: bool = False
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen2.5:7b"
    DEFAULT_BUDGET: int = 8000
    MIN_BUDGET: int = 1000
    MAX_BUDGET: int = 32000
    SIMILARITY_THRESHOLD: float = 0.7
    MAX_RESULTS_PER_TOOL: int = 10
    SUMMARY_RATIO: float = 0.3
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600
    CACHE_MAX_SIZE: int = 1000

    TOOL_PRIORITY_CODE_INDEX: float = 1.5
    TOOL_PRIORITY_KNOWLEDGE: float = 1.2
    TOOL_PRIORITY_MEMORY: float = 1.0
    TOOL_PRIORITY_ASSET: float = 0.8
    TOOL_PRIORITY_QUALITY: float = 0.5
    TOOL_PRIORITY_SANDBOX: float = 0.3

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
