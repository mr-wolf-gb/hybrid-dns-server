# RPZ Bulk Import Guide

This guide explains how to use the bulk import functionality for Response Policy Zone (RPZ) rules in the Hybrid DNS Server.

## Overview

The bulk import feature allows you to import large numbers of RPZ rules from various file formats:
- **Text files (.txt)**: One domain per line
- **CSV files (.csv)**: Structured data with headers
- **JSON files (.json)**: Structured rule data

## API Endpoints

### 1. File-based Bulk Import

**Endpoint:** `POST /api/rpz/rules/bulk-import`

**Parameters:**
- `rpz_zone` (required): RPZ zone category (e.g., "malware", "phishing", "adult")
- `action` (optional): Default action for all rules (default: "block")
- `source` (optional): Source identifier (default: "bulk_import")
- `redirect_target` (optional): Required if action is "redirect"
- `file` (required): File to upload

**Example using curl:**
```bash
# Import malware domains from text file
curl -X POST "http://localhost:8000/api/rpz/rules/bulk-import?rpz_zone=malware&action=block" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@malware_domains.txt"

# Import with redirect action
curl -X POST "http://localhost:8000/api/rpz/rules/bulk-import?rpz_zone=custom&action=redirect&redirect_target=safe.com" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@redirect_domains.txt"
```

### 2. JSON-based Bulk Import

**Endpoint:** `POST /api/rpz/rules/bulk-import-json`

**Parameters:**
- `source` (optional): Source identifier (default: "bulk_import")

**Request Body:** Array of RPZ rule objects

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/api/rpz/rules/bulk-import-json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @rules.json
```

## File Formats

### Text Files (.txt)

Simple format with one domain per line. Comments start with `#`.

```
# Malware domains
malware-site1.com
malware-site2.net
trojan-host.org

# Phishing sites
fake-bank.com
phishing-login.net
```

**Hosts file format is also supported:**
```
0.0.0.0 malware-site1.com
127.0.0.1 malware-site2.net
```

### CSV Files (.csv)

Structured format with headers. The first column should contain domains.

```csv
domain,category,description
gambling-site1.com,gambling,Online gambling site
gambling-site2.net,gambling,Casino website
adult-content1.com,adult,Adult content site
```

### JSON Files (.json)

Full rule specification with all fields:

```json
[
  {
    "domain": "malware1.com",
    "rpz_zone": "malware",
    "action": "block",
    "description": "Known malware distribution site"
  },
  {
    "domain": "redirect-me.com",
    "rpz_zone": "custom",
    "action": "redirect",
    "redirect_target": "safe-alternative.com",
    "description": "Redirect to safe alternative"
  }
]
```

**Supported JSON structures:**
1. Array of rule objects (as shown above)
2. Simple array of domains: `["domain1.com", "domain2.com"]`
3. Object with domains array: `{"domains": ["domain1.com", "domain2.com"]}`

## RPZ Actions

- **block**: Block the domain (default)
- **redirect**: Redirect to another domain (requires `redirect_target`)
- **passthru**: Allow the domain (whitelist)

## RPZ Zones

Common RPZ zone categories:
- `malware`: Malware and virus sites
- `phishing`: Phishing and scam sites
- `adult`: Adult content sites
- `gambling`: Gambling sites
- `social_media`: Social media platforms
- `custom`: Custom rules
- `whitelist`: Explicitly allowed domains

## Response Format

Both endpoints return an `RPZRuleImportResult` object:

```json
{
  "total_processed": 100,
  "rules_added": 95,
  "rules_updated": 0,
  "rules_skipped": 5,
  "errors": [
    "Rule 10 (domain: invalid..domain): Domain contains invalid characters",
    "Rule 25 (domain: duplicate.com): Rule for domain 'duplicate.com' already exists"
  ]
}
```

## Error Handling

The bulk import process is designed to be resilient:
- Invalid rules are skipped and reported in the errors array
- Duplicate domains are detected and skipped
- Processing continues even if some rules fail
- Detailed error messages help identify issues

## Limits

- Maximum 10,000 rules per JSON import
- File uploads limited by server configuration
- Error messages limited to first 50 errors in response

## Best Practices

1. **Test with small files first** to verify format compatibility
2. **Use descriptive source identifiers** to track rule origins
3. **Review error messages** to fix data quality issues
4. **Use appropriate RPZ zones** for better organization
5. **Consider redirect targets** for user-friendly blocking

## Integration with BIND9

After successful import:
1. RPZ zone files are automatically updated
2. BIND9 configuration is reloaded
3. New rules take effect immediately
4. Changes are logged for audit purposes

## Monitoring

- Import operations are logged with detailed information
- Statistics are available via `/api/rpz/rules/statistics`
- Rule counts and sources are tracked
- Performance metrics are recorded

## Troubleshooting

**Common issues:**
- **File encoding**: Ensure files are UTF-8 encoded
- **Domain format**: Check for invalid characters or formatting
- **Duplicate rules**: Existing rules with same domain/zone combination will be skipped
- **Missing redirect targets**: Required when action is "redirect"
- **Large files**: Consider splitting very large imports into smaller batches

**Checking import results:**
```bash
# Get statistics after import
curl -X GET "http://localhost:8000/api/rpz/rules/statistics?rpz_zone=malware" \
  -H "Authorization: Bearer YOUR_TOKEN"
```