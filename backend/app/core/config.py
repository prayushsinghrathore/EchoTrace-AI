"""
Centralized configuration management.

Uses pydantic-settings to load environment variables with validation.
All configuration values are accessed through a single `settings` instance.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Follows the principle of immutable configuration:
    - All values are validated at load time
    - No mutable globals
    - Single source of truth
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── General ─────────────────────────────────────────────────────────
    PROJECT_NAME: str = "EchoTrace AI"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    DEBUG: bool = True
    LOG_LEVEL: str = Field(default="DEBUG", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # ── Backend ─────────────────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = Field(default=8000, ge=1024, le=65535)
    SECRET_KEY: str = Field(
        default="",
        description="JWT signing secret. REQUIRED in production. Must be at least 32 characters.",
    )

    # ── PostgreSQL ──────────────────────────────────────────────────────
    POSTGRES_USER: str = "echotrace"
    POSTGRES_PASSWORD: str = "echotrace_secret"
    POSTGRES_DB: str = "echotrace"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    DATABASE_URL: Optional[str] = None
    DATABASE_SYNC_URL: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def build_database_urls(cls, data: dict) -> dict:
        """Construct DATABASE_URL if not explicitly provided."""
        if not data.get("DATABASE_URL"):
            data["DATABASE_URL"] = (
                f"postgresql+asyncpg://{data.get('POSTGRES_USER', 'echotrace')}"
                f":{data.get('POSTGRES_PASSWORD', 'echotrace_secret')}"
                f"@{data.get('POSTGRES_HOST', 'localhost')}"
                f":{data.get('POSTGRES_PORT', 5432)}"
                f"/{data.get('POSTGRES_DB', 'echotrace')}"
            )
        if not data.get("DATABASE_SYNC_URL"):
            data["DATABASE_SYNC_URL"] = (
                f"postgresql://{data.get('POSTGRES_USER', 'echotrace')}"
                f":{data.get('POSTGRES_PASSWORD', 'echotrace_secret')}"
                f"@{data.get('POSTGRES_HOST', 'localhost')}"
                f":{data.get('POSTGRES_PORT', 5432)}"
                f"/{data.get('POSTGRES_DB', 'echotrace')}"
            )
        return data

    ASYNC_DATABASE_URI: PostgresDsn | str = ""
    SYNC_DATABASE_URI: PostgresDsn | str = ""

    @model_validator(mode="after")
    def set_database_uris(self) -> "Settings":
        """Set validated database URIs after construction."""
        self.ASYNC_DATABASE_URI = self.DATABASE_URL  # type: ignore[assignment]
        self.SYNC_DATABASE_URI = self.DATABASE_SYNC_URL  # type: ignore[assignment]
        return self

    @model_validator(mode="after")
    def enforce_secret_key_in_production(self) -> "Settings":
        """Require a proper SECRET_KEY in production/staging environments."""
        if self.is_production or self.is_staging:
            if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be set and at least 32 characters long "
                    "in production/staging environments."
                )
        return self

    # ── Authentication ───────────────────────────────────────────────────
    AUTH_USE_COOKIES: bool = False
    AUTH_COOKIE_SECURE: bool = True
    AUTH_COOKIE_SAMESITE: str = "lax"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1)
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = Field(default=24, ge=1)
    PASSWORD_RESET_URL: str = "http://localhost:3000"

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_MAX: int = Field(default=10, ge=1)
    RATE_LIMIT_LOGIN_WINDOW: int = Field(default=300, ge=1)
    RATE_LIMIT_REGISTER_MAX: int = Field(default=5, ge=1)
    RATE_LIMIT_REGISTER_WINDOW: int = Field(default=3600, ge=1)
    RATE_LIMIT_REFRESH_MAX: int = Field(default=20, ge=1)
    RATE_LIMIT_REFRESH_WINDOW: int = Field(default=900, ge=1)
    RATE_LIMIT_RESET_MAX: int = Field(default=3, ge=1)
    RATE_LIMIT_RESET_WINDOW: int = Field(default=3600, ge=1)

    # ── Storage ─────────────────────────────────────────────────────────
    STORAGE_PROVIDER: str = "local"
    STORAGE_LOCAL_PATH: str = "./storage"
    STORAGE_S3_BUCKET: str = ""
    STORAGE_S3_REGION: str = ""
    STORAGE_S3_ACCESS_KEY: str = ""
    STORAGE_S3_SECRET_KEY: str = ""
    STORAGE_S3_ENDPOINT: str = ""
    MAX_UPLOAD_SIZE_MB: int = Field(default=500, ge=1, le=10240)
    ALLOWED_MIME_TYPES: list[str] = [
        "application/pdf", "application/zip", "application/x-tar", "application/gzip",
        "application/x-7z-compressed", "application/x-rar-compressed",
        "image/jpeg", "image/png", "image/tiff", "image/webp",
        "text/plain", "text/csv", "text/html", "text/xml", "text/json",
        "application/json", "application/xml",
        "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "video/mp4", "video/x-msvideo", "video/x-matroska",
        "audio/mpeg", "audio/wav", "audio/ogg",
        "application/octet-stream",
    ]

    # ── Neo4j ──────────────────────────────────────────────────────────
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "echotrace_neo4j"
    NEO4J_DATABASE: str = "neo4j"

    # ── Database Pool ──────────────────────────────────────────────────
    DB_POOL_SIZE: int = Field(default=20, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0, le=50)
    DB_ECHO: bool = False

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT == "staging"

    def __repr__(self) -> str:
        return f"<Settings environment={self.ENVIRONMENT} project={self.PROJECT_NAME}>"


# Singleton settings instance
settings = Settings()
