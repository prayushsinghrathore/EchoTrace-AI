<!-- Capsule Render Banner -->

<p align="center">
<img src="YOUR_BANNER_URL" width="100%">
</p>
<p align="center">

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=30&pause=1000&color=00E5FF&center=true&vCenter=true&width=900&lines=AI-Powered+Software+Intelligence;Knowledge+Graph+Visualization;Semantic+Repository+Analysis;Production-Ready+FastAPI+Platform;Built+with+OpenAI+%2B+Neo4j"/>

</p>
div align="center">
  <h1>🔍 EchoTrace AI</h1>
  <p><strong>Production-Grade Traceability & Knowledge Graph Platform</strong></p>
  <p>
    <a href="https://github.com/prayushsinghrathore/EchoTrace-AI/actions"><img src="https://img.shields.io/github/actions/workflow/status/prayushsinghrathore/EchoTrace-AI/ci.yml?branch=main&label=CI&logo=github" alt="CI"/></a>
    <a href="https://github.com/prayushsinghrathore/EchoTrace-AI/actions"><img src="https://img.shields.io/github/actions/workflow/status/prayushsinghrathore/EchoTrace-AI/docker.yml?branch=main&label=Docker&logo=docker" alt="Docker"/></a>
    <a href="https://github.com/prayushsinghrathore/EchoTrace-AI/releases"><img src="https://img.shields.io/github/v/release/prayushsinghrathore/EchoTrace-AI?logo=semver" alt="Release"/></a>
    <img src="https://img.shields.io/badge/python-3.12-blue?logo=python" alt="Python" />
    <img src="https://img.shields.io/badge/node-20-green?logo=node.js" alt="Node" />
    <img src="https://img.shields.io/badge/next.js-15-black?logo=next.js" alt="Next.js" />
    <img src="https://img.shields.io/badge/fastapi-latest-teal?logo=fastapi" alt="FastAPI" />
    <img src="https://img.shields.io/badge/license-MIT-blue" alt="License" />
    <img src="https://img.shields.io/badge/code_style-ruff-purple" alt="Ruff" />
    <img src="https://img.shields.io/badge/Kubernetes-✓-blue?logo=kubernetes" alt="Kubernetes" />
  </p>
</div>

---

## 📋 Overview

EchoTrace AI is a **production-grade SaaS platform** that combines **vector knowledge graphs**, **AI-powered traceability**, and **interactive visualization** to help organizations understand, trace, and analyze complex relationships across their data.

Built with a modern stack — Next.js 15, FastAPI, PostgreSQL, and Neo4j — it delivers real-time collaboration, AI-driven investigation workflows, and enterprise-grade observability.

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js 15)                          │
│    shadcn/ui  ·  Custom Graph        │
└────────────────────┬──────────────────────┬───────────────────────┘
                     │ HTTP/REST            │ WebSocket
┌────────────────────▼──────────────────────▼───────────────────────┐
│                       Backend (FastAPI)                             │
│          Services  ·  Repositories  ·  AI Providers  ·  Asyncio       │
└───────┬────────────────────────────┬───────────────────────────────┘
        │                            │
┌───────▼────────┐          ┌───────▼────────┐
│   PostgreSQL    │          │    Neo4j 5      │
│  (Relational)   │          │  (Graph Store)  │
└────────────────┘          └────────────────┘
```

---


## ✨ Features

| Category | Features |
|----------|----------|
| **🔐 Authentication** | JWT with refresh tokens, OAuth2, password reset, rate limiting |
| **🏢 Organizations** | Multi-tenant workspaces, role-based access (RBAC), member management |
| **🔍 Investigations** | Create, track, and manage traceability investigations with full CRUD |
| **📊 Dashboard** | Real-time metrics, activity feeds, workspace statistics |
| **🤖 AI Engine** | LangGraph-powered agents, vector similarity search, auto-tagging, anomaly detection |
| **🧠 Knowledge Graph** | Neo4j-backed graph visualization, relationship mapping, entity resolution |
| **📈 Reporting** | Custom reports, exports (CSV/JSON), templates |
| **🔗 Evidence** | Attach and manage evidence items, file uploads, classification |
| **💬 Realtime** | WebSocket-based collaboration, live updates, notifications |
| **📡 Observability** | OpenTelemetry, Prometheus metrics, structured logging, health checks |
| **🔒 Security** | CORS, helmet headers, input validation, SQL injection protection, rate limiting |

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** >= 20.x
- **Python** >= 3.12
- **Docker** & **Docker Compose** v2.20+

### 1. Clone & Setup

```bash
git clone https://github.com/prayushsinghrathore/EchoTrace-AI.git echotrace-ai
cd echotrace-ai

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 2. Run with Docker (Recommended)

```bash
# Build and start all services
docker compose up --build -d

# Check service health
curl http://localhost:8000/api/v1/health
```

### 3. Run Locally (Development)

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Visit **http://localhost:3000** for the frontend and **http://localhost:8000/docs** for the API docs.

---

## 🏗️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 15, TypeScript, TailwindCSS | SSR React application |
| **UI** | shadcn/ui, Radix UI, Lucide Icons | Accessible component library |
| **State** | React Context, React Query | Client state & server cache |
| **Animation** | CSS Transitions | UI transitions & micro-interactions |
| **Visualization** | Custom Graph | Graph visualization |
| **Backend** | FastAPI, Python 3.12 | High-performance REST API |
| **ORM** | SQLAlchemy 2.0 (async) | Database access layer |
| **Migrations** | Alembic | Schema versioning |
| **Validation** | Pydantic v2 | Request/response validation |
| **Auth** | JWT, OAuth2, passlib, python-jose | Authentication & authorization |
| **AI/Agents** | LangGraph, LangChain | AI-powered investigations |
| **Vector Store** | pgvector | Similarity search on embeddings |
| **Database** | PostgreSQL 16 | Primary data store |
| **Graph DB** | Neo4j 5 Enterprise | Knowledge graph storage |
| **Realtime** | WebSockets (FastAPI) | Live collaboration & updates |
| **Task Queue** | Asyncio, background tasks | Async job processing |
| **Observability** | OpenTelemetry, Prometheus | Metrics & tracing |
| **Monitoring** | Grafana | Dashboard & visualization |
| **Container** | Docker, Docker Compose | Local & production deployment |
| **Orchestration** | Kubernetes | Production container orchestration |
| **CI/CD** | GitHub Actions | Automated builds & deployments |
| **Security** | Trivy, Bandit, Helmet | Vulnerability scanning & hardening |

---

## 📑 Table of Contents

- Features
- Architecture
- Screenshots
- Installation
- API
- Deployment
- Roadmap
- Contributing

---  

## 🏗️ Project Structure

```
echotrace-ai/
│
├── frontend/                        # Next.js 15 Application
│   ├── app/                         # App Router pages & layouts
│   ├── components/                  # React components
│   │   ├── ui/                      # shadcn/ui primitives
│   │   ├── shared/                  # Shared components
│   │   └── features/                # Feature-specific components
│   ├── lib/                         # Utility functions & helpers
│   ├── hooks/                       # Custom React hooks
│   ├── types/                       # TypeScript definitions
│   ├── config/                      # Frontend configuration
│   └── Dockerfile                   # Multi-stage build
│
├── backend/                         # FastAPI Application
│   ├── app/
│   │   ├── api/                     # API routes & dependencies
│   │   │   └── v1/                  # Versioned API (v1)
│   │   ├── core/                    # Config, logging, security
│   │   ├── db/                      # Database sessions & base
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic request/response
│   │   ├── services/                # Business logic layer
│   │   ├── repositories/            # Data access layer
│   │   └── graph/                   # Neo4j integration
│   ├── alembic/                     # Database migrations
│   ├── tests/                       # Test suite (247 tests)
│   └── Dockerfile                   # Multi-stage build
│
├── k8s/                             # Kubernetes manifests
│   ├── backend.yaml                 # Backend deployment & service
│   ├── frontend.yaml                # Frontend deployment & service
│   ├── postgres.yaml                # PostgreSQL statefulset
│   ├── neo4j.yaml                   # Neo4j statefulset
│   ├── ingress.yaml                 # Ingress controller
│   ├── hpa.yaml                     # Horizontal pod autoscaler
│   ├── pdb.yaml                     # Pod disruption budget
│   └── ...                          # Network policies, configs, secrets
│
├── .github/workflows/               # CI/CD pipelines
│   ├── ci.yml                       # Lint, test, build, security scan
│   ├── docker.yml                   # Docker build & push
│   └── release.yml                  # GitHub release & publishing
│
├── docs/                            # Documentation
│   ├── docker-deployment.md         # Docker deployment guide
│   └── kubernetes.md                # K8s deployment guide
│
├── docker/                          # Docker auxiliary files
├── monitoring/                      # Prometheus/Grafana configs
├── scripts/                         # Utility scripts
├── terraform/                       # Infrastructure as code
├── docker-compose.yml               # Development orchestration
├── docker-compose.prod.yml          # Production orchestration
└── README.md
```

---

## 🔧 Configuration

Configuration is managed through environment variables. See [`.env.example`](.env.example) for all available options.

### Key Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_NAME` | Application name | EchoTrace AI |
| `ENVIRONMENT` | Deployment environment | development |
| `DATABASE_URL` | PostgreSQL connection string | postgresql+asyncpg://… |
| `NEO4J_URI` | Neo4j connection string | bolt://localhost:7687 |
| `SECRET_KEY` | JWT/encryption secret | (change in production) |

---

## 📚 API Documentation

When running, interactive API documentation is automatically available:

| Documentation | URL |
|--------------|-----|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

### API Endpoints Summary

| Prefix | Description |
|--------|-------------|
| `/api/v1/health` | Health checks & readiness probes |
| `/api/v1/auth` | Authentication (register, login, refresh, logout, password reset) |
| `/api/v1/users` | User profiles & management |
| `/api/v1/organizations` | Organization CRUD & membership |
| `/api/v1/workspaces` | Workspace CRUD, members, invitations |
| `/api/v1/projects` | Project management |
| `/api/v1/dashboard` | Dashboard metrics & statistics |
| `/api/v1/evidence` | Evidence items, classification, uploads |
| `/api/v1/investigations` | Investigation workflows |
| `/api/v1/ai` | AI engine queries & analysis |
| `/api/v1/reports` | Report generation & exports |
| WebSocket | Real-time collaboration & notifications |

### Health Check

```bash
curl http://localhost:8000/api/v1/health
# Response: {"status":"healthy","version":"0.1.0","timestamp":"..."}
```

---

## 🧪 Testing

### Backend

```bash
cd backend

# Run all tests with coverage
pytest --cov=app --cov-report=term-missing -v

# Run specific test file
pytest tests/test_auth.py -v

# Lint & type checking
ruff check .
mypy app --ignore-missing-imports

# Security scan
bandit -r app/ -ll
```

### Frontend

```bash
cd frontend

# Lint & type checking
npm run lint
npm run type-check

# Build verification
npm run build
```

---

## 🚢 Deployment

### Docker (Production)

```bash
# Build and start production services
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

See [Docker Deployment Guide](docs/docker-deployment.md) for detailed instructions.

### Kubernetes

```bash
# Apply infrastructure components
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/

# Check rollout status
kubectl rollout status deployment/echotrace-backend -n echotrace
kubectl rollout status deployment/echotrace-frontend -n echotrace
```

See [Kubernetes Deployment Guide](docs/kubernetes.md) for detailed instructions.

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

- 📝 [Contributing Guide](CONTRIBUTING.md)
- 🐛 [Bug Reports](.github/ISSUE_TEMPLATE/bug_report.md)
- ✨ [Feature Requests](.github/ISSUE_TEMPLATE/feature_request.md)
- 🔒 [Security Policy](SECURITY.md)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 📊 Project Metrics

| Metric | Value |
|--------|-------|
| REST API Endpoints | 111+ |
| WebSocket Channels | 1 |
| Backend Tests | 247 |
| Python Files | 106 |
| TypeScript Files | 53 |
| Kubernetes Manifests | 14 |
| CI/CD Workflows | 4 |
| Docker Stages | Multi-stage (deps, dev, builder, production) |
| Code Coverage | Comprehensive (pytest with coverage) |
| Security Scanning | Trivy, Bandit, GitHub Advanced Security, CodeQL |

---

## 🙏 Acknowledgments

Built with modern open-source tools and frameworks. Special thanks to the FastAPI, Next.js, Neo4j, and LangChain communities.

---

