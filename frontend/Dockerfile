# ═══════════════════════════════════════════════════════════════════════════════
# EchoTrace AI — Frontend Dockerfile
# ═══════════════════════════════════════════════════════════════════════════════
# Multi-stage build with production hardening, OCI labels, and security
# hardening for containerized deployment.
# Targets: deps, development, builder, production
# ═══════════════════════════════════════════════════════════════════════════════

# ── Build Arguments ──────────────────────────────────────────────────────────
ARG NODE_VERSION=20-alpine

# ── Dependencies Stage ─────────────────────────────────────────────────────
FROM node:${NODE_VERSION} AS deps

ARG NODE_VERSION

LABEL org.opencontainers.image.title="EchoTrace AI Frontend — Dependencies" \
      org.opencontainers.image.description="Dependency installation stage for EchoTrace AI frontend" \
      org.opencontainers.image.vendor="EchoTrace AI"

WORKDIR /app

RUN apk add --no-cache libc6-compat

COPY package.json package-lock.json* ./
RUN npm ci

# ── Development Stage ──────────────────────────────────────────────────────
FROM node:${NODE_VERSION} AS development

ARG NODE_VERSION

LABEL org.opencontainers.image.title="EchoTrace AI Frontend — Development" \
      org.opencontainers.image.description="Development image for EchoTrace AI frontend" \
      org.opencontainers.image.vendor="EchoTrace AI"

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

EXPOSE 3000

ENV NODE_ENV=development

CMD ["npm", "run", "dev"]

# ── Build Stage ────────────────────────────────────────────────────────────
FROM node:${NODE_VERSION} AS builder

ARG NODE_VERSION

LABEL org.opencontainers.image.title="EchoTrace AI Frontend — Builder" \
      org.opencontainers.image.description="Build stage for EchoTrace AI frontend" \
      org.opencontainers.image.vendor="EchoTrace AI"

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Ensure /app/public exists (it may be empty and thus excluded by .dockerignore
# whitelist), so COPY --from=builder in the production stage does not fail.
RUN mkdir -p /app/public

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ── Production Stage ───────────────────────────────────────────────────────
FROM node:${NODE_VERSION} AS production

ARG APP_USER=nextjs
ARG APP_UID=1001
ARG APP_GID=1001

ARG NODE_VERSION

# OCI image annotations
LABEL org.opencontainers.image.title="EchoTrace AI Frontend" \
      org.opencontainers.image.description="EchoTrace AI frontend web application" \
      org.opencontainers.image.source="https://github.com/pratyushsinghrathore/echotrace-ai" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.vendor="EchoTrace AI" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.ref.name="echotrace-frontend"

WORKDIR /app

# Create non-root user with configurable UID/GID
RUN addgroup -S -g ${APP_GID} ${APP_USER} && \
    adduser -S -u ${APP_UID} -G ${APP_USER} -D -H ${APP_USER}

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

# Copy only the standalone build output
COPY --from=builder --chown=${APP_USER}:${APP_USER} /app/.next/standalone ./
COPY --from=builder --chown=${APP_USER}:${APP_USER} /app/.next/static ./.next/static
COPY --from=builder --chown=${APP_USER}:${APP_USER} /app/public ./public

USER ${APP_USER}

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

STOPSIGNAL SIGTERM

CMD ["node", "server.js"]
