# Firewall Rules Configuration

## UFW (Ubuntu/Debian)

```bash
#!/bin/bash
# setup-firewall.sh - BikeMaster firewall configuration

# Reset to defaults
ufw --force disable
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing
ufw default deny routed

# Allow SSH (restrict to admin IPs if possible)
ufw allow 22/tcp comment 'SSH'

# Allow HTTP/HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Allow backend API (localhost only for production)
# ufw allow 8000/tcp comment 'Backend API'

# Enable logging
ufw logging on

# Enable firewall
ufw --force enable

# Show status
ufw status verbose
```

## iptables (Advanced)

```bash
#!/bin/bash
# iptables-rules.sh - Advanced firewall rules

# Flush existing rules
iptables -F
iptables -X

# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Allow SSH (restrict to specific IPs)
iptables -A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -s 192.168.1.0/24 -j ACCEPT

# Allow HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Rate limiting for SSH
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m limit --limit 3/min --limit-burst 3 -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -j DROP

# Log dropped packets
iptables -A INPUT -m limit --limit 5/min -j LOG --log-prefix "iptables-drop: "

# Save rules
iptables-save > /etc/iptables/rules.v4
ip6tables-save > /etc/iptables/rules.v6
```

## Docker Network Security

```yaml
# docker-compose.security.yml
version: '3.8'

services:
  backend:
    build: .
    networks:
      - backend-net
    ports:
      - "127.0.0.1:8000:8000"  # Localhost only
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed
    volumes:
      - ./logs:/app/logs:rw

  postgres:
    image: postgres:15-alpine
    networks:
      - backend-net
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
    read_only: true
    volumes:
      - pgdata:/var/lib/postgresql/data

  nginx:
    image: nginx:alpine
    networks:
      - frontend-net
      - backend-net
    ports:
      - "443:443"
    read_only: true
    volumes:
      - ./nginx/conf:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro

networks:
  frontend-net:
    driver: bridge
  backend-net:
    driver: bridge
    internal: true  # No external access

secrets:
  db_password:
    file: ./secrets/db_password.txt

volumes:
  pgdata:
```

## Cloud Firewall Rules

### AWS Security Group
```json
{
  "GroupName": "bikemaster-backend",
  "Description": "BikeMaster backend security group",
  "SecurityGroupIngress": [
    {
      "IpProtocol": "tcp",
      "FromPort": 443,
      "ToPort": 443,
      "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTPS"}]
    },
    {
      "IpProtocol": "tcp",
      "FromPort": 22,
      "ToPort": 22,
      "IpRanges": [{"CidrIp": "10.0.0.0/8", "Description": "SSH from internal"}]
    }
  ],
  "SecurityGroupEgress": [
    {
      "IpProtocol": "-1",
      "FromPort": 0,
      "ToPort": 65535,
      "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
    }
  ]
}
```

## Security Checklist

- [ ] Default deny policy on all firewalls
- [ ] Only required ports open
- [ ] SSH restricted to admin IPs/VPN
- [ ] Database not exposed to Internet
- [ ] Rate limiting configured
- [ ] Logging enabled for dropped packets
- [ ] Rules tested and documented
- [ ] Firewall rules reviewed quarterly
