# Changelog

All notable changes to EchoTrace AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Enterprise release finalization
- SECURITY.md with vulnerability reporting and security best practices
- CONTRIBUTING.md with comprehensive contributor guide
- RELEASE.md with versioning, release checklist, and rollback procedures
- CHANGELOG.md following Keep a Changelog format
- GitHub issue templates (bug report, feature request, security report, documentation issue)
- Pull request template with checklists for code quality, testing, security
- CODEOWNERS file for repository governance
- MIT LICENSE file

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

[unreleased]: https://github.com/prayushsinghrathore/EchoTrace-AI/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/prayushsinghrathore/EchoTrace-AI/releases/tag/v0.1.0
[0.0.1]: https://github.com/prayushsinghrathore/EchoTrace-AI/releases/tag/v0.0.1
