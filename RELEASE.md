# 🚢 Release Process

This document outlines the release process for EchoTrace AI. It covers versioning, build, deployment, and rollback procedures.

---

## Table of Contents

- [Versioning](#versioning)
- [Release Checklist](#release-checklist)
- [Creating a Release](#creating-a-release)
- [Docker Image Release](#docker-image-release)
- [GitHub Release](#github-release)
- [Kubernetes Rollout](#kubernetes-rollout)
- [Rollback Process](#rollback-process)
- [Hotfix Process](#hotfix-process)

---

## Versioning

EchoTrace AI follows [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

| Component | Description |
|-----------|-------------|
| **MAJOR** | Incompatible API or breaking changes |
| **MINOR** | Backward-compatible new functionality |
| **PATCH** | Backward-compatible bug fixes |

**Pre-release tags**: `-alpha`, `-beta`, `-rc.1` (e.g., `1.0.0-beta.1`)

### Version Locations

Update the version in the following locations:

- `backend/pyproject.toml` — `version = "x.y.z"`
- `frontend/package.json` — `"version": "x.y.z"`
- `CHANGELOG.md` — Add entry under new version
- Git tag — `git tag vx.y.z`

---

## Release Checklist

### Pre-Release

- [ ] All CI workflows pass (lint, test, build, scan)
- [ ] Docker images build successfully
- [ ] All tests pass (backend + frontend)
- [ ] Security scan (Trivy) reports no critical/high vulnerabilities
- [ ] CHANGELOG.md is up to date
- [ ] Version numbers updated in all locations
- [ ] All migrations are finalized and tested
- [ ] API documentation (Swagger/OpenAPI) reflects current state
- [ ] No known regressions from previous release

### Release

- [ ] Tag committed with `v*` format
- [ ] GitHub Release created with changelog
- [ ] Docker images built and pushed to GHCR
- [ ] Release images scanned with Trivy
- [ ] Release artifacts uploaded

### Post-Release

- [ ] Kubernetes manifests updated (if needed)
- [ ] Deployment tested in staging environment
- [ ] Monitoring dashboards verified
- [ ] Rollback procedure documented and tested
- [ ] Release communicated to team/stakeholders

---

## Creating a Release

### Automated Release (via GitHub Actions)

1. Ensure `main` branch is up to date and all CI checks pass
2. Create and push a version tag:
   ```bash
   git checkout main
   git pull origin main
   git tag v1.0.0                    # Use the new version
   git push origin v1.0.0
   ```
3. The [Release workflow](.github/workflows/release.yml) automatically:
   - Generates changelog
   - Creates a GitHub Release
   - Builds and pushes Docker images to GHCR
   - Runs Trivy vulnerability scan
4. Verify the release at `https://github.com/prayushsinghrathore/EchoTrace-AI/releases`

### Manual Release

```bash
# 1. Update version in pyproject.toml
sed -i '' 's/version = ".*"/version = "x.y.z"/' backend/pyproject.toml

# 2. Update version in frontend/package.json
sed -i '' 's/"version": ".*"/"version": "x.y.z"/' frontend/package.json

# 3. Update CHANGELOG.md with new version

# 4. Commit and tag
git add -A
git commit -m "chore(release): vx.y.z"
git tag vx.y.z
git push origin main --tags
```

---

## Docker Image Release

Images are published to **GitHub Container Registry (GHCR)**:

```bash
# Registry location
ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-backend
ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-frontend
```

### Image Tags

| Tag Pattern | Example | Description |
|-------------|---------|-------------|
| `x.y.z` | `1.0.0` | Exact version release |
| `latest` | `latest` | Latest stable release |
| `sha-XXXXXX` | `sha-a1b2c3` | Commit SHA (development) |

### Publishing

The CI pipeline automatically handles image publishing when a tag is pushed.
For manual publishing:

```bash
# Build and tag
docker build -t ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-backend:1.0.0 ./backend
docker build -t ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-frontend:1.0.0 ./frontend

# Push
docker push ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-backend:1.0.0
docker push ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-frontend:1.0.0

# Tag as latest (if this is the latest release)
docker tag ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-backend:1.0.0 \
  ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-backend:latest
docker push ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-backend:latest
```

---

## GitHub Release

Releases are created automatically by the [Release workflow](.github/workflows/release.yml). Each release includes:

- Version number and tag
- Auto-generated changelog
- Links to Docker images
- Build provenance and SBOM

To view releases: `https://github.com/prayushsinghrathore/EchoTrace-AI/releases`

---

## Kubernetes Rollout

### Rolling Update

```bash
# Update image version in deployment manifest
kubectl set image deployment/echotrace-backend \
  echotrace-backend=ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-backend:1.0.0 \
  -n echotrace

kubectl set image deployment/echotrace-frontend \
  echotrace-frontend=ghcr.io/prayushsinghrathore/echotrace-ai/echotrace-frontend:1.0.0 \
  -n echotrace

# Monitor rollout
kubectl rollout status deployment/echotrace-backend -n echotrace
kubectl rollout status deployment/echotrace-frontend -n echotrace
```

### Using Updated Manifests

```bash
# If K8s manifests reference updated image tags
kubectl apply -f k8s/backend.yaml
kubectl apply -k8s frontend.yaml

# Verify all pods are running
kubectl get pods -n echotrace -w
```

### Zero-Downtime Deployment

The Kubernetes configuration supports zero-downtime deployments through:

- **RollingUpdate** strategy (default)
- **Pod Disruption Budget** (PDB) ensuring minimum available pods
- **Readiness probes** preventing traffic routing before pod readiness
- **Horizontal Pod Autoscaler** (HPA) maintaining capacity during rollout
- **Health checks** confirming service availability

---

## Rollback Process

### Docker Compose Rollback

```bash
# Revert to previous image version
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### Kubernetes Rollback

```bash
# Rollback to previous revision
kubectl rollout undo deployment/echotrace-backend -n echotrace
kubectl rollout undo deployment/echotrace-frontend -n echotrace

# Rollback to specific revision
kubectl rollout undo deployment/echotrace-backend -n echotrace --to-revision=2

# Verify rollback status
kubectl rollout status deployment/echotrace-backend -n echotrace

# View rollout history
kubectl rollout history deployment/echotrace-backend -n echotrace
```

### Git Rollback

```bash
# Revert the release commit
git revert <release-commit-hash>
git push origin main

# Remove the tag (if needed)
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0

# Create a hotfix release with the revert
git tag v0.1.1
git push origin v0.1.1
```

---

## Hotfix Process

For critical bug fixes that cannot wait for the next scheduled release:

1. **Branch from the release tag**:
   ```bash
   git checkout -b hotfix/issue-description v1.0.0
   ```

2. **Fix and commit**:
   ```bash
   git commit -m "fix: critical issue description"
   ```

3. **Version bump** (patch increment):
   ```bash
   # Update version to 0.1.1 in pyproject.toml and package.json
   git tag v0.1.1
   ```

4. **Merge back to main**:
   ```bash
   git checkout main
   git merge --no-ff hotfix/issue-description
   git push origin main --tags
   ```

5. **Release** follows the standard automated process
