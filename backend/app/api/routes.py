"""
Main API routes configuration
"""

from fastapi import APIRouter

from .endpoints import (
    auth, backup, dashboard, dns_records, forwarders, health, rollback, rpz, system, users, zones
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
api_router.include_router(rpz.router, prefix="/rpz", tags=["Response Policy Zones"])
api_router.include_router(health.router, prefix="/health", tags=["Health & Monitoring"])
api_router.include_router(backup.router, prefix="/backup", tags=["Configuration Backup"])
api_router.include_router(rollback.router, prefix="/rollback", tags=["Configuration Rollback"])
api_router.include_router(system.router, prefix="/system", tags=["System Administration"])