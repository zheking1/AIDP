from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "sandbox-tool"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 18083

    DATABASE_URL: str = ""
    DATABASE_ECHO: bool = False

    SECRET_KEY: str = ""

    EXECUTION_TIMEOUT: int = 30
    EXECUTION_MAX_OUTPUT: int = 10240

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
