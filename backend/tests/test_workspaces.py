"""
Workspace management tests.

Tests organizations, workspaces, projects, members, and invitations.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecureP@ss1",
        "display_name": "Test User",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "SecureP@ss1",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
class TestOrganizations:
    """Organization CRUD tests."""

    async def test_create_organization(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "orgadmin@test.com")
        resp = await client.post(
            "/api/v1/organizations",
            json={"name": "Test Org", "slug": "test-org", "description": "A test org"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Test Org"
        assert resp.json()["slug"] == "test-org"

    async def test_create_duplicate_slug(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "orgdup@test.com")
        await client.post(
            "/api/v1/organizations",
            json={"name": "Org One", "slug": "dup-slug"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.post(
            "/api/v1/organizations",
            json={"name": "Org Two", "slug": "dup-slug"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    async def test_list_organizations(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "orglist@test.com")
        await client.post(
            "/api/v1/organizations",
            json={"name": "Org A", "slug": "org-a"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_get_organization(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "orgget@test.com")
        create_resp = await client.post(
            "/api/v1/organizations",
            json={"name": "Get Org", "slug": "get-org"},
            headers={"Authorization": f"Bearer {token}"},
        )
        org_id = create_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/organizations/{org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Org"

    async def test_delete_organization(self, client: AsyncClient) -> None:
        token = await _register_and_login(client, "orgdel@test.com")
        create_resp = await client.post(
            "/api/v1/organizations",
            json={"name": "Del Org", "slug": "del-org"},
            headers={"Authorization": f"Bearer {token}"},
        )
        org_id = create_resp.json()["id"]
        resp = await client.delete(
            f"/api/v1/organizations/{org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestWorkspaces:
    """Workspace CRUD and permission tests."""

    async def _setup(self, client: AsyncClient) -> tuple[str, str]:
        token = await _register_and_login(client, "wsadmin@test.com")
        org_resp = await client.post(
            "/api/v1/organizations",
            json={"name": "WS Org", "slug": "ws-org"},
            headers={"Authorization": f"Bearer {token}"},
        )
        org_id = org_resp.json()["id"]
        return token, org_id

    async def test_create_workspace(self, client: AsyncClient) -> None:
        token, org_id = await self._setup(client)
        resp = await client.post(
            "/api/v1/workspaces",
            json={"organization_id": org_id, "name": "Test WS", "slug": "test-ws", "description": "Test workspace"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Test WS"

    async def test_list_workspaces(self, client: AsyncClient) -> None:
        token, org_id = await self._setup(client)
        await client.post(
            "/api/v1/workspaces",
            json={"organization_id": org_id, "name": "WS One", "slug": "ws-one"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            "/api/v1/workspaces",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_workspace_member_count(self, client: AsyncClient) -> None:
        token, org_id = await self._setup(client)
        ws_resp = await client.post(
            "/api/v1/workspaces",
            json={"organization_id": org_id, "name": "Member WS", "slug": "member-ws"},
            headers={"Authorization": f"Bearer {token}"},
        )
        ws_id = ws_resp.json()["id"]
        resp = await client.get(
            f"/api/v1/workspaces/{ws_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["member_count"] == 1

    async def test_delete_workspace(self, client: AsyncClient) -> None:
        token, org_id = await self._setup(client)
        ws_resp = await client.post(
            "/api/v1/workspaces",
            json={"organization_id": org_id, "name": "Del WS", "slug": "del-ws"},
            headers={"Authorization": f"Bearer {token}"},
        )
        ws_id = ws_resp.json()["id"]
        resp = await client.delete(
            f"/api/v1/workspaces/{ws_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestProjects:
    """Project CRUD and permission tests."""

    async def _setup(self, client: AsyncClient) -> tuple[str, str]:
        token = await _register_and_login(client, "projadm@test.com")
        org_resp = await client.post(
            "/api/v1/organizations",
            json={"name": "Proj Org", "slug": "proj-org"},
            headers={"Authorization": f"Bearer {token}"},
        )
        org_id = org_resp.json()["id"]
        ws_resp = await client.post(
            "/api/v1/workspaces",
            json={"organization_id": org_id, "name": "Proj WS", "slug": "proj-ws"},
            headers={"Authorization": f"Bearer {token}"},
        )
        ws_id = ws_resp.json()["id"]
        return token, ws_id

    async def test_create_project(self, client: AsyncClient) -> None:
        token, ws_id = await self._setup(client)
        resp = await client.post(
            "/api/v1/projects",
            json={"workspace_id": ws_id, "name": "Test Project", "slug": "test-project"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "active"

    async def test_list_projects(self, client: AsyncClient) -> None:
        token, ws_id = await self._setup(client)
        await client.post(
            "/api/v1/projects",
            json={"workspace_id": ws_id, "name": "Proj A", "slug": "proj-a"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.get(
            f"/api/v1/projects?workspace_id={ws_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_delete_project(self, client: AsyncClient) -> None:
        token, ws_id = await self._setup(client)
        proj_resp = await client.post(
            "/api/v1/projects",
            json={"workspace_id": ws_id, "name": "Del Proj", "slug": "del-proj"},
            headers={"Authorization": f"Bearer {token}"},
        )
        proj_id = proj_resp.json()["id"]
        resp = await client.delete(
            f"/api/v1/projects/{proj_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestPermissions:
    """Permission enforcement tests."""

    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/organizations")
        assert resp.status_code == 401

        resp = await client.get("/api/v1/workspaces")
        assert resp.status_code == 401

        resp = await client.get("/api/v1/projects?workspace_id=00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 401

    async def test_non_member_cannot_access_workspace(self, client: AsyncClient) -> None:
        owner_token = await _register_and_login(client, "owner@permtest.com")
        other_token = await _register_and_login(client, "other@permtest.com")

        org_resp = await client.post(
            "/api/v1/organizations",
            json={"name": "Perm Org", "slug": "perm-org"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        org_id = org_resp.json()["id"]
        ws_resp = await client.post(
            "/api/v1/workspaces",
            json={"organization_id": org_id, "name": "Perm WS", "slug": "perm-ws"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        ws_id = ws_resp.json()["id"]

        # Other user cannot list projects
        resp = await client.get(
            f"/api/v1/projects?workspace_id={ws_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403

    async def test_workspace_isolation(self, client: AsyncClient) -> None:
        """Verify users in different workspaces can't see each other's projects."""
        token1 = await _register_and_login(client, "user1@iso.com")
        token2 = await _register_and_login(client, "user2@iso.com")

        # User 1 creates org, workspace, project
        org1 = await client.post("/api/v1/organizations", json={"name": "Iso1", "slug": "iso1"}, headers={"Authorization": f"Bearer {token1}"})
        org1_id = org1.json()["id"]
        ws1 = await client.post("/api/v1/workspaces", json={"organization_id": org1_id, "name": "WS1", "slug": "ws1"}, headers={"Authorization": f"Bearer {token1}"})
        ws1_id = ws1.json()["id"]
        await client.post("/api/v1/projects", json={"workspace_id": ws1_id, "name": "P1", "slug": "p1"}, headers={"Authorization": f"Bearer {token1}"})

        # User 2 creates org, workspace, project
        org2 = await client.post("/api/v1/organizations", json={"name": "Iso2", "slug": "iso2"}, headers={"Authorization": f"Bearer {token2}"})
        org2_id = org2.json()["id"]
        ws2 = await client.post("/api/v1/workspaces", json={"organization_id": org2_id, "name": "WS2", "slug": "ws2"}, headers={"Authorization": f"Bearer {token2}"})
        ws2_id = ws2.json()["id"]
        await client.post("/api/v1/projects", json={"workspace_id": ws2_id, "name": "P2", "slug": "p2"}, headers={"Authorization": f"Bearer {token2}"})

        # User 2 cannot access User 1's workspace projects
        resp = await client.get(f"/api/v1/projects?workspace_id={ws1_id}", headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 403
