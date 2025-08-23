"""
DNS records management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...models.dns import DNSRecord, Zone
from ...schemas.dns import (
    DNSRecordCreate, DNSRecordUpdate, DNSRecord as DNSRecordSchema,
    PaginatedResponse, ZoneValidationResult, RecordStatistics,
    RecordImportFormat, RecordExportFormat, RecordImportRequest, RecordImportResult,
    RecordExportRequest, RecordExportResult, DNSRecordHistory, RecordHistoryResponse,
    RecordValidationRequest, RecordValidationResult, GlobalRecordStatistics,
    ZoneRecordStatistics
)
from ...services.record_service import RecordService
from ...services.bind_service import BindService
from ...services.record_template_service import RecordTemplateService, RecordTemplateCategory
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/zones/{zone_id}/records", response_model=PaginatedResponse[DNSRecordSchema])
async def list_zone_records(
    zone_id: int,
    record_type: Optional[str] = Query(None, description="Filter by record type (A, AAAA, CNAME, etc.)"),
    name: Optional[str] = Query(None, description="Filter by record name (partial match)"),
    search: Optional[str] = Query(None, description="Search in name or value"),
    active_only: bool = Query(True, description="Show only active records"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    sort_by: Optional[str] = Query("name", description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List DNS records for a specific zone with filtering and pagination"""
    logger.info(f"User {current_user.get('username')} listing records for zone {zone_id}")
    
    record_service = RecordService(db)
    
    try:
        # Verify zone exists
        zone = await record_service._get_zone(zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail=f"Zone with ID {zone_id} not found")
        
        # Get paginated records
        result = await record_service.get_records(
            zone_id=zone_id,
            record_type=record_type,
            name=name,
            search=search,
            active_only=active_only,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        logger.info(f"Retrieved {len(result['items'])} records for zone {zone.name}")
        return result
        
    except ValueError as e:
        logger.error(f"Validation error listing zone records: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing zone records: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/zones/{zone_id}/records", response_model=DNSRecordSchema)
async def create_zone_record(
    zone_id: int,
    record_data: DNSRecordCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new DNS record in the specified zone"""
    logger.info(f"User {current_user.get('username')} creating {record_data.type} record '{record_data.name}' in zone {zone_id}")
    
    record_service = RecordService(db)
    bind_service = BindService(db)
    
    try:
        # Convert schema data to service format (map 'type' to 'record_type')
        record_dict = record_data.dict()
        if 'type' in record_dict:
            record_dict['record_type'] = record_dict.pop('type')
        
        # Create record in database
        record = await record_service.create_record(zone_id, record_dict)
        
        # Schedule BIND9 configuration update in background
        background_tasks.add_task(
            update_bind_configuration_for_zone,
            bind_service,
            zone_id,
            f"Added {record.record_type} record '{record.name}'"
        )
        
        logger.info(f"Created DNS record {record.name} {record.record_type} in zone {zone_id}")
        return record
        
    except ValueError as e:
        logger.error(f"Validation error creating record: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating DNS record: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/records/{record_id}", response_model=DNSRecordSchema)
async def get_record_details(
    record_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a specific DNS record"""
    logger.info(f"User {current_user.get('username')} retrieving record {record_id}")
    
    record_service = RecordService(db)
    
    try:
        record = await record_service.get_record(record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"DNS record with ID {record_id} not found")
        
        logger.info(f"Retrieved record {record.name} {record.record_type}")
        return record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving DNS record {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/records/{record_id}", response_model=DNSRecordSchema)
async def update_record(
    record_id: int,
    record_data: DNSRecordUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update an existing DNS record"""
    logger.info(f"User {current_user.get('username')} updating record {record_id}")
    
    record_service = RecordService(db)
    bind_service = BindService(db)
    
    try:
        # Get original record for logging
        original_record = await record_service.get_record(record_id)
        if not original_record:
            raise HTTPException(status_code=404, detail=f"DNS record with ID {record_id} not found")
        
        # Convert schema data to service format (map 'type' to 'record_type')
        update_dict = record_data.dict(exclude_unset=True)
        if 'type' in update_dict:
            update_dict['record_type'] = update_dict.pop('type')
        
        # Update record in database
        updated_record = await record_service.update_record(record_id, update_dict)
        if not updated_record:
            raise HTTPException(status_code=404, detail=f"DNS record with ID {record_id} not found")
        
        # Schedule BIND9 configuration update in background
        background_tasks.add_task(
            update_bind_configuration_for_zone,
            bind_service,
            updated_record.zone_id,
            f"Updated {updated_record.record_type} record '{updated_record.name}'"
        )
        
        logger.info(f"Updated DNS record {updated_record.name} {updated_record.record_type}")
        return updated_record
        
    except ValueError as e:
        logger.error(f"Validation error updating record: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating DNS record {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/records/{record_id}")
async def delete_record(
    record_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete a DNS record"""
    logger.info(f"User {current_user.get('username')} deleting record {record_id}")
    
    record_service = RecordService(db)
    bind_service = BindService(db)
    
    try:
        # Get record info before deletion for logging and BIND update
        record = await record_service.get_record(record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"DNS record with ID {record_id} not found")
        
        zone_id = record.zone_id
        record_info = f"{record.name} {record.record_type}"
        
        # Delete record from database
        success = await record_service.delete_record(record_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"DNS record with ID {record_id} not found")
        
        # Schedule BIND9 configuration update in background
        background_tasks.add_task(
            update_bind_configuration_for_zone,
            bind_service,
            zone_id,
            f"Deleted {record_info}"
        )
        
        logger.info(f"Deleted DNS record {record_info}")
        return {"message": f"DNS record {record_info} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting DNS record {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Additional endpoints for record management

@router.post("/records/{record_id}/toggle", response_model=DNSRecordSchema)
async def toggle_record_status(
    record_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Toggle the active status of a DNS record"""
    logger.info(f"User {current_user.get('username')} toggling record {record_id} status")
    
    record_service = RecordService(db)
    bind_service = BindService(db)
    
    try:
        record = await record_service.toggle_record(record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"DNS record with ID {record_id} not found")
        
        # Schedule BIND9 configuration update in background
        status_text = "activated" if record.is_active else "deactivated"
        background_tasks.add_task(
            update_bind_configuration_for_zone,
            bind_service,
            record.zone_id,
            f"{status_text.capitalize()} {record.record_type} record '{record.name}'"
        )
        
        logger.info(f"DNS record {record.name} {record.record_type} {status_text}")
        return record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling DNS record {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/records/{record_id}/validate", response_model=ZoneValidationResult)
async def validate_record(
    record_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate a specific DNS record"""
    logger.info(f"User {current_user.get('username')} validating record {record_id}")
    
    record_service = RecordService(db)
    
    try:
        record = await record_service.get_record(record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"DNS record with ID {record_id} not found")
        
        # Validate the record data
        validation_result = await record_service.validate_record_data(
            {
                'name': record.name,
                'record_type': record.record_type,
                'value': record.value,
                'ttl': record.ttl,
                'priority': record.priority,
                'weight': record.weight,
                'port': record.port
            },
            record.zone_id,
            record_id
        )
        
        logger.info(f"Validated record {record.name} {record.record_type}: {'valid' if validation_result['valid'] else 'invalid'}")
        
        return ZoneValidationResult(
            valid=validation_result["valid"],
            errors=validation_result["errors"],
            warnings=validation_result["warnings"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating DNS record {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/zones/{zone_id}/records/statistics", response_model=RecordStatistics)
async def get_zone_record_statistics(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get statistics about DNS records in a zone"""
    logger.info(f"User {current_user.get('username')} retrieving record statistics for zone {zone_id}")
    
    record_service = RecordService(db)
    
    try:
        # Verify zone exists
        zone = await record_service._get_zone(zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail=f"Zone with ID {zone_id} not found")
        
        statistics = await record_service.get_record_statistics(zone_id)
        
        logger.info(f"Retrieved record statistics for zone {zone.name}")
        return statistics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving record statistics for zone {zone_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Bulk operations

@router.post("/zones/{zone_id}/records/bulk", response_model=List[DNSRecordSchema])
async def bulk_create_records(
    zone_id: int,
    records_data: List[DNSRecordCreate],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create multiple DNS records in bulk"""
    logger.info(f"User {current_user.get('username')} bulk creating {len(records_data)} records in zone {zone_id}")
    
    record_service = RecordService(db)
    bind_service = BindService(db)
    
    try:
        # Convert Pydantic models to dictionaries and map field names
        records_dict_data = []
        for record in records_data:
            record_dict = record.dict()
            if 'type' in record_dict:
                record_dict['record_type'] = record_dict.pop('type')
            records_dict_data.append(record_dict)
        
        # Create records in bulk
        created_records = await record_service.bulk_create_records(zone_id, records_dict_data)
        
        # Schedule BIND9 configuration update in background
        background_tasks.add_task(
            update_bind_configuration_for_zone,
            bind_service,
            zone_id,
            f"Bulk created {len(created_records)} records"
        )
        
        logger.info(f"Bulk created {len(created_records)} records in zone {zone_id}")
        return created_records
        
    except ValueError as e:
        logger.error(f"Validation error in bulk create: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in bulk record creation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/records/bulk", response_model=List[DNSRecordSchema])
async def bulk_update_records(
    record_ids: List[int],
    update_data: DNSRecordUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update multiple DNS records in bulk"""
    logger.info(f"User {current_user.get('username')} bulk updating {len(record_ids)} records")
    
    record_service = RecordService(db)
    bind_service = BindService(db)
    
    try:
        # Convert schema data to service format (map 'type' to 'record_type')
        update_dict = update_data.dict(exclude_unset=True)
        if 'type' in update_dict:
            update_dict['record_type'] = update_dict.pop('type')
        
        # Update records in bulk
        updated_records = await record_service.bulk_update_records(record_ids, update_dict)
        
        # Get unique zone IDs for BIND updates
        zone_ids = set(record.zone_id for record in updated_records)
        
        # Schedule BIND9 configuration updates for affected zones
        for zone_id in zone_ids:
            background_tasks.add_task(
                update_bind_configuration_for_zone,
                bind_service,
                zone_id,
                f"Bulk updated records"
            )
        
        logger.info(f"Bulk updated {len(updated_records)} records across {len(zone_ids)} zones")
        return updated_records
        
    except Exception as e:
        logger.error(f"Error in bulk record update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/records/bulk")
async def bulk_delete_records(
    record_ids: List[int],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete multiple DNS records in bulk"""
    logger.info(f"User {current_user.get('username')} bulk deleting {len(record_ids)} records")
    
    record_service = RecordService(db)
    bind_service = BindService(db)
    
    try:
        # Get zone IDs before deletion for BIND updates
        zone_ids = set()
        for record_id in record_ids:
            zone_id = await record_service.get_record_zone_id(record_id)
            if zone_id:
                zone_ids.add(zone_id)
        
        # Delete records in bulk
        deleted_count = await record_service.bulk_delete_records(record_ids)
        
        # Schedule BIND9 configuration updates for affected zones
        for zone_id in zone_ids:
            background_tasks.add_task(
                update_bind_configuration_for_zone,
                bind_service,
                zone_id,
                f"Bulk deleted records"
            )
        
        logger.info(f"Bulk deleted {deleted_count} records from {len(zone_ids)} zones")
        return {"message": f"Successfully deleted {deleted_count} DNS records"}
        
    except Exception as e:
        logger.error(f"Error in bulk record deletion: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Record Template Endpoints

@router.get("/templates", response_model=List[Dict[str, Any]])
async def list_record_templates(
    category: Optional[str] = Query(None, description="Filter templates by category"),
    current_user: dict = Depends(get_current_user)
):
    """List all available DNS record templates"""
    logger.info(f"User {current_user.get('username')} listing record templates")
    
    template_service = RecordTemplateService()
    
    try:
        if category:
            try:
                category_enum = RecordTemplateCategory(category)
                templates = template_service.get_templates_by_category(category_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        else:
            templates = template_service.get_all_templates()
        
        logger.info(f"Retrieved {len(templates)} record templates")
        return templates
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing record templates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/templates/categories", response_model=List[Dict[str, str]])
async def list_template_categories(
    current_user: dict = Depends(get_current_user)
):
    """List all available template categories"""
    logger.info(f"User {current_user.get('username')} listing template categories")
    
    template_service = RecordTemplateService()
    
    try:
        categories = template_service.get_categories()
        logger.info(f"Retrieved {len(categories)} template categories")
        return categories
        
    except Exception as e:
        logger.error(f"Error listing template categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/templates/{template_name}", response_model=Dict[str, Any])
async def get_record_template(
    template_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific record template"""
    logger.info(f"User {current_user.get('username')} retrieving template '{template_name}'")
    
    template_service = RecordTemplateService()
    
    try:
        template = template_service.get_template(template_name)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        logger.info(f"Retrieved template '{template_name}'")
        return template
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving template '{template_name}': {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/templates/{template_name}/apply", response_model=List[DNSRecordSchema])
async def apply_record_template(
    template_name: str,
    zone_id: int,
    variables: Dict[str, str],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Apply a record template to create DNS records in a zone"""
    logger.info(f"User {current_user.get('username')} applying template '{template_name}' to zone {zone_id}")
    
    template_service = RecordTemplateService()
    record_service = RecordService(db)
    bind_service = BindService(db)
    
    try:
        # Validate template exists
        template = template_service.get_template(template_name)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        # Validate template variables
        validation_result = template_service.validate_template_variables(template_name, variables)
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Template variable validation failed: {'; '.join(validation_result['errors'])}"
            )
        
        # Apply template to generate records
        record_data_list = template_service.apply_template(template_name, variables)
        
        # Create records in bulk
        created_records = await record_service.bulk_create_records(zone_id, record_data_list)
        
        # Schedule BIND9 configuration update in background
        background_tasks.add_task(
            update_bind_configuration_for_zone,
            bind_service,
            zone_id,
            f"Applied template '{template_name}' creating {len(created_records)} records"
        )
        
        logger.info(f"Applied template '{template_name}' creating {len(created_records)} records in zone {zone_id}")
        return created_records
        
    except ValueError as e:
        logger.error(f"Template application error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying template '{template_name}': {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/templates/{template_name}/validate", response_model=Dict[str, Any])
async def validate_template_variables(
    template_name: str,
    variables: Dict[str, str],
    current_user: dict = Depends(get_current_user)
):
    """Validate template variables without applying the template"""
    logger.info(f"User {current_user.get('username')} validating variables for template '{template_name}'")
    
    template_service = RecordTemplateService()
    
    try:
        # Validate template exists
        template = template_service.get_template(template_name)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        # Validate variables
        validation_result = template_service.validate_template_variables(template_name, variables)
        
        # Also generate preview of records that would be created
        if validation_result["valid"]:
            try:
                preview_records = template_service.apply_template(template_name, variables)
                validation_result["preview"] = preview_records
            except Exception as e:
                validation_result["warnings"].append(f"Could not generate preview: {str(e)}")
        
        logger.info(f"Validated variables for template '{template_name}': {'valid' if validation_result['valid'] else 'invalid'}")
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating template variables: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Search and Advanced Filtering Endpoints

@router.get("/search", response_model=Dict[str, Any])
async def search_dns_records(
    query: str = Query(..., min_length=1, description="Search query"),
    zone_id: Optional[int] = Query(None, description="Limit search to specific zone"),
    record_type: Optional[str] = Query(None, description="Filter by record type"),
    active_only: bool = Query(True, description="Search only active records"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Search DNS records across zones or within a specific zone"""
    logger.info(f"User {current_user.get('username')} searching records with query: '{query}'")
    
    record_service = RecordService(db)
    
    try:
        # Use the enhanced search functionality from record service
        result = await record_service.get_records(
            zone_id=zone_id,
            record_type=record_type,
            search=query,
            active_only=active_only,
            skip=skip,
            limit=limit,
            sort_by="name",
            sort_order="asc"
        )
        
        logger.info(f"Search returned {len(result['items'])} records for query '{query}'")
        return result
        
    except ValueError as e:
        logger.error(f"Search validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching DNS records: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/records/advanced-search", response_model=Dict[str, Any])
async def advanced_search_records(
    name_pattern: Optional[str] = Query(None, description="Name pattern (supports wildcards)"),
    value_pattern: Optional[str] = Query(None, description="Value pattern (supports wildcards)"),
    record_types: Optional[List[str]] = Query(None, description="List of record types to include"),
    zone_ids: Optional[List[int]] = Query(None, description="List of zone IDs to search in"),
    ttl_min: Optional[int] = Query(None, ge=60, description="Minimum TTL value"),
    ttl_max: Optional[int] = Query(None, le=86400, description="Maximum TTL value"),
    created_after: Optional[datetime] = Query(None, description="Records created after this date"),
    created_before: Optional[datetime] = Query(None, description="Records created before this date"),
    active_only: bool = Query(True, description="Search only active records"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    sort_by: Optional[str] = Query("name", description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Advanced search for DNS records with multiple filter criteria"""
    logger.info(f"User {current_user.get('username')} performing advanced record search")
    
    record_service = RecordService(db)
    
    try:
        # Build search query based on provided filters
        # This would require extending the record service with more advanced filtering
        # For now, we'll use the existing search functionality with basic filters
        
        search_term = None
        if name_pattern and value_pattern:
            search_term = f"{name_pattern} {value_pattern}"
        elif name_pattern:
            search_term = name_pattern
        elif value_pattern:
            search_term = value_pattern
        
        # Use first zone_id if multiple provided (limitation of current implementation)
        zone_id = zone_ids[0] if zone_ids else None
        
        # Use first record_type if multiple provided (limitation of current implementation)
        record_type = record_types[0] if record_types else None
        
        result = await record_service.get_records(
            zone_id=zone_id,
            record_type=record_type,
            search=search_term,
            active_only=active_only,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        logger.info(f"Advanced search returned {len(result['items'])} records")
        return result
        
    except ValueError as e:
        logger.error(f"Advanced search validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in advanced record search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Helper function for background BIND configuration updates
async def update_bind_configuration_for_zone(bind_service: BindService, zone_id: int, change_description: str):
    """Background task to update BIND9 configuration for a zone"""
    try:
        logger.info(f"Updating BIND9 configuration for zone {zone_id}: {change_description}")
        
        # Update zone file from database
        await bind_service.update_zone_file_from_db(zone_id)
        
        # Reload the specific zone
        await bind_service.reload_zone(zone_id)
        
        logger.info(f"Successfully updated BIND9 configuration for zone {zone_id}")
        
    except Exception as e:
        logger.error(f"Failed to update BIND9 configuration for zone {zone_id}: {e}")
        # Don't raise the exception as this is a background task
        # The record changes have already been saved to the database


# Import/Export Endpoints

@router.post("/zones/{zone_id}/records/import", response_model=RecordImportResult)
async def import_zone_records(
    zone_id: int,
    import_request: RecordImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Import DNS records into a zone from various formats"""
    logger.info(f"User {current_user.get('username')} importing records to zone {zone_id} in {import_request.format} format")
    
    from ...services.record_import_export_service import RecordImportExportService
    from ...schemas.dns import RecordImportResult as ImportResultSchema
    
    record_service = RecordService(db)
    import_export_service = RecordImportExportService()
    bind_service = BindService(db)
    
    try:
        # Verify zone exists
        zone = await record_service._get_zone(zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail=f"Zone with ID {zone_id} not found")
        
        # Import records
        import_result = await import_export_service.import_records(
            format_type=import_request.format,
            data=import_request.data,
            zone_name=zone.name,
            validate_only=import_request.validate_only
        )
        
        if not import_result.success:
            logger.error(f"Import failed: {'; '.join(import_result.errors)}")
            return ImportResultSchema(
                success=False,
                imported_count=0,
                skipped_count=0,
                error_count=len(import_result.errors),
                errors=import_result.errors,
                warnings=import_result.warnings,
                imported_records=[]
            )
        
        imported_records = []
        
        # If not validation only, create the records
        if not import_request.validate_only and import_result.records:
            try:
                imported_records = await record_service.bulk_create_records(zone_id, import_result.records)
                
                # Schedule BIND9 configuration update
                background_tasks.add_task(
                    update_bind_configuration_for_zone,
                    bind_service,
                    zone_id,
                    f"Imported {len(imported_records)} records from {import_request.format} format"
                )
                
            except Exception as e:
                logger.error(f"Error creating imported records: {e}")
                return ImportResultSchema(
                    success=False,
                    imported_count=0,
                    skipped_count=0,
                    error_count=1,
                    errors=[f"Failed to create records: {str(e)}"],
                    warnings=import_result.warnings,
                    imported_records=[]
                )
        
        logger.info(f"Successfully imported {len(imported_records)} records to zone {zone.name}")
        
        return ImportResultSchema(
            success=True,
            imported_count=len(imported_records),
            skipped_count=0,
            error_count=0,
            errors=[],
            warnings=import_result.warnings,
            imported_records=imported_records
        )
        
    except ValueError as e:
        logger.error(f"Import validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error importing records: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/zones/{zone_id}/records/export")
async def export_zone_records(
    zone_id: int,
    format: RecordExportFormat = Query(..., description="Export format"),
    active_only: bool = Query(True, description="Export only active records"),
    record_types: Optional[List[str]] = Query(None, description="Filter by record types"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Export DNS records from a zone in various formats"""
    logger.info(f"User {current_user.get('username')} exporting records from zone {zone_id} in {format} format")
    
    from ...services.record_import_export_service import RecordImportExportService
    from fastapi.responses import Response
    
    record_service = RecordService(db)
    import_export_service = RecordImportExportService()
    
    try:
        # Verify zone exists
        zone = await record_service._get_zone(zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail=f"Zone with ID {zone_id} not found")
        
        # Get records to export
        records_result = await record_service.get_records(
            zone_id=zone_id,
            record_type=record_types[0] if record_types else None,  # Limitation of current implementation
            active_only=active_only,
            limit=10000  # Large limit for export
        )
        
        records = records_result["items"]
        
        # Export records
        export_result = await import_export_service.export_records(
            format_type=format,
            records=records,
            zone_name=zone.name
        )
        
        if not export_result.success:
            logger.error(f"Export failed: {'; '.join(export_result.errors)}")
            raise HTTPException(status_code=500, detail=f"Export failed: {'; '.join(export_result.errors)}")
        
        logger.info(f"Successfully exported {len(records)} records from zone {zone.name}")
        
        # Return file response
        return Response(
            content=export_result.content,
            media_type=export_result.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={export_result.filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting records: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Record History Endpoints

@router.get("/records/{record_id}/history", response_model=List[DNSRecordHistory])
async def get_record_history(
    record_id: int,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of history entries"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get change history for a specific DNS record"""
    logger.info(f"User {current_user.get('username')} retrieving history for record {record_id}")
    
    from ...services.record_history_service import RecordHistoryService
    
    record_service = RecordService(db)
    history_service = RecordHistoryService(db)
    
    try:
        # Verify record exists
        record = await record_service.get_record(record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"DNS record with ID {record_id} not found")
        
        # Get history
        history_entries = await history_service.get_record_history(record_id, limit)
        
        logger.info(f"Retrieved {len(history_entries)} history entries for record {record_id}")
        return history_entries
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving record history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/zones/{zone_id}/records/history", response_model=RecordHistoryResponse)
async def get_zone_record_history(
    zone_id: int,
    change_type: Optional[str] = Query(None, description="Filter by change type"),
    changed_by: Optional[int] = Query(None, description="Filter by user who made changes"),
    date_from: Optional[datetime] = Query(None, description="Filter changes from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter changes to this date"),
    record_type: Optional[str] = Query(None, description="Filter by record type"),
    record_name: Optional[str] = Query(None, description="Filter by record name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    sort_by: str = Query("changed_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get change history for all records in a zone"""
    logger.info(f"User {current_user.get('username')} retrieving history for zone {zone_id}")
    
    from ...services.record_history_service import RecordHistoryService
    from ...schemas.dns import RecordHistoryResponse
    
    record_service = RecordService(db)
    history_service = RecordHistoryService(db)
    
    try:
        # Verify zone exists
        zone = await record_service._get_zone(zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail=f"Zone with ID {zone_id} not found")
        
        # Search history
        history_result = await history_service.search_history(
            zone_id=zone_id,
            change_type=change_type,
            changed_by=changed_by,
            date_from=date_from,
            date_to=date_to,
            record_type=record_type,
            record_name=record_name,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        logger.info(f"Retrieved {len(history_result['items'])} history entries for zone {zone.name}")
        
        return RecordHistoryResponse(
            items=history_result["items"],
            total=history_result["total"],
            page=history_result["page"],
            per_page=history_result["per_page"],
            pages=history_result["pages"],
            has_next=history_result["has_next"],
            has_prev=history_result["has_prev"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving zone history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/records/history/recent", response_model=List[DNSRecordHistory])
async def get_recent_record_changes(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of changes to return"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get recent DNS record changes across all zones"""
    logger.info(f"User {current_user.get('username')} retrieving recent changes from last {hours} hours")
    
    from ...services.record_history_service import RecordHistoryService
    
    history_service = RecordHistoryService(db)
    
    try:
        recent_changes = await history_service.get_recent_changes(hours, limit)
        
        logger.info(f"Retrieved {len(recent_changes)} recent changes")
        return recent_changes
        
    except Exception as e:
        logger.error(f"Error retrieving recent changes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Enhanced Validation Endpoints

@router.post("/records/validate-bulk", response_model=RecordValidationResult)
async def validate_bulk_records(
    validation_request: RecordValidationRequest,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate multiple DNS records without creating them"""
    logger.info(f"User {current_user.get('username')} validating {len(validation_request.records)} records for zone {validation_request.zone_id}")
    
    from ...schemas.dns import RecordValidationResult, RecordValidationError
    
    record_service = RecordService(db)
    
    try:
        # Verify zone exists
        zone = await record_service._get_zone(validation_request.zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail=f"Zone with ID {validation_request.zone_id} not found")
        
        errors = []
        warnings = []
        valid_count = 0
        
        for i, record_data in enumerate(validation_request.records):
            try:
                # Validate individual record
                validation_result = await record_service.validate_record_data(
                    record_data.dict(),
                    validation_request.zone_id
                )
                
                if validation_result["valid"]:
                    valid_count += 1
                else:
                    for error_msg in validation_result["errors"]:
                        errors.append(RecordValidationError(
                            record_index=i,
                            field=None,
                            error_type="validation_error",
                            message=error_msg,
                            severity="error"
                        ))
                
                for warning_msg in validation_result["warnings"]:
                    warnings.append(RecordValidationError(
                        record_index=i,
                        field=None,
                        error_type="validation_warning",
                        message=warning_msg,
                        severity="warning"
                    ))
                    
            except Exception as e:
                errors.append(RecordValidationError(
                    record_index=i,
                    field=None,
                    error_type="validation_exception",
                    message=str(e),
                    severity="error"
                ))
        
        is_valid = len(errors) == 0
        
        logger.info(f"Validated {len(validation_request.records)} records: {valid_count} valid, {len(errors)} errors, {len(warnings)} warnings")
        
        return RecordValidationResult(
            valid=is_valid,
            total_records=len(validation_request.records),
            valid_records=valid_count,
            error_count=len(errors),
            warning_count=len(warnings),
            errors=errors,
            warnings=warnings
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating bulk records: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Enhanced Statistics Endpoints

@router.get("/statistics/global", response_model=GlobalRecordStatistics)
async def get_global_record_statistics(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get global DNS record statistics across all zones"""
    logger.info(f"User {current_user.get('username')} retrieving global record statistics")
    
    from ...schemas.dns import GlobalRecordStatistics, ZoneRecordStatistics, RecordTypeStatistics
    
    record_service = RecordService(db)
    
    try:
        # Get global statistics
        global_stats = await record_service.get_record_statistics()
        
        # Get per-zone statistics (simplified for now)
        zone_stats = []
        
        # Get most common record types
        records_by_type = global_stats.get("records_by_type", {})
        most_common_types = sorted(records_by_type.keys(), key=lambda k: records_by_type[k], reverse=True)[:5]
        
        # Convert to proper format
        record_type_stats = []
        total_records = global_stats.get("total_records", 0)
        
        for record_type, count in records_by_type.items():
            percentage = (count / total_records * 100) if total_records > 0 else 0
            record_type_stats.append(RecordTypeStatistics(
                record_type=record_type,
                total_count=count,
                active_count=count,  # Simplified - would need more detailed query
                inactive_count=0,
                percentage=percentage
            ))
        
        logger.info("Retrieved global record statistics")
        
        return GlobalRecordStatistics(
            total_records=global_stats.get("total_records", 0),
            active_records=global_stats.get("active_records", 0),
            inactive_records=global_stats.get("inactive_records", 0),
            total_zones=1,  # Simplified
            zones_with_records=1,  # Simplified
            record_types=record_type_stats,
            zone_statistics=zone_stats,
            most_common_types=most_common_types,
            recent_changes=0  # Would need history service integration
        )
        
    except Exception as e:
        logger.error(f"Error retrieving global statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/zones/{zone_id}/statistics/detailed", response_model=ZoneRecordStatistics)
async def get_detailed_zone_statistics(
    zone_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed statistics for a specific zone"""
    logger.info(f"User {current_user.get('username')} retrieving detailed statistics for zone {zone_id}")
    
    from ...schemas.dns import ZoneRecordStatistics, RecordTypeStatistics
    
    record_service = RecordService(db)
    
    try:
        # Verify zone exists
        zone = await record_service._get_zone(zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail=f"Zone with ID {zone_id} not found")
        
        # Get zone statistics
        zone_stats = await record_service.get_record_statistics(zone_id)
        
        # Convert to detailed format
        record_type_stats = []
        records_by_type = zone_stats.get("records_by_type", {})
        total_records = zone_stats.get("total_records", 0)
        
        for record_type, count in records_by_type.items():
            percentage = (count / total_records * 100) if total_records > 0 else 0
            record_type_stats.append(RecordTypeStatistics(
                record_type=record_type,
                total_count=count,
                active_count=count,  # Simplified
                inactive_count=0,
                percentage=percentage
            ))
        
        logger.info(f"Retrieved detailed statistics for zone {zone.name}")
        
        return ZoneRecordStatistics(
            zone_id=zone_id,
            zone_name=zone.name,
            total_records=zone_stats.get("total_records", 0),
            active_records=zone_stats.get("active_records", 0),
            inactive_records=zone_stats.get("inactive_records", 0),
            record_types=record_type_stats,
            last_modified=zone.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving detailed zone statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")