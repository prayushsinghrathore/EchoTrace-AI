# Runbook: PostgreSQL Failure

## Severity
**Critical** — Primary data store unavailable, all write operations fail.

## Symptoms
- `PostgresHighConnections` or `PostgresSlowQueries` alert firing
- Backend logs show connection errors: `could not connect to server`
- Health check reports PostgreSQL as unhealthy
- Queries timing out or returning errors

## Immediate Steps

### 1. Verify PostgreSQL status
```bash
docker compose ps postgres
kubectl get pods -n echotrace -l app=postgres
```

### 2. Check PostgreSQL logs
```bash
docker compose logs --tail=100 postgres
kubectl logs -n echotrace statefulset/postgres --tail=100
```

### 3. Test direct connection
```bash
docker compose exec postgres psql -U echotrace -d echotrace -c "SELECT 1"
```

## Root Cause Diagnosis

### High Connection Count
- Symptom: Many idle connections
- Query:
  ```sql
  SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
  ```
- Fix: Increase `max_connections`, review connection pool settings, terminate idle connections

### Slow Queries / Lock Contention
- Symptom: High `pg_stat_activity_max_tx_duration`
- Query:
  ```sql
  SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
  FROM pg_stat_activity
  ORDER BY duration DESC LIMIT 10;
  ```
- Fix: Kill long-running queries, add missing indexes, optimize queries

### Low Cache Hit Ratio
- Symptom: `PostgresLowCacheHitRatio` alert
- Check: `pg_stat_database.blks_hit / (blks_hit + blks_read)`
- Fix: Increase `shared_buffers`, tune `effective_cache_size`

### Disk Full
- Symptom: `could not extend file` errors
- Check:
  ```sql
  SELECT pg_size_pretty(pg_database_size(datname)) FROM pg_database;
  ```
- Fix: Delete old data, increase disk size, add cleanup jobs

### Out of Memory
- Symptom: PostgreSQL process killed by OOM killer
- Check: `dmesg | grep -i oom`
- Fix: Reduce `shared_buffers`, increase container memory limit

## Resolution Steps

### Restart PostgreSQL
```bash
docker compose restart postgres
kubectl rollout restart statefulset/postgres -n echotrace
```

### Kill blocking queries
```sql
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '5 minutes';
```

### Scale up storage
```bash
# Increase PVC size in k8s/postgres.yaml
# Or add more disk space in Docker environment
```

### Restore from backup
See [Backup and Restore Runbook](backup-restore.md)

## Verification
- [ ] PostgreSQL accepts connections: `docker compose exec postgres psql -U echotrace -c "SELECT 1"`
- [ ] Backend health check passes: `curl http://localhost:8000/api/v1/health`
- [ ] Connection count is below 80% of max
- [ ] Cache hit ratio is above 95%
- [ ] No slow queries
- [ ] Monitoring dashboards show normal metrics

## Post-Incident
- [ ] Tune PostgreSQL configuration if needed
- [ ] Add missing indexes
- [ ] Review connection pool settings
- [ ] Schedule regular VACUUM ANALYZE
