"""
Zone service with authentication integration
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from .base_service import BaseService
from ..models.dns import Zone, DNSRecord
from ..core.auth_context import get_current_user_id, track_user_action
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class ZoneService(BaseService[Zone]):
    """Zone service with authentication and audit logging"""
    
    def __init__(self, db: Session | AsyncSession):
        super().__init__(db, Zone)
    
    async def create_zone(self, zone_data: Dict[str, Any]) -> Zone:
        """Create a new DNS zone with user tracking"""
        logger.info(f"Creating zone: {zone_data.get('name')}")
        
        # Validate zone data
        if not zone_data.get('name'):
            raise ValueError("Zone name is required")
        if not zone_data.get('email'):
            raise ValueError("Zone email is required")
        
        # Set default values
        zone_data.setdefault('zone_type', 'master')
        zone_data.setdefault('is_active', True)
        
        # Create the zone
        zone = await self.create(zone_data, track_action=True)
        
        logger.info(f"Created zone {zone.name} with ID {zone.id}")
        return zone
    
    async def update_zone(self, zone_id: int, zone_data: Dict[str, Any]) -> Optional[Zone]:
        """Update a DNS zone with user tracking"""
        logger.info(f"Updating zone ID: {zone_id}")
        
        zone = await self.update(zone_id, zone_data, track_action=True)
        
        if zone:
            logger.info(f"Updated zone {zone.name}")
        else:
            logger.warning(f"Zone {zone_id} not found for update")
        
        return zone
    
    async def delete_zone(self, zone_id: int) -> bool:
        """Delete a DNS zone with user tracking"""
        logger.info(f"Deleting zone ID: {zone_id}")
        
        # Get zone info before deletion for logging
        zone = await self.get_by_id(zone_id)
        if not zone:
            logger.warning(f"Zone {zone_id} not found for deletion")
            return False
        
        zone_name = zone.name
        success = await self.delete(zone_id, track_action=True)
        
        if success:
            logger.info(f"Deleted zone {zone_name}")
        
        return success
    
    async def get_zone(self, zone_id: int) -> Optional[Zone]:
        """Get a zone by ID"""
        return await self.get_by_id(zone_id)
    
    async def get_zones(self, skip: int = 0, limit: int = 100, 
                       zone_type: Optional[str] = None, 
                       active_only: bool = True) -> List[Zone]:
        """Get zones with filtering"""
        filters = {}
        
        if zone_type:
            filters['zone_type'] = zone_type
        if active_only:
            filters['is_active'] = True
        
        return await self.get_all(skip=skip, limit=limit, filters=filters)
    
    async def get_zones_by_user(self, user_id: int, created_only: bool = False) -> List[Zone]:
        """Get zones created or updated by a specific user"""
        return await self.get_by_user(user_id, created_only=created_only)
    
    async def get_zone_with_records(self, zone_id: int) -> Optional[Dict[str, Any]]:
        """Get a zone with its DNS records"""
        zone = await self.get_by_id(zone_id)
        if not zone:
            return None
        
        # Get records for this zone
        if self.is_async:
            result = await self.db.execute(
                select(DNSRecord).filter(DNSRecord.zone_id == zone_id, DNSRecord.is_active == True)
            )
            records = result.scalars().all()
        else:
            records = self.db.query(DNSRecord).filter(
                DNSRecord.zone_id == zone_id, 
                DNSRecord.is_active == True
            ).all()
        
        return {
            "zone": zone,
            "records": records,
            "record_count": len(records)
        }
    
    async def get_zone_statistics(self, zone_id: int) -> Optional[Dict[str, Any]]:
        """Get statistics for a zone"""
        zone = await self.get_by_id(zone_id)
        if not zone:
            return None
        
        # Count records by type
        if self.is_async:
            result = await self.db.execute(
                select(DNSRecord.record_type, func.count(DNSRecord.id))
                .filter(DNSRecord.zone_id == zone_id, DNSRecord.is_active == True)
                .group_by(DNSRecord.record_type)
            )
            record_counts = dict(result.fetchall())
            
            # Get total record count
            result = await self.db.execute(
                select(func.count(DNSRecord.id))
                .filter(DNSRecord.zone_id == zone_id, DNSRecord.is_active == True)
            )
            total_records = result.scalar()
        else:
            record_counts = dict(
                self.db.query(DNSRecord.record_type, func.count(DNSRecord.id))
                .filter(DNSRecord.zone_id == zone_id, DNSRecord.is_active == True)
                .group_by(DNSRecord.record_type)
                .all()
            )
            
            total_records = self.db.query(func.count(DNSRecord.id)).filter(
                DNSRecord.zone_id == zone_id, 
                DNSRecord.is_active == True
            ).scalar()
        
        return {
            "zone_id": zone_id,
            "zone_name": zone.name,
            "zone_type": zone.zone_type,
            "is_active": zone.is_active,
            "total_records": total_records,
            "record_counts": record_counts,
            "created_at": zone.created_at,
            "updated_at": zone.updated_at,
            "created_by": zone.created_by,
            "updated_by": zone.updated_by
        }
    
    async def toggle_zone_status(self, zone_id: int) -> Optional[Zone]:
        """Toggle zone active status"""
        zone = await self.get_by_id(zone_id)
        if not zone:
            return None
        
        new_status = not zone.is_active
        updated_zone = await self.update(zone_id, {"is_active": new_status}, track_action=True)
        
        if updated_zone:
            status_text = "activated" if new_status else "deactivated"
            logger.info(f"Zone {zone.name} {status_text}")
            
            # Track specific action
            track_user_action(
                action=f"zone_{'activate' if new_status else 'deactivate'}",
                resource_type="zone",
                resource_id=str(zone_id),
                details=f"Zone {zone.name} {status_text}",
                db=self.db
            )
        
        return updated_zone
    
    async def validate_zone_data(self, zone_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate zone data and return validation results"""
        errors = []
        warnings = []
        
        # Required fields
        if not zone_data.get('name'):
            errors.append("Zone name is required")
        elif len(zone_data['name']) > 255:
            errors.append("Zone name must be 255 characters or less")
        
        if not zone_data.get('email'):
            errors.append("Zone email is required")
        elif '@' not in zone_data['email']:
            errors.append("Zone email must be a valid email address")
        
        # Zone type validation
        valid_types = ['master', 'slave', 'forward']
        if zone_data.get('zone_type') and zone_data['zone_type'] not in valid_types:
            errors.append(f"Zone type must be one of: {', '.join(valid_types)}")
        
        # SOA record validation
        if zone_data.get('refresh') and (zone_data['refresh'] < 300 or zone_data['refresh'] > 86400):
            errors.append("Refresh interval must be between 300 and 86400 seconds")
        
        if zone_data.get('retry') and (zone_data['retry'] < 300 or zone_data['retry'] > 86400):
            errors.append("Retry interval must be between 300 and 86400 seconds")
        
        if zone_data.get('expire') and (zone_data['expire'] < 86400 or zone_data['expire'] > 2419200):
            errors.append("Expire interval must be between 86400 and 2419200 seconds")
        
        if zone_data.get('minimum') and (zone_data['minimum'] < 300 or zone_data['minimum'] > 86400):
            errors.append("Minimum TTL must be between 300 and 86400 seconds")
        
        # Check for duplicate zone name
        if zone_data.get('name'):
            if self.is_async:
                result = await self.db.execute(
                    select(func.count(Zone.id)).filter(Zone.name == zone_data['name'])
                )
                existing_count = result.scalar()
            else:
                existing_count = self.db.query(func.count(Zone.id)).filter(
                    Zone.name == zone_data['name']
                ).scalar()
            
            if existing_count > 0:
                errors.append(f"Zone '{zone_data['name']}' already exists")
        
        # Warnings
        if zone_data.get('zone_type') == 'slave' and not zone_data.get('master_servers'):
            warnings.append("Slave zones should specify master servers")
        
        if zone_data.get('zone_type') == 'forward' and not zone_data.get('forwarders'):
            warnings.append("Forward zones should specify forwarder servers")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }