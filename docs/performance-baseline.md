# 📊 EchoTrace AI — Performance Baseline

Recommended performance baselines for production deployment. These values are **recommended targets** derived from architecture analysis. Actual measurements require running the load test suite in a representative environment.

---

## API Latency

| Endpoint | Target P50 | Target P95 | Target P99 |
|----------|-----------|-----------|-----------|
| Health Check | < 10ms | < 30ms | < 50ms |
| Auth Login | < 200ms | < 500ms | < 1000ms |
| List Evidence (paginated) | < 50ms | < 150ms | < 300ms |
| Get Evidence by ID | < 30ms | < 80ms | < 150ms |
| Create Investigation | < 100ms | < 300ms | < 500ms |
| List Investigations | < 80ms | < 200ms | < 400ms |
| Dashboard Metrics | < 200ms | < 500ms | < 1000ms |
| AI Analysis Query | < 3000ms | < 8000ms | < 15000ms |
| Report Generation | < 2000ms | < 5000ms | < 10000ms |
| Graph Query (Neo4j) | < 100ms | < 300ms | < 500ms |

## Throughput

| Service | Single Instance | Horizontal (per replica) |
|---------|----------------|--------------------------|
| Backend (FastAPI) | 500 req/s | +300 req/s per replica |
| Frontend (Next.js) | 200 req/s | +150 req/s per replica |
| PostgreSQL | 1000 tps | Read replicas/+500 tps |

## Resource Usage (Steady State)

| Service | CPU | Memory | Disk |
|---------|-----|--------|------|
| Backend | 0.1–0.3 cores | 128–256 MB | Minimal |
| Frontend | 0.05–0.15 cores | 128–256 MB | Minimal |
| PostgreSQL | 0.2–0.5 cores | 256–512 MB | 100 MB + data |
| Neo4j | 0.3–0.8 cores | 512 MB–1 GB | 200 MB + data |

## Startup Time

| Service | Cold Start | Warm Start |
|---------|-----------|------------|
| Backend | 2–5s | < 1s |
| Frontend | 5–15s | < 2s |
| PostgreSQL | 5–10s | < 3s |
| Neo4j | 15–30s | < 10s |

## Error Budget

| SLO | Target | Monthly Budget |
|-----|--------|---------------|
| API Availability | 99.9% | 43m 12s downtime |
| API Latency P95 < 1s | 99.5% | 216m above threshold |

---

## Measurement Methodology

### Running the Load Test Suite

```bash
# Smoke test (quick validation)
k6 run -e BASE_URL=http://localhost:8000/api/v1 benchmarks/k6/smoke.js

# Sustained load test
k6 run --vus 20 --duration 10m benchmarks/k6/load.js

# Stress test (find breaking point)
k6 run --vus 200 --duration 15m benchmarks/k6/stress.js

# Locust (UI-based)
locust -f benchmarks/locust/locustfile.py --host=http://localhost:8000
```

### Capturing Results

```bash
# k6 JSON output
k6 run --summary-export=results.json benchmarks/k6/load.js

# Prometheus metrics
curl http://localhost:8000/api/v1/metrics/prometheus

# Application metrics snapshot
curl http://localhost:8000/api/v1/metrics
```

### Interpreting Results

| Metric | Target | Action if Exceeded |
|--------|--------|-------------------|
| P95 latency > 2s | Review database queries | Add indexes, optimize |
| Error rate > 5% | Check infrastructure | Scale up, check resources |
| CPU > 70% | Add replicas | Scale horizontally |
| Memory > 80% | Increase memory limit | Add replicas |

---

## References

- [Load Testing Guide](benchmarking.md)
- [Scaling Guide](scaling.md)
- [Monitoring Guide](monitoring.md)
- [k6 Scripts](../benchmarks/k6/)
- [Locust Scripts](../benchmarks/locust/)
