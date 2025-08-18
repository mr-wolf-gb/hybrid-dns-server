"""
Setup error handling for the FastAPI application
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from .exceptions import DNSServerException
from .error_handlers import (
    dns_server_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    generic_exception_handler
)


def setup_error_handlers(app: FastAPI) -> None:
    """
    Setup all error handlers for the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    
    # Custom DNS server exceptions
    app.add_exception_handler(DNSServerException, dns_server_exception_handler)
    
    # FastAPI validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Pydantic validation errors
    app.add_exception_handler(ValidationError, validation_exception_handler)
    
    # Database errors
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    
    # Generic exception handler (catch-all)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    # Note: HTTPException handler is automatically handled by FastAPI,
    # but we can override it if needed
    # app.add_exception_handler(HTTPException, http_exception_handler)


def create_startup_message() -> dict:
    """Create a startup message with error handling information"""
    return {
        "message": "Hybrid DNS Server API",
        "error_handling": {
            "structured_errors": True,
            "helpful_messages": True,
            "suggestions_included": True,
            "validation_details": True
        },
        "features": [
            "Clear error messages with context",
            "Actionable suggestions for fixing errors",
            "Detailed validation error information",
            "Consistent error response format"
        ]
    }