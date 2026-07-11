# 🔒 Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | ✅ Active support   |

## Reporting a Vulnerability

We take the security of EchoTrace AI seriously. If you believe you have found a security vulnerability, please report it to us as described below.

**Please do NOT report security vulnerabilities through public GitHub issues.**

### How to Report

1. **Email**: Send details to the repository maintainer via GitHub's private vulnerability reporting feature
2. **GitHub Advisories**: Use the "Report a vulnerability" link under the repository's Security tab

Include the following information in your report:

- Type of vulnerability
- Full path(s) of affected source file(s)
- Location of affected code (line number(s))
- Step-by-step reproduction instructions
- Proof-of-concept or exploit code (if possible)
- Impact description

### What to Expect

- **Acknowledgment**: Within 48 hours of submitting your report
- **Status Update**: Within 5 business days, we will confirm the vulnerability and begin assessment
- **Mitigation Timeline**: Depends on severity, but we aim for:
  - **Critical**: Patch within 48 hours
  - **High**: Patch within 7 days
  - **Medium**: Patch within 14 days
  - **Low**: Patch within next release cycle

### Response Timeline

| Phase | Duration |
|-------|----------|
| **Acknowledgment** | Within 48 hours |
| **Triage & Assessment** | 2–5 business days |
| **Fix Development** | Per severity (see above) |
| **Release** | Coordinated disclosure |
| **Public Disclosure** | After fix is released |

## Responsible Disclosure

We ask that you:

- Allow reasonable time for a fix before public disclosure
- Do not access or modify user data without permission
- Act in good faith to avoid harm to the project and its users
- Provide sufficient detail to reproduce and validate the issue

## Security Best Practices

For users deploying EchoTrace AI in production:

### Authentication & Secrets

- **Always** override the default `SECRET_KEY` with a strong, cryptographically random 32+ character secret
- Use environment variables or a secret manager (HashiCorp Vault, AWS Secrets Manager, etc.)
- Enable MFA where supported
- Rotate credentials regularly

### Network Security

- Run services behind a reverse proxy (nginx, Traefik, or your ingress controller)
- Enforce TLS/HTTPS in production
- Restrict database access to application IPs only
- Use network policies in Kubernetes environments

### Database

- Use strong, unique passwords for PostgreSQL and Neo4j
- Restrict database users to minimum required privileges
- Enable SSL/TLS for database connections
- Regularly back up data and test restoration

### Container Security

- Use the provided production Dockerfiles (do not use development images in production)
- Run containers as non-root user (configured by default)
- Enable Docker Content Trust
- Regularly scan images with Trivy (included in CI pipeline)
- Apply resource limits to containers

### Runtime Security

- Keep dependencies updated (`pip-audit`, `npm audit`)
- Enable rate limiting (built-in)
- Use structured logging and monitor for anomalies
- Configure CORS properly for your deployment domain
- Use `no-new-privileges` security option (configured in production compose)

### Monitoring

- Review security advisories regularly
- Enable and review audit logs
- Set up alerts for suspicious activity
- Monitor resource usage for anomalies

## Security Features

EchoTrace AI includes the following built-in security measures:

- ✅ JWT-based authentication with refresh token rotation
- ✅ Password hashing with bcrypt/argon2
- ✅ Rate limiting on auth endpoints
- ✅ SQL injection protection via SQLAlchemy parameterization
- ✅ XSS protection via Content Security Policy headers
- ✅ CORS middleware with configurable origins
- ✅ Helmet-style security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- ✅ Input validation via Pydantic schemas
- ✅ RBAC (Role-Based Access Control)
- ✅ Zero-trust networking model in Kubernetes
- ✅ Container security (non-root user, read-only root filesystem)
- ✅ Automated vulnerability scanning in CI/CD pipeline
