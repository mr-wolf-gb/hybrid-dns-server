"""
Main API routes configuration
"""

from fastapi import APIRouter

from .endpoints import (
    auth, backup, dashboard, dns_records, events, forwarders, forwarder_templates, health, realtime, reports, rollback, rpz, system, users, websocket, zones
)
# from .routes import analytics  # Temporarily disabled due to circular import

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(zones.router, prefix="/zones", tags=["DNS Zones"])
api_router.include_router(dns_records.router, prefix="/records", tags=["DNS Records"])
api_router.include_router(forwarders.router, prefix="/forwarders", tags=["Forwarders"])
api_router.include_router(forwarder_templates.router, prefix="/forwarder-templates", tags=["Forwarder Templates"])
api_router.include_router(rpz.router, prefix="/rpz", tags=["Response Policy Zones"])
api_router.include_router(health.router, prefix="/health", tags=["Health & Monitoring"])
api_router.include_router(realtime.router, prefix="/realtime", tags=["Real-time Updates"])
api_router.include_router(backup.router, prefix="/backup", tags=["Configuration Backup"])
api_router.include_router(rollback.router, prefix="/rollback", tags=["Configuration Rollback"])
api_router.include_router(system.router, prefix="/system", tags=["System Administration"])
api_router.include_router(events.router, prefix="/events", tags=["Event Broadcasting"])
# api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Performance"])  # Temporarily disabled
api_router.include_router(reports.router, prefix="/reports", tags=["Reports & Analytics"])

# WebSocket routes
api_router.include_router(websocket.router, prefix="/websocket", tags=["WebSocket"])

# WebSocket demo routes (for development and testing)
# from .routes import websocket_demo  # Temporarily disabled due to circular import
# api_router.include_router(websocket_demo.router)  # Temporarily disabled