#!/usr/bin/env python3
"""
Hybrid DNS Server - FastAPI Backend
Production-ready DNS management API with authentication and monitoring
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends
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
from app.core.error_setup import setup_error_handlers, create_startup_message
from app.services.bind_service import BindService
from app.services.monitoring_service import MonitoringService
from app.services.background_tasks import get_background_task_service
from app.services.event_service import get_event_service
from app.websocket.manager import get_websocket_manager
from app.websocket.unified_manager import get_unified_websocket_manager

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
    background_service = get_background_task_service()
    event_service = get_event_service()
    websocket_manager = get_websocket_manager()
    unified_websocket_manager = get_unified_websocket_manager()
    
    # Regenerate BIND9 configurations from database on startup
    try:
        from app.core.database import get_database_session
        db = next(get_database_session())
        bind_service_with_db = BindService(db)
        await bind_service_with_db.regenerate_all_configurations()
        logger.info("BIND9 configurations regenerated from database on startup")
    except Exception as e:
        logger.error(f"Failed to regenerate BIND9 configurations on startup: {e}")
    
    # Start background services
    asyncio.create_task(monitoring_service.start())
    await background_service.start()
    await event_service.start()
    # WebSocket manager starts automatically when first connection is made
    
    logger.info("API server started successfully")
    
    yield
    
    # Shutdown cleanup
    logger.info("Shutting down API server...")
    await monitoring_service.stop()
    await background_service.stop()
    await event_service.stop()
    # Stop WebSocket managers
    websocket_manager = get_websocket_manager()
    await websocket_manager.stop_broadcasting()
    
    unified_websocket_manager = get_unified_websocket_manager()
    await unified_websocket_manager._stop_background_services()
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

# Setup comprehensive error handling
setup_error_handlers(app)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Configure CORS and middleware
def setup_middleware():
    settings = get_settings()
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Add trusted host middleware for production
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware, 
            allowed_hosts=settings.allowed_hosts_list
        )

setup_middleware()

# Include API routes
app.include_router(api_router, prefix="/api")

# Serve static files for web UI (if built)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - basic API info with error handling information"""
    settings = get_settings()
    startup_info = create_startup_message()
    startup_info.update({
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled in production"
    })
    return startup_info


@app.websocket("/ws/{connection_type}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, connection_type: str, user_id: str):
    """WebSocket endpoint for real-time updates"""
    websocket_manager = get_websocket_manager()
    
    # Validate connection type
    valid_types = ["health", "dns_management", "security", "system", "admin"]
    if connection_type not in valid_types:
        await websocket.close(code=4000, reason="Invalid connection type")
        return
    
    try:
        # For now, we'll accept any user_id - in production you'd validate the user
        await websocket_manager.connect(websocket, user_id, connection_type)
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                
                # Handle different message types
                try:
                    message = json.loads(data)
                    await handle_websocket_message(websocket, message, websocket_manager)
                except json.JSONDecodeError:
                    # Handle simple text messages
                    if data == "ping":
                        await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error for user {user_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error for user {user_id}: {e}")
    finally:
        websocket_manager.disconnect(websocket)


async def handle_websocket_message(websocket: WebSocket, message: dict, websocket_manager):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "ping":
        await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()}))
    
    elif message_type == "subscribe":
        # Subscribe to specific event types
        event_types = message.get("events", [])
        await websocket_manager.subscribe_to_events(websocket, event_types)
    
    elif message_type == "get_stats":
        # Send connection statistics
        stats = websocket_manager.get_connection_stats()
        await websocket.send_text(json.dumps({
            "type": "stats",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    else:
        # Unknown message type
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {"message": f"Unknown message type: {message_type}"},
            "timestamp": datetime.utcnow().isoformat()
        }))


# Legacy health endpoint for backward compatibility
@app.websocket("/ws/health/{user_id}")
async def websocket_health_endpoint(websocket: WebSocket, user_id: str):
    """Legacy WebSocket endpoint for health monitoring (backward compatibility)"""
    await websocket_endpoint(websocket, "health", user_id)


@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint for load balancers"""
    return {
        "status": "healthy",
        "timestamp": "2024-08-15T10:00:00Z"
    }


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler with helpful suggestions"""
    from datetime import datetime
    
    return JSONResponse(
        status_code=404,
        content={
            "message": f"The requested path '{request.url.path}' was not found",
            "error_code": "NOT_FOUND",
            "details": {
                "path": request.url.path,
                "method": request.method
            },
            "suggestions": [
                "Check that the URL is correct",
                "Verify the API endpoint exists in the documentation",
                "Ensure you're using the correct HTTP method",
                "Visit /docs for API documentation (if available)"
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
            "method": request.method
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler with helpful information"""
    from datetime import datetime
    
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "message": "An unexpected internal server error occurred",
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": {
                "error_type": type(exc).__name__
            },
            "suggestions": [
                "Try the request again in a moment",
                "Check that all required fields are provided",
                "Verify that the server is running properly",
                "Contact support if the problem persists"
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
            "method": request.method
        }
    )


if __name__ == "__main__":
    # Development server
    settings = get_settings()
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