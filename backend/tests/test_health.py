"""
Health check endpoint tests.

Validates the health check endpoint behavior and response format.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.endpoints import ops
from app.core.config import settings


class TestHealthEndpoint:
    """Test suite for the /api/v1/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_200(self, client: AsyncClient) -> None:
        """Verify the health endpoint returns a 200 status code."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_structure(self, client: AsyncClient) -> None:
        """Verify the health response contains all required fields."""
        response = await client.get("/api/v1/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data
        assert "services" in data
        assert "uptime_seconds" in data

    @pytest.mark.asyncio
    async def test_health_version_format(self, client: AsyncClient) -> None:
        """Verify the version is a non-empty string."""
        response = await client.get("/api/v1/health")
        data = response.json()

        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    @pytest.mark.asyncio
    async def test_health_status_is_string(self, client: AsyncClient) -> None:
        """Verify the status field is a string."""
        response = await client.get("/api/v1/health")
        data = response.json()

        assert isinstance(data["status"], str)

    @pytest.mark.asyncio
    async def test_health_services_is_list(self, client: AsyncClient) -> None:
        """Verify the services field is a list."""
        response = await client.get("/api/v1/health")
        data = response.json()

        assert isinstance(data["services"], list)

    @pytest.mark.asyncio
    async def test_readiness_reports_enabled_dependencies(self, client: AsyncClient) -> None:
        """Readiness exposes the dependency state used by orchestrators."""
        response = await client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["services"]["database"] == "connected"

    @pytest.mark.asyncio
    async def test_readiness_checks_enabled_dependencies(self, client: AsyncClient) -> None:
        """Enabled Neo4j and Redis dependencies must be reachable before readiness."""
        original_neo4j = settings.NEO4J_ENABLED
        original_redis = settings.REDIS_ENABLED
        settings.NEO4J_ENABLED = True
        settings.REDIS_ENABLED = True
        try:
            with (
                patch.object(ops, "check_neo4j_connection", new=AsyncMock(return_value=True)),
                patch.object(ops, "check_redis_connection", new=AsyncMock(return_value=True)),
            ):
                response = await client.get("/api/v1/ready")
        finally:
            settings.NEO4J_ENABLED = original_neo4j
            settings.REDIS_ENABLED = original_redis

        assert response.status_code == 200
        assert response.json()["services"] == {
            "database": "connected",
            "neo4j": "connected",
            "redis": "connected",
        }

    @pytest.mark.asyncio
    async def test_readiness_fails_when_enabled_dependency_is_unavailable(
        self, client: AsyncClient
    ) -> None:
        """Readiness must fail closed when an enabled dependency is down."""
        original_neo4j = settings.NEO4J_ENABLED
        original_redis = settings.REDIS_ENABLED
        settings.NEO4J_ENABLED = True
        settings.REDIS_ENABLED = True
        try:
            with (
                patch.object(ops, "check_neo4j_connection", new=AsyncMock(return_value=False)),
                patch.object(ops, "check_redis_connection", new=AsyncMock(return_value=True)),
            ):
                response = await client.get("/api/v1/ready")
        finally:
            settings.NEO4J_ENABLED = original_neo4j
            settings.REDIS_ENABLED = original_redis

        assert response.status_code == 503
        assert response.json()["detail"] == {
            "status": "not_ready",
            "services": {
                "database": "connected",
                "neo4j": "unavailable",
                "redis": "connected",
            },
        }
