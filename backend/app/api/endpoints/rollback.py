"""
Rollback API endpoints for BIND9 configuration management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...services.bind_service import BindService
from ...services.backup_service import BackupService

router = APIRouter()

@router.get("/candidates")
async def get_rollback_candidates(
    rollback_type: str = Query("all", regex="^(all|full|zone|rpz|forwarder)$"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get list of available backups that can be used for rollback"""
    try:
        bind_service = BindService(db)
        candidates = await bind_service.get_rollback_candidates(rollback_type)
        
        return {
            "candidates": candidates,
            "total": len(candidates),
            "type_filter": rollback_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rollback candidates: {str(e)}")

@router.post("/test/{backup_id}")
async def test_rollback_safety(
    backup_id: str,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Test if a rollback would be safe without actually performing it"""
    try:
        bind_service = BindService(db)
        safety_result = await bind_service.test_rollback_safety(backup_id)
        
        return safety_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test rollback safety: {str(e)}")

@router.post("/configuration/{backup_id}")
async def rollback_configuration(
    backup_id: str,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Rollback full BIND9 configuration to a previous backup"""
    try:
        bind_service = BindService(db)
        
        # Test safety first
        safety_result = await bind_service.test_rollback_safety(backup_id)
        if not safety_result["safe"]:
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": "Rollback is not safe to perform",
                    "errors": safety_result["errors"],
                    "warnings": safety_result["warnings"]
                }
            )
        
        # Perform the rollback
        success = await bind_service.rollback_configuration(backup_id)
        
        if success:
            return {
                "message": "Configuration rollback completed successfully",
                "backup_id": backup_id,
                "status": "success"
            }
        else:
            raise HTTPException(status_code=500, detail="Configuration rollback failed")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollback configuration: {str(e)}")

@router.post("/zone/{zone_name}")
async def rollback_zone_changes(
    zone_name: str,
    backup_id: Optional[str] = Query(None, description="Specific backup ID to restore from"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Rollback zone changes to a previous backup"""
    try:
        bind_service = BindService(db)
        
        # If backup_id is provided, test safety
        if backup_id:
            safety_result = await bind_service.test_rollback_safety(backup_id)
            if not safety_result["safe"]:
                raise HTTPException(
                    status_code=400, 
                    detail={
                        "message": "Rollback is not safe to perform",
                        "errors": safety_result["errors"],
                        "warnings": safety_result["warnings"]
                    }
                )
        
        # Perform the rollback
        success = await bind_service.rollback_zone_changes(zone_name, backup_id)
        
        if success:
            return {
                "message": f"Zone {zone_name} rollback completed successfully",
                "zone_name": zone_name,
                "backup_id": backup_id,
                "status": "success"
            }
        else:
            raise HTTPException(status_code=500, detail=f"Zone {zone_name} rollback failed")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollback zone {zone_name}: {str(e)}")

@router.post("/rpz/{rpz_zone}")
async def rollback_rpz_changes(
    rpz_zone: str,
    backup_id: Optional[str] = Query(None, description="Specific backup ID to restore from"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Rollback RPZ zone changes to a previous backup"""
    try:
        bind_service = BindService(db)
        
        # If backup_id is provided, test safety
        if backup_id:
            safety_result = await bind_service.test_rollback_safety(backup_id)
            if not safety_result["safe"]:
                raise HTTPException(
                    status_code=400, 
                    detail={
                        "message": "Rollback is not safe to perform",
                        "errors": safety_result["errors"],
                        "warnings": safety_result["warnings"]
                    }
                )
        
        # Perform the rollback
        success = await bind_service.rollback_rpz_changes(rpz_zone, backup_id)
        
        if success:
            return {
                "message": f"RPZ zone {rpz_zone} rollback completed successfully",
                "rpz_zone": rpz_zone,
                "backup_id": backup_id,
                "status": "success"
            }
        else:
            raise HTTPException(status_code=500, detail=f"RPZ zone {rpz_zone} rollback failed")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollback RPZ zone {rpz_zone}: {str(e)}")

@router.post("/forwarders")
async def rollback_forwarder_changes(
    backup_id: Optional[str] = Query(None, description="Specific backup ID to restore from"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Rollback forwarder configuration changes to a previous backup"""
    try:
        bind_service = BindService(db)
        
        # If backup_id is provided, test safety
        if backup_id:
            safety_result = await bind_service.test_rollback_safety(backup_id)
            if not safety_result["safe"]:
                raise HTTPException(
                    status_code=400, 
                    detail={
                        "message": "Rollback is not safe to perform",
                        "errors": safety_result["errors"],
                        "warnings": safety_result["warnings"]
                    }
                )
        
        # Perform the rollback
        success = await bind_service.rollback_forwarder_changes(backup_id)
        
        if success:
            return {
                "message": "Forwarder configuration rollback completed successfully",
                "backup_id": backup_id,
                "status": "success"
            }
        else:
            raise HTTPException(status_code=500, detail="Forwarder configuration rollback failed")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollback forwarder configuration: {str(e)}")

@router.get("/history")
async def get_rollback_history(
    limit: int = Query(50, ge=1, le=200),
    rollback_type: Optional[str] = Query(None, regex="^(full_config|zone_file|rpz_file|configuration)$"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get history of rollback operations"""
    try:
        backup_service = BackupService()
        
        # Get backup history based on type filter
        if rollback_type:
            from ...services.backup_service import BackupType
            backup_type_enum = BackupType(rollback_type)
            backups = await backup_service.list_backups(backup_type_enum, limit)
        else:
            backups = await backup_service.list_backups(limit=limit)
        
        # Format history entries
        history = []
        for backup in backups:
            history.append({
                "backup_id": backup.backup_id,
                "type": backup.backup_type.value,
                "description": backup.description,
                "timestamp": backup.timestamp.isoformat(),
                "file_size": backup.file_size,
                "original_path": backup.original_path,
                "can_rollback": True  # All backups in history can potentially be used for rollback
            })
        
        return {
            "history": history,
            "total": len(history),
            "limit": limit,
            "type_filter": rollback_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rollback history: {str(e)}")

@router.delete("/cleanup")
async def cleanup_old_rollback_data(
    days_old: int = Query(30, ge=1, le=365, description="Delete rollback data older than this many days"),
    dry_run: bool = Query(True, description="If true, only show what would be deleted"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Clean up old rollback data and backups"""
    try:
        backup_service = BackupService()
        
        if dry_run:
            # Get list of what would be cleaned up
            all_backups = await backup_service.list_backups(limit=1000)
            
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            old_backups = [
                {
                    "backup_id": b.backup_id,
                    "type": b.backup_type.value,
                    "description": b.description,
                    "timestamp": b.timestamp.isoformat(),
                    "file_size": b.file_size
                }
                for b in all_backups 
                if b.timestamp < cutoff_date
            ]
            
            total_size = sum(b["file_size"] for b in old_backups)
            
            return {
                "dry_run": True,
                "would_delete": len(old_backups),
                "total_size_bytes": total_size,
                "backups": old_backups,
                "cutoff_date": cutoff_date.isoformat()
            }
        else:
            # Actually perform cleanup
            cleaned_count = await backup_service.cleanup_old_backups()
            
            return {
                "dry_run": False,
                "deleted_count": cleaned_count,
                "message": f"Successfully cleaned up {cleaned_count} old backups"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup rollback data: {str(e)}")