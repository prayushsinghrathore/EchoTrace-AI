# 📈 EchoTrace AI — Scaling Guide

Production scaling strategies for EchoTrace AI across Docker and Kubernetes deployments.

---

## When to Scale

| Indicator | Threshold | Action |
|-----------|-----------|--------|
| P95 API latency > 1000ms | Sustained > 5m | Add backend replicas |
| Error rate > 1% | Sustained > 5m | Investigate, then scale |
| CPU > 70% (per pod) | Sustained > 10m | Add replicas |
| Memory > 80% (per pod) | Sustained > 10m | Increase memory limit or add replicas |
| Database connections > 60% of max | Sustained > 10m | Increase pool size or add read replicas |
| Database disk > 80% | Immediate | Increase storage or archive data |
| Neo4j heap > 80% | Sustained > 5m | Increase heap allocation |

---

## Horizontal Scaling

### Kubernetes (HPA)

HPA is pre-configured in [`k8s/hpa.yaml`](../k8s/hpa.yaml) to scale on CPU and memory:

```yaml
# Current thresholds (from k8s/hpa.yaml)
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70
```

```bash
# Monitor HPA
kubectl get hpa -n echotrace -w

# Manual scale override
kubectl scale deployment/echotrace-backend -n echotrace --replicas=5

# Disable HPA temporarily
kubectl delete hpa backend-hpa -n echotrace
```

### Docker Compose

```bash
# Manual scale
docker compose -f docker-compose.prod.yml up -d --scale backend=5

# Check resource usage
docker stats --no-stream
```

### Database Scaling

```bash
# Check connection pool usage
SELECT count(*) FROM pg_stat_activity WHERE datname = 'echotrace';
SELECT max_conn FROM pg_settings WHERE name = 'max_connections';

# Increase pool size in environment
# DB_POOL_SIZE=20  DB_MAX_OVERFLOW=10
```

---

## Vertical Scaling

### Backend

```yaml
# docker-compose.prod.yml
backend:
  deploy:
    resources:
      limits:
        cpus: "2.0"
        memory: "2G"
```

### PostgreSQL

```yaml
# docker-compose.prod.yml
postgres:
  deploy:
    resources:
      limits:
        cpus: "4.0"
        memory: "4G"
  # Key tuning params
  command:
    - "shared_buffers=1GB"
    - "effective_cache_size=3GB"
    - "work_mem=64MB"
    - "maintenance_work_mem=256MB"
```

### Neo4j

```yaml
# docker-compose.prod.yml
neo4j:
  environment:
    NEO4J_dbms_memory_heap_max__size: "4G"
    NEO4J_dbms_memory_pagecache_size: "2G"
```

---

## Database Connection Pool Sizing

### Formula

```
pool_size = (max_connections * (100 - overhead_pct)) / application_instances
```

### Recommended Settings

| Backend Instances | DB_POOL_SIZE | DB_MAX_OVERFLOW | Max Total Connections |
|-------------------|-------------|-----------------|----------------------|
| 2 | 10 | 5 | 30 |
| 3 | 8 | 4 | 36 |
| 5 | 6 | 3 | 45 |
| 10 | 4 | 2 | 60 |

---

## Cache Scaling

When Redis is enabled (set `REDIS_ENABLED=true`):

```bash
# Monitor cache hit ratio
curl http://localhost:8000/api/v1/metrics | jq '.cache'
```

Target cache hit ratio: **> 90%**

If cache hit ratio is below target:
- Increase TTL for frequently accessed data
- Add caching for additional query patterns
- Increase Redis `maxmemory`

---

## Neo4j Scaling

### Single Instance vs. Cluster

| Deployment | Max Data Size | Read Throughput | Write Throughput | HA |
|-----------|--------------|-----------------|-----------------|----|
| Single | < 100 GB | Up to 10k qps | Up to 2k tps | No |
| Cluster (3 cores) | < 1 TB | Up to 30k qps | Up to 5k tps | Yes |

### Heap Sizing

```yaml
# General rule: heap_max = min(total_ram * 0.7, 32GB)
NEO4J_dbms_memory_heap_max__size: "4G"     # 8GB host
NEO4J_dbms_memory_heap_initial__size: "2G"
NEO4J_dbms_memory_pagecache_size: "2G"     # 50% of heap for page cache
```

---

## References

- [SRE Guide](sre.md)
- [Operations Guide](operations.md)
- [Performance Baselines](performance-baseline.md)
- [Monitoring Guide](monitoring.md)
