# Configuration Guide

This guide covers all configuration options for the Hybrid DNS Server, from basic DNS settings to advanced security policies.

## Table of Contents
- [DNS Server Configuration](#dns-server-configuration)
- [Conditional Forwarding](#conditional-forwarding)
- [Authoritative Zones](#authoritative-zones)
- [Security Policies (RPZ)](#security-policies-rpz)
- [Web Interface Settings](#web-interface-settings)
- [Performance Tuning](#performance-tuning)
- [Monitoring Configuration](#monitoring-configuration)

## DNS Server Configuration

### BIND9 Core Settings

The main BIND9 configuration is located at `/etc/bind/named.conf.options`:

```bind
options {
    directory "/var/cache/bind";
    
    // Recursion settings
    recursion yes;
    allow-recursion { 
        192.168.0.0/16; 
        10.0.0.0/8; 
        172.16.0.0/12; 
        127.0.0.0/8; 
    };
    
    // Cache settings
    max-cache-size 1G;
    max-cache-ttl 86400;    // 24 hours
    max-ncache-ttl 3600;    // 1 hour
    
    // Forwarders (public DNS)
    forwarders {
        1.1.1.1;
        1.0.0.1;
        8.8.8.8;
        8.8.4.4;
        9.9.9.9;
    };
    forward first;
    
    // Security settings
    version "DNS Server";
    hostname "dns.example.com";
    server-id "dns01";
    
    // Rate limiting (DDoS protection)
    rate-limit {
        responses-per-second 10;
        window 5;
        slip 2;
    };
    
    // Query logging (optional)
    querylog yes;
    
    // DNSSEC validation
    dnssec-validation auto;
    
    // Statistics
    statistics-channels {
        inet 127.0.0.1 port 8053 allow { 127.0.0.1; };
    };
    
    // Logging channels
    channel query_log {
        file "/var/log/bind/queries.log" versions 10 size 100M;
        print-time yes;
        print-category yes;
        print-severity yes;
        severity info;
    };
    
    channel security_log {
        file "/var/log/bind/security.log" versions 5 size 50M;
        print-time yes;
        print-category yes;
        print-severity yes;
        severity notice;
    };
};

// Logging configuration
logging {
    category queries { query_log; };
    category security { security_log; };
    category rpz { security_log; };
};
```

### Access Control Lists (ACLs)

Define network access groups in `/etc/bind/named.conf.local`:

```bind
// Define ACLs
acl "internal_networks" {
    192.168.0.0/16;
    10.0.0.0/8;
    172.16.0.0/12;
    127.0.0.0/8;
};

acl "ad_servers" {
    192.168.1.10;
    192.168.1.11;
    192.168.1.12;
};

acl "dmz_servers" {
    192.168.100.0/24;
};
```

## Conditional Forwarding

Configure different DNS resolution paths for different domain types.

### Active Directory Domains

Forward AD-related queries to domain controllers:

```bind
// Active Directory zones
zone "corp.local" IN {
    type forward;
    forward only;
    forwarders { 
        192.168.1.10;  // Primary DC
        192.168.1.11;  // Secondary DC
        192.168.1.12;  // Backup DC
    };
};

zone "subsidiary.corp" IN {
    type forward;
    forward only;
    forwarders { 
        192.168.50.5;
        192.168.50.6;
    };
};
```

### Internal/Intranet Zones

Route internal network queries to dedicated DNS servers:

```bind
// Intranet zones
zone "intranet.company" IN {
    type forward;
    forward only;
    forwarders { 
        10.10.10.5;
        10.10.10.6;
    };
};

zone "research.local" IN {
    type forward;
    forward only;
    forwarders { 
        10.20.0.1;
        10.20.0.2;
    };
};
```

### Reverse DNS Zones

Configure reverse DNS lookups:

```bind
// Reverse zones for internal networks
zone "1.168.192.in-addr.arpa" IN {
    type forward;
    forward only;
    forwarders { 
        192.168.1.10;
        192.168.1.11;
    };
};

zone "10.10.10.in-addr.arpa" IN {
    type forward;
    forward only;
    forwarders { 
        10.10.10.5;
        10.10.10.6;
    };
};
```

### Web Interface Configuration

Configure forwarders through the web interface:

1. **Navigate to Forwarders Section**
2. **Add New Forwarder Group**:
   - **Name**: Corporate AD
   - **Type**: Active Directory
   - **Domains**: corp.local, subsidiary.corp
   - **Servers**: 192.168.1.10, 192.168.1.11, 192.168.1.12
   - **Health Check**: Enabled

3. **Configure Failover**:
   - **Primary**: 192.168.1.10
   - **Secondary**: 192.168.1.11
   - **Backup**: 192.168.1.12
   - **Timeout**: 2 seconds
   - **Retry Count**: 3

## Authoritative Zones

Create and manage DNS zones hosted directly on the server.

### Creating a New Zone

#### Via Web Interface

1. **Navigate to DNS Zones**
2. **Click "Add Zone"**:
   - **Zone Name**: internal.local
   - **Type**: Master (Primary)
   - **Email**: admin@internal.local
   - **TTL**: 3600
   - **Refresh**: 3600
   - **Retry**: 1800
   - **Expire**: 604800
   - **Minimum**: 300

3. **Add DNS Records**:
   - **A Records**: Point hostnames to IP addresses
   - **CNAME Records**: Create aliases
   - **MX Records**: Configure mail routing
   - **TXT Records**: Add SPF, DMARC records
   - **SRV Records**: Service discovery

#### Manual Zone File

Create zone file `/etc/bind/zones/db.internal.local`:

```bind
$TTL 3600
@       IN  SOA internal.local. admin.internal.local. (
            2024010101  ; serial (YYYYMMDDNN)
            3600        ; refresh (1 hour)
            1800        ; retry (30 minutes)  
            604800      ; expire (1 week)
            300 )       ; minimum (5 minutes)

; Name servers
@       IN  NS  ns1.internal.local.
@       IN  NS  ns2.internal.local.

; A records
ns1     IN  A   192.168.1.100
ns2     IN  A   192.168.1.101
www     IN  A   192.168.1.200
mail    IN  A   192.168.1.201
ftp     IN  A   192.168.1.202

; CNAME records
intranet    IN  CNAME   www
webmail     IN  CNAME   mail

; MX records
@       IN  MX  10 mail.internal.local.

; TXT records (SPF, DMARC)
@       IN  TXT "v=spf1 mx a ~all"
_dmarc  IN  TXT "v=DMARC1; p=quarantine; rua=mailto:admin@internal.local"

; SRV records (Active Directory services)
_ldap._tcp          IN  SRV 0 5 389  dc1.internal.local.
_kerberos._tcp      IN  SRV 0 5 88   dc1.internal.local.
_gc._tcp            IN  SRV 0 5 3268 dc1.internal.local.
```

### Reverse DNS Zone

Create reverse zone `/etc/bind/zones/db.192.168.1`:

```bind
$TTL 3600
@       IN  SOA internal.local. admin.internal.local. (
            2024010101  ; serial
            3600        ; refresh
            1800        ; retry
            604800      ; expire
            300 )       ; minimum

; Name servers
@       IN  NS  ns1.internal.local.
@       IN  NS  ns2.internal.local.

; PTR records
100     IN  PTR ns1.internal.local.
101     IN  PTR ns2.internal.local.
200     IN  PTR www.internal.local.
201     IN  PTR mail.internal.local.
202     IN  PTR ftp.internal.local.
```

### Zone Configuration

Add zone to `/etc/bind/named.conf.local`:

```bind
// Authoritative zones
zone "internal.local" IN {
    type master;
    file "/etc/bind/zones/db.internal.local";
    allow-update { none; };
    allow-transfer { 192.168.1.101; }; // Secondary NS
    also-notify { 192.168.1.101; };
};

zone "1.168.192.in-addr.arpa" IN {
    type master;
    file "/etc/bind/zones/db.192.168.1";
    allow-update { none; };
    allow-transfer { 192.168.1.101; };
    also-notify { 192.168.1.101; };
};
```

## Security Policies (RPZ)

Response Policy Zones provide DNS-based security filtering.

### RPZ Configuration

Configure RPZ in `/etc/bind/named.conf.options`:

```bind
response-policy {
    zone "rpz.malware"      policy cname;
    zone "rpz.phishing"     policy cname;
    zone "rpz.adult"        policy cname;
    zone "rpz.social-media" policy cname;
    zone "rpz.safesearch"   policy cname;
    zone "rpz.custom"       policy cname;
} break-dnssec yes qname-wait-recurse no;
```

### Malware Protection

Create `/etc/bind/rpz/db.rpz.malware`:

```bind
$TTL 300
@   IN  SOA localhost. admin.localhost. (
    2024010101  ; serial
    3600        ; refresh  
    1800        ; retry
    604800      ; expire
    300 )       ; minimum
    IN  NS  localhost.

; Block malware domains
malware-example.com         CNAME   .
*.malware-example.com       CNAME   .
phishing-site.net          CNAME   .
trojan-host.org            CNAME   .
```

### Category Filtering

Create `/etc/bind/rpz/db.rpz.social-media`:

```bind
$TTL 300
@   IN  SOA localhost. admin.localhost. (
    2024010101  ; serial
    3600        ; refresh
    1800        ; retry  
    604800      ; expire
    300 )       ; minimum
    IN  NS  localhost.

; Block social media sites
facebook.com        CNAME   blocked.internal.local.
*.facebook.com      CNAME   blocked.internal.local.
twitter.com         CNAME   blocked.internal.local.
*.twitter.com       CNAME   blocked.internal.local.
instagram.com       CNAME   blocked.internal.local.
*.instagram.com     CNAME   blocked.internal.local.
linkedin.com        CNAME   blocked.internal.local.
*.linkedin.com      CNAME   blocked.internal.local.
```

### SafeSearch Enforcement

Create `/etc/bind/rpz/db.rpz.safesearch`:

```bind
$TTL 300
@   IN  SOA localhost. admin.localhost. (
    2024010101  ; serial
    3600        ; refresh
    1800        ; retry
    604800      ; expire
    300 )       ; minimum
    IN  NS  localhost.

; Force SafeSearch on search engines
google.com          CNAME   forcesafesearch.google.com.
*.google.com        CNAME   forcesafesearch.google.com.
youtube.com         CNAME   restrict.youtube.com.
*.youtube.com       CNAME   restrictmoderate.youtube.com.
duckduckgo.com      CNAME   safe.duckduckgo.com.
```

### Custom Block/Allow Lists

Create `/etc/bind/rpz/db.rpz.custom`:

```bind
$TTL 300
@   IN  SOA localhost. admin.localhost. (
    2024010101  ; serial
    3600        ; refresh
    1800        ; retry
    604800      ; expire
    300 )       ; minimum
    IN  NS  localhost.

; Custom blocked domains
gambling-site.com       CNAME   .
streaming-service.net   CNAME   .

; Override blocks (allowlist)
business-facebook.com   CNAME   rpz-passthru.
work-linkedin.com       CNAME   rpz-passthru.
```

### RPZ Zone Configuration

Add RPZ zones to `/etc/bind/named.conf.local`:

```bind
// RPZ Security Zones
zone "rpz.malware" IN {
    type master;
    file "/etc/bind/rpz/db.rpz.malware";
    allow-query { none; };
};

zone "rpz.phishing" IN {
    type master;
    file "/etc/bind/rpz/db.rpz.phishing";
    allow-query { none; };
};

zone "rpz.adult" IN {
    type master;
    file "/etc/bind/rpz/db.rpz.adult";
    allow-query { none; };
};

zone "rpz.social-media" IN {
    type master;
    file "/etc/bind/rpz/db.rpz.social-media";
    allow-query { none; };
};

zone "rpz.safesearch" IN {
    type master;
    file "/etc/bind/rpz/db.rpz.safesearch";
    allow-query { none; };
};

zone "rpz.custom" IN {
    type master;
    file "/etc/bind/rpz/db.rpz.custom";
    allow-query { none; };
};
```

## Web Interface Settings

### Backend Configuration

Configure the FastAPI backend in `/opt/hybrid-dns-server/backend/.env`:

```bash
# Database Configuration
DATABASE_URL=postgresql://dns_user:password@localhost/hybrid_dns

# Security Settings
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Admin Account
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-admin-password

# Two-Factor Authentication
ENABLE_2FA=true
ISSUER_NAME="Hybrid DNS Server"

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=3600

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/hybrid-dns/backend.log
```

### Authentication Settings

Configure authentication options:

```python
# Backend configuration
AUTH_SETTINGS = {
    "password_min_length": 12,
    "require_special_chars": True,
    "require_numbers": True,
    "require_uppercase": True,
    "max_login_attempts": 5,
    "lockout_duration": 900,  # 15 minutes
    "session_timeout": 1800,  # 30 minutes
}

# Two-factor authentication
TOTP_SETTINGS = {
    "issuer": "Hybrid DNS Server",
    "window": 1,
    "backup_codes": 10,
}
```

### User Management

Create additional users via web interface or API:

```bash
# Create user via API
curl -X POST http://localhost:8000/api/auth/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator",
    "email": "operator@example.com",
    "password": "SecurePassword123!",
    "role": "user"
  }'
```

## Performance Tuning

### Memory Configuration

Adjust BIND9 memory usage based on server resources:

```bind
options {
    // Cache size (adjust based on available RAM)
    max-cache-size 2G;          // 2GB cache for busy servers
    max-cache-ttl 86400;        // 24 hours
    max-ncache-ttl 3600;        // 1 hour negative cache
    
    // Memory usage limits
    datasize 512M;              // Maximum memory per server process
    stacksize 8M;               // Stack size limit
    
    // Client limits
    clients-per-query 10;       // Max clients per query
    max-clients-per-query 100;  // Absolute maximum
    
    // Recursive clients
    recursive-clients 1000;     // Concurrent recursive queries
    tcp-clients 100;            // TCP connections
};
```

### Query Processing

Optimize query processing:

```bind
options {
    // Resolver configuration
    resolver-query-timeout 10;  // Query timeout (seconds)
    max-recursion-depth 7;      // Recursion depth limit
    max-recursion-queries 75;   // Max queries per recursion
    
    // Prefetch configuration
    prefetch 2 9;               // Prefetch when TTL <= 2 and >= 9
    
    // Query minimization
    qname-minimization relaxed; // Improve privacy
    
    // DNSSEC configuration
    dnssec-validation auto;
    dnssec-lookaside auto;
    
    // Response policy zones
    response-policy {
        zone "rpz.malware" policy cname;
    } qname-wait-recurse no;    // Don't wait for recursion
};
```

### Network Optimization

Configure network settings:

```bind
options {
    // Network interfaces
    listen-on port 53 { 
        192.168.1.100;      // Primary interface
        127.0.0.1;          // Loopback
    };
    listen-on-v6 port 53 { ::1; };
    
    // TCP configuration
    tcp-listen-queue 10;    // TCP listen queue size
    transfer-format many-answers;  // Zone transfer format
    transfers-in 10;        // Concurrent inbound transfers
    transfers-out 10;       // Concurrent outbound transfers
    transfers-per-ns 2;     // Transfers per name server
};
```

### System-Level Tuning

Optimize the system for DNS performance:

```bash
# /etc/sysctl.d/99-dns-performance.conf

# Network buffer sizes
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144
net.core.wmem_max = 16777216

# UDP buffer sizes
net.core.netdev_max_backlog = 5000
net.ipv4.udp_mem = 102400 873800 16777216
net.ipv4.udp_rmem_min = 8192
net.ipv4.udp_wmem_min = 8192

# Connection tracking (for RPZ)
net.netfilter.nf_conntrack_max = 1000000

# File descriptor limits
fs.file-max = 1000000

# Apply settings
sudo sysctl -p /etc/sysctl.d/99-dns-performance.conf
```

### PostgreSQL Optimization

Tune PostgreSQL for DNS logging:

```postgresql
-- /etc/postgresql/14/main/postgresql.conf

# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Checkpoint settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB

# Logging optimization
log_statement = 'none'
log_min_duration_statement = 1000

# Connection settings
max_connections = 200
```

## Monitoring Configuration

### Query Logging

Configure detailed query logging:

```bind
logging {
    channel query_log {
        file "/var/log/bind/queries.log" 
        versions 10 size 100M;
        print-time yes;
        print-category yes;
        severity info;
    };
    
    channel security_log {
        file "/var/log/bind/security.log" 
        versions 5 size 50M;
        print-time yes;
        print-category yes;
        severity notice;
    };
    
    channel performance_log {
        file "/var/log/bind/performance.log"
        versions 3 size 10M;
        print-time yes;
        severity debug 3;
    };
    
    // Log categories
    category queries { query_log; };
    category security { security_log; };
    category rpz { security_log; };
    category rate-limit { security_log; };
    category resolver { performance_log; };
    category cname { performance_log; };
};
```

### Statistics Collection

Enable BIND9 statistics:

```bind
options {
    // Statistics channels
    statistics-channels {
        inet 127.0.0.1 port 8053 allow { 127.0.0.1; };
        inet 192.168.1.100 port 8053 allow { 192.168.1.0/24; };
    };
    
    // Zone statistics
    zone-statistics yes;
    
    // Query statistics
    querylog yes;
};

// Statistics configuration
statistics-channels {
    inet * port 8053 allow { localhost; 192.168.1.0/24; };
};
```

### Health Monitoring

Configure health checks:

```bash
# Health check script
#!/bin/bash
# /opt/hybrid-dns-server/scripts/health-check.sh

# Check BIND9 status
if ! systemctl is-active --quiet bind9; then
    echo "CRITICAL: BIND9 service is down"
    exit 2
fi

# Test DNS resolution
if ! dig @localhost google.com +short >/dev/null; then
    echo "CRITICAL: DNS resolution failed"
    exit 2
fi

# Check statistics server
if ! curl -s http://localhost:8053/ >/dev/null; then
    echo "WARNING: Statistics server not responding"
    exit 1
fi

echo "OK: All DNS services operational"
exit 0
```

### Log Rotation

Configure log rotation:

```bash
# /etc/logrotate.d/hybrid-dns
/var/log/bind/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 bind bind
    postrotate
        /usr/sbin/rndc reconfig >/dev/null 2>&1 || true
    endscript
}

/var/log/hybrid-dns/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 dns-admin dns-admin
    postrotate
        systemctl reload hybrid-dns-backend >/dev/null 2>&1 || true
    endscript
}
```

## Configuration Validation

### BIND9 Configuration Check

```bash
# Check main configuration
sudo named-checkconf

# Check zone files
sudo named-checkzone internal.local /etc/bind/zones/db.internal.local
sudo named-checkzone 1.168.192.in-addr.arpa /etc/bind/zones/db.192.168.1

# Test RPZ configuration
sudo named-checkzone rpz.malware /etc/bind/rpz/db.rpz.malware
```

### Configuration Reload

```bash
# Reload BIND9 configuration
sudo rndc reconfig

# Reload specific zone
sudo rndc reload internal.local

# Flush cache
sudo rndc flush
```

### Testing Configuration

```bash
# Test forwarders
dig @localhost corp.local
dig @localhost internal.local

# Test RPZ blocking
dig @localhost malware-example.com

# Test performance
time dig @localhost google.com
```

## Best Practices

### Security Best Practices

1. **Minimal Permissions**: Run services with least privilege
2. **Regular Updates**: Keep BIND9 and system updated
3. **Firewall Rules**: Restrict access to DNS ports
4. **Monitoring**: Implement comprehensive logging
5. **Backup Configuration**: Regular configuration backups

### Performance Best Practices

1. **Memory Allocation**: Size caches appropriately
2. **Query Limits**: Set reasonable client limits
3. **Network Optimization**: Tune network buffers
4. **Log Management**: Rotate logs to prevent disk issues
5. **Monitor Resources**: Watch CPU, memory, and disk usage

### Operational Best Practices

1. **Change Management**: Test configuration changes
2. **Documentation**: Maintain up-to-date documentation
3. **Monitoring**: Implement alerting for critical issues
4. **Backup Strategy**: Regular automated backups
5. **Disaster Recovery**: Test recovery procedures

---

This configuration guide covers the essential settings for running a production Hybrid DNS Server. For additional configuration options, consult the BIND9 documentation and the application-specific guides.