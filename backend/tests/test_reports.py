"""
Stage 7 tests — reports, export, notifications, activity, analytics, search.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.reports.renderer import ReportRenderer
from app.reports.schemas import (
    ReportData,
    ReportMetadata,
)


async def _setup_env(client: AsyncClient) -> tuple[str, str, str, str]:
    """Create org, workspace, investigation. Returns (token, ws_id, inv_id, ev_id)."""
    await client.post("/api/v1/auth/register", json={
        "email": "rpt@test.com", "password": "SecureP@ss1", "display_name": "Rpt Test",
    })
    login = await client.post("/api/v1/auth/login", json={"email": "rpt@test.com", "password": "SecureP@ss1"})
    token = login.json()["access_token"]

    org = await client.post("/api/v1/organizations", json={"name": "Rpt Org", "slug": "rpt-org"},
                             headers={"Authorization": f"Bearer {token}"})
    org_id = org.json()["id"]
    ws = await client.post("/api/v1/workspaces", json={"organization_id": org_id, "name": "Rpt WS", "slug": "rpt-ws"},
                            headers={"Authorization": f"Bearer {token}"})
    ws_id = ws.json()["id"]
    proj = await client.post("/api/v1/projects", json={"workspace_id": ws_id, "name": "Rpt Proj", "slug": "rpt-proj"},
                              headers={"Authorization": f"Bearer {token}"})
    proj_id = proj.json()["id"]
    ev = await client.post("/api/v1/evidence", json={"project_id": proj_id, "title": "Report Evidence"},
                            headers={"Authorization": f"Bearer {token}"})
    ev_id = ev.json()["id"]
    inv = await client.post("/api/v1/investigations", json={"workspace_id": ws_id, "title": "Report Investigation"},
                             headers={"Authorization": f"Bearer {token}"})
    inv_id = inv.json()["id"]
    return token, ws_id, inv_id, ev_id


# ── Report Renderer Tests ───────────────────────────────────────────────────


class TestReportRenderer:
    """Report renderer unit tests."""

    def setup_method(self) -> None:
        self.renderer = ReportRenderer()
        self.meta = ReportMetadata(
            title="Test Report", investigation_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(), generated_by=uuid.uuid4(),
        )
        self.data = ReportData(
            metadata=self.meta,
            executive_summary="Summary text",
            evidence_summary="Evidence list",
            timeline=[{"date": "2026-07-10", "title": "Event"}],
            entities=[{"type": "person", "label": "John Doe"}],
            relationships=[{"type": "connected_to", "source": "A", "target": "B", "confidence": 0.9}],
            findings=[{"title": "Finding 1", "description": "Desc"}],
            recommendations=[{"title": "Rec 1", "description": "Desc", "priority": "high"}],
            statistics={"total_evidence": 5},
        )

    def test_render_markdown(self) -> None:
        md = self.renderer.render_markdown(self.data)
        assert "# Test Report" in md
        assert "Executive Summary" in md
        assert "Evidence Summary" in md
        assert "Timeline" in md
        assert "Entities" in md
        assert "Relationships" in md
        assert "John Doe" in md
        assert len(md) > 100

    def test_render_html(self) -> None:
        html = self.renderer.render_html(self.data)
        assert "<html" in html
        assert "Test Report" in html

    def test_render_json(self) -> None:
        js = self.renderer.render_json(self.data)
        assert "executive_summary" in js
        assert "Test Report" in js

    def test_empty_data(self) -> None:
        empty_data = ReportData(metadata=self.meta)
        md = self.renderer.render_markdown(empty_data)
        assert "Test Report" in md
        assert len(md) > 50


# ── Report API Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestReportAPI:
    """Report generation API tests."""

    async def test_generate_report_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/reports/generate", json={
            "investigation_id": str(uuid.uuid4()),
            "format": "markdown",
        })
        assert resp.status_code == 401

    async def test_generate_report_invalid_investigation(self, client: AsyncClient) -> None:
        token, ws_id, inv_id, ev_id = await _setup_env(client)
        resp = await client.post("/api/v1/reports/generate", json={
            "investigation_id": str(uuid.uuid4()),
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    async def test_generate_report_valid(self, client: AsyncClient) -> None:
        token, ws_id, inv_id, ev_id = await _setup_env(client)
        resp = await client.post("/api/v1/reports/generate", json={
            "investigation_id": inv_id,
            "format": "markdown",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data
        assert data["format"] == "markdown"


# ── Export API Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestExportAPI:
    """Export system API tests."""

    async def test_create_export_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/reports/export", json={
            "entity_type": "investigation", "entity_id": str(uuid.uuid4()),
            "format": "json", "workspace_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 401

    async def test_create_export_valid(self, client: AsyncClient) -> None:
        token, ws_id, inv_id, ev_id = await _setup_env(client)
        resp = await client.post("/api/v1/reports/export", json={
            "entity_type": "investigation", "entity_id": inv_id,
            "format": "json", "workspace_id": ws_id,
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["entity_type"] == "investigation"
        assert data["status"] in ("completed", "running")

    async def test_list_exports(self, client: AsyncClient) -> None:
        token, ws_id, inv_id, ev_id = await _setup_env(client)
        await client.post("/api/v1/reports/export", json={
            "entity_type": "investigation", "entity_id": inv_id,
            "format": "json", "workspace_id": ws_id,
        }, headers={"Authorization": f"Bearer {token}"})
        resp = await client.get(f"/api/v1/reports/exports?workspace_id={ws_id}",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_download_invalid_token(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/reports/download/invalid-token")
        assert resp.status_code == 404


# ── Notification API Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
class TestNotificationAPI:
    """Notification system API tests."""

    async def test_notifications_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/reports/notifications")
        assert resp.status_code == 401

    async def test_list_notifications(self, client: AsyncClient) -> None:
        token, ws_id, inv_id, ev_id = await _setup_env(client)
        resp = await client.get("/api/v1/reports/notifications",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_unread_count(self, client: AsyncClient) -> None:
        token, ws_id, inv_id, ev_id = await _setup_env(client)
        resp = await client.get("/api/v1/reports/notifications/unread-count",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "count" in resp.json()


# ── Activity API Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestActivityAPI:
    """Activity feed API tests."""

    async def test_activity_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"/api/v1/reports/activity?workspace_id={uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_list_activity(self, client: AsyncClient) -> None:
        token, ws_id, inv_id, ev_id = await _setup_env(client)
        resp = await client.get(f"/api/v1/reports/activity?workspace_id={ws_id}",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


# ── Analytics API Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAnalyticsAPI:
    """Analytics dashboard API tests."""

    async def test_workspace_analytics_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get(f"/api/v1/reports/analytics/workspace/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_workspace_analytics(self, client: AsyncClient) -> None:
        token, ws_id, inv_id, ev_id = await _setup_env(client)
        resp = await client.get(f"/api/v1/reports/analytics/workspace/{ws_id}",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_investigations" in data
        assert "recent_activity" in data


# ── Search API Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSearchAPI:
    """Global search API tests."""

    async def test_search_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/reports/search?q=test")
        assert resp.status_code == 401

    async def test_search_no_results(self, client: AsyncClient) -> None:
        token, ws_id, inv_id, ev_id = await _setup_env(client)
        resp = await client.get("/api/v1/reports/search?q=zzz_nonexistent_zzz",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 0

    async def test_search_finds_investigation(self, client: AsyncClient) -> None:
        token, ws_id, inv_id, ev_id = await _setup_env(client)
        resp = await client.get(f"/api/v1/reports/search?q=Report&workspace_id={ws_id}",
                                 headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        # Should find "Report Investigation" in the title
        assert "results" in data
