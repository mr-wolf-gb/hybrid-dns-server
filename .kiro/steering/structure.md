# Project Structure & Organization

## Root Directory Layout

```
hybrid-dns-server/
├── README.md                     # Main project documentation
├── docs/                        # Comprehensive documentation
├── install.sh                   # Automated installation script
├── docker-compose.yml           # Container orchestration
├── backend/                     # FastAPI backend application
├── frontend/                    # React web interface
├── bind9/                       # BIND9 DNS server configuration
├── monitoring/                  # Log monitoring service
├── systemd/                     # System service configurations
├── scripts/                     # Maintenance and utility scripts
└── docs/                        # Comprehensive documentation
```

## Backend Structure (`backend/`)

```
backend/
├── Dockerfile                   # Container build configuration
├── main.py                      # FastAPI application entry point
├── requirements.txt             # Python dependencies
├── alembic/                     # Database migrations
│   └── versions/               # Migration files
├── examples/                    # Sample data and import examples
│   ├── domains.csv             # Sample domain lists
│   ├── malware_domains.txt     # Sample threat data
│   ├── rules.json              # Sample RPZ rules
│   ├── sample_zone.bind        # BIND zone file examples
│   ├── sample_zone.csv         # CSV import examples
│   ├── sample_zone.json        # JSON import examples
│   └── zone_import_examples.md # Import documentation
└── app/                         # Application source code
    ├── core/                    # Core configuration and utilities
    │   ├── config.py           # Application settings
    │   ├── database.py         # Database connection setup
    │   ├── logging_config.py   # Logging configuration
    │   ├── security.py         # Security utilities
    │   ├── auth_context.py     # Authentication context
    │   ├── dependencies.py     # FastAPI dependencies
    │   ├── exceptions.py       # Custom exceptions
    │   ├── error_handlers.py   # Error handling
    │   ├── monitoring_config.py # Monitoring configuration
    │   ├── validation_helpers.py # Input validation
    │   └── websocket_auth.py   # WebSocket authentication
    ├── api/                     # REST API endpoints
    │   ├── routes.py           # Main route aggregator
    │   ├── endpoints/          # Individual endpoint modules
    │   │   ├── auth.py         # Authentication endpoints
    │   │   ├── backup.py       # Backup management
    │   │   ├── dashboard.py    # Dashboard data
    │   │   ├── dns_records.py  # DNS record management
    │   │   ├── events.py       # Event management
    │   │   ├── forwarders.py   # DNS forwarder configuration
    │   │   ├── forwarder_templates.py # Forwarder templates
    │   │   ├── health.py       # Health checks
    │   │   ├── realtime.py     # Real-time data
    │   │   ├── reports.py      # Reporting endpoints
    │   │   ├── rollback.py     # Configuration rollback
    │   │   ├── rpz.py          # Response Policy Zones
    │   │   ├── system.py       # System management
    │   │   ├── users.py        # User management
    │   │   ├── websocket.py    # WebSocket endpoints
    │   │   └── zones.py        # DNS zone management
    │   └── routes/             # Additional route modules
    │       ├── analytics.py    # Analytics routes
    │       └── websocket_demo.py # WebSocket demo
    ├── services/                # Business logic services
    │   ├── base_service.py     # Base service class
    │   ├── bind_service.py     # BIND9 management
    │   ├── monitoring_service.py # Query log monitoring
    │   ├── health_service.py   # System health checks
    │   ├── zone_service.py     # DNS zone management
    │   ├── record_service.py   # DNS record management
    │   ├── rpz_service.py      # RPZ management
    │   ├── forwarder_service.py # Forwarder management
    │   ├── forwarder_template_service.py # Forwarder templates
    │   ├── threat_feed_service.py # Threat intelligence
    │   ├── backup_service.py   # Backup operations
    │   ├── reporting_service.py # Report generation
    │   ├── analytics_service.py # Analytics processing
    │   ├── event_service.py    # Event management
    │   ├── event_integration.py # Event integration
    │   ├── websocket_events.py # WebSocket event handling
    │   ├── background_tasks.py # Background job processing
    │   ├── scheduler_service.py # Task scheduling
    │   ├── acl_service.py      # Access control lists
    │   ├── record_history_service.py # Record change history
    │   ├── record_import_export_service.py # Import/export
    │   └── record_template_service.py # Record templates
    ├── models/                  # Database models
    │   ├── auth.py             # Authentication models
    │   ├── dns.py              # DNS-related models
    │   ├── events.py           # Event models
    │   ├── monitoring.py       # Monitoring models
    │   ├── security.py         # Security models
    │   └── system.py           # System models
    ├── schemas/                 # Pydantic schemas
    │   ├── auth.py             # Authentication schemas
    │   ├── dns.py              # DNS schemas
    │   ├── monitoring.py       # Monitoring schemas
    │   ├── reports.py          # Report schemas
    │   ├── security.py         # Security schemas
    │   ├── system.py           # System schemas
    │   └── examples.py         # Schema examples
    ├── templates/               # Jinja2 templates for config generation
    │   ├── config/             # BIND9 configuration templates
    │   │   ├── acl.j2          # Access control lists
    │   │   ├── forwarders.j2   # Forwarder configuration
    │   │   ├── logging.j2      # Logging configuration
    │   │   └── statistics.j2   # Statistics configuration
    │   ├── zones/              # Zone file templates
    │   │   ├── master.j2       # Master zone template
    │   │   ├── reverse.j2      # Reverse zone template
    │   │   └── slave.j2        # Slave zone template
    │   ├── rpz_*.j2            # RPZ templates (multiple files)
    │   ├── threat_feed_*.j2    # Threat feed templates
    │   ├── template_mapping.py # Template mapping logic
    │   ├── template_validator.py # Template validation
    │   └── threat_feed_template_validator.py # Threat feed validation
    ├── utils/                   # Utility functions
    └── websocket/               # WebSocket handling
        └── manager.py          # WebSocket connection manager
```

## Frontend Structure (`frontend/`)

```
frontend/
├── Dockerfile                   # Container build configuration
├── package.json                 # Node.js dependencies and scripts
├── vite.config.ts              # Vite build configuration
├── tailwind.config.js          # TailwindCSS configuration
├── tsconfig.json               # TypeScript configuration
├── nginx.conf                  # Nginx configuration for production
├── index.html                  # Main HTML template
└── src/                        # React application source
    ├── components/             # Reusable UI components
    ├── pages/                  # Application pages/routes
    ├── services/               # API service layer
    ├── contexts/               # React contexts for state
    ├── hooks/                  # Custom React hooks
    ├── types/                  # TypeScript type definitions
    └── utils/                  # Utility functions
```

## DNS Configuration (`bind9/`)

```
bind9/
├── Dockerfile                   # BIND9 container configuration
├── named.conf.options          # Main BIND9 configuration
├── named.conf.local            # Zone definitions and ACLs
├── zones.conf                  # Zone configuration file
├── zones/                      # DNS zone files (created dynamically)
└── rpz/                        # Response Policy Zone files (created dynamically)
```

## System Services (`systemd/`)

```
systemd/
├── hybrid-dns-backend.service      # FastAPI backend service
├── hybrid-dns-maintenance.service  # Maintenance tasks
└── hybrid-dns-maintenance.timer    # Scheduled maintenance
```

## Monitoring Service (`monitoring/`)

```
monitoring/
├── Dockerfile                      # Container build for monitoring
├── requirements.txt                # Python dependencies for monitoring
└── monitor.py                      # DNS log parser and analytics
```

## Maintenance Scripts (`scripts/`)

```
scripts/
├── backup.sh                       # Backup utility script
├── maintenance.sh                  # Daily maintenance tasks
└── optimize_monitoring.py          # Monitoring optimization
```

## Documentation (`docs/`)

```
docs/
├── installation.md              # Detailed installation guide
├── configuration.md             # Configuration reference
├── api.md                      # Complete API documentation
├── troubleshooting.md          # Common issues and solutions
├── security.md                 # Security best practices
└── backup-recovery.md          # Backup and disaster recovery
```

## File Naming Conventions

### Python Files
- **Snake case**: `dns_service.py`, `health_check.py`
- **Classes**: PascalCase (`DNSService`, `HealthChecker`)
- **Functions/variables**: snake_case (`get_zones`, `zone_config`)
- **Constants**: UPPER_SNAKE_CASE (`DEFAULT_TTL`, `MAX_RETRIES`)

### TypeScript/React Files
- **Components**: PascalCase (`DNSZoneList.tsx`, `SecurityPolicies.tsx`)
- **Hooks**: camelCase with `use` prefix (`useAuth.ts`, `useDNSZones.ts`)
- **Services**: camelCase (`apiService.ts`, `authService.ts`)
- **Types**: PascalCase (`DNSZone`, `SecurityRule`)

### Configuration Files
- **BIND9 zones**: `db.zone-name` (`db.internal.local`)
- **RPZ files**: `db.rpz.category` (`db.rpz.malware`)
- **Environment**: `.env`, `.env.local`, `.env.production`

## Directory Conventions

### Backend Organization
- **Core utilities** in `app/core/`
- **API endpoints** grouped by feature in `app/api/routes/`
- **Business logic** in `app/services/`
- **Database models** in `app/models/`
- **Tests** mirror source structure in `tests/`

### Frontend Organization
- **Reusable components** in `src/components/`
- **Page components** in `src/pages/`
- **API calls** centralized in `src/services/`
- **Type definitions** in `src/types/`
- **Shared utilities** in `src/utils/`

### Configuration Management
- **BIND9 config** in `/etc/bind/` (production) or `bind9/` (development)
- **Application config** in `/opt/hybrid-dns-server/` (production)
- **Logs** in `/var/log/hybrid-dns/` and `/var/log/bind/`
- **Backups** in `/opt/hybrid-dns-server/backups/`

## Import Patterns

### Python Imports
```python
# Standard library first
import os
import sys
from pathlib import Path

# Third-party packages
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine

# Local application imports
from app.core.config import get_settings
from app.services.dns_service import DNSService
```

### TypeScript Imports
```typescript
// React and third-party libraries
import React from 'react';
import { useQuery } from '@tanstack/react-query';

// Local components and services
import { DNSZoneList } from '@/components/DNSZoneList';
import { apiService } from '@/services/apiService';
import type { DNSZone } from '@/types/dns';
```

## Code Organization Principles

1. **Separation of Concerns**: Keep DNS logic, web API, and UI clearly separated
2. **Configuration Management**: Use environment variables and config files, never hardcode values
3. **Error Handling**: Implement comprehensive error handling at all layers
4. **Logging**: Use structured logging with appropriate levels (DEBUG, INFO, WARNING, ERROR)
5. **Security**: Follow principle of least privilege, validate all inputs
6. **Testing**: Maintain test files alongside source code with clear naming
7. **Documentation**: Include docstrings for all public functions and classes