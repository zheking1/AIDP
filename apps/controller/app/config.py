from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "aidp-controller"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 8883

    DATABASE_URL: str = ""
    DATABASE_ECHO: bool = False

    SECRET_KEY: str = ""

    INVOCATION_TIMEOUT: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
