import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "PDF Classifier API"
    version: str = "1.0.0"

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "pdf_classifier"

    uploads_dir: str = "uploads"

    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    jwt_secret: str = "change-me-to-a-random-32-char-secret-key-123"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    allow_registration: bool = True
    admin_username: str = ""
    admin_password: str = ""

    ai_provider: str = "disabled"
    ai_base_url: str = "https://opencode.ai/zen/v1"
    ai_model: str = "big-pickle"
    ai_api_key: str = ""
    ai_timeout_seconds: float = 30.0
    ai_max_input_chars: int = 6000
    ai_fallback_to_keywords: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            texto = value.strip()
            if not texto:
                return []
            if texto.startswith("[") and texto.endswith("]"):
                try:
                    return json.loads(texto)
                except json.JSONDecodeError:
                    pass
            return [origen.strip() for origen in texto.split(",") if origen.strip()]
        return value

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.db_user,
            password=self.db_password or None,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )

    @property
    def uploads_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / self.uploads_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()