"""Application settings, read only from environment variables (or a .env file in dev)."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEV_JWT_SECRET = "change-me-dev-secret"  # noqa: S105 - known development default, rejected in prod
DEV_DATABASE_URL = "postgresql+psycopg://fintrack_app:fintrack_app@localhost:54329/fintrack"
DEV_MIGRATION_DATABASE_URL = "postgresql+psycopg://fintrack:fintrack@localhost:54329/fintrack"


class ConfigurationError(RuntimeError):
    """Raised when the runtime configuration is unsafe or incomplete."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = DEV_DATABASE_URL
    migration_database_url: str = DEV_MIGRATION_DATABASE_URL
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    password_reset_ttl_minutes: int = 30
    # Comma-separated in the environment (e.g. "https://a.example,https://b.example"); a JSON
    # list is also accepted.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "FinTrack <no-reply@fintrack.local>"
    frontend_base_url: str = "http://localhost:5173"
    upload_dir: str = "./data/uploads"
    redis_url: str = "redis://localhost:6379/0"
    login_max_failures: int = 5
    login_window_seconds: int = 15 * 60
    api_rate_limit: str = "300/minute"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                import json

                return json.loads(text)
            return [o.strip() for o in text.split(",") if o.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate_for_runtime(self) -> None:
        """Refuse unsafe production configuration (missing or default secrets)."""
        if not self.is_production:
            return
        problems: list[str] = []
        if not self.jwt_secret or self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be set to a random value of at least 32 characters")
        if "database_url" not in self.model_fields_set or self.database_url == DEV_DATABASE_URL:
            problems.append("DATABASE_URL must be set explicitly")
        if problems:
            raise ConfigurationError("Invalid production configuration: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
