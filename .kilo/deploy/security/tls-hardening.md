# TLS Hardening Guide

## Nginx TLS Configuration

```nginx
# /etc/nginx/conf.d/tls-hardening.conf

# TLS Protocol Settings
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers off;

# DH Parameters (generate with: openssl dhparam -out /etc/nginx/dhparam.pem 4096)
ssl_dhparam /etc/nginx/dhparam.pem;

# Session Settings
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# Security Headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

# Content Security Policy (adjust for your needs)
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; frame-ancestors 'self';" always;

# SSL Certificate paths
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;
ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
```

## Docker TLS Termination

```dockerfile
# Dockerfile snippet for TLS termination
FROM nginx:alpine

# Copy TLS certificates
COPY ssl/cert.pem /etc/nginx/ssl/
COPY ssl/key.pem /etc/nginx/ssl/
COPY ssl/chain.pem /etc/nginx/ssl/
COPY nginx-tls.conf /etc/nginx/conf.d/default.conf

# Generate DH params
RUN openssl dhparam -out /etc/nginx/dhparam.pem 4096

# Run as non-root
RUN addgroup -g 1001 -S nginx || true
RUN adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginx nginx || true
USER nginx

EXPOSE 443
CMD ["nginx", "-g", "daemon off;"]
```

## Certificate Management

### Let's Encrypt with Certbot
```bash
# Obtain certificate
certbot certonly --nginx -d bikemaster.example.com

# Test auto-renewal
certbot renew --dry-run

# Renewal cron (runs twice daily)
0 0,12 * * * root certbot renew --quiet
```

### Certificate Validation Checklist
- [ ] Certificate not expired
- [ ] Certificate matches domain name
- [ ] Intermediate certificates included
- [ ] Private key permissions: 600
- [ ] Certificate chain validated
- [ ] OCSP stapling working
- [ ] Perfect Forward Secrecy enabled

## TLS Testing

```bash
# Test SSL configuration
openssl s_client -connect bikemaster.example.com:443 -servername bikemaster.example.com

# Check certificate details
openssl s_client -connect bikemaster.example.com:443 2>/dev/null | openssl x509 -noout -dates -subject -issuer

# Test cipher suites
nmap --script ssl-enum-ciphers -p 443 bikemaster.example.com

# Online testing
# - SSL Labs: https://www.ssllabs.com/ssltest/
# - Mozilla Observatory: https://observatory.mozilla.org/
```
