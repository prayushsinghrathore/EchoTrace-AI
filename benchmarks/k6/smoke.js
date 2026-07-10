// ═══════════════════════════════════════════════════════════════════════════════
// EchoTrace AI — k6 Load Test Suite
// ═══════════════════════════════════════════════════════════════════════════════
// Run against a local or staging deployment.
//
// Usage:
//   k6 run -e BASE_URL=http://localhost:8000/api/v1 benchmarks/k6/smoke.js
//   k6 run -e BASE_URL=http://localhost:8000/api/v1 -e USER_EMAIL=... -e USER_PASSWORD=... \
//     --vus 10 --duration 30s benchmarks/k6/load.js
//   k6 run --vus 50 --duration 5m benchmarks/k6/stress.js
// ═══════════════════════════════════════════════════════════════════════════════

import { check, fail, group, sleep } from "k6";
import http from "k6/http";
import { Rate, Trend } from "k6/metrics";

// ── Custom Metrics ──────────────────────────────────────────────────────────
const loginDuration = new Trend("login_duration");
const healthDuration = new Trend("health_duration");
const evidenceListDuration = new Trend("evidence_list_duration");
const investigationCreateDuration = new Trend("investigation_create_duration");
const errorRate = new Rate("errors");

// ── Default Options ─────────────────────────────────────────────────────────
export const options = {
  thresholds: {
    http_req_duration: ["p(95)<2000"],   // 95% of requests under 2s
    http_req_failed: ["rate<0.05"],       // <5% failure rate
    errors: ["rate<0.05"],
  },
  // Defaults — override via CLI flags
  vus: 1,
  duration: "30s",
};

const BASE = __ENV.BASE_URL || "http://localhost:8000/api/v1";

// ── Shared State ────────────────────────────────────────────────────────────
let authToken: string | null = null;
let workspaceId: string | null = null;

// ── Setup ───────────────────────────────────────────────────────────────────
export function setup() {
  // Smoke-test basic connectivity
  const health = http.get(`${BASE}/health`);
  check(health, { "health endpoint responds": (r) => r.status === 200 });
  return { baseUrl: BASE };
}

// ── Authentication ──────────────────────────────────────────────────────────
function login(): boolean {
  const email = __ENV.USER_EMAIL || "test@echotrace.ai";
  const password = __ENV.USER_PASSWORD || "test-password";

  const payload = JSON.stringify({ email, password });
  const headers = { "Content-Type": "application/json" };

  const start = Date.now();
  const res = http.post(`${BASE}/auth/login`, payload, { headers });
  loginDuration.add(Date.now() - start);

  if (res.status === 200) {
    const body = res.json() as Record<string, any>;
    authToken = body.access_token || null;
    return authToken !== null;
  }
  errorRate.add(1);
  return false;
}

function ensureAuthenticated(): boolean {
  if (authToken) return true;
  return login();
}

// ── Request Helper ──────────────────────────────────────────────────────────
function authedRequest(method: string, path: string, body?: string | null) {
  if (!ensureAuthenticated()) return null;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${authToken}`,
    "Content-Type": "application/json",
  };
  const url = `${BASE}${path}`;
  const res = method === "GET"
    ? http.get(url, { headers })
    : http.post(url, body || "", { headers });
  return res;
}

// ── Workload Functions ──────────────────────────────────────────────────────

export function healthCheck() {
  const start = Date.now();
  const res = http.get(`${BASE}/health`);
  healthDuration.add(Date.now() - start);
  check(res, { "health is 200": (r) => r.status === 200 });
}

export function listWorkspaces() {
  const res = authedRequest("GET", "/workspaces");
  if (!res) return;
  check(res, { "workspaces listed": (r) => r.status === 200 });
}

export function listEvidence() {
  const wsPath = workspaceId ? `?workspace_id=${workspaceId}` : "";
  const start = Date.now();
  const res = authedRequest("GET", `/evidence${wsPath}`);
  evidenceListDuration.add(Date.now() - start);
  if (res) {
    check(res, { "evidence listed": (r) => r.status === 200 });
  }
}

export function createInvestigation() {
  const payload = JSON.stringify({
    title: `k6-load-test-${Date.now()}`,
    description: "Generated during k6 load test",
  });
  const start = Date.now();
  const res = authedRequest("POST", "/investigations", payload);
  investigationCreateDuration.add(Date.now() - start);
  if (res && res.status === 201) {
    const body = res.json() as Record<string, any>;
    workspaceId = body.workspace_id || null;
    check(res, { "investigation created": (r) => r.status === 201 });
  }
}

export function getDashboard() {
  const res = authedRequest("GET", "/dashboard");
  if (res) {
    check(res, { "dashboard accessible": (r) => r.status === 200 });
  }
}

// ── Default Scenario (smoke test) ───────────────────────────────────────────
export default function () {
  group("health", () => healthCheck());

  if (!ensureAuthenticated()) {
    fail("authentication failed — aborting");
  }

  group("workspaces", () => listWorkspaces());

  group("investigations", () => {
    createInvestigation();
    sleep(1);
  });

  group("evidence", () => {
    listEvidence();
    sleep(1);
  });

  group("dashboard", () => getDashboard());

  sleep(2);
}
