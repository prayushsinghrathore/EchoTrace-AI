// ═══════════════════════════════════════════════════════════════════════════════
// EchoTrace AI — k6 Stress & Soak Test
// ═══════════════════════════════════════════════════════════════════════════════
// Stress: find breaking point. Soak: 1h+ sustained.
// ═══════════════════════════════════════════════════════════════════════════════

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const errorRate = new Rate("errors");

// ── Stress Test: ramp up until failure ──────────────────────────────────────
export const stressOptions = {
  stages: [
    { duration: "2m", target: 10 },
    { duration: "2m", target: 25 },
    { duration: "2m", target: 50 },
    { duration: "2m", target: 100 },
    { duration: "2m", target: 200 },
    { duration: "2m", target: 400 },
    { duration: "2m", target: 0 },    // cool down
  ],
  thresholds: {
    http_req_failed: ["rate<0.10"],   // Allow some failure at peak
    http_req_duration: ["p(95)<10000"],
  },
};

// ── Soak Test: sustained load over 2h ───────────────────────────────────────
export const soakOptions = {
  stages: [
    { duration: "15m", target: 30 },  // Ramp
    { duration: "90m", target: 30 },  // Soak
    { duration: "15m", target: 0 },   // Cool down
  ],
  thresholds: {
    http_req_failed: ["rate<0.03"],
    http_req_duration: ["p(95)<3000", "p(99)<8000"],
  },
};

// Default is the stress test
export const options = stressOptions;

const BASE = __ENV.BASE_URL || "http://localhost:8000/api/v1";
let authToken: string | null = null;

export default function () {
  // Authenticate
  if (!authToken) {
    const payload = JSON.stringify({
      email: __ENV.USER_EMAIL || "stress@echotrace.ai",
      password: __ENV.USER_PASSWORD || "stress-password",
    });
    const headers = { "Content-Type": "application/json" };
    const res = http.post(`${BASE}/auth/login`, payload, { headers });
    if (res.status === 200) {
      authToken = (res.json() as Record<string, any>).access_token;
    }
  }

  if (!authToken) {
    sleep(1);
    return;
  }

  const headers = { Authorization: `Bearer ${authToken}` };

  // Mixed workload
  const paths = [
    "/evidence",
    "/investigations",
    "/dashboard",
    "/health",
    "/workspaces",
  ];
  const path = paths[Math.floor(Math.random() * paths.length)];
  const url = `${BASE}${path}`;
  const res = http.get(url, { headers });
  check(res, { [`${path} ok`]: (r) => r.status < 500 });
  errorRate.add(res.status >= 500 ? 1 : 0);

  sleep(Math.random() * 1 + 0.2); // 0.2–1.2s think time
}
