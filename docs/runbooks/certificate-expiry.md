# Runbook: TLS Certificate Expiry

## Severity
**High** — HTTPS access will break when certificate expires.

## Symptoms
- Browser shows security warnings
- API clients report certificate errors
- `kubectl describe certificate` shows expiry approaching
- Monitoring alert for certificate expiry (if configured)

## Immediate Steps

### 1. Check certificate expiry dates
```bash
# Kubernetes cert-manager
kubectl get certificates -A
kubectl describe certificate -n echotrace echotrace-tls

# Let's Encrypt expiry
openssl s_client -connect <domain>:443 -servername <domain> 2>/dev/null | openssl x509 -noout -dates

# Local certificate files
openssl x509 -in <cert-file> -noout -dates
```

### 2. Verify cert-manager status
```bash
kubectl get certificaterequests -A
kubectl get orders -A
kubectl get challenges -A
```

## Root Cause Diagnosis

### cert-manager Not Running
- Symptom: No CertificateRequests created
- Check: `kubectl get pods -n cert-manager`
- Fix: Restart cert-manager, check RBAC

### DNS Validation Failure
- Symptom: Challenges in `pending` or `invalid` state
- Check: DNS records, `kubectl describe challenge`
- Fix: Ensure DNS A/AAAA records point to the ingress

### Rate Limiting
- Symptom: Let's Encrypt rate limit errors
- Check: cert-manager logs for `rateLimited`
- Fix: Wait for rate limit to reset, use staging CA for testing

### Manual Certificate
- Symptom: Certificate issued outside cert-manager
- Check: Certificate file locations
- Fix: Replace certificate before expiry

## Resolution Steps

### Automatic (cert-manager)
```bash
# Trigger renewal
kubectl annotate certificate -n echotrace echotrace-tls \
  cert-manager.io/issue-temporary-certificate="true"

# Force renewal
kubectl delete certificaterequest -n echotrace <old-cr>
kubectl delete order -n echotrace <old-order>
```

### Manual cert-manager renewal
```bash
# cert-manager should auto-renew within 30 days of expiry
# Check renewal status
kubectl get certificate -n echotrace echotrace-tls -o json | jq '.status'
```

### For Let's Encrypt staging tests
```yaml
# Use staging issuer first
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
```

### Manual certificate replacement
```bash
# Upload new certificate
kubectl create secret tls echotrace-tls \
  --cert=new-cert.pem \
  --key=new-key.pem \
  -n echotrace --dry-run=client -o yaml | kubectl apply -f -
```

## Verification
- [ ] Certificate valid for >30 days
- [ ] `kubectl get certificate -n echotrace` shows `Ready`
- [ ] HTTPS works: `curl -I https://<domain>`
- [ ] No browser security warnings
- [ ] cert-manager renews automatically

## Post-Incident
- [ ] Set up certificate expiry monitoring (recommended: alert at 30 days)
- [ ] Verify cert-manager auto-renewal works
- [ ] Document manual renewal process
