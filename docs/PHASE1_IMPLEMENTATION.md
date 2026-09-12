# Phase 1 Implementation

Phase 1 makes the application safe to run beyond a single API process.

## Durable jobs

AI and export requests are persisted as `queued` jobs in PostgreSQL. The API
only validates and enqueues work. `python -m app.worker` claims jobs using
row-level locking, records leases and attempts, retries failures with backoff,
and recovers stale leases after a worker crash.

Run a worker alongside the API in development:

```bash
docker compose up --build
```

The production Compose and Kubernetes manifests include separate worker
processes. Multiple workers may run concurrently without claiming the same
job.

## Redis

Redis is enabled in Compose and Kubernetes. AI result caching uses Redis when
enabled and falls back to the local LRU cache if Redis is unavailable. This
keeps development resilient while allowing shared cache behavior in scaled
deployments.

## Storage

Evidence and generated exports use the provider factory. `local` is intended
for development. `s3` supports AWS S3 and S3-compatible services through
`STORAGE_S3_ENDPOINT`, with the same interface for upload, download, delete,
existence, and size checks.

## Email

Password reset and workspace invitation messages use the email service. The
`console` provider is safe for local development; production should use
`EMAIL_PROVIDER=smtp` with SMTP credentials supplied through secrets.

## Required production checks

- Configure Redis persistence and backups.
- Configure S3-compatible object storage and lifecycle policies.
- Configure SMTP credentials and verify delivery from a staging environment.
- Run database migrations before starting API and worker processes.
- Monitor queued, running, failed, and stale jobs.
