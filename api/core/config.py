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
    trusted_proxies: set[str] = Field(default_factory=set)

    # Password Hashing
    password_hash_rounds: int = 12

    # External Services (for future use)
    redis_url: str | None = None
    sentry_dsn: str | None = None

    # ESO Game Data
    current_patch: str = "U48"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v, info):
        """Parse comma-separated origins string to list and reject wildcard with credentials."""
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(",")]
        else:
            origins = v
        if "*" in origins:
            raise ValueError(
                "Wildcard '*' is not allowed in allowed_origins when credentials are enabled. "
                "Specify explicit origin URLs instead."
            )
        return origins

    @field_validator("trusted_proxies", mode="before")
    @classmethod
    def parse_trusted_proxies(cls, v):
        """Parse comma-separated trusted proxy IPs to set."""
        if isinstance(v, str):
            return {ip.strip() for ip in v.split(",") if ip.strip()}
        return v

    @field_validator("debug", mode="after")
    @classmethod
    def validate_debug_mode(cls, v, info):
        """Prevent debug mode in production."""
        environment = info.data.get("environment", "development")
        if environment == "production" and v is True:
            raise ValueError(
                "Debug mode must not be enabled in production. "
                "Set DEBUG=false or remove the DEBUG environment variable."
            )
        return v

    @field_validator("database_url", mode="after")
    @classmethod
    def validate_database_url(cls, v, info):
        """Reject default database credentials in production."""
        environment = info.data.get("environment", "development")
        if environment == "production" and "postgres:postgres@localhost" in v:
            raise ValueError(
                "Default database credentials must not be used in production. "
                "Set the DATABASE_URL environment variable to a secure connection string."
            )
        return v

    @field_validator("jwt_secret_key", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v, info):
        """Raise an error if the default JWT secret is used in production/staging."""
        # Access other field values via info.data
        environment = info.data.get("environment", "development")
        if environment in ("production", "staging") and v == "CHANGE_ME_IN_PRODUCTION_USE_SECURE_SECRET_KEY":
            raise ValueError(
                "JWT secret key must be changed from the default value in production/staging. "
                "Set the JWT_SECRET_KEY environment variable to a secure random string."
            )
        if len(v) < 32:
            raise ValueError(
                "JWT secret key must be at least 32 characters"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
