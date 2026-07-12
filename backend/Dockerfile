# ═══════════════════════════════════════════════════════════════════════════════
# EchoTrace AI — Backend Dockerfile
# ═══════════════════════════════════════════════════════════════════════════════
# Multi-stage build with production hardening, OCI labels, and security
# hardening for containerized deployment.
# Targets: builder, development, production
# ═══════════════════════════════════════════════════════════════════════════════

# ── Build Arguments ──────────────────────────────────────────────────────────
ARG PYTHON_VERSION=3.12-slim

# ── Builder Stage ──────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION} AS builder

ARG PYTHON_VERSION

LABEL org.opencontainers.image.title="EchoTrace AI Backend — Builder" \
      org.opencontainers.image.description="Builder stage for EchoTrace AI backend" \
      org.opencontainers.image.vendor="EchoTrace AI"

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        python3-dev \
        && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt && \
    find /root/.local -name '*.pyc' -delete && \
    find /root/.local -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

# ── Development Stage ──────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION} AS development

ARG PYTHON_VERSION

LABEL org.opencontainers.image.title="EchoTrace AI Backend — Development" \
      org.opencontainers.image.description="Development image for EchoTrace AI backend" \
      org.opencontainers.image.vendor="EchoTrace AI"

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        netcat-openbsd \
        curl \
        && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production Stage ───────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION} AS production

ARG APP_USER=echotrace
ARG APP_UID=1001
ARG APP_GID=1001

# OCI image annotations
LABEL org.opencontainers.image.title="EchoTrace AI Backend" \
      org.opencontainers.image.description="Production-grade traceability and knowledge graph API server" \
      org.opencontainers.image.url="https://echotrace-ai.example.com" \
      org.opencontainers.image.source="https://github.com/pratyushsinghrathore/echotrace-ai" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.vendor="EchoTrace AI" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.ref.name="echotrace-backend" \
      org.opencontainers.image.base.digest="" \
      org.opencontainers.image.created="" \
      org.opencontainers.image.authors="EchoTrace AI Team"

WORKDIR /app

# Install runtime system dependencies only (no build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Create non-root user with configurable UID/GID
RUN addgroup --system --gid ${APP_GID} ${APP_USER} && \
    adduser --system --uid ${APP_UID} --gid ${APP_GID} --disabled-password --home /app --shell /bin/false ${APP_USER} && \
    mkdir -p /app/storage /app/exports /app/tmp && \
    chown -R ${APP_USER}:${APP_USER} /app

# Copy installed Python packages from builder
COPY --from=builder --chown=${APP_USER}:${APP_USER} /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code with explicit ownership
COPY --chown=${APP_USER}:${APP_USER} app/ app/
COPY --chown=${APP_USER}:${APP_USER} alembic/ alembic/
COPY --chown=${APP_USER}:${APP_USER} alembic.ini .
COPY --chown=${APP_USER}:${APP_USER} requirements.txt .

# Ensure ownership of all copied files
RUN chown -R ${APP_USER}:${APP_USER} /app

# Production entrypoint for migrations and server startup
COPY --chown=${APP_USER}:${APP_USER} entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Python runtime hardening
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

EXPOSE 8000

USER ${APP_USER}

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail --silent http://localhost:${PORT:-8000}/api/v1/live || exit 1

STOPSIGNAL SIGTERM

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--limit-max-requests", "10000", "--timeout-keep-alive", "30"]
