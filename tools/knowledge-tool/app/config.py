from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "knowledge-tool"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 18081

    DATABASE_URL: str = "postgresql+asyncpg://novel_os:jygame_postgres_01@127.0.0.1:5432/novel_os"
    DATABASE_ECHO: bool = False

    SECRET_KEY: str = "knowledge-tool-secret-change-in-production"

    STORAGE_PROVIDER: str = "local"
    STORAGE_LOCAL_ROOT: str = "./data/knowledge"

    EMBEDDING_PROVIDER: str = "mock"
    EMBEDDING_MODEL: str = "mock-embedding-v1"
    EMBEDDING_DIMENSION: int = 384

    CHUNK_DEFAULT_SIZE: int = 800
    CHUNK_DEFAULT_OVERLAP: int = 120
    CHUNK_MAX_SIZE: int = 1600

    SEARCH_DEFAULT_TOP_K: int = 8
    SEARCH_MAX_TOP_K: int = 50
    SEARCH_DEFAULT_MODE: str = "hybrid"

    UPLOAD_MAX_FILE_SIZE_MB: int = 50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
