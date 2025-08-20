"""
Backup management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...services.backup_service import BackupService, BackupType, BackupMetadata
from ...services.bind_service import BindService

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def list_backups(
    backup_type: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """List available backups with optional filtering by type"""
    try:
        backup_service = BackupService()
        
        # Convert string to BackupType enum if provided
        filter_type = None
        if backup_type:
            try:
                filter_type = BackupType(backup_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid backup type: {backup_type}")
        
        backups = await backup_service.list_backups(backup_type=filter_type, limit=limit)
        
        # Convert to dict format for JSON response
        return [backup.to_dict() for backup in backups]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

@router.post("/full")
async def create_full_backup(
    description: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(get_current_user)
):
    """Create a full configuration backup"""
    try:
        backup_service = BackupService()
        
        # Create backup in background for better performance
        backup_id = await backup_service.create_full_configuration_backup(
            description or f"Manual full backup by {current_user.get('username', 'unknown')}"
        )
        
        if not backup_id:
            raise HTTPException(status_code=500, detail="Failed to create backup")
        
        return {
            "message": "Full backup created successfully",
            "backup_id": backup_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create full backup: {str(e)}")

@router.get("/{backup_id}")
async def get_backup_info(
    backup_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific backup"""
    try:
        backup_service = BackupService()
        backup_info = await backup_service.get_backup_info(backup_id)
        
        if not backup_info:
            raise HTTPException(status_code=404, detail="Backup not found")
        
        return backup_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backup info: {str(e)}")

@router.post("/{backup_id}/restore")
async def restore_backup(
    backup_id: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Restore configuration from a backup"""
    try:
        backup_service = BackupService()
        bind_service = BindService(db)
        
        # Create a backup before restore
        pre_restore_backup = await backup_service.create_full_configuration_backup(
            f"Pre-restore backup before restoring {backup_id} by {current_user.get('username', 'unknown')}"
        )
        
        if not pre_restore_backup:
            raise HTTPException(status_code=500, detail="Failed to create pre-restore backup")
        
        # Perform the restore
        success = await backup_service.restore_from_backup(backup_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to restore from backup")
        
        # Reload BIND9 configuration after restore
        background_tasks.add_task(bind_service.reload_configuration)
        
        return {
            "message": "Backup restored successfully",
            "pre_restore_backup_id": pre_restore_backup,
            "restored_backup_id": backup_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {str(e)}")

@router.delete("/{backup_id}")
async def delete_backup(
    backup_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a specific backup"""
    try:
        backup_service = BackupService()
        success = await backup_service.delete_backup(backup_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Backup not found or could not be deleted")
        
        return {"message": "Backup deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")

@router.post("/cleanup")
async def cleanup_old_backups(
    current_user: dict = Depends(get_current_user)
):
    """Clean up old backups based on retention policy"""
    try:
        backup_service = BackupService()
        cleaned_count = await backup_service.cleanup_old_backups()
        
        return {
            "message": f"Cleaned up {cleaned_count} old backups",
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup old backups: {str(e)}")

@router.get("/types/available")
async def get_backup_types(
    current_user: dict = Depends(get_current_user)
):
    """Get available backup types"""
    return {
        "backup_types": [
            {
                "value": backup_type.value,
                "name": backup_type.value.replace('_', ' ').title(),
                "description": _get_backup_type_description(backup_type)
            }
            for backup_type in BackupType
        ]
    }

def _get_backup_type_description(backup_type: BackupType) -> str:
    """Get description for backup type"""
    descriptions = {
        BackupType.ZONE_FILE: "Individual DNS zone file backups",
        BackupType.RPZ_FILE: "Response Policy Zone (RPZ) file backups",
        BackupType.CONFIGURATION: "BIND9 configuration file backups",
        BackupType.FULL_CONFIG: "Complete system configuration backups"
    }
    return descriptions.get(backup_type, "Unknown backup type")