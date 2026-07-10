# 🔒 EchoTrace AI — Security & Production Hardening Guide

Enterprise security hardening checklist and configuration reference for EchoTrace AI production deployments.

---

## Security Headers

Headers are applied by `app/core/middleware.py`:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `X-XSS-Protection` | `1; mode=block` | XSS filter (legacy) |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Enforces HTTPS |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controls referrer info |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | Restricts API access |

---

## Production Checklist

### Authentication

- [ ] `SECRET_KEY` is set to a strong random value (32+ chars)
  ```bash
  openssl rand -hex 32
  ```
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES` is set appropriately (default: 30)
- [ ] `REFRESH_TOKEN_EXPIRE_DAYS` is set (default: 7)
- [ ] `AUTH_USE_COOKIES` is set to `true` with `AUTH_COOKIE_SECURE=true`
- [ ] MFA is configured if required by compliance

### Rate Limiting

| Endpoint | Default Max | Window | Type |
|----------|-------------|--------|------|
| Login | 10 | 5 min | Per-IP |
| Register | 5 | 60 min | Per-IP |
| Token Refresh | 20 | 15 min | Per-IP |
| Password Reset | 3 | 60 min | Per-IP |
| AI Queries | 20 | 60s | Per-user |

Configured in [`backend/app/core/config.py`](../backend/app/core/config.py):

```python
RATE_LIMIT_LOGIN_MAX: int = 10
RATE_LIMIT_LOGIN_WINDOW: int = 300
# ...
```

### Database

- [ ] PostgreSQL connections use SSL/TLS
- [ ] `pool_pre_ping=True` is enabled (already configured)
- [ ] `pool_recycle=3600` prevents stale connections
- [ ] `DB_POOL_SIZE` is tuned for instance count (default: 10)
- [ ] Database user has minimal required privileges

### Docker Security

Built-in hardening (see `docker-compose.prod.yml`):

```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
```

Non-root user execution (configured in Dockerfiles):
```dockerfile
RUN addgroup -S -g ${APP_GID} ${APP_USER} && \
    adduser -S -u ${APP_UID} -G ${APP_USER} -D -H ${APP_USER}
USER ${APP_USER}
```

### Kubernetes Security

Zero-trust networking via `NetworkPolicy`:
```yaml
# Network isolation per-service
```

Pod Security Context (configured in `k8s/backend.yaml`):
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  runAsGroup: 1001
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

### Dependency Auditing

```bash
# Python
pip-audit

# Node.js
npm audit

# GitHub Dependabot — configure in .github/dependabot.yml
```

---

## Dependency Audit

### Python

```bash
# Run audit
pip install pip-audit
pip-audit

# Check for known vulnerabilities
pip-audit -r backend/requirements.txt --requirement
```

### Node.js

```bash
cd frontend

# Audit
npm audit

# Fix non-breaking issues
npm audit fix

# Review breaking changes
npm audit fix --force  # Use with caution
```

### GitHub Dependabot

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10

  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10

  - package-ecosystem: "docker"
    directory: "/backend"
    schedule:
      interval: "weekly"

  - package-ecosystem: "docker"
    directory: "/frontend"
    schedule:
      interval: "weekly"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

## Container Security

### Image Scanning

```bash
# Trivy (configured in CI)
trivy image ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-backend:latest

# Scan for high/critical only
trivy image --severity HIGH,CRITICAL echotrace-backend:latest

# Scan Dockerfile for misconfigurations
trivy config --severity HIGH,CRITICAL ./backend/
```

### Run as Non-Root

Both Dockerfiles create and switch to a non-root user:

```dockerfile
RUN addgroup -S -g 1001 appuser && \
    adduser -S -u 1001 -G appuser appuser
USER appuser
```

### Read-Only Filesystem

For Kubernetes (already configured in K8s manifests):

```yaml
securityContext:
  readOnlyRootFilesystem: true
  runAsNonRoot: true
```

---

## Secret Management

### Environment Variables

- [ ] Secrets are never hardcoded in source code
- [ ] `.env` files are in `.gitignore`
- [ ] Production secrets use a secret manager (HashiCorp Vault, AWS Secrets Manager, etc.)
- [ ] Kubernetes secrets are base64-encoded (at minimum)
- [ ] External secret management (SealedSecrets, External Secrets Operator)

### Kubernetes Secrets

```yaml
# Use SealedSecrets for GitOps:
# kubeseal -o yaml < secret.yaml > sealed-secret.yaml

# Or External Secrets Operator:
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: echotrace-secrets
spec:
  refreshInterval: "1h"
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: echotrace-secrets
```

---

## Production Configuration Reference

### Backend (.env)

```ini
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=<random-32-char-hex>
OTEL_ENABLED=false
REDIS_ENABLED=false
COMPRESSION_ENABLED=true
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
```

### Frontend (.env.local)

```ini
NEXT_PUBLIC_API_URL=https://api.echotrace.example.com/api/v1
NEXT_PUBLIC_APP_URL=https://app.echotrace.example.com
NEXT_PUBLIC_ENVIRONMENT=production
```

---

## References

- [Security Policy](../SECURITY.md)
- [Operations Guide](operations.md)
- [Kubernetes Deployment](../k8s/)
- [Docker Production Compose](../docker-compose.prod.yml)
- [Securing a FastAPI Application](https://fastapi.tiangolo.com/tutorial/security/)
