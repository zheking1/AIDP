import os
from typing import Optional


class SecretManager:
    _instance = None
    _secrets = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        self._secrets = {
            "JWT_SECRET": os.getenv("JWT_SECRET"),
            "LLM_API_KEY": os.getenv("LLM_API_KEY"),
            "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN"),
            "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        }

    def get(self, key: str) -> Optional[str]:
        return self._secrets.get(key)

    def set(self, key: str, value: str):
        self._secrets[key] = value
