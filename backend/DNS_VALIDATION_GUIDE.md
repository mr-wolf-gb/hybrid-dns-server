# DNS Record Type Validation Guide

This document describes the comprehensive DNS record type validation implemented in the Hybrid DNS Server project.

## Overview

The DNS validation system provides robust validation for all common DNS record types, ensuring data integrity and compliance with DNS standards (RFC 1035, RFC 3596, and others).

## Supported Record Types

### A Records (IPv4 Address)
- **Format**: IPv4 address (e.g., `192.168.1.1`)
- **Validation**: 
  - Must be a valid IPv4 address
  - Uses Python's `ipaddress.IPv4Address` for validation
- **Example**: `192.168.1.100`

### AAAA Records (IPv6 Address)
- **Format**: IPv6 address (e.g., `2001:db8::1`)
- **Validation**:
  - Must be a valid IPv6 address
  - Uses Python's `ipaddress.IPv6Address` for validation
- **Example**: `2001:db8:85a3::8a2e:370:7334`

### CNAME Records (Canonical Name)
- **Format**: Domain name (e.g., `target.example.com`)
- **Validation**:
  - Must be a valid domain name
  - Cannot coexist with other record types at the same name (enforced at service level)
- **Example**: `www.example.com`

### MX Records (Mail Exchange)
- **Format**: Domain name (e.g., `mail.example.com`)
- **Validation**:
  - Must be a valid domain name
  - **Priority field is required** (0-65535)
- **Example**: Value: `mail.example.com`, Priority: `10`

### NS Records (Name Server)
- **Format**: Domain name (e.g., `ns1.example.com`)
- **Validation**:
  - Must be a valid domain name
- **Example**: `ns1.example.com`

### PTR Records (Pointer)
- **Format**: Domain name (e.g., `host.example.com`)
- **Validation**:
  - Must be a valid domain name
  - Typically used for reverse DNS lookups
- **Example**: `server.example.com`

### SRV Records (Service)
- **Format**: Domain name or `.` for no service
- **Validation**:
  - Must be a valid domain name or `.`
  - **Name must follow `_service._proto.name` format** (e.g., `_http._tcp.example.com`)
  - **Priority, Weight, and Port fields are required**
- **Example**: 
  - Name: `_http._tcp.example.com`
  - Value: `server.example.com`
  - Priority: `10`, Weight: `20`, Port: `80`

### TXT Records (Text)
- **Format**: Text string (max 255 characters per string)
- **Validation**:
  - Must be valid UTF-8 text
  - Maximum 255 characters per string
  - **Special validation for common formats**:
    - **SPF Records**: Must start with `v=spf1` and contain valid mechanisms
    - **DKIM Records**: Must start with `v=DKIM1` and contain required parameters
    - **DMARC Records**: Must start with `v=DMARC1` and contain valid policy
- **Examples**:
  - General: `"This is a text record"`
  - SPF: `v=spf1 include:_spf.google.com ~all`
  - DKIM: `v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ...`
  - DMARC: `v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com`

### SOA Records (Start of Authority)
- **Format**: `primary-ns admin-email serial refresh retry expire minimum`
- **Validation**:
  - Must have exactly 7 space-separated values
  - Primary nameserver must be a valid domain name
  - Admin email must be in DNS format (dots instead of @)
  - All numeric values must be valid 32-bit integers within appropriate ranges
- **Example**: `ns1.example.com. admin.example.com. 2024010101 10800 3600 604800 86400`

### CAA Records (Certificate Authority Authorization)
- **Format**: `flags tag "value"`
- **Validation**:
  - Flags must be 0-255
  - Tag must be one of: `issue`, `issuewild`, `iodef`
  - Value must be enclosed in double quotes
- **Example**: `0 issue "letsencrypt.org"`

### SSHFP Records (SSH Fingerprint)
- **Format**: `algorithm fptype fingerprint`
- **Validation**:
  - Algorithm: 1 (RSA), 2 (DSS), 3 (ECDSA), or 4 (Ed25519)
  - Fingerprint type: 1 (SHA-1) or 2 (SHA-256)
  - Fingerprint must be hexadecimal string with correct length:
    - SHA-1: 40 characters
    - SHA-256: 64 characters
- **Example**: `1 2 123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234`

## Field Constraints

### Priority Field
- **Required for**: MX and SRV records
- **Not allowed for**: All other record types
- **Range**: 0-65535

### Weight Field
- **Required for**: SRV records only
- **Not allowed for**: All other record types
- **Range**: 0-65535

### Port Field
- **Required for**: SRV records only
- **Not allowed for**: All other record types
- **Range**: 1-65535

### TTL Field
- **Optional for**: All record types
- **Range**: 60-86400 seconds (1 minute to 24 hours)
- **Default**: Inherits from zone settings if not specified

## Domain Name Validation

All domain name validations follow RFC 1035 standards:

- Maximum total length: 253 characters
- Maximum label length: 63 characters per label
- Valid characters: letters, numbers, hyphens, dots
- Cannot start or end with hyphens
- Cannot contain consecutive dots
- Case-insensitive (converted to lowercase)

## Special Name Formats

### SRV Record Names
- Must follow `_service._proto.name` format
- Service and protocol must start with underscore
- Examples: `_http._tcp.example.com`, `_sip._udp.example.com`

### Special TXT Record Names
- DMARC records: Should be at `_dmarc.domain.com`
- DKIM records: Should end with `._domainkey.domain.com`

## Error Handling

The validation system provides detailed error messages for:
- Invalid IP addresses
- Malformed domain names
- Missing required fields
- Invalid field values for specific record types
- Format violations for special record types

## Usage Examples

```python
from schemas.dns import DNSRecordCreate, RecordType

# Valid A record
a_record = DNSRecordCreate(
    name="www",
    record_type=RecordType.A,
    value="192.168.1.100"
)

# Valid MX record with priority
mx_record = DNSRecordCreate(
    name="@",
    record_type=RecordType.MX,
    value="mail.example.com",
    priority=10
)

# Valid SRV record with all required fields
srv_record = DNSRecordCreate(
    name="_http._tcp.example.com",
    record_type=RecordType.SRV,
    value="server.example.com",
    priority=10,
    weight=20,
    port=80
)

# Valid TXT record with SPF
spf_record = DNSRecordCreate(
    name="@",
    record_type=RecordType.TXT,
    value="v=spf1 include:_spf.google.com ~all"
)
```

## Testing

Run the validation tests with:
```bash
python backend/test_dns_validation.py
```

This will test all record types and validation rules to ensure they work correctly.

## Implementation Details

The validation is implemented using:
- **Pydantic validators**: For field-level validation
- **Model validators**: For cross-field validation
- **Custom validator classes**: For complex DNS-specific validation logic
- **Regular expressions**: For format validation
- **Python ipaddress module**: For IP address validation

The validation system is designed to be:
- **Comprehensive**: Covers all common DNS record types
- **Standards-compliant**: Follows RFC specifications
- **User-friendly**: Provides clear error messages
- **Extensible**: Easy to add new record types or validation rules