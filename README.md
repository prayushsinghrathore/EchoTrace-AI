<div align="center">
  <h1>🔍 EchoTrace AI</h1>
  <p><strong>Production-Grade Traceability & Knowledge Graph Platform</strong></p>
  <p>
    <img src="https://img.shields.io/badge/status-development-yellow" alt="Status" />
    <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python" />
    <img src="https://img.shields.io/badge/node-20-green" alt="Node" />
    <img src="https://img.shields.io/badge/next.js-15-black" alt="Next.js" />
    <img src="https://img.shields.io/badge/fastapi-latest-teal" alt="FastAPI" />
    <img src="https://img.shields.io/badge/license-MIT-blue" alt="License" />
  </p>
</div>

---

## 📋 Overview

EchoTrace AI is a production-grade SaaS platform that combines **vector knowledge graphs**, **AI-powered traceability**, and **interactive visualization** to help organizations understand, trace, and analyze complex relationships across their data.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 15)                  │
│  shadcn/ui  ·  Framer Motion  ·  React Flow  ·  ThreeJS │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTP/REST
┌──────────────────▼──────────────────────────────────────┐
│                  Backend (FastAPI)                        │
│        Services  ·  Repositories  ·  LangChain           │
└───────┬────────────────────────────┬────────────────────┘
        │                            │
┌───────▼────────┐          ┌───────▼────────┐
│   PostgreSQL    │          │     Neo4j       │
│  (Relational)   │          │  (Graph Store)  │
└────────────────┘          └────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** >= 20.x
- **Python** >= 3.12
- **Docker** & **Docker Compose** v2
- **Poetry** or **pip** (Python package manager)

### 1. Clone & Setup

```bash
git clone <repo-url> echotrace-ai
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

## 🏗️ Project Structure

```
echotrace-ai/
│
├── frontend/                        # Next.js 15 Application
│   ├── app/                         # App Router pages & layouts
│   ├── components/
│   │   ├── ui/                      # shadcn/ui components
│   │   ├── shared/                  # Shared UI components
│   │   └── features/                # Feature-specific components
│   ├── lib/                         # Utility functions
│   ├── hooks/                       # Custom React hooks
│   ├── types/                       # TypeScript type definitions
│   └── config/                      # Frontend configuration
│
├── backend/                         # FastAPI Application
│   ├── app/
│   │   ├── api/                     # API routes & dependencies
│   │   │   └── v1/                  # API version 1
│   │   ├── core/                    # Config, logging, security
│   │   ├── db/                      # Database sessions & base
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic schemas
│   │   ├── services/                # Business logic layer
│   │   ├── repositories/            # Data access layer
│   │   └── graph/                   # Neo4j integration
│   ├── alembic/                     # Database migrations
│   └── tests/                       # Test suite
│
├── docker/                          # Docker auxiliary files
├── .github/workflows/               # CI/CD pipelines
├── docker-compose.yml               # Service orchestration
└── README.md
```

---

## 🧰 Tech Stack

| Layer       | Technology                          |
|------------|-------------------------------------|
| **Frontend**  | Next.js 15, TypeScript, TailwindCSS, shadcn/ui |
| **Animation** | Framer Motion                       |
| **Visualization** | React Flow, Three.js            |
| **Backend**   | FastAPI, Python 3.12, SQLAlchemy    |
| **Database**  | PostgreSQL 16                       |
| **Graph DB**  | Neo4j 5 Enterprise                  |
| **AI/Agents** | LangGraph, LangChain (Stage 3+)     |
| **Infra**     | Docker, Docker Compose, GitHub Actions |

---

## 🔧 Configuration

Configuration is managed through environment variables. See `.env.example` for all available options.

### Key Variables

| Variable              | Description                  | Default                 |
|----------------------|------------------------------|------------------------|
| `PROJECT_NAME`       | Application name            | EchoTrace AI           |
| `ENVIRONMENT`        | deployment environment       | development            |
| `DATABASE_URL`       | PostgreSQL connection string | postgresql+asyncpg://… |
| `NEO4J_URI`          | Neo4j connection string      | bolt://localhost:7687  |
| `SECRET_KEY`         | JWT/encryption secret        | (change in production) |

---

## 📚 API Documentation

When running, API docs are automatically available:

| Documentation | URL                         |
|--------------|-----------------------------|
| Swagger UI   | http://localhost:8000/docs  |
| ReDoc        | http://localhost:8000/redoc |

### Health Check

```bash
curl http://localhost:8000/api/v1/health
# Response: {"status":"healthy","version":"0.1.0","timestamp":"..."}
```

---

## 🧪 Testing

```bash
# Backend tests
cd backend && pytest --cov=app --cov-report=term-missing

# Frontend tests (when configured)
cd frontend && npm run test

# Linting
cd backend && ruff check .
cd frontend && npm run lint
```

---

## 🚢 Deployment

### Build for Production

```bash
# Build all images
docker compose -f docker-compose.yml build

# Start in production mode
ENVIRONMENT=production docker compose up -d
```

---

## 🤝 Contributing

1. Branch from `main` for feature work
2. Write tests for new functionality
3. Ensure CI passes before merging
4. Follow existing code style and conventions

---

## 📄 License

MIT © EchoTrace AI
