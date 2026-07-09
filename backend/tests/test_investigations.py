"""
Investigation management tests.

Tests CRUD, entities, relationships, timeline, graph, search, dashboard, permissions.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _setup(client: AsyncClient) -> tuple[str, str, str]:
    """Create org, workspace, project, investigation. Returns (token, ws_id, inv_id)."""
    await client.post("/api/v1/auth/register", json={
        "email": "invt@test.com", "password": "SecureP@ss1", "display_name": "Inv Test",
    })
    login = await client.post("/api/v1/auth/login", json={"email": "invt@test.com", "password": "SecureP@ss1"})
    token = login.json()["access_token"]

    org = await client.post("/api/v1/organizations", json={"name": "Inv Org", "slug": "inv-org"},
                             headers={"Authorization": f"Bearer {token}"})
    org_id = org.json()["id"]
    ws = await client.post("/api/v1/workspaces", json={"organization_id": org_id, "name": "Inv WS", "slug": "inv-ws"},
                            headers={"Authorization": f"Bearer {token}"})
    ws_id = ws.json()["id"]

    inv = await client.post("/api/v1/investigations", json={"workspace_id": ws_id, "title": "Test Investigation"},
                             headers={"Authorization": f"Bearer {token}"})
    inv_id = inv.json()["id"]
    return token, ws_id, inv_id


@pytest.mark.asyncio
class TestInvestigations:
    """Investigation CRUD tests."""

    async def test_create(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        assert inv_id is not None
        # Verify via get
        resp = await client.get(f"/api/v1/investigations/{inv_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test Investigation"
        assert resp.json()["status"] == "open"

    async def test_list(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        resp = await client.get(f"/api/v1/investigations/workspace/{ws_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        resp = await client.patch(f"/api/v1/investigations/{inv_id}", json={"title": "Updated Inv", "priority": "high"},
                                   headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Inv"
        assert resp.json()["priority"] == "high"

    async def test_delete(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        resp = await client.delete(f"/api/v1/investigations/{inv_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204

    async def test_dashboard(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        resp = await client.get(f"/api/v1/investigations/dashboard/{ws_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert "open" in data

    async def test_search(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        resp = await client.get(f"/api/v1/investigations/search?q=Test&workspace_id={ws_id}",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_unauthenticated_blocked(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/investigations/workspace/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestEntities:
    """Entity CRUD tests."""

    async def test_create_entity(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        resp = await client.post(f"/api/v1/investigations/{inv_id}/entities", json={
            "type": "person", "label": "John Doe", "description": "A person of interest",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
        assert resp.json()["label"] == "John Doe"
        assert resp.json()["type"] == "person"

    async def test_list_entities(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        await client.post(f"/api/v1/investigations/{inv_id}/entities", json={"type": "email", "label": "test@example.com"},
                           headers={"Authorization": f"Bearer {token}"})
        resp = await client.get(f"/api/v1/investigations/{inv_id}/entities", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_entity(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        create = await client.post(f"/api/v1/investigations/{inv_id}/entities", json={"type": "ip", "label": "192.168.1.1"},
                                     headers={"Authorization": f"Bearer {token}"})
        eid = create.json()["id"]
        resp = await client.patch(f"/api/v1/investigations/entities/{eid}", json={"label": "10.0.0.1"},
                                   headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["label"] == "10.0.0.1"

    async def test_delete_entity(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        create = await client.post(f"/api/v1/investigations/{inv_id}/entities", json={"type": "device", "label": "Laptop-01"},
                                     headers={"Authorization": f"Bearer {token}"})
        eid = create.json()["id"]
        resp = await client.delete(f"/api/v1/investigations/entities/{eid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestRelationships:
    """Relationship CRUD tests."""

    async def _setup_entities(self, client: AsyncClient) -> tuple[str, str, str, str]:
        token, ws_id, inv_id = await _setup(client)
        e1 = await client.post(f"/api/v1/investigations/{inv_id}/entities", json={"type": "person", "label": "Alice"},
                                headers={"Authorization": f"Bearer {token}"})
        e2 = await client.post(f"/api/v1/investigations/{inv_id}/entities", json={"type": "email", "label": "alice@test.com"},
                                headers={"Authorization": f"Bearer {token}"})
        return token, inv_id, e1.json()["id"], e2.json()["id"]

    async def test_create_relationship(self, client: AsyncClient) -> None:
        token, inv_id, e1, e2 = await self._setup_entities(client)
        resp = await client.post(f"/api/v1/investigations/{inv_id}/relationships", json={
            "source_entity_id": e1, "target_entity_id": e2, "relationship_type": "uses", "confidence": 0.9,
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
        assert resp.json()["relationship_type"] == "uses"
        assert resp.json()["confidence"] == 0.9

    async def test_list_relationships(self, client: AsyncClient) -> None:
        token, inv_id, e1, e2 = await self._setup_entities(client)
        await client.post(f"/api/v1/investigations/{inv_id}/relationships", json={
            "source_entity_id": e1, "target_entity_id": e2, "relationship_type": "uses",
        }, headers={"Authorization": f"Bearer {token}"})
        resp = await client.get(f"/api/v1/investigations/{inv_id}/relationships", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_delete_relationship(self, client: AsyncClient) -> None:
        token, inv_id, e1, e2 = await self._setup_entities(client)
        create = await client.post(f"/api/v1/investigations/{inv_id}/relationships", json={
            "source_entity_id": e1, "target_entity_id": e2, "relationship_type": "connected_to",
        }, headers={"Authorization": f"Bearer {token}"})
        rid = create.json()["id"]
        resp = await client.delete(f"/api/v1/investigations/relationships/{rid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestTimeline:
    """Timeline event tests."""

    async def test_create_timeline_event(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        resp = await client.post(f"/api/v1/investigations/{inv_id}/timeline", json={
            "event_timestamp": "2026-07-10T12:00:00Z", "title": "Initial finding",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
        assert resp.json()["title"] == "Initial finding"

    async def test_list_timeline(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        await client.post(f"/api/v1/investigations/{inv_id}/timeline", json={
            "event_timestamp": "2026-07-10T12:00:00Z", "title": "Event 1",
        }, headers={"Authorization": f"Bearer {token}"})
        resp = await client.get(f"/api/v1/investigations/{inv_id}/timeline", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_delete_timeline_event(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        create = await client.post(f"/api/v1/investigations/{inv_id}/timeline", json={
            "event_timestamp": "2026-07-10T12:00:00Z", "title": "Delete me",
        }, headers={"Authorization": f"Bearer {token}"})
        eid = create.json()["id"]
        resp = await client.delete(f"/api/v1/investigations/timeline/{eid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestPermissions:
    """Permission enforcement tests."""

    async def test_non_member_cannot_access(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        await client.post("/api/v1/auth/register", json={
            "email": "other_inv@test.com", "password": "SecureP@ss1", "display_name": "Other",
        })
        other_login = await client.post("/api/v1/auth/login", json={"email": "other_inv@test.com", "password": "SecureP@ss1"})
        other_token = other_login.json()["access_token"]

        resp = await client.get(f"/api/v1/investigations/{inv_id}", headers={"Authorization": f"Bearer {other_token}"})
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestGraph:
    """Graph endpoint tests."""

    async def test_graph_returns_nodes_edges(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        e1 = await client.post(f"/api/v1/investigations/{inv_id}/entities", json={"type": "person", "label": "Alice"},
                                headers={"Authorization": f"Bearer {token}"})
        e2 = await client.post(f"/api/v1/investigations/{inv_id}/entities", json={"type": "device", "label": "Phone"},
                                headers={"Authorization": f"Bearer {token}"})
        await client.post(f"/api/v1/investigations/{inv_id}/relationships", json={
            "source_entity_id": e1.json()["id"], "target_entity_id": e2.json()["id"], "relationship_type": "owns",
        }, headers={"Authorization": f"Bearer {token}"})

        resp = await client.get(f"/api/v1/investigations/{inv_id}/graph", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) >= 2
        assert len(data["edges"]) >= 1

    async def test_graph_empty_no_entities(self, client: AsyncClient) -> None:
        token, ws_id, inv_id = await _setup(client)
        resp = await client.get(f"/api/v1/investigations/{inv_id}/graph", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["nodes"] == []
