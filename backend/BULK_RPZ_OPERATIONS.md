# Bulk RPZ Operations Implementation

This document describes the newly implemented bulk operations for RPZ (Response Policy Zone) rules.

## Overview

The bulk operations allow administrators to efficiently manage large numbers of RPZ rules through the API. These operations include:

1. **Bulk Import** - Import rules from files or JSON payloads
2. **Bulk Update** - Apply the same changes to multiple rules
3. **Bulk Delete** - Delete multiple rules at once

## API Endpoints

### 1. Bulk Import from File

**Endpoint:** `POST /api/rpz/rules/bulk-import`

**Parameters:**
- `rpz_zone` (query): RPZ zone category for imported rules
- `action` (query): Default action for imported rules (default: "block")
- `source` (query): Source identifier for imported rules (default: "bulk_import")
- `redirect_target` (query, optional): Redirect target (required if action is redirect)
- `file` (form-data): File containing domains to import

**Supported File Formats:**
- **TXT**: One domain per line, supports comments (#) and hosts file format
- **CSV**: First column contains domains, supports headers
- **JSON**: Various structures supported (arrays, objects with domain fields)

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/rpz/rules/bulk-import" \
  -H "Authorization: Bearer <token>" \
  -F "file=@malware_domains.txt" \
  -F "rpz_zone=malware" \
  -F "action=block" \
  -F "source=threat_feed"
```

### 2. Bulk Import from JSON

**Endpoint:** `POST /api/rpz/rules/bulk-import-json`

**Body:** Array of RPZ rule objects

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/rpz/rules/bulk-import-json" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "domain": "malicious.example.com",
      "rpz_zone": "malware",
      "action": "block",
      "description": "Known malware domain"
    },
    {
      "domain": "phishing.example.com", 
      "rpz_zone": "phishing",
      "action": "redirect",
      "redirect_target": "blocked.company.com"
    }
  ]'
```

### 3. Bulk Update

**Endpoint:** `POST /api/rpz/rules/bulk-update`

**Body:**
```json
{
  "rule_ids": [1, 2, 3, 4],
  "updates": {
    "action": "block",
    "description": "Updated via bulk operation",
    "is_active": true
  }
}
```

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/rpz/rules/bulk-update" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_ids": [1, 2, 3],
    "updates": {
      "action": "block",
      "description": "Updated description"
    }
  }'
```

### 4. Bulk Delete

**Endpoint:** `POST /api/rpz/rules/bulk-delete`

**Body:**
```json
{
  "rule_ids": [1, 2, 3, 4],
  "confirm": true
}
```

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/rpz/rules/bulk-delete" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_ids": [1, 2, 3],
    "confirm": true
  }'
```

## Response Formats

### Import Result
```json
{
  "total_processed": 100,
  "rules_added": 95,
  "rules_updated": 0,
  "rules_skipped": 5,
  "errors": [
    "Rule 10 (domain: invalid..domain): Domain contains invalid characters"
  ]
}
```

### Update Result
```json
{
  "total_processed": 10,
  "rules_updated": 8,
  "rules_failed": 2,
  "errors": [
    "Rule 5: Not found",
    "Rule 9: Redirect target is required for redirect action"
  ]
}
```

### Delete Result
```json
{
  "total_processed": 5,
  "rules_deleted": 5,
  "rules_failed": 0,
  "affected_zones": ["malware", "phishing"],
  "errors": []
}
```

## Features

### File Format Support

**Text Files (.txt):**
- One domain per line
- Comments starting with # are ignored
- Supports hosts file format (IP domain)
- Empty lines are ignored

**CSV Files (.csv):**
- First column contains domains
- Headers are automatically detected and skipped
- Comments starting with # are ignored

**JSON Files (.json):**
- Simple array: `["domain1.com", "domain2.com"]`
- Object array: `[{"domain": "domain1.com"}, {"domain": "domain2.com"}]`
- Nested object: `{"domains": ["domain1.com", "domain2.com"]}`

### Error Handling

- Individual rule failures don't stop the entire operation
- Detailed error messages for each failed rule
- Validation errors are reported with specific rule context
- Duplicate domain detection within the same zone

### BIND9 Integration

- Automatic backup creation before bulk operations
- Background BIND9 configuration updates
- Zone file regeneration for affected RPZ zones
- Automatic service reload after changes

### Performance Optimizations

- Background task processing for BIND9 updates
- Batch database operations
- Error limiting (first 50 errors reported)
- Transaction management for data consistency

## Validation

### Bulk Update Validation
- Rule IDs must be provided (minimum 1)
- Update data is validated according to RPZ rule schema
- Redirect target required when action is "redirect"

### Bulk Delete Validation
- Explicit confirmation required (`confirm: true`)
- Rule IDs must be provided (minimum 1)
- Affected zones are tracked for BIND9 updates

### Import Validation
- File format validation
- Domain format validation
- Action-specific validation (redirect target for redirect action)
- Duplicate detection within import and existing rules

## Security Considerations

- All operations require authentication
- User actions are tracked in audit logs
- Rate limiting applies to all endpoints
- File size limits prevent abuse
- Confirmation required for destructive operations

## Monitoring

- Comprehensive logging for all bulk operations
- Performance metrics (processing time, success rates)
- Error tracking and reporting
- BIND9 integration status monitoring

## Testing

Run the test suite to verify bulk operations:

```bash
cd backend
python test_bulk_rpz_operations.py
python test_bulk_rpz_api.py
```

Both test scripts should pass all tests, confirming that:
- Schemas validate correctly
- API endpoints are properly structured
- Service methods are available
- Import functionality works as expected