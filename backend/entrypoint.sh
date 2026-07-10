#!/bin/sh
# ═══════════════════════════════════════════════════════════════════════════════
# EchoTrace AI — Backend Production Entrypoint
# ═══════════════════════════════════════════════════════════════════════════════
# Production container entrypoint that:
#   1. Validates critical environment variables
#   2. Runs database migrations (alembic upgrade head)
#   3. Execs the application server with proper signal forwarding
#
# This script uses POSIX /bin/sh for maximum compatibility and uses `exec`
# so that signals (SIGTERM, SIGINT) are forwarded to the uvicorn process.
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# ── Environment Validation ─────────────────────────────────────────────────

if [ -z "${SECRET_KEY}" ]; then
    echo "ERROR: SECRET_KEY environment variable is required in production." >&2
    exit 1
fi

if [ -z "${DATABASE_URL}" ]; then
    echo "ERROR: DATABASE_URL environment variable is required in production." >&2
    exit 1
fi

# ── Database Migrations ────────────────────────────────────────────────────
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."

# ── Application Server ─────────────────────────────────────────────────────
# Use exec to replace shell with uvicorn so signals are forwarded correctly.
exec uvicorn app.main:app \
    --host "${BACKEND_HOST:-0.0.0.0}" \
    --port "${BACKEND_PORT:-8000}" \
    --workers "${UVICORN_WORKERS:-4}" \
    --limit-max-requests "${UVICORN_LIMIT_MAX_REQUESTS:-10000}" \
    --timeout-keep-alive "${UVICORN_TIMEOUT_KEEP_ALIVE:-30}"
