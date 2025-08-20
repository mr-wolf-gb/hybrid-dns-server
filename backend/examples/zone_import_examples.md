# Zone Import/Export Examples

This document provides examples of how to use the zone import/export functionality with different formats.

## JSON Format Import

### Example JSON Import Data

```json
{
  "zone": {
    "name": "example.com",
    "zone_type": "master",
    "email": "admin.example.com",
    "description": "Example domain zone",
    "refresh": 10800,
    "retry": 3600,
    "expire": 604800,
    "minimum": 86400
  },
  "records": [
    {
      "name": "@",
      "record_type": "A",
      "value": "192.168.1.100",
      "ttl": 3600
    },
    {
      "name": "www",
      "record_type": "A",
      "value": "192.168.1.100",
      "ttl": 3600
    },
    {
      "name": "@",
      "record_type": "MX",
      "value": "mail.example.com",
      "ttl": 3600,
      "priority": 10
    },
    {
      "name": "_http._tcp",
      "record_type": "SRV",
      "value": "www.example.com",
      "ttl": 3600,
      "priority": 10,
      "weight": 5,
      "port": 80
    }
  ],
  "format": "json",
  "validate_only": false,
  "overwrite_existing": false
}
```

### API Call Example

```bash
curl -X POST "http://localhost:8000/api/zones/import" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d @zone_import.json
```

## BIND Zone File Format Import

### Example BIND Zone File

```bind
; Zone file for example.com
$TTL 86400
@       IN      SOA     ns1.example.com. admin.example.com. (
                        2024012001      ; Serial
                        10800           ; Refresh
                        3600            ; Retry
                        604800          ; Expire
                        86400           ; Minimum TTL
                        )

; Name servers
@       IN      NS      ns1.example.com.
@       IN      NS      ns2.example.com.

; A records
@       IN      A       192.168.1.100
www     IN      A       192.168.1.100
ftp     IN      A       192.168.1.101
mail    IN      A       192.168.1.102

; CNAME records
blog    IN      CNAME   www.example.com.
shop    IN      CNAME   www.example.com.

; MX records
@       IN      MX      10 mail.example.com.
@       IN      MX      20 backup-mail.example.com.

; TXT records
@       IN      TXT     "v=spf1 mx a -all"
_dmarc  IN      TXT     "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com"

; SRV records
_http._tcp      IN      SRV     10 5 80 www.example.com.
_https._tcp     IN      SRV     10 5 443 www.example.com.
```

### API Call Example

```bash
curl -X POST "http://localhost:8000/api/zones/import" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "zone_name": "example.com",
    "email": "admin.example.com",
    "zone_file_content": "...", 
    "format": "bind",
    "validate_only": false,
    "overwrite_existing": false
  }'
```

## CSV Format Import

### Example CSV File

```csv
name,type,value,ttl,priority,weight,port
@,A,192.168.1.100,3600,,,
www,A,192.168.1.100,3600,,,
ftp,A,192.168.1.101,3600,,,
mail,A,192.168.1.102,3600,,,
blog,CNAME,www.example.com,3600,,,
shop,CNAME,www.example.com,3600,,,
@,MX,mail.example.com,3600,10,,
@,MX,backup-mail.example.com,3600,20,,
@,TXT,"v=spf1 mx a -all",3600,,,
_dmarc,TXT,"v=DMARC1; p=quarantine",3600,,,
_http._tcp,SRV,www.example.com,3600,10,5,80
_https._tcp,SRV,www.example.com,3600,10,5,443
```

### API Call Example

```bash
curl -X POST "http://localhost:8000/api/zones/import" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "zone_name": "example.com",
    "email": "admin.example.com",
    "csv_content": "name,type,value,ttl,priority,weight,port\n@,A,192.168.1.100,3600,,,\n...",
    "format": "csv",
    "validate_only": false,
    "overwrite_existing": false
  }'
```

## Zone Export Examples

### Export Zone as JSON

```bash
curl -X GET "http://localhost:8000/api/zones/1/export?format=json" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Export Zone as BIND Zone File

```bash
curl -X GET "http://localhost:8000/api/zones/1/export?format=bind" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o db.example.com
```

### Export Zone as CSV

```bash
curl -X GET "http://localhost:8000/api/zones/1/export?format=csv" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o example.com_records.csv
```

## Validation Only Mode

To validate import data without actually importing:

```bash
curl -X POST "http://localhost:8000/api/zones/import/validate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d @zone_import.json
```

Or set `"validate_only": true` in your import data.

## Error Handling

The API provides detailed error messages for common issues:

### Invalid Format Error
```json
{
  "detail": "Invalid export format 'xml'. Supported formats: json, bind, csv"
}
```

### Missing Required Fields
```json
{
  "detail": "BIND format requires 'zone_file_content' and 'zone_name' fields"
}
```

### Validation Errors
```json
{
  "success": false,
  "zone_name": "example.com",
  "errors": [
    "Line 5: Invalid IPv4 address '192.168.1.999' for A record",
    "Line 8: MX record requires priority field"
  ],
  "warnings": [
    "Line 3: TTL 30 is below recommended minimum of 60 seconds"
  ]
}
```

## Supported Record Types

The import/export functionality supports all common DNS record types:

- **A**: IPv4 address records
- **AAAA**: IPv6 address records  
- **CNAME**: Canonical name records
- **MX**: Mail exchange records (requires priority)
- **TXT**: Text records
- **SRV**: Service records (requires priority, weight, port)
- **PTR**: Pointer records (for reverse DNS)
- **NS**: Name server records
- **SOA**: Start of authority records

## Best Practices

1. **Always validate first**: Use `validate_only: true` to check your data before importing
2. **Backup existing zones**: Export existing zones before overwriting
3. **Use appropriate TTL values**: Generally 300-86400 seconds
4. **Include all required fields**: MX records need priority, SRV records need priority/weight/port
5. **Follow DNS naming conventions**: Use FQDN format where appropriate
6. **Test in development**: Import test zones before production zones

## Integration with BIND9

When zones are successfully imported, the system automatically:

1. Creates the zone in the database
2. Generates the BIND9 zone file
3. Updates the BIND9 configuration
4. Reloads BIND9 to activate the new zone

This ensures that imported zones are immediately available for DNS resolution.