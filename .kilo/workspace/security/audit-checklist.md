# Security Audit Checklist

## Application Security
- [ ] No hardcoded secrets in source code
- [ ] `.gitignore` covers `.env`, `*.env`, `secrets/`, `*.pem`, `*.key`
- [ ] JWT tokens have expiration and proper signing (HS256/RS256)
- [ ] CORS configured with specific origins, not `*` with credentials
- [ ] OAuth flow uses `state` and `PKCE`
- [ ] All sensitive endpoints have `Depends` auth checks
- [ ] No `v-html` with untrusted data in Vue components
- [ ] CSP headers configured
- [ ] No `console.log` with sensitive data
- [ ] File uploads validated for type and size
- [ ] SQL queries use parameterized ORM (no f-strings)
- [ ] Object-level permissions enforced

## Network Security
- [ ] Firewall rules restrict inbound/outbound traffic
- [ ] TLS 1.2+ enforced on all endpoints
- [ ] Valid SSL certificates (no self-signed in production)
- [ ] HSTS header configured
- [ ] No `verify=False` in production HTTP clients
- [ ] CORS allow-list includes only deployed domains
- [ ] ngrok/tunnel URLs not publicly exposed without auth
- [ ] Database not directly reachable from Internet
- [ ] DNS uses secure resolvers (DoH preferred)

## Deploy Security
- [ ] No secrets hardcoded in Dockerfile, configs, or CI/CD
- [ ] Container base images are updated and scanned
- [ ] Containers run as non-root user
- [ ] Environment variables used for all sensitive config
- [ ] Health checks endpoint present and functional
- [ ] Database backups automated, encrypted, with retention policy
- [ ] Secrets managed via environment variables or secret manager

## Dependencies
- [ ] `pip-audit` or `safety check` run on backend
- [ ] `npm audit --audit-level=high` run on frontend
- [ ] No known critical CVEs in dependencies

## Logging & Monitoring
- [ ] Logs contain no passwords, tokens, session IDs, GPS data
- [ ] Audit trail for critical events (login, logout, DB changes)
- [ ] Rate limiting active on public endpoints
- [ ] Alerting configured for anomalies (5xx errors, failed logins)
