"""
Main API routes configuration
"""

from fastapi import APIRouter

from .endpoints import (
    analytics, auth, backup, dashboard, dns_records, events, forwarders, forwarder_templates, health, realtime, reports, rollback, rpz, system, users, websocket, zones
)

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
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Performance"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports & Analytics"])

# WebSocket routes
api_router.include_router(websocket.router, prefix="/websocket", tags=["WebSocket"])

# WebSocket health check
from .endpoints import websocket_health
api_router.include_router(websocket_health.router, prefix="/websocket", tags=["WebSocket Health"])

# WebSocket routes for production use
# Note: WebSocket demo routes removed for production deployment