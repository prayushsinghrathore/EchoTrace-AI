"""
Health check schemas.

Provides request and response models for the health check endpoint.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ServiceStatus(BaseModel):
    """Status of an individual service dependency."""

    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Status: healthy | unhealthy | degraded")
    latency_ms: float | None = Field(None, description="Response latency in milliseconds")
    details: str | None = Field(None, description="Additional status details")


class HealthResponse(BaseModel):
    """Complete health check response."""

    status: str = Field(..., description="Overall system health: healthy | degraded | unhealthy")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Check timestamp")
    services: list[ServiceStatus] = Field(default_factory=list, description="Individual service statuses")
    uptime_seconds: float | None = Field(None, description="Application uptime")


class ErrorResponse(BaseModel):
    """Standard error response format."""

    detail: str = Field(..., description="Error detail message")
    error_code: str | None = Field(None, description="Machine-readable error code")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Error timestamp")
