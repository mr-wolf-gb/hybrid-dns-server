# DNS Validators Documentation

This document describes the comprehensive DNS validation system implemented in the Hybrid DNS Server project.

## Overview

The DNS validation system provides robust validation for all DNS-related data using Pydantic schemas with custom validators. The validators ensure data integrity, prevent invalid configurations, and provide helpful error messages.

## Validator Classes

### DNSValidators Class

The `DNSValidators` class contains static methods for validating various DNS data formats:

#### Domain Name Validation
- **`validate_domain_name(domain, record_type)`**: Validates domain names according to RFC standards
  - Supports internationalized domain names (IDN) with punycode conversion
  - Allows wildcards (*.example.com) for DNS records
  - Supports underscores for service records and internal domains
  - Validates label length (max 63 characters per label)
  - Validates total domain length (max 253 characters)
  - Handles single-label domains for internal use

#### IP Address Validation
- **`validate_ipv4_address(ip)`**: Validates IPv4 addresses using Python's ipaddress module
- **`validate_ipv6_address(ip)`**: Validates IPv6 addresses with enhanced support
  - Normalizes IPv6 addresses
  - Supports compressed notation (::)
  - Validates various IPv6 address types (loopback, private, link-local, multicast)

#### Email Validation
- **`validate_dns_email_format(email)`**: Validates email addresses in DNS format
  - Uses dots instead of @ symbol (admin.example.com instead of admin@example.com)
  - Validates each part of the email address
  - Ensures proper DNS-compatible format for SOA records

#### Record Type-Specific Validation
- **`validate_cname_record_format(value)`**: Validates CNAME target domains
- **`validate_ns_record_format(value)`**: Validates NS nameserver domains
- **`validate_ptr_record_format(value)`**: Validates PTR hostname domains
- **`validate_mx_record_format(value)`**: Validates MX exchange domains
- **`validate_srv_record_format(value)`**: Validates SRV target domains (allows '.' for no service)

#### Advanced Record Validation
- **`validate_txt_record_format(value)`**: Validates TXT records with special format detection
  - Detects and validates SPF records (v=spf1)
  - Detects and validates DKIM records (v=DKIM1)
  - Detects and validates DMARC records (v=DMARC1)
  - Ensures valid UTF-8 encoding
  - Validates length constraints

- **`validate_soa_record_format(value)`**: Validates SOA records
  - Validates primary nameserver domain
  - Validates admin email in DNS format
  - Validates all numeric values (serial, refresh, retry, expire, minimum)
  - Ensures proper SOA record structure

- **`validate_caa_record_format(value)`**: Validates CAA records
  - Supports both quoted and unquoted values
  - Validates flags (0-255)
  - Validates tags (issue, issuewild, iodef)
  - Flexible value format handling

#### Specialized Record Types
- **`validate_sshfp_record_format(value)`**: Validates SSH fingerprint records
- **`validate_tlsa_record_format(value)`**: Validates TLSA records for TLS authentication
- **`validate_naptr_record_format(value)`**: Validates NAPTR records
- **`validate_loc_record_format(value)`**: Validates location records
- **`validate_spf_record_syntax(value)`**: Enhanced SPF record validation

## Schema Validators

### Zone Schemas

#### ZoneBase
- **Email validation**: Uses DNS format (dots instead of @)
- **Name validation**: Validates zone names according to DNS standards
- **SOA parameter validation**: Validates refresh, retry, expire, and minimum values

#### ZoneCreate
- **Master server validation**: Validates IP addresses for slave zones
- **Forwarder validation**: Validates forwarder IPs for forward zones
- **Zone type consistency**: Ensures required fields are present for each zone type

### DNS Record Schemas

#### DNSRecordBase
- **TTL validation**: Allows TTL values from 1 to 2147483647 seconds
- **Record value validation**: Type-specific validation based on record type
- **Name constraints**: Validates record names with type-specific rules

#### DNSRecordCreate
- **Priority validation**: Required for MX and SRV records
- **Weight validation**: Required for SRV records
- **Port validation**: Required for SRV records
- **Name format validation**: Validates SRV record naming convention (_service._proto.name)
- **Model-level validation**: Cross-field validation for record consistency

#### Special Validations
- **CNAME restrictions**: Prevents CNAME records at zone apex (@)
- **SRV naming**: Enforces _service._proto.name format
- **Label length**: Validates individual DNS labels (max 63 characters)
- **Domain length**: Validates total domain name length (max 253 characters)

### Forwarder Schemas

#### ForwarderServer
- **IP validation**: Validates IPv4 addresses for forwarder servers
- **Port validation**: Validates port numbers (1-65535)
- **Priority validation**: Validates server priority (1-10)

#### ForwarderBase
- **Domain validation**: Validates domains to forward
- **Server validation**: Validates forwarder server configurations
- **Type validation**: Ensures proper forwarder type selection

## Error Handling

### Validation Error Messages
All validators provide clear, actionable error messages that include:
- The specific validation that failed
- The invalid value that caused the failure
- Suggestions for correction when applicable
- Context about the record type or field being validated

### Example Error Messages
- "Invalid IPv4 address: 192.168.1.256"
- "SRV record name must follow _service._proto.name format (e.g., _http._tcp.example.com)"
- "CNAME record cannot be created for the zone apex (@)"
- "Record name label too long (max 63 characters per label)"

## Supported Record Types

The validation system supports all common DNS record types:
- **A**: IPv4 addresses
- **AAAA**: IPv6 addresses
- **CNAME**: Canonical name records
- **MX**: Mail exchange records
- **TXT**: Text records (including SPF, DKIM, DMARC)
- **SRV**: Service records
- **PTR**: Pointer records
- **NS**: Name server records
- **SOA**: Start of authority records
- **CAA**: Certificate authority authorization
- **SSHFP**: SSH fingerprint records
- **TLSA**: TLS authentication records
- **NAPTR**: Name authority pointer records
- **LOC**: Location records

## Testing

The validation system includes comprehensive tests in `test_dns_validators.py` that verify:
- All record types validate correctly
- Invalid data is properly rejected
- Edge cases are handled appropriately
- Error messages are helpful and accurate

## Usage Examples

### Creating a Valid A Record
```python
record = DNSRecordCreate(
    name='www',
    record_type=RecordType.A,
    value='192.168.1.1',
    ttl=3600
)
```

### Creating a Valid SRV Record
```python
record = DNSRecordCreate(
    name='_http._tcp',
    record_type=RecordType.SRV,
    value='server.example.com',
    priority=10,
    weight=5,
    port=80
)
```

### Creating a Valid Zone
```python
zone = ZoneCreate(
    name='example.com',
    zone_type=ZoneType.MASTER,
    email='admin.example.com'  # DNS format with dots
)
```

## Benefits

1. **Data Integrity**: Prevents invalid DNS configurations from being stored
2. **User Experience**: Provides clear error messages for quick problem resolution
3. **Standards Compliance**: Ensures all DNS data follows RFC standards
4. **Flexibility**: Supports both strict and flexible validation where appropriate
5. **Extensibility**: Easy to add new record types and validation rules
6. **Performance**: Efficient validation using compiled regex patterns and optimized logic

## Future Enhancements

Potential future improvements to the validation system:
- DNSSEC record validation (DNSKEY, RRSIG, DS, NSEC)
- Additional TXT record format detection (CAA, DMARC policy validation)
- Internationalized domain name (IDN) normalization
- Custom validation rules per zone or organization
- Integration with external DNS validation services