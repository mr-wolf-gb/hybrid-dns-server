"""
Forwarder templates management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...schemas.dns import (
    ForwarderTemplateCreate,
    ForwarderTemplateUpdate,
    ForwarderTemplate as ForwarderTemplateSchema,
    ForwarderFromTemplate
)
from ...services.forwarder_template_service import ForwarderTemplateService

router = APIRouter()

@router.get("/", response_model=List[ForwarderTemplateSchema])
async def list_forwarder_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    forwarder_type: Optional[str] = Query(None),
    system_only: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("asc"),
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """List all forwarder templates with filtering and pagination"""
    template_service = ForwarderTemplateService(db)
    result = await template_service.get_templates(
        skip=skip,
        limit=limit,
        forwarder_type=forwarder_type,
        system_only=system_only,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return result["items"]

@router.post("/", response_model=ForwarderTemplateSchema)
async def create_forwarder_template(
    template_data: ForwarderTemplateCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a new forwarder template"""
    template_service = ForwarderTemplateService(db)
    template = await template_service.create_template(template_data.dict())
    return template

@router.get("/{template_id}", response_model=ForwarderTemplateSchema)
async def get_forwarder_template(
    template_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific forwarder template"""
    template_service = ForwarderTemplateService(db)
    template = await template_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.put("/{template_id}", response_model=ForwarderTemplateSchema)
async def update_forwarder_template(
    template_id: int,
    template_data: ForwarderTemplateUpdate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Update a forwarder template"""
    template_service = ForwarderTemplateService(db)
    template = await template_service.update_template(template_id, template_data.dict(exclude_unset=True))
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.delete("/{template_id}")
async def delete_forwarder_template(
    template_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Delete a forwarder template"""
    template_service = ForwarderTemplateService(db)
    
    try:
        success = await template_service.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"message": "Template deleted successfully"}

@router.get("/{template_id}/usage")
async def get_template_usage(
    template_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get usage count for a template"""
    template_service = ForwarderTemplateService(db)
    
    # Check if template exists
    template = await template_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    usage_count = await template_service.get_template_usage_count(template_id)
    return {"template_id": template_id, "usage_count": usage_count}

@router.get("/{template_id}/statistics")
async def get_template_statistics(
    template_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive statistics for a template"""
    template_service = ForwarderTemplateService(db)
    
    # Check if template exists
    template = await template_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    statistics = await template_service.get_template_statistics(template_id)
    return statistics

@router.get("/system/list")
async def get_system_templates(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get all system templates"""
    template_service = ForwarderTemplateService(db)
    templates = await template_service.get_system_templates()
    return templates

@router.post("/system/create")
async def create_system_templates(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create default system templates"""
    template_service = ForwarderTemplateService(db)
    templates = await template_service.create_system_templates()
    return {"created_count": len(templates), "templates": templates}

@router.get("/user/{user_id}")
async def get_user_templates(
    user_id: int,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get templates created by a specific user"""
    template_service = ForwarderTemplateService(db)
    templates = await template_service.get_user_templates(user_id)
    return templates

@router.post("/{template_id}/use")
async def create_forwarder_from_template(
    template_id: int,
    forwarder_data: ForwarderFromTemplate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Create a forwarder configuration from a template"""
    template_service = ForwarderTemplateService(db)
    
    # Check if template exists
    template = await template_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Generate forwarder configuration
    config = await template_service.create_forwarder_from_template(
        template_id, 
        forwarder_data.dict(exclude_unset=True, exclude={"template_id"})
    )
    
    return {
        "template_id": template_id,
        "template_name": template.name,
        "forwarder_config": config
    }

@router.post("/validate")
async def validate_template_data(
    template_data: ForwarderTemplateCreate,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Validate template data without creating the template"""
    template_service = ForwarderTemplateService(db)
    validation_result = await template_service.validate_template_data(template_data.dict())
    return validation_result