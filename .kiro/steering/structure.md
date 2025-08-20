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
└── app/                         # Application source code
    ├── core/                    # Core configuration and utilities
    │   ├── config.py           # Application settings
    │   ├── database.py         # Database connection setup
    │   └── logging_config.py   # Logging configuration
    ├── api/                     # REST API endpoints
    │   └── routes/             # API route definitions
    ├── services/                # Business logic services
    │   ├── bind_service.py     # BIND9 management
    │   ├── monitoring_service.py # Query log monitoring
    │   └── health_service.py   # System health checks
    └── models/                  # Database models and schemas
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
├── zones/                      # DNS zone files
│   ├── db.internal.local       # Example authoritative zone
│   └── db.192.168.1           # Reverse DNS zone
└── rpz/                        # Response Policy Zone files
    ├── db.rpz.malware          # Malware blocking rules
    ├── db.rpz.phishing         # Phishing protection
    ├── db.rpz.adult            # Adult content filtering
    ├── db.rpz.social-media     # Social media blocking
    ├── db.rpz.safesearch       # SafeSearch enforcement
    └── db.rpz.custom           # Custom block/allow rules
```

## System Services (`systemd/`)

```
systemd/
├── hybrid-dns-backend.service      # FastAPI backend service
├── hybrid-dns-monitoring.service   # Log monitoring service
├── hybrid-dns-maintenance.service  # Maintenance tasks
└── hybrid-dns-maintenance.timer    # Scheduled maintenance
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