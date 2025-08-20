# API & WebSocket Implementation

## REST API Structure

The FastAPI backend provides comprehensive REST API endpoints organized by functionality:

### Authentication & Users (`/api/auth`, `/api/users`)
- JWT-based authentication with refresh tokens
- 2FA support with TOTP (Google Authenticator, Authy)
- User management with role-based access control
- Account lockout protection and audit logging

### DNS Management
- **Zones** (`/api/zones`): Create, read, update, delete DNS zones
- **Records** (`/api/dns-records`): Full CRUD operations for DNS records
- **Forwarders** (`/api/forwarders`): Conditional forwarding configuration
- **RPZ** (`/api/rpz`): Response Policy Zone management

### System Management
- **Health** (`/api/health`): System health checks and monitoring
- **Dashboard** (`/api/dashboard`): Real-time statistics and metrics
- **System** (`/api/system`): System configuration and status
- **Backup** (`/api/backup`): Backup and restore operations

### Monitoring & Analytics
- **Events** (`/api/events`): Event logging and retrieval
- **Reports** (`/api/reports`): Report generation and analytics
- **Realtime** (`/api/realtime`): Real-time data endpoints

## WebSocket Implementation

### Real-time Features
- **Live Query Monitoring**: Real-time DNS query stream
- **System Metrics**: Live system performance data
- **Event Broadcasting**: Real-time event notifications
- **Health Status**: Live forwarder and service health updates

### WebSocket Manager
- Connection management with authentication
- Message broadcasting to subscribed clients
- Event-driven updates from backend services
- Automatic reconnection handling

### WebSocket Endpoints
- `/ws/queries`: Live DNS query stream
- `/ws/metrics`: Real-time system metrics
- `/ws/events`: Event notifications
- `/ws/health`: Health status updates

## Template System

### Jinja2 Templates
- **Zone Templates**: Master, slave, and reverse zone generation
- **RPZ Templates**: Response Policy Zone rule generation
- **Configuration Templates**: BIND9 configuration file generation
- **Threat Feed Templates**: Automated threat intelligence integration

### Template Categories
- **Config Templates** (`app/templates/config/`): BIND9 configuration
- **Zone Templates** (`app/templates/zones/`): DNS zone files
- **RPZ Templates** (`app/templates/rpz_*.j2`): Security policies
- **Threat Feed Templates** (`app/templates/threat_feed_*.j2`): Threat intelligence

## Service Architecture

### Base Service Pattern
All services inherit from `BaseService` providing:
- Database session management
- Error handling and logging
- Common CRUD operations
- Event integration

### Key Services
- **BindService**: BIND9 configuration management and reloading
- **ZoneService**: DNS zone management with template generation
- **RecordService**: DNS record CRUD operations
- **RPZService**: Response Policy Zone management
- **ForwarderService**: Conditional forwarding configuration
- **ThreatFeedService**: Threat intelligence integration
- **MonitoringService**: Query log parsing and analytics
- **HealthService**: System health monitoring
- **BackupService**: Configuration backup and restore

## Database Models

### Core Models
- **DNS Models** (`models/dns.py`): Zones, records, forwarders
- **Auth Models** (`models/auth.py`): Users, sessions, permissions
- **Security Models** (`models/security.py`): RPZ rules, threat feeds
- **Monitoring Models** (`models/monitoring.py`): Query logs, metrics
- **Event Models** (`models/events.py`): Audit logs, system events

### Schema Validation
- **Pydantic Schemas** (`schemas/`): Request/response validation
- **Input Validation**: DNS record validation, domain name validation
- **Output Serialization**: Consistent API response formats

## Background Tasks

### Celery Integration
- **Background Processing**: Long-running tasks (imports, exports)
- **Scheduled Tasks**: Maintenance, threat feed updates
- **Event Processing**: Asynchronous event handling

### Task Types
- DNS record bulk operations
- Configuration backups
- Threat feed updates
- Log processing and analytics
- Health monitoring checks

## Security Implementation

### Authentication
- JWT tokens with configurable expiration
- Refresh token rotation
- 2FA with TOTP support
- Account lockout after failed attempts

### Authorization
- Role-based access control (Admin, User)
- Endpoint-level permission checks
- Resource-level access control

### Input Validation
- Pydantic schema validation
- DNS record format validation
- Domain name validation
- IP address validation

### Security Headers
- CORS configuration
- Rate limiting with SlowAPI
- Security headers (HSTS, CSP)
- Request logging and monitoring

## Error Handling

### Exception Hierarchy
- Custom exception classes (`core/exceptions.py`)
- HTTP exception mapping
- Structured error responses
- Comprehensive error logging

### Error Response Format
```json
{
  "error": "error_code",
  "message": "Human readable message",
  "details": "Additional context",
  "timestamp": "ISO timestamp"
}
```

## API Documentation

### Interactive Documentation
- Swagger UI at `/docs`
- ReDoc at `/redoc`
- OpenAPI 3.0 specification
- Example requests and responses

### Schema Examples
- Request/response examples in schemas
- Comprehensive field documentation
- Validation error examples
- Authentication examples