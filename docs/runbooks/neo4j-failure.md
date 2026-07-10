# Runbook: Neo4j Failure

## Severity
**High** — Graph database unavailable, graph-related features degrade.

## Symptoms
- `Neo4jHighHeapUsage` or `Neo4jTransactionFailures` alert firing
- Backend graph query errors: `Unable to connect to Neo4j`
- Health check reports Neo4j as unhealthy
- Graph visualization features not working

## Immediate Steps

### 1. Verify Neo4j status
```bash
docker compose ps neo4j
kubectl get pods -n echotrace -l app=neo4j
```

### 2. Check Neo4j logs
```bash
docker compose logs --tail=100 neo4j
kubectl logs -n echotrace statefulset/neo4j --tail=100
```

### 3. Verify connectivity
```bash
docker compose exec neo4j cypher-shell -u neo4j -p <password> "RETURN 1"
```

## Root Cause Diagnosis

### Out of Memory (Heap)
- Symptom: `Neo4jHighHeapUsage` alert
- Check:
  ```
  CALL dbms.listConfig() YIELD name, value WHERE name = 'dbms.memory.heap.max_size';
  ```
- Fix: Increase heap size in Neo4j config or container memory limit

### Transaction Failures
- Symptom: `Neo4jTransactionFailures` alert
- Query:
  ```cypher
  CALL dbms.listTransactions();
  ```
- Fix: Terminate stuck transactions, review query patterns

### Disk Full
- Symptom: Write operations fail
- Check: Database size with `CALL dbms.database.state();`
- Fix: Run cleanup queries, compact database, increase storage

### Connection Pool Exhausted
- Symptom: New connections refused
- Check: `CALL dbms.listConnections();`
- Fix: Consider read replicas or connection pooling

## Resolution Steps

### Restart Neo4j
```bash
docker compose restart neo4j
kubectl rollout restart statefulset/neo4j -n echotrace
```

### Clear transaction logs (if disk is full)
```bash
# Reduce checkpoint retention
CALL dbms.changePassword('new-password');
```

### Increase memory
```yaml
# In docker-compose.yml or k8s/neo4j.yaml
NEO4J_dbms_memory_heap_max__size: 2G
NEO4J_dbms_memory_pagecache_size: 1G
```

## Verification
- [ ] Neo4j accepts queries: `docker compose exec neo4j cypher-shell -u neo4j -p <password> "RETURN 1"`
- [ ] Backend health check passes
- [ ] Graph visualization works in UI
- [ ] Memory usage is under 80%
- [ ] No transaction failures in logs

## Post-Incident
- [ ] Review and optimize slow Cypher queries
- [ ] Add missing indexes
- [ ] Tune heap and page cache settings
- [ ] Schedule periodic database maintenance
