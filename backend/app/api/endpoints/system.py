"""
System administration endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...services.bind_service import BindService

router = APIRouter()

@router.get("/status")
async def get_system_status(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive system status"""
    try:
        bind_service = BindService(db)
        
        # Get BIND9 service status
        bind_status = await bind_service.get_service_status()
        
        # Get basic system information
        system_info = {
            "bind9": bind_status,
            "database": {
                "connected": db is not None,
                "status": "connected" if db else "disconnected"
            }
        }
        
        return system_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

@router.get("/validate")
async def validate_system_configuration(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Perform comprehensive system configuration validation"""
    try:
        bind_service = BindService(db)
        
        # Perform detailed configuration validation
        validation_result = await bind_service.validate_configuration_detailed()
        
        return validation_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration validation failed: {str(e)}")

@router.get("/validate/quick")
async def quick_validate_configuration(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Perform quick configuration validation (boolean result)"""
    try:
        bind_service = BindService(db)
        
        # Perform basic configuration validation
        is_valid = await bind_service.validate_configuration()
        
        return {
            "valid": is_valid,
            "message": "Configuration is valid" if is_valid else "Configuration has errors"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration validation failed: {str(e)}")

@router.post("/validate/zones")
async def validate_zones_configuration(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate all zone configurations"""
    try:
        bind_service = BindService(db)
        
        # Validate all zones
        zones_validation = await bind_service._validate_all_zone_files()
        
        return zones_validation
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Zone validation failed: {str(e)}")

@router.post("/validate/forwarders")
async def validate_forwarders_configuration(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate forwarder configurations"""
    try:
        bind_service = BindService(db)
        
        # Validate forwarders
        forwarders_validation = await bind_service._validate_forwarders_configuration()
        
        return forwarders_validation
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forwarder validation failed: {str(e)}")

@router.post("/validate/rpz")
async def validate_rpz_configuration(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate RPZ configurations"""
    try:
        bind_service = BindService(db)
        
        # Validate RPZ configuration
        rpz_validation = await bind_service._validate_rpz_configuration()
        
        return rpz_validation
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RPZ validation failed: {str(e)}")

@router.post("/validate/permissions")
async def validate_file_permissions(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate file permissions and ownership"""
    try:
        bind_service = BindService(db)
        
        # Validate file permissions
        permissions_validation = await bind_service._validate_file_permissions()
        
        return permissions_validation
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Permissions validation failed: {str(e)}")

@router.get("/health")
async def get_system_health(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get overall system health status"""
    try:
        bind_service = BindService(db)
        
        # Get service status
        bind_status = await bind_service.get_service_status()
        
        # Perform quick validation
        config_valid = await bind_service.validate_configuration()
        
        # Determine overall health
        overall_health = "healthy"
        issues = []
        
        if bind_status["status"] != "active":
            overall_health = "unhealthy"
            issues.append("BIND9 service is not running")
        
        if not config_valid:
            overall_health = "degraded" if overall_health == "healthy" else "unhealthy"
            issues.append("Configuration validation failed")
        
        if not bind_status["config_valid"]:
            overall_health = "degraded" if overall_health == "healthy" else "unhealthy"
            issues.append("BIND9 configuration has syntax errors")
        
        return {
            "status": overall_health,
            "bind9_running": bind_status["status"] == "active",
            "config_valid": config_valid,
            "issues": issues,
            "details": bind_status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")