# Runbook: Frontend Service Failure

## Severity
**Critical** — UI unavailable, all users affected.

## Symptoms
- `FrontendServiceUnavailable` alert firing
- Browser returns 502/503 when accessing the application
- `up == 0` for `echotrace-frontend` Prometheus target
- Next.js error page displayed

## Immediate Steps

### 1. Verify service status
```bash
docker compose ps frontend
kubectl get pods -n echotrace -l app=echotrace-frontend
```

### 2. Check logs
```bash
docker compose logs --tail=100 frontend
kubectl logs -n echotrace deployment/echotrace-frontend --tail=100
```

### 3. Verify frontend can reach backend
```bash
docker compose exec frontend wget --no-verbose --tries=1 --spider http://backend:8000/api/v1/health
```

## Root Cause Diagnosis

### Backend Unreachable
- Symptom: Frontend logs show `connect ECONNREFUSED` or 502 to backend
- Check: Backend health and network connectivity
- Fix: See [Backend Failure Runbook](backend-failure.md)

### Build Error
- Symptom: Frontend logs contain build errors
- Check: `docker compose logs frontend --tail=50 | grep -i error`
- Fix: Rebuild with corrected configuration

### Static Assets Missing
- Symptom: 404 errors on `.js`/`.css` files
- Check: `docker compose exec frontend ls -la /app/.next/static`
- Fix: Rebuild the frontend image

### Port Conflict
- Symptom: `EADDRINUSE` or `port already in use`
- Check: `lsof -i :3000`
- Fix: Stop conflicting process or change port

## Resolution Steps

### Restart the service
```bash
docker compose restart frontend
kubectl rollout restart deployment/echotrace-frontend -n echotrace
```

### Rebuild the frontend
```bash
docker compose build frontend
docker compose up -d frontend
```

### Rollback
```bash
# Kubernetes
kubectl rollout undo deployment/echotrace-frontend -n echotrace
```

## Verification
- [ ] Frontend returns 200: `curl http://localhost:3000`
- [ ] Static assets load correctly
- [ ] API calls succeed from browser dev tools
- [ ] Prometheus target is UP
- [ ] No JavaScript console errors

## Post-Incident
- [ ] Document root cause
- [ ] Review CI/CD pipeline for gaps
- [ ] Update monitoring alerts if needed
