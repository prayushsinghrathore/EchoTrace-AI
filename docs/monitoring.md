# 📊 EchoTrace AI — Monitoring & Observability Guide

This document describes the complete monitoring and observability infrastructure for EchoTrace AI.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Metrics](#metrics)
- [Dashboards](#dashboards)
- [Logging](#logging)
- [Tracing](#tracing)
- [Alerting](#alerting)
- [Troubleshooting](#troubleshooting)
- [References](#references)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Instrumented Services                         │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Backend    │  │  Frontend  │  │PostgreSQL │  │    Neo4j      │  │
│  │  (FastAPI)  │  │ (Next.js)  │  │ Exporter  │  │   Exporter    │  │
│  └──────┬──────┘  └──────┬─────┘  └─────┬────┘  └──────┬────────┘  │
│         │                │              │              │            │
│    OTLP │           OTLP │              │              │            │
└─────────┼────────────────┼──────────────┼──────────────┼────────────┘
          │                │              │              │
          ▼                ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    OpenTelemetry Collector                            │
│            ┌──────────────────────────────┐                          │
│            │  Processors: batch, memory,  │                          │
│            │  attributes, transform       │                          │
│            └──────────┬───────────────────┘                          │
└───────────────────────┼─────────────────────────────────────────────┘
                        │
          ┌─────────────┼────────────────┬───────────────┐
          ▼             ▼                ▼               ▼
    ┌──────────┐  ┌──────────┐   ┌──────────┐   ┌──────────────┐
    │ Jaeger   │  │  Tempo   │   │Prometheus│   │   Loki       │
    │ (Traces) │  │ (Traces) │   │(Metrics) │   │   (Logs)     │
    └──────────┘  └──────────┘   └─────┬────┘   └──────┬───────┘
                                       │                │
                                       ▼                ▼
                                 ┌───────────────────────────┐
                                 │        Grafana             │
                                 │  Dashboards · Alerts ·    │
                                 │  Explore · Unified UI     │
                                 └───────────────────────────┘
```

### Components

| Component | Purpose | Port | Image |
|-----------|---------|------|-------|
| **Prometheus** | Metrics storage & alert evaluation | 9090 | prom/prometheus:v2.54.1 |
| **Grafana** | Dashboard & visualization | 3001 | grafana/grafana:11.3.0 |
| **OTel Collector** | Trace/metric/log collection & routing | 4317, 4318 | otel/opentelemetry-collector-contrib:0.113.0 |
| **Jaeger** | Trace storage & UI | 16686 | jaegertracing/all-in-one:1.62 |
| **Tempo** | Long-term trace storage | 3200 | grafana/tempo:2.6.1 |
| **PostgreSQL Exporter** | Database metrics | 9187 | prometheuscommunity/postgres-exporter:v0.15.0 |
| **Neo4j Exporter** | Graph database metrics | 7475 | mneedham/neo4j-exporter:latest |
| **Node Exporter** | Host-level metrics | 9100 | prom/node-exporter:v1.8.2 |
| **cAdvisor** | Container metrics | 8080 | gcr.io/cadvisor/cadvisor:v0.49.1 |

### Quick Start

```bash
# Ensure the main stack is running
docker compose up -d

# Start the monitoring stack
docker compose -f docker-compose.monitoring.yml up -d

# Access Grafana at http://localhost:3001 (admin/admin)
# Access Prometheus at http://localhost:9090
# Access Jaeger at http://localhost:16686
```

---

## Metrics

### Scraping Targets

Prometheus scrapes the following targets (see [`monitoring/prometheus/prometheus.yml`](../monitoring/prometheus/prometheus.yml)):

| Job | Target | Interval | Path |
|-----|--------|----------|------|
| `echotrace-backend` | `backend:8000` | 10s | `/api/v1/metrics` |
| `echotrace-frontend` | `frontend:3000` | 15s | `/api/metrics` |
| `postgres-exporter` | `postgres-exporter:9187` | 30s | `/metrics` |
| `neo4j-exporter` | `neo4j-exporter:7474` | 30s | `/metrics` |
| `node-exporter` | `node-exporter:9100` | 30s | `/metrics` |
| `cadvisor` | `cadvisor:8080` | 15s | `/metrics` |

### Application Metrics

The backend exposes application-level metrics at `/api/v1/metrics` via the built-in [`MetricsCollector`](../backend/app/core/metrics.py):

| Metric | Type | Description |
|--------|------|-------------|
| `echotrace_requests_total` | Counter | Total request count |
| `echotrace_errors_total` | Counter | Total error count |
| `echotrace_latency_seconds` | Histogram | Request latency distribution |
| `echotrace_db_latency_seconds` | Histogram | Database query latency |
| `echotrace_ai_tokens_total` | Counter | AI token usage |
| `echotrace_ai_cost_total` | Counter | AI cost in USD |
| `echotrace_cache_operations_total` | Counter | Cache hit/miss count |
| `echotrace_websocket_connections` | Gauge | Active WS connections |
| `echotrace_failed_logins_total` | Counter | Failed login attempts |
| `echotrace_rate_limit_hits_total` | Counter | Rate limit violations |

### Recording Rules

Pre-computed metrics (see [`monitoring/prometheus/rules/`](../monitoring/prometheus/rules/)):

| Rule | Expression | Purpose |
|------|-----------|---------|
| `echotrace:backend:requests_rate_5m` | `rate(echotrace_requests_total[5m])` | Request throughput |
| `echotrace:backend:error_ratio_5m` | `rate(errors[5m]) / rate(requests[5m])` | Error ratio |
| `echotrace:backend:latency_p95_5m` | `histogram_quantile(0.95, ...)` | P95 latency |
| `echotrace:backend:latency_p99_5m` | `histogram_quantile(0.99, ...)` | P99 latency |

---

## Dashboards

Dashboards are defined in [`monitoring/grafana/dashboards/`](../monitoring/grafana/dashboards/) and auto-provisioned via Grafana's provisioning API.

| Dashboard | UID | Panels |
|-----------|-----|--------|
| **Backend** | `echotrace-backend` | Request rate, latency (P50/P95/P99), error rate, status codes, active requests, DB latency |
| **Frontend** | `echotrace-frontend` | Response time, client errors (4xx), asset loading, request volume |
| **PostgreSQL** | `echotrace-postgresql` | Connections, slow queries, cache hit ratio, database size, locks, transaction rate |
| **Neo4j** | `echotrace-neo4j` | Heap usage, transactions, query time, open connections, page cache, failed transactions |
| **Infrastructure** | `echotrace-infrastructure` | CPU, memory, disk, network I/O, container metrics (CPU/memory), disk I/O |

### Importing Dashboards

Dashboards are auto-provisioned. To import manually:

1. Grafana → Dashboards → New → Import
2. Upload the JSON file from `monitoring/grafana/dashboards/`
3. Select the Prometheus datasource

---

## Logging

### Structured Logging

EchoTrace AI uses [structlog](https://www.structlog.org/) for structured logging. See [`backend/app/core/logging.py`](../backend/app/core/logging.py).

### Log Format

**Production** (JSON):
```json
{
  "event": "Request completed",
  "level": "info",
  "logger": "echotrace.core.middleware",
  "environment": "production",
  "service": "echotrace-backend",
  "version": "0.1.0",
  "timestamp": "2026-07-11T12:00:00Z",
  "request_id": "abc-123",
  "correlation_id": "xyz-789",
  "trace_id": "0x4e3f2a1b",
  "span_id": "0x8c7d6e5f",
  "user_id": "user_42",
  "workspace_id": "ws_7",
  "method": "GET",
  "path": "/api/v1/evidence",
  "status_code": 200,
  "duration_ms": 45.23,
  "filename": "middleware.py",
  "func_name": "security_headers",
  "lineno": 67
}
```

**Development**: Pretty-printed color console output.

### Log Context Fields

| Field | Source | Example |
|-------|--------|---------|
| `request_id` | Generated or X-Request-ID header | `"abc-123"` |
| `correlation_id` | X-Correlation-ID header | `"xyz-789"` |
| `trace_id` | OpenTelemetry span context | `"0x4e3f2a1b"` |
| `span_id` | OpenTelemetry span context | `"0x8c7d6e5f"` |
| `user_id` | Auth middleware (request.state.user) | `"user_42"` |
| `workspace_id` | Request state | `"ws_7"` |
| `environment` | Settings.ENVIRONMENT | `"production"` |
| `service` | Service name | `"echotrace-backend"` |
| `version` | Application version | `"0.1.0"` |

### Log Levels

| Level | Usage |
|-------|-------|
| `DEBUG` | Detailed diagnostic information (development only) |
| `INFO` | Normal operational messages (request completion, startup) |
| `WARNING` | Unexpected but handled conditions (4xx errors, retries) |
| `ERROR` | Runtime errors that should be investigated (5xx, exceptions) |
| `CRITICAL` | System-level failures (database unavailable, startup failure) |

---

## Tracing

### OpenTelemetry

Distributed tracing is implemented via OpenTelemetry (see [`backend/app/core/otel.py`](../backend/app/core/otel.py)).

**Instrumentations:**
- FastAPI (auto-instrumentation of routes, middleware, request/response)
- HTTPX (outbound HTTP calls)
- SQLAlchemy (database queries)
- Neo4j (database transactions where supported)

**Trace Export:**
- OTLP gRPC to OTel Collector → **Jaeger** (short-term) + **Tempo** (long-term)

### Trace Context Propagation

Traces are propagated via:
- `traceparent` / `tracestate` W3C trace context headers
- `x-b3-traceid` Zipkin headers (legacy)
- `baggage` headers for custom context

### Viewing Traces

- **Jaeger UI**: http://localhost:16686 (search by service, operation, tags, duration)
- **Grafana Explore**: Select Tempo datasource → Search by trace ID or query by service

---

## Alerting

### Alert Rules

Alert rules are defined in [`monitoring/prometheus/rules/`](../monitoring/prometheus/rules/):

| File | Alerts |
|------|--------|
| [`backend.yml`](../monitoring/prometheus/rules/backend.yml) | BackendHighErrorRate, BackendHighLatency, BackendServiceDown, BackendCrashLooping |
| [`frontend.yml`](../monitoring/prometheus/rules/frontend.yml) | FrontendServiceUnavailable, FrontendHighClientErrorRate |
| [`database.yml`](../monitoring/prometheus/rules/database.yml) | PostgresHighConnections, PostgresSlowQueries, PostgresLowCacheHitRatio, PostgresStorageUsage, Neo4jHighHeapUsage, Neo4jTransactionFailures, Neo4jSlowQueries |
| [`infrastructure.yml`](../monitoring/prometheus/rules/infrastructure.yml) | HighCPUUsage, CriticalCPUUsage, HighMemoryUsage, LowDiskSpace, CriticalLowDiskSpace, NodeDown, PodCrashLooping, ContainerHighCPU |
| [`security.yml`](../monitoring/prometheus/rules/security.yml) | FailedLoginSpike, CriticalFailedLoginSpike, HighAuthFailureRate, RateLimitViolations |

### Alert Routing

Configure alert receivers (Slack, PagerDuty, email) via the Alertmanager configuration or Grafana alerting.

### Recommended Alertmanager Configuration

```yaml
route:
  receiver: default
  routes:
    - match:
        severity: critical
      receiver: pagerduty-critical
      repeat_interval: 5m
    - match:
        team: security
      receiver: slack-security
      repeat_interval: 15m

receivers:
  - name: default
    slack_configs:
      - channel: "#alerts"
        send_resolved: true
  - name: pagerduty-critical
    pagerduty_configs:
      - routing_key: "${PAGERDUTY_ROUTING_KEY}"
  - name: slack-security
    slack_configs:
      - channel: "#security-alerts"
        send_resolved: true
```

---

## Troubleshooting

### Monitoring Stack Issues

**Prometheus not scraping targets:**
```bash
# Check target status
curl http://localhost:9090/api/v1/targets | jq

# Verify service discovery
curl http://localhost:9090/api/v1/service-discovery
```

**Grafana dashboards not showing data:**
```bash
# Verify datasource connectivity
# Grafana → Configuration → Data Sources → Prometheus → Test

# Check dashboard JSON import
docker compose -f docker-compose.monitoring.yml logs grafana
```

**OTel Collector not receiving traces:**
```bash
# Check collector logs
docker compose -f docker-compose.monitoring.yml logs otel-collector

# Verify OTLP endpoint
curl -X POST http://localhost:4318/v1/traces
```

**Missing PostgreSQL metrics:**
```bash
# Verify exporter can connect to DB
docker compose -f docker-compose.monitoring.yml logs postgres-exporter

# Check exporter metrics endpoint
curl http://localhost:9187/metrics | head
```

### Common Issues

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| No metrics in Prometheus | Target unreachable | Check network connectivity and service health |
| `up == 0` for all targets | Service not started | `docker compose up -d` |
| Grafana "Datasource not found" | Datasource provisioning failed | Check `monitoring/grafana/datasources/datasource.yml` |
| High cardinality metrics | Unbounded label values | Review path grouping in `MetricsCollector._group_path` |
| No traces in Jaeger | OTel not configured | Set `OTEL_ENABLED=true` in environment |

---

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Grafana Tempo Documentation](https://grafana.com/docs/tempo/)
- [PostgreSQL Exporter](https://github.com/prometheus-community/postgres_exporter)
- [Node Exporter](https://github.com/prometheus/node_exporter)
- [cAdvisor](https://github.com/google/cadvisor)
- [Runbooks](runbooks/)
- [SRE Guide](sre.md)
- [Operations Guide](operations.md)
- [Deployment Guide](docker-deployment.md)
- [Kubernetes Guide](kubernetes.md)
- [Performance Baselines](performance.md)
