"""
DNS-related Pydantic schemas for the Hybrid DNS Server
"""

from pydantic import BaseModel, Field, validator, model_validator
from typing import List, Optional, Dict, Any, TypeVar, Generic
from datetime import datetime
from enum import Enum
import re
import ipaddress

# Import RPZAction from security module to avoid duplication
from .security import RPZAction

# Generic type variable for pagination
T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema"""
    items: List[T]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    
    class Config:
        from_attributes = True


class DNSValidators:
    """Utility class for DNS-specific validation functions"""
    
    @staticmethod
    def validate_domain_name(domain: str, record_type: str = "DNS") -> str:
        """Validate domain name format according to RFC standards"""
        if not domain:
            raise ValueError(f'Domain name cannot be empty for {record_type} record')
        
        original_domain = domain
        
        # Check for trailing dot - only allow for FQDN contexts, reject for zone names
        if domain.endswith('.'):
            if record_type in ['zone', 'DNS record', 'DNS']:
                raise ValueError(f'Domain name cannot end with dot for {record_type}')
            domain = domain[:-1]
        
        # Handle internationalized domain names (IDN)
        try:
            # Convert IDN to ASCII (punycode) for validation
            ascii_domain = domain.encode('idna').decode('ascii')
            domain = ascii_domain
        except (UnicodeError, UnicodeDecodeError):
            # If IDN conversion fails, continue with original validation
            # but allow basic international characters for internal domains
            pass
        
        # Check overall length (RFC 1035)
        if len(domain) > 253:
            raise ValueError(f'Domain name too long for {record_type} record (max 253 characters)')
        
        # Allow wildcards for DNS records (e.g., *.example.com)
        # Also allow underscores for service records and internal domains
        wildcard_pattern = r'^(\*\.)?[a-zA-Z0-9._-]+$'
        if not re.match(wildcard_pattern, domain):
            raise ValueError(f'Invalid characters in domain name for {record_type} record')
        
        # Check for consecutive dots
        if '..' in domain:
            raise ValueError(f'Domain name cannot contain consecutive dots for {record_type} record')
        
        # Check for leading/trailing dots or hyphens (except wildcard)
        if domain.startswith('.') or domain.endswith('.') or domain.endswith('-'):
            raise ValueError(f'Domain name cannot start/end with dot or hyphen for {record_type} record')
        
        if domain.startswith('-') and not domain.startswith('*.'):
            raise ValueError(f'Domain name cannot start with hyphen for {record_type} record')
        
        # Validate each label (RFC 1035)
        labels = domain.split('.')
        if len(labels) < 1:
            raise ValueError(f'Domain name must have at least one label for {record_type} record')
        
        # For single-label domains (like localhost), allow them for internal use
        if len(labels) == 1 and record_type not in ['zone']:
            # Single label domains are allowed for internal DNS records
            label = labels[0]
            if len(label) > 63:
                raise ValueError(f'Domain label too long for {record_type} record (max 63 characters per label)')
            if not re.match(r'^[a-zA-Z0-9._-]+$', label):
                raise ValueError(f'Invalid characters in domain label for {record_type} record')
            return domain.lower()
        
        # For multi-label domains, require at least 2 labels for zones
        if len(labels) < 2 and record_type == 'zone':
            raise ValueError(f'Zone name must have at least two labels for {record_type}')
        
        for i, label in enumerate(labels):
            if not label:
                continue
            
            # Allow wildcard in first label only
            if label == '*' and i == 0:
                continue
                
            if len(label) > 63:
                raise ValueError(f'Domain label too long for {record_type} record (max 63 characters per label)')
            
            # Allow underscores in labels for service records and internal domains
            if not re.match(r'^[a-zA-Z0-9._-]+$', label):
                raise ValueError(f'Invalid characters in domain label for {record_type} record')
            
            if label.startswith('-') or label.endswith('-'):
                raise ValueError(f'Domain label cannot start/end with hyphen for {record_type} record')
            
            # Validate TLD (last label) for multi-label domains
            if i == len(labels) - 1 and len(labels) > 1:  # This is the TLD
                if len(label) < 2:
                    raise ValueError(f'Top-level domain must be at least 2 characters for {record_type} record')
                # Allow numeric TLDs for reverse DNS and internal domains
                if not (label[0].isalpha() or label[0].isdigit()):
                    raise ValueError(f'Top-level domain must start with a letter or digit for {record_type} record')
        
        return domain.lower()
    
    @staticmethod
    def validate_dns_email_format(email: str) -> str:
        """Validate email address in DNS format (dots instead of @)"""
        # DNS email format: user.domain.com instead of user@domain.com
        if '@' in email:
            raise ValueError('SOA admin email must use DNS format (dots instead of @)')
        
        # Should have at least one dot to separate user from domain
        if '.' not in email:
            raise ValueError('SOA admin email must contain at least one dot')
        
        # Validate as domain name but allow more flexible format for email
        parts = email.split('.')
        if len(parts) < 2:
            raise ValueError('SOA admin email must have at least user and domain parts')
        
        # Validate each part
        for part in parts:
            if not part:
                raise ValueError('SOA admin email cannot have empty parts')
            if len(part) > 63:
                raise ValueError('SOA admin email parts cannot exceed 63 characters')
            if not re.match(r'^[a-zA-Z0-9-]+$', part):
                raise ValueError('SOA admin email contains invalid characters')
            if part.startswith('-') or part.endswith('-'):
                raise ValueError('SOA admin email parts cannot start/end with hyphen')
        
        return email.lower()
    
    @staticmethod
    def validate_ipv4_address(ip: str) -> str:
        """Validate IPv4 address format"""
        try:
            addr = ipaddress.IPv4Address(ip)
            return str(addr)
        except ValueError:
            raise ValueError(f'Invalid IPv4 address: {ip}')
    
    @staticmethod
    def validate_ipv6_address(ip: str) -> str:
        """Validate IPv6 address format with enhanced support"""
        try:
            addr = ipaddress.IPv6Address(ip)
            
            # Normalize the address (expand compressed notation for consistency)
            normalized = str(addr)
            
            # Additional validation for specific IPv6 formats
            if ip.count('::') > 1:
                raise ValueError(f'Invalid IPv6 address format (multiple :: sequences): {ip}')
            
            # Check for valid IPv6 address types and provide helpful messages
            if addr.is_loopback:
                # Allow loopback addresses
                pass
            elif addr.is_private:
                # Allow private IPv6 addresses
                pass
            elif addr.is_link_local:
                # Allow link-local addresses
                pass
            elif addr.is_multicast:
                # Allow multicast addresses (might be used in some DNS contexts)
                pass
            
            # Return the original format to preserve user preference (compressed vs expanded)
            # but ensure it's valid
            return ip.lower()
        except ValueError as e:
            if 'Invalid IPv6 address' in str(e):
                raise e
            raise ValueError(f'Invalid IPv6 address: {ip}')
    
    @staticmethod
    def validate_cname_record_format(value: str) -> str:
        """Validate CNAME record target format"""
        # CNAME target must be a valid domain name
        return DNSValidators.validate_domain_name(value, 'CNAME target')
    
    @staticmethod
    def validate_ns_record_format(value: str) -> str:
        """Validate NS record nameserver format"""
        # NS record must be a valid domain name
        return DNSValidators.validate_domain_name(value, 'NS nameserver')
    
    @staticmethod
    def validate_ptr_record_format(value: str) -> str:
        """Validate PTR record hostname format"""
        # PTR record must be a valid domain name
        return DNSValidators.validate_domain_name(value, 'PTR hostname')
    
    @staticmethod
    def validate_reverse_zone_name(zone_name: str) -> str:
        """Validate reverse DNS zone name format"""
        zone_name = zone_name.lower()
        
        # IPv4 reverse zones end with .in-addr.arpa
        if zone_name.endswith('.in-addr.arpa'):
            # Extract the IP part
            ip_part = zone_name[:-13]  # Remove .in-addr.arpa
            ip_octets = ip_part.split('.')
            
            # Validate that we have 1-4 octets and they're valid
            if len(ip_octets) > 4:
                raise ValueError('Invalid IPv4 reverse zone format')
            
            for octet in ip_octets:
                try:
                    octet_int = int(octet)
                    if octet_int < 0 or octet_int > 255:
                        raise ValueError(f'Invalid IPv4 octet in reverse zone: {octet}')
                except ValueError:
                    raise ValueError(f'Invalid IPv4 octet in reverse zone: {octet}')
        
        # IPv6 reverse zones end with .ip6.arpa
        elif zone_name.endswith('.ip6.arpa'):
            # IPv6 reverse zones use nibble format
            nibble_part = zone_name[:-9]  # Remove .ip6.arpa
            nibbles = nibble_part.split('.')
            
            # Each nibble should be a single hex digit
            for nibble in nibbles:
                if len(nibble) != 1 or not re.match(r'^[0-9a-f]$', nibble):
                    raise ValueError(f'Invalid IPv6 nibble in reverse zone: {nibble}')
        
        else:
            # Regular forward zone validation
            return DNSValidators.validate_domain_name(zone_name, 'zone')
        
        return zone_name
    
    @staticmethod
    def validate_srv_record_format(value: str) -> str:
        """Validate SRV record target format"""
        # SRV record target should be a domain name or '.' for no service
        if value == '.':
            return value
        return DNSValidators.validate_domain_name(value, 'SRV target')
    
    @staticmethod
    def validate_mx_record_format(value: str) -> str:
        """Validate MX record exchange format"""
        # MX record exchange should be a domain name
        return DNSValidators.validate_domain_name(value, 'MX exchange')
    
    @staticmethod
    def validate_txt_record_format(value: str) -> str:
        """Validate TXT record format"""
        # TXT records can contain any text, but check for reasonable constraints
        if len(value) > 255:
            raise ValueError('TXT record value cannot exceed 255 characters per string')
        
        # Check for valid UTF-8 encoding
        try:
            value.encode('utf-8')
        except UnicodeEncodeError:
            raise ValueError('TXT record must contain valid UTF-8 text')
        
        # Additional validation for common TXT record formats
        try:
            if value.startswith('v=spf1'):
                DNSValidators.validate_spf_record_syntax(value)
            elif value.startswith('v=DKIM1'):
                DNSValidators._validate_dkim_record(value)
            elif value.startswith('v=DMARC1'):
                DNSValidators._validate_dmarc_record(value)
        except ValueError as e:
            # Re-raise with more context
            raise ValueError(f'TXT record validation failed: {str(e)}')
        
        return value
    
    @staticmethod
    def validate_spf_record_syntax(value: str) -> str:
        """Validate SPF record format"""
        # Basic SPF validation - check for valid mechanisms
        valid_mechanisms = ['include:', 'a:', 'mx:', 'ptr:', 'ip4:', 'ip6:', 'exists:', 'redirect=']
        valid_qualifiers = ['+', '-', '~', '?']
        
        parts = value.split()
        if parts[0] != 'v=spf1':
            raise ValueError('SPF record must start with v=spf1')
        
        for part in parts[1:]:
            if part in ['all', '+all', '-all', '~all', '?all']:
                continue
            
            # Check if it's a valid mechanism
            found_mechanism = False
            for mechanism in valid_mechanisms:
                if part.startswith(mechanism) or any(part.startswith(q + mechanism) for q in valid_qualifiers):
                    found_mechanism = True
                    break
            
            if not found_mechanism and not part.startswith('exp='):
                raise ValueError(f'Invalid SPF mechanism: {part}')
        
        return value
    
    @staticmethod
    def _validate_dkim_record(value: str) -> None:
        """Validate DKIM record format"""
        # Basic DKIM validation
        if not value.startswith('v=DKIM1'):
            raise ValueError('DKIM record must start with v=DKIM1')
        
        # Check for required parameters
        if 'k=' not in value or 'p=' not in value:
            raise ValueError('DKIM record must contain k= and p= parameters')
    
    @staticmethod
    def _validate_dmarc_record(value: str) -> None:
        """Validate DMARC record format"""
        # Basic DMARC validation
        if not value.startswith('v=DMARC1'):
            raise ValueError('DMARC record must start with v=DMARC1')
        
        # Check for required policy
        if 'p=' not in value:
            raise ValueError('DMARC record must contain p= policy parameter')
        
        # Validate policy values
        policy_match = re.search(r'p=([^;]+)', value)
        if policy_match:
            policy = policy_match.group(1).strip()
            if policy not in ['none', 'quarantine', 'reject']:
                raise ValueError(f'Invalid DMARC policy: {policy}')
    
    @staticmethod
    def validate_soa_record_format(value: str) -> str:
        """Validate SOA record format"""
        # SOA format: primary-ns admin-email serial refresh retry expire minimum
        parts = value.split()
        if len(parts) != 7:
            raise ValueError('SOA record must have exactly 7 space-separated values')
        
        # Validate primary nameserver
        DNSValidators.validate_domain_name(parts[0], 'SOA primary nameserver')
        
        # Validate admin email (in DNS format with dots instead of @)
        DNSValidators.validate_dns_email_format(parts[1])
        
        # Validate numeric values
        try:
            serial = int(parts[2])
            refresh = int(parts[3])
            retry = int(parts[4])
            expire = int(parts[5])
            minimum = int(parts[6])
            
            # Basic sanity checks
            if serial < 0 or serial > 4294967295:  # 32-bit unsigned int
                raise ValueError('SOA serial must be between 0 and 4294967295')
            if refresh < 1 or refresh > 2147483647:
                raise ValueError('SOA refresh must be between 1 and 2147483647 seconds')
            if retry < 1 or retry > 2147483647:
                raise ValueError('SOA retry must be between 1 and 2147483647 seconds')
            if expire < 1 or expire > 2147483647:
                raise ValueError('SOA expire must be between 1 and 2147483647 seconds')
            if minimum < 0 or minimum > 2147483647:
                raise ValueError('SOA minimum must be between 0 and 2147483647 seconds')
                
        except ValueError as e:
            if 'invalid literal' in str(e):
                raise ValueError('SOA record numeric values must be valid integers')
            raise e
        
        return value
    
    @staticmethod
    def validate_caa_record_format(value: str) -> str:
        """Validate CAA (Certificate Authority Authorization) record format"""
        # CAA format: flags tag "value" or flags tag value
        parts = value.split(None, 2)  # Split into max 3 parts
        if len(parts) != 3:
            raise ValueError('CAA record must have exactly 3 parts: flags tag value')
        
        flags, tag, caa_value = parts
        
        # Validate flags (0-255)
        try:
            flag_int = int(flags)
            if flag_int < 0 or flag_int > 255:
                raise ValueError('CAA flags must be between 0 and 255')
        except ValueError:
            raise ValueError('CAA flags must be a valid integer')
        
        # Validate tag
        valid_tags = ['issue', 'issuewild', 'iodef']
        if tag not in valid_tags:
            raise ValueError(f'CAA tag must be one of: {", ".join(valid_tags)}')
        
        # Validate value format (can be quoted or unquoted)
        if caa_value.startswith('"') and caa_value.endswith('"'):
            # Quoted format - validate the content inside quotes
            inner_value = caa_value[1:-1]
            if not inner_value:
                raise ValueError('CAA value cannot be empty')
        else:
            # Unquoted format - validate directly
            if not caa_value:
                raise ValueError('CAA value cannot be empty')
            # For unquoted values, ensure no spaces (which would break parsing)
            if ' ' in caa_value:
                raise ValueError('CAA value with spaces must be enclosed in double quotes')
        
        return value
    
    @staticmethod
    def validate_sshfp_record_format(value: str) -> str:
        """Validate SSHFP (SSH Fingerprint) record format"""
        # SSHFP format: algorithm fptype fingerprint
        parts = value.split()
        if len(parts) != 3:
            raise ValueError('SSHFP record must have exactly 3 parts: algorithm fptype fingerprint')
        
        algorithm, fptype, fingerprint = parts
        
        # Validate algorithm (1=RSA, 2=DSS, 3=ECDSA, 4=Ed25519)
        try:
            alg_int = int(algorithm)
            if alg_int not in [1, 2, 3, 4]:
                raise ValueError('SSHFP algorithm must be 1 (RSA), 2 (DSS), 3 (ECDSA), or 4 (Ed25519)')
        except ValueError:
            raise ValueError('SSHFP algorithm must be a valid integer')
        
        # Validate fingerprint type (1=SHA-1, 2=SHA-256)
        try:
            fp_int = int(fptype)
            if fp_int not in [1, 2]:
                raise ValueError('SSHFP fingerprint type must be 1 (SHA-1) or 2 (SHA-256)')
        except ValueError:
            raise ValueError('SSHFP fingerprint type must be a valid integer')
        
        # Validate fingerprint format (hex string)
        if not re.match(r'^[0-9a-fA-F]+$', fingerprint):
            raise ValueError('SSHFP fingerprint must be a hexadecimal string')
        
        # Validate fingerprint length based on type
        expected_lengths = {1: 40, 2: 64}  # SHA-1: 40 chars, SHA-256: 64 chars
        if fp_int in expected_lengths and len(fingerprint) != expected_lengths[fp_int]:
            raise ValueError(f'SSHFP fingerprint length must be {expected_lengths[fp_int]} characters for type {fp_int}')
        
        return value
    
    @staticmethod
    def validate_tlsa_record_format(value: str) -> str:
        """Validate TLSA (Transport Layer Security Authentication) record format"""
        # TLSA format: usage selector matching_type certificate_data
        parts = value.split(None, 3)  # Split into max 4 parts
        if len(parts) != 4:
            raise ValueError('TLSA record must have exactly 4 parts: usage selector matching_type certificate_data')
        
        usage, selector, matching_type, cert_data = parts
        
        # Validate usage (0-3)
        try:
            usage_int = int(usage)
            if usage_int not in [0, 1, 2, 3]:
                raise ValueError('TLSA usage must be 0 (CA constraint), 1 (service certificate constraint), 2 (trust anchor assertion), or 3 (domain-issued certificate)')
        except ValueError:
            raise ValueError('TLSA usage must be a valid integer')
        
        # Validate selector (0-1)
        try:
            selector_int = int(selector)
            if selector_int not in [0, 1]:
                raise ValueError('TLSA selector must be 0 (full certificate) or 1 (SubjectPublicKeyInfo)')
        except ValueError:
            raise ValueError('TLSA selector must be a valid integer')
        
        # Validate matching type (0-2)
        try:
            matching_int = int(matching_type)
            if matching_int not in [0, 1, 2]:
                raise ValueError('TLSA matching type must be 0 (exact match), 1 (SHA-256 hash), or 2 (SHA-512 hash)')
        except ValueError:
            raise ValueError('TLSA matching type must be a valid integer')
        
        # Validate certificate data (hex string)
        if not re.match(r'^[0-9a-fA-F]+$', cert_data):
            raise ValueError('TLSA certificate data must be a hexadecimal string')
        
        # Validate certificate data length based on matching type
        expected_lengths = {0: None, 1: 64, 2: 128}  # SHA-256: 64 chars, SHA-512: 128 chars
        if matching_int in expected_lengths and expected_lengths[matching_int] is not None:
            if len(cert_data) != expected_lengths[matching_int]:
                raise ValueError(f'TLSA certificate data length must be {expected_lengths[matching_int]} characters for matching type {matching_int}')
        
        return value
    
    @staticmethod
    def validate_naptr_record_format(value: str) -> str:
        """Validate NAPTR (Name Authority Pointer) record format"""
        # NAPTR format: order preference flags service regexp replacement
        # Example: 100 10 "u" "E2U+sip" "!^.*$!sip:info@example.com!" .
        parts = value.split(None, 5)  # Split into max 6 parts
        if len(parts) != 6:
            raise ValueError('NAPTR record must have exactly 6 parts: order preference flags service regexp replacement')
        
        order, preference, flags, service, regexp, replacement = parts
        
        # Validate order (0-65535)
        try:
            order_int = int(order)
            if order_int < 0 or order_int > 65535:
                raise ValueError('NAPTR order must be between 0 and 65535')
        except ValueError:
            raise ValueError('NAPTR order must be a valid integer')
        
        # Validate preference (0-65535)
        try:
            pref_int = int(preference)
            if pref_int < 0 or pref_int > 65535:
                raise ValueError('NAPTR preference must be between 0 and 65535')
        except ValueError:
            raise ValueError('NAPTR preference must be a valid integer')
        
        # Validate flags format (quoted string)
        if not (flags.startswith('"') and flags.endswith('"')):
            raise ValueError('NAPTR flags must be enclosed in double quotes')
        
        # Validate service format (quoted string)
        if not (service.startswith('"') and service.endswith('"')):
            raise ValueError('NAPTR service must be enclosed in double quotes')
        
        # Validate regexp format (quoted string)
        if not (regexp.startswith('"') and regexp.endswith('"')):
            raise ValueError('NAPTR regexp must be enclosed in double quotes')
        
        # Validate replacement (domain name or '.')
        if replacement != '.':
            DNSValidators.validate_domain_name(replacement, 'NAPTR replacement')
        
        return value
    
    @staticmethod
    def validate_loc_record_format(value: str) -> str:
        """Validate LOC (Location) record format"""
        # LOC format: latitude longitude altitude size horizontal_precision vertical_precision
        # Example: 52 22 23.000 N 4 53 32.000 E -2.00m 0.00m 10000m 10m
        parts = value.split()
        if len(parts) < 8:
            raise ValueError('LOC record must have at least 8 parts for basic format')
        
        # Basic validation - LOC records have complex format
        # Latitude: degrees minutes seconds N/S
        try:
            lat_deg = int(parts[0])
            lat_min = int(parts[1])
            lat_sec = float(parts[2])
            lat_dir = parts[3].upper()
            
            if lat_deg < 0 or lat_deg > 90:
                raise ValueError('LOC latitude degrees must be between 0 and 90')
            if lat_min < 0 or lat_min > 59:
                raise ValueError('LOC latitude minutes must be between 0 and 59')
            if lat_sec < 0 or lat_sec >= 60:
                raise ValueError('LOC latitude seconds must be between 0 and 59.999')
            if lat_dir not in ['N', 'S']:
                raise ValueError('LOC latitude direction must be N or S')
        except (ValueError, IndexError):
            raise ValueError('Invalid LOC latitude format')
        
        # Longitude: degrees minutes seconds E/W
        try:
            lon_deg = int(parts[4])
            lon_min = int(parts[5])
            lon_sec = float(parts[6])
            lon_dir = parts[7].upper()
            
            if lon_deg < 0 or lon_deg > 180:
                raise ValueError('LOC longitude degrees must be between 0 and 180')
            if lon_min < 0 or lon_min > 59:
                raise ValueError('LOC longitude minutes must be between 0 and 59')
            if lon_sec < 0 or lon_sec >= 60:
                raise ValueError('LOC longitude seconds must be between 0 and 59.999')
            if lon_dir not in ['E', 'W']:
                raise ValueError('LOC longitude direction must be E or W')
        except (ValueError, IndexError):
            raise ValueError('Invalid LOC longitude format')
        
        # Additional parts (altitude, size, etc.) are optional and have complex validation
        # For now, we'll accept the basic format validation
        
        return value
    
    @staticmethod
    def validate_url_record_format(value: str) -> str:
        """Validate URL record format (non-standard but commonly used)"""
        # URL records typically contain a URL
        if not value.startswith(('http://', 'https://')):
            raise ValueError('URL record must start with http:// or https://')
        
        # Basic URL validation
        url_pattern = r'^https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})?(?:/[^\s]*)?$'
        if not re.match(url_pattern, value):
            raise ValueError('Invalid URL format')
        
        return value
    

    
    @staticmethod
    def validate_hostname_format(hostname: str) -> str:
        """Validate hostname format (stricter than domain name)"""
        # Hostnames cannot start with digits or contain underscores
        if not hostname:
            raise ValueError('Hostname cannot be empty')
        
        # Remove trailing dot if present
        if hostname.endswith('.'):
            hostname = hostname[:-1]
        
        # Basic domain validation first
        validated = DNSValidators.validate_domain_name(hostname, 'hostname')
        
        # Additional hostname-specific rules
        labels = validated.split('.')
        for label in labels:
            if not label:
                continue
            
            # Hostnames cannot start with a digit (traditional rule)
            if label[0].isdigit():
                raise ValueError(f'Hostname label cannot start with digit: {label}')
            
            # Hostnames should not contain underscores (though DNS allows it)
            if '_' in label:
                raise ValueError(f'Hostname label should not contain underscores: {label}')
        
        return validated
    
    @staticmethod
    def validate_fqdn_format(fqdn: str) -> str:
        """Validate Fully Qualified Domain Name format"""
        if not fqdn.endswith('.'):
            raise ValueError('FQDN must end with a dot')
        
        # Validate the domain part (without the trailing dot)
        domain_part = fqdn[:-1]
        return DNSValidators.validate_domain_name(domain_part, 'FQDN') + '.'


class ZoneType(str, Enum):
    """Enumeration for DNS zone types"""
    MASTER = "master"
    SLAVE = "slave"
    FORWARD = "forward"


class RecordType(str, Enum):
    """Enumeration for DNS record types"""
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    SRV = "SRV"
    PTR = "PTR"
    NS = "NS"
    SOA = "SOA"
    CAA = "CAA"
    SSHFP = "SSHFP"
    TLSA = "TLSA"
    NAPTR = "NAPTR"
    LOC = "LOC"


class ForwarderType(str, Enum):
    """Enumeration for forwarder types"""
    ACTIVE_DIRECTORY = "active_directory"
    INTRANET = "intranet"
    PUBLIC = "public"


# RPZAction is imported from security module to avoid duplication


# Zone Import/Export Schemas
class ZoneImportFormat(str, Enum):
    """Supported zone import formats"""
    BIND = "bind"
    JSON = "json"
    CSV = "csv"


class ZoneExportFormat(str, Enum):
    """Supported zone export formats"""
    BIND = "bind"
    JSON = "json"
    CSV = "csv"


class ZoneImportRecord(BaseModel):
    """Schema for importing DNS records"""
    name: str = Field(..., description="DNS record name")
    record_type: str = Field(..., description="DNS record type")
    value: str = Field(..., description="DNS record value")
    ttl: Optional[int] = Field(None, description="Time to live in seconds")
    priority: Optional[int] = Field(None, description="Priority for MX and SRV records")
    weight: Optional[int] = Field(None, description="Weight for SRV records")
    port: Optional[int] = Field(None, description="Port for SRV records")



    errors: List[str] = Field(default=[], description="Import errors")
    warnings: List[str] = Field(default=[], description="Import warnings")
    validation_only: bool = Field(default=False, description="Whether this was validation only")




class ZoneValidationError(BaseModel):
    """Schema for zone validation errors"""
    field: str = Field(..., description="Field with error")
    message: str = Field(..., description="Error message")
    line_number: Optional[int] = Field(None, description="Line number in import file")
    record_name: Optional[str] = Field(None, description="Record name with error")


class ZoneValidationResult(BaseModel):
    """Schema for zone validation results"""
    valid: bool = Field(..., description="Whether validation passed")
    errors: List[ZoneValidationError] = Field(default=[], description="Validation errors")
    warnings: List[str] = Field(default=[], description="Validation warnings")
    records_validated: int = Field(default=0, description="Number of records validated")


# RPZAction is imported from security module to avoid duplication


# Zone Schemas
class ZoneBase(BaseModel):
    """Base schema for DNS zones with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="DNS zone name (e.g., example.com)")
    zone_type: ZoneType = Field(..., description="Type of DNS zone")
    email: str = Field(..., min_length=1, max_length=255, description="Administrator email address")
    description: Optional[str] = Field(None, max_length=1000, description="Optional zone description")
    refresh: int = Field(default=10800, ge=300, le=86400, description="SOA refresh interval in seconds")
    retry: int = Field(default=3600, ge=300, le=86400, description="SOA retry interval in seconds")
    expire: int = Field(default=604800, ge=86400, le=2419200, description="SOA expire interval in seconds")
    minimum: int = Field(default=86400, ge=300, le=86400, description="SOA minimum TTL in seconds")

    @validator('name')
    def validate_zone_name(cls, v):
        """Validate zone name format"""
        if not v or not v.strip():
            raise ValueError('Zone name cannot be empty. Please provide a valid domain name (e.g., example.com)')
        
        v = v.strip().lower()
        
        # Use specialized reverse zone validation for reverse zones
        if v.endswith('.in-addr.arpa') or v.endswith('.ip6.arpa'):
            try:
                return DNSValidators.validate_reverse_zone_name(v)
            except ValueError as e:
                raise ValueError(f'Invalid reverse zone name: {str(e)}. Reverse zones should follow the format like "1.168.192.in-addr.arpa" for IPv4 or use nibble format for IPv6')
        
        try:
            return DNSValidators.validate_domain_name(v, 'zone')
        except ValueError as e:
            raise ValueError(f'Invalid zone name: {str(e)}. Zone names should be valid domain names like "example.com" or "internal.local"')

    @validator('email')
    def validate_email_format(cls, v):
        """Validate email format for SOA record (DNS format with dots instead of @)"""
        if not v or not v.strip():
            raise ValueError('Administrator email cannot be empty. Please provide an email address in DNS format (e.g., admin.example.com instead of admin@example.com)')
        
        try:
            return DNSValidators.validate_dns_email_format(v.strip())
        except ValueError as e:
            raise ValueError(f'Invalid administrator email: {str(e)}. Please use DNS format with dots instead of @ (e.g., admin.example.com instead of admin@example.com)')
    
    @validator('refresh')
    def validate_refresh_interval(cls, v):
        """Validate SOA refresh interval"""
        if v < 300:
            raise ValueError(f'Refresh interval too short ({v} seconds). Minimum is 300 seconds (5 minutes) to avoid excessive zone transfer requests')
        if v > 86400:
            raise ValueError(f'Refresh interval too long ({v} seconds). Maximum is 86400 seconds (24 hours) to ensure timely updates')
        return v
    
    @validator('retry')
    def validate_retry_interval(cls, v):
        """Validate SOA retry interval"""
        if v < 300:
            raise ValueError(f'Retry interval too short ({v} seconds). Minimum is 300 seconds (5 minutes) to avoid excessive retry attempts')
        if v > 86400:
            raise ValueError(f'Retry interval too long ({v} seconds). Maximum is 86400 seconds (24 hours) for reasonable retry behavior')
        return v
    
    @validator('expire')
    def validate_expire_interval(cls, v):
        """Validate SOA expire interval"""
        if v < 86400:
            raise ValueError(f'Expire interval too short ({v} seconds). Minimum is 86400 seconds (1 day) to prevent premature zone expiration')
        if v > 2419200:
            raise ValueError(f'Expire interval too long ({v} seconds). Maximum is 2419200 seconds (28 days) for reasonable zone expiration')
        return v
    
    @validator('minimum')
    def validate_minimum_ttl(cls, v):
        """Validate SOA minimum TTL"""
        if v < 300:
            raise ValueError(f'Minimum TTL too short ({v} seconds). Minimum is 300 seconds (5 minutes) to reduce DNS query load')
        if v > 86400:
            raise ValueError(f'Minimum TTL too long ({v} seconds). Maximum is 86400 seconds (24 hours) for reasonable caching behavior')
        return v


class ZoneCreate(ZoneBase):
    """Schema for creating new DNS zones"""
    master_servers: Optional[List[str]] = Field(None, description="Master servers for slave zones")
    forwarders: Optional[List[str]] = Field(None, description="Forwarder servers for forward zones")

    @validator('master_servers', always=True)
    def validate_master_servers(cls, v, values):
        """Validate master servers for slave zones"""
        zone_type = values.get('zone_type')
        
        if zone_type == ZoneType.SLAVE:
            if not v or len(v) == 0:
                raise ValueError('Master servers are required for slave zones. Please provide at least one IP address of the master DNS server (e.g., ["192.168.1.10", "192.168.1.11"])')
            
            # Validate IP addresses
            for i, server in enumerate(v):
                try:
                    ipaddress.ip_address(server)
                except ValueError:
                    raise ValueError(f'Invalid IP address at position {i+1}: "{server}". Please provide a valid IPv4 or IPv6 address (e.g., 192.168.1.10 or 2001:db8::1)')
        
        elif zone_type != ZoneType.SLAVE and v:
            raise ValueError(f'Master servers can only be specified for slave zones, but zone type is "{zone_type}". Please remove master_servers or change zone_type to "slave"')
        
        return v

    @validator('forwarders', always=True)
    def validate_forwarders(cls, v, values):
        """Validate forwarders for forward zones"""
        zone_type = values.get('zone_type')
        
        if zone_type == ZoneType.FORWARD:
            if not v or len(v) == 0:
                raise ValueError('Forwarders are required for forward zones. Please provide at least one IP address of the DNS server to forward queries to (e.g., ["8.8.8.8", "1.1.1.1"])')
            
            # Validate IP addresses
            for i, forwarder in enumerate(v):
                try:
                    ipaddress.ip_address(forwarder)
                except ValueError:
                    raise ValueError(f'Invalid IP address at position {i+1}: "{forwarder}". Please provide a valid IPv4 or IPv6 address (e.g., 8.8.8.8 or 2001:4860:4860::8888)')
        
        elif zone_type != ZoneType.FORWARD and v:
            raise ValueError(f'Forwarders can only be specified for forward zones, but zone type is "{zone_type}". Please remove forwarders or change zone_type to "forward"')
        
        return v


class ZoneUpdate(BaseModel):
    """Schema for updating existing DNS zones"""
    email: Optional[str] = Field(None, min_length=1, max_length=255, description="Administrator email address")
    description: Optional[str] = Field(None, max_length=1000, description="Zone description")
    refresh: Optional[int] = Field(None, ge=300, le=86400, description="SOA refresh interval in seconds")
    retry: Optional[int] = Field(None, ge=300, le=86400, description="SOA retry interval in seconds")
    expire: Optional[int] = Field(None, ge=86400, le=2419200, description="SOA expire interval in seconds")
    minimum: Optional[int] = Field(None, ge=300, le=86400, description="SOA minimum TTL in seconds")
    is_active: Optional[bool] = Field(None, description="Whether the zone is active")
    master_servers: Optional[List[str]] = Field(None, description="Master servers for slave zones")
    forwarders: Optional[List[str]] = Field(None, description="Forwarder servers for forward zones")

    @validator('email')
    def validate_email_format(cls, v):
        """Validate email format for SOA record (DNS format with dots instead of @)"""
        if v is not None:
            try:
                return DNSValidators.validate_dns_email_format(v)
            except ValueError as e:
                raise ValueError(f'Invalid email format: {str(e)}')
        return v

    @validator('master_servers')
    def validate_master_servers(cls, v):
        """Validate master server IP addresses"""
        if v is not None:
            for server in v:
                try:
                    ipaddress.ip_address(server)
                except ValueError:
                    raise ValueError(f'Invalid IP address: {server}')
        return v

    @validator('forwarders')
    def validate_forwarders(cls, v):
        """Validate forwarder IP addresses"""
        if v is not None:
            for forwarder in v:
                try:
                    ipaddress.ip_address(forwarder)
                except ValueError:
                    raise ValueError(f'Invalid IP address: {forwarder}')
        return v


class Zone(ZoneBase):
    """Schema for DNS zone responses"""
    id: int = Field(..., description="Unique zone identifier")
    serial: Optional[int] = Field(None, description="SOA serial number")
    is_active: bool = Field(..., description="Whether the zone is active")
    file_path: Optional[str] = Field(None, description="Path to zone file")
    master_servers: Optional[List[str]] = Field(None, description="Master servers for slave zones")
    forwarders: Optional[List[str]] = Field(None, description="Forwarder servers for forward zones")
    created_by: Optional[int] = Field(None, description="ID of user who created the zone")
    updated_by: Optional[int] = Field(None, description="ID of user who last updated the zone")
    created_at: datetime = Field(..., description="Zone creation timestamp")
    updated_at: datetime = Field(..., description="Zone last update timestamp")
    record_count: Optional[int] = Field(0, description="Number of DNS records in the zone")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ZoneImportData(BaseModel):
    """Schema for zone import data"""
    zone: ZoneCreate = Field(..., description="Zone configuration")
    records: List[ZoneImportRecord] = Field(default=[], description="DNS records to import")
    format: ZoneImportFormat = Field(default=ZoneImportFormat.JSON, description="Import format")
    validate_only: bool = Field(default=False, description="Only validate, don't import")
    overwrite_existing: bool = Field(default=False, description="Overwrite existing zone if it exists")


class ZoneImportResult(BaseModel):
    """Schema for zone import results"""
    success: bool = Field(..., description="Whether import was successful")
    zone_id: Optional[int] = Field(None, description="ID of imported zone")
    zone_name: str = Field(..., description="Name of the zone")
    records_imported: int = Field(default=0, description="Number of records imported")
    records_skipped: int = Field(default=0, description="Number of records skipped")
    errors: List[str] = Field(default=[], description="Import errors")
    warnings: List[str] = Field(default=[], description="Import warnings")





class ZoneQueryParams(BaseModel):
    """Schema for zone query parameters with filtering and pagination"""
    skip: int = Field(0, ge=0, description="Number of items to skip for pagination")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of items to return")
    zone_type: Optional[ZoneType] = Field(None, description="Filter by zone type")
    active_only: bool = Field(True, description="Filter to show only active zones")
    search: Optional[str] = Field(None, min_length=1, max_length=255, description="Search term for zone name or description")
    sort_by: Optional[str] = Field("name", description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order (asc or desc)")
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort_by field"""
        allowed_fields = ['name', 'zone_type', 'created_at', 'updated_at', 'serial', 'is_active']
        if v and v not in allowed_fields:
            raise ValueError(f'sort_by must be one of: {", ".join(allowed_fields)}')
        return v


# DNS Record Schemas
class DNSRecordBase(BaseModel):
    """Base schema for DNS records with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="DNS record name")
    record_type: RecordType = Field(..., description="DNS record type")
    value: str = Field(..., min_length=1, max_length=500, description="DNS record value")
    ttl: Optional[int] = Field(None, ge=1, le=2147483647, description="Time to live in seconds")
    priority: Optional[int] = Field(None, ge=0, le=65535, description="Priority for MX and SRV records")
    weight: Optional[int] = Field(None, ge=0, le=65535, description="Weight for SRV records")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Port for SRV records")

    @validator('ttl')
    def validate_ttl(cls, v):
        """Validate TTL with reasonable defaults and warnings"""
        if v is not None:
            # Provide warnings for unusual TTL values
            if v < 60:
                # Allow but warn about very low TTL values
                pass  # Could add logging here in production
            elif v > 86400:  # More than 1 day
                # Allow but could warn about very high TTL values
                pass  # Could add logging here in production
        return v

    @validator('value')
    def validate_record_value(cls, v, values):
        """Validate DNS record value based on record type"""
        record_type = values.get('record_type')
        
        if record_type == RecordType.A:
            # Validate IPv4 address
            return DNSValidators.validate_ipv4_address(v)
        
        elif record_type == RecordType.AAAA:
            # Validate IPv6 address
            return DNSValidators.validate_ipv6_address(v)
        
        elif record_type == RecordType.CNAME:
            # Validate domain name for CNAME
            return DNSValidators.validate_cname_record_format(v)
        
        elif record_type == RecordType.MX:
            # MX record value should be a domain name
            return DNSValidators.validate_mx_record_format(v)
        
        elif record_type == RecordType.NS:
            # NS record value should be a domain name
            return DNSValidators.validate_ns_record_format(v)
        
        elif record_type == RecordType.PTR:
            # PTR record value should be a domain name
            return DNSValidators.validate_ptr_record_format(v)
        
        elif record_type == RecordType.TXT:
            # TXT records validation
            return DNSValidators.validate_txt_record_format(v)
        
        elif record_type == RecordType.SRV:
            # SRV record value should be a domain name or '.'
            return DNSValidators.validate_srv_record_format(v)
        
        elif record_type == RecordType.SOA:
            # SOA record validation
            return DNSValidators.validate_soa_record_format(v)
        
        elif record_type == RecordType.CAA:
            # CAA record validation
            return DNSValidators.validate_caa_record_format(v)
        
        elif record_type == RecordType.SSHFP:
            # SSHFP record validation
            return DNSValidators.validate_sshfp_record_format(v)
        
        elif record_type == RecordType.TLSA:
            # TLSA record validation
            return DNSValidators.validate_tlsa_record_format(v)
        
        elif record_type == RecordType.NAPTR:
            # NAPTR record validation
            return DNSValidators.validate_naptr_record_format(v)
        
        elif record_type == RecordType.LOC:
            # LOC record validation
            return DNSValidators.validate_loc_record_format(v)
        
        return v


class DNSRecordCreate(DNSRecordBase):
    """Schema for creating new DNS records"""
    
    @validator('priority', always=True)
    def validate_priority(cls, v, values):
        """Validate priority for MX and SRV records"""
        record_type = values.get('record_type')
        if record_type in [RecordType.MX, RecordType.SRV] and v is None:
            if record_type == RecordType.MX:
                raise ValueError('Priority is required for MX records. Please provide a numeric priority value (lower numbers have higher priority, typically 10-50)')
            else:
                raise ValueError('Priority is required for SRV records. Please provide a numeric priority value (0-65535, lower numbers have higher priority)')
        elif record_type not in [RecordType.MX, RecordType.SRV] and v is not None:
            raise ValueError(f'Priority field is not applicable for {record_type} records. Please remove the priority value or change the record type')
        return v

    @validator('weight', always=True)
    def validate_weight(cls, v, values):
        """Validate weight for SRV records"""
        record_type = values.get('record_type')
        if record_type == RecordType.SRV and v is None:
            raise ValueError('Weight is required for SRV records. Please provide a numeric weight value (0-65535, where 0 means no preference among records with the same priority)')
        elif record_type != RecordType.SRV and v is not None:
            raise ValueError(f'Weight field is not applicable for {record_type} records. Please remove the weight value or change the record type to SRV')
        return v

    @validator('port', always=True)
    def validate_port(cls, v, values):
        """Validate port for SRV records"""
        record_type = values.get('record_type')
        if record_type == RecordType.SRV and v is None:
            raise ValueError('Port is required for SRV records. Please provide the target port number (1-65535, e.g., 80 for HTTP, 443 for HTTPS)')
        elif record_type != RecordType.SRV and v is not None:
            raise ValueError(f'Port field is not applicable for {record_type} records. Please remove the port value or change the record type to SRV')
        return v
    
    @validator('name')
    def validate_record_name_constraints(cls, v, values):
        """Validate record name constraints based on record type"""
        record_type = values.get('record_type')
        
        # Basic name validation
        if not v:
            raise ValueError('Record name cannot be empty. Use "@" for the zone root or provide a valid hostname')
        
        # Remove trailing dot if present
        if v.endswith('.'):
            v = v[:-1]
        
        # Allow wildcards, underscores, @ and other valid DNS characters
        # Also allow dots for FQDN record names
        if not re.match(r'^[a-zA-Z0-9.*_@.-]+$', v):
            raise ValueError('Record name contains invalid characters. Only letters, numbers, dots, hyphens, underscores, asterisks, and @ are allowed')
        
        validated_name = v.lower()
        
        # Additional constraints based on record type
        if record_type == RecordType.SRV:
            # SRV records must follow _service._proto.name format
            if not re.match(r'^_[a-zA-Z0-9-]+\._[a-zA-Z0-9-]+', validated_name):
                raise ValueError('SRV record name must follow _service._proto.name format (e.g., _http._tcp for HTTP service over TCP, _sip._udp for SIP over UDP)')
        
        elif record_type == RecordType.CNAME:
            # CNAME records cannot be @ (zone apex)
            if validated_name in ['@', '']:
                raise ValueError('CNAME record cannot be created for the zone apex (@). Use A or AAAA records instead for the root domain')
        
        # Validate length constraints
        if len(validated_name) > 253:
            raise ValueError(f'Record name too long ({len(validated_name)} characters). DNS names cannot exceed 253 characters total')
        
        # Validate individual labels
        if '.' in validated_name and validated_name not in ['@', '*']:
            labels = validated_name.split('.')
            for i, label in enumerate(labels):
                if label and len(label) > 63:
                    raise ValueError(f'Record name label "{label}" is too long ({len(label)} characters). Each label in a DNS name cannot exceed 63 characters')
        else:
            # Single label validation (no dots)
            if validated_name not in ['@', '*'] and len(validated_name) > 63:
                raise ValueError(f'Record name "{validated_name}" is too long ({len(validated_name)} characters). DNS labels cannot exceed 63 characters')
        
        return validated_name
    
    @model_validator(mode='after')
    def validate_record_consistency(self):
        """Validate overall record consistency"""
        record_type = self.record_type
        name = self.name
        
        # Additional SRV validation at model level
        if record_type == RecordType.SRV:
            if name and not re.match(r'^_[a-zA-Z0-9-]+\._[a-zA-Z0-9-]+', name.lower()):
                raise ValueError('SRV record name must follow _service._proto.name format (e.g., _http._tcp for HTTP service, _sip._udp for SIP service)')
        
        # CNAME record constraints
        if record_type == RecordType.CNAME:
            # CNAME records cannot coexist with other record types at the same name
            # This validation would need to be done at the service level with database context
            # For now, we'll validate the basic format
            if name and name.lower() in ['@', '']:
                raise ValueError('CNAME record cannot be created for the zone apex (@). Use A or AAAA records for the root domain instead')
        
        # Additional validation for specific record types
        if record_type == RecordType.MX and self.priority is None:
            raise ValueError('MX records must have a priority value. Lower numbers indicate higher priority (typically 10, 20, 30)')
        
        if record_type == RecordType.SRV:
            if self.priority is None or self.weight is None or self.port is None:
                raise ValueError('SRV records must have priority, weight, and port values. Priority determines order (lower = higher priority), weight is for load balancing, and port is the service port number')
        
        return self


class DNSRecordUpdate(BaseModel):
    """Schema for updating existing DNS records"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="DNS record name")
    value: Optional[str] = Field(None, min_length=1, max_length=500, description="DNS record value")
    ttl: Optional[int] = Field(None, ge=60, le=86400, description="Time to live in seconds")
    priority: Optional[int] = Field(None, ge=0, le=65535, description="Priority for MX and SRV records")
    weight: Optional[int] = Field(None, ge=0, le=65535, description="Weight for SRV records")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Port for SRV records")
    is_active: Optional[bool] = Field(None, description="Whether the record is active")

    @validator('name')
    def validate_record_name(cls, v):
        """Validate DNS record name"""
        if v is not None:
            if not v:
                raise ValueError('Record name cannot be empty')
            
            # Remove trailing dot if present
            if v.endswith('.'):
                v = v[:-1]
            
            # Allow wildcards, underscores, and @ for DNS records
            if not re.match(r'^[a-zA-Z0-9.*_@-]+$', v):
                raise ValueError('Record name contains invalid characters')
            
            return v.lower()
        return v

    @validator('value')
    def validate_record_value(cls, v):
        """Validate DNS record value format (basic validation without record type context)"""
        if v is not None:
            # Basic validation - specific validation will be done at service level with record type context
            if not v.strip():
                raise ValueError('Record value cannot be empty or whitespace only')
            
            # Check for reasonable length
            if len(v) > 500:
                raise ValueError('Record value too long (max 500 characters)')
        
        return v


class DNSRecord(DNSRecordBase):
    """Schema for DNS record responses"""
    id: int = Field(..., description="Unique record identifier")
    zone_id: int = Field(..., description="ID of the zone this record belongs to")
    is_active: bool = Field(..., description="Whether the record is active")
    created_by: Optional[int] = Field(None, description="ID of user who created the record")
    updated_by: Optional[int] = Field(None, description="ID of user who last updated the record")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ZoneExportData(BaseModel):
    """Schema for zone export data"""
    zone: Zone = Field(..., description="Zone configuration")
    records: List[DNSRecord] = Field(default=[], description="DNS records")
    format: ZoneExportFormat = Field(default=ZoneExportFormat.JSON, description="Export format")
    export_timestamp: datetime = Field(..., description="Export timestamp")
    export_version: str = Field(default="1.0", description="Export format version")


# Forwarder Schemas
class ForwarderServer(BaseModel):
    """Schema for forwarder server configuration"""
    ip: str = Field(..., description="IP address of the forwarder server")
    port: int = Field(default=53, ge=1, le=65535, description="Port number for DNS queries")
    priority: int = Field(default=1, ge=1, le=10, description="Server priority within forwarder (1 = highest)")
    weight: int = Field(default=1, ge=1, le=100, description="Server weight for load balancing")
    enabled: bool = Field(default=True, description="Whether this server is enabled")

    @validator('ip')
    def validate_ip_address(cls, v):
        """Validate IP address format"""
        if not v or not v.strip():
            raise ValueError('IP address cannot be empty. Please provide a valid IPv4 or IPv6 address (e.g., 192.168.1.1 or 2001:db8::1)')
        
        v = v.strip()
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f'Invalid IP address format: "{v}". Please provide a valid IPv4 address (e.g., 192.168.1.1) or IPv6 address (e.g., 2001:db8::1)')
        return v
    
    @validator('port')
    def validate_port_number(cls, v):
        """Validate port number"""
        if v < 1:
            raise ValueError(f'Port number too low ({v}). Port numbers must be between 1 and 65535')
        if v > 65535:
            raise ValueError(f'Port number too high ({v}). Port numbers must be between 1 and 65535')
        if v != 53 and v < 1024:
            # Warn about privileged ports (though not an error)
            pass  # Could add a warning here if we had a warning system
        return v
    
    @validator('priority')
    def validate_priority_value(cls, v):
        """Validate priority value"""
        if v < 1:
            raise ValueError(f'Priority too low ({v}). Priority must be between 1 and 10, where 1 is highest priority')
        if v > 10:
            raise ValueError(f'Priority too high ({v}). Priority must be between 1 and 10, where 1 is highest priority')
        return v
    
    @validator('weight')
    def validate_weight_value(cls, v):
        """Validate weight value"""
        if v < 1:
            raise ValueError(f'Weight too low ({v}). Weight must be between 1 and 100')
        if v > 100:
            raise ValueError(f'Weight too high ({v}). Weight must be between 1 and 100')
        return v
    
    class Config:
        from_attributes = True


class ForwarderBase(BaseModel):
    """Base schema for DNS forwarders with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Forwarder name")
    domains: List[str] = Field(..., min_items=1, description="List of domains to forward")
    forwarder_type: ForwarderType = Field(..., description="Type of forwarder")
    servers: List[ForwarderServer] = Field(..., min_items=1, description="List of forwarder servers")
    description: Optional[str] = Field(None, max_length=500, description="Optional forwarder description")
    health_check_enabled: bool = Field(True, description="Whether health checking is enabled")
    
    # Priority management
    priority: int = Field(default=5, ge=1, le=10, description="Forwarder priority (1 = highest)")
    
    # Grouping support
    group_name: Optional[str] = Field(None, max_length=100, description="Optional group name for organization")
    group_priority: int = Field(default=5, ge=1, le=10, description="Priority within group (1 = highest)")

    @validator('domains')
    def validate_domains(cls, v):
        """Validate domain names"""
        if not v or len(v) == 0:
            raise ValueError('At least one domain must be specified for forwarding. Please provide domains like ["example.com", "internal.local"]')
        
        validated_domains = []
        for i, domain in enumerate(v):
            if not domain or not domain.strip():
                raise ValueError(f'Domain at position {i+1} cannot be empty. Please provide a valid domain name')
            
            domain = domain.strip()
            try:
                validated_domain = DNSValidators.validate_domain_name(domain, 'forwarder domain')
                validated_domains.append(validated_domain)
            except ValueError as e:
                raise ValueError(f'Invalid domain at position {i+1}: {str(e)}')
        
        # Check for duplicates
        if len(validated_domains) != len(set(validated_domains)):
            raise ValueError('Duplicate domains found. Each domain should only be listed once')
        
        return validated_domains
    
    @validator('name')
    def validate_forwarder_name(cls, v):
        """Validate forwarder name"""
        if not v or not v.strip():
            raise ValueError('Forwarder name cannot be empty. Please provide a descriptive name (e.g., "Active Directory", "Internal DNS")')
        
        v = v.strip()
        if len(v) > 255:
            raise ValueError(f'Forwarder name too long ({len(v)} characters). Maximum length is 255 characters')
        
        # Check for reasonable characters
        if not re.match(r'^[a-zA-Z0-9\s\-_.()]+$', v):
            raise ValueError('Forwarder name contains invalid characters. Only letters, numbers, spaces, hyphens, underscores, dots, and parentheses are allowed')
        
        return v
    
    @validator('servers')
    def validate_server_list(cls, v):
        """Validate server list"""
        if not v or len(v) == 0:
            raise ValueError('At least one forwarder server must be specified. Please provide server configurations with IP addresses')
        
        if len(v) > 10:
            raise ValueError(f'Too many forwarder servers ({len(v)}). Maximum is 10 servers per forwarder')
        
        # Check for duplicate IPs
        ips = [server.ip for server in v]
        if len(ips) != len(set(ips)):
            raise ValueError('Duplicate server IP addresses found. Each server should have a unique IP address')
        
        return v


class ForwarderCreate(ForwarderBase):
    """Schema for creating new DNS forwarders"""
    pass


class ForwarderUpdate(BaseModel):
    """Schema for updating existing DNS forwarders"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Forwarder name")
    domains: Optional[List[str]] = Field(None, min_items=1, description="List of domains to forward")
    servers: Optional[List[ForwarderServer]] = Field(None, min_items=1, description="List of forwarder servers")
    description: Optional[str] = Field(None, max_length=500, description="Forwarder description")
    health_check_enabled: Optional[bool] = Field(None, description="Whether health checking is enabled")
    is_active: Optional[bool] = Field(None, description="Whether the forwarder is active")
    
    # Priority management
    priority: Optional[int] = Field(None, ge=1, le=10, description="Forwarder priority (1 = highest)")
    
    # Grouping support
    group_name: Optional[str] = Field(None, max_length=100, description="Optional group name for organization")
    group_priority: Optional[int] = Field(None, ge=1, le=10, description="Priority within group (1 = highest)")

    @validator('domains')
    def validate_domains(cls, v):
        """Validate domain names"""
        if v is not None:
            validated_domains = []
            for domain in v:
                validated_domain = DNSValidators.validate_domain_name(domain, 'forwarder')
                validated_domains.append(validated_domain)
            return validated_domains
        return v


# Forwarder Template Schemas
class ForwarderTemplateBase(BaseModel):
    """Base schema for forwarder templates"""
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    forwarder_type: ForwarderType = Field(..., description="Type of forwarder")
    
    # Default configuration
    default_domains: Optional[List[str]] = Field(None, description="Default domains for this template")
    default_servers: Optional[List[ForwarderServer]] = Field(None, description="Default server configurations")
    default_priority: int = Field(default=5, ge=1, le=10, description="Default forwarder priority")
    default_group_name: Optional[str] = Field(None, max_length=100, description="Default group name")
    default_health_check_enabled: bool = Field(True, description="Default health check setting")
    
    @validator('default_domains')
    def validate_default_domains(cls, v):
        """Validate default domain names"""
        if v is not None:
            validated_domains = []
            for domain in v:
                validated_domain = DNSValidators.validate_domain_name(domain, 'template')
                validated_domains.append(validated_domain)
            return validated_domains
        return v


class ForwarderTemplateCreate(ForwarderTemplateBase):
    """Schema for creating new forwarder templates"""
    is_system_template: bool = Field(False, description="Whether this is a system template")


class ForwarderTemplateUpdate(BaseModel):
    """Schema for updating existing forwarder templates"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    default_domains: Optional[List[str]] = Field(None, description="Default domains for this template")
    default_servers: Optional[List[ForwarderServer]] = Field(None, description="Default server configurations")
    default_priority: Optional[int] = Field(None, ge=1, le=10, description="Default forwarder priority")
    default_group_name: Optional[str] = Field(None, max_length=100, description="Default group name")
    default_health_check_enabled: Optional[bool] = Field(None, description="Default health check setting")
    
    @validator('default_domains')
    def validate_default_domains(cls, v):
        """Validate default domain names"""
        if v is not None:
            validated_domains = []
            for domain in v:
                validated_domain = DNSValidators.validate_domain_name(domain, 'template')
                validated_domains.append(validated_domain)
            return validated_domains
        return v


class ForwarderTemplate(ForwarderTemplateBase):
    """Schema for forwarder template responses"""
    id: int
    is_system_template: bool
    usage_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ForwarderFromTemplate(BaseModel):
    """Schema for creating a forwarder from a template"""
    template_id: int = Field(..., description="ID of the template to use")
    name: str = Field(..., min_length=1, max_length=255, description="Name for the new forwarder")
    
    # Override template defaults
    domains: Optional[List[str]] = Field(None, description="Override default domains")
    servers: Optional[List[ForwarderServer]] = Field(None, description="Override default servers")
    priority: Optional[int] = Field(None, ge=1, le=10, description="Override default priority")
    group_name: Optional[str] = Field(None, max_length=100, description="Override default group name")
    health_check_enabled: Optional[bool] = Field(None, description="Override default health check setting")
    description: Optional[str] = Field(None, max_length=500, description="Forwarder description")
    
    @validator('domains')
    def validate_domains(cls, v):
        """Validate domain names"""
        if v is not None:
            validated_domains = []
            for domain in v:
                validated_domain = DNSValidators.validate_domain_name(domain, 'forwarder')
                validated_domains.append(validated_domain)
            return validated_domains
        return v


# Forwarder Grouping Schemas
class ForwarderGroup(BaseModel):
    """Schema for forwarder group information"""
    group_name: str = Field(..., description="Group name")
    forwarder_count: int = Field(..., description="Number of forwarders in group")
    active_count: int = Field(..., description="Number of active forwarders in group")
    forwarder_types: List[str] = Field(..., description="Types of forwarders in group")
    avg_priority: float = Field(..., description="Average priority of forwarders in group")
    health_status: str = Field(..., description="Overall health status of group")


class ForwarderGroupUpdate(BaseModel):
    """Schema for updating forwarder group settings"""
    new_group_name: Optional[str] = Field(None, max_length=100, description="New group name")
    group_priority: Optional[int] = Field(None, ge=1, le=10, description="New group priority for all forwarders")


class Forwarder(ForwarderBase):
    """Schema for DNS forwarder responses"""
    id: int = Field(..., description="Unique forwarder identifier")
    is_active: bool = Field(..., description="Whether the forwarder is active")
    
    # Template information
    is_template: bool = Field(False, description="Whether this is a template")
    template_name: Optional[str] = Field(None, description="Template name if this is a template")
    created_from_template: Optional[str] = Field(None, description="Template used to create this forwarder")
    
    # Audit fields
    created_by: Optional[int] = Field(None, description="ID of user who created the forwarder")
    updated_by: Optional[int] = Field(None, description="ID of user who last updated the forwarder")
    created_at: datetime = Field(..., description="Forwarder creation timestamp")
    updated_at: datetime = Field(..., description="Forwarder last update timestamp")
    health_status: Optional[str] = Field("unknown", description="Overall health status")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Forwarder Health Schemas
class ForwarderHealthBase(BaseModel):
    """Base schema for forwarder health checks"""
    forwarder_id: int = Field(..., description="ID of the forwarder")
    server_ip: str = Field(..., description="IP address of the forwarder server")
    status: str = Field(..., min_length=1, max_length=20, description="Health status")
    response_time: Optional[int] = Field(None, ge=0, description="Response time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if health check failed")
    checked_at: datetime = Field(..., description="Timestamp of the health check")

    @validator('server_ip')
    def validate_server_ip(cls, v):
        """Validate server IP address"""
        return DNSValidators.validate_ipv4_address(v)

    @validator('status')
    def validate_status(cls, v):
        """Validate health status"""
        valid_statuses = ['healthy', 'unhealthy', 'timeout', 'error', 'unknown']
        if v.lower() not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v.lower()


class ForwarderHealthCreate(ForwarderHealthBase):
    """Schema for creating forwarder health check records"""
    pass


class ForwarderHealthUpdate(BaseModel):
    """Schema for updating forwarder health check records"""
    status: Optional[str] = Field(None, min_length=1, max_length=20)
    response_time: Optional[int] = Field(None, ge=0)
    error_message: Optional[str] = None
    checked_at: Optional[datetime] = None

    @validator('status')
    def validate_status(cls, v):
        """Validate health status"""
        if v is not None:
            valid_statuses = ['healthy', 'unhealthy', 'timeout', 'error', 'unknown']
            if v.lower() not in valid_statuses:
                raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
            return v.lower()
        return v


class ForwarderHealth(ForwarderHealthBase):
    """Schema for forwarder health check response"""
    id: int

    class Config:
        from_attributes = True


# Response Schemas
class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema for paginated responses
    
    Usage:
        PaginatedResponse[Zone] for paginated zone responses
        PaginatedResponse[DNSRecord] for paginated record responses
        PaginatedResponse[Forwarder] for paginated forwarder responses
    """
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=1000, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")
    
    @validator('pages', always=True)
    def calculate_pages(cls, v, values):
        """Calculate total pages based on total items and per_page"""
        total = values.get('total', 0)
        per_page = values.get('per_page', 1)
        if per_page > 0:
            return (total + per_page - 1) // per_page  # Ceiling division
        return 0
    
    @model_validator(mode='after')
    def validate_page_range(cls, values):
        """Validate that page number is within valid range"""
        if hasattr(values, 'page') and hasattr(values, 'pages'):
            if values.pages > 0 and values.page > values.pages:
                raise ValueError(f'Page {values.page} exceeds total pages {values.pages}')
        return values
    
    class Config:
        """Pydantic configuration"""
        # Allow arbitrary types for generic support
        arbitrary_types_allowed = True
        # JSON schema extra information
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "per_page": 20,
                "pages": 5
            }
        }


class HealthCheckResult(BaseModel):
    """Schema for health check results"""
    server_ip: str = Field(..., description="IP address of the checked server")
    status: str = Field(..., description="Health status")
    response_time: Optional[int] = Field(None, description="Response time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    checked_at: datetime = Field(..., description="Timestamp of the health check")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ZoneValidationResult(BaseModel):
    """Schema for zone validation results"""
    valid: bool = Field(..., description="Whether the zone is valid")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")


class SerialValidationResult(BaseModel):
    """Schema for serial number validation results"""
    valid: bool = Field(..., description="Whether the serial number is valid")
    format: str = Field(..., description="Serial number format (YYYYMMDDNN, unknown, invalid)")
    year: Optional[int] = Field(None, description="Year from serial number")
    month: Optional[int] = Field(None, description="Month from serial number")
    day: Optional[int] = Field(None, description="Day from serial number")
    sequence: Optional[int] = Field(None, description="Sequence number from serial")
    date_valid: Optional[bool] = Field(None, description="Whether the date portion is valid")
    date_str: Optional[str] = Field(None, description="Date string representation")
    error: Optional[str] = Field(None, description="Error message if invalid")


class SerialHistoryEntry(BaseModel):
    """Schema for serial number history entries"""
    serial: Optional[int] = Field(None, description="Serial number")
    updated_at: Optional[datetime] = Field(None, description="When the serial was updated")
    updated_by: Optional[int] = Field(None, description="User who updated the serial")
    current: bool = Field(False, description="Whether this is the current serial")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SerialHistoryResponse(BaseModel):
    """Schema for serial history response"""
    zone_id: int = Field(..., description="Zone ID")
    zone_name: str = Field(..., description="Zone name")
    history: List[SerialHistoryEntry] = Field(..., description="Serial number history")
    
    class Config:
        from_attributes = True


class ValidationResult(BaseModel):
    """Generic schema for validation results"""
    valid: bool = Field(..., description="Whether the validation passed")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional validation details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "valid": False,
                "errors": ["Invalid domain name format", "Missing required field"],
                "warnings": ["TTL value is very low"],
                "details": {
                    "field": "domain",
                    "value": "invalid..domain",
                    "suggestion": "Use valid domain format like 'example.com'"
                }
            }
        }


# SystemStatus moved to system.py to avoid duplication

class HealthCheckResult(BaseModel):
    """Schema for individual health check results"""
    server_ip: str = Field(..., description="IP address of the DNS server")
    server_port: int = Field(default=53, description="Port of the DNS server")
    status: str = Field(..., description="Health status: healthy, unhealthy, timeout, error")
    response_time: Optional[int] = Field(None, description="Response time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if status is not healthy")
    resolved_ips: Optional[List[str]] = Field(None, description="Resolved IP addresses for test query")
    message: Optional[str] = Field(None, description="Additional status message")
    checked_at: datetime = Field(..., description="Timestamp of the health check")
    
    class Config:
        from_attributes = True

class ForwarderHealthStatus(BaseModel):
    """Schema for forwarder overall health status"""
    overall_status: str = Field(..., description="Overall health status: healthy, unhealthy, degraded, unknown")
    healthy_servers: int = Field(..., description="Number of healthy servers")
    total_servers: int = Field(..., description="Total number of servers")
    last_checked: Optional[datetime] = Field(None, description="Last health check timestamp")
    server_statuses: Dict[str, Dict] = Field(default_factory=dict, description="Individual server statuses")
    
    class Config:
        from_attributes = True

class ForwarderTestResult(BaseModel):
    """Schema for forwarder test results"""
    server_ip: str = Field(..., description="IP address of the tested server")
    server_port: int = Field(default=53, description="Port of the tested server")
    successful_queries: int = Field(..., description="Number of successful queries")
    total_queries: int = Field(..., description="Total number of queries attempted")
    success_rate: float = Field(..., description="Success rate as percentage")
    avg_response_time: Optional[float] = Field(None, description="Average response time in milliseconds")
    query_results: List[Dict] = Field(default_factory=list, description="Individual query results")
    
    class Config:
        from_attributes = True

class HealthSummary(BaseModel):
    """Schema for overall health summary"""
    total_forwarders: int = Field(..., description="Total number of forwarders")
    active_forwarders: int = Field(..., description="Number of active forwarders")
    health_check_enabled: int = Field(..., description="Number of forwarders with health checking enabled")
    healthy_forwarders: int = Field(..., description="Number of healthy forwarders")
    unhealthy_forwarders: int = Field(..., description="Number of unhealthy forwarders")
    degraded_forwarders: int = Field(..., description="Number of degraded forwarders")
    unknown_forwarders: int = Field(..., description="Number of forwarders with unknown status")
    last_updated: datetime = Field(..., description="Last update timestamp")
    forwarder_details: List[Dict] = Field(default_factory=list, description="Detailed forwarder information")
    
    class Config:
        from_attributes = True


# Zone Management Schemas
class ZoneValidationResult(BaseModel):
    """Schema for zone validation results"""
    valid: bool = Field(..., description="Whether the zone configuration is valid")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional validation details")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "valid": True,
                "errors": [],
                "warnings": ["Zone has no NS records"],
                "details": {
                    "zone_name": "example.com",
                    "zone_type": "master",
                    "record_count": 5
                }
            }
        }


class SerialValidationResult(BaseModel):
    """Schema for serial number validation results"""
    valid: bool = Field(..., description="Whether the serial number is valid")
    format: str = Field(..., description="Serial number format (YYYYMMDDNN, timestamp, etc.)")
    year: Optional[int] = Field(None, description="Year component if YYYYMMDDNN format")
    month: Optional[int] = Field(None, description="Month component if YYYYMMDDNN format")
    day: Optional[int] = Field(None, description="Day component if YYYYMMDDNN format")
    sequence: Optional[int] = Field(None, description="Sequence number if YYYYMMDDNN format")
    date_valid: Optional[bool] = Field(None, description="Whether the date component is valid")
    date_str: Optional[str] = Field(None, description="Date string representation")
    error: Optional[str] = Field(None, description="Error message if invalid")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "valid": True,
                "format": "YYYYMMDDNN",
                "year": 2024,
                "month": 1,
                "day": 15,
                "sequence": 1,
                "date_valid": True,
                "date_str": "2024-01-15",
                "error": None
            }
        }


class SerialHistoryEntry(BaseModel):
    """Schema for a single serial history entry"""
    serial: int = Field(..., description="Serial number")
    updated_at: datetime = Field(..., description="When the serial was set")
    updated_by: Optional[int] = Field(None, description="User ID who updated the serial")
    reason: Optional[str] = Field(None, description="Reason for the serial change")
    current: bool = Field(default=False, description="Whether this is the current serial")
    
    class Config:
        from_attributes = True


class SerialHistoryResponse(BaseModel):
    """Schema for serial number history response"""
    zone_id: int = Field(..., description="Zone ID")
    zone_name: str = Field(..., description="Zone name")
    history: List[SerialHistoryEntry] = Field(..., description="Serial number history")
    
    class Config:
        from_attributes = True


class ZoneQueryParams(BaseModel):
    """Schema for zone query parameters"""
    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of items to return")
    zone_type: Optional[str] = Field(None, description="Filter by zone type")
    active_only: bool = Field(default=True, description="Filter to active zones only")
    search: Optional[str] = Field(None, description="Search term")
    sort_by: Optional[str] = Field(default="name", description="Field to sort by")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")
    
    class Config:
        from_attributes = True


class ZoneStatistics(BaseModel):
    """Schema for zone statistics"""
    zone_id: int = Field(..., description="Zone ID")
    zone_name: str = Field(..., description="Zone name")
    zone_type: str = Field(..., description="Zone type")
    is_active: bool = Field(..., description="Whether the zone is active")
    total_records: int = Field(..., description="Total number of records")
    record_counts: Dict[str, int] = Field(default_factory=dict, description="Record counts by type")
    serial: Optional[int] = Field(None, description="Current serial number")
    serial_info: Optional[Dict[str, Any]] = Field(None, description="Serial number information")
    refresh: int = Field(..., description="SOA refresh interval")
    retry: int = Field(..., description="SOA retry interval")
    expire: int = Field(..., description="SOA expire interval")
    minimum: int = Field(..., description="SOA minimum TTL")
    created_at: datetime = Field(..., description="Zone creation timestamp")
    updated_at: datetime = Field(..., description="Zone last update timestamp")
    created_by: Optional[int] = Field(None, description="User ID who created the zone")
    updated_by: Optional[int] = Field(None, description="User ID who last updated the zone")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "zone_id": 1,
                "zone_name": "example.com",
                "zone_type": "master",
                "is_active": True,
                "total_records": 10,
                "record_counts": {
                    "A": 5,
                    "AAAA": 2,
                    "CNAME": 2,
                    "MX": 1
                },
                "serial": 2024011501,
                "serial_info": {
                    "valid": True,
                    "format": "YYYYMMDDNN",
                    "date_str": "2024-01-15"
                },
                "refresh": 10800,
                "retry": 3600,
                "expire": 604800,
                "minimum": 86400,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T15:30:00Z",
                "created_by": 1,
                "updated_by": 1
            }
        }


class ZoneValidationResult(BaseModel):
    """Schema for zone/record validation results"""
    valid: bool = Field(..., description="Whether the validation passed")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "valid": False,
                "errors": ["Invalid IPv4 address format", "Record name too long"],
                "warnings": ["TTL value is very low"]
            }
        }


class RecordStatistics(BaseModel):
    """Schema for DNS record statistics"""
    total_records: int = Field(..., description="Total number of records")
    active_records: int = Field(..., description="Number of active records")
    inactive_records: int = Field(..., description="Number of inactive records")
    records_by_type: Dict[str, int] = Field(..., description="Count of records by type")
    zone_id: Optional[int] = Field(None, description="Zone ID if statistics are zone-specific")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "total_records": 25,
                "active_records": 23,
                "inactive_records": 2,
                "records_by_type": {
                    "A": 10,
                    "AAAA": 5,
                    "CNAME": 8,
                    "MX": 2
                },
                "zone_id": 1
            }
        }


# DNS Record History Schemas

class DNSRecordHistoryBase(BaseModel):
    """Base schema for DNS record history"""
    record_id: int = Field(..., description="Original record ID")
    zone_id: int = Field(..., description="Zone ID")
    name: str = Field(..., description="Record name at time of change")
    record_type: str = Field(..., description="Record type at time of change")
    value: str = Field(..., description="Record value at time of change")
    ttl: Optional[int] = Field(None, description="TTL at time of change")
    priority: Optional[int] = Field(None, description="Priority at time of change")
    weight: Optional[int] = Field(None, description="Weight at time of change")
    port: Optional[int] = Field(None, description="Port at time of change")
    is_active: bool = Field(..., description="Active status at time of change")
    change_type: str = Field(..., description="Type of change (create, update, delete, activate, deactivate)")
    change_details: Optional[Dict[str, Any]] = Field(None, description="Details about what changed")
    previous_values: Optional[Dict[str, Any]] = Field(None, description="Previous values for updates")

class DNSRecordHistory(DNSRecordHistoryBase):
    """Schema for DNS record history with metadata"""
    id: int = Field(..., description="History record ID")
    changed_at: datetime = Field(..., description="When the change occurred")
    changed_by: Optional[int] = Field(None, description="User ID who made the change")
    changed_by_username: Optional[str] = Field(None, description="Username who made the change")
    
    class Config:
        from_attributes = True


# Record Import/Export Schemas

class RecordImportFormat(str, Enum):
    """Supported record import formats"""
    BIND_ZONE = "bind_zone"
    CSV = "csv"
    JSON = "json"

class RecordExportFormat(str, Enum):
    """Supported record export formats"""
    BIND_ZONE = "bind_zone"
    CSV = "csv"
    JSON = "json"

class RecordImportRequest(BaseModel):
    """Schema for record import request"""
    format: RecordImportFormat = Field(..., description="Import format")
    data: str = Field(..., description="Import data content")
    zone_id: int = Field(..., description="Target zone ID")
    overwrite_existing: bool = Field(False, description="Whether to overwrite existing records")
    validate_only: bool = Field(False, description="Only validate, don't import")

class RecordImportResult(BaseModel):
    """Schema for record import result"""
    success: bool = Field(..., description="Whether import was successful")
    imported_count: int = Field(0, description="Number of records imported")
    skipped_count: int = Field(0, description="Number of records skipped")
    error_count: int = Field(0, description="Number of records with errors")
    errors: List[str] = Field(default_factory=list, description="Import errors")
    warnings: List[str] = Field(default_factory=list, description="Import warnings")
    imported_records: List[DNSRecord] = Field(default_factory=list, description="Successfully imported records")

class RecordExportRequest(BaseModel):
    """Schema for record export request"""
    format: RecordExportFormat = Field(..., description="Export format")
    zone_id: Optional[int] = Field(None, description="Zone ID to export (all zones if not specified)")
    record_types: Optional[List[str]] = Field(None, description="Record types to export")
    active_only: bool = Field(True, description="Export only active records")
    include_metadata: bool = Field(False, description="Include creation/modification metadata")

class RecordExportResult(BaseModel):
    """Schema for record export result"""
    success: bool = Field(..., description="Whether export was successful")
    format: RecordExportFormat = Field(..., description="Export format used")
    data: str = Field(..., description="Exported data content")
    record_count: int = Field(..., description="Number of records exported")
    filename: Optional[str] = Field(None, description="Suggested filename for download")


# Enhanced Record Validation Schemas

class RecordValidationRequest(BaseModel):
    """Schema for record validation request"""
    records: List[DNSRecordCreate] = Field(..., description="Records to validate")
    zone_id: int = Field(..., description="Target zone ID")
    check_conflicts: bool = Field(True, description="Check for conflicts with existing records")
    check_dns_compliance: bool = Field(True, description="Check DNS compliance")

class RecordValidationError(BaseModel):
    """Schema for individual record validation error"""
    record_index: int = Field(..., description="Index of the record in the validation request")
    field: Optional[str] = Field(None, description="Field that caused the error")
    error_type: str = Field(..., description="Type of validation error")
    message: str = Field(..., description="Error message")
    severity: str = Field(..., description="Error severity (error, warning)")

class RecordValidationResult(BaseModel):
    """Schema for record validation result"""
    valid: bool = Field(..., description="Whether all records are valid")
    total_records: int = Field(..., description="Total number of records validated")
    valid_records: int = Field(..., description="Number of valid records")
    error_count: int = Field(..., description="Number of records with errors")
    warning_count: int = Field(..., description="Number of records with warnings")
    errors: List[RecordValidationError] = Field(default_factory=list, description="Validation errors")
    warnings: List[RecordValidationError] = Field(default_factory=list, description="Validation warnings")


# Enhanced Record Statistics Schemas

class RecordTypeStatistics(BaseModel):
    """Schema for statistics by record type"""
    record_type: str = Field(..., description="DNS record type")
    total_count: int = Field(..., description="Total records of this type")
    active_count: int = Field(..., description="Active records of this type")
    inactive_count: int = Field(..., description="Inactive records of this type")
    percentage: float = Field(..., description="Percentage of total records")

class ZoneRecordStatistics(BaseModel):
    """Schema for zone-specific record statistics"""
    zone_id: int = Field(..., description="Zone ID")
    zone_name: str = Field(..., description="Zone name")
    total_records: int = Field(..., description="Total records in zone")
    active_records: int = Field(..., description="Active records in zone")
    inactive_records: int = Field(..., description="Inactive records in zone")
    record_types: List[RecordTypeStatistics] = Field(..., description="Statistics by record type")
    last_modified: Optional[datetime] = Field(None, description="Last modification time")

class GlobalRecordStatistics(BaseModel):
    """Schema for global record statistics across all zones"""
    total_records: int = Field(..., description="Total records across all zones")
    active_records: int = Field(..., description="Active records across all zones")
    inactive_records: int = Field(..., description="Inactive records across all zones")
    total_zones: int = Field(..., description="Total number of zones")
    zones_with_records: int = Field(..., description="Number of zones with records")
    record_types: List[RecordTypeStatistics] = Field(..., description="Global statistics by record type")
    zone_statistics: List[ZoneRecordStatistics] = Field(..., description="Per-zone statistics")
    most_common_types: List[str] = Field(..., description="Most common record types")
    recent_changes: int = Field(..., description="Number of changes in last 24 hours")


# Record History Query Schemas

class RecordHistoryQuery(BaseModel):
    """Schema for querying record history"""
    record_id: Optional[int] = Field(None, description="Filter by specific record ID")
    zone_id: Optional[int] = Field(None, description="Filter by zone ID")
    change_type: Optional[str] = Field(None, description="Filter by change type")
    changed_by: Optional[int] = Field(None, description="Filter by user who made changes")
    date_from: Optional[datetime] = Field(None, description="Filter changes from this date")
    date_to: Optional[datetime] = Field(None, description="Filter changes to this date")
    record_type: Optional[str] = Field(None, description="Filter by record type")
    record_name: Optional[str] = Field(None, description="Filter by record name")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of records to return")
    sort_by: str = Field("changed_at", description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")

class RecordHistoryResponse(BaseModel):
    """Schema for record history response"""
    items: List[DNSRecordHistory] = Field(..., description="History records")
    total: int = Field(..., description="Total number of history records")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Records per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")