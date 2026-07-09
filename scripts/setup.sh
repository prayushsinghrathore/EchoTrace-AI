#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# EchoTrace AI — Development Setup Script
# ═══════════════════════════════════════════════════════════════════════════════
# Sets up the full development environment on a fresh clone.
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "═══ EchoTrace AI — Setup ═══"
echo ""

# ── Configuration ────────────────────────────────────────────────────────────
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"

# ── 1. Environment File ──────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    echo "◆ Creating .env from .env.example..."
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "  ✓ .env created — edit it with your configuration values."
else
    echo "◆ .env already exists, skipping."
fi

# ── 2. Backend Setup ─────────────────────────────────────────────────────────
echo ""
echo "◆ Setting up backend..."
cd "$PROJECT_DIR/backend"

if [ ! -d ".venv" ]; then
    echo "  Creating Python virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "  Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  ✓ Backend dependencies installed."

# ── 3. Frontend Setup ────────────────────────────────────────────────────────
echo ""
echo "◆ Setting up frontend..."
cd "$PROJECT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    echo "  Installing Node.js dependencies..."
    npm install
    echo "  ✓ Frontend dependencies installed."
else
    echo "  node_modules exists, skipping install."
fi

# ── 4. Docker Check ──────────────────────────────────────────────────────────
echo ""
echo "◆ Checking Docker..."
if command -v docker &> /dev/null; then
    echo "  ✓ Docker found: $(docker --version)"
    if docker compose version &> /dev/null; then
        echo "  ✓ Docker Compose found: $(docker compose version)"
    else
        echo "  ⚠ docker compose not found. Install Docker Compose v2."
    fi
else
    echo "  ⚠ Docker not found. Install Docker to run the full stack."
fi

# ── 5. Git Hooks (pre-commit) ────────────────────────────────────────────────
echo ""
echo "◆ Setting up pre-commit hooks..."
cd "$PROJECT_DIR/backend"
if pip show pre-commit &> /dev/null; then
    pre-commit install 2>/dev/null || true
    echo "  ✓ pre-commit hooks installed."
else
    echo "  ⚠ pre-commit not available."
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "═══ Setup Complete ═══"
echo ""
echo "Next steps:"
echo "  1. Edit $ENV_FILE with your configuration"
echo "  2. Start infrastructure: docker compose up -d postgres neo4j"
echo "  3. Run migrations:    cd backend && alembic upgrade head"
echo "  4. Start backend:     cd backend && uvicorn app.main:app --reload"
echo "  5. Start frontend:    cd frontend && npm run dev"
echo ""
echo "Backend API:  http://localhost:8000"
echo "API Docs:     http://localhost:8000/api/v1/docs"
echo "Frontend:     http://localhost:3000"
echo ""
