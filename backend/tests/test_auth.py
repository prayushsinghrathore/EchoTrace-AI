"""
Authentication endpoint tests.

Tests register, login, token refresh, and profile endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestRegistration:
    """Test user registration flow."""

    @pytest.mark.asyncio
    async def test_register_returns_201(self, client: AsyncClient) -> None:
        """Verify successful registration returns 201."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "SecureP@ss1",
            "display_name": "New User",
        })
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_register_returns_user_profile(self, client: AsyncClient) -> None:
        """Verify registration returns a valid user profile."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "profile@example.com",
            "password": "SecureP@ss1",
            "display_name": "Profile User",
        })
        data = response.json()
        assert "id" in data
        assert data["email"] == "profile@example.com"
        assert data["display_name"] == "Profile User"
        assert data["role"] == "user"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient) -> None:
        """Verify duplicate email returns 409."""
        await client.post("/api/v1/auth/register", json={
            "email": "dupe@example.com",
            "password": "SecureP@ss1",
            "display_name": "First",
        })
        response = await client.post("/api/v1/auth/register", json={
            "email": "dupe@example.com",
            "password": "SecureP@ss1",
            "display_name": "Second",
        })
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient) -> None:
        """Verify weak passwords are rejected."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "weakpw@example.com",
            "password": "short",
            "display_name": "Weak",
        })
        assert response.status_code == 422


class TestLogin:
    """Test user login flow."""

    @pytest.mark.asyncio
    async def test_login_returns_tokens(self, client: AsyncClient) -> None:
        """Verify successful login returns token pair."""
        await client.post("/api/v1/auth/register", json={
            "email": "logintest@example.com",
            "password": "SecureP@ss1",
            "display_name": "Login Test",
        })
        response = await client.post("/api/v1/auth/login", json={
            "email": "logintest@example.com",
            "password": "SecureP@ss1",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient) -> None:
        """Verify wrong password returns 401."""
        await client.post("/api/v1/auth/register", json={
            "email": "wrongpw@example.com",
            "password": "SecureP@ss1",
            "display_name": "Wrong PW",
        })
        response = await client.post("/api/v1/auth/login", json={
            "email": "wrongpw@example.com",
            "password": "WrongP@ss1",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient) -> None:
        """Verify login for nonexistent user returns 401."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "SecureP@ss1",
        })
        assert response.status_code == 401


class TestTokenRefresh:
    """Test token refresh flow."""

    @pytest.mark.asyncio
    async def test_refresh_returns_new_tokens(self, client: AsyncClient) -> None:
        """Verify refresh endpoint returns a new token pair."""
        await client.post("/api/v1/auth/register", json={
            "email": "refreshtest@example.com",
            "password": "SecureP@ss1",
            "display_name": "Refresh Test",
        })
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "refreshtest@example.com",
            "password": "SecureP@ss1",
        })
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, client: AsyncClient) -> None:
        """Verify invalid refresh token returns 401."""
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid-token-here",
        })
        assert response.status_code == 401


class TestProfile:
    """Test profile endpoints."""

    @pytest.mark.asyncio
    async def test_get_profile_requires_auth(self, client: AsyncClient) -> None:
        """Verify unauthenticated request returns 401."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_profile_returns_user(self, client: AsyncClient) -> None:
        """Verify authenticated request returns user profile."""
        await client.post("/api/v1/auth/register", json={
            "email": "profileget@example.com",
            "password": "SecureP@ss1",
            "display_name": "Profile Get",
        })
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "profileget@example.com",
            "password": "SecureP@ss1",
        })
        token = login_resp.json()["access_token"]

        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profileget@example.com"
        assert data["display_name"] == "Profile Get"

    @pytest.mark.asyncio
    async def test_update_profile(self, client: AsyncClient) -> None:
        """Verify profile update works."""
        await client.post("/api/v1/auth/register", json={
            "email": "profileupd@example.com",
            "password": "SecureP@ss1",
            "display_name": "Original",
        })
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "profileupd@example.com",
            "password": "SecureP@ss1",
        })
        token = login_resp.json()["access_token"]

        response = await client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"display_name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Updated Name"
