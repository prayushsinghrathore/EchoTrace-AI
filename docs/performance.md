# 📈 EchoTrace AI — Performance Baselines

Expected production performance baselines for EchoTrace AI services.

**NOTE:** These values are **recommended targets** based on architecture analysis, not measured benchmark results. Actual performance should be validated through load testing in your target environment.

---

## Table of Contents

- [API Performance](#api-performance)
- [Database Performance](#database-performance)
- [Container Performance](#container-performance)
- [Infrastructure Sizing](#infrastructure-sizing)
- [Scaling Guidelines](#scaling-guidelines)
- [Startup Times](#startup-times)
- [Recommended Sizing by Deployment Size](#recommended-sizing-by-deployment-size)

---

## API Performance

### Backend (FastAPI)

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| **P50 Latency** | < 100ms | > 200ms | > 500ms |
| **P95 Latency** | < 500ms | > 1000ms | > 2000ms |
| **P99 Latency** | < 1000ms | > 2000ms | > 5000ms |
| **Throughput (single instance)** | 500 req/s | 1000 req/s | 2000 req/s |
| **Error Rate** | < 0.1% | > 1% | > 5% |
| **Availability** | 99.9% | 99.5% | 99.0% |

### Common Endpoint Latency Targets

| Endpoint | Target P50 | Target P95 |
|----------|-----------|-----------|
| Health check | < 10ms | < 50ms |
| Auth (login/register) | < 200ms | < 500ms |
| List resources (paginated) | < 50ms | < 200ms |
| Get resource by ID | < 30ms | < 100ms |
| Create resource | < 100ms | < 300ms |
| AI analysis queries | < 5000ms | < 15000ms |
| Report generation | < 2000ms | < 5000ms |
| Graph queries (Neo4j) | < 100ms | < 500ms |

### Frontend (Next.js)

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| **Page Load (SSR)** | < 2s | < 4s | > 6s |
| **Time to First Byte (TTFB)** | < 200ms | < 500ms | > 1000ms |
| **First Contentful Paint (FCP)** | < 1.5s | < 3s | > 5s |
| **Largest Contentful Paint (LCP)** | < 2.5s | < 4s | > 6s |
| **Client Error Rate (4xx)** | < 1% | > 3% | > 10% |

---

## Database Performance

### PostgreSQL

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| **Query Latency (P50)** | < 10ms | > 50ms | > 200ms |
| **Query Latency (P95)** | < 50ms | > 200ms | > 1000ms |
| **Max Concurrent Connections** | 20 | 40 | 80% of max |
| **Cache Hit Ratio** | > 99% | < 97% | < 95% |
| **Transaction Rate** | 100 tps | 500 tps | 1000 tps |
| **Replication Lag** | < 1s | < 5s | > 30s |

### Neo4j

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| **Query Latency (P50)** | < 50ms | > 200ms | > 1000ms |
| **Query Latency (P95)** | < 200ms | > 500ms | > 2000ms |
| **Heap Usage** | < 60% | > 80% | > 90% |
| **Page Cache Hit Ratio** | > 95% | < 90% | < 80% |
| **Transaction Rate** | 50 tps | 200 tps | 500 tps |

---

## Container Performance

### Resource Usage Per Instance

| Service | CPU (steady) | CPU (peak) | Memory (steady) | Memory (peak) |
|---------|-------------|-----------|-----------------|---------------|
| Backend | 0.1–0.3 cores | 0.5–1.0 cores | 128–256 MB | 512 MB |
| Frontend | 0.05–0.2 cores | 0.3–0.5 cores | 128–256 MB | 512 MB |
| PostgreSQL | 0.3–0.5 cores | 1.0–2.0 cores | 256–512 MB | 1–2 GB |
| Neo4j | 0.5–1.0 cores | 2.0–4.0 cores | 512 MB–1 GB | 2–4 GB |
| Prometheus | 0.1–0.2 cores | 0.5 cores | 256–512 MB | 1 GB |
| Grafana | 0.05–0.1 cores | 0.2 cores | 64–128 MB | 256 MB |

### Docker Container Sizes

| Image | Size (approx) |
|-------|---------------|
| Backend (production) | 150–250 MB |
| Frontend (production) | 200–350 MB |

---

## Infrastructure Sizing

### Minimum Production Deployment

| Component | vCPU | Memory | Storage |
|-----------|------|--------|---------|
| Backend (2 replicas) | 2 × 0.5 | 2 × 256 MB | — |
| Frontend (2 replicas) | 2 × 0.25 | 2 × 256 MB | — |
| PostgreSQL | 1 | 1 GB | 20 GB SSD |
| Neo4j | 2 | 2 GB | 20 GB SSD |
| **Total** | **~3.5 vCPU** | **~4 GB** | **40 GB SSD** |

### Recommended Production Deployment

| Component | vCPU | Memory | Storage |
|-----------|------|--------|---------|
| Backend (3 replicas) | 3 × 1.0 | 3 × 512 MB | — |
| Frontend (2 replicas) | 2 × 0.5 | 2 × 512 MB | — |
| PostgreSQL | 2 | 4 GB | 50 GB SSD |
| Neo4j | 4 | 8 GB | 50 GB SSD |
| Monitoring stack | 1 | 2 GB | 20 GB SSD |
| **Total** | **~12 vCPU** | **~16 GB** | **120 GB SSD** |

### High-Volume Production Deployment

| Component | vCPU | Memory | Storage |
|-----------|------|--------|---------|
| Backend (5+ replicas) | 5 × 2.0 | 5 × 1 GB | — |
| Frontend (3+ replicas) | 3 × 1.0 | 3 × 512 MB | — |
| PostgreSQL (replicated) | 4 | 8 GB | 100 GB SSD |
| Neo4j (clustered) | 8 | 16 GB | 200 GB SSD |
| Monitoring stack | 2 | 4 GB | 50 GB SSD |
| **Total** | **~28 vCPU** | **~38 GB** | **350 GB SSD** |

---

## Scaling Guidelines

### When to Scale Vertically

| Indicator | Threshold | Action |
|-----------|-----------|--------|
| Backend CPU > 70% for 10m | Increase backend replicas | Scale horizontally first, then vertically |
| PostgreSQL CPU > 60% | Increase DB vCPU/memory | Upgrade instance size |
| PostgreSQL disk > 80% | Increase storage | Add storage or archive old data |
| Neo4j heap > 80% | Increase heap memory | Increase container memory limit |

### When to Scale Horizontally

| Indicator | Threshold | Action |
|-----------|-----------|--------|
| P95 latency > 1000ms | Increase replicas | Add 2 replicas, re-evaluate |
| Error rate > 1% | Investigate + scale | Check for saturation, add replicas |
| Throughput > 70% of max | Add replicas | Scale by 50% |

### Kubernetes Auto-scaling

HPA is configured in [k8s/hpa.yaml](../k8s/hpa.yaml):

```bash
# Current HPA status
kubectl get hpa -n echotrace -w
```

---

## Startup Times

| Service | Cold Start | Warm Start |
|---------|-----------|------------|
| Backend | 2–5 seconds | < 1 second |
| Frontend | 5–15 seconds | < 2 seconds |
| PostgreSQL | 5–10 seconds | < 3 seconds |
| Neo4j | 15–30 seconds | < 10 seconds |
| Prometheus | 2–5 seconds | < 2 seconds |
| Grafana | 3–10 seconds | < 3 seconds |

---

## Recommended Sizing by Deployment Size

### Small (Personal / Dev / Demo)
- 1–2 backend instances, 1 frontend instance
- Single PostgreSQL, single Neo4j
- Minimal or no monitoring
- **Estimated monthly infra cost:** $50–150

### Medium (Team / Startup)
- 2–3 backend instances, 2 frontend instances
- PostgreSQL with replicas, single Neo4j
- Full monitoring stack
- **Estimated monthly infra cost:** $500–1500

### Large (Enterprise)
- 5+ backend instances, 3+ frontend instances
- PostgreSQL cluster, Neo4j cluster
- Full monitoring, tracing, logging
- Auto-scaling, multi-AZ
- **Estimated monthly infra cost:** $2000–5000+

---

## References

- [SRE Guide](sre.md)
- [Operations Guide](operations.md)
- [Monitoring Guide](monitoring.md)
- [Alert Rules](../monitoring/prometheus/rules/)
