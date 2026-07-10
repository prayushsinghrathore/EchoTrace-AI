# Runbook: Backup & Restore

## Overview

This runbook covers backup and restore procedures for EchoTrace AI data stores.

## Backup Procedures

### PostgreSQL Backup

#### Automated (Recommended)

Configure periodic backups via cron or Kubernetes CronJob:

```bash
#!/bin/bash
# pg_dump with custom format
BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

pg_dump -U echotrace -h postgres -d echotrace \
  -F c -Z 9 \
  -f "${BACKUP_DIR}/echotrace_db_${TIMESTAMP}.dump"
```

**Kubernetes CronJob:**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: echotrace
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: pgdump
            image: postgres:16-alpine
            env:
            - name: PGHOST
              value: postgres
            - name: PGUSER
              value: echotrace
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: echotrace-secrets
                  key: postgres-password
            command:
            - sh
            - -c
            - pg_dump -F c -Z 9 -f /backups/echotrace_$(date +%Y%m%d).dump echotrace
            volumeMounts:
            - mountPath: /backups
              name: backup-storage
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

#### Manual Backup

```bash
# Plain SQL format
docker compose exec postgres pg_dump -U echotrace echotrace > backup.sql

# Custom format (compressed, parallel restore)
docker compose exec postgres pg_dump -U echotrace -F c -Z 9 -f /tmp/backup.dump echotrace
docker compose cp postgres:/tmp/backup.dump ./backup.dump

# Schema only
docker compose exec postgres pg_dump -U echotrace --schema-only echotrace > schema.sql
```

### Neo4j Backup

#### Automated

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: neo4j-backup
  namespace: echotrace
spec:
  schedule: "0 3 * * *"  # Daily at 3 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: neo4j-backup
            image: neo4j:5-enterprise
            command:
            - neo4j-admin
            - database
            - dump
            - --to-path=/backups
            - neo4j
            volumeMounts:
            - mountPath: /data
              name: neo4j-data
            - mountPath: /backups
              name: backup-storage
          volumes:
          - name: neo4j-data
            persistentVolumeClaim:
              claimName: neo4j-data
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
```

#### Manual Backup

```bash
# Online backup (enterprise feature)
docker compose exec neo4j neo4j-admin database dump neo4j --to-path=/tmp
docker compose cp neo4j:/tmp/neo4j.dump ./neo4j-backup.dump

# Offline backup
docker compose stop neo4j
docker compose run --rm neo4j neo4j-admin database dump neo4j --to-path=/backups
docker compose start neo4j
```

### Uploaded Files Backup

```bash
# Backup storage directory
tar -czf storage-backup.tar.gz backend/storage/
```

---

## Restore Procedures

### PostgreSQL Restore

```bash
# Custom format
docker compose exec -T postgres pg_restore -U echotrace -d echotrace -v < backup.dump

# SQL format
docker compose exec -T postgres psql -U echotrace echotrace < backup.sql

# Create database first if needed
docker compose exec postgres createdb -U echotrace echotrace_restore
docker compose exec -T postgres pg_restore -U echotrace -d echotrace_restore -v < backup.dump
```

### Neo4j Restore

```bash
# Stop Neo4j
docker compose stop neo4j

# Remove existing database
docker compose run --rm neo4j neo4j-admin database delete neo4j

# Load backup
docker compose run --rm -v $(pwd)/neo4j-backup.dump:/backup.dump neo4j \
  neo4j-admin database load neo4j --from-path=/backup.dump

# Start Neo4j
docker compose start neo4j
```

---

## Backup Verification

Regularly verify backups can be restored:

```bash
# Test PostgreSQL restore
docker compose exec -T postgres createdb -U echotrace echotrace_test_restore
docker compose exec -T postgres pg_restore -U echotrace -d echotrace_test_restore < backup.dump
docker compose exec postgres psql -U echotrace -d echotrace_test_restore -c "SELECT count(*) FROM users;"
docker compose exec postgres psql -U echotrace -c "DROP DATABASE echotrace_test_restore;"
```

## Retention Policy

| Backup Type | Retention | Storage |
|-------------|-----------|---------|
| Daily PostgreSQL | 30 days | Local or S3 |
| Weekly PostgreSQL | 12 weeks | Local or S3 |
| Monthly PostgreSQL | 12 months | S3/Glacier |
| Daily Neo4j | 30 days | Local or S3 |
| Weekly Neo4j | 12 weeks | Local or S3 |

## Disaster Recovery

In case of total data loss:

1. **Restore infrastructure**: Deploy fresh with `docker compose up -d`
2. **Restore PostgreSQL**: Use latest backup (see above)
3. **Restore Neo4j**: Use latest backup (see above)
4. **Restore files**: Unpack storage backup
5. **Verify**: Run health checks and smoke tests
6. **Monitor**: Watch for errors in logs
