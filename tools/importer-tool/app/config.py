from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "importer-tool"
    APP_VERSION: str = "0.1.0"
    PORT: int = 18085
    HOST: str = "0.0.0.0"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aidp_importer"
    DATABASE_ECHO: bool = False

    CONTROLLER_URL: str = "http://localhost:8883"

    MAX_FILE_SIZE_MB: int = 5
    MAX_TEXT_LENGTH: int = 100000
    URL_TIMEOUT_SECONDS: int = 15
    URL_MAX_LENGTH: int = 50000
    DIRECTORY_MAX_FILES: int = 500

    TEXT_EXTENSIONS: list[str] = [
        ".md", ".txt", ".yaml", ".yml", ".json", ".xml", ".sql",
        ".py", ".js", ".ts", ".sh", ".properties", ".env",
        ".cfg", ".ini", ".toml", ".csv", ".html", ".css",
    ]
    IGNORE_DIRS: list[str] = [
        ".git", "node_modules", "__pycache__", "venv",
        ".venv", "dist", "build", ".mypy_cache", ".pytest_cache",
    ]

    AI_API_KEY: str = ""
    AI_API_BASE: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4o"
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.3


settings = Settings()
