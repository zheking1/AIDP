from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "asset-tool"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 18082

    DATABASE_URL: str = ""
    DATABASE_ECHO: bool = False

    SECRET_KEY: str = ""

    SEARCH_DEFAULT_TOP_K: int = 8
    SEARCH_MAX_TOP_K: int = 50

    UPLOAD_MAX_CONTENT_SIZE_MB: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
