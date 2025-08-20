"""
DNS zones management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from ...core.database import get_database_session
from ...core.dependencies import get_current_user
from ...models.dns import Zone as ZoneModel
from ...schemas.dns import (
    ZoneCreate, ZoneUpdate, Zone as ZoneSchema, 
    PaginatedResponse, ZoneQueryParams, ZoneValidationResult,
    SerialValidationResult, SerialHistoryResponse,
    ZoneImportFormat, ZoneExportFormat, ZoneImportResult
)
from ...services.zone_service import ZoneService
from ...services.bind_service import BindService

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[ZoneSchema])
async def list_zones(
    skip: int = Query(0, ge=0, description="Number of items to skip for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    zone_type: Optional[str] = Query(None, description="Filter by zone type (master, slave, forward)"),
    active_only: bool = Query(True, description="Filter to show only active zones"),
    search: Optional[str] = Query(None, min_length=1, max_length=255, description="Search term for zone name or description"),
    sort_by: Optional[str] = Query("name", description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order (asc or desc)"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List all DNS zones with enhanced filtering and pagination"""
    zone_service = ZoneService(db)
    
    # Validate sort_by field
    allowed_sort_fields = ['name', 'zone_type', 'created_at', 'updated_at', 'serial', 'is_active']
    if sort_by and sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid sort_by field. Allowed values: {', '.join(allowed_sort_fields)}"
        )
    
    result = await zone_service.get_zones(
        skip=skip,
        limit=limit,
        zone_type=zone_type,
        active_only=active_only,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return PaginatedResponse[ZoneSchema](**result)


@router.post("/", response_model=ZoneSchema)
async def create_zone(
    zone_data: ZoneCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new DNS zone"""
    zone_service = ZoneService(db)
    bind_service = BindService(db)
    
    # Validate zone data
    validation_result = await zone_service.validate_zone_data(zone_data.dict())
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Zone validation failed",
                "errors": validation_result["errors"],
                "warnings": validation_result["warnings"]
            }
        )
    
    # Create backup before zone creation
    backup_success = await bind_service.backup_before_zone_changes(zone_data.name, "create")
    if not backup_success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create backup before zone creation"
        )
    
    # Create zone in database
    zone = await zone_service.create_zone(zone_data.dict())
    
    # Generate BIND9 configuration
    try:
        await bind_service.create_zone_file(zone)
        await bind_service.reload_configuration()
    except Exception as e:
        # If BIND configuration fails, we should still return the zone
        # but log the error for investigation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update BIND9 configuration for zone {zone.name}: {e}")
    
    return zone


@router.get("/{zone_id}", response_model=ZoneSchema)
async def get_zone(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific DNS zone"""
    zone_service = ZoneService(db)
    zone = await zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@router.put("/{zone_id}", response_model=ZoneSchema)
async def update_zone(
    zone_id: int,
    zone_data: ZoneUpdate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update a DNS zone"""
    zone_service = ZoneService(db)
    bind_service = BindService(db)
    
    # Get existing zone for backup
    existing_zone = await zone_service.get_zone(zone_id)
    if not existing_zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Validate zone data
    validation_result = await zone_service.validate_zone_data(zone_data.dict(exclude_unset=True), zone_id)
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Zone validation failed",
                "errors": validation_result["errors"],
                "warnings": validation_result["warnings"]
            }
        )
    
    # Create backup before zone update
    backup_success = await bind_service.backup_before_zone_changes(existing_zone.name, "update")
    if not backup_success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create backup before zone update"
        )
    
    zone = await zone_service.update_zone(zone_id, zone_data.dict(exclude_unset=True))
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Update BIND9 configuration
    try:
        await bind_service.update_zone_file(zone)
        await bind_service.reload_configuration()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update BIND9 configuration for zone {zone.name}: {e}")
    
    return zone


@router.delete("/{zone_id}")
async def delete_zone(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete a DNS zone"""
    zone_service = ZoneService(db)
    bind_service = BindService(db)
    
    # Get zone info before deletion
    zone = await zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Create backup before zone deletion
    backup_success = await bind_service.backup_before_zone_changes(zone.name, "delete")
    if not backup_success:
        raise HTTPException(
            status_code=500,
            detail="Failed to create backup before zone deletion"
        )
    
    zone_name = zone.name
    success = await zone_service.delete_zone(zone_id)
    if not success:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Remove from BIND9 configuration
    try:
        await bind_service.delete_zone_file(zone_id)
        await bind_service.reload_configuration()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update BIND9 configuration after deleting zone {zone_name}: {e}")
    
    return {"message": f"Zone '{zone_name}' deleted successfully"}


@router.post("/{zone_id}/validate", response_model=ZoneValidationResult)
async def validate_zone(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Comprehensive zone configuration validation"""
    zone_service = ZoneService(db)
    bind_service = BindService()
    
    zone = await zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Use comprehensive zone validation for BIND9 compatibility
    validation_result = await zone_service.validate_zone_for_bind(zone_id)
    
    return ZoneValidationResult(
        valid=validation_result["valid"],
        errors=validation_result["errors"],
        warnings=validation_result["warnings"]
    )


@router.post("/{zone_id}/reload")
async def reload_zone(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Reload zone in BIND9"""
    zone_service = ZoneService(db)
    bind_service = BindService()
    
    zone = await zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    try:
        await bind_service.reload_zone(zone_id)
        return {"message": f"Zone '{zone.name}' reloaded successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload zone '{zone.name}': {str(e)}"
        )


@router.post("/{zone_id}/toggle")
async def toggle_zone(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Toggle zone active status"""
    zone_service = ZoneService(db)
    bind_service = BindService()
    
    zone = await zone_service.toggle_zone_status(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Update BIND9 configuration
    try:
        if zone.is_active:
            await bind_service.create_zone_file(zone)
        else:
            await bind_service.delete_zone_file(zone_id)
        await bind_service.reload_configuration()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update BIND9 configuration for zone {zone.name}: {e}")
    
    status = "activated" if zone.is_active else "deactivated"
    return {"message": f"Zone '{zone.name}' {status} successfully", "zone": zone}


@router.get("/{zone_id}/statistics")
async def get_zone_statistics(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get zone statistics"""
    zone_service = ZoneService(db)
    
    statistics = await zone_service.get_zone_statistics(zone_id)
    if not statistics:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    return statistics


@router.get("/{zone_id}/health")
async def get_zone_health(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get zone health status"""
    zone_service = ZoneService(db)
    
    health = await zone_service.get_zone_health(zone_id)
    if not health:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    return health


@router.get("/{zone_id}/statistics/health")
async def get_zone_health_statistics(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get zone health and performance statistics"""
    zone_service = ZoneService(db)
    
    health_stats = await zone_service.get_zone_health_statistics(zone_id)
    if not health_stats:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    return health_stats


@router.get("/{zone_id}/statistics/activity")
async def get_zone_activity_statistics(
    zone_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get zone activity statistics over a specified period"""
    zone_service = ZoneService(db)
    
    activity_stats = await zone_service.get_zone_activity_statistics(zone_id, days)
    if not activity_stats:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    return activity_stats


@router.get("/{zone_id}/statistics/records")
async def get_zone_record_distribution(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed distribution of record types in a zone"""
    zone_service = ZoneService(db)
    
    distribution = await zone_service.get_zone_record_type_distribution(zone_id)
    if not distribution:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    return distribution


@router.get("/{zone_id}/statistics/size")
async def get_zone_size_statistics(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get zone size and complexity statistics"""
    zone_service = ZoneService(db)
    
    size_stats = await zone_service.get_zone_size_statistics(zone_id)
    if not size_stats:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    return size_stats


@router.post("/statistics/compare")
async def compare_zones_statistics(
    zone_ids: List[int],
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comparative statistics for multiple zones"""
    if not zone_ids:
        raise HTTPException(status_code=400, detail="At least one zone ID is required")
    
    if len(zone_ids) > 20:
        raise HTTPException(status_code=400, detail="Cannot compare more than 20 zones at once")
    
    zone_service = ZoneService(db)
    comparison = await zone_service.get_zones_comparison_statistics(zone_ids)
    
    return comparison


@router.get("/statistics/summary")
async def get_zones_summary_statistics(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get summary statistics for all zones"""
    zone_service = ZoneService(db)
    summary = await zone_service.get_zones_summary()
    
    return summary


@router.get("/{zone_id}/export")
async def export_zone(
    zone_id: int,
    format: str = Query("json", description="Export format: json, bind, csv"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Export zone data in various formats"""
    from ...schemas.dns import ZoneExportFormat
    
    # Validate format
    valid_formats = [f.value for f in ZoneExportFormat]
    if format.lower() not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid export format '{format}'. Supported formats: {', '.join(valid_formats)}"
        )
    
    zone_service = ZoneService(db)
    
    # Check if zone exists
    zone = await zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    try:
        export_data = await zone_service.export_zone_in_format(zone_id, format.lower())
        if not export_data:
            raise HTTPException(status_code=404, detail="Zone not found or has no data to export")
        
        # Set appropriate response headers based on format
        from fastapi import Response
        
        if format.lower() == "bind":
            return Response(
                content=export_data["zone_file_content"],
                media_type="text/plain",
                headers={
                    "Content-Disposition": f"attachment; filename={export_data['filename']}"
                }
            )
        elif format.lower() == "csv":
            return Response(
                content=export_data["csv_content"],
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={export_data['filename']}"
                }
            )
        else:
            # JSON format
            return export_data
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export zone: {str(e)}"
        )


@router.post("/import")
async def import_zone(
    import_data: Dict[str, Any],
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Import zone from various formats"""
    from ...schemas.dns import ZoneImportFormat, ZoneImportResult
    
    zone_service = ZoneService(db)
    bind_service = BindService(db)
    
    try:
        # Handle different import formats
        format_type = import_data.get('format', 'json')
        
        if format_type == ZoneImportFormat.BIND.value:
            # Parse BIND zone file
            zone_file_content = import_data.get('zone_file_content', '')
            zone_name = import_data.get('zone_name', '')
            
            if not zone_file_content or not zone_name:
                raise HTTPException(
                    status_code=400,
                    detail="BIND format requires 'zone_file_content' and 'zone_name' fields"
                )
            
            # Parse the zone file
            parse_result = await zone_service.parse_bind_zone_file(zone_file_content, zone_name)
            
            if parse_result["errors"]:
                return ZoneImportResult(
                    success=False,
                    zone_name=zone_name,
                    errors=parse_result["errors"],
                    warnings=parse_result["warnings"]
                )
            
            # Create zone data from parsed content
            zone_data = {
                'name': zone_name,
                'zone_type': 'master',
                'email': import_data.get('email', f'admin.{zone_name}'),
                'description': f'Imported from BIND zone file'
            }
            
            import_data = {
                'zone': zone_data,
                'records': parse_result["records"],
                'format': format_type,
                'validate_only': import_data.get('validate_only', False),
                'overwrite_existing': import_data.get('overwrite_existing', False)
            }
        
        elif format_type == ZoneImportFormat.CSV.value:
            # Parse CSV content
            csv_content = import_data.get('csv_content', '')
            zone_name = import_data.get('zone_name', '')
            
            if not csv_content or not zone_name:
                raise HTTPException(
                    status_code=400,
                    detail="CSV format requires 'csv_content' and 'zone_name' fields"
                )
            
            # Parse the CSV
            parse_result = await zone_service.parse_csv_zone_data(csv_content)
            
            if parse_result["errors"]:
                return ZoneImportResult(
                    success=False,
                    zone_name=zone_name,
                    errors=parse_result["errors"],
                    warnings=parse_result["warnings"]
                )
            
            # Create zone data from CSV
            zone_data = {
                'name': zone_name,
                'zone_type': 'master',
                'email': import_data.get('email', f'admin.{zone_name}'),
                'description': f'Imported from CSV file'
            }
            
            import_data = {
                'zone': zone_data,
                'records': parse_result["records"],
                'format': format_type,
                'validate_only': import_data.get('validate_only', False),
                'overwrite_existing': import_data.get('overwrite_existing', False)
            }
        
        # Import the zone
        result = await zone_service.import_zone_from_data(import_data)
        
        # Update BIND9 configuration if import was successful and not validation only
        if result["success"] and not result["validation_only"] and result["zone_id"]:
            try:
                zone = await zone_service.get_zone(result["zone_id"])
                if zone:
                    await bind_service.create_zone_file(zone)
                    await bind_service.reload_configuration()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to update BIND9 configuration after import: {e}")
                result["warnings"].append("Zone imported but BIND9 configuration update failed")
        
        return ZoneImportResult(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Import failed: {str(e)}"
        )


@router.post("/import/validate")
async def validate_zone_import(
    import_data: Dict[str, Any],
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate zone import data without actually importing"""
    # Set validation only flag
    import_data['validate_only'] = True
    
    # Use the same import endpoint but with validation only
    return await import_zone(import_data, db, current_user)


@router.post("/{zone_id}/serial/increment")
async def increment_zone_serial(
    zone_id: int,
    reason: str = Query("manual", description="Reason for serial increment"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Manually increment zone serial number"""
    zone_service = ZoneService(db)
    bind_service = BindService()
    
    zone = await zone_service.increment_serial(zone_id, reason)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Update BIND9 configuration
    try:
        await bind_service.update_zone_file(zone)
        await bind_service.reload_zone(zone_id)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update BIND9 configuration for zone {zone.name}: {e}")
    
    return {
        "message": f"Zone '{zone.name}' serial incremented to {zone.serial}",
        "zone": zone,
        "serial": zone.serial
    }


@router.post("/{zone_id}/serial/reset")
async def reset_zone_serial(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Reset zone serial number to current date"""
    zone_service = ZoneService(db)
    bind_service = BindService()
    
    zone = await zone_service.reset_serial_to_current_date(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Update BIND9 configuration
    try:
        await bind_service.update_zone_file(zone)
        await bind_service.reload_zone(zone_id)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update BIND9 configuration for zone {zone.name}: {e}")
    
    return {
        "message": f"Zone '{zone.name}' serial reset to {zone.serial}",
        "zone": zone,
        "serial": zone.serial
    }


@router.put("/{zone_id}/serial/{serial}")
async def set_zone_serial(
    zone_id: int,
    serial: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Set custom serial number for zone"""
    zone_service = ZoneService(db)
    bind_service = BindService()
    
    try:
        zone = await zone_service.set_custom_serial(zone_id, serial)
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Update BIND9 configuration
    try:
        await bind_service.update_zone_file(zone)
        await bind_service.reload_zone(zone_id)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update BIND9 configuration for zone {zone.name}: {e}")
    
    return {
        "message": f"Zone '{zone.name}' serial set to {zone.serial}",
        "zone": zone,
        "serial": zone.serial
    }


@router.get("/{zone_id}/serial/validate/{serial}", response_model=SerialValidationResult)
async def validate_serial_number(
    zone_id: int,
    serial: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate a serial number format"""
    zone_service = ZoneService(db)
    
    # Check if zone exists
    zone = await zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    validation = await zone_service.validate_serial_number(serial)
    return SerialValidationResult(**validation)


@router.get("/{zone_id}/serial/history", response_model=SerialHistoryResponse)
async def get_serial_history(
    zone_id: int,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of history entries"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get serial number change history for zone"""
    zone_service = ZoneService(db)
    
    # Check if zone exists
    zone = await zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    history = await zone_service.get_serial_history(zone_id, limit)
    return SerialHistoryResponse(
        zone_id=zone_id,
        zone_name=zone.name,
        history=history
    )


@router.post("/{zone_id}/validate/configuration")
async def validate_zone_configuration(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate zone configuration only (without records)"""
    zone_service = ZoneService(db)
    
    zone = await zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    validation_result = await zone_service.validate_zone_configuration(zone_id)
    return validation_result


@router.post("/{zone_id}/validate/records")
async def validate_zone_records(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate all DNS records in a zone"""
    zone_service = ZoneService(db)
    
    zone = await zone_service.get_zone(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    validation_result = await zone_service.validate_zone_records(zone_id)
    return validation_result


@router.post("/validate/name")
async def validate_zone_name(
    zone_name: str = Query(..., min_length=1, max_length=253, description="Zone name to validate"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate zone name format and structure"""
    zone_service = ZoneService(db)
    
    validation_result = await zone_service.validate_zone_name(zone_name)
    return validation_result


@router.post("/validate/servers")
async def validate_server_list(
    servers: list[str] = Query(..., description="List of server IP addresses to validate"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate a list of server IP addresses"""
    zone_service = ZoneService(db)
    
    validation_result = await zone_service.validate_server_list(servers)
    return validation_result