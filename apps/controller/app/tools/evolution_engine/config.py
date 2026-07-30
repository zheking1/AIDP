from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Evolution Engine"
    APP_VERSION: str = "0.1.0"
    PORT: int = 18089
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/evolution_engine.db"
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen2.5:7b"
    BATCH_SIZE: int = 10
    ANALYSIS_TIMEOUT: int = 30
    UPDATE_RETRY: int = 3
    UPDATE_TIMEOUT: int = 10

    ROUTE_ERROR: list = ["memory"]
    ROUTE_SUCCESS: list = ["memory", "asset"]
    ROUTE_OPTIMIZATION: list = ["knowledge", "code_index"]

    class Config:
        extra = "allow"
        env_file = ".env"


settings = Settings()

