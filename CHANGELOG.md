# Changelog

All notable changes to EchoTrace AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-07-11

### Stage 13 — Final Release Engineering & Documentation

#### Added

- ARCHITECTURE.md with Mermaid system diagrams (auth, AI pipeline, DB ER, deployment)
- ROADMAP.md with 3-phase development plan
- v1.0.0 version tagging across all modules

### Stage 12 — Security Hardening

#### Added

- Server-side MIME type validation via magic bytes (14 format signatures)
- Upload MIME enforcement against ALLOWED_MIME_TYPES (415 on rejection)
- Concurrent upload semaphore with configurable UPLOAD_CONCURRENCY_LIMIT
- Filename sanitization for Content-Disposition headers
- Zero-byte upload rejection

#### Security

- 🛡️ Magic byte detection prevents MIME spoofing (CWE-434)
- 🛡️ Content-Disposition header injection eliminated (CWE-79)
- 🛡️ Upload resource exhaustion guarded via semaphore (CWE-400)

### Stage 11 — Performance Optimization

#### Added

- Circuit breaker pattern for AI provider calls
- Request body size protection middleware (10MB default, 413 rejection)
- Database connection pool health monitoring (`get_pool_status()`)
- Composite indexes migration (5 indexes for workspace/project queries)
- Frontend API client retry (2 retries, exponential backoff, AbortController timeout)

#### Changed

- **N+1 elimination**: EvidenceService batch tag loading, GROUP BY stats, EXISTS tag filter
- **N+1 elimination**: InvestigationService batch counting, paginated list
- **Batch Neo4j writes**: UNWIND replaces per-item CREATE in GraphSync
- **AI job session reuse**: Shared DB sessions in background jobs
- **AI provider timeout**: `asyncio.wait_for` protection on all provider calls
- **Prepared statement cache**: SQLAlchemy `query_cache_size=500`

#### Performance

- ⚡ Evidence listing: ~50× fewer DB round-trips (N+1→1)
- ⚡ Investigation listing: ~3×N→3 queries per list
- ⚡ Graph sync: ~N× faster via batch UNWIND
- ⚡ Evidence stats: 6 queries→1 GROUP BY

### Stage 10 — Enterprise Observability & Security

#### Added

- Enterprise security headers: CSP, COOP, COEP, CORP, enhanced Permissions-Policy, HSTS preload
- CodeQL GitHub Actions workflow for security scanning
- python-multipart security update (0.0.18→0.0.31)

#### Observability

- Prometheus: 7 scrape targets, 5 rule files, 32 alert rules
- Grafana: 5 dashboards (30 panels), 3 auto-provisioned datasources
- OpenTelemetry: collector, Jaeger, Tempo, FastAPI/HTTPX/SQLAlchemy instrumentation
- Structured logging: env metadata, correlation IDs, trace/span IDs
- 11 runbooks (backend, frontend, Neo4j, PostgreSQL, crashloop, etc.)
- SRE guide, operations guide, monitoring architecture doc

#### Performance

- Redis-backed caching layer with graceful degradation
- GZip compression middleware
- 13 database indexes across 8 tables
- Tuned connection pooling (10+5)
- k6 load test suite (smoke, load, stress)
- Locust alternative load test
- Dependabot config
- Performance baselines with measurable targets

---

## [0.1.0] — 2026-07-10

### Stage 9B — Kubernetes & CI/CD Infrastructure

#### Added

- Kubernetes deployment manifests (14 files):
  - Backend and frontend deployments with services
  - PostgreSQL StatefulSet with persistent storage
  - Neo4j Enterprise StatefulSet with persistent storage
  - Ingress controller with TLS configuration
  - Horizontal Pod Autoscaler (HPA) for auto-scaling
  - Pod Disruption Budget (PDB) for high availability
  - Network policies for zero-trust networking
  - ConfigMap and Secret templates
  - ServiceAccount with RBAC
  - ClusterIssuer for Let's Encrypt TLS certificates
- GitHub Actions workflows:
  - `docker.yml`: Build, push, and scan Docker images
  - `release.yml`: Create GitHub releases with automated Docker publishing
- Production Docker Compose configuration (`docker-compose.prod.yml`)

### Stage 9A — Production Docker Infrastructure

#### Added

- Multi-stage Dockerfiles for frontend and backend
- Production Docker Compose with security hardening:
  - `no-new-privileges` security option
  - Resource limits and reservations
  - Health checks on all services
  - Non-root user execution
  - Network isolation with dedicated network
- Container security scanning pipeline via Trivy
- Docker build provenance and SBOM generation
- Frontend Dockerfile targets: `deps`, `development`, `builder`, `production`
- Backend Dockerfile targets: `dependencies`, `development`, `production`

---

## [0.0.1] — 2026-07-09

### Stage 8 — Realtime Collaboration, Observability & Production Infrastructure

#### Added

- WebSocket-based realtime collaboration system
- WebSocket connection manager with heartbeat monitoring
- Workspace invitation system with WebSocket notifications
- Notification system with real-time delivery
- Member management with role assignment endpoints
- Rate limiting middleware for API protection
- User activity tracking and feed generation
- OpenTelemetry integration for distributed tracing
- Prometheus metrics endpoint for monitoring
- Structured logging with JSON format
- Health check endpoints with service dependency status
- Graceful shutdown handling
- Exponential backoff for database reconnection

#### Changed

- Enhanced auth system with refresh token rotation
- Improved error handling throughout the API layer

### Stage 7 — Reporting, Collaboration & Enterprise UX

#### Added

- Custom report generation system with templates
- Report export functionality (PDF, CSV, JSON)
- Scheduled report generation via background tasks
- Dashboard API with workspace statistics and metrics
- Investigation management with AI-powered insights
- Evidence classification and management system
- AI analysis endpoints with LangGraph integration
- Graph analytics query endpoints

### Stage 6 — AI Engine & Knowledge Graph

#### Added

- AI agent system built on LangGraph
- LangChain integration for LLM-powered analysis
- Vector similarity search with pgvector
- Auto-tagging and classification pipelines
- Anomaly detection algorithms
- Neo4j knowledge graph with relationship mapping
- Entity resolution and deduplication
- Graph traversal and path analysis

### Stage 5 — Graph Database & Advanced Visualization

#### Added

- Neo4j Enterprise 5 integration
- Graph data models and CRUD operations
- Relationship mapping and traversal services
- Interactive graph visualization with React Flow
- 3D graph rendering with Three.js

### Stage 4 — API, Testing & Advanced Features

#### Added

- Complete REST API with versioning (v1)
- CRUD endpoints for all core entities
- RBAC with workspace-level permissions
- Member and invitation management
- Project management endpoints
- Comprehensive test suite (pytest, coverage)
- Migration system with Alembic

### Stage 3 — Authentication & Authorization

#### Added

- JWT-based authentication (access + refresh tokens)
- OAuth2 password flow with form or JSON input
- User registration with email verification
- Password management (change, reset, forgot)
- Rate limiting on authentication endpoints
- Organization and workspace management

### Stage 2 — Database Schema & Backend Foundation

#### Added

- SQLAlchemy 2.0 async ORM models
- PostgreSQL schema with migrations
- Repository pattern for data access
- Service layer for business logic
- Configuration management via Pydantic Settings

### Stage 1 — Project Scaffolding

#### Added

- Next.js 15 frontend with App Router
- FastAPI backend with modular architecture
- TailwindCSS with shadcn/ui components
- Docker Compose development environment
- CI/CD pipeline with GitHub Actions
- TypeScript type definitions and React hooks

---

## [0.0.0] — 2026-07-08

### Added

- Initial project scaffolding and repository setup
- Frontend: Next.js 15 with TypeScript and TailwindCSS
- Backend: FastAPI with Python 3.12
- Docker Compose for local development
- CI workflow with linting and testing
- Environment configuration (.env.example)

---

## Legend

- ✨ **Added** for new features
- 🔧 **Changed** for changes in existing functionality
- ⚠️ **Deprecated** for soon-to-be removed features
- ❌ **Removed** for now removed features
- 🐛 **Fixed** for any bug fixes
- 🔒 **Security** in case of vulnerabilities

---

[1.0.0]: https://github.com/prayushsinghrathore/EchoTrace-AI/releases/tag/v1.0.0
[0.1.0]: https://github.com/prayushsinghrathore/EchoTrace-AI/releases/tag/v0.1.0
[0.0.1]: https://github.com/prayushsinghrathore/EchoTrace-AI/releases/tag/v0.0.1
