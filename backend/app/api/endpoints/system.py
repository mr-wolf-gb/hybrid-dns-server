"""
System administration endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
import asyncio
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...services.bind_service import BindService
from ...services.acl_service import ACLService
from ...schemas.system import (
    ACLCreate, ACLUpdate, ACL, ACLSummary, ACLEntryCreate, ACLEntryUpdate, 
    ACLEntry, BulkACLEntryUpdate, ACLValidationResult
)

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
        
        # Return simplified wrapper expected by frontend
        return {
            "data": {
                "status": bind_status.get("status", "unknown"),
                "version": bind_status.get("version", "unknown"),
                # Ensure uptime is numeric seconds; fallback to 0
                "uptime": bind_status.get("uptime", 0) if isinstance(bind_status.get("uptime", 0), (int, float)) else 0,
            },
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

@router.get("/bind/status")
async def get_bind_service_status(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get BIND9 service running status"""
    try:
        bind_service = BindService(db)
        status = await bind_service.get_service_status()
        return {
            "data": {
                "running": status.get("status") == "active"
            },
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get BIND status: {str(e)}")

@router.get("/bind/installation")
async def check_bind9_installation(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Check BIND9 installation status and provide guidance"""
    try:
        bind_service = BindService(db)
        installation_status = await bind_service.check_bind9_installation()
        return {
            "data": installation_status,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check BIND9 installation: {str(e)}")

@router.post("/bind/reload")
async def reload_bind_configuration(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Reload BIND9 configuration"""
    try:
        bind_service = BindService(db)
        success = await bind_service.reload_service()
        return {"data": success, "success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload BIND: {str(e)}")

@router.post("/bind/restart")
async def restart_bind_service(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Restart BIND9 service"""
    try:
        bind_service = BindService(db)
        stopped = await bind_service.stop_service()
        # small delay to allow service to stop cleanly
        await asyncio.sleep(0.3)
        started = await bind_service.start_service()
        success = stopped and started
        return {"data": success, "success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart BIND: {str(e)}")

@router.post("/bind/flush-cache")
async def flush_bind_cache(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Flush DNS cache via rndc"""
    try:
        bind_service = BindService(db)
        success = await bind_service.flush_cache()
        return {"data": success, "success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to flush DNS cache: {str(e)}")

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


# ACL Management Endpoints
@router.get("/acls", response_model=List[ACLSummary])
async def list_acls(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    acl_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List all ACLs with optional filtering"""
    try:
        acl_service = ACLService(db)
        acls = await acl_service.get_acls(
            skip=skip,
            limit=limit,
            acl_type=acl_type,
            active_only=active_only,
            search=search
        )
        
        # Convert to summary format
        summaries = []
        for acl in acls:
            summaries.append(ACLSummary(
                id=acl.id,
                name=acl.name,
                acl_type=acl.acl_type,
                description=acl.description,
                is_active=acl.is_active,
                entry_count=len([e for e in acl.entries if e.is_active]) if acl.entries else 0,
                created_at=acl.created_at,
                updated_at=acl.updated_at
            ))
        
        return summaries
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list ACLs: {str(e)}")

@router.post("/acls", response_model=ACL)
async def create_acl(
    acl_data: ACLCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new ACL"""
    try:
        acl_service = ACLService(db)
        bind_service = BindService(db)
        
        # Create ACL
        acl = await acl_service.create_acl(acl_data, current_user.get("id"))
        
        # Regenerate ACL configuration
        all_acls = await acl_service.get_acls(active_only=True)
        await bind_service.generate_acl_configuration(all_acls)
        
        return acl
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ACL: {str(e)}")

@router.get("/acls/{acl_id}", response_model=ACL)
async def get_acl(
    acl_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific ACL"""
    try:
        acl_service = ACLService(db)
        acl = await acl_service.get_acl(acl_id)
        
        if not acl:
            raise HTTPException(status_code=404, detail="ACL not found")
        
        return acl
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ACL: {str(e)}")

@router.put("/acls/{acl_id}", response_model=ACL)
async def update_acl(
    acl_id: int,
    acl_data: ACLUpdate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update an ACL"""
    try:
        acl_service = ACLService(db)
        bind_service = BindService(db)
        
        acl = await acl_service.update_acl(acl_id, acl_data, current_user.get("id"))
        
        if not acl:
            raise HTTPException(status_code=404, detail="ACL not found")
        
        # Regenerate ACL configuration
        all_acls = await acl_service.get_acls(active_only=True)
        await bind_service.generate_acl_configuration(all_acls)
        
        return acl
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update ACL: {str(e)}")

@router.delete("/acls/{acl_id}")
async def delete_acl(
    acl_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete an ACL"""
    try:
        acl_service = ACLService(db)
        bind_service = BindService(db)
        
        success = await acl_service.delete_acl(acl_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="ACL not found")
        
        # Regenerate ACL configuration
        all_acls = await acl_service.get_acls(active_only=True)
        await bind_service.generate_acl_configuration(all_acls)
        
        return {"message": "ACL deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete ACL: {str(e)}")

@router.post("/acls/{acl_id}/toggle", response_model=ACL)
async def toggle_acl(
    acl_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Toggle ACL active status"""
    try:
        acl_service = ACLService(db)
        bind_service = BindService(db)
        
        acl = await acl_service.toggle_acl(acl_id, current_user.get("id"))
        
        if not acl:
            raise HTTPException(status_code=404, detail="ACL not found")
        
        # Regenerate ACL configuration
        all_acls = await acl_service.get_acls(active_only=True)
        await bind_service.generate_acl_configuration(all_acls)
        
        return acl
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle ACL: {str(e)}")

@router.post("/acls/{acl_id}/validate", response_model=ACLValidationResult)
async def validate_acl(
    acl_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate an ACL configuration"""
    try:
        acl_service = ACLService(db)
        validation_result = await acl_service.validate_acl(acl_id)
        
        return validation_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate ACL: {str(e)}")

# ACL Entry Management Endpoints
@router.get("/acls/{acl_id}/entries", response_model=List[ACLEntry])
async def list_acl_entries(
    acl_id: int,
    active_only: bool = Query(True),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List entries for a specific ACL"""
    try:
        acl_service = ACLService(db)
        
        # Check if ACL exists
        acl = await acl_service.get_acl(acl_id)
        if not acl:
            raise HTTPException(status_code=404, detail="ACL not found")
        
        entries = await acl_service.get_acl_entries(acl_id, active_only=active_only)
        return entries
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list ACL entries: {str(e)}")

@router.post("/acls/{acl_id}/entries", response_model=ACLEntry)
async def add_acl_entry(
    acl_id: int,
    entry_data: ACLEntryCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Add an entry to an ACL"""
    try:
        acl_service = ACLService(db)
        bind_service = BindService(db)
        
        entry = await acl_service.add_acl_entry(acl_id, entry_data, current_user.get("id"))
        
        if not entry:
            raise HTTPException(status_code=404, detail="ACL not found")
        
        # Regenerate ACL configuration
        all_acls = await acl_service.get_acls(active_only=True)
        await bind_service.generate_acl_configuration(all_acls)
        
        return entry
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add ACL entry: {str(e)}")

@router.put("/acl-entries/{entry_id}", response_model=ACLEntry)
async def update_acl_entry(
    entry_id: int,
    entry_data: ACLEntryUpdate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update an ACL entry"""
    try:
        acl_service = ACLService(db)
        bind_service = BindService(db)
        
        entry = await acl_service.update_acl_entry(entry_id, entry_data, current_user.get("id"))
        
        if not entry:
            raise HTTPException(status_code=404, detail="ACL entry not found")
        
        # Regenerate ACL configuration
        all_acls = await acl_service.get_acls(active_only=True)
        await bind_service.generate_acl_configuration(all_acls)
        
        return entry
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update ACL entry: {str(e)}")

@router.delete("/acl-entries/{entry_id}")
async def delete_acl_entry(
    entry_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete an ACL entry"""
    try:
        acl_service = ACLService(db)
        bind_service = BindService(db)
        
        success = await acl_service.delete_acl_entry(entry_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="ACL entry not found")
        
        # Regenerate ACL configuration
        all_acls = await acl_service.get_acls(active_only=True)
        await bind_service.generate_acl_configuration(all_acls)
        
        return {"message": "ACL entry deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete ACL entry: {str(e)}")

@router.post("/acls/{acl_id}/entries/bulk")
async def bulk_update_acl_entries(
    acl_id: int,
    bulk_data: BulkACLEntryUpdate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Bulk update ACL entries"""
    try:
        acl_service = ACLService(db)
        bind_service = BindService(db)
        
        results = await acl_service.bulk_update_acl_entries(acl_id, bulk_data, current_user.get("id"))
        
        # Regenerate ACL configuration if any updates were successful
        if results["successful_updates"] > 0:
            all_acls = await acl_service.get_acls(active_only=True)
            await bind_service.generate_acl_configuration(all_acls)
        
        return results
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk update ACL entries: {str(e)}")

@router.get("/acls/statistics")
async def get_acl_statistics(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get ACL statistics"""
    try:
        acl_service = ACLService(db)
        statistics = await acl_service.get_acl_statistics()
        
        return statistics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ACL statistics: {str(e)}")

@router.post("/acls/generate-config")
async def generate_acl_configuration(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Generate ACL configuration file"""
    try:
        acl_service = ACLService(db)
        bind_service = BindService(db)
        
        # Get all active ACLs
        all_acls = await acl_service.get_acls(active_only=True)
        
        # Generate configuration
        success = await bind_service.generate_acl_configuration(all_acls)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to generate ACL configuration")
        
        return {"message": "ACL configuration generated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate ACL configuration: {str(e)}")