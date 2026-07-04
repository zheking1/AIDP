from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Doc Index Tool"
    APP_VERSION: str = "0.1.0"
    PORT: int = 18087
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/doc_index.db"

    class Config:
        env_file = ".env"


settings = Settings()
