# Runbook: High API Latency

## Severity
**Warning** — User experience degraded, SLO at risk.

## Symptoms
- `BackendHighLatency` alert (P95 > 2s for 5m)
- Users report slow page loads
- API responses exceeding timeout thresholds
- Increased error rates due to timeouts

## Immediate Steps

### 1. Confirm the latency scope
```bash
# Check backend latency metrics in Grafana
# Backend dashboard → Latency panel

# Check database latency
curl http://localhost:9090/api/v1/query?query=echotrace:backend:latency_p95_5m
```

### 2. Identify slow endpoints
Run a quick check:
```bash
# Check recent request durations from logs
docker compose logs backend --tail=500 | grep -o '"duration_ms":[0-9.]*' | sort -t: -k2 -rn | head -10
```

## Root Cause Diagnosis

### Database Bottleneck
- Symptom: DB latency panel shows high values
- Check: PostgreSQL/Neo4j dashboard for slow queries, locks, cache hit ratio
- Fix: Optimize queries, add indexes, increase cache

### Missing Indexes
- Symptom: Sequential scans increasing
- PostgreSQL:
  ```sql
  SELECT relname, seq_scan, seq_tup_read, idx_scan
  FROM pg_stat_user_tables
  WHERE seq_scan > 1000 ORDER BY seq_scan DESC;
  ```
- Fix: Add indexes to frequently queried columns

### Lock Contention
- Symptom: `pg_locks_waiting_count` elevated
- Query:
  ```sql
  SELECT blocked.pid AS blocked_pid, blocker.pid AS blocker_pid
  FROM pg_catalog.pg_locks blocked
  JOIN pg_catalog.pg_locks blocker ON ...
  ```
- Fix: Kill blocking sessions, optimize transaction scope

### Resource Starvation (CPU/Memory)
- Symptom: Latency correlated with CPU/memory
- Check: Infrastructure dashboard
- Fix: See [High CPU Runbook](high-cpu.md) or [High Memory Runbook](high-memory.md)

### Network Issues
- Symptom: Latency across all services
- Check: Network I/O panels in Grafana, DNS resolution
- Fix: Check network connectivity between services

## Resolution Steps

### Scale horizontally
```bash
kubectl scale deployment/echotrace-backend -n echotrace --replicas=5
```

### Clear cache
```bash
# If using Redis-based caching
redis-cli FLUSHDB
```

### Kill slow queries
```sql
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '30 seconds';
```

## Verification
- [ ] P95 latency below 1000ms
- [ ] P99 latency below 2000ms
- [ ] No slow query alerts
- [ ] Database cache hit ratio > 95%
- [ ] Error rate back to baseline

## Post-Incident
- [ ] Review and optimize the identified slow endpoints
- [ ] Add Database indexing if needed
- [ ] Implement caching for frequently accessed data
- [ ] Review API pagination and field selection
