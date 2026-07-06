from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "File Watcher Tool"
    APP_VERSION: str = "0.1.0"
    PORT: int = 18091
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/file_watcher.db"
    CODE_INDEX_URL: str = "http://127.0.0.1:18086"
    CONTROLLER_URL: str = "http://127.0.0.1:8883"
    DEBOUNCE_SECONDS: float = 1.0
    IGNORED_DIRS: list = [".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"]

    class Config:
        env_file = ".env"


settings = Settings()
