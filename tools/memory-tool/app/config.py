from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "memory-tool"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 18085

    DATABASE_URL: str = "postgresql+asyncpg://novel_os:jygame_postgres_01@127.0.0.1:5432/novel_os"
    DATABASE_ECHO: bool = False

    SECRET_KEY: str = "memory-tool-secret-change-in-production"

    MEMORY_DEFAULT_LIMIT: int = 50
    MEMORY_MAX_LIMIT: int = 200

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
