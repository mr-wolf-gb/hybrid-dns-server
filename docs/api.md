# API Documentation

The Hybrid DNS Server provides a comprehensive REST API for managing DNS configurations, security policies, and monitoring. This document covers all available endpoints and their usage.

## Base URL

```
https://your-dns-server/api
```

## Authentication

All API endpoints require authentication via JWT tokens.

### Login

```http
POST /api/auth/login
```

**Request Body:**
```json
{
    "username": "admin",
    "password": "your_password",
    "totp_code": "123456"  // Optional, required if 2FA enabled
}
```

**Response:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "two_factor_enabled": true
    }
}
```

### Refresh Token

```http
POST /api/auth/refresh
```

**Request Headers:**
```
Authorization: Bearer <refresh_token>
```

**Response:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_in": 1800
}
```

## DNS Zones Management

### List Zones

```http
GET /api/zones
```

**Response:**
```json
{
    "zones": [
        {
            "id": 1,
            "name": "internal.local",
            "type": "master",
            "serial": 2024010101,
            "refresh": 3600,
            "retry": 1800,
            "expire": 604800,
            "minimum": 300,
            "email": "admin@internal.local",
            "status": "active",
            "record_count": 15,
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T15:30:00Z"
        }
    ],
    "total": 1
}
```

### Create Zone

```http
POST /api/zones
```

**Request Body:**
```json
{
    "name": "new-zone.local",
    "type": "master",
    "email": "admin@new-zone.local",
    "ttl": 3600,
    "refresh": 3600,
    "retry": 1800,
    "expire": 604800,
    "minimum": 300
}
```

**Response:**
```json
{
    "id": 2,
    "name": "new-zone.local",
    "type": "master",
    "serial": 2024010201,
    "status": "active",
    "created_at": "2024-01-02T10:00:00Z"
}
```

### Update Zone

```http
PUT /api/zones/{zone_id}
```

**Request Body:**
```json
{
    "email": "newadmin@new-zone.local",
    "ttl": 7200,
    "refresh": 7200
}
```

### Delete Zone

```http
DELETE /api/zones/{zone_id}
```

**Response:**
```json
{
    "message": "Zone deleted successfully"
}
```

## DNS Records Management

### List Records

```http
GET /api/zones/{zone_id}/records
```

**Query Parameters:**
- `type`: Filter by record type (A, AAAA, CNAME, MX, TXT, SRV, PTR)
- `name`: Filter by record name
- `page`: Page number (default: 1)
- `limit`: Records per page (default: 50)

**Response:**
```json
{
    "records": [
        {
            "id": 1,
            "name": "www",
            "type": "A",
            "value": "192.168.1.200",
            "ttl": 3600,
            "priority": null,
            "weight": null,
            "port": null,
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z"
        },
        {
            "id": 2,
            "name": "@",
            "type": "MX",
            "value": "mail.internal.local.",
            "ttl": 3600,
            "priority": 10,
            "weight": null,
            "port": null,
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z"
        }
    ],
    "total": 2,
    "page": 1,
    "pages": 1
}
```

### Create Record

```http
POST /api/zones/{zone_id}/records
```

**Request Body (A Record):**
```json
{
    "name": "server1",
    "type": "A",
    "value": "192.168.1.150",
    "ttl": 3600
}
```

**Request Body (MX Record):**
```json
{
    "name": "@",
    "type": "MX",
    "value": "mail2.internal.local.",
    "ttl": 3600,
    "priority": 20
}
```

**Request Body (SRV Record):**
```json
{
    "name": "_ldap._tcp",
    "type": "SRV",
    "value": "dc1.internal.local.",
    "ttl": 3600,
    "priority": 0,
    "weight": 5,
    "port": 389
}
```

### Update Record

```http
PUT /api/records/{record_id}
```

### Delete Record

```http
DELETE /api/records/{record_id}
```

## DNS Forwarders Management

### List Forwarders

```http
GET /api/forwarders
```

**Response:**
```json
{
    "forwarders": [
        {
            "id": 1,
            "name": "Corporate AD",
            "type": "active_directory",
            "domains": ["corp.local", "subsidiary.corp"],
            "servers": [
                {
                    "ip": "192.168.1.10",
                    "port": 53,
                    "priority": 1,
                    "status": "healthy",
                    "response_time": 15.2,
                    "last_check": "2024-01-01T15:30:00Z"
                },
                {
                    "ip": "192.168.1.11", 
                    "port": 53,
                    "priority": 2,
                    "status": "healthy",
                    "response_time": 18.7,
                    "last_check": "2024-01-01T15:30:00Z"
                }
            ],
            "enabled": true,
            "created_at": "2024-01-01T10:00:00Z"
        }
    ],
    "total": 1
}
```

### Create Forwarder

```http
POST /api/forwarders
```

**Request Body:**
```json
{
    "name": "Internal Network",
    "type": "intranet",
    "domains": ["intranet.company", "internal.net"],
    "servers": [
        {"ip": "10.10.10.5", "port": 53, "priority": 1},
        {"ip": "10.10.10.6", "port": 53, "priority": 2}
    ],
    "enabled": true,
    "health_check": true
}
```

### Test Forwarder

```http
POST /api/forwarders/{forwarder_id}/test
```

**Response:**
```json
{
    "results": [
        {
            "server": "192.168.1.10",
            "status": "success",
            "response_time": 12.5,
            "query_domain": "corp.local",
            "resolved_ips": ["192.168.1.100", "192.168.1.101"]
        },
        {
            "server": "192.168.1.11",
            "status": "timeout",
            "response_time": null,
            "error": "Connection timeout after 5 seconds"
        }
    ]
}
```

## Security Policies (RPZ)

### List RPZ Rules

```http
GET /api/security/rpz
```

**Query Parameters:**
- `category`: Filter by category (malware, phishing, adult, social_media, etc.)
- `action`: Filter by action (block, redirect, allow)
- `search`: Search domains

**Response:**
```json
{
    "rules": [
        {
            "id": 1,
            "domain": "malware-example.com",
            "category": "malware",
            "action": "block",
            "policy_zone": "rpz.malware",
            "description": "Known malware distribution site",
            "enabled": true,
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z"
        }
    ],
    "total": 1
}
```

### Create RPZ Rule

```http
POST /api/security/rpz
```

**Request Body:**
```json
{
    "domain": "suspicious-site.com",
    "category": "custom",
    "action": "block",
    "description": "Blocked by administrator",
    "enabled": true
}
```

### Bulk Import RPZ Rules

```http
POST /api/security/rpz/import
```

**Request Body:**
```json
{
    "category": "malware",
    "source": "threat_feed",
    "domains": [
        "malware1.com",
        "malware2.net",
        "phishing-site.org"
    ]
}
```

### Update Threat Feeds

```http
POST /api/security/threats/update
```

**Response:**
```json
{
    "updated_feeds": [
        {
            "name": "malware_domains",
            "domains_added": 1523,
            "domains_updated": 45,
            "last_updated": "2024-01-01T15:30:00Z"
        }
    ],
    "total_rules": 15678,
    "status": "success"
}
```

## Query Logs

### List Query Logs

```http
GET /api/logs/queries
```

**Query Parameters:**
- `client_ip`: Filter by client IP
- `domain`: Filter by domain
- `record_type`: Filter by DNS record type
- `blocked`: Filter blocked queries (true/false)
- `start_date`: Start date (ISO format)
- `end_date`: End date (ISO format)
- `page`: Page number
- `limit`: Logs per page (max 1000)

**Response:**
```json
{
    "logs": [
        {
            "id": 12345,
            "timestamp": "2024-01-01T15:30:45.123Z",
            "client_ip": "192.168.1.50",
            "client_port": 54321,
            "domain": "google.com",
            "record_type": "A",
            "response_code": "NOERROR",
            "query_flags": "RD",
            "blocked": false,
            "policy_zone": null,
            "policy_action": null,
            "response_time": 25.4,
            "cache_hit": true
        },
        {
            "id": 12346,
            "timestamp": "2024-01-01T15:31:02.456Z",
            "client_ip": "192.168.1.75",
            "client_port": 45678,
            "domain": "malware-example.com",
            "record_type": "A",
            "response_code": "NXDOMAIN",
            "query_flags": "RD",
            "blocked": true,
            "policy_zone": "rpz.malware",
            "policy_action": "CNAME",
            "response_time": 1.2,
            "cache_hit": false
        }
    ],
    "total": 2,
    "page": 1,
    "pages": 1
}
```

### Export Query Logs

```http
GET /api/logs/queries/export
```

**Query Parameters:** Same as list logs
**Additional Parameters:**
- `format`: Export format (csv, json)

**Response:** File download with logs in requested format

## Analytics & Statistics

### Dashboard Statistics

```http
GET /api/dashboard/stats
```

**Response:**
```json
{
    "queries_per_hour": 1250,
    "blocked_per_hour": 85,
    "cache_hit_rate": 89.5,
    "top_domains": [
        {"domain": "google.com", "count": 245},
        {"domain": "microsoft.com", "count": 189},
        {"domain": "cloudflare.com", "count": 156}
    ],
    "top_clients": [
        {"client_ip": "192.168.1.50", "count": 89},
        {"client_ip": "192.168.1.75", "count": 67},
        {"client_ip": "192.168.1.100", "count": 54}
    ],
    "blocked_categories": [
        {"category": "malware", "count": 45},
        {"category": "phishing", "count": 23},
        {"category": "social_media", "count": 17}
    ],
    "forwarder_health": [
        {"name": "Corporate AD", "status": "healthy", "avg_response": 15.2},
        {"name": "Public DNS", "status": "healthy", "avg_response": 28.7}
    ]
}
```

### Query Volume Trends

```http
GET /api/analytics/query-trends
```

**Query Parameters:**
- `period`: Time period (hour, day, week, month)
- `start_date`: Start date
- `end_date`: End date

**Response:**
```json
{
    "period": "hour",
    "data": [
        {"timestamp": "2024-01-01T14:00:00Z", "queries": 1150, "blocked": 75},
        {"timestamp": "2024-01-01T15:00:00Z", "queries": 1250, "blocked": 85},
        {"timestamp": "2024-01-01T16:00:00Z", "queries": 980, "blocked": 62}
    ]
}
```

### Client Analytics

```http
GET /api/analytics/clients
```

**Response:**
```json
{
    "clients": [
        {
            "client_ip": "192.168.1.50",
            "hostname": "workstation-01.corp.local",
            "queries_total": 1250,
            "blocked_total": 45,
            "first_seen": "2024-01-01T08:00:00Z",
            "last_seen": "2024-01-01T16:30:00Z",
            "top_domains": ["google.com", "microsoft.com", "github.com"]
        }
    ]
}
```

## System Management

### System Health

```http
GET /api/system/health
```

**Response:**
```json
{
    "status": "healthy",
    "services": {
        "bind9": {
            "status": "running",
            "uptime": 86400,
            "memory_usage": "245MB",
            "cpu_usage": 5.2
        },
        "postgresql": {
            "status": "running",
            "connections": 25,
            "database_size": "1.2GB"
        },
        "redis": {
            "status": "running",
            "memory_usage": "45MB",
            "hit_rate": 92.5
        }
    },
    "system": {
        "cpu_usage": 15.4,
        "memory_usage": 67.8,
        "disk_usage": 34.2,
        "load_average": [0.85, 0.92, 1.05]
    }
}
```

### Configuration Backup

```http
POST /api/system/backup
```

**Request Body:**
```json
{
    "include_logs": false,
    "compress": true
}
```

**Response:**
```json
{
    "backup_id": "backup_20240101_153045",
    "filename": "hybrid_dns_backup_20240101_153045.tar.gz",
    "size": "15.2MB",
    "created_at": "2024-01-01T15:30:45Z"
}
```

### Cache Management

```http
POST /api/system/cache/{action}
```

**Actions:** `flush`, `stats`, `dump`

**Response for flush:**
```json
{
    "message": "DNS cache flushed successfully",
    "entries_cleared": 15672
}
```

**Response for stats:**
```json
{
    "cache_size": "512MB",
    "entries": 25643,
    "hit_rate": 89.5,
    "memory_usage": 67.2
}
```

## User Management

### List Users

```http
GET /api/users
```

**Response:**
```json
{
    "users": [
        {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "role": "admin",
            "enabled": true,
            "two_factor_enabled": true,
            "last_login": "2024-01-01T15:30:00Z",
            "created_at": "2024-01-01T10:00:00Z"
        }
    ],
    "total": 1
}
```

### Create User

```http
POST /api/users
```

**Request Body:**
```json
{
    "username": "operator",
    "email": "operator@example.com",
    "password": "SecurePassword123!",
    "role": "user",
    "enabled": true
}
```

### Enable Two-Factor Authentication

```http
POST /api/users/{user_id}/2fa/enable
```

**Response:**
```json
{
    "secret": "JBSWY3DPEHPK3PXP",
    "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "backup_codes": [
        "12345678",
        "87654321",
        "11223344"
    ]
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input data",
        "details": {
            "domain": ["Domain name is required"],
            "type": ["Invalid record type"]
        }
    }
}
```

### Error Codes

- `AUTHENTICATION_REQUIRED` (401)
- `INSUFFICIENT_PERMISSIONS` (403)
- `RESOURCE_NOT_FOUND` (404)
- `VALIDATION_ERROR` (400)
- `RATE_LIMIT_EXCEEDED` (429)
- `INTERNAL_SERVER_ERROR` (500)

## Rate Limiting

API endpoints are rate-limited per user:
- **Standard endpoints**: 100 requests per hour
- **Query logs**: 20 requests per hour
- **Authentication**: 10 attempts per hour

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1704121845
```

## WebSocket API

Real-time data streaming via WebSocket connection:

```javascript
// Connect to WebSocket
const ws = new WebSocket('wss://your-dns-server/api/ws');

// Authentication
ws.send(JSON.stringify({
    type: 'authenticate',
    token: 'your_jwt_token'
}));

// Subscribe to query logs
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'query_logs'
}));

// Subscribe to system stats
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'system_stats'
}));
```

**Message Types:**
- `query_log`: Real-time DNS queries
- `system_stats`: System performance metrics
- `security_event`: Security alerts and blocks
- `forwarder_health`: Forwarder status changes

## SDK Examples

### Python

```python
import requests

class HybridDNSAPI:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.session = requests.Session()
        self.authenticate(username, password)
    
    def authenticate(self, username, password):
        response = self.session.post(f"{self.base_url}/auth/login", json={
            "username": username,
            "password": password
        })
        data = response.json()
        self.session.headers.update({
            "Authorization": f"Bearer {data['access_token']}"
        })
    
    def get_zones(self):
        response = self.session.get(f"{self.base_url}/zones")
        return response.json()
    
    def create_record(self, zone_id, name, record_type, value, ttl=3600):
        response = self.session.post(f"{self.base_url}/zones/{zone_id}/records", json={
            "name": name,
            "type": record_type,
            "value": value,
            "ttl": ttl
        })
        return response.json()

# Usage
api = HybridDNSAPI("https://dns.example.com/api", "admin", "password")
zones = api.get_zones()
api.create_record(1, "server1", "A", "192.168.1.100")
```

### JavaScript

```javascript
class HybridDNSAPI {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.token = null;
    }
    
    async authenticate(username, password, totpCode = null) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password, totp_code: totpCode})
        });
        const data = await response.json();
        this.token = data.access_token;
        return data;
    }
    
    async getZones() {
        const response = await fetch(`${this.baseUrl}/zones`, {
            headers: {'Authorization': `Bearer ${this.token}`}
        });
        return response.json();
    }
    
    async createRecord(zoneId, name, type, value, ttl = 3600) {
        const response = await fetch(`${this.baseUrl}/zones/${zoneId}/records`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({name, type, value, ttl})
        });
        return response.json();
    }
}

// Usage
const api = new HybridDNSAPI('https://dns.example.com/api');
await api.authenticate('admin', 'password');
const zones = await api.getZones();
await api.createRecord(1, 'server1', 'A', '192.168.1.100');
```

---

This API documentation provides comprehensive coverage of all available endpoints. For interactive API documentation, visit `/docs` (Swagger UI) on your Hybrid DNS Server instance.