from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "asset-tool"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 18082

    DATABASE_URL: str = "postgresql+asyncpg://novel_os:jygame_postgres_01@127.0.0.1:5432/novel_os"
    DATABASE_ECHO: bool = False

    SECRET_KEY: str = "asset-tool-secret-change-in-production"

    SEARCH_DEFAULT_TOP_K: int = 8
    SEARCH_MAX_TOP_K: int = 50

    UPLOAD_MAX_CONTENT_SIZE_MB: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
