"""
Configuration settings for ESO Build Optimizer API.

Uses environment variables with sensible defaults for development.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
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
    def parse_origins(cls, v):
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

    @field_validator("jwt_secret_key", mode="after")
    @classmethod
    def validate_jwt_secret_length(cls, v):
        """Reject JWT secrets shorter than 32 characters."""
        if len(v) < 32:
            raise ValueError(
                "JWT secret key must be at least 32 characters"
            )
        return v

    @model_validator(mode="after")
    def validate_production_settings(self):
        """Cross-field validation that requires all fields to be resolved.

        Uses model_validator instead of field_validator because field validators
        run in definition order — fields defined later (like 'environment') may
        not be available in info.data when validating earlier fields (like 'debug').
        """
        env = self.environment

        if env == "production" and self.debug is True:
            raise ValueError(
                "Debug mode must not be enabled in production. "
                "Set DEBUG=false or remove the DEBUG environment variable."
            )

        if env == "production" and "postgres:postgres@localhost" in self.database_url:
            raise ValueError(
                "Default database credentials must not be used in production. "
                "Set the DATABASE_URL environment variable to a secure connection string."
            )

        if env in ("production", "staging") and self.jwt_secret_key == "CHANGE_ME_IN_PRODUCTION_USE_SECURE_SECRET_KEY":
            raise ValueError(
                "JWT secret key must be changed from the default value in production/staging. "
                "Set the JWT_SECRET_KEY environment variable to a secure random string."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
