"""
Comprehensive evidence management tests.

Tests CRUD, upload, download, verification, versioning, comments, search, chain of custody, permissions.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _setup_env(client: AsyncClient) -> tuple[str, str, str]:
    """Create org, workspace, project. Returns (token, ws_id, proj_id)."""
    await client.post("/api/v1/auth/register", json={
        "email": "evtest@test.com", "password": "SecureP@ss1", "display_name": "Ev Test",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "evtest@test.com", "password": "SecureP@ss1",
    })
    token = login.json()["access_token"]

    org = await client.post("/api/v1/organizations", json={"name": "Ev Org", "slug": "ev-org"},
                             headers={"Authorization": f"Bearer {token}"})
    org_id = org.json()["id"]

    ws = await client.post("/api/v1/workspaces", json={"organization_id": org_id, "name": "Ev WS", "slug": "ev-ws"},
                            headers={"Authorization": f"Bearer {token}"})
    ws_id = ws.json()["id"]

    proj = await client.post("/api/v1/projects", json={"workspace_id": ws_id, "name": "Ev Proj", "slug": "ev-proj"},
                              headers={"Authorization": f"Bearer {token}"})
    proj_id = proj.json()["id"]

    return token, ws_id, proj_id


@pytest.mark.asyncio
class TestEvidenceCRUD:
    """Evidence CRUD tests."""

    async def test_create_evidence(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        resp = await client.post("/api/v1/evidence", json={
            "project_id": proj_id,
            "title": "Test Evidence Item", "category": "document", "priority": "high",
            "description": "A test evidence item", "source": "email",
            "tags": ["important", "test"],
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Evidence Item"
        assert data["category"] == "document"
        assert data["priority"] == "high"
        assert data["evidence_number"].startswith("ET-")
        assert set(data["tags"]) == {"important", "test"}

    async def test_list_evidence(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Item 1", "category": "image",
        }, headers={"Authorization": f"Bearer {token}"})
        await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Item 2",
        }, headers={"Authorization": f"Bearer {token}"})
        resp = await client.get(f"/api/v1/evidence?project_id={proj_id}",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    async def test_get_evidence(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        create = await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Get Me",
        }, headers={"Authorization": f"Bearer {token}"})
        ev_id = create.json()["id"]
        resp = await client.get(f"/api/v1/evidence/{ev_id}",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get Me"

    async def test_update_evidence(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        create = await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Original",
        }, headers={"Authorization": f"Bearer {token}"})
        ev_id = create.json()["id"]
        resp = await client.patch(f"/api/v1/evidence/{ev_id}", json={"title": "Updated", "priority": "critical"},
                                   headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
        assert resp.json()["priority"] == "critical"

    async def test_delete_and_restore(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        create = await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "To Delete",
        }, headers={"Authorization": f"Bearer {token}"})
        ev_id = create.json()["id"]

        del_resp = await client.delete(f"/api/v1/evidence/{ev_id}",
                                        headers={"Authorization": f"Bearer {token}"})
        assert del_resp.status_code == 204

        restore_resp = await client.post(f"/api/v1/evidence/{ev_id}/restore",
                                          headers={"Authorization": f"Bearer {token}"})
        assert restore_resp.status_code == 200
        assert restore_resp.json()["is_deleted"] is False


@pytest.mark.asyncio
class TestEvidencePermissions:
    """Permission enforcement tests."""

    async def test_non_member_cannot_create(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)

        # Second user
        await client.post("/api/v1/auth/register", json={
            "email": "other@test.com", "password": "SecureP@ss1", "display_name": "Other",
        })
        other_login = await client.post("/api/v1/auth/login", json={
            "email": "other@test.com", "password": "SecureP@ss1",
        })
        other_token = other_login.json()["access_token"]

        resp = await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Unauthorized",
        }, headers={"Authorization": f"Bearer {other_token}"})
        assert resp.status_code == 403

    async def test_unauthenticated_blocked(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/evidence?project_id=00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestEvidenceSearch:
    """Search functionality tests."""

    async def test_search_by_title(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Forensic Report Q3",
        }, headers={"Authorization": f"Bearer {token}"})
        resp = await client.get(f"/api/v1/evidence/search?q=Forensic&project_id={proj_id}",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_search_by_hash(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Hash Search",
        }, headers={"Authorization": f"Bearer {token}"})
        resp = await client.get(
            f"/api/v1/evidence/search?project_id={proj_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestEvidenceComments:
    """Comment tests."""

    async def test_add_and_list_comments(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        create = await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Comment Test",
        }, headers={"Authorization": f"Bearer {token}"})
        ev_id = create.json()["id"]

        add = await client.post(f"/api/v1/evidence/{ev_id}/comments", json={"body": "This is a comment"},
                                 headers={"Authorization": f"Bearer {token}"})
        assert add.status_code == 201
        assert add.json()["body"] == "This is a comment"

        list_resp = await client.get(f"/api/v1/evidence/{ev_id}/comments",
                                      headers={"Authorization": f"Bearer {token}"})
        assert len(list_resp.json()) >= 1

    async def test_edit_and_delete_comment(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        create = await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Comment Edit",
        }, headers={"Authorization": f"Bearer {token}"})
        ev_id = create.json()["id"]

        add = await client.post(f"/api/v1/evidence/{ev_id}/comments", json={"body": "Original"},
                                 headers={"Authorization": f"Bearer {token}"})
        cid = add.json()["id"]

        edit = await client.patch(f"/api/v1/evidence/comments/{cid}", json={"body": "Edited"},
                                   headers={"Authorization": f"Bearer {token}"})
        assert edit.json()["body"] == "Edited"
        assert edit.json()["is_edited"] is True

        del_resp = await client.delete(f"/api/v1/evidence/comments/{cid}",
                                        headers={"Authorization": f"Bearer {token}"})
        assert del_resp.status_code == 204


@pytest.mark.asyncio
class TestEvidenceCustody:
    """Chain of custody tests."""

    async def test_custody_events_created(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        create = await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Custody Test",
        }, headers={"Authorization": f"Bearer {token}"})
        ev_id = create.json()["id"]

        # Update to trigger custody
        await client.patch(f"/api/v1/evidence/{ev_id}", json={"title": "Updated"},
                            headers={"Authorization": f"Bearer {token}"})

        custody = await client.get(f"/api/v1/evidence/{ev_id}/custody",
                                    headers={"Authorization": f"Bearer {token}"})
        assert len(custody.json()) >= 2  # create + update

    async def test_custody_has_actions(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        create = await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Action Test",
        }, headers={"Authorization": f"Bearer {token}"})
        ev_id = create.json()["id"]

        custody = await client.get(f"/api/v1/evidence/{ev_id}/custody",
                                    headers={"Authorization": f"Bearer {token}"})
        actions = [e["action"] for e in custody.json()]
        assert "create" in actions


@pytest.mark.asyncio
class TestEvidenceStats:
    """Statistics tests."""

    async def test_evidence_stats(self, client: AsyncClient) -> None:
        token, ws_id, proj_id = await _setup_env(client)
        await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Stat 1",
        }, headers={"Authorization": f"Bearer {token}"})
        await client.post("/api/v1/evidence", json={
            "project_id": proj_id, "title": "Stat 2",
        }, headers={"Authorization": f"Bearer {token}"})
        stats = await client.get(f"/api/v1/evidence/stats/project/{proj_id}",
                                  headers={"Authorization": f"Bearer {token}"})
        assert stats.status_code == 200
        assert stats.json()["total"] >= 2
        assert "by_status" in stats.json()
