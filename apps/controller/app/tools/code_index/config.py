from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Code Index Tool"
    APP_VERSION: str = "0.1.0"
    PORT: int = 18086
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/code_index.db"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
