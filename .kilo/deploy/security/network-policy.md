# Network Security Policy

## Overview
This document defines network security policies for BikeMaster deployments.

## Firewall Rules

### Inbound Traffic
| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 443  | TCP      | 0.0.0.0/0 | HTTPS (production) |
| 8000 | TCP      | 127.0.0.1 | Backend API (local dev only) |
| 22   | TCP      | Admin IPs | SSH (if needed) |

### Outbound Traffic
| Port | Protocol | Destination | Purpose |
|------|----------|-------------|---------|
| 443  | TCP      | * | HTTPS outbound (API calls, updates) |
| 53   | UDP/TCP  | * | DNS resolution |
| 123  | UDP      | * | NTP time sync |

## TLS Configuration

### Minimum Requirements
- TLS 1.2 minimum (TLS 1.3 preferred)
- Strong cipher suites only
- Valid certificates from trusted CA
- HSTS header with max-age >= 31536000
- No TLS compression (CRIME attack prevention)

### Certificate Management
- Automatic renewal 30 days before expiry
- Certificate transparency logs monitored
- OCSP stapling enabled

## Network Segmentation

### Production Zones
1. **Public Zone**: Load balancers, CDN (Vercel edge)
2. **Application Zone**: Backend servers, API endpoints
3. **Data Zone**: Database servers (PostgreSQL, SQLite)
4. **Management Zone**: Admin interfaces, monitoring

### Communication Rules
- Public Zone -> Application Zone: HTTPS only
- Application Zone -> Data Zone: Private network only
- Data Zone: No direct Internet access
- Management Zone: Restricted to admin IPs, VPN required

## VPN / Tunnel Security

### ngrok (Development)
- Use auth tokens for all tunnels
- Set tunnel domain restrictions
- Limit tunnel lifetime
- Never expose tunnel URLs in public repos

### Production Tunnels
- Use WireGuard or IPSec for site-to-site
- MFA required for VPN access
- Session timeout after 4 hours idle
- Audit log all VPN connections

## DNS Security

### Requirements
- DNSSEC enabled where supported
- DNS over HTTPS (DoH) preferred for internal resolution
- Primary and secondary DNS servers from different providers
- DNS caching with appropriate TTL values

### Monitoring
- Monitor for DNS hijacking attempts
- Alert on unexpected DNS changes
- Log all DNS queries for security events

## DDoS Protection

### Measures
- Rate limiting at load balancer level
- CDN DDoS protection (Vercel edge)
- IP reputation filtering
- Automatic traffic scrubbing during attacks

## Incident Response

### Network Breach
1. Isolate affected segment immediately
2. Preserve logs and evidence
3. Notify security team
4. Assess data exposure
5. Implement containment measures
6. Notify affected parties if required

### Monitoring Thresholds
- Unusual outbound traffic: > 2x baseline
- Connection spikes: > 5x normal rate
- Failed auth attempts: > 10/min from single IP
- New external connections: Alert immediately
