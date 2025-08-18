"""
Validation helper functions with clear error messages for DNS operations
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import ipaddress
from pydantic import ValidationError

from ..schemas.dns import DNSValidators
from .exceptions import ValidationException


class DNSValidationHelper:
    """Helper class for DNS validation with user-friendly error messages"""
    
    @staticmethod
    def validate_zone_data(zone_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate zone data and return validation results with helpful messages
        
        Args:
            zone_data: Dictionary containing zone data
            
        Returns:
            Tuple of (is_valid, errors, suggestions)
        """
        errors = []
        suggestions = []
        
        # Check required fields
        required_fields = ['name', 'zone_type', 'email']
        for field in required_fields:
            if field not in zone_data or not zone_data[field]:
                errors.append(f"Field '{field}' is required")
                if field == 'name':
                    suggestions.append("Provide a valid domain name like 'example.com' or 'internal.local'")
                elif field == 'zone_type':
                    suggestions.append("Choose zone type: 'master' for authoritative zones, 'slave' for secondary zones, or 'forward' for forwarding zones")
                elif field == 'email':
                    suggestions.append("Provide administrator email in DNS format like 'admin.example.com' (use dots instead of @)")
        
        # Validate zone name
        if 'name' in zone_data and zone_data['name']:
            try:
                DNSValidators.validate_domain_name(zone_data['name'], 'zone')
            except ValueError as e:
                errors.append(f"Invalid zone name: {str(e)}")
                suggestions.append("Zone names should be valid domain names without trailing dots")
        
        # Validate email format
        if 'email' in zone_data and zone_data['email']:
            try:
                DNSValidators.validate_dns_email_format(zone_data['email'])
            except ValueError as e:
                errors.append(f"Invalid email format: {str(e)}")
                suggestions.append("Use DNS email format with dots instead of @ (e.g., 'admin.example.com' instead of 'admin@example.com')")
        
        # Validate zone type specific requirements
        zone_type = zone_data.get('zone_type')
        if zone_type == 'slave':
            if 'master_servers' not in zone_data or not zone_data['master_servers']:
                errors.append("Master servers are required for slave zones")
                suggestions.append("Provide IP addresses of master DNS servers (e.g., ['192.168.1.10', '192.168.1.11'])")
            else:
                for i, server in enumerate(zone_data['master_servers']):
                    try:
                        ipaddress.ip_address(server)
                    except ValueError:
                        errors.append(f"Invalid master server IP at position {i+1}: {server}")
                        suggestions.append(f"Provide valid IP address for master server {i+1}")
        
        elif zone_type == 'forward':
            if 'forwarders' not in zone_data or not zone_data['forwarders']:
                errors.append("Forwarders are required for forward zones")
                suggestions.append("Provide IP addresses of DNS servers to forward to (e.g., ['8.8.8.8', '1.1.1.1'])")
            else:
                for i, forwarder in enumerate(zone_data['forwarders']):
                    try:
                        ipaddress.ip_address(forwarder)
                    except ValueError:
                        errors.append(f"Invalid forwarder IP at position {i+1}: {forwarder}")
                        suggestions.append(f"Provide valid IP address for forwarder {i+1}")
        
        # Validate SOA timing values
        soa_fields = {
            'refresh': (300, 86400, "5 minutes to 24 hours"),
            'retry': (300, 86400, "5 minutes to 24 hours"),
            'expire': (86400, 2419200, "1 day to 28 days"),
            'minimum': (300, 86400, "5 minutes to 24 hours")
        }
        
        for field, (min_val, max_val, range_desc) in soa_fields.items():
            if field in zone_data and zone_data[field] is not None:
                try:
                    value = int(zone_data[field])
                    if value < min_val or value > max_val:
                        errors.append(f"SOA {field} value {value} is out of range")
                        suggestions.append(f"SOA {field} should be between {min_val} and {max_val} seconds ({range_desc})")
                except (ValueError, TypeError):
                    errors.append(f"SOA {field} must be a valid integer")
                    suggestions.append(f"Provide a numeric value for SOA {field} in seconds")
        
        return len(errors) == 0, errors, suggestions
    
    @staticmethod
    def validate_record_data(record_data: Dict[str, Any], zone_name: Optional[str] = None) -> Tuple[bool, List[str], List[str]]:
        """
        Validate DNS record data and return validation results with helpful messages
        
        Args:
            record_data: Dictionary containing record data
            zone_name: Optional zone name for context
            
        Returns:
            Tuple of (is_valid, errors, suggestions)
        """
        errors = []
        suggestions = []
        
        # Check required fields
        required_fields = ['name', 'record_type', 'value']
        for field in required_fields:
            if field not in record_data or not record_data[field]:
                errors.append(f"Field '{field}' is required")
                if field == 'name':
                    suggestions.append("Provide record name like 'www', 'mail', or '@' for root domain")
                elif field == 'record_type':
                    suggestions.append("Choose record type: A, AAAA, CNAME, MX, TXT, SRV, PTR, NS, etc.")
                elif field == 'value':
                    suggestions.append("Provide the record value (IP address, domain name, text, etc.)")
        
        record_type = record_data.get('record_type', '').upper()
        record_name = record_data.get('name', '')
        record_value = record_data.get('value', '')
        
        # Validate record name
        if record_name:
            try:
                if record_name not in ['@', '']:
                    DNSValidators.validate_domain_name(record_name, f'{record_type} record name')
            except ValueError as e:
                errors.append(f"Invalid record name: {str(e)}")
                suggestions.append("Record names should be valid hostnames or '@' for the zone root")
        
        # Validate record value based on type
        if record_type and record_value:
            try:
                if record_type == 'A':
                    DNSValidators.validate_ipv4_address(record_value)
                elif record_type == 'AAAA':
                    DNSValidators.validate_ipv6_address(record_value)
                elif record_type == 'CNAME':
                    DNSValidators.validate_cname_record_format(record_value)
                    if record_name in ['@', '']:
                        errors.append("CNAME records cannot be created for the zone root")
                        suggestions.append("Use A or AAAA records for the root domain instead")
                elif record_type == 'MX':
                    DNSValidators.validate_mx_record_format(record_value)
                    if 'priority' not in record_data or record_data['priority'] is None:
                        errors.append("Priority is required for MX records")
                        suggestions.append("Provide priority value (lower numbers = higher priority, typically 10, 20, 30)")
                elif record_type == 'TXT':
                    DNSValidators.validate_txt_record_format(record_value)
                elif record_type == 'SRV':
                    DNSValidators.validate_srv_record_format(record_value)
                    required_srv_fields = ['priority', 'weight', 'port']
                    for srv_field in required_srv_fields:
                        if srv_field not in record_data or record_data[srv_field] is None:
                            errors.append(f"{srv_field.title()} is required for SRV records")
                    if not record_name.startswith('_'):
                        errors.append("SRV record names must follow _service._proto format")
                        suggestions.append("Use format like '_http._tcp' or '_sip._udp'")
                elif record_type == 'PTR':
                    DNSValidators.validate_ptr_record_format(record_value)
                elif record_type == 'NS':
                    DNSValidators.validate_ns_record_format(record_value)
                # Add more record type validations as needed
                    
            except ValueError as e:
                errors.append(f"Invalid {record_type} record value: {str(e)}")
                if record_type == 'A':
                    suggestions.append("Provide a valid IPv4 address like '192.168.1.1'")
                elif record_type == 'AAAA':
                    suggestions.append("Provide a valid IPv6 address like '2001:db8::1'")
                elif record_type == 'CNAME':
                    suggestions.append("Provide a valid domain name as the target")
                elif record_type == 'MX':
                    suggestions.append("Provide a valid mail server domain name")
                elif record_type == 'TXT':
                    suggestions.append("Provide valid text content (enclose in quotes if it contains spaces)")
        
        # Validate TTL if provided
        if 'ttl' in record_data and record_data['ttl'] is not None:
            try:
                ttl = int(record_data['ttl'])
                if ttl < 60:
                    errors.append(f"TTL too short ({ttl} seconds)")
                    suggestions.append("TTL should be at least 60 seconds to reduce DNS query load")
                elif ttl > 86400:
                    errors.append(f"TTL too long ({ttl} seconds)")
                    suggestions.append("TTL should be at most 86400 seconds (24 hours) for reasonable caching")
            except (ValueError, TypeError):
                errors.append("TTL must be a valid integer")
                suggestions.append("Provide TTL in seconds (e.g., 300 for 5 minutes, 3600 for 1 hour)")
        
        return len(errors) == 0, errors, suggestions
    
    @staticmethod
    def validate_forwarder_data(forwarder_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate forwarder data and return validation results with helpful messages
        
        Args:
            forwarder_data: Dictionary containing forwarder data
            
        Returns:
            Tuple of (is_valid, errors, suggestions)
        """
        errors = []
        suggestions = []
        
        # Check required fields
        required_fields = ['name', 'domains', 'forwarder_type', 'servers']
        for field in required_fields:
            if field not in forwarder_data or not forwarder_data[field]:
                errors.append(f"Field '{field}' is required")
                if field == 'name':
                    suggestions.append("Provide a descriptive name like 'Active Directory' or 'Internal DNS'")
                elif field == 'domains':
                    suggestions.append("Provide domains to forward like ['example.com', 'internal.local']")
                elif field == 'forwarder_type':
                    suggestions.append("Choose type: 'active_directory', 'intranet', or 'public'")
                elif field == 'servers':
                    suggestions.append("Provide server configurations with IP addresses and ports")
        
        # Validate domains
        if 'domains' in forwarder_data and forwarder_data['domains']:
            domains = forwarder_data['domains']
            if not isinstance(domains, list):
                errors.append("Domains must be a list")
                suggestions.append("Provide domains as a list like ['example.com', 'internal.local']")
            else:
                for i, domain in enumerate(domains):
                    try:
                        DNSValidators.validate_domain_name(domain, 'forwarder domain')
                    except ValueError as e:
                        errors.append(f"Invalid domain at position {i+1}: {str(e)}")
                        suggestions.append(f"Provide valid domain name for position {i+1}")
        
        # Validate servers
        if 'servers' in forwarder_data and forwarder_data['servers']:
            servers = forwarder_data['servers']
            if not isinstance(servers, list):
                errors.append("Servers must be a list")
                suggestions.append("Provide servers as a list of server configurations")
            else:
                if len(servers) == 0:
                    errors.append("At least one server is required")
                    suggestions.append("Provide at least one server configuration with IP address")
                
                for i, server in enumerate(servers):
                    if not isinstance(server, dict):
                        errors.append(f"Server at position {i+1} must be an object")
                        suggestions.append(f"Provide server {i+1} as an object with 'ip' field")
                        continue
                    
                    if 'ip' not in server or not server['ip']:
                        errors.append(f"Server at position {i+1} missing IP address")
                        suggestions.append(f"Provide IP address for server {i+1}")
                    else:
                        try:
                            ipaddress.ip_address(server['ip'])
                        except ValueError:
                            errors.append(f"Invalid IP address for server {i+1}: {server['ip']}")
                            suggestions.append(f"Provide valid IP address for server {i+1}")
                    
                    if 'port' in server and server['port'] is not None:
                        try:
                            port = int(server['port'])
                            if port < 1 or port > 65535:
                                errors.append(f"Invalid port for server {i+1}: {port}")
                                suggestions.append(f"Port for server {i+1} must be between 1 and 65535")
                        except (ValueError, TypeError):
                            errors.append(f"Port for server {i+1} must be a valid integer")
                            suggestions.append(f"Provide numeric port for server {i+1}")
        
        return len(errors) == 0, errors, suggestions
    
    @staticmethod
    def validate_rpz_rule_data(rule_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate RPZ rule data and return validation results with helpful messages
        
        Args:
            rule_data: Dictionary containing RPZ rule data
            
        Returns:
            Tuple of (is_valid, errors, suggestions)
        """
        errors = []
        suggestions = []
        
        # Check required fields
        required_fields = ['domain', 'rpz_zone', 'action']
        for field in required_fields:
            if field not in rule_data or not rule_data[field]:
                errors.append(f"Field '{field}' is required")
                if field == 'domain':
                    suggestions.append("Provide domain to block/redirect like 'malicious.com'")
                elif field == 'rpz_zone':
                    suggestions.append("Provide RPZ zone category like 'malware', 'phishing', 'adult'")
                elif field == 'action':
                    suggestions.append("Choose action: 'block', 'redirect', or 'passthru'")
        
        # Validate domain
        if 'domain' in rule_data and rule_data['domain']:
            try:
                DNSValidators.validate_domain_name(rule_data['domain'], 'RPZ domain')
            except ValueError as e:
                errors.append(f"Invalid domain: {str(e)}")
                suggestions.append("Provide valid domain name for RPZ rule")
        
        # Validate action and redirect target
        action = rule_data.get('action')
        if action == 'redirect':
            if 'redirect_target' not in rule_data or not rule_data['redirect_target']:
                errors.append("Redirect target is required for redirect action")
                suggestions.append("Provide redirect target domain or IP address")
            else:
                redirect_target = rule_data['redirect_target']
                # Try to validate as IP first, then as domain
                try:
                    ipaddress.ip_address(redirect_target)
                except ValueError:
                    try:
                        DNSValidators.validate_domain_name(redirect_target, 'redirect target')
                    except ValueError as e:
                        errors.append(f"Invalid redirect target: {str(e)}")
                        suggestions.append("Provide valid IP address or domain name for redirect target")
        
        return len(errors) == 0, errors, suggestions


def create_validation_error_response(
    validation_errors: List[str],
    suggestions: List[str],
    context: str = "input data"
) -> ValidationException:
    """
    Create a validation exception with helpful error messages
    
    Args:
        validation_errors: List of validation error messages
        suggestions: List of suggestions to fix the errors
        context: Context of what was being validated
        
    Returns:
        ValidationException with structured error information
    """
    if len(validation_errors) == 1:
        message = validation_errors[0]
    else:
        message = f"Multiple validation errors found in {context}"
    
    details = {
        "validation_errors": validation_errors,
        "error_count": len(validation_errors)
    }
    
    return ValidationException(
        message=message,
        details=details,
        suggestions=suggestions
    )