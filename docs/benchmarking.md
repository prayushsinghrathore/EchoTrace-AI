# 🧪 EchoTrace AI — Load Testing & Benchmarking Guide

Guide to running load tests, interpreting results, and establishing performance baselines.

---

## Tools

### k6 (Recommended)

[k6](https://k6.io) is the primary load testing tool. Test scripts are in [`benchmarks/k6/`](../benchmarks/k6/).

### Locust

[Locust](https://locust.io) is available as an alternative for Python-native tests. Scripts in [`benchmarks/locust/`](../benchmarks/locust/).

---

## Quick Start

### k6

```bash
# Install k6
brew install k6          # macOS
apt install k6            # Debian/Ubuntu
# Or download from https://k6.io/docs/get-started/installation/

# Smoke test (1 VU, 30s)
k6 run benchmarks/k6/smoke.js

# Point at a specific deployment
k6 run -e BASE_URL=https://staging.echotrace.ai/api/v1 benchmarks/k6/smoke.js

# Sustained load (20 VUs, 10m)
k6 run --vus 20 --duration 10m benchmarks/k6/load.js

# Stress test (ramp to 200 VUs)
k6 run benchmarks/k6/stress.js

# Export results
k6 run --summary-export=results.json benchmarks/k6/load.js
```

### Locust

```bash
# Install
pip install locust

# Web UI mode
locust -f benchmarks/locust/locustfile.py --host=http://localhost:8000

# Headless
locust -f benchmarks/locust/locustfile.py \
  --headless -u 20 -r 2 --run-time 10m \
  --host=http://localhost:8000

# CSV output
locust -f benchmarks/locust/locustfile.py \
  --headless -u 20 -r 2 --run-time 10m \
  --csv=locust-results --host=http://localhost:8000
```

---

## Available Test Scenarios

### Smoke Test (`k6/smoke.js`)

| Parameter | Value |
|-----------|-------|
| Duration | 30s |
| VUs | 1–2 |
| Goal | Verify pipeline, auth, and basic endpoints |
| Thresholds | P95 < 2s, Error rate < 5% |

### Load Test (`k6/load.js`)

| Parameter | Value |
|-----------|-------|
| Stages | Ramp 2min → Steady 5min → Ramp-down 1min |
| Peak VUs | 20 |
| Workload | 70% read / 30% write |
| Think time | 0.5–2.5s |
| Thresholds | P95 < 2s, P99 < 5s, Error rate < 2% |

### Stress Test (`k6/stress.js`)

| Parameter | Value |
|-----------|-------|
| Stages | Ramp from 10 → 400 VUs over 12min |
| Goal | Find the system's breaking point |
| Thresholds | P95 < 10s, Error rate < 10% at peak |

### Soak Test (`k6/stress.js` — `soakOptions`)

| Parameter | Value |
|-----------|-------|
| Duration | 2h |
| Peak VUs | 30 |
| Goal | Validate stability under sustained load |
| Thresholds | P95 < 3s, Error rate < 3% |

---

## Test Data Setup

### 1. Create test users

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"loadtest@echotrace.ai","password":"loadtest-password","name":"Load Test User"}'
```

### 2. Seed test data

```bash
# Create workspaces, investigations, evidence
curl -X POST http://localhost:8000/api/v1/workspaces \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Load Test Workspace"}'
```

### 3. Verify connectivity

```bash
curl http://localhost:8000/api/v1/health
```

---

## Interpreting Results

### Key Metrics

| Metric | Description | Good | Needs Attention | Critical |
|--------|-------------|------|----------------|----------|
| `http_req_duration p(95)` | 95th percentile latency | < 500ms | 500-2000ms | > 2000ms |
| `http_req_failed` | Request failure rate | < 1% | 1-5% | > 5% |
| `http_reqs` | Throughput (req/s) | > 100/s | 50-100/s | < 50/s |
| `vus` | Active virtual users | Matches target | — | Drops below target |
| `errors` | Custom error metric | < 1% | 1-5% | > 5% |

### What to Look For

1. **Latency spikes** — Check for database query degradation, lock contention
2. **Error rate increase** — Look for 5xx responses, connection pool exhaustion
3. **Throughput plateau** — Identifies resource bottleneck (CPU, memory, DB, connections)
4. **Memory growth** — During soak tests, identify memory leaks
5. **Garbage collection** — Excessive GC pauses indicate memory pressure

### Post-Test Analysis

```bash
# Check application metrics
curl http://localhost:8000/api/v1/metrics

# Check Prometheus rules
curl http://localhost:9090/api/v1/rules

# Check database connections
SELECT count(*) FROM pg_stat_activity;
SELECT pid, now() - query_start AS duration, query, state
FROM pg_stat_activity
WHERE state = 'active' ORDER BY duration DESC LIMIT 10;
```

---

## Benchmarking Process

### Pre-Test Checklist

- [ ] Deployment is healthy (`/api/v1/health` returns 200)
- [ ] All services are at steady state
- [ ] Test data has been seeded
- [ ] Monitoring is active (Prometheus, Grafana)
- [ ] Baseline metrics have been recorded
- [ ] No other load on the system

### Test Execution

```bash
# 1. Record baseline
curl http://localhost:8000/api/v1/metrics > baseline.json

# 2. Run load test
k6 run --summary-export=results.json benchmarks/k6/load.js

# 3. Record post-test metrics
curl http://localhost:8000/api/v1/metrics > post-test.json

# 4. Compare
diff <(jq -S . baseline.json) <(jq -S . post-test.json)
```

### Test Report Template

```markdown
## Load Test Report
- **Date:** YYYY-MM-DD
- **Test:** [Smoke / Load / Stress / Soak]
- **Environment:** [Local / Staging / Production]
- **Target:** [URL]
- **Duration:** [time]
- **VUs:** [count]

### Results
| Metric | Value | Target | Pass? |
|--------|-------|--------|-------|
| P95 Latency | xxx ms | < 2000ms | ✅/❌ |
| Error Rate | x.x% | < 2% | ✅/❌ |
| Throughput | xx req/s | — | — |
| Peak Memory | xxx MB | < 512 MB | ✅/❌ |
| Peak CPU | xx% | < 70% | ✅/❌ |

### Observations

### Recommendations
```

---

## References

- [k6 Documentation](https://k6.io/docs/)
- [Locust Documentation](https://docs.locust.io/)
- [Performance Baselines](performance-baseline.md)
- [Scaling Guide](scaling.md)
- [SRE Guide](sre.md)
