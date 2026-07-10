# Runbook: High Memory Usage

## Severity
**Warning** → **Critical** if approaching memory limit.

## Symptoms
- `HighMemoryUsage` alert (>85% for 10m)
- OOM kills (`exit code 137`)
- Services restarting unexpectedly
- Slow response times due to swapping

## Immediate Steps

### 1. Identify memory consumers
```bash
# Docker
docker stats --no-stream
# Host
top -o %MEM
# Kubernetes
kubectl top pods -n echotrace
```

### 2. Check for OOM kills
```bash
# Docker
docker inspect <container> | jq '.[0].State'
# System
dmesg | grep -i "killed process"
```

### 3. Review memory trends
- Check Grafana infrastructure dashboard for memory usage over time
- Look for linear growth (memory leak) vs step changes (configuration change)

## Root Cause Diagnosis

### Memory Leak
- Symptom: Memory usage increases linearly over time, never drops
- Check: Grafana memory dashboard over 24h/7d
- Fix: Restart service, investigate the leak in development

### Increased Load
- Symptom: Memory correlates with request rate
- Check: `rate(echotrace_requests_total[5m])` vs memory usage
- Fix: Scale horizontally

### Configuration Issue
- Symptom: Step increase after deployment
- Check: Recent config changes (pool sizes, cache sizes, etc.)
- Fix: Tune memory settings

### Database Buffers Too Large
- Symptom: PostgreSQL/Neo4j using most memory
- Check: `shared_buffers`, `effective_cache_size`, `heap_max_size`
- Fix: Reduce buffer sizes proportionally

## Resolution Steps

### Increase memory limit
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G
```

### Restart service to reclaim memory
```bash
docker compose restart <service>
kubectl rollout restart deployment/<name> -n echotrace
```

### Tune memory settings
- Reduce SQLAlchemy pool size: `DB_POOL_SIZE=10`
- Reduce AI cache TTL: `AI_CACHE_TTL_SECONDS=1800`
- Reduce PostgreSQL `shared_buffers`

## Verification
- [ ] Memory usage below 70%
- [ ] No OOM kills in logs
- [ ] Service stable without restarts for 1h
- [ ] No swap usage
- [ ] All containers healthy

## Post-Incident
- [ ] Profile memory usage to identify leaks
- [ ] Add memory limit alerts if missing
- [ ] Review garbage collection / memory management settings
- [ ] Add memory profiling to CI
