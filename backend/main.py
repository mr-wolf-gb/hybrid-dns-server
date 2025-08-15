#!/usr/bin/env python3
"""
Hybrid DNS Server - FastAPI Backend
Production-ready DNS management API with authentication and monitoring
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.database import init_database
from app.core.logging_config import setup_logging
from app.services.bind_service import BindService
from app.services.monitoring_service import MonitoringService
from app.services.health_service import HealthService

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Hybrid DNS Server API...")
    
    # Initialize database
    await init_database()
    
    # Initialize services
    bind_service = BindService()
    monitoring_service = MonitoringService()
    health_service = HealthService()
    
    # Start background services
    asyncio.create_task(monitoring_service.start())
    asyncio.create_task(health_service.start())
    
    logger.info("API server started successfully")
    
    yield
    
    # Shutdown cleanup
    logger.info("Shutting down API server...")
    await monitoring_service.stop()
    await health_service.stop()
    logger.info("API server stopped")


# Create FastAPI application
def create_app():
    settings = get_settings()
    return FastAPI(
        title="Hybrid DNS Server API",
        description="Production-ready DNS server management API with BIND9 backend",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )

app = create_app()

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Configure CORS and middleware
def setup_middleware():
    settings = get_settings()
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Add trusted host middleware for production
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware, 
            allowed_hosts=settings.ALLOWED_HOSTS
        )

setup_middleware()

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Serve static files for web UI (if built)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - basic API info"""
    settings = get_settings()
    return {
        "name": "Hybrid DNS Server API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled in production"
    }


@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint for load balancers"""
    return {
        "status": "healthy",
        "timestamp": "2024-08-15T10:00:00Z"
    }


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"Path {request.url.path} not found",
            "status_code": 404
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status_code": 500
        }
    )


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        access_log=True,
        server_header=False,
        date_header=False
    )