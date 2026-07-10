# 🤝 Contributing to EchoTrace AI

First off, thank you for considering contributing to EchoTrace AI! We value contributions from the community and want to make the process as smooth as possible.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Local Development Setup](#local-development-setup)
- [Development Workflow](#development-workflow)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Commit Conventions](#commit-conventions)
- [Branch Naming](#branch-naming)
- [Pull Request Process](#pull-request-process)
- [Pull Request Checklist](#pull-request-checklist)
- [Issue Templates](#issue-templates)
- [Questions & Support](#questions--support)

---

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow. Please be respectful, constructive, and professional in all interactions.

**Our standards:**
- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

---

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/EchoTrace-AI.git
   cd EchoTrace-AI
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/prayushsinghrathore/EchoTrace-AI.git
   ```
4. **Create a branch** for your work (see [Branch Naming](#branch-naming))

---

## Local Development Setup

### Prerequisites

- **Node.js** >= 20.x
- **Python** >= 3.12
- **Docker** & **Docker Compose** v2.20+
- **PostgreSQL** 16 (if not using Docker)
- **Neo4j** 5 (if not using Docker)

### Option 1: Docker (Recommended)

```bash
# Copy environment file
cp .env.example .env

# Start all services
docker compose up --build -d

# Services available at:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - PostgreSQL: localhost:5432
# - Neo4j Browser: http://localhost:7474
```

### Option 2: Local (Manual)

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov ruff mypy bandit

# Set up environment
export DATABASE_URL=postgresql+asyncpg://echotrace:echotrace_secret@localhost:5432/echotrace
export SECRET_KEY=dev-secret-key

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## Development Workflow

1. **Sync your fork** with upstream:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create a feature branch** (see [Branch Naming](#branch-naming))

3. **Make your changes** following our [Code Style](#code-style)

4. **Write or update tests** for your changes

5. **Run tests** to verify everything passes

6. **Commit your changes** following [Commit Conventions](#commit-conventions)

7. **Push your branch** and open a Pull Request

---

## Running Tests

### Backend Tests

```bash
cd backend

# Run all tests with coverage
pytest --cov=app --cov-report=term-missing -v

# Run specific test file
pytest tests/test_auth.py -v

# Run tests matching keyword
pytest -k "workspace" -v
```

### Linting & Type Checking

```bash
# Backend
cd backend
ruff check .                    # Lint
ruff format . --check           # Format check
mypy app --ignore-missing-imports  # Type checking
bandit -r app/ -ll              # Security scan

# Frontend
cd frontend
npm run lint                    # ESLint
npm run type-check              # TypeScript
```

### Docker Build Verification

```bash
# Build production images locally
docker compose -f docker-compose.prod.yml build

# Verify frontend Docker build
docker build -t echotrace-frontend:test --target production ./frontend/
```

---

## Code Style

### Python

- Follow **PEP 8** conventions
- Use **type hints** for all function signatures and public methods
- Import ordering: standard library → third-party → local (handled by ruff)
- Use **async/await** for I/O-bound operations
- Maximum line length: **100 characters**
- Use **double quotes** for strings
- Docstrings follow **Google style** or reStructuredText

### TypeScript / React

- Follow the existing component patterns in the codebase
- Use **TypeScript** — avoid `any` where possible
- Use **functional components** with hooks
- Use **named exports** for components
- Component files use **PascalCase**, utilities use **camelCase**
- Use TailwindCSS for styling

### General

- Keep functions small and focused (single responsibility)
- Write meaningful comments for non-obvious logic
- Avoid TODO/FIXME comments in committed code
- Follow the principle of least surprise

---

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/) for all commit messages:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `style` | Code style changes (formatting, missing semicolons) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `build` | Build system or external dependency changes |
| `ci` | CI/CD configuration changes |
| `chore` | Other changes that don't modify source or tests |

### Scope Examples

- `frontend`, `backend`, `docker`, `k8s`, `docs`, `ci`, `auth`, `api`, `graph`, `deps`

### Examples

```
feat(auth): add MFA TOTP verification endpoint
fix(docker): resolve missing public directory in production build
docs(api): update WebSocket connection documentation
ci: add Trivy vulnerability scanning to Docker workflow
refactor(backend): consolidate repository pattern implementations
```

---

## Branch Naming

Use descriptive branch names with a consistent pattern:

```
<type>/<short-description>
```

### Examples

| Branch Name | Purpose |
|-------------|---------|
| `feat/investigation-templates` | New feature |
| `fix/auth-refresh-token-bug` | Bug fix |
| `docs/api-websocket-guide` | Documentation |
| `refactor/consolidate-repos` | Refactoring |
| `chore/update-dependencies` | Maintenance |

---

## Pull Request Process

1. **Create a draft PR** early to signal you're working on something
2. **Ensure all CI checks pass** before requesting review
3. **Request review** from at least one maintainer
4. **Address review feedback** with additional commits
5. **Squash commits** if requested before merge
6. **Merge** after approval

### PR Title Format

Follow the same convention as commit messages:

```
<type>(<scope>): <description>
```

---

## Pull Request Checklist

Before submitting your PR, verify the following:

- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] No debugging code, console.log, or commented-out code
- [ ] Tests added or updated for all changes
- [ ] All existing tests pass
- [ ] New endpoints include proper validation and error handling
- [ ] API changes are documented (OpenAPI/Swagger annotations)
- [ ] No new TODOs or FIXMEs introduced
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
- [ ] Branch is up to date with `main`
- [ ] No merge conflicts
- [ ] Breaking changes are clearly noted in the PR description

### Security Checklist

- [ ] No secrets, tokens, or credentials in code
- [ ] Input validation on all user-facing endpoints
- [ ] Auth checks on protected endpoints
- [ ] SQL injection prevention (use parameterized queries)
- [ ] XSS prevention (use framework-safe rendering)

---

## Issue Templates

When creating issues, please use the appropriate template:

- [🐛 Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) — Report a bug or unexpected behavior
- [✨ Feature Request](.github/ISSUE_TEMPLATE/feature_request.md) — Suggest a new feature or enhancement
- [🔒 Security Report](.github/ISSUE_TEMPLATE/security_report.md) — Report a security vulnerability
- [📖 Documentation Issue](.github/ISSUE_TEMPLATE/documentation_issue.md) — Report docs issues or suggest improvements

---

## Questions & Support

- **GitHub Issues**: For bug reports and feature requests
- **Discussions**: For questions and general discussion

---

Thank you for contributing to EchoTrace AI! 🚀
