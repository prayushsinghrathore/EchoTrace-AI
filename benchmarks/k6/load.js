// ═══════════════════════════════════════════════════════════════════════════════
// EchoTrace AI — k6 Load Test (sustained)
// ═══════════════════════════════════════════════════════════════════════════════
// Run against staging/pre-prod to validate throughput targets.
//
// Usage:
//   k6 run --vus 20 --duration 10m benchmarks/k6/load.js
// ═══════════════════════════════════════════════════════════════════════════════

import { check, group, sleep } from "k6";
import http from "k6/http";
import { Rate, Trend } from "k6/metrics";

const errorRate = new Rate("errors");
const allDuration = new Trend("all_request_duration");

export const options = {
  stages: [
    { duration: "2m", target: 5 },   // Ramp-up
    { duration: "5m", target: 20 },  // Steady
    { duration: "1m", target: 0 },   // Ramp-down
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000", "p(99)<5000"],
    http_req_failed: ["rate<0.02"],
    errors: ["rate<0.02"],
  },
};

const BASE = __ENV.BASE_URL || "http://localhost:8000/api/v1";
let authToken: string | null = null;

// Simulate a real-user browsing session
export default function () {
  // Login every 50th request to refresh (simulating session expiry)
  if (!authToken || Math.random() < 0.02) {
    const email = __ENV.USER_EMAIL || "loadtest@echotrace.ai";
    const pwd = __ENV.USER_PASSWORD || "loadtest-password";
    const payload = JSON.stringify({ email, password: pwd });
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

  const headers = {
    Authorization: `Bearer ${authToken}`,
    "Content-Type": "application/json",
  };

  // Mix of read and write operations
  const r = Math.random();

  let url: string;
  if (r < 0.3) {
    // Health & dashboard (read-heavy, no auth)
    url = `${BASE}/health`;
    delete headers.Authorization;
    const res = http.get(url);
    allDuration.add(Date.now());
    check(res, { "health ok": (r2) => r2.status === 200 });
  } else if (r < 0.55) {
    // List evidence
    url = `${BASE}/evidence`;
    const res = http.get(url, { headers });
    allDuration.add(Date.now());
    errorRate.add(res.status >= 400 ? 1 : 0);
  } else if (r < 0.75) {
    // List investigations
    url = `${BASE}/investigations`;
    const res = http.get(url, { headers });
    allDuration.add(Date.now());
    errorRate.add(res.status >= 400 ? 1 : 0);
  } else if (r < 0.9) {
    // Get dashboard
    url = `${BASE}/dashboard`;
    const res = http.get(url, { headers });
    allDuration.add(Date.now());
    errorRate.add(res.status >= 400 ? 1 : 0);
  } else {
    // Create investigation (write)
    url = `${BASE}/investigations`;
    const body = JSON.stringify({ title: `load-test-${Date.now()}` });
    const res = http.post(url, body, { headers });
    allDuration.add(Date.now());
    errorRate.add(res.status >= 400 ? 1 : 0);
  }

  sleep(Math.random() * 2 + 0.5);  // Think time: 0.5–2.5s
}
