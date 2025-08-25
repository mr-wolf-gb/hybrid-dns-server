# Backend Scripts Directory

This directory contains utility scripts organized by functionality for better maintainability and clean architecture.

## Directory Structure

```
scripts/
├── database/           # Database management scripts
├── websocket/          # WebSocket deployment and management scripts
├── deployment/         # Production deployment monitoring scripts
└── monitoring/         # Production monitoring and alerting scripts
```

## Database Scripts (`database/`)

### `init_db.py`
- **Purpose**: Initialize database schema and tables
- **Usage**: `python scripts/database/init_db.py`
- **When to use**: First-time setup, schema updates, development environment setup

### `create_admin.py`
- **Purpose**: Create administrative user accounts
- **Usage**: `python scripts/database/create_admin.py --username admin --password <password> --email admin@example.com`
- **When to use**: Initial admin setup, creating additional admin users

## WebSocket Scripts (`websocket/`)

### `deploy_websocket.py`
- **Purpose**: Deploy and manage WebSocket system rollouts
- **Usage**: 
  - Testing: `python scripts/websocket/deploy_websocket.py testing --test-users admin user1`
  - Gradual: `python scripts/websocket/deploy_websocket.py gradual --initial-percentage 5`
  - Full: `python scripts/websocket/deploy_websocket.py full`

### `rollback_websocket.py`
- **Purpose**: Emergency rollback of WebSocket deployments
- **Usage**: `python scripts/websocket/rollback_websocket.py emergency --reason "Production issue"`
- **When to use**: Production issues, failed deployments, emergency situations

### `monitor_websocket_deployment.py`
- **Purpose**: Monitor WebSocket deployment progress and health
- **Usage**: `python scripts/websocket/monitor_websocket_deployment.py`
- **Features**: Real-time monitoring, automatic rollback triggers, health checks

### `production_websocket_monitor.py`
- **Purpose**: Production-grade WebSocket monitoring with comprehensive session management
- **Usage**: `python scripts/websocket/production_websocket_monitor.py`
- **Features**: Session management, performance monitoring, alerting

### `websocket_monitoring_dashboard.py`
- **Purpose**: Real-time dashboard for WebSocket system monitoring
- **Usage**: `python scripts/websocket/websocket_monitoring_dashboard.py`
- **Features**: Live metrics, connection statistics, health visualization

## Deployment Scripts (`deployment/`)

### `production_deployment_monitor.py`
- **Purpose**: Monitor overall production deployment progress
- **Usage**: `python scripts/deployment/production_deployment_monitor.py`
- **Features**: Deployment tracking, rollback management, system health monitoring

### `production_deployment_dashboard.py`
- **Purpose**: Dashboard for production deployment monitoring
- **Usage**: `python scripts/deployment/production_deployment_dashboard.py`
- **Features**: Visual deployment progress, metrics dashboard, alert management

## Monitoring Scripts (`monitoring/`)

### `production_monitoring_cli.py`
- **Purpose**: Unified command-line interface for production monitoring
- **Usage**: 
  - Monitor: `python scripts/monitoring/production_monitoring_cli.py monitor --duration 4 --level comprehensive`
  - Dashboard: `python scripts/monitoring/production_monitoring_cli.py dashboard --mode summary`
  - Reports: `python scripts/monitoring/production_monitoring_cli.py report --hours 2`
  - Status: `python scripts/monitoring/production_monitoring_cli.py status`

### `production_monitoring_integration.py`
- **Purpose**: Integrated monitoring system combining all monitoring components
- **Usage**: `python scripts/monitoring/production_monitoring_integration.py`
- **Features**: Unified monitoring, alert correlation, comprehensive reporting

## Usage Guidelines

### Development Environment
```bash
# Initialize database
cd backend
python scripts/database/init_db.py

# Create admin user
python scripts/database/create_admin.py --username admin --password admin123 --email admin@localhost
```

### Production Deployment
```bash
# Deploy WebSocket system gradually
python scripts/websocket/deploy_websocket.py gradual --initial-percentage 10 --step-size 10 --step-duration 30

# Monitor deployment
python scripts/websocket/monitor_websocket_deployment.py

# Start production monitoring
python scripts/monitoring/production_monitoring_cli.py monitor --duration 24 --level comprehensive
```

### Emergency Procedures
```bash
# Emergency WebSocket rollback
python scripts/websocket/rollback_websocket.py emergency --reason "Critical production issue"

# Check system status
python scripts/monitoring/production_monitoring_cli.py status

# Generate emergency report
python scripts/monitoring/production_monitoring_cli.py report --hours 1 --format json
```

## Script Dependencies

All scripts are designed to work from the backend directory and have access to the main application modules:

```python
# Common import pattern in scripts
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings
from app.core.database import get_database_session
```

## Logging and Output

- All scripts use the application's logging configuration
- Output is directed to both console and log files
- Error handling includes detailed logging for troubleshooting
- Production scripts include structured logging for monitoring systems

## Security Considerations

- Database scripts require appropriate database permissions
- WebSocket scripts require admin privileges for deployment operations
- Monitoring scripts may require system-level access for metrics collection
- All scripts validate authentication and authorization before executing operations

## Maintenance

- Scripts are version-controlled with the main application
- Update scripts when making changes to core application modules
- Test scripts in development environment before production use
- Monitor script execution logs for errors and performance issues