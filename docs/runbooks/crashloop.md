# Runbook: Pod / Container CrashLoop

## Severity
**Critical** — Service unavailable.

## Symptoms
- `PodCrashLooping` alert firing
- Container restarting repeatedly
- `CrashLoopBackOff` status in Kubernetes
- Service intermittently available

## Immediate Steps

### 1. Check pod/container status and restart count
```bash
# Docker
docker ps -a | grep echotrace

# Kubernetes
kubectl get pods -n echotrace
kubectl describe pod -n echotrace <pod-name>
```

### 2. View logs from the crashed instance
```bash
# Docker (include stopped containers)
docker logs <container-id> --tail=100

# Kubernetes — previous instance logs
kubectl logs -n echotrace <pod-name> --previous --tail=100
```

### 3. Check events for the pod
```bash
kubectl describe pod -n echotrace <pod-name> | grep -A 10 Events:
```

## Root Cause Diagnosis

### Application Error on Startup
- Symptom: Logs show `Traceback` or `Error` before exit
- Fix: Fix the code/config, rebuild and redeploy

### Configuration Error
- Symptom: Logs show `ValueError`, `KeyError`, or misconfiguration
- Fix: Correct environment variables or config files

### Dependency Unavailable
- Symptom: Logs show `connection refused`, `could not connect`
- Fix: Start dependency services first, check for connectivity

### OOM Killed
- Symptom: Exit code 137, `OOMKilled` in events
- Fix: Increase memory limit, reduce memory usage

### Liveness Probe Failure
- Symptom: `Liveness probe failed` in events
- Fix: Check health endpoint, adjust probe parameters

### Readiness Probe Failure
- Symptom: Pod running but not ready
- Fix: Check if startup takes longer than probe allows

## Resolution Steps

### Immediate fix — rollback
```bash
# Kubernetes
kubectl rollout undo deployment/<name> -n echotrace
```

### Increase startup delay
```yaml
# Adjust liveness/readiness probes
livenessProbe:
  initialDelaySeconds: 60  # Increased from 30
  periodSeconds: 30
```

### Increase resources
```yaml
resources:
  limits:
    memory: 1G  # Increased
    cpu: "1.0"
```

### Scale down to reduce load during recovery
```bash
kubectl scale deployment/echotrace-backend -n echotrace --replicas=1
```

## Verification
- [ ] Pod in `Running` state
- [ ] No restarts in last 15 minutes
- [ ] Liveness/readiness probes passing
- [ ] Service responds to health checks
- [ ] Application logs show normal operation

## Post-Incident
- [ ] Determine root cause from crash logs
- [ ] Fix the underlying issue (code, config, dependency)
- [ ] Update probe thresholds if needed
- [ ] Add startup scripts or health checks if missing
