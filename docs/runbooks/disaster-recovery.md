# Runbook: Disaster Recovery

## Severity
**Critical** — Complete service failure requiring full recovery.

## Scope
This runbook covers recovery from catastrophic failures including:
- Complete data center/region outage
- Accidental deletion of all data
- Critical security breach requiring rebuild
- Extended infrastructure failure

## Recovery Objectives

| Metric | Target |
|--------|--------|
| Recovery Time Objective (RTO) | 4 hours |
| Recovery Point Objective (RPO) | 1 hour |
| Data Loss Tolerance | < 1 hour of data |

## Recovery Strategies

### Strategy A: Rebuild from Infrastructure-as-Code (Recommended)

**RTO: 2–4 hours**

```bash
# 1. Provision infrastructure
cd terraform
terraform init
terraform apply -auto-approve

# 2. Configure Kubernetes cluster
aws eks update-kubeconfig --name echotrace-prod
kubectl apply -f k8s/namespace.yaml

# 3. Deploy secrets (from vault or secure store)
kubectl apply -f k8s/secret.yaml

# 4. Deploy infrastructure components
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/storage-pvc.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/neo4j.yaml

# 5. Restore databases from backup
# See backup-restore.md

# 6. Deploy applications
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml

# 7. Deploy networking
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/network-policy.yaml

# 8. Deploy monitoring
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/cluster-issuer.yaml
```

### Strategy B: Docker Compose Recovery

**RTO: 1–2 hours**

```bash
# 1. Clone repository
git clone https://github.com/prayushsinghrathore/EchoTrace-AI.git
cd EchoTrace-AI

# 2. Configure environment
cp .env.example .env.prod
# Edit .env.prod with production values

# 3. Start data stores
docker compose -f docker-compose.prod.yml up -d postgres neo4j

# 4. Restore databases (see backup-restore.md)

# 5. Start application services
docker compose -f docker-compose.prod.yml up -d

# 6. Start monitoring
docker compose -f docker-compose.monitoring.yml up -d

# 7. Verify deployment
curl http://localhost:8000/api/v1/health
```

### Strategy C: Fresh Deploy (No Backup Available)

**RTO: 2–3 hours, RPO: Full data loss**

```bash
# Follow Strategy A or B, but skip database restore.
# Application will start with empty databases.
# This is a last resort — data will be lost.
```

## Recovery Steps

### Phase 1: Assess Damage (15 min)
- [ ] Determine scope (single service, entire stack, data center)
- [ ] Check if DNS/routing needs redirection
- [ ] Verify if backup infrastructure is accessible
- [ ] Notify stakeholders of incident

### Phase 2: Infrastructure Recovery (30–60 min)
- [ ] Provision compute resources
- [ ] Restore Kubernetes cluster or Docker hosts
- [ ] Deploy base infrastructure (storage, networking)
- [ ] Verify TLS certificates

### Phase 3: Data Restoration (30–60 min)
- [ ] Restore PostgreSQL from latest backup
- [ ] Restore Neo4j from latest backup
- [ ] Verify data integrity (row counts, referential integrity)

### Phase 4: Application Deploy (15–30 min)
- [ ] Deploy backend
- [ ] Deploy frontend
- [ ] Run database migrations
- [ ] Verify all services healthy

### Phase 5: Verify (15–30 min)
- [ ] Run health checks
- [ ] Run smoke tests
- [ ] Verify monitoring dashboards
- [ ] Confirm with stakeholders

## Communication

| Stakeholder | Channel | Timing |
|-------------|---------|--------|
| Engineering team | Slack #incidents | Immediate |
| Leadership | Email / Slack | Within 30 min |
| Users (if applicable) | Status page | Within 1 hour |

## Post-Recovery

- [ ] Conduct root cause analysis
- [ ] Update backup and recovery procedures
- [ ] Test recovery process with drill
- [ ] Update this runbook with lessons learned
