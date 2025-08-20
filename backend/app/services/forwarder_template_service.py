"""
Forwarder template service for managing reusable forwarder configurations
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, asc

from .base_service import BaseService
from ..models.dns import ForwarderTemplate, Forwarder
from ..core.auth_context import get_current_user_id, track_user_action
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class ForwarderTemplateService(BaseService[ForwarderTemplate]):
    """Service for managing forwarder templates"""
    
    def __init__(self, db: Session | AsyncSession):
        super().__init__(db, ForwarderTemplate)
    
    async def create_template(self, template_data: Dict[str, Any]) -> ForwarderTemplate:
        """Create a new forwarder template"""
        logger.info(f"Creating forwarder template: {template_data.get('name')}")
        
        # Validate template data
        validation_result = await self.validate_template_data(template_data)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid template data: {', '.join(validation_result['errors'])}")
        
        # Set default values
        template_data.setdefault('is_system_template', False)
        template_data.setdefault('usage_count', 0)
        template_data.setdefault('default_priority', 5)
        template_data.setdefault('default_health_check_enabled', True)
        
        # Create the template
        template = await self.create(template_data, track_action=True)
        
        logger.info(f"Created forwarder template {template.name} with ID {template.id}")
        return template
    
    async def update_template(self, template_id: int, template_data: Dict[str, Any]) -> Optional[ForwarderTemplate]:
        """Update a forwarder template"""
        logger.info(f"Updating forwarder template ID: {template_id}")
        
        # Get existing template for validation
        existing_template = await self.get_by_id(template_id)
        if not existing_template:
            logger.warning(f"Template {template_id} not found for update")
            return None
        
        # Validate template data (partial validation for updates)
        validation_result = await self.validate_template_data(template_data, template_id)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid template data: {', '.join(validation_result['errors'])}")
        
        # Update the template
        template = await self.update(template_id, template_data, track_action=True)
        
        if template:
            logger.info(f"Updated forwarder template {template.name}")
        
        return template
    
    async def delete_template(self, template_id: int) -> bool:
        """Delete a forwarder template"""
        logger.info(f"Deleting forwarder template ID: {template_id}")
        
        # Get template info before deletion for logging
        template = await self.get_by_id(template_id)
        if not template:
            logger.warning(f"Template {template_id} not found for deletion")
            return False
        
        # Check if template is in use
        usage_count = await self.get_template_usage_count(template_id)
        if usage_count > 0:
            logger.warning(f"Cannot delete template {template.name} - it is in use by {usage_count} forwarders")
            raise ValueError(f"Cannot delete template '{template.name}' - it is currently in use by {usage_count} forwarders")
        
        template_name = template.name
        success = await self.delete(template_id, track_action=True)
        
        if success:
            logger.info(f"Deleted forwarder template {template_name}")
        
        return success
    
    async def get_template(self, template_id: int) -> Optional[ForwarderTemplate]:
        """Get a template by ID"""
        return await self.get_by_id(template_id)
    
    async def get_templates(self, skip: int = 0, limit: int = 100,
                          forwarder_type: Optional[str] = None,
                          system_only: Optional[bool] = None,
                          search: Optional[str] = None,
                          sort_by: Optional[str] = None,
                          sort_order: str = "asc") -> Dict[str, Any]:
        """Get templates with filtering and pagination"""
        
        # Build the base query
        if self.is_async:
            query = select(ForwarderTemplate)
            count_query = select(func.count(ForwarderTemplate.id))
        else:
            query = self.db.query(ForwarderTemplate)
            count_query = self.db.query(func.count(ForwarderTemplate.id))
        
        # Apply filters
        conditions = []
        
        if forwarder_type:
            conditions.append(ForwarderTemplate.forwarder_type == forwarder_type)
        
        if system_only is not None:
            conditions.append(ForwarderTemplate.is_system_template == system_only)
        
        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            search_conditions = [
                ForwarderTemplate.name.ilike(search_term)
            ]
            # Add description search if the field exists
            if hasattr(ForwarderTemplate, 'description') and ForwarderTemplate.description is not None:
                search_conditions.append(ForwarderTemplate.description.ilike(search_term))
            
            conditions.append(or_(*search_conditions))
        
        # Apply all conditions
        if conditions:
            if self.is_async:
                query = query.filter(and_(*conditions))
                count_query = count_query.filter(and_(*conditions))
            else:
                query = query.filter(and_(*conditions))
                count_query = count_query.filter(and_(*conditions))
        
        # Apply sorting
        if sort_by and hasattr(ForwarderTemplate, sort_by):
            sort_column = getattr(ForwarderTemplate, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            # Default sorting by name
            query = query.order_by(asc(ForwarderTemplate.name))
        
        # Get total count
        if self.is_async:
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()
        else:
            total = count_query.scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        if self.is_async:
            result = await self.db.execute(query)
            templates = result.scalars().all()
        else:
            templates = query.all()
        
        # Calculate pagination info
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1
        
        return {
            "items": templates,
            "total": total,
            "page": current_page,
            "per_page": limit,
            "pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1
        }
    
    async def get_template_usage_count(self, template_id: int) -> int:
        """Get the number of forwarders created from a template"""
        template = await self.get_by_id(template_id)
        if not template:
            return 0
        
        if self.is_async:
            result = await self.db.execute(
                select(func.count(Forwarder.id))
                .filter(Forwarder.created_from_template == template.name)
            )
            count = result.scalar()
        else:
            count = self.db.query(func.count(Forwarder.id)).filter(
                Forwarder.created_from_template == template.name
            ).scalar()
        
        return count or 0
    
    async def increment_template_usage(self, template_id: int) -> None:
        """Increment the usage count for a template"""
        template = await self.get_by_id(template_id)
        if template:
            await self.update(template_id, {"usage_count": template.usage_count + 1})
    
    async def create_forwarder_from_template(self, template_id: int, forwarder_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a forwarder configuration from a template"""
        logger.info(f"Creating forwarder from template ID: {template_id}")
        
        template = await self.get_by_id(template_id)
        if not template:
            raise ValueError(f"Template with ID {template_id} not found")
        
        # Start with template defaults
        config = {
            "forwarder_type": template.forwarder_type,
            "domains": template.default_domains or [],
            "servers": template.default_servers or [],
            "priority": template.default_priority,
            "group_name": template.default_group_name,
            "health_check_enabled": template.default_health_check_enabled,
            "description": template.description,
            "created_from_template": template.name
        }
        
        # Override with provided data
        config.update({k: v for k, v in forwarder_data.items() if v is not None})
        
        # Increment template usage count
        await self.increment_template_usage(template_id)
        
        logger.info(f"Generated forwarder configuration from template {template.name}")
        return config
    
    async def get_system_templates(self) -> List[ForwarderTemplate]:
        """Get all system templates"""
        result = await self.get_templates(system_only=True, limit=1000)
        return result["items"]
    
    async def get_user_templates(self, user_id: int) -> List[ForwarderTemplate]:
        """Get templates created by a specific user"""
        return await self.get_by_user(user_id, created_only=True)
    
    async def validate_template_data(self, template_data: Dict[str, Any], template_id: Optional[int] = None) -> Dict[str, Any]:
        """Validate template data"""
        errors = []
        warnings = []
        
        # Validate required fields
        if not template_data.get("name"):
            errors.append("Template name is required")
        elif len(template_data["name"]) > 255:
            errors.append("Template name cannot exceed 255 characters")
        
        if not template_data.get("forwarder_type"):
            errors.append("Forwarder type is required")
        elif template_data["forwarder_type"] not in ["active_directory", "intranet", "public"]:
            errors.append("Invalid forwarder type")
        
        # Check for duplicate template names (excluding current template if updating)
        if template_data.get("name"):
            if self.is_async:
                query = select(ForwarderTemplate).filter(ForwarderTemplate.name == template_data["name"])
                if template_id:
                    query = query.filter(ForwarderTemplate.id != template_id)
                result = await self.db.execute(query)
                existing = result.scalar_one_or_none()
            else:
                query = self.db.query(ForwarderTemplate).filter(ForwarderTemplate.name == template_data["name"])
                if template_id:
                    query = query.filter(ForwarderTemplate.id != template_id)
                existing = query.first()
            
            if existing:
                errors.append(f"Template name '{template_data['name']}' already exists")
        
        # Validate default domains if provided
        if template_data.get("default_domains"):
            if not isinstance(template_data["default_domains"], list):
                errors.append("Default domains must be a list")
            elif len(template_data["default_domains"]) == 0:
                warnings.append("Template has no default domains")
        
        # Validate default servers if provided
        if template_data.get("default_servers"):
            if not isinstance(template_data["default_servers"], list):
                errors.append("Default servers must be a list")
            elif len(template_data["default_servers"]) == 0:
                warnings.append("Template has no default servers")
        
        # Validate priority ranges
        if template_data.get("default_priority") is not None:
            priority = template_data["default_priority"]
            if not isinstance(priority, int) or priority < 1 or priority > 10:
                errors.append("Default priority must be between 1 and 10")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def get_template_statistics(self, template_id: int) -> Dict[str, Any]:
        """Get statistics for a specific template"""
        template = await self.get_by_id(template_id)
        if not template:
            return {}
        
        # Get usage count
        usage_count = await self.get_template_usage_count(template_id)
        
        # Get forwarders created from this template
        if self.is_async:
            result = await self.db.execute(
                select(Forwarder)
                .filter(Forwarder.created_from_template == template.name)
                .order_by(desc(Forwarder.created_at))
                .limit(10)
            )
            recent_forwarders = result.scalars().all()
        else:
            recent_forwarders = self.db.query(Forwarder).filter(
                Forwarder.created_from_template == template.name
            ).order_by(desc(Forwarder.created_at)).limit(10).all()
        
        return {
            "template_id": template_id,
            "template_name": template.name,
            "template_type": template.forwarder_type,
            "is_system_template": template.is_system_template,
            "usage_count": usage_count,
            "stored_usage_count": template.usage_count,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
            "recent_forwarders": [
                {
                    "id": f.id,
                    "name": f.name,
                    "created_at": f.created_at,
                    "is_active": f.is_active
                }
                for f in recent_forwarders
            ]
        }
    
    async def create_system_templates(self) -> List[ForwarderTemplate]:
        """Create default system templates"""
        logger.info("Creating default system templates")
        
        system_templates = [
            {
                "name": "Active Directory",
                "description": "Template for Active Directory DNS forwarding",
                "forwarder_type": "active_directory",
                "default_domains": ["corp.local", "ad.local"],
                "default_servers": [
                    {"ip": "192.168.1.10", "port": 53, "priority": 1, "weight": 1, "enabled": True},
                    {"ip": "192.168.1.11", "port": 53, "priority": 2, "weight": 1, "enabled": True}
                ],
                "default_priority": 1,
                "default_group_name": "Active Directory",
                "default_health_check_enabled": True,
                "is_system_template": True
            },
            {
                "name": "Internal Network",
                "description": "Template for internal network DNS forwarding",
                "forwarder_type": "intranet",
                "default_domains": ["internal.local", "intranet.local"],
                "default_servers": [
                    {"ip": "10.0.0.1", "port": 53, "priority": 1, "weight": 1, "enabled": True}
                ],
                "default_priority": 3,
                "default_group_name": "Internal",
                "default_health_check_enabled": True,
                "is_system_template": True
            },
            {
                "name": "Public DNS",
                "description": "Template for public DNS forwarding",
                "forwarder_type": "public",
                "default_domains": ["*"],
                "default_servers": [
                    {"ip": "8.8.8.8", "port": 53, "priority": 1, "weight": 1, "enabled": True},
                    {"ip": "8.8.4.4", "port": 53, "priority": 2, "weight": 1, "enabled": True}
                ],
                "default_priority": 10,
                "default_group_name": "Public",
                "default_health_check_enabled": True,
                "is_system_template": True
            }
        ]
        
        created_templates = []
        for template_data in system_templates:
            try:
                # Check if template already exists
                if self.is_async:
                    result = await self.db.execute(
                        select(ForwarderTemplate).filter(ForwarderTemplate.name == template_data["name"])
                    )
                    existing = result.scalar_one_or_none()
                else:
                    existing = self.db.query(ForwarderTemplate).filter(
                        ForwarderTemplate.name == template_data["name"]
                    ).first()
                
                if not existing:
                    template = await self.create_template(template_data)
                    created_templates.append(template)
                    logger.info(f"Created system template: {template.name}")
                else:
                    logger.info(f"System template already exists: {template_data['name']}")
                    created_templates.append(existing)
                    
            except Exception as e:
                logger.error(f"Failed to create system template {template_data['name']}: {str(e)}")
        
        return created_templates