# 🗄️ EchoTrace AI — Database Optimization Guide

Query optimization, indexing strategy, and performance tuning for PostgreSQL and Neo4j.

---

## Table of Contents

- [PostgreSQL Indexing Strategy](#postgresql-indexing-strategy)
- [Query Optimization](#query-optimization)
- [Connection Pool Tuning](#connection-pool-tuning)
- [VACUUM & Maintenance](#vacuum--maintenance)
- [Neo4j Optimization](#neo4j-optimization)
- [Monitoring Database Performance](#monitoring-database-performance)

---

## PostgreSQL Indexing Strategy

### Current Indexes

Indexes are defined in SQLAlchemy model files and the migration [`010_add_performance_indexes`](../backend/alembic/versions/20260711_add_performance_indexes.py):

| Table | Indexed Columns | Purpose |
|-------|----------------|---------|
| `evidence` | `project_id`, `workspace_id`, `title`, `evidence_number`, `category`, `status`, `sha256_hash`, `created_by`, `updated_by`, `(workspace_id, status)` | Comprehensive coverage for listing, search, and ownership queries |
| `investigations` | `workspace_id`, `title`, `status`, `created_by`, `lead_investigator` | Workspace-scoped lists, assignment queries |
| `entities` | `investigation_id`, `type`, `label`, `created_by` | Investigation graph lookups |
| `relationships` | `investigation_id`, `source_entity_id`, `target_entity_id`, `relationship_type` | Graph traversal |
| `activity_events` | `workspace_id`, `investigation_id`, `user_id` | Activity feeds |
| `audit_logs` | `user_id`, `workspace_id` | Audit trail |
| `ai_suggestions` | `investigation_id`, `workspace_id`, `created_by` | AI feature queries |
| `ai_jobs` | `user_id`, `workspace_id`, `investigation_id` | Job tracking |
| `evidence_comments` | `created_by` | User's comments |
| `chain_of_custody` | `created_by` | Custody trail |
| `evidence_versions` | `created_by` | Version history |
| `invitations` | `workspace_id`, `invited_by` | Invitation lookups |
| `notifications` | `user_id` | Notification queries |

### Index Maintenance

```sql
-- Check index usage (identify unused indexes)
SELECT
    schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;

-- Check for missing indexes (sequential scans)
SELECT
    relname, seq_scan, seq_tup_read, idx_scan
FROM pg_stat_user_tables
WHERE seq_scan > 1000
ORDER BY seq_scan DESC
LIMIT 20;

-- Rebuild indexes (during low traffic)
REINDEX DATABASE echotrace;
```

---

## Query Optimization

### Using EXPLAIN ANALYZE

```sql
-- Identify slow queries
EXPLAIN ANALYZE
SELECT * FROM evidence
WHERE workspace_id = 'uuid-here'
  AND status = 'active'
ORDER BY created_at DESC
LIMIT 50;
```

### Common Patterns

**Paginated listing with count:**
```sql
-- Use window functions instead of separate COUNT query
SELECT *, COUNT(*) OVER() AS total_count
FROM evidence
WHERE workspace_id = 'uuid'
ORDER BY created_at DESC
LIMIT 50 OFFSET 0;
```

**Search with ILIKE:**
```sql
-- For text search, consider PostgreSQL full-text search or pg_trgm
CREATE INDEX ix_evidence_title_trgm ON evidence
  USING gin (title gin_trgm_ops);
-- Requires: CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**Join optimization:**
```sql
-- Ensure join columns are indexed on both sides
EXPLAIN ANALYZE
SELECT e.*, u.name AS created_by_name
FROM evidence e
LEFT JOIN users u ON u.id = e.created_by
WHERE e.workspace_id = 'uuid';
```

### N+1 Query Detection

```bash
# Check for repeated identical queries in application logs
docker compose logs backend | grep -o "SELECT.*FROM evidence" | sort | uniq -c | sort -rn | head -10
```

The repository pattern in [`backend/app/repositories/base.py`](../backend/app/repositories/base.py) should use eager loading where appropriate:

```python
# Eager load relationships to avoid N+1
from sqlalchemy.orm import joinedload
stmt = select(Evidence).options(joinedload(Evidence.created_by_user))
```

---

## Connection Pool Tuning

### Current Settings

```python
# backend/app/core/config.py
DB_POOL_SIZE = 10        # Base pool connections
DB_MAX_OVERFLOW = 5      # Overflow connections allowed
DB_POOL_RECYCLE = 3600   # Recycle connections after 1 hour
```

### Sizing Formula

```
pool_size = (max_connections * (100 - reserve_pct)) / app_instances
```

### Recommended Settings

| App Instances | DB_POOL_SIZE | DB_MAX_OVERFLOW | Total Connections |
|---------------|-------------|-----------------|-------------------|
| 2 | 10 | 5 | 30 |
| 3 | 8 | 4 | 36 |
| 5 | 6 | 3 | 45 |
| 10 | 4 | 2 | 60 |

### Monitoring Pool Usage

```sql
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
SELECT count(*) FROM pg_stat_activity WHERE wait_event IS NOT NULL;
```

---

## VACUUM & Maintenance

### Auto-Vacuum Configuration

The default PostgreSQL auto-vacuum settings are usually sufficient for EchoTrace AI's workload. For heavy-write deployments:

```ini
# postgresql.conf or docker-compose command
autovacuum_vacuum_scale_factor = 0.01
autovacuum_analyze_scale_factor = 0.005
autovacuum_vacuum_threshold = 1000
```

### Manual Maintenance

```bash
# Weekly maintenance during low traffic
docker compose exec postgres psql -U echotrace -d echotrace -c "
  VACUUM ANALYZE;
  REINDEX DATABASE echotrace;
"

# Check table bloat
SELECT
    schemaname, tablename,
    n_live_tup, n_dead_tup,
    round(n_dead_tup * 100.0 / GREATEST(n_live_tup + n_dead_tup, 1), 2) AS dead_pct
FROM pg_stat_user_tables
ORDER BY dead_pct DESC
LIMIT 20;
```

### Monitoring Dead Tuples

```sql
SELECT relname, n_dead_tup
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;
```

---

## Neo4j Optimization

### Indexing Strategy

```cypher
// Create indexes on frequently queried properties
CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX entity_label_idx IF NOT EXISTS FOR (e:Entity) ON (e.label);

// Composite index for lookups
CREATE INDEX investigation_entity_idx IF NOT EXISTS
  FOR (e:Entity) ON (e.investigation_id, e.type);

// Full-text search
CREATE FULLTEXT INDEX entity_search IF NOT EXISTS
  FOR (n:Entity) ON EACH [n.label, n.description];
```

### Query Optimization

```cypher
// Use PROFILE to identify performance bottlenecks
PROFILE
MATCH (inv:Investigation {id: $id})-[:HAS_EVENT]->(ev:Event)
RETURN ev ORDER BY ev.timestamp DESC
LIMIT 100;
```

### Heap & Page Cache

```yaml
# docker-compose.prod.yml
NEO4J_dbms_memory_heap_max__size: "4G"
NEO4J_dbms_memory_pagecache_size: "2G"
GENERIC RULE: heap = min(host_ram * 0.7, 32GB), pagecache = 50% of heap
```

### Transaction Management

```cypher
// Avoid long-running transactions
CALL dbms.listTransactions();
// Terminate stuck transactions:
// CALL dbms.killTransaction(transactionId);
```

---

## Monitoring Database Performance

### Prometheus Queries

```promql
# PostgreSQL cache hit ratio
rate(pg_stat_database_blks_hit{datname=~"echotrace.*"}[5m])
/
(rate(pg_stat_database_blks_hit{datname=~"echotrace.*"}[5m]) + rate(pg_stat_database_blks_read{datname=~"echotrace.*"}[5m]))
* 100

# Slow queries
pg_stat_activity_max_tx_duration{datname=~"echotrace.*"}

# Connection utilization
pg_stat_activity_count{datname=~"echotrace.*"}
```

### Neo4j Prometheus Queries

```promql
# Heap usage
neo4j_memory_pool_usage_bytes{pool="heap"}
/
neo4j_memory_pool_max_bytes{pool="heap"}

# Query latency
rate(neo4j_query_duration_seconds_sum[5m])
/
rate(neo4j_query_duration_seconds_count[5m])
```

---

## References

- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Neo4j Performance Tuning](https://neo4j.com/docs/operations-manual/current/performance/)
- [Monitoring Guide](monitoring.md)
- [Scaling Guide](scaling.md)
- [Performance Baselines](performance-baseline.md)
