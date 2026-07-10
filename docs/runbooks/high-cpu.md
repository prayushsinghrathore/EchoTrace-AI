# Runbook: High CPU Usage

## Severity
**Warning** → **Critical** as usage increases.

## Symptoms
- `HighCPUUsage` alert (80% for 10m)
- `CriticalCPUUsage` alert (95% for 5m)
- Services responding slowly
- Timeouts on API calls

## Immediate Steps

### 1. Identify which process is consuming CPU
```bash
# Docker
docker stats --no-stream
# Host
top -o %CPU
# Kubernetes
kubectl top pods -n echotrace
```

### 2. Check if it's a single container or host-wide
```bash
# Container-level
docker stats --no-stream $(docker ps -q)
# Or from cAdvisor metrics in Grafana
```

### 3. Review recent deployments
- Check if a new version was recently deployed
- Review release notes for performance regressions

## Root Cause Diagnosis

### Traffic Spike
- Symptom: Elevated request rate across all services
- Check: `rate(echotrace_requests_total[5m])` in Grafana
- Fix: Scale horizontally, consider auto-scaling

### Resource Leak
- Symptom: CPU gradually increases over time
- Check: Grafana dashboard for trend analysis
- Fix: Restart service, investigate memory/connection leaks

### Query Regression
- Symptom: Database CPU high but application CPU normal
- Check: Slow query logs, database metrics in Grafana
- Fix: Add indexes, optimize queries, review recent changes

### Background Job Problem
- Symptom: Periodic CPU spikes
- Check: Cron jobs, scheduled tasks, AI processing jobs
- Fix: Throttle batch jobs, schedule during off-peak

## Resolution Steps

### Scale horizontally
```bash
docker compose up -d --scale backend=3 --scale frontend=2
kubectl scale deployment/echotrace-backend -n echotrace --replicas=5
kubectl scale deployment/echotrace-frontend -n echotrace --replicas=3
```

### Restart the affected service
```bash
docker compose restart <service>
kubectl rollout restart deployment/<name> -n echotrace
```

### Add resource limits
```yaml
# In docker-compose.yml or k8s manifests
deploy:
  resources:
    limits:
      cpus: "2.0"
      memory: 1G
```

### Enable auto-scaling
```bash
# Already configured via HPA in Kubernetes
kubectl get hpa -n echotrace
```

## Verification
- [ ] CPU usage below 60%
- [ ] No `CriticalCPUUsage` alerts firing
- [ ] API latency within SLO
- [ ] Auto-scaling functioning correctly
- [ ] All services responsive

## Post-Incident
- [ ] Review and optimize problematic code paths
- [ ] Adjust HPA thresholds if needed
- [ ] Add missing database indexes
- [ ] Review cache effectiveness
