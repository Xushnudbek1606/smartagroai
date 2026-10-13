from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # --- app ---
    APP_NAME: str = "SmartAgroAI"
    ENVIRONMENT: str = "development"  # development | production | test
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # --- database ---
    DATABASE_URL: str = "postgresql+psycopg://smartagro:smartagro@localhost:5432/smartagro"
    DATABASE_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- security ---
    JWT_SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    INVITATION_EXPIRE_MINUTES: int = 30
    TEMP_PASSWORD_TTL_HOURS: int = 72
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 8
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300
    API_RATE_LIMIT_ATTEMPTS: int = 120
    API_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # --- files / uploads ---
    UPLOAD_STORAGE_PATH: str = "./uploads"
    UPLOAD_MAX_BYTES: int = 8 * 1024 * 1024  # 8 MB
    UPLOAD_ALLOWED_TYPES: str = "image/jpeg,image/png,image/webp"

    # --- external services ---
    WEATHER_API_KEY: str = ""
    WEATHER_PROVIDER: str = "openweathermap"
    WEATHER_CACHE_TTL_SECONDS: int = 600
    FORECAST_CACHE_TTL_SECONDS: int = 3600

    AI_PROVIDER: str = "none"  # none | openai | anthropic | custom
    AI_API_KEY: str = ""
    AI_MODEL_NAME: str = ""
    AI_CUSTOM_BASE_URL: str = ""
    AI_TIMEOUT_SECONDS: int = 60

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_API_BASE: str = "https://api.telegram.org"

    REDIS_URL: str = ""

    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://localhost:4173"

    # --- telegram bot location (shared with bot container) ---
    BACKEND_INTERNAL_URL: str = "http://localhost:8000"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _coerce_origins(cls, v):  # allow list-style env values
        if isinstance(v, list):
            return ",".join(v)
        return v

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @property
    def upload_dir(self) -> Path:
        return Path(self.UPLOAD_STORAGE_PATH).expanduser().resolve()

    @property
    def ai_configured(self) -> bool:
        if self.AI_PROVIDER in ("", "none"):
            return False
        if self.AI_PROVIDER == "custom":
            return bool(self.AI_CUSTOM_BASE_URL)
        return bool(self.AI_API_KEY) and bool(self.AI_MODEL_NAME)

    @property
    def weather_configured(self) -> bool:
        return bool(self.WEATHER_API_KEY)

    @property
    def telegram_configured(self) -> bool:
        return bool(self.TELEGRAM_BOT_TOKEN)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
