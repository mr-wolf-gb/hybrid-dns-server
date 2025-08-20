# Atomic Configuration Updates

This document describes the atomic configuration update functionality implemented in the BIND service.

## Overview

Atomic configuration updates ensure that DNS configuration changes are applied safely with automatic rollback capability. This prevents broken configurations from being deployed and provides a reliable way to make complex changes to the DNS server.

## Key Features

### 1. Transaction-Based Updates
- All configuration changes are grouped into transactions
- Changes are validated before being applied
- Automatic backup creation before changes
- Rollback capability if any step fails

### 2. Multi-Component Support
- **Zone Changes**: Create, update, delete DNS zones
- **Forwarder Changes**: Modify conditional forwarding rules
- **RPZ Changes**: Update Response Policy Zone security rules

### 3. Comprehensive Validation
- Configuration syntax validation
- Dependency checking
- Conflict detection
- Rollback capability verification

## Usage Examples

### Basic Atomic Transaction

```python
from app.services.bind_service import BindService

bind_service = BindService(db_session)

# Define changes
transaction_data = {
    "description": "Add new internal zone and forwarder",
    "changes": {
        "zones": [
            {
                "action": "create",
                "name": "internal.company.com",
                "zone_type": "master",
                "email": "admin@company.com",
                "description": "Internal company zone"
            }
        ],
        "forwarders": [
            {
                "action": "create",
                "name": "ad-forwarder",
                "domains": ["ad.company.com"],
                "forwarder_type": "active_directory",
                "servers": [
                    {"ip": "192.168.1.10", "port": 53, "priority": 1},
                    {"ip": "192.168.1.11", "port": 53, "priority": 2}
                ]
            }
        ]
    }
}

# Execute transaction
result = await bind_service.execute_atomic_transaction(transaction_data)

if result["success"]:
    print(f"Transaction completed: {result['transaction_id']}")
    print(f"Changes applied: {result['changes_applied']}")
else:
    print(f"Transaction failed: {result['errors']}")
    if result.get("rollback_success"):
        print("Configuration rolled back successfully")
```

### Dry Run Validation

```python
# Test changes without applying them
transaction_data = {
    "description": "Test configuration changes",
    "dry_run": True,  # Only validate, don't apply
    "changes": {
        "zones": [
            {
                "action": "update",
                "id": 1,
                "description": "Updated description"
            }
        ]
    }
}

result = await bind_service.execute_atomic_transaction(transaction_data)
print(f"Validation result: {result['success']}")
print(f"Errors: {result.get('errors', [])}")
```

### Configuration Checkpoints

```python
# Create a checkpoint before major changes
checkpoint_result = await bind_service.create_atomic_configuration_checkpoint(
    "before-major-restructure"
)

if checkpoint_result["success"]:
    backup_id = checkpoint_result["backup_id"]
    print(f"Checkpoint created: {backup_id}")
    
    # Later, if needed, rollback to checkpoint
    rollback_result = await bind_service.rollback_configuration(backup_id)
```

## Transaction Structure

### Transaction Data Format

```python
{
    "description": "Human-readable description",
    "dry_run": False,  # Optional: validate only
    "force_backup": False,  # Optional: create backup even with no changes
    "changes": {
        "zones": [
            {
                "action": "create|update|delete",
                "name": "zone.example.com",  # For create
                "id": 123,  # For update/delete
                # ... other zone fields
            }
        ],
        "forwarders": [
            {
                "action": "create|update|delete",
                "name": "forwarder-name",  # For create
                "id": 456,  # For update/delete
                # ... other forwarder fields
            }
        ],
        "rpz": [
            {
                "action": "create|update|delete",
                "domain": "malicious.example.com",  # For create
                "id": 789,  # For update/delete
                # ... other RPZ fields
            }
        ]
    }
}
```

### Response Format

```python
{
    "success": True,
    "transaction_id": "transaction_20240120_143022_123456",
    "phase": "completed",  # validation|backup_creation|completed|failed
    "errors": [],
    "warnings": [],
    "backup_id": "full_config_20240120_143022",
    "applied_changes": [
        {
            "type": "zone",
            "action": "create",
            "details": {"zone_id": 1, "zone_name": "test.local"}
        }
    ],
    "changes_count": 1,
    "rollback_attempted": False,
    "rollback_success": False
}
```

## Safety Features

### 1. Pre-Change Validation
- Current configuration must be valid
- Proposed changes are validated
- Conflict detection between changes
- Rollback capability verification

### 2. Automatic Backup
- Full configuration backup before changes
- Backup integrity validation
- Metadata tracking for rollback

### 3. Rollback on Failure
- Automatic rollback if any step fails
- Validation after rollback
- Detailed error reporting

### 4. Configuration Verification
- BIND9 syntax validation
- Service reload verification
- Post-change health checks

## Error Handling

### Validation Errors
- Configuration syntax errors
- Missing dependencies
- Invalid field values
- Conflict detection

### Runtime Errors
- Database transaction failures
- File system errors
- BIND9 service errors
- Network connectivity issues

### Recovery Actions
- Automatic rollback to backup
- Error logging and reporting
- Service status verification
- Manual intervention guidance

## Best Practices

### 1. Use Dry Run First
Always test changes with `dry_run: true` before applying them.

### 2. Create Checkpoints
Create named checkpoints before major configuration changes.

### 3. Monitor Results
Check transaction results and handle errors appropriately.

### 4. Backup Management
Regularly clean up old backups to manage disk space.

### 5. Test Rollback
Periodically test rollback procedures to ensure they work.

## Limitations

### Current Limitations
- Transaction status is not persisted (in-memory only)
- No concurrent transaction support
- Limited to single-server deployments

### Future Enhancements
- Persistent transaction history
- Concurrent transaction handling
- Multi-server coordination
- Advanced conflict resolution

## Troubleshooting

### Common Issues

1. **Validation Failures**
   - Check BIND9 installation and configuration
   - Verify file permissions
   - Ensure database connectivity

2. **Rollback Failures**
   - Check backup integrity
   - Verify file system permissions
   - Manual configuration restoration may be needed

3. **Service Reload Issues**
   - Check BIND9 service status
   - Verify configuration syntax
   - Review system logs

### Debug Information

Enable debug logging to get detailed information about atomic transactions:

```python
import logging
logging.getLogger('bind_service').setLevel(logging.DEBUG)
```

## API Integration

The atomic configuration functionality is designed to be used by the REST API endpoints:

- `POST /api/atomic/transaction` - Execute atomic transaction
- `POST /api/atomic/validate` - Validate changes (dry run)
- `POST /api/atomic/checkpoint` - Create configuration checkpoint
- `GET /api/atomic/backups` - List available backups
- `POST /api/atomic/rollback/{backup_id}` - Rollback to backup

This ensures that all configuration changes through the web interface are atomic and safe.