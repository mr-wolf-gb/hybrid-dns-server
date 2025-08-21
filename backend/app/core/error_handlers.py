"""
Error handling middleware and exception handlers for the Hybrid DNS Server
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .exceptions import (
    DNSServerException,
    create_validation_error_response,
    create_http_exception,
    create_conflict_error,
    create_service_unavailable_error
)

logger = logging.getLogger(__name__)


async def dns_server_exception_handler(request: Request, exc: DNSServerException) -> JSONResponse:
    """Handle custom DNS server exceptions"""
    logger.error(f"DNS Server Exception: {exc.message}", extra={
        "details": exc.details,
        "suggestions": exc.suggestions,
        "path": request.url.path,
        "method": request.method
    })
    
    error_response = {
        "message": exc.message,
        "error_code": type(exc).__name__.upper(),
        "details": exc.details,
        "suggestions": exc.suggestions,
        "timestamp": datetime.utcnow().isoformat(),
        "path": request.url.path,
        "method": request.method
    }
    
    # Determine appropriate HTTP status code based on exception type
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if "not found" in exc.message.lower():
        status_code = status.HTTP_404_NOT_FOUND
    elif "already exists" in exc.message.lower() or "duplicate" in exc.message.lower():
        status_code = status.HTTP_409_CONFLICT
    elif "permission" in exc.message.lower() or "unauthorized" in exc.message.lower():
        status_code = status.HTTP_403_FORBIDDEN
    elif "invalid" in exc.message.lower() or "validation" in exc.message.lower():
        status_code = status.HTTP_400_BAD_REQUEST
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions with enhanced error information"""
    
    # If the detail is already a dict (from our custom exceptions), use it
    if isinstance(exc.detail, dict):
        error_response = exc.detail.copy()
        error_response["timestamp"] = datetime.utcnow().isoformat()
        error_response["path"] = request.url.path
        error_response["method"] = request.method
    else:
        # Convert simple string detail to structured format
        error_response = {
            "message": str(exc.detail),
            "error_code": f"HTTP_{exc.status_code}",
            "details": {},
            "suggestions": _get_default_suggestions_for_status(exc.status_code),
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
            "method": request.method
        }
    
    logger.warning(f"HTTP Exception {exc.status_code}: {error_response['message']}", extra={
        "status_code": exc.status_code,
        "path": request.url.path,
        "method": request.method,
        "details": error_response.get("details", {})
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI request validation errors"""
    
    # Determine context from the request path
    context = _get_context_from_path(request.url.path)
    
    # Convert to our custom validation error format
    try:
        # Create a Pydantic ValidationError from the FastAPI RequestValidationError
        validation_error = ValidationError.from_exception_data(
            title="RequestValidationError",
            line_errors=exc.errors()
        )
        http_exc = create_validation_error_response(validation_error, context)
        return await http_exception_handler(request, http_exc)
    except Exception:
        # Fallback to basic error handling (avoid noisy stacktraces)
        return await _handle_validation_fallback(request, exc, context)


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database exceptions"""
    
    logger.error(f"Database error: {str(exc)}", extra={
        "path": request.url.path,
        "method": request.method,
        "exception_type": type(exc).__name__
    })
    
    # Handle specific SQLAlchemy exceptions
    if isinstance(exc, IntegrityError):
        # Extract meaningful information from integrity errors
        error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
        
        if "unique constraint" in error_msg.lower() or "duplicate" in error_msg.lower():
            message = "A resource with this information already exists"
            suggestions = [
                "Check if a similar resource already exists",
                "Use a different name or identifier",
                "Update the existing resource instead of creating a new one"
            ]
            error_code = "DUPLICATE_RESOURCE"
            status_code = status.HTTP_409_CONFLICT
        elif "foreign key constraint" in error_msg.lower():
            message = "Cannot perform this operation due to related data constraints"
            suggestions = [
                "Ensure all referenced resources exist",
                "Remove or update related resources first",
                "Check that the referenced IDs are correct"
            ]
            error_code = "FOREIGN_KEY_CONSTRAINT"
            status_code = status.HTTP_400_BAD_REQUEST
        elif "not null constraint" in error_msg.lower():
            message = "Required information is missing"
            suggestions = [
                "Provide all required fields",
                "Check that no required values are null or empty"
            ]
            error_code = "MISSING_REQUIRED_DATA"
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            message = "Database constraint violation"
            suggestions = [
                "Check that all data meets the required constraints",
                "Verify that related resources exist"
            ]
            error_code = "CONSTRAINT_VIOLATION"
            status_code = status.HTTP_400_BAD_REQUEST
    else:
        # Generic database error
        message = "A database error occurred"
        suggestions = [
            "Try the operation again",
            "Check that the database is available",
            "Contact support if the problem persists"
        ]
        error_code = "DATABASE_ERROR"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    error_response = {
        "message": message,
        "error_code": error_code,
        "details": {"database_error": str(exc)},
        "suggestions": suggestions,
        "timestamp": datetime.utcnow().isoformat(),
        "path": request.url.path,
        "method": request.method
    }
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    
    logger.error(f"Unexpected error: {str(exc)}", extra={
        "path": request.url.path,
        "method": request.method,
        "exception_type": type(exc).__name__,
        "traceback": traceback.format_exc()
    })
    
    # Don't expose internal error details in production
    error_response = {
        "message": "An unexpected error occurred",
        "error_code": "INTERNAL_SERVER_ERROR",
        "details": {"error_type": type(exc).__name__},
        "suggestions": [
            "Try the operation again",
            "Check that all input data is valid",
            "Contact support if the problem persists"
        ],
        "timestamp": datetime.utcnow().isoformat(),
        "path": request.url.path,
        "method": request.method
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


def _get_context_from_path(path: str) -> str:
    """Extract context from request path for better error messages"""
    if "/zones" in path:
        if "/records" in path:
            return "DNS record"
        return "DNS zone"
    elif "/forwarders" in path:
        return "DNS forwarder"
    elif "/rpz" in path:
        return "RPZ rule"
    elif "/auth" in path:
        return "authentication"
    elif "/system" in path:
        return "system configuration"
    else:
        return "request"


def _get_default_suggestions_for_status(status_code: int) -> list[str]:
    """Get default suggestions based on HTTP status code"""
    suggestions_map = {
        400: [
            "Check that all required fields are provided",
            "Verify that all data is in the correct format",
            "Review the API documentation for correct usage"
        ],
        401: [
            "Ensure you are logged in",
            "Check that your authentication token is valid",
            "Try logging in again"
        ],
        403: [
            "Verify that you have permission for this operation",
            "Contact your administrator for access",
            "Check that you are using the correct account"
        ],
        404: [
            "Verify that the resource exists",
            "Check that the URL is correct",
            "Ensure you have permission to access this resource"
        ],
        409: [
            "Check for existing resources with the same name",
            "Use a different identifier",
            "Update the existing resource instead"
        ],
        422: [
            "Check that all data is valid",
            "Verify required fields are provided",
            "Review field format requirements"
        ],
        429: [
            "Wait before making another request",
            "Reduce the frequency of requests",
            "Consider implementing request batching"
        ],
        500: [
            "Try the operation again",
            "Check that all services are running",
            "Contact support if the problem persists"
        ],
        503: [
            "Wait a moment and try again",
            "Check service status",
            "Contact support if the service remains unavailable"
        ]
    }
    
    return suggestions_map.get(status_code, [
        "Review your request and try again",
        "Check the API documentation",
        "Contact support if you need assistance"
    ])


async def _handle_validation_fallback(
    request: Request, 
    exc: RequestValidationError, 
    context: str
) -> JSONResponse:
    """Fallback validation error handler"""
    
    errors = []
    suggestions = []
    
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        error_msg = error["msg"]
        
        errors.append({
            "field": field_path,
            "message": error_msg,
            "type": error["type"],
            "input": error.get("input")
        })
        
        # Add basic suggestions
        if error["type"] == "missing":
            suggestions.append(f"Please provide a value for '{field_path}'")
        elif "type" in error["type"]:
            suggestions.append(f"Please check the data type for '{field_path}'")
    
    # Remove duplicates
    suggestions = list(dict.fromkeys(suggestions))
    
    error_response = {
        "message": f"Validation failed for {context}",
        "error_code": "VALIDATION_ERROR",
        "details": {"validation_errors": errors},
        "suggestions": suggestions or [
            "Check that all required fields are provided",
            "Verify that all data is in the correct format"
        ],
        "timestamp": datetime.utcnow().isoformat(),
        "path": request.url.path,
        "method": request.method
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )