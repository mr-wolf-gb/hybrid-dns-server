"""
Logging configuration for Hybrid DNS Server API
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from .config import get_settings


def setup_logging():
    """Configure application logging"""
    
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    if settings.LOG_FILE:
        log_file_path = Path(settings.LOG_FILE)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if settings.LOG_FILE:
        # Use rotating file handler to manage log file size
        file_handler = logging.handlers.RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    
    # FastAPI/Uvicorn loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    
    # SQLAlchemy logger (only show warnings and above)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    
    # HTTP client loggers (reduce noise)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Application-specific loggers
    logging.getLogger("app.services.bind_service").setLevel(logging.INFO)
    logging.getLogger("app.services.monitoring_service").setLevel(logging.INFO)
    logging.getLogger("app.services.health_service").setLevel(logging.INFO)
    
    # Security-related events should always be logged
    security_logger = logging.getLogger("app.security")
    security_logger.setLevel(logging.INFO)
    
    # DNS query logger (separate file if needed)
    dns_logger = logging.getLogger("app.dns.queries")
    dns_logger.setLevel(logging.INFO)
    
    if settings.DEBUG:
        # In debug mode, log more details
        root_logger.setLevel(logging.DEBUG)
        logging.getLogger("app").setLevel(logging.DEBUG)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)


# Specific loggers for different components
def get_security_logger() -> logging.Logger:
    """Get security events logger"""
    return logging.getLogger("app.security")


def get_dns_logger() -> logging.Logger:
    """Get DNS queries logger"""
    return logging.getLogger("app.dns.queries")


def get_bind_logger() -> logging.Logger:
    """Get BIND service logger"""
    return logging.getLogger("app.services.bind_service")


def get_monitoring_logger() -> logging.Logger:
    """Get monitoring service logger"""
    return logging.getLogger("app.services.monitoring_service")


def get_health_logger() -> logging.Logger:
    """Get health service logger"""
    return logging.getLogger("app.services.health_service")