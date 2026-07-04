from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "aidp-controller"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 8883

    DATABASE_URL: str = "postgresql+asyncpg://novel_os:jygame_postgres_01@127.0.0.1:5432/novel_os"
    DATABASE_ECHO: bool = False

    SECRET_KEY: str = "controller-secret-change-in-production"

    INVOCATION_TIMEOUT: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
