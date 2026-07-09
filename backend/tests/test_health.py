"""
Health check endpoint tests.

Validates the health check endpoint behavior and response format.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


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
