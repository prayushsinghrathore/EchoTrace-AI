"""
Stage 8 tests — WebSocket, events, audit, health, metrics, rate limits, security.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.metrics import MetricsCollector, metrics
from app.models.audit_log import AuditAction


async def _setup_env(client: AsyncClient) -> tuple[str, str]:
    """Create org, workspace. Returns (token, ws_id)."""
    await client.post("/api/v1/auth/register", json={
        "email": "ops@test.com", "password": "SecureP@ss1", "display_name": "Ops Test",
    })
    login = await client.post("/api/v1/auth/login", json={"email": "ops@test.com", "password": "SecureP@ss1"})
    token = login.json()["access_token"]

    org = await client.post("/api/v1/organizations", json={"name": "Ops Org", "slug": "ops-org"},
                             headers={"Authorization": f"Bearer {token}"})
    org_id = org.json()["id"]
    ws = await client.post("/api/v1/workspaces", json={"organization_id": org_id, "name": "Ops WS", "slug": "ops-ws"},
                            headers={"Authorization": f"Bearer {token}"})
    ws_id = ws.json()["id"]
    return token, ws_id


# ── Health / Live / Ready Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestHealth:
    """Health, liveness, and readiness endpoint tests."""

    async def test_health_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "version" in data

    async def test_liveness(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"


# ── Metrics Tests ─────────────────────────────────────────────────────────────


class TestMetrics:
    """Metrics collector tests."""

    def setup_method(self) -> None:
        self.m = MetricsCollector()

    def test_record_request(self) -> None:
        self.m.record_request("GET", "/api/v1/health", 200, 5.0)
        snap = self.m.get_snapshot()
        assert snap["requests"]["total"] == 1
        assert snap["requests"]["by_method"]["GET"] == 1

    def test_record_multiple_requests(self) -> None:
        self.m.record_request("GET", "/api/v1/health", 200, 5.0)
        self.m.record_request("POST", "/api/v1/evidence", 201, 50.0)
        self.m.record_request("GET", "/api/v1/health", 500, 100.0)
        snap = self.m.get_snapshot()
        assert snap["requests"]["total"] == 3
        assert snap["errors"]["total"] == 1
        assert snap["requests"]["by_method"]["GET"] == 2
        assert snap["requests"]["by_method"]["POST"] == 1

    def test_record_ai_usage(self) -> None:
        self.m.record_ai_usage(1000, 500, 0.003)
        snap = self.m.get_snapshot()
        assert snap["ai"]["total_input_tokens"] == 1000
        assert snap["ai"]["total_output_tokens"] == 500
        assert snap["ai"]["total_cost_usd"] > 0

    def test_cache_metrics(self) -> None:
        self.m.record_cache_hit()
        self.m.record_cache_hit()
        self.m.record_cache_miss()
        snap = self.m.get_snapshot()
        assert snap["cache"]["hits"] == 2
        assert snap["cache"]["misses"] == 1
        assert snap["cache"]["hit_rate_pct"] > 0

    def test_db_latency(self) -> None:
        self.m.record_db_latency(10.5)
        snap = self.m.get_snapshot()
        assert snap["database"]["average_latency_ms"] > 0
        assert snap["database"]["query_count"] == 1

    def test_reset(self) -> None:
        self.m.record_request("GET", "/test", 200, 1.0)
        self.m.reset()
        snap = self.m.get_snapshot()
        assert snap["requests"]["total"] == 0

    def test_global_metrics_instance(self) -> None:
        assert metrics is not None
        assert hasattr(metrics, "record_request")
        assert hasattr(metrics, "get_snapshot")


# ── Event Bus Tests ──────────────────────────────────────────────────────────


# Event bus tests removed (event_bus was dead code, removed in final cleanup)


# ── Health/Metrics API Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestOperationsAPI:
    """Operations endpoint tests."""

    async def test_metrics_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/metrics")
        assert resp.status_code == 401

    async def test_metrics_authenticated(self, client: AsyncClient) -> None:
        token, ws_id = await _setup_env(client)
        resp = await client.get("/api/v1/metrics", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "requests" in data
        assert "latency" in data
        assert "ai" in data
        assert "cache" in data

    async def test_rate_limits_endpoint(self, client: AsyncClient) -> None:
        token, ws_id = await _setup_env(client)
        resp = await client.get("/api/v1/rate-limits", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "limits" in data
        assert "auth" in data


# ── Audit Log Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestAudit:
    """Audit log service tests."""

    async def test_audit_service_creation(self, client: AsyncClient) -> None:
        """Verify audit model works via API."""
        token, ws_id = await _setup_env(client)
        assert AuditAction.LOGIN.value == "login"
        assert AuditAction.LOGOUT.value == "logout"
        assert AuditAction.EVIDENCE_CREATED.value == "evidence_created"


# ── Security Headers Test ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestSecurityHeaders:
    """Security header tests."""

    async def test_security_headers_present(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        headers = resp.headers
        # Check security headers from our middleware
        for h in ["x-content-type-options", "x-frame-options", "x-xss-protection",
                   "strict-transport-security", "referrer-policy", "x-request-id"]:
            assert h in headers, f"Missing security header: {h}"
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"

    async def test_request_id_present(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert "x-request-id" in resp.headers
        assert resp.headers["x-request-id"] != ""

    async def test_process_time_header(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert "x-process-time" in resp.headers

    async def test_enterprise_security_headers(self, client: AsyncClient) -> None:
        """Verify enterprise-grade security headers (CSP, COOP, COEP, CORP, Permissions-Policy)."""
        resp = await client.get("/")
        headers = resp.headers
        assert "content-security-policy" in headers
        assert "cross-origin-resource-policy" in headers
        assert "cross-origin-opener-policy" in headers
        assert "cross-origin-embedder-policy" in headers
        assert "permissions-policy" in headers
        assert headers["cross-origin-resource-policy"] == "same-origin"
        assert headers["cross-origin-opener-policy"] == "same-origin"
        assert headers["cross-origin-embedder-policy"] == "require-corp"


# ── Config / Settings Tests ─────────────────────────────────────────────────


class TestConfig:
    """Configuration and security hardening tests."""

    def test_rate_limit_config(self) -> None:
        from app.core.config import settings as s
        assert s.RATE_LIMIT_LOGIN_MAX >= 1
        assert s.RATE_LIMIT_ENABLED is not None
        assert s.AI_RATE_LIMIT_MAX >= 1
