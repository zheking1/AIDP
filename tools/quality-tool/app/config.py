from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "quality-tool"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 18084

    DATABASE_URL: str = ""
    DATABASE_ECHO: bool = False

    SECRET_KEY: str = ""

    LINT_MAX_LINE_LENGTH: int = 120
    LINT_CHECK_TRAILING_WHITESPACE: bool = True
    LINT_CHECK_MISSING_NEWLINE: bool = True

    SECURITY_CHECK_HARDCODED_SECRETS: bool = True
    SECURITY_CHECK_SQL_INJECTION: bool = True
    SECURITY_CHECK_DANGEROUS_FUNCTIONS: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
