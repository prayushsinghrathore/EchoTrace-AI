# ═══════════════════════════════════════════════════════════════════════════════
# EchoTrace AI — Locust Load Test Suite
# ═══════════════════════════════════════════════════════════════════════════════
# Run against a local or staging deployment.
#
# Usage:
#   locust -f benchmarks/locust/locustfile.py --host=http://localhost:8000
#   locust -f benchmarks/locust/locustfile.py --headless -u 20 -r 2 --run-time 5m
# ═══════════════════════════════════════════════════════════════════════════════

import random
import time

from locust import HttpUser, between, task


class EchoTraceApiUser(HttpUser):
    """
    Simulates an authenticated API user performing typical workflows.

    Reuses the same auth token across requests to avoid login overhead
    in load tests. A separate auth-only task handles token refresh.
    """

    wait_time = between(0.5, 3.0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token: str | None = None
        self.workspace_id: str | None = None

    def on_start(self):
        """Authenticate once at user start."""
        self._login()

    def _login(self):
        """Authenticate and store the access token."""
        payload = {
            "email": self.environment.parsed_options.email or "loadtest@echotrace.ai",
            "password": self.environment.parsed_options.password or "loadtest-password",
        }
        headers = {"Content-Type": "application/json"}
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            headers=headers,
            catch_response=True,
            name="auth_login",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data.get("access_token")
            else:
                resp.failure(f"Login failed: {resp.status_code}")

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    # ── Read-heavy tasks (70% of traffic) ────────────────────────────────

    @task(20)
    def health_check(self):
        """Liveness check — no auth required."""
        with self.client.get(
            "/api/v1/health", name="health_check", catch_response=True
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Health failed: {resp.status_code}")

    @task(15)
    def list_evidence(self):
        """Paginated evidence listing."""
        if not self.access_token:
            return
        with self.client.get(
            "/api/v1/evidence",
            headers=self._auth_headers(),
            name="list_evidence",
            catch_response=True,
        ) as resp:
            if resp.status_code == 401:
                self._login()

    @task(12)
    def list_investigations(self):
        """Paginated investigation listing."""
        if not self.access_token:
            return
        with self.client.get(
            "/api/v1/investigations",
            headers=self._auth_headers(),
            name="list_investigations",
            catch_response=True,
        ) as resp:
            if resp.status_code == 401:
                self._login()

    @task(10)
    def get_dashboard(self):
        """Dashboard metrics."""
        if not self.access_token:
            return
        self.client.get(
            "/api/v1/dashboard",
            headers=self._auth_headers(),
            name="dashboard",
        )

    @task(8)
    def list_workspaces(self):
        """Workspace listing."""
        if not self.access_token:
            return
        with self.client.get(
            "/api/v1/workspaces",
            headers=self._auth_headers(),
            name="list_workspaces",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    self.workspace_id = data[0].get("id")

    # ── Write tasks (30% of traffic) ─────────────────────────────────────

    @task(6)
    def create_investigation(self):
        """Create a new investigation."""
        if not self.access_token:
            return
        payload = {
            "title": f"locust-load-{int(time.time())}",
            "description": "Generated during load test",
        }
        with self.client.post(
            "/api/v1/investigations",
            json=payload,
            headers=self._auth_headers(),
            name="create_investigation",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                data = resp.json()
                self.workspace_id = data.get("workspace_id")
            elif resp.status_code == 401:
                self._login()

    @task(4)
    def search_evidence(self):
        """Search evidence by keyword."""
        if not self.access_token:
            return
        query = random.choice(["incident", "report", "log", "screenshot"])
        self.client.get(
            f"/api/v1/evidence?search={query}",
            headers=self._auth_headers(),
            name="search_evidence",
        )
