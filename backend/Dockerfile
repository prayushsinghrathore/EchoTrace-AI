# ═══════════════════════════════════════════════════════════════════════════════
# EchoTrace AI — Backend Dockerfile
# ═══════════════════════════════════════════════════════════════════════════════
# Multi-stage build for production optimization.
# ═══════════════════════════════════════════════════════════════════════════════

# ── Build Stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        python3-dev \
        && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Development Stage ───────────────────────────────────────────────────────
FROM python:3.12-slim AS development

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        netcat-openbsd \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Ensure local bin is in PATH
ENV PATH=/root/.local/bin:$PATH

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production Stage ────────────────────────────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

RUN groupadd -r echotrace && useradd -r -g echotrace -d /app -s /bin/false echotrace

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

COPY . .

RUN chown -R echotrace:echotrace /app

USER echotrace

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
