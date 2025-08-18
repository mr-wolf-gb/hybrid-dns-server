"""
Custom exceptions and error handling for the Hybrid DNS Server
"""

from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, status
from pydantic import ValidationError


class DNSServerException(Exception):
    """Base exception for DNS server operations"""
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        self.message = message
        self.details = details or {}
        self.suggestions = suggestions or []
        super().__init__(self.message)


class ZoneException(DNSServerException):
    """Exception for DNS zone operations"""
    pass


class RecordException(DNSServerException):
    """Exception for DNS record operations"""
    pass


class ForwarderException(DNSServerException):
    """Exception for DNS forwarder operations"""
    pass


class RPZException(DNSServerException):
    """Exception for RPZ operations"""
    pass


class BindException(DNSServerException):
    """Exception for BIND9 operations"""
    pass


class ValidationException(DNSServerException):
    """Exception for validation errors with helpful context"""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        self.field = field
        self.value = value
        super().__init__(message, details, suggestions)


class ConfigurationException(DNSServerException):
    """Exception for configuration errors"""
    pass


class ServiceException(DNSServerException):
    """Exception for service-related errors"""
    pass


def create_http_exception(
    status_code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    suggestions: Optional[List[str]] = None,
    error_code: Optional[str] = None
) -> HTTPException:
    """
    Create a standardized HTTP exception with helpful error information
    
    Args:
        status_code: HTTP status code
        message: Main error message
        details: Additional error details
        suggestions: List of suggestions to fix the error
        error_code: Internal error code for debugging
    
    Returns:
        HTTPException with structured error response
    """
    error_detail = {
        "message": message,
        "error_code": error_code,
        "details": details or {},
        "suggestions": suggestions or [],
        "timestamp": None  # Will be set by middleware
    }
    
    return HTTPException(status_code=status_code, detail=error_detail)


def create_validation_error_response(
    validation_error: ValidationError,
    context: Optional[str] = None
) -> HTTPException:
    """
    Convert Pydantic ValidationError to helpful HTTP exception
    
    Args:
        validation_error: Pydantic validation error
        context: Additional context about what was being validated
    
    Returns:
        HTTPException with detailed validation error information
    """
    errors = []
    suggestions = []
    
    for error in validation_error.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        error_msg = error["msg"]
        error_type = error["type"]
        
        # Create user-friendly error messages
        if error_type == "value_error":
            # Custom validation errors are already user-friendly
            friendly_msg = error_msg
        elif error_type == "missing":
            friendly_msg = f"The field '{field_path}' is required but was not provided"
            suggestions.append(f"Please provide a value for '{field_path}'")
        elif error_type == "type_error":
            expected_type = error.get("ctx", {}).get("expected_type", "correct type")
            friendly_msg = f"The field '{field_path}' has an invalid type. Expected {expected_type}"
            suggestions.append(f"Please provide a valid {expected_type} for '{field_path}'")
        elif error_type == "string_too_short":
            min_length = error.get("ctx", {}).get("limit_value", "minimum")
            friendly_msg = f"The field '{field_path}' is too short. Minimum length is {min_length}"
            suggestions.append(f"Please provide at least {min_length} characters for '{field_path}'")
        elif error_type == "string_too_long":
            max_length = error.get("ctx", {}).get("limit_value", "maximum")
            friendly_msg = f"The field '{field_path}' is too long. Maximum length is {max_length}"
            suggestions.append(f"Please limit '{field_path}' to {max_length} characters or less")
        elif error_type == "value_error.number.not_ge":
            min_value = error.get("ctx", {}).get("limit_value", "minimum")
            friendly_msg = f"The field '{field_path}' must be greater than or equal to {min_value}"
            suggestions.append(f"Please provide a value >= {min_value} for '{field_path}'")
        elif error_type == "value_error.number.not_le":
            max_value = error.get("ctx", {}).get("limit_value", "maximum")
            friendly_msg = f"The field '{field_path}' must be less than or equal to {max_value}"
            suggestions.append(f"Please provide a value <= {max_value} for '{field_path}'")
        elif error_type == "value_error.url":
            friendly_msg = f"The field '{field_path}' must be a valid URL"
            suggestions.append(f"Please provide a valid URL starting with http:// or https:// for '{field_path}'")
        elif error_type == "value_error.email":
            friendly_msg = f"The field '{field_path}' must be a valid email address"
            suggestions.append(f"Please provide a valid email address for '{field_path}'")
        else:
            # Fallback for other error types
            friendly_msg = f"The field '{field_path}': {error_msg}"
        
        errors.append({
            "field": field_path,
            "message": friendly_msg,
            "type": error_type,
            "input": error.get("input")
        })
    
    # Add context-specific suggestions
    if context:
        if "zone" in context.lower():
            suggestions.extend([
                "Ensure zone names follow DNS naming conventions (e.g., example.com)",
                "Check that email addresses use DNS format (admin.example.com instead of admin@example.com)",
                "Verify that numeric values are within valid ranges"
            ])
        elif "record" in context.lower():
            suggestions.extend([
                "Verify that record names and values match the record type requirements",
                "Check that IP addresses are in valid format",
                "Ensure domain names follow DNS naming conventions"
            ])
        elif "forwarder" in context.lower():
            suggestions.extend([
                "Verify that server IP addresses are valid",
                "Check that domain names are properly formatted",
                "Ensure port numbers are between 1 and 65535"
            ])
        elif "rpz" in context.lower():
            suggestions.extend([
                "Verify that domain names are properly formatted",
                "Check that redirect targets are valid when using redirect action",
                "Ensure RPZ zone names are valid"
            ])
    
    # Remove duplicate suggestions
    suggestions = list(dict.fromkeys(suggestions))
    
    main_message = f"Validation failed for {context or 'input data'}"
    if len(errors) == 1:
        main_message = errors[0]["message"]
    
    return create_http_exception(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message=main_message,
        details={"validation_errors": errors},
        suggestions=suggestions,
        error_code="VALIDATION_ERROR"
    )


def create_zone_error(
    message: str,
    zone_name: Optional[str] = None,
    operation: Optional[str] = None,
    suggestions: Optional[List[str]] = None
) -> HTTPException:
    """Create zone-specific error with helpful context"""
    details = {}
    if zone_name:
        details["zone_name"] = zone_name
    if operation:
        details["operation"] = operation
    
    default_suggestions = [
        "Check that the zone name is valid and follows DNS naming conventions",
        "Verify that you have permission to perform this operation",
        "Ensure the zone configuration is correct"
    ]
    
    return create_http_exception(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message,
        details=details,
        suggestions=suggestions or default_suggestions,
        error_code="ZONE_ERROR"
    )


def create_record_error(
    message: str,
    record_name: Optional[str] = None,
    record_type: Optional[str] = None,
    zone_name: Optional[str] = None,
    suggestions: Optional[List[str]] = None
) -> HTTPException:
    """Create record-specific error with helpful context"""
    details = {}
    if record_name:
        details["record_name"] = record_name
    if record_type:
        details["record_type"] = record_type
    if zone_name:
        details["zone_name"] = zone_name
    
    default_suggestions = [
        "Verify that the record name and value are valid for the record type",
        "Check that the record doesn't conflict with existing records",
        "Ensure the zone exists and is active"
    ]
    
    # Add record-type specific suggestions
    if record_type:
        type_suggestions = {
            "A": ["Ensure the value is a valid IPv4 address (e.g., 192.168.1.1)"],
            "AAAA": ["Ensure the value is a valid IPv6 address (e.g., 2001:db8::1)"],
            "CNAME": ["Ensure the value is a valid domain name", "CNAME records cannot coexist with other record types for the same name"],
            "MX": ["Ensure the value is a valid domain name", "Priority must be specified for MX records"],
            "TXT": ["TXT record values should be enclosed in quotes if they contain spaces"],
            "SRV": ["SRV records require priority, weight, port, and target values"],
            "PTR": ["PTR records are used for reverse DNS lookups"]
        }
        if record_type.upper() in type_suggestions:
            default_suggestions.extend(type_suggestions[record_type.upper()])
    
    return create_http_exception(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message,
        details=details,
        suggestions=suggestions or default_suggestions,
        error_code="RECORD_ERROR"
    )


def create_forwarder_error(
    message: str,
    forwarder_name: Optional[str] = None,
    server_ip: Optional[str] = None,
    suggestions: Optional[List[str]] = None
) -> HTTPException:
    """Create forwarder-specific error with helpful context"""
    details = {}
    if forwarder_name:
        details["forwarder_name"] = forwarder_name
    if server_ip:
        details["server_ip"] = server_ip
    
    default_suggestions = [
        "Verify that server IP addresses are reachable",
        "Check that DNS servers are responding on the specified ports",
        "Ensure domain names are properly formatted",
        "Test connectivity to the forwarder servers"
    ]
    
    return create_http_exception(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message,
        details=details,
        suggestions=suggestions or default_suggestions,
        error_code="FORWARDER_ERROR"
    )


def create_rpz_error(
    message: str,
    domain: Optional[str] = None,
    rpz_zone: Optional[str] = None,
    suggestions: Optional[List[str]] = None
) -> HTTPException:
    """Create RPZ-specific error with helpful context"""
    details = {}
    if domain:
        details["domain"] = domain
    if rpz_zone:
        details["rpz_zone"] = rpz_zone
    
    default_suggestions = [
        "Verify that the domain name is properly formatted",
        "Check that the RPZ action is valid (block, redirect, or passthru)",
        "Ensure redirect targets are provided when using redirect action",
        "Verify that the RPZ zone exists and is active"
    ]
    
    return create_http_exception(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message,
        details=details,
        suggestions=suggestions or default_suggestions,
        error_code="RPZ_ERROR"
    )


def create_bind_error(
    message: str,
    config_file: Optional[str] = None,
    suggestions: Optional[List[str]] = None
) -> HTTPException:
    """Create BIND9-specific error with helpful context"""
    details = {}
    if config_file:
        details["config_file"] = config_file
    
    default_suggestions = [
        "Check BIND9 configuration syntax",
        "Verify that BIND9 service is running",
        "Ensure configuration files have correct permissions",
        "Check BIND9 logs for detailed error information"
    ]
    
    return create_http_exception(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        details=details,
        suggestions=suggestions or default_suggestions,
        error_code="BIND_ERROR"
    )


def create_not_found_error(
    resource_type: str,
    resource_id: Optional[Union[int, str]] = None,
    suggestions: Optional[List[str]] = None
) -> HTTPException:
    """Create not found error with helpful context"""
    if resource_id:
        message = f"{resource_type.title()} with ID '{resource_id}' was not found"
    else:
        message = f"{resource_type.title()} was not found"
    
    default_suggestions = [
        f"Verify that the {resource_type} exists",
        f"Check that you have permission to access this {resource_type}",
        f"Ensure the {resource_type} ID is correct"
    ]
    
    details = {"resource_type": resource_type}
    if resource_id:
        details["resource_id"] = resource_id
    
    return create_http_exception(
        status_code=status.HTTP_404_NOT_FOUND,
        message=message,
        details=details,
        suggestions=suggestions or default_suggestions,
        error_code="NOT_FOUND"
    )


def create_conflict_error(
    message: str,
    resource_type: Optional[str] = None,
    conflicting_value: Optional[str] = None,
    suggestions: Optional[List[str]] = None
) -> HTTPException:
    """Create conflict error with helpful context"""
    details = {}
    if resource_type:
        details["resource_type"] = resource_type
    if conflicting_value:
        details["conflicting_value"] = conflicting_value
    
    default_suggestions = [
        "Choose a different name or value that doesn't conflict",
        "Check existing resources to avoid duplicates",
        "Update the existing resource instead of creating a new one"
    ]
    
    return create_http_exception(
        status_code=status.HTTP_409_CONFLICT,
        message=message,
        details=details,
        suggestions=suggestions or default_suggestions,
        error_code="CONFLICT"
    )


def create_service_unavailable_error(
    service_name: str,
    suggestions: Optional[List[str]] = None
) -> HTTPException:
    """Create service unavailable error with helpful context"""
    message = f"The {service_name} service is currently unavailable"
    
    default_suggestions = [
        f"Check that the {service_name} service is running",
        "Wait a moment and try again",
        "Contact your system administrator if the problem persists"
    ]
    
    return create_http_exception(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        message=message,
        details={"service_name": service_name},
        suggestions=suggestions or default_suggestions,
        error_code="SERVICE_UNAVAILABLE"
    )


def create_permission_error(
    operation: str,
    resource_type: Optional[str] = None,
    suggestions: Optional[List[str]] = None
) -> HTTPException:
    """Create permission error with helpful context"""
    if resource_type:
        message = f"You don't have permission to {operation} {resource_type}"
    else:
        message = f"You don't have permission to {operation}"
    
    default_suggestions = [
        "Check that you are logged in with the correct account",
        "Verify that your account has the necessary permissions",
        "Contact your administrator to request access"
    ]
    
    details = {"operation": operation}
    if resource_type:
        details["resource_type"] = resource_type
    
    return create_http_exception(
        status_code=status.HTTP_403_FORBIDDEN,
        message=message,
        details=details,
        suggestions=suggestions or default_suggestions,
        error_code="PERMISSION_DENIED"
    )


def create_rate_limit_error(
    limit: int,
    window: int,
    suggestions: Optional[List[str]] = None
) -> HTTPException:
    """Create rate limit error with helpful context"""
    message = f"Rate limit exceeded: {limit} requests per {window} seconds"
    
    default_suggestions = [
        f"Wait {window} seconds before making another request",
        "Reduce the frequency of your requests",
        "Consider implementing request batching if available"
    ]
    
    return create_http_exception(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        message=message,
        details={"limit": limit, "window": window},
        suggestions=suggestions or default_suggestions,
        error_code="RATE_LIMIT_EXCEEDED"
    )