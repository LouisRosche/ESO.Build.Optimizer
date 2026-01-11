"""
Configuration settings for ESO Build Optimizer API.

Uses environment variables with sensible defaults for development.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "ESO Build Optimizer API"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False)
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"]
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/eso_optimizer"
    )

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_USE_SECURE_SECRET_KEY"
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_requests_per_day: int = 10000
    rate_limit_burst_size: int = 10

    # Password Hashing
    password_hash_rounds: int = 12

    # External Services (for future use)
    redis_url: str | None = None
    sentry_dsn: str | None = None

    # ESO Game Data
    current_patch: str = "U48"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Parse comma-separated origins string to list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
