# Runbook: Backend Service Failure

## Severity
**Critical** — API unavailable, all clients affected.

## Symptoms
- `BackendServiceDown` alert firing in Prometheus
- Health check endpoint returning 503 or connection refused
- Frontend showing 502 Bad Gateway errors
- Grafana dashboard showing `up == 0` for backend target

## Immediate Steps

### 1. Verify service status
```bash
docker compose ps backend
kubectl get pods -n echotrace -l app=echotrace-backend
```

### 2. Check logs
```bash
docker compose logs --tail=100 backend
kubectl logs -n echotrace deployment/echotrace-backend --tail=100
```

### 3. Check resource usage
```bash
docker stats --no-stream echotrace-backend
kubectl top pod -n echotrace -l app=echotrace-backend
```

## Root Cause Diagnosis

### OOM (Out of Memory)
- Symptom: Container exits with code 137
- Check: `docker inspect echotrace-backend | jq '.[0].State'`
- Fix: Increase memory limit in `docker-compose.yml` or `k8s/backend.yaml`

### Database Connection Failure
- Symptom: Logs contain `connection refused` or `could not connect to server`
- Check: `docker compose logs postgres --tail=20`
- Fix: Restart PostgreSQL, verify credentials

### Port Conflict
- Symptom: Logs show `Address already in use`
- Check: `lsof -i :8000`
- Fix: Kill conflicting process or change port

### Application Crash
- Symptom: Logs contain `Traceback` or `Unhandled error`
- Check: Full log output for stack trace
- Fix: Depends on error — version mismatch, configuration error, etc.

## Resolution Steps

### Restart the service
```bash
docker compose restart backend
kubectl rollout restart deployment/echotrace-backend -n echotrace
```

### Rollback to previous version
```bash
# Docker Compose
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# Kubernetes
kubectl rollout undo deployment/echotrace-backend -n echotrace
```

### Scale up (if resource-constrained)
```bash
docker compose up -d --scale backend=3
kubectl scale deployment/echotrace-backend -n echotrace --replicas=3
```

## Verification
- [ ] Backend returns 200 on health check: `curl http://localhost:8000/api/v1/health`
- [ ] Prometheus target is UP: `http://localhost:9090/targets`
- [ ] Frontend can reach backend
- [ ] All test suites pass
- [ ] Logs show no new errors

## Post-Incident
- [ ] Document root cause in postmortem
- [ ] Update alert thresholds if needed
- [ ] Add monitoring if gap identified
- [ ] Update this runbook if steps were incorrect
