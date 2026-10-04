from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    jwt_secret: str = "change-me-to-a-random-32-char-secret-key-123"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    ai_provider: str = "disabled"
    ai_base_url: str = "https://opencode.ai/zen/v1"
    ai_model: str = "big-pickle"
    ai_api_key: str = ""
    ai_timeout_seconds: float = 30.0
    ai_max_input_chars: int = 6000
    ai_fallback_to_keywords: bool = True

    @property
    def database_url(self) -> str:
        password = f":{self.db_password}" if self.db_password else ""
        return (
            f"mysql+pymysql://{self.db_user}{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def uploads_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / self.uploads_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()