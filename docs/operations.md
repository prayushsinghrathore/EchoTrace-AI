# 🔧 EchoTrace AI — Operations Guide

Production operations guide covering deployment, scaling, updates, backup, capacity planning, maintenance, and health checks.

---

## Table of Contents

- [Deployment](#deployment)
- [Scaling](#scaling)
- [Rolling Updates](#rolling-updates)
- [Rollback](#rollback)
- [Backup & Restore](#backup--restore)
- [Capacity Planning](#capacity-planning)
- [Maintenance](#maintenance)
- [Health Checks](#health-checks)
- [Environment Configuration](#environment-configuration)

---

## Deployment

### Prerequisites

- Docker & Docker Compose v2.20+ (for Docker deployments)
- Kubernetes cluster 1.28+ (for K8s deployments)
- PostgreSQL 16+
- Neo4j 5 Enterprise

### Docker Compose (Production)

```bash
# 1. Clone the repository
git clone https://github.com/prayushsinghrathore/EchoTrace-AI.git
cd EchoTrace-AI

# 2. Configure environment
cp .env.example .env.prod
# Edit .env.prod with production values:
#   - Set SECRET_KEY to a strong 32+ char random string
#   - Set ENVIRONMENT=production
#   - Configure database passwords
#   - Set AI provider API keys if needed

# 3. Build and start
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Verify deployment
curl http://localhost:8000/api/v1/health
```

### Kubernetes

```bash
# 1. Create namespace and secrets
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 2. Deploy infrastructure
kubectl apply -f k8s/storage-pvc.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/neo4j.yaml

# 3. Deploy applications
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml

# 4. Deploy networking
kubectl apply -f k8s/cluster-issuer.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/network-policy.yaml

# 5. Deploy autoscaling and HA
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml

# 6. Run database migrations
kubectl exec -n echotrace deployment/echotrace-backend -- alembic upgrade head

# 7. Verify deployment
kubectl get pods -n echotrace -w
kubectl get ingress -n echotrace
```

### Environment Files

| File | Purpose |
|------|---------|
| `.env.example` | Template with documentation comments |
| `.env.prod` | Production values (gitignored) |
| `.env.staging` | Staging values (gitignored) |
| `.env.test` | CI/test values |

---

## Scaling

### Horizontal Scaling (Docker Compose)

```bash
# Scale a specific service
docker compose -f docker-compose.prod.yml up -d --scale backend=5 --scale frontend=3
```

### Horizontal Scaling (Kubernetes)

HPA automatically scales based on CPU/memory. Manual scaling:

```bash
# Manual scale
kubectl scale deployment/echotrace-backend -n echotrace --replicas=5
kubectl scale deployment/echotrace-frontend -n echotrace --replicas=3

# Check HPA status
kubectl get hpa -n echotrace
kubectl describe hpa -n echotrace
```

### Vertical Scaling

Adjust resource limits in `docker-compose.prod.yml` or K8s manifests:

```yaml
# docker-compose.prod.yml
deploy:
  resources:
    limits:
      cpus: "2.0"
      memory: 2G
    reservations:
      cpus: "0.5"
      memory: 512M
```

---

## Rolling Updates

### Docker Compose

```bash
# Pull latest images and recreate services
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --no-deps --build
```

### Kubernetes

Kubernetes handles rolling updates automatically when manifests change:

```bash
# Update image tag
kubectl set image deployment/echotrace-backend -n echotrace \
  echotrace-backend=ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-backend:0.1.0

# Monitor rollout
kubectl rollout status deployment/echotrace-backend -n echotrace

# Update via manifest change
kubectl apply -f k8s/backend.yaml
```

### Update Strategy

The Kubernetes deployment uses `RollingUpdate` with:
- `maxSurge: 25%` — allow 25% extra pods during update
- `maxUnavailable: 25%` — allow 25% pods unavailable during update

---

## Rollback

See the [Release Process](../RELEASE.md#rollback-process) for detailed rollback instructions.

### Docker Compose

```bash
# Rollback to previous image
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### Kubernetes

```bash
# Rollback to previous revision
kubectl rollout undo deployment/echotrace-backend -n echotrace

# Rollback to specific revision
kubectl rollout undo deployment/echotrace-backend -n echotrace --to-revision=2

# View rollout history
kubectl rollout history deployment/echotrace-backend -n echotrace
```

---

## Backup & Restore

See the [Backup & Restore Runbook](runbooks/backup-restore.md) for detailed procedures.

### Quick Reference

```bash
# PostgreSQL backup
docker compose exec postgres pg_dump -U echotrace -F c -Z 9 echotrace > backup.dump

# PostgreSQL restore
docker compose exec -T postgres pg_restore -U echotrace -d echotrace < backup.dump

# Neo4j backup
docker compose exec neo4j neo4j-admin database dump neo4j --to-path=/tmp

# Neo4j restore
docker compose run --rm neo4j neo4j-admin database load neo4j --from-path=/backup
```

---

## Capacity Planning

### Monitoring Metrics

Track the following for capacity planning:

| Metric | Source | Planning Horizon |
|--------|--------|-----------------|
| Request rate (req/s) | Prometheus | Weekly, Monthly |
| P95 latency | Prometheus | Weekly |
| Active database connections | PostgreSQL exporter | Daily |
| Database size growth | PostgreSQL exporter | Weekly, Monthly |
| Disk usage | Node exporter | Daily, Weekly |
| Memory usage | Node exporter / cAdvisor | Daily |
| Container restarts | Kubernetes events | Daily |

### Growth Planning

```bash
# Database size trend (check weekly)
curl 'http://localhost:9090/api/v1/query?query=pg_database_size_bytes{datname=~"echotrace.*"}'
```

### When to Scale

- **Request rate** consistently > 60% of peak capacity
- **Database connections** consistently > 60% of max
- **P95 latency** trending upward over 2 weeks
- **Disk usage** growing faster than expected

---

## Maintenance

### Routine Maintenance

| Task | Frequency | Impact |
|------|-----------|--------|
| Apply security patches | Monthly | Restart required |
| Review logs for anomalies | Weekly | None |
| Check disk usage | Weekly | None |
| Vacuum PostgreSQL | Weekly | Low |
| Review alert rules | Monthly | None |
| Rotate secrets | Quarterly | Config update |
| TLS certificate renewal | Automatic (cert-manager) | None |
| Database backup verification | Weekly | None |
| Load test review | Monthly | None |
| Dependency updates | Monthly | Build + deploy |
| Review monitoring dashboards | Monthly | None |

### PostgreSQL Maintenance

```bash
# Manual VACUUM
docker compose exec postgres psql -U echotrace -d echotrace -c "VACUUM ANALYZE;"

# Check table bloat
docker compose exec postgres psql -U echotrace -d echotrace -c "
SELECT schemaname, tablename, n_live_tup, n_dead_tup
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 10;"

# Reindex (low traffic period)
docker compose exec postgres psql -U echotrace -d echotrace -c "REINDEX DATABASE echotrace;"
```

### Neo4j Maintenance

```cypher
// Check database state
CALL dbms.database.state();

// List active transactions
CALL dbms.listTransactions();

// Run index maintenance
CALL db.index.fulltext.awaitEventuallyConsistentIndexRefresh();
```

### Log Rotation

Logs are managed by Docker's json-file logging driver with rotation:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## Health Checks

### Endpoints

| Endpoint | Method | Purpose | Expected Response |
|----------|--------|---------|------------------|
| `/api/v1/health` | GET | Full health check | `{"status":"healthy",...}` |
| `/api/v1/ready` | GET | Readiness check | 200 OK |
| `/api/v1/live` | GET | Liveness check | 200 OK |
| `/` | GET | Root info | `{"name":"EchoTrace AI",...}` |

### Docker Health Checks

Production Compose includes health checks for all services:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/live"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Kubernetes Probes

Kubernetes manifests include liveness and readiness probes:

```yaml
livenessProbe:
  httpGet:
    path: /api/v1/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /api/v1/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Manual Health Verification

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Readiness check
curl http://localhost:8000/api/v1/ready

# Liveness check
curl http://localhost:8000/api/v1/live

# Metrics snapshot
curl http://localhost:8000/api/v1/metrics
```

---

## Environment Configuration

### Production Checklist

- [ ] `SECRET_KEY` set to a strong random 32+ character string
- [ ] `ENVIRONMENT` set to `production`
- [ ] `LOG_LEVEL` set to `INFO` (not `DEBUG`)
- [ ] Database passwords set to strong values
- [ ] CORS origins configured for your domain
- [ ] TLS/HTTPS enabled
- [ ] Docker security hardening applied (already configured)
- [ ] Monitoring stack deployed
- [ ] Backups configured and verified
- [ ] Alert receivers configured (Slack, PagerDuty, etc.)

### Environment Variables

See [`.env.example`](../.env.example) for the complete environment variable reference.

---

## References

- [Deployment Guide (Docker)](docker-deployment.md)
- [Deployment Guide (Kubernetes)](kubernetes.md)
- [Monitoring Guide](monitoring.md)
- [SRE Guide](sre.md)
- [Release Process](../RELEASE.md)
- [Backup & Restore Runbook](runbooks/backup-restore.md)
- [Disaster Recovery Runbook](runbooks/disaster-recovery.md)
