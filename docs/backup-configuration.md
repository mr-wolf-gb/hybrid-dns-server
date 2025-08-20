# Configuration Backup System

The Hybrid DNS Server includes a comprehensive configuration backup system that automatically creates backups before any configuration changes to ensure system reliability and enable quick recovery.

## Overview

The backup system consists of:
- **Centralized Backup Service**: Manages all backup operations with metadata tracking
- **Automatic Backup Integration**: Automatically creates backups before configuration changes
- **Multiple Backup Types**: Supports different types of backups for different scenarios
- **Retention Management**: Automatically cleans up old backups based on retention policies

## Backup Types

### 1. Zone File Backups (`ZONE_FILE`)
- Created before zone file modifications
- Includes individual DNS zone files
- Triggered by zone creation, updates, and deletions

### 2. RPZ File Backups (`RPZ_FILE`)
- Created before Response Policy Zone file changes
- Includes RPZ zone files for security policies
- Triggered by RPZ rule changes and bulk imports

### 3. Configuration Backups (`CONFIGURATION`)
- Created before BIND9 configuration file changes
- Includes forwarder configurations, RPZ policies, and main config files
- Triggered by forwarder changes and policy updates

### 4. Full Configuration Backups (`FULL_CONFIG`)
- Complete backup of all DNS configuration
- Includes all zone files, RPZ files, and configuration files
- Triggered by major operations or manually

## Automatic Backup Integration

### Zone Operations
```python
# Automatically creates backup before zone changes
await bind_service.backup_before_zone_changes(zone_name, "create")
await bind_service.backup_before_zone_changes(zone_name, "update")
await bind_service.backup_before_zone_changes(zone_name, "delete")
```

### Forwarder Operations
```python
# Automatically creates backup before forwarder changes
await bind_service.backup_before_forwarder_changes("create")
await bind_service.backup_before_forwarder_changes("update")
await bind_service.backup_before_forwarder_changes("delete")
```

### RPZ Operations
```python
# Automatically creates backup before RPZ changes
await bind_service.backup_before_rpz_changes(rpz_zone, "create_rule")
await bind_service.backup_before_rpz_changes(rpz_zone, "bulk_import")
await bind_service.backup_before_rpz_changes(rpz_zone, "policy_update")
```

## API Endpoints

### List Backups
```http
GET /api/backup/
```
Query parameters:
- `backup_type`: Filter by backup type (optional)
- `limit`: Maximum number of backups to return (default: 50)

### Create Full Backup
```http
POST /api/backup/full
```
Body:
```json
{
  "description": "Manual backup description"
}
```

### Get Backup Information
```http
GET /api/backup/{backup_id}
```

### Restore from Backup
```http
POST /api/backup/{backup_id}/restore
```

### Delete Backup
```http
DELETE /api/backup/{backup_id}
```

### Cleanup Old Backups
```http
POST /api/backup/cleanup
```

## Backup Storage

### Directory Structure
```
/opt/hybrid-dns-server/backups/
├── zone_file/           # Zone file backups
├── rpz_file/           # RPZ file backups
├── configuration/      # Configuration file backups
├── full_config/        # Full configuration backups
└── backup_metadata.json # Backup metadata
```

### Backup Metadata
Each backup includes metadata:
- Backup ID and timestamp
- Original file path and backup path
- File size and checksum
- Description and source information
- Related files (for full backups)

## Retention Policy

### Default Settings
- **Maximum backups per type**: 50
- **Retention period**: 30 days
- **Automatic cleanup**: Runs during backup operations

### Cleanup Rules
1. Keep the most recent 50 backups of each type
2. Delete backups older than 30 days
3. Preserve backups created before restore operations

## Security Features

### Pre-Restore Backup
Before any restore operation, the system automatically creates a backup of the current configuration to prevent data loss.

### Integrity Verification
- SHA256 checksums verify backup integrity
- File existence checks before restore operations
- Validation of backup metadata

### Access Control
- All backup operations require authentication
- Role-based access control for backup management
- Audit logging of all backup operations

## Configuration

### Environment Variables
```bash
# Backup configuration (optional)
BACKUP_RETENTION_DAYS=30
MAX_BACKUPS_PER_TYPE=50
BACKUP_ROOT_DIR=/opt/hybrid-dns-server/backups
```

### Service Configuration
The backup service is automatically configured and requires no manual setup. Configuration is handled through the main application settings.

## Monitoring and Alerts

### Backup Status
- Backup success/failure is logged
- Failed backups trigger error responses
- Backup statistics available through API

### Health Checks
- Backup directory accessibility
- Metadata file integrity
- Storage space monitoring

## Best Practices

### Manual Backups
Create manual full backups before:
- Major system updates
- Bulk configuration changes
- Maintenance operations

### Restore Testing
- Regularly test backup restore procedures
- Verify backup integrity periodically
- Document restore procedures

### Storage Management
- Monitor backup storage usage
- Adjust retention policies as needed
- Consider external backup storage for critical environments

## Troubleshooting

### Common Issues

#### Backup Creation Fails
- Check disk space availability
- Verify backup directory permissions
- Review application logs for errors

#### Restore Operation Fails
- Verify backup file integrity
- Check BIND9 service status
- Ensure proper file permissions

#### Cleanup Not Working
- Check backup metadata file
- Verify retention policy settings
- Review cleanup operation logs

### Recovery Procedures

#### Emergency Restore
1. Stop BIND9 service
2. Use backup API to restore configuration
3. Verify configuration validity
4. Restart BIND9 service

#### Partial Recovery
1. Identify specific backup needed
2. Use appropriate restore endpoint
3. Reload affected configuration
4. Verify DNS resolution

## Integration Examples

### Custom Backup Before Changes
```python
from app.services.backup_service import BackupService, BackupType

# Create custom backup
backup_service = BackupService()
backup_id = await backup_service.create_backup(
    file_path=Path("/etc/bind/custom.conf"),
    backup_type=BackupType.CONFIGURATION,
    description="Custom configuration backup"
)
```

### Automated Backup Scheduling
```python
# Schedule regular full backups
import asyncio
from datetime import datetime

async def scheduled_backup():
    backup_service = BackupService()
    backup_id = await backup_service.create_full_configuration_backup(
        f"Scheduled backup {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    return backup_id
```

The backup system provides comprehensive protection for DNS configuration changes while maintaining system performance and reliability.