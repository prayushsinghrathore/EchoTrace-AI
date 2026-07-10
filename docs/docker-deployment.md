# EchoTrace AI — Docker Production Deployment Guide

This document describes how to build and deploy EchoTrace AI in a production
environment using Docker and the accompanying production Compose file.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Production Compose Configuration](#production-compose-configuration)
- [Environment Configuration](#environment-configuration)
- [Multi-Stage Build Targets](#multi-stage-build-targets)
- [Health Checks](#health-checks)
- [Security Hardening](#security-hardening)
- [Resource Management](#resource-management)
- [Operational Guide](#operational-guide)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Docker Engine 24+ with BuildKit support
- Docker Compose v2.20+
- A `.env.prod` file with production secrets (see below)

---

## Quick Start

```bash
# 1. Clone the repository
git clone <repository-url> echotrace-ai
cd echotrace-ai

# 2. Create production environment file
cp .env.example .env.prod
# Edit .env.prod — set all secrets (see environment section)

# 3. Build and start all services
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 4. Verify deployment
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/api/v1/live
```

---

## Production Compose Configuration

Use the production Compose file instead of the default `docker-compose.yml`:

```bash
# Start all services
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop all services
docker compose -f docker-compose.prod.yml down

# Stop and remove volumes (destructive)
docker compose -f docker-compose.prod.yml down -v
```

### Differences from development Compose

| Feature               | Development             | Production                        |
|-----------------------|-------------------------|-----------------------------------|
| Build target          | `development`           | `production`                      |
| Code mounting         | Bind mounts (live sync) | No mounts (immutable image)       |
| Restart policy        | `unless-stopped`        | `always`                          |
| Security              | Minimal                 | `no-new-privileges`, `cap_drop`   |
| Init                  | No init process         | `init: true` (proper reaping)     |
| Resource limits       | None                    | CPU/memory limits                 |
| Port binding          | `0.0.0.0`               | `127.0.0.1` (localhost only)      |
| Environment           | Defaults with warnings  | Required secrets fail at startup   |

---

## Environment Configuration

Create a `.env.prod` file by copying `.env.example` and overriding every value.
At minimum, the following **must** be set to strong, unique values:

```bash
# ── Required Secrets ─────────────────────────────────────────────────────────
SECRET_KEY=<generate with: openssl rand -hex 32>
POSTGRES_PASSWORD=<generate with: openssl rand -hex 32>
NEO4J_PASSWORD=<generate with: openssl rand -hex 32>

# ── Environment ──────────────────────────────────────────────────────────────
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# ── CORS (set to your frontend domain) ────────────────────────────────────────
BACKEND_CORS_ORIGINS=["https://your-frontend-domain.com"]

# ── AI Provider (optional, set API key for your provider) ─────────────────────
# OPENAI_API_KEY=<your-openai-api-key>
# OPENROUTER_API_KEY=<your-openrouter-api-key>
```

> **Security note:** Never store secrets in the Compose file itself. Always use
> a `.env` file or Docker secrets (Docker Swarm mode). The production Compose
> uses the `:?` parameter expansion syntax which fails at startup if required
> variables are unset.

---

## Multi-Stage Build Targets

### Backend (backend/Dockerfile)

| Target       | Purpose                          | Includes              |
|--------------|----------------------------------|-----------------------|
| `builder`    | Compile dependencies             | gcc, libpq-dev        |
| `development`| Hot-reload development server    | Full source, netcat   |
| `production` | Hardened production image        | Minimal runtime deps  |

Build a specific target:

```bash
# Production image
docker build -t echotrace-backend:latest --target production backend/

# Development image
docker build -t echotrace-backend:dev --target development backend/
```

### Production stage features
- **Non-root user** (`echotrace`, UID 1001) with no shell access
- **Read-only root filesystem** compatible (writable paths: `/app/tmp`, `/app/storage`, `/app/exports`)
- **OCI labels** for image metadata and provenance tracking
- **Health check** against `/api/v1/live` endpoint
- **Entrypoint script** runs database migrations before app startup

### Frontend (frontend/Dockerfile)

| Target       | Purpose                          | Includes              |
|--------------|----------------------------------|-----------------------|
| `deps`       | Install npm dependencies         | node_modules          |
| `development`| Hot-reload dev server            | Full source           |
| `builder`    | Production build                 | Compiled output       |
| `production` | Hardened production image        | Standalone output only|

```bash
# Production image
docker build -t echotrace-frontend:latest --target production frontend/
```

### Production stage features
- **Next.js standalone output** — only the compiled runtime is copied, no source
- **Non-root user** (`nextjs`, UID 1001)
- **OCI labels** for image metadata
- **Health check** against the root page
- **Telemetry disabled** (`NEXT_TELEMETRY_DISABLED=1`)

---

## Health Checks

All services define Docker health checks:

| Service   | Endpoint                          | Interval | Start Period |
|-----------|-----------------------------------|----------|-------------|
| PostgreSQL| `pg_isready`                      | 10s      | 30s         |
| Neo4j     | `cypher-shell RETURN 1`           | 15s      | 60s         |
| Backend   | `GET /api/v1/live`                | 30s      | 40s         |
| Frontend  | `GET /`                           | 30s      | 30s         |

The backend depends on both databases being healthy before starting. The
frontend depends on the backend (but does not wait for health — it retries
on the client side).

Check container health:

```bash
docker inspect --format='{{json .State.Health}}' echotrace-backend
```

---

## Security Hardening

### Container-level protections (docker-compose.prod.yml)
- **`init: true`** — an init process (tini) runs as PID 1 to properly reap
  zombie processes and forward signals
- **`no-new-privileges:true`** — prevents privilege escalation via setuid/setgid
  binaries
- **`cap_drop: ALL`** — removes all Linux capabilities from application
  containers
- **Ports bound to `127.0.0.1`** — services are not exposed on public
  interfaces without a reverse proxy

### Image-level protections (Dockerfile)
- **Non-root user** — application processes never run as root
- **`PYTHONDONTWRITEBYTECODE=1`** — prevents writing .pyc files
- **`PYTHONHASHSEED=random`** — enables hash randomization
- **`PYTHONUNBUFFERED=1`** — ensures log output isn't buffered
- **`PIP_NO_CACHE_DIR=1`** — no pip cache in production images
- **`STOPSIGNAL SIGTERM`** — ensures uvicorn receives graceful shutdown signal
- **System packages pinned** — `--no-install-recommends` avoids unnecessary
  packages

### Recommended external security measures
- Run behind a reverse proxy (nginx, Caddy, Traefik) for TLS termination
- Use Docker Content Trust for image signing
- Scan images with Trivy or Snyk before deployment
- Use Docker Swarm secrets or HashiCorp Vault for secret management
- Enable Docker's user namespace remapping (`/etc/docker/daemon.json`)

---

## Resource Management

Resources are configured per service in `docker-compose.prod.yml`:

| Service   | CPU Limit | Memory Limit | CPU Reserve | Memory Reserve |
|-----------|-----------|-------------|-------------|---------------|
| PostgreSQL| 1.0       | 512 MB      | 0.25        | 256 MB        |
| Neo4j     | 2.0       | 2 GB        | 0.5         | 1 GB          |
| Backend   | 2.0       | 1 GB        | 0.5         | 512 MB        |
| Frontend  | 1.0       | 512 MB      | 0.25        | 256 MB        |

Adjust these values based on your workload and host capacity. The `deploy`
section is used by Docker Swarm and `docker compose` (v2) for resource
enforcement.

---

## Operational Guide

### Viewing logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Single service
docker compose -f docker-compose.prod.yml logs -f backend

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```

### Restarting a service

```bash
docker compose -f docker-compose.prod.yml restart backend
```

### Updating a service

```bash
# Rebuild and recreate without downtime (uses new image if tag changed)
docker compose -f docker-compose.prod.yml up -d --no-deps --build backend
```

### Running migrations manually

```bash
# Entrypoint runs migrations automatically on startup.
# To run manually:
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Checking database connectivity

```bash
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U echotrace
```

---

## Troubleshooting

### Container exits immediately

Check logs:

```bash
docker compose -f docker-compose.prod.yml logs backend
```

Common causes:
- Missing `SECRET_KEY` environment variable
- Database unreachable (check `depends_on` and health check status)
- Migration failure (check Alembic configuration)

### Database connection refused

```bash
# Verify database is healthy
docker inspect --format='{{json .State.Health.Status}}' echotrace-postgres

# Check database logs
docker compose -f docker-compose.prod.yml logs postgres
```

### Build fails

```bash
# Clear Docker BuildKit cache
docker builder prune -f

# Rebuild with verbose output
docker compose -f docker-compose.prod.yml build --no-cache
```

### Performance tuning

If the backend is CPU-bound:
- Increase `UVICORN_WORKERS` environment variable (default: 4)
- Increase Neo4j heap size via `NEO4J_dbms_memory_heap_max__size`
- Adjust database pool settings (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`)

### Security audit checklist

- [ ] `SECRET_KEY` is at least 32 characters and randomly generated
- [ ] All database passwords are randomly generated and rotated
- [ ] Only the reverse proxy port (80/443) is publicly exposed
- [ ] Docker daemon is configured with user namespace remapping
- [ ] Images are scanned for vulnerabilities before deployment
- [ ] `docker compose` is running with `--env-file .env.prod`
- [ ] Health checks are passing on all services
- [ ] Logging driver is configured with rotation limits
