# 🏢 EchoTrace AI — SRE Guide

Site Reliability Engineering practices, SLI/SLO definitions, error budgets, incident response, and on-call processes.

---

## Table of Contents

- [Incident Severity Definitions](#incident-severity-definitions)
- [Service Level Indicators (SLIs)](#service-level-indicators-slis)
- [Service Level Objectives (SLOs)](#service-level-objectives-slos)
- [Service Level Agreements (SLAs)](#service-level-agreements-slas)
- [Error Budgets](#error-budgets)
- [Escalation Policy](#escalation-policy)
- [Incident Response](#incident-response)
- [Postmortems](#postmortems)
- [On-Call Process](#on-call-process)

---

## Incident Severity Definitions

| Severity | Label | Description | Response Time | Examples |
|----------|-------|-------------|---------------|----------|
| **SEV-1** | Critical | Complete service outage or data loss | 15 min | All APIs down, database corrupted, security breach |
| **SEV-2** | High | Major feature degraded, no workaround | 30 min | Graph queries failing, authentication broken |
| **SEV-3** | Medium | Partial feature degraded, has workaround | 2 hours | Slow queries, non-critical UI bugs |
| **SEV-4** | Low | Minor issue, cosmetic, no user impact | Next business day | Typo in UI, documentation error |

### Severity 1 — Critical

**Definition:** Complete service unavailability or active data loss.

**Examples:**
- All API endpoints returning 5xx
- Database corruption or data loss
- Active security breach
- Frontend completely unavailable

**Response:**
- Immediately page the on-call engineer
- Escalate to engineering lead within 15 minutes
- Declare incident in Slack #incidents channel
- Assemble incident response team
- Every 30-minute status updates

### Severity 2 — High

**Definition:** Major feature unavailable, but core API remains operational.

**Examples:**
- Authentication failures
- AI/investigation features unavailable
- Graph database unavailable (degraded)
- File uploads failing

**Response:**
- Page on-call engineer within 30 minutes
- Open incident investigation
- Hourly status updates

### Severity 3 — Medium

**Definition:** Feature partially degraded with a known workaround.

**Examples:**
- API latency above SLO but service is usable
- Specific endpoints slow
- UI rendering issues for non-critical features

**Response:**
- Investigate during business hours
- No page required
- Track via GitHub issue

### Severity 4 — Low

**Definition:** Cosmetic or minor issues with no user impact.

**Examples:**
- Documentation errors
- Minor UI alignment issues
- Non-critical log warnings

**Response:**
- Track via backlog
- Fix in normal development cycle

---

## Service Level Indicators (SLIs)

### API SLIs

| Indicator | Definition | Measurement Method |
|-----------|-----------|-------------------|
| **Availability** | Fraction of requests that return successful (2xx/3xx) responses | `rate(echotrace_requests_total{status=~"2.*|3.*"} / rate(echotrace_requests_total[1m])` |
| **Latency (P95)** | 95th percentile of request duration | `histogram_quantile(0.95, rate(echotrace_latency_seconds_bucket[5m]))` |
| **Latency (P99)** | 99th percentile of request duration | `histogram_quantile(0.99, rate(echotrace_latency_seconds_bucket[5m]))` |
| **Error Rate** | Fraction of requests returning 5xx | `rate(echotrace_errors_total[5m]) / rate(echotrace_requests_total[5m])` |
| **Throughput** | Number of requests per second | `rate(echotrace_requests_total[5m])` |

### Database SLIs

| Indicator | Definition | Measurement Method |
|-----------|-----------|-------------------|
| **Query Latency (P95)** | 95th percentile of database query time | `histogram_quantile(0.95, rate(echotrace_db_latency_seconds_bucket[5m]))` |
| **Cache Hit Ratio** | Buffer cache hit percentage | `blks_hit / (blks_hit + blks_read)` |
| **Connection Utilization** | Fraction of max connections used | `active_connections / max_connections` |

### Infrastructure SLIs

| Indicator | Definition | Target |
|-----------|-----------|--------|
| **CPU Utilization** | Average CPU usage across nodes | < 70% |
| **Memory Utilization** | Average memory usage across nodes | < 75% |
| **Disk Utilization** | Root filesystem usage | < 80% |

---

## Service Level Objectives (SLOs)

### Monthly SLO Targets

| Service | Indicator | Target | Measurement Window |
|---------|-----------|--------|-------------------|
| **API** | Availability | 99.9% | Rolling 30 days |
| **API** | Latency P95 | < 1000ms | Rolling 7 days |
| **API** | Latency P99 | < 3000ms | Rolling 7 days |
| **API** | Error Rate | < 0.1% | Rolling 30 days |
| **PostgreSQL** | Query Latency P95 | < 100ms | Rolling 7 days |
| **PostgreSQL** | Availability | 99.95% | Rolling 30 days |
| **PostgreSQL** | Cache Hit Ratio | > 95% | Rolling 7 days |
| **Neo4j** | Query Latency P95 | < 500ms | Rolling 7 days |
| **Neo4j** | Availability | 99.9% | Rolling 30 days |
| **Frontend** | Availability | 99.9% | Rolling 30 days |
| **Frontend** | Page Load Time P95 | < 3s | Rolling 7 days |

### SLO Compliance Checking

```promql
# API Availability SLO (30d rolling)
(
  sum(rate(echotrace_requests_total{status=~"2.*|3.*"}[30d]))
  /
  sum(rate(echotrace_requests_total[30d]))
) * 100
```

---

## Service Level Agreements (SLAs)

The following SLA commitments apply to production deployments:

| Metric | Commitment | Remediation |
|--------|-----------|-------------|
| API Availability | 99.5% uptime (monthly) | Service credit |
| API Latency P95 | < 2s (monthly) | Service credit |
| Support Response | SEV-1: 15min, SEV-2: 30min | Escalation |

**Note:** SLAs are only applicable for paid production deployments. Open-source deployments have no SLA commitment.

---

## Error Budgets

### Calculation

```
Error Budget = 100% - SLO
Budget Consumption = (1 - actual_availability) / (1 - SLO) * 100
```

### Example

For a 99.9% SLO over a 30-day window:
- **Error budget:** 0.1% = 43.2 minutes of allowable downtime
- **Error budget consumed:** Actual downtime / Allowable downtime * 100

### Error Budget Policy

| Budget Remaining | Action |
|-----------------|--------|
| > 50% | Normal operations, deploy freely |
| 20% – 50% | Slow deploys, require code review |
| 5% – 20% | Freeze all deploys except critical fixes |
| < 5% | Rollback recent changes, full incident review |

---

## Escalation Policy

### Escalation Levels

| Level | Response | Time to Escalate |
|-------|----------|-----------------|
| **L1** | On-call engineer | Immediate |
| **L2** | Engineering team lead | 15 min (SEV-1), 30 min (SEV-2) |
| **L3** | Engineering director / CTO | 30 min (SEV-1), 60 min (SEV-2) |
| **L4** | VP Engineering / CEO | 60 min (SEV-1 only) |

### Escalation Path

```
Incident Detected
    │
    ▼
L1 — On-Call Engineer    ─── Resolved? ─── Done
    │ No
    ▼
L2 — Team Lead           ─── Resolved? ─── Done
    │ No
    ▼
L3 — Engineering Director ─── Resolved? ─── Done
    │ No
    ▼
L4 — VP / CEO
```

### How to Escalate

1. Post in Slack `#incidents` channel with severity and details
2. @mention the next-level contact
3. Call if no response within the escalation timeout
4. Continue escalating up the chain

---

## Incident Response

### Incident Lifecycle

```
Detect → Triage → Mitigate → Resolve → Postmortem
```

### 1. Detection
- Automated alerts from Prometheus
- User reports
- Monitoring dashboard anomalies
- Log analysis

### 2. Triage (first 5 minutes)
- Determine severity
- Assign incident commander
- Open `#incidents` Slack channel thread
- Create GitHub issue with incident label

### 3. Mitigate (aim for < 30 min)
- Roll back recent changes
- Restart services
- Scale up resources
- Traffic rerouting (if applicable)
- Document all actions taken

### 4. Resolve
- Confirm fix is effective
- Verify health checks pass
- Monitor for 15 minutes post-resolution
- Close incident
- Send communication to stakeholders

### 5. Postmortem
- Conduct within 48 hours
- Document timeline, root cause, lessons learned
- Assign action items
- Track to completion

### Incident Commander Responsibilities

- Coordinate response efforts
- Make Go/No-Go decisions on mitigations
- Communicate status updates (every 30 min for SEV-1)
- Decide when to escalate
- Ensure documentation is captured

---

## Postmortems

### Postmortem Template

```markdown
## Incident Summary
- **Date:** YYYY-MM-DD
- **Duration:** HH:MM
- **Severity:** SEV-X
- **Detected By:**
- **Reported By:**

## Timeline
| Time (UTC) | Event |
|------------|-------|
| HH:MM | Incident detected |
| HH:MM | Triage started |
| HH:MM | Mitigation deployed |
| HH:MM | Service restored |
| HH:MM | Incident closed |

## Root Cause

## Impact
- Users affected:
- Downtime duration:
- Data loss: None / Partial / Full
- Error budget consumed:

## Contributing Factors
- Factor 1
- Factor 2

## What Went Well
- 

## What Went Wrong
- 

## Action Items
| # | Action | Owner | Due Date | Status |
|---|--------|-------|----------|--------|
| 1 | Fix root cause | @name | YYYY-MM-DD | Open |
| 2 | Add monitoring | @name | YYYY-MM-DD | Open |

## Lessons Learned

## Appendix
- Related alerts
- Log excerpts
- Grafana dashboard snapshots
```

---

## On-Call Process

### Schedule
- **Rotation:** Weekly, Monday → Monday
- **Coverage:** 24/7 for SEV-1/SEV-2
- **Handoff:** Monday at 10:00 AM local time

### On-Call Responsibilities

During the on-call shift:
1. Respond to alerts within the SLO response time
2. Triage and mitigate incidents
3. Document all actions in the incident log
4. Update stakeholders on incident status
5. Complete handoff documentation before shift end

### Handoff Process

- Review open incidents from the week
- Document ongoing investigations
- Verify monitoring dashboards are healthy
- Confirm alert routing is configured
- Transfer pager/notification ownership

### Tools

| Tool | Purpose |
|------|---------|
| Prometheus + Alertmanager | Alerting |
| PagerDuty / OpsGenie | On-call scheduling & paging |
| Slack #incidents | Incident communication |
| GitHub Issues | Incident tracking |
| Grafana | Dashboard monitoring |
| Jaeger / Tempo | Trace analysis |

---

## References

- [Monitoring Guide](monitoring.md)
- [Runbooks](runbooks/)
- [Operations Guide](operations.md)
- [Alert Rules](../monitoring/prometheus/rules/)
- [Performance Baselines](performance.md)
