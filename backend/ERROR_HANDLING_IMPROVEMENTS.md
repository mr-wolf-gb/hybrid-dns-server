# Error Handling Improvements

This document outlines the comprehensive error handling improvements implemented for the Hybrid DNS Server to make error messages clear and helpful.

## Overview

The error handling system has been completely redesigned to provide:
- Clear, contextual error messages
- Actionable suggestions for fixing errors
- Detailed validation information
- Consistent error response format
- Field-specific validation with helpful hints

## Key Components

### 1. Custom Exception Classes (`app/core/exceptions.py`)

- **DNSServerException**: Base exception with message, details, and suggestions
- **ZoneException**: DNS zone operation errors
- **RecordException**: DNS record operation errors
- **ForwarderException**: DNS forwarder operation errors
- **RPZException**: RPZ rule operation errors
- **BindException**: BIND9 service errors
- **ValidationException**: Validation errors with field context

### 2. Error Response Creators

Helper functions to create standardized HTTP exceptions:
- `create_http_exception()`: Standard error response format
- `create_validation_error_response()`: Pydantic validation errors
- `create_zone_error()`: Zone-specific errors
- `create_record_error()`: Record-specific errors
- `create_forwarder_error()`: Forwarder-specific errors
- `create_rpz_error()`: RPZ-specific errors
- `create_bind_error()`: BIND9-specific errors
- `create_not_found_error()`: Resource not found errors
- `create_conflict_error()`: Resource conflict errors

### 3. Error Handlers (`app/core/error_handlers.py`)

Comprehensive exception handlers for:
- Custom DNS server exceptions
- FastAPI HTTP exceptions
- Pydantic validation errors
- SQLAlchemy database errors
- Generic unexpected errors

### 4. Enhanced Schema Validation

#### Zone Validation Improvements
- Clear zone name format requirements
- DNS email format explanation (dots instead of @)
- SOA timing value validation with ranges
- Zone type-specific validation (master/slave/forward)
- IP address validation for master servers and forwarders

#### DNS Record Validation Improvements
- Record type-specific validation messages
- Field requirement explanations (priority for MX, weight/port for SRV)
- Format examples for each record type
- CNAME constraint explanations
- SRV record naming format requirements

#### Forwarder Validation Improvements
- Server configuration validation
- Domain list validation
- IP address and port validation
- Priority value explanations

#### RPZ Rule Validation Improvements
- Action-specific validation
- Redirect target requirements
- Domain format validation

### 5. Validation Helper Functions (`app/core/validation_helpers.py`)

The `DNSValidationHelper` class provides:
- `validate_zone_data()`: Comprehensive zone validation
- `validate_record_data()`: DNS record validation
- `validate_forwarder_data()`: Forwarder configuration validation
- `validate_rpz_rule_data()`: RPZ rule validation

Each function returns:
- Boolean validity status
- List of specific error messages
- List of actionable suggestions

### 6. Error Response Format

All errors now follow a consistent format:

```json
{
  "message": "Main error message",
  "error_code": "ERROR_TYPE",
  "details": {
    "field": "value",
    "additional_context": "info"
  },
  "suggestions": [
    "Specific suggestion to fix the error",
    "Alternative approach",
    "Reference to documentation"
  ],
  "timestamp": "2024-08-18T10:00:00Z",
  "path": "/api/zones",
  "method": "POST"
}
```

## Examples of Improved Error Messages

### Before (Generic)
```json
{
  "detail": "Validation error"
}
```

### After (Helpful)
```json
{
  "message": "Priority is required for MX records. Please provide a numeric priority value (lower numbers have higher priority, typically 10-50)",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "field": "priority",
    "record_type": "MX"
  },
  "suggestions": [
    "Provide priority value (lower numbers = higher priority, typically 10, 20, 30)",
    "Common MX priorities: 10 for primary mail server, 20 for backup"
  ]
}
```

### Zone Creation Error Example
```json
{
  "message": "Invalid administrator email: SOA admin email must use DNS format (dots instead of @)",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "field": "email",
    "provided_value": "admin@example.com"
  },
  "suggestions": [
    "Use DNS format with dots instead of @ (e.g., admin.example.com instead of admin@example.com)",
    "The email admin@example.com should be written as admin.example.com"
  ]
}
```

### SRV Record Error Example
```json
{
  "message": "SRV record name must follow _service._proto.name format (e.g., _http._tcp for HTTP service, _sip._udp for SIP service)",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "field": "name",
    "record_type": "SRV",
    "provided_value": "http.tcp"
  },
  "suggestions": [
    "Use format like '_http._tcp' for HTTP over TCP",
    "Use format like '_sip._udp' for SIP over UDP",
    "Service names must start with underscore (_)"
  ]
}
```

## Benefits

1. **Reduced Support Burden**: Users can fix errors themselves with clear guidance
2. **Improved User Experience**: No more cryptic error messages
3. **Faster Development**: Developers get immediate feedback on what's wrong
4. **Better API Adoption**: Clear errors make the API easier to use
5. **Consistent Experience**: All errors follow the same helpful format

## Integration

The error handling is automatically integrated into:
- FastAPI application startup
- All API endpoints
- Schema validation
- Database operations
- Service layer operations

## Testing

A comprehensive test suite (`test_error_handling.py`) validates:
- Schema validation error messages
- Helper function responses
- Error response formatting
- Suggestion generation
- Context-specific error handling

## Future Enhancements

- Internationalization support for error messages
- Error analytics and monitoring
- User-specific error message customization
- Integration with help documentation
- Error recovery suggestions based on user context