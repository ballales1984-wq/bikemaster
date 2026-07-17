# Deployment Security Checklist

## Pre-Deployment Checks

### Code Review
- [ ] All changes reviewed for security implications
- [ ] No hardcoded secrets or credentials
- [ ] No debug code or console.log with sensitive data
- [ ] Dependencies updated and scanned
- [ ] Security tests passing

### Configuration
- [ ] All environment variables documented
- [ ] No secrets in config files or Docker images
- [ ] CORS origins correctly configured for production
- [ ] Rate limiting configured for production traffic
- [ ] Health check endpoints functional

### Infrastructure
- [ ] TLS certificates valid and not expiring soon
- [ ] Firewall rules updated for new services
- [ ] Database backups configured and tested
- [ ] Monitoring and alerting configured
- [ ] Log aggregation configured

## Platform-Specific Checks

### Vercel (Frontend)
- [ ] Environment variables set in Vercel dashboard
- [ ] `VITE_API_BASE_URL` points to production backend
- [ ] Build previews disabled or restricted
- [ ] Domain verification complete
- [ ] Security headers configured in vercel.json

### Railway (Backend)
- [ ] PostgreSQL plugin configured
- [ ] Redis plugin configured (if used)
- [ ] Environment variables set (SECRET_KEY, DATABASE_URL, etc.)
- [ ] Health check endpoint responding
- [ ] Auto-deploy on main branch enabled

### Fly.io (Backend)
- [ ] PostgreSQL cluster attached
- [ ] Redis attached or URL configured
- [ ] Secrets set via `fly secrets set`
- [ ] `fly.toml` has proper health checks
- [ ] Private networking enabled

### Render (Hub)
- [ ] `render-hub.yaml` configuration valid
- [ ] PostgreSQL addon attached
- [ ] Environment variables set in Render dashboard
- [ ] Auto-deploy on push enabled
- [ ] Health check path configured

## Post-Deployment Checks

### Immediate
- [ ] Application loads correctly
- [ ] HTTPS redirect working
- [ ] Health check endpoint returns 200
- [ ] SSL certificate valid (no warnings)
- [ ] CORS headers correct

### Within 1 Hour
- [ ] Error rates normal (check 5xx count)
- [ ] Response times within SLA
- [ ] Database connections stable
- [ ] Logs flowing to aggregation
- [ ] Alerts firing correctly

### Within 24 Hours
- [ ] No unusual traffic patterns
- [ ] Backup jobs completed successfully
- [ ] SSL certificate stapling working
- [ ] DNS propagation complete
- [ ] CDN cache warming complete

## Rollback Plan

### Trigger Conditions
- Critical security vulnerability discovered
- Data breach or unauthorized access
- Service unavailable for > 15 minutes
- Database corruption or data loss

### Rollback Steps
1. Identify last known good deployment
2. Execute rollback via platform (Vercel/Railway/Fly dashboard)
3. Verify rollback successful
4. Preserve logs from incident period
5. Notify stakeholders
6. Root cause analysis
7. Fix and re-deploy

## Security Incident Response

### During Deployment
If security issue discovered during deploy:
1. **STOP** - Do not continue deployment
2. **ASSESS** - Determine severity and impact
3. **ISOLATE** - If critical, rollback immediately
4. **DOCUMENT** - Record timeline and actions
5. **NOTIFY** - Alert security team and stakeholders

### Post-Incident
1. Conduct blameless post-mortem
2. Update security checklist based on findings
3. Implement preventive measures
4. Schedule follow-up review
5. Update documentation
