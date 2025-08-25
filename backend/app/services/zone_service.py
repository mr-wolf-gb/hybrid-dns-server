"""
Zone service with authentication integration and event broadcasting
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from .base_service import BaseService
from ..models.dns import Zone, DNSRecord
from ..core.auth_context import get_current_user_id, track_user_action
from ..core.logging_config import get_logger
from .enhanced_event_service import get_enhanced_event_service
from ..websocket.event_types import EventType, EventPriority, EventCategory, create_event

logger = get_logger(__name__)


class ZoneService(BaseService[Zone]):
    """Zone service with authentication, audit logging, and event broadcasting"""
    
    def __init__(self, db: Session | AsyncSession):
        super().__init__(db, Zone)
        self.event_service = get_enhanced_event_service()
    
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
        
        # Generate serial number if not provided
        if not zone_data.get('serial'):
            zone_data['serial'] = await self.generate_serial_number()
        
        # Generate file path if not provided
        if not zone_data.get('file_path'):
            zone_data['file_path'] = await self.validate_zone_file_path(
                zone_data['name'], 
                zone_data['zone_type']
            )
        
        # Create the zone
        zone = await self.create(zone_data, track_action=True)
        
        # Emit zone creation event
        await self._emit_zone_event(
            event_type=EventType.DNS_ZONE_CREATED,
            zone=zone,
            action="create",
            details={
                "zone_name": zone.name,
                "zone_type": zone.zone_type,
                "serial": zone.serial,
                "is_active": zone.is_active
            }
        )
        
        logger.info(f"Created zone {zone.name} with ID {zone.id} and serial {zone.serial}")
        return zone
    
    async def update_zone(self, zone_id: int, zone_data: Dict[str, Any], auto_increment_serial: bool = True) -> Optional[Zone]:
        """Update a DNS zone with user tracking and automatic serial increment"""
        logger.info(f"Updating zone ID: {zone_id}")
        
        # Auto-increment serial number if zone data changes and not explicitly provided
        if auto_increment_serial and 'serial' not in zone_data:
            # Check if this is a significant change that should increment serial
            if await self.should_increment_serial(zone_data):
                zone_data['serial'] = await self.generate_serial_number(zone_id)
                logger.info(f"Auto-incrementing serial for zone {zone_id} to {zone_data['serial']}")
        
        zone = await self.update(zone_id, zone_data, track_action=True)
        
        if zone:
            # Emit zone update event
            await self._emit_zone_event(
                event_type=EventType.DNS_ZONE_UPDATED,
                zone=zone,
                action="update",
                details={
                    "zone_name": zone.name,
                    "zone_type": zone.zone_type,
                    "serial": zone.serial,
                    "is_active": zone.is_active,
                    "updated_fields": list(zone_data.keys()),
                    "auto_increment_serial": auto_increment_serial
                }
            )
            logger.info(f"Updated zone {zone.name} (serial: {zone.serial})")
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
        zone_type = zone.zone_type
        success = await self.delete(zone_id, track_action=True)
        
        if success:
            # Emit zone deletion event
            await self._emit_zone_event(
                event_type=EventType.DNS_ZONE_DELETED,
                zone=None,  # Zone is deleted, so pass None
                action="delete",
                details={
                    "zone_id": zone_id,
                    "zone_name": zone_name,
                    "zone_type": zone_type
                }
            )
            logger.info(f"Deleted zone {zone_name}")
        
        return success
    
    async def get_zone(self, zone_id: int) -> Optional[Zone]:
        """Get a zone by ID"""
        return await self.get_by_id(zone_id)
    
    async def get_zones(self, skip: int = 0, limit: int = 100, 
                       zone_type: Optional[str] = None, 
                       active_only: bool = True,
                       search: Optional[str] = None,
                       sort_by: Optional[str] = None,
                       sort_order: str = "asc") -> Dict[str, Any]:
        """Get zones with enhanced filtering and pagination"""
        from sqlalchemy import func, or_, asc, desc
        
        # Build the base query
        if self.is_async:
            query = select(Zone)
            count_query = select(func.count(Zone.id))
        else:
            query = self.db.query(Zone)
            count_query = self.db.query(func.count(Zone.id))
        
        # Apply filters
        conditions = []
        
        if zone_type:
            conditions.append(Zone.zone_type == zone_type)
        
        if active_only:
            conditions.append(Zone.is_active == True)
        
        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            search_conditions = [
                Zone.name.ilike(search_term)
            ]
            # Add description search if the field exists
            if hasattr(Zone, 'description') and Zone.description is not None:
                search_conditions.append(Zone.description.ilike(search_term))
            
            conditions.append(or_(*search_conditions))
        
        # Apply all conditions
        if conditions:
            if self.is_async:
                query = query.filter(*conditions)
                count_query = count_query.filter(*conditions)
            else:
                query = query.filter(*conditions)
                count_query = count_query.filter(*conditions)
        
        # Apply sorting
        if sort_by and hasattr(Zone, sort_by):
            sort_column = getattr(Zone, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            # Default sorting by name
            query = query.order_by(asc(Zone.name))
        
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
            zones = result.scalars().all()
        else:
            zones = query.all()
        
        # Calculate pagination info
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1
        
        return {
            "items": zones,
            "total": total,
            "page": current_page,
            "per_page": limit,
            "pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1
        }
    
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
    
    async def get_zone_records(self, zone_id: int) -> List[Any]:
        """Get all DNS records for a zone"""
        from ..models.dns import DNSRecord
        
        if self.is_async:
            # For async database operations
            result = await self.db.execute(
                select(DNSRecord).where(DNSRecord.zone_id == zone_id)
            )
            return result.scalars().all()
        else:
            return self.db.query(DNSRecord).filter(DNSRecord.zone_id == zone_id).all()
    
    async def get_zone_statistics(self, zone_id: int) -> Optional[Dict[str, Any]]:
        """Get statistics for a zone including serial number information and health status"""
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
        
        # Get serial number information
        serial_info = None
        if zone.serial:
            serial_info = await self.validate_serial_number(zone.serial)
        
        # Get health information
        health_data = await self.get_zone_health(zone_id)
        health_status = health_data.get("status", "unknown") if health_data else "unknown"
        last_check = health_data.get("last_check") if health_data else None
        
        # Use updated_at as last_modified
        last_modified = zone.updated_at.isoformat() if zone.updated_at else None
        
        return {
            "zone_id": zone_id,
            "zone_name": zone.name,
            "zone_type": zone.zone_type,
            "is_active": zone.is_active,
            "record_count": total_records,  # Match frontend interface
            "total_records": total_records,  # Keep for backward compatibility
            "record_counts": record_counts,
            "serial": zone.serial,
            "serial_info": serial_info,
            "refresh": zone.refresh,
            "retry": zone.retry,
            "expire": zone.expire,
            "minimum": zone.minimum,
            "created_at": zone.created_at,
            "updated_at": zone.updated_at,
            "last_modified": last_modified,  # Add for frontend compatibility
            "last_check": last_check,  # Add for frontend compatibility
            "health_status": health_status,  # Add for frontend compatibility
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
    
    async def generate_serial_number(self, zone_id: Optional[int] = None) -> int:
        """Generate a new serial number for a zone in YYYYMMDDNN format"""
        from datetime import datetime
        
        # Generate serial in YYYYMMDDNN format
        now = datetime.now()
        date_part = now.strftime("%Y%m%d")
        
        if zone_id:
            # Get current serial for this zone
            zone = await self.get_by_id(zone_id)
            if zone and zone.serial:
                current_serial_str = str(zone.serial)
                # Check if it's from today and in correct format
                if (current_serial_str.startswith(date_part) and 
                    len(current_serial_str) == 10 and 
                    current_serial_str.isdigit()):
                    # Increment the sequence number
                    sequence = int(current_serial_str[-2:]) + 1
                    if sequence > 99:
                        # If we've reached max sequences for the day, keep at 99
                        # In practice, this is very unlikely for DNS zones
                        sequence = 99
                        logger.warning(f"Zone {zone.name} has reached maximum serial increments for today")
                else:
                    # Current serial is not in today's format, start fresh
                    sequence = 1
            else:
                # No existing serial, start with 1
                sequence = 1
        else:
            # New zone, start with 1
            sequence = 1
        
        new_serial = int(f"{date_part}{sequence:02d}")
        logger.debug(f"Generated serial number: {new_serial} for zone_id: {zone_id}")
        return new_serial
    
    async def increment_serial(self, zone_id: int, reason: str = "manual") -> Optional[Zone]:
        """Increment the serial number for a zone"""
        logger.info(f"Incrementing serial for zone ID: {zone_id}, reason: {reason}")
        
        new_serial = await self.generate_serial_number(zone_id)
        updated_zone = await self.update(zone_id, {"serial": new_serial}, track_action=True)
        
        if updated_zone:
            logger.info(f"Updated zone {updated_zone.name} serial to {new_serial}")
            
            # Track specific action
            track_user_action(
                action="zone_serial_increment",
                resource_type="zone",
                resource_id=str(zone_id),
                details=f"Zone {updated_zone.name} serial incremented to {new_serial} (reason: {reason})",
                db=self.db
            )
        else:
            logger.error(f"Failed to increment serial for zone ID: {zone_id}")
        
        return updated_zone
    
    async def increment_serial_for_record_change(self, zone_id: int, change_type: str, record_info: str = "") -> Optional[Zone]:
        """Increment serial number when DNS records are modified"""
        reason = f"record_{change_type}"
        if record_info:
            reason += f"_{record_info}"
        
        logger.info(f"Incrementing serial for zone ID: {zone_id} due to record {change_type}")
        return await self.increment_serial(zone_id, reason)
    
    async def should_increment_serial(self, zone_data: Dict[str, Any]) -> bool:
        """Determine if zone changes should trigger serial increment"""
        # Fields that should trigger serial increment when changed
        significant_fields = [
            'name', 'email', 'refresh', 'retry', 'expire', 'minimum',
            'master_servers', 'forwarders', 'is_active'
        ]
        
        return any(field in zone_data for field in significant_fields)
    
    async def get_serial_history(self, zone_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get serial number change history for a zone (from audit logs)"""
        # This would typically query audit_logs table, but for now return basic info
        zone = await self.get_by_id(zone_id)
        if not zone:
            return []
        
        # Return current serial info
        # In a full implementation, this would query audit_logs table
        return [{
            "serial": zone.serial,
            "updated_at": zone.updated_at,
            "updated_by": zone.updated_by,
            "current": True
        }]
    
    async def validate_serial_number(self, serial: int) -> Dict[str, Any]:
        """Validate a serial number format and provide information"""
        serial_str = str(serial)
        
        # Check if it's in YYYYMMDDNN format
        if len(serial_str) != 10 or not serial_str.isdigit():
            return {
                "valid": False,
                "format": "unknown",
                "error": "Serial number must be 10 digits in YYYYMMDDNN format"
            }
        
        try:
            # Extract date part
            year = int(serial_str[:4])
            month = int(serial_str[4:6])
            day = int(serial_str[6:8])
            sequence = int(serial_str[8:10])
            
            # Validate date
            from datetime import datetime
            try:
                date_obj = datetime(year, month, day)
                date_valid = True
            except ValueError:
                date_valid = False
            
            return {
                "valid": date_valid and 1900 <= year <= 2100 and 1 <= sequence <= 99,
                "format": "YYYYMMDDNN",
                "year": year,
                "month": month,
                "day": day,
                "sequence": sequence,
                "date_valid": date_valid,
                "date_str": f"{year}-{month:02d}-{day:02d}",
                "error": None if date_valid else "Invalid date in serial number"
            }
        except (ValueError, IndexError):
            return {
                "valid": False,
                "format": "invalid",
                "error": "Could not parse serial number format"
            }
    
    async def reset_serial_to_current_date(self, zone_id: int) -> Optional[Zone]:
        """Reset zone serial number to current date with sequence 01"""
        from datetime import datetime
        
        logger.info(f"Resetting serial to current date for zone ID: {zone_id}")
        
        now = datetime.now()
        date_part = now.strftime("%Y%m%d")
        new_serial = int(f"{date_part}01")
        
        updated_zone = await self.update(zone_id, {"serial": new_serial}, track_action=True)
        
        if updated_zone:
            logger.info(f"Reset zone {updated_zone.name} serial to {new_serial}")
            
            # Track specific action
            track_user_action(
                action="zone_serial_reset",
                resource_type="zone",
                resource_id=str(zone_id),
                details=f"Zone {updated_zone.name} serial reset to current date: {new_serial}",
                db=self.db
            )
        
        return updated_zone
    
    async def set_custom_serial(self, zone_id: int, serial: int) -> Optional[Zone]:
        """Set a custom serial number for a zone (with validation)"""
        logger.info(f"Setting custom serial {serial} for zone ID: {zone_id}")
        
        # Validate the serial number
        validation = await self.validate_serial_number(serial)
        if not validation["valid"]:
            raise ValueError(f"Invalid serial number: {validation['error']}")
        
        updated_zone = await self.update(zone_id, {"serial": serial}, track_action=True)
        
        if updated_zone:
            logger.info(f"Set zone {updated_zone.name} serial to {serial}")
            
            # Track specific action
            track_user_action(
                action="zone_serial_custom",
                resource_type="zone",
                resource_id=str(zone_id),
                details=f"Zone {updated_zone.name} serial set to custom value: {serial}",
                db=self.db
            )
        
        return updated_zone
    
    async def validate_zone_data(self, zone_data: Dict[str, Any], zone_id: Optional[int] = None) -> Dict[str, Any]:
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
        elif '@' in zone_data['email']:
            errors.append("Zone email must be in DNS format (use dots instead of @, e.g., admin.example.com)")
        
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
        
        # Check for duplicate zone name (exclude current zone if updating)
        if zone_data.get('name'):
            if self.is_async:
                query = select(func.count(Zone.id)).filter(Zone.name == zone_data['name'])
                if zone_id:
                    query = query.filter(Zone.id != zone_id)
                result = await self.db.execute(query)
                existing_count = result.scalar()
            else:
                query = self.db.query(func.count(Zone.id)).filter(Zone.name == zone_data['name'])
                if zone_id:
                    query = query.filter(Zone.id != zone_id)
                existing_count = query.scalar()
            
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
    
    async def search_zones(self, search_term: str, zone_type: Optional[str] = None, 
                          active_only: bool = True, skip: int = 0, limit: int = 100) -> List[Zone]:
        """Search zones by name or description"""
        filters = {}
        
        if zone_type:
            filters['zone_type'] = zone_type
        if active_only:
            filters['is_active'] = True
        
        if self.is_async:
            query = select(Zone)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(Zone, key):
                    query = query.filter(getattr(Zone, key) == value)
            
            # Add search condition
            search_condition = Zone.name.ilike(f'%{search_term}%')
            if hasattr(Zone, 'description') and Zone.description is not None:
                search_condition = search_condition | Zone.description.ilike(f'%{search_term}%')
            
            query = query.filter(search_condition).offset(skip).limit(limit)
            result = await self.db.execute(query)
            return result.scalars().all()
        else:
            query = self.db.query(Zone)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(Zone, key):
                    query = query.filter(getattr(Zone, key) == value)
            
            # Add search condition
            search_condition = Zone.name.ilike(f'%{search_term}%')
            if hasattr(Zone, 'description') and Zone.description is not None:
                search_condition = search_condition | Zone.description.ilike(f'%{search_term}%')
            
            return query.filter(search_condition).offset(skip).limit(limit).all()
    
    async def get_zone_by_name(self, zone_name: str) -> Optional[Zone]:
        """Get a zone by its name"""
        if self.is_async:
            result = await self.db.execute(
                select(Zone).filter(Zone.name == zone_name)
            )
            return result.scalar_one_or_none()
        else:
            return self.db.query(Zone).filter(Zone.name == zone_name).first()
    
    async def get_zones_summary(self) -> Dict[str, Any]:
        """Get a summary of all zones"""
        if self.is_async:
            # Total zones
            result = await self.db.execute(select(func.count(Zone.id)))
            total_zones = result.scalar()
            
            # Active zones
            result = await self.db.execute(
                select(func.count(Zone.id)).filter(Zone.is_active == True)
            )
            active_zones = result.scalar()
            
            # Zones by type
            result = await self.db.execute(
                select(Zone.zone_type, func.count(Zone.id))
                .group_by(Zone.zone_type)
            )
            zones_by_type = dict(result.fetchall())
            
            # Total records across all zones
            result = await self.db.execute(
                select(func.count(DNSRecord.id))
                .filter(DNSRecord.is_active == True)
            )
            total_records = result.scalar()
        else:
            # Total zones
            total_zones = self.db.query(func.count(Zone.id)).scalar()
            
            # Active zones
            active_zones = self.db.query(func.count(Zone.id)).filter(Zone.is_active == True).scalar()
            
            # Zones by type
            zones_by_type = dict(
                self.db.query(Zone.zone_type, func.count(Zone.id))
                .group_by(Zone.zone_type)
                .all()
            )
            
            # Total records across all zones
            total_records = self.db.query(func.count(DNSRecord.id)).filter(
                DNSRecord.is_active == True
            ).scalar()
        
        return {
            "total_zones": total_zones,
            "active_zones": active_zones,
            "inactive_zones": total_zones - active_zones,
            "zones_by_type": zones_by_type,
            "total_records": total_records
        }
    
    async def bulk_update_zones(self, zone_ids: List[int], update_data: Dict[str, Any]) -> List[Zone]:
        """Bulk update multiple zones"""
        logger.info(f"Bulk updating {len(zone_ids)} zones")
        
        updated_zones = []
        for zone_id in zone_ids:
            try:
                updated_zone = await self.update(zone_id, update_data, track_action=True)
                if updated_zone:
                    updated_zones.append(updated_zone)
            except Exception as e:
                logger.error(f"Failed to update zone {zone_id}: {e}")
                continue
        
        logger.info(f"Successfully updated {len(updated_zones)} zones")
        return updated_zones
    
    async def bulk_toggle_zones(self, zone_ids: List[int], active: bool) -> List[Zone]:
        """Bulk toggle zone active status"""
        logger.info(f"Bulk {'activating' if active else 'deactivating'} {len(zone_ids)} zones")
        
        updated_zones = []
        for zone_id in zone_ids:
            try:
                updated_zone = await self.update(zone_id, {"is_active": active}, track_action=True)
                if updated_zone:
                    updated_zones.append(updated_zone)
                    
                    # Track specific action
                    action = "zone_bulk_activate" if active else "zone_bulk_deactivate"
                    track_user_action(
                        action=action,
                        resource_type="zone",
                        resource_id=str(zone_id),
                        details=f"Zone {updated_zone.name} {'activated' if active else 'deactivated'} in bulk operation",
                        db=self.db
                    )
            except Exception as e:
                logger.error(f"Failed to toggle zone {zone_id}: {e}")
                continue
        
        logger.info(f"Successfully {'activated' if active else 'deactivated'} {len(updated_zones)} zones")
        return updated_zones
    
    async def bulk_increment_serials(self, zone_ids: List[int], reason: str = "bulk_update") -> List[Zone]:
        """Bulk increment serial numbers for multiple zones"""
        logger.info(f"Bulk incrementing serials for {len(zone_ids)} zones")
        
        updated_zones = []
        for zone_id in zone_ids:
            try:
                updated_zone = await self.increment_serial(zone_id, reason)
                if updated_zone:
                    updated_zones.append(updated_zone)
            except Exception as e:
                logger.error(f"Failed to increment serial for zone {zone_id}: {e}")
                continue
        
        logger.info(f"Successfully incremented serials for {len(updated_zones)} zones")
        return updated_zones
    
    async def export_zone_data(self, zone_id: int) -> Optional[Dict[str, Any]]:
        """Export zone data including all records for backup/transfer"""
        zone_data = await self.get_zone_with_records(zone_id)
        if not zone_data:
            return None
        
        zone = zone_data["zone"]
        records = zone_data["records"]
        
        # Convert to exportable format
        export_data = {
            "zone": {
                "name": zone.name,
                "zone_type": zone.zone_type,
                "email": zone.email,
                "description": zone.description,
                "refresh": zone.refresh,
                "retry": zone.retry,
                "expire": zone.expire,
                "minimum": zone.minimum,
                "master_servers": zone.master_servers,
                "forwarders": zone.forwarders,
                "serial": zone.serial,
                "created_at": zone.created_at.isoformat() if zone.created_at else None,
                "updated_at": zone.updated_at.isoformat() if zone.updated_at else None
            },
            "records": [
                {
                    "name": record.name,
                    "record_type": record.record_type,
                    "value": record.value,
                    "ttl": record.ttl,
                    "priority": record.priority,
                    "weight": record.weight,
                    "port": record.port,
                    "is_active": record.is_active
                }
                for record in records
            ],
            "export_timestamp": datetime.now().isoformat(),
            "export_version": "1.0"
        }
        
        logger.info(f"Exported zone {zone.name} with {len(records)} records")
        return export_data
    
    async def validate_zone_file_path(self, zone_name: str, zone_type: str) -> str:
        """Generate and validate zone file path using BindService"""
        from .bind_service import BindService
        
        # Use BindService to generate the file path
        bind_service = BindService(self.db)
        file_path = bind_service._validate_zone_file_path(zone_name, zone_type)
        
        return file_path
    
    async def validate_zone_name(self, zone_name: str) -> Dict[str, Any]:
        """Validate DNS zone name format and structure"""
        errors = []
        warnings = []
        
        if not zone_name:
            errors.append("Zone name cannot be empty")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Check length
        if len(zone_name) > 253:
            errors.append("Zone name cannot exceed 253 characters")
        
        # Check for valid characters
        import re
        if not re.match(r'^[a-zA-Z0-9.-]+$', zone_name):
            errors.append("Zone name can only contain letters, numbers, dots, and hyphens")
        
        # Check label length (each part between dots)
        labels = zone_name.split('.')
        for label in labels:
            if len(label) > 63:
                errors.append(f"Label '{label}' exceeds 63 characters")
            if len(label) == 0:
                errors.append("Zone name cannot have empty labels (consecutive dots)")
            if label.startswith('-') or label.endswith('-'):
                errors.append(f"Label '{label}' cannot start or end with hyphen")
        
        # Check for reserved names
        reserved_names = ['localhost', 'localdomain', 'local']
        if zone_name.lower() in reserved_names:
            warnings.append(f"Zone name '{zone_name}' is a reserved name")
        
        # Check for common TLDs that might indicate misconfiguration
        common_tlds = ['.com', '.org', '.net', '.edu', '.gov']
        if any(zone_name.lower().endswith(tld) for tld in common_tlds):
            warnings.append(f"Zone name '{zone_name}' appears to be a public domain - ensure this is intentional")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def validate_zone_configuration(self, zone_id: int) -> Dict[str, Any]:
        """Comprehensive zone configuration validation"""
        zone = await self.get_by_id(zone_id)
        if not zone:
            return {
                "valid": False,
                "errors": ["Zone not found"],
                "warnings": []
            }
        
        errors = []
        warnings = []
        
        # Validate zone name
        name_validation = await self.validate_zone_name(zone.name)
        errors.extend(name_validation["errors"])
        warnings.extend(name_validation["warnings"])
        
        # Validate zone data
        zone_data = {
            "name": zone.name,
            "email": zone.email,
            "zone_type": zone.zone_type,
            "refresh": zone.refresh,
            "retry": zone.retry,
            "expire": zone.expire,
            "minimum": zone.minimum
        }
        
        data_validation = await self.validate_zone_data(zone_data, zone_id)
        errors.extend(data_validation["errors"])
        warnings.extend(data_validation["warnings"])
        
        # Validate serial number
        if zone.serial:
            serial_validation = await self.validate_serial_number(zone.serial)
            if not serial_validation["valid"]:
                errors.append(f"Invalid serial number: {serial_validation['error']}")
        else:
            warnings.append("Zone has no serial number")
        
        # Validate zone type specific requirements
        if zone.zone_type == 'slave':
            if not zone.master_servers:
                errors.append("Slave zones must specify master servers")
            else:
                # Validate master server IPs
                master_validation = await self.validate_server_list(zone.master_servers)
                errors.extend(master_validation["errors"])
                warnings.extend(master_validation["warnings"])
        
        elif zone.zone_type == 'forward':
            if not zone.forwarders:
                errors.append("Forward zones must specify forwarder servers")
            else:
                # Validate forwarder IPs
                forwarder_validation = await self.validate_server_list(zone.forwarders)
                errors.extend(forwarder_validation["errors"])
                warnings.extend(forwarder_validation["warnings"])
        
        # Check for conflicting zones
        conflict_check = await self.check_zone_conflicts(zone.name, zone_id)
        errors.extend(conflict_check["errors"])
        warnings.extend(conflict_check["warnings"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "zone_id": zone_id,
            "zone_name": zone.name
        }
    
    async def validate_server_list(self, servers: List[str]) -> Dict[str, Any]:
        """Validate a list of server IP addresses"""
        import ipaddress
        
        errors = []
        warnings = []
        
        if not servers:
            errors.append("Server list cannot be empty")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        for server in servers:
            try:
                # Try to parse as IP address
                ip = ipaddress.ip_address(server)
                
                # Check for private/reserved addresses
                if ip.is_private:
                    warnings.append(f"Server {server} is a private IP address")
                elif ip.is_loopback:
                    warnings.append(f"Server {server} is a loopback address")
                elif ip.is_reserved:
                    warnings.append(f"Server {server} is a reserved IP address")
                
            except ValueError:
                errors.append(f"Invalid IP address: {server}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def check_zone_conflicts(self, zone_name: str, exclude_zone_id: Optional[int] = None) -> Dict[str, Any]:
        """Check for conflicting zone names or overlapping zones"""
        errors = []
        warnings = []
        
        # Check for exact duplicate
        if self.is_async:
            query = select(Zone).filter(Zone.name == zone_name)
            if exclude_zone_id:
                query = query.filter(Zone.id != exclude_zone_id)
            result = await self.db.execute(query)
            existing_zones = result.scalars().all()
        else:
            query = self.db.query(Zone).filter(Zone.name == zone_name)
            if exclude_zone_id:
                query = query.filter(Zone.id != exclude_zone_id)
            existing_zones = query.all()
        
        if existing_zones:
            errors.append(f"Zone '{zone_name}' already exists")
        
        # Check for parent/child zone conflicts
        zone_parts = zone_name.split('.')
        
        # Check if this zone is a subdomain of an existing zone
        for i in range(1, len(zone_parts)):
            parent_zone = '.'.join(zone_parts[i:])
            
            if self.is_async:
                query = select(Zone).filter(Zone.name == parent_zone, Zone.is_active == True)
                if exclude_zone_id:
                    query = query.filter(Zone.id != exclude_zone_id)
                result = await self.db.execute(query)
                parent_exists = result.scalar_one_or_none()
            else:
                query = self.db.query(Zone).filter(Zone.name == parent_zone, Zone.is_active == True)
                if exclude_zone_id:
                    query = query.filter(Zone.id != exclude_zone_id)
                parent_exists = query.first()
            
            if parent_exists:
                warnings.append(f"Zone '{zone_name}' is a subdomain of existing zone '{parent_zone}'")
        
        # Check if existing zones are subdomains of this zone
        if self.is_async:
            query = select(Zone).filter(Zone.name.like(f'%.{zone_name}'), Zone.is_active == True)
            if exclude_zone_id:
                query = query.filter(Zone.id != exclude_zone_id)
            result = await self.db.execute(query)
            child_zones = result.scalars().all()
        else:
            query = self.db.query(Zone).filter(Zone.name.like(f'%.{zone_name}'), Zone.is_active == True)
            if exclude_zone_id:
                query = query.filter(Zone.id != exclude_zone_id)
            child_zones = query.all()
        
        if child_zones:
            child_names = [zone.name for zone in child_zones]
            warnings.append(f"Existing subdomains will be affected: {', '.join(child_names)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def validate_zone_records(self, zone_id: int) -> Dict[str, Any]:
        """Validate all DNS records in a zone"""
        zone = await self.get_by_id(zone_id)
        if not zone:
            return {
                "valid": False,
                "errors": ["Zone not found"],
                "warnings": []
            }
        
        errors = []
        warnings = []
        
        # Get all active records for this zone
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
        
        # Check for required SOA record (for master zones)
        if zone.zone_type == 'master':
            soa_records = [r for r in records if r.record_type == 'SOA']
            if not soa_records:
                errors.append("Master zone must have an SOA record")
            elif len(soa_records) > 1:
                errors.append("Zone cannot have multiple SOA records")
        
        # Check for NS records
        ns_records = [r for r in records if r.record_type == 'NS']
        if zone.zone_type == 'master' and not ns_records:
            warnings.append("Master zone should have NS records")
        
        # Validate individual records
        record_names = {}
        for record in records:
            # Check for duplicate records
            record_key = (record.name, record.record_type)
            if record_key in record_names:
                if record.record_type not in ['A', 'AAAA', 'MX', 'TXT', 'NS']:
                    errors.append(f"Duplicate {record.record_type} record for {record.name}")
            else:
                record_names[record_key] = []
            record_names[record_key].append(record)
            
            # Validate record format
            record_validation = await self.validate_record_format(record)
            errors.extend(record_validation["errors"])
            warnings.extend(record_validation["warnings"])
        
        # Check for CNAME conflicts
        cname_records = [r for r in records if r.record_type == 'CNAME']
        for cname in cname_records:
            other_records = [r for r in records if r.name == cname.name and r.record_type != 'CNAME']
            if other_records:
                errors.append(f"CNAME record '{cname.name}' conflicts with other record types")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "total_records": len(records),
            "record_types": list(set(r.record_type for r in records))
        }
    
    async def validate_record_format(self, record) -> Dict[str, Any]:
        """Validate individual DNS record format"""
        import ipaddress
        import re
        
        errors = []
        warnings = []
        
        record_type = record.record_type
        value = record.value
        name = record.name
        
        # Validate based on record type
        if record_type == 'A':
            try:
                ip = ipaddress.IPv4Address(value)
                if ip.is_private:
                    warnings.append(f"A record '{name}' points to private IP {value}")
            except ValueError:
                errors.append(f"A record '{name}' has invalid IPv4 address: {value}")
        
        elif record_type == 'AAAA':
            try:
                ip = ipaddress.IPv6Address(value)
                if ip.is_private:
                    warnings.append(f"AAAA record '{name}' points to private IP {value}")
            except ValueError:
                errors.append(f"AAAA record '{name}' has invalid IPv6 address: {value}")
        
        elif record_type == 'CNAME':
            if not re.match(r'^[a-zA-Z0-9.-]+\.$', value):
                if not value.endswith('.'):
                    warnings.append(f"CNAME record '{name}' should end with a dot: {value}")
        
        elif record_type == 'MX':
            if not record.priority:
                errors.append(f"MX record '{name}' must have a priority value")
            if not re.match(r'^[a-zA-Z0-9.-]+\.?$', value):
                errors.append(f"MX record '{name}' has invalid mail server format: {value}")
        
        elif record_type == 'SRV':
            if not all([record.priority, record.weight, record.port]):
                errors.append(f"SRV record '{name}' must have priority, weight, and port values")
            if not re.match(r'^[a-zA-Z0-9.-]+\.?$', value):
                errors.append(f"SRV record '{name}' has invalid target format: {value}")
        
        elif record_type == 'TXT':
            if len(value) > 255:
                errors.append(f"TXT record '{name}' exceeds 255 characters")
        
        elif record_type == 'PTR':
            if not re.match(r'^[a-zA-Z0-9.-]+\.?$', value):
                errors.append(f"PTR record '{name}' has invalid hostname format: {value}")
        
        # Validate TTL
        if record.ttl and (record.ttl < 60 or record.ttl > 86400):
            warnings.append(f"Record '{name}' TTL {record.ttl} is outside recommended range (60-86400)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def validate_zone_for_bind(self, zone_id: int) -> Dict[str, Any]:
        """Validate zone configuration for BIND9 compatibility"""
        zone = await self.get_by_id(zone_id)
        if not zone:
            return {
                "valid": False,
                "errors": ["Zone not found"],
                "warnings": []
            }
        
        errors = []
        warnings = []
        
        # Run comprehensive validation
        config_validation = await self.validate_zone_configuration(zone_id)
        errors.extend(config_validation["errors"])
        warnings.extend(config_validation["warnings"])
        
        records_validation = await self.validate_zone_records(zone_id)
        errors.extend(records_validation["errors"])
        warnings.extend(records_validation["warnings"])
        
        # BIND-specific validations
        if zone.zone_type == 'master':
            # Check for required records
            if self.is_async:
                result = await self.db.execute(
                    select(DNSRecord).filter(
                        DNSRecord.zone_id == zone_id,
                        DNSRecord.is_active == True,
                        DNSRecord.record_type == 'SOA'
                    )
                )
                soa_records = result.scalars().all()
            else:
                soa_records = self.db.query(DNSRecord).filter(
                    DNSRecord.zone_id == zone_id,
                    DNSRecord.is_active == True,
                    DNSRecord.record_type == 'SOA'
                ).all()
            
            if not soa_records:
                errors.append("Master zone requires an SOA record for BIND9")
        
        # Check file path validity
        try:
            file_path = await self.validate_zone_file_path(zone.name, zone.zone_type)
            if not file_path:
                errors.append("Could not generate valid zone file path")
        except Exception as e:
            errors.append(f"Zone file path validation failed: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "bind_compatible": len(errors) == 0,
            "zone_id": zone_id,
            "zone_name": zone.name,
            "zone_type": zone.zone_type
        }
    
    async def get_zone_health(self, zone_id: int) -> Optional[Dict[str, Any]]:
        """Get zone health status"""
        zone = await self.get_by_id(zone_id)
        if not zone:
            return None
        
        from datetime import datetime, timedelta
        import asyncio
        
        # Initialize health data
        health_data = {
            "status": "healthy",
            "last_check": datetime.utcnow().isoformat(),
            "issues": [],
            "response_time": None
        }
        
        issues = []
        
        # Check if zone is active
        if not zone.is_active:
            health_data["status"] = "warning"
            issues.append("Zone is inactive")
        
        # Check for records
        records = await self.get_zone_records(zone_id)
        if not records:
            health_data["status"] = "warning"
            issues.append("Zone has no DNS records")
        
        # Check serial number age
        if zone.serial:
            try:
                # Extract date from serial (assuming YYYYMMDDNN format)
                serial_str = str(zone.serial)
                if len(serial_str) >= 8:
                    date_part = serial_str[:8]
                    serial_date = datetime.strptime(date_part, "%Y%m%d")
                    days_old = (datetime.utcnow() - serial_date).days
                    
                    if days_old > 30:
                        if health_data["status"] == "healthy":
                            health_data["status"] = "warning"
                        issues.append(f"Serial number is {days_old} days old")
                    elif days_old > 90:
                        health_data["status"] = "error"
                        issues.append(f"Serial number is very old ({days_old} days)")
            except (ValueError, TypeError):
                issues.append("Invalid serial number format")
        
        # Check zone file syntax (basic validation)
        try:
            validation_result = await self.validate_zone_for_bind(zone_id)
            if not validation_result.get("valid", True):
                health_data["status"] = "error"
                issues.extend(validation_result.get("errors", []))
        except Exception as e:
            health_data["status"] = "error"
            issues.append(f"Zone validation failed: {str(e)}")
        
        # Simulate response time check (in a real implementation, this would test DNS resolution)
        start_time = datetime.utcnow()
        await asyncio.sleep(0.001)  # Simulate network delay
        end_time = datetime.utcnow()
        health_data["response_time"] = int((end_time - start_time).total_seconds() * 1000)
        
        health_data["issues"] = issues
        
        # Set final status based on issues
        if len(issues) == 0:
            health_data["status"] = "healthy"
        elif any("error" in issue.lower() or "failed" in issue.lower() for issue in issues):
            health_data["status"] = "error"
        elif health_data["status"] != "error":
            health_data["status"] = "warning"
        
        return health_data
    
    async def get_zone_health_statistics(self, zone_id: int) -> Optional[Dict[str, Any]]:
        """Get health and performance statistics for a zone"""
        zone = await self.get_by_id(zone_id)
        if not zone:
            return None
        
        # Get basic zone statistics
        basic_stats = await self.get_zone_statistics(zone_id)
        if not basic_stats:
            return None
        
        # Calculate zone health metrics
        health_score = 100  # Start with perfect score
        health_issues = []
        
        # Check for common issues
        if basic_stats["total_records"] == 0:
            health_score -= 30
            health_issues.append("Zone has no DNS records")
        
        # Check serial number age
        if zone.serial and basic_stats["serial_info"]:
            serial_info = basic_stats["serial_info"]
            if serial_info.get("valid"):
                from datetime import datetime, timedelta
                try:
                    serial_date = datetime.strptime(serial_info["date_str"], "%Y-%m-%d")
                    days_old = (datetime.now() - serial_date).days
                    if days_old > 30:
                        health_score -= 20
                        health_issues.append(f"Serial number is {days_old} days old")
                    elif days_old > 7:
                        health_score -= 10
                        health_issues.append(f"Serial number is {days_old} days old")
                except ValueError:
                    health_score -= 15
                    health_issues.append("Invalid serial number format")
        
        # Check SOA record parameters
        if zone.refresh > 86400:  # More than 24 hours
            health_score -= 10
            health_issues.append("Refresh interval is very high (>24h)")
        
        if zone.retry > zone.refresh:
            health_score -= 15
            health_issues.append("Retry interval is higher than refresh interval")
        
        if zone.expire < (zone.refresh * 7):  # Less than 7 refresh cycles
            health_score -= 10
            health_issues.append("Expire time is too low relative to refresh interval")
        
        # Determine health status
        if health_score >= 90:
            health_status = "excellent"
        elif health_score >= 75:
            health_status = "good"
        elif health_score >= 60:
            health_status = "fair"
        elif health_score >= 40:
            health_status = "poor"
        else:
            health_status = "critical"
        
        return {
            "zone_id": zone_id,
            "zone_name": zone.name,
            "health_score": max(0, health_score),
            "health_status": health_status,
            "health_issues": health_issues,
            "recommendations": await self._get_zone_recommendations(zone, basic_stats),
            "last_updated": zone.updated_at,
            "days_since_update": (datetime.now() - zone.updated_at).days if zone.updated_at else None
        }
    
    async def get_zone_activity_statistics(self, zone_id: int, days: int = 30) -> Optional[Dict[str, Any]]:
        """Get zone activity statistics over a specified period"""
        zone = await self.get_by_id(zone_id)
        if not zone:
            return None
        
        from datetime import datetime, timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get record modification activity (this would typically come from audit logs)
        # For now, we'll provide basic activity metrics
        activity_stats = {
            "zone_id": zone_id,
            "zone_name": zone.name,
            "period_days": days,
            "start_date": start_date,
            "end_date": end_date,
            "zone_modifications": 0,  # Would be calculated from audit logs
            "record_additions": 0,    # Would be calculated from audit logs
            "record_modifications": 0, # Would be calculated from audit logs
            "record_deletions": 0,    # Would be calculated from audit logs
            "serial_increments": 0,   # Would be calculated from audit logs
            "last_activity": zone.updated_at,
            "is_active_zone": zone.is_active,
            "activity_level": "low"   # low, medium, high based on changes
        }
        
        # Calculate activity level based on last update
        if zone.updated_at:
            days_since_update = (datetime.now() - zone.updated_at).days
            if days_since_update <= 1:
                activity_stats["activity_level"] = "high"
            elif days_since_update <= 7:
                activity_stats["activity_level"] = "medium"
            else:
                activity_stats["activity_level"] = "low"
        
        return activity_stats
    
    async def get_zone_record_type_distribution(self, zone_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed distribution of record types in a zone"""
        zone = await self.get_by_id(zone_id)
        if not zone:
            return None
        
        # Get record counts by type (including inactive records for full picture)
        if self.is_async:
            # Active records by type
            result = await self.db.execute(
                select(DNSRecord.record_type, func.count(DNSRecord.id))
                .filter(DNSRecord.zone_id == zone_id, DNSRecord.is_active == True)
                .group_by(DNSRecord.record_type)
            )
            active_counts = dict(result.fetchall())
            
            # All records by type (including inactive)
            result = await self.db.execute(
                select(DNSRecord.record_type, func.count(DNSRecord.id))
                .filter(DNSRecord.zone_id == zone_id)
                .group_by(DNSRecord.record_type)
            )
            total_counts = dict(result.fetchall())
            
            # Get total counts
            result = await self.db.execute(
                select(func.count(DNSRecord.id))
                .filter(DNSRecord.zone_id == zone_id, DNSRecord.is_active == True)
            )
            total_active = result.scalar()
            
            result = await self.db.execute(
                select(func.count(DNSRecord.id))
                .filter(DNSRecord.zone_id == zone_id)
            )
            total_all = result.scalar()
        else:
            # Active records by type
            active_counts = dict(
                self.db.query(DNSRecord.record_type, func.count(DNSRecord.id))
                .filter(DNSRecord.zone_id == zone_id, DNSRecord.is_active == True)
                .group_by(DNSRecord.record_type)
                .all()
            )
            
            # All records by type
            total_counts = dict(
                self.db.query(DNSRecord.record_type, func.count(DNSRecord.id))
                .filter(DNSRecord.zone_id == zone_id)
                .group_by(DNSRecord.record_type)
                .all()
            )
            
            # Get total counts
            total_active = self.db.query(func.count(DNSRecord.id)).filter(
                DNSRecord.zone_id == zone_id, DNSRecord.is_active == True
            ).scalar()
            
            total_all = self.db.query(func.count(DNSRecord.id)).filter(
                DNSRecord.zone_id == zone_id
            ).scalar()
        
        # Calculate percentages and create detailed distribution
        distribution = {}
        common_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'NS']
        
        for record_type in common_types:
            active_count = active_counts.get(record_type, 0)
            total_count = total_counts.get(record_type, 0)
            inactive_count = total_count - active_count
            
            distribution[record_type] = {
                "active_count": active_count,
                "inactive_count": inactive_count,
                "total_count": total_count,
                "active_percentage": round((active_count / total_active * 100) if total_active > 0 else 0, 2),
                "total_percentage": round((total_count / total_all * 100) if total_all > 0 else 0, 2)
            }
        
        # Add any other record types not in common_types
        all_types = set(list(active_counts.keys()) + list(total_counts.keys()))
        for record_type in all_types:
            if record_type not in distribution:
                active_count = active_counts.get(record_type, 0)
                total_count = total_counts.get(record_type, 0)
                inactive_count = total_count - active_count
                
                distribution[record_type] = {
                    "active_count": active_count,
                    "inactive_count": inactive_count,
                    "total_count": total_count,
                    "active_percentage": round((active_count / total_active * 100) if total_active > 0 else 0, 2),
                    "total_percentage": round((total_count / total_all * 100) if total_all > 0 else 0, 2)
                }
        
        return {
            "zone_id": zone_id,
            "zone_name": zone.name,
            "total_active_records": total_active,
            "total_inactive_records": total_all - total_active,
            "total_all_records": total_all,
            "record_type_distribution": distribution,
            "most_common_type": max(active_counts.items(), key=lambda x: x[1])[0] if active_counts else None,
            "record_type_count": len(active_counts),
            "has_inactive_records": (total_all - total_active) > 0
        }
    
    async def get_zones_comparison_statistics(self, zone_ids: List[int]) -> Dict[str, Any]:
        """Get comparative statistics for multiple zones"""
        if not zone_ids:
            return {"zones": [], "comparison": {}}
        
        zone_stats = []
        for zone_id in zone_ids:
            stats = await self.get_zone_statistics(zone_id)
            if stats:
                zone_stats.append(stats)
        
        if not zone_stats:
            return {"zones": [], "comparison": {}}
        
        # Calculate comparison metrics
        total_records = [stats["total_records"] for stats in zone_stats]
        record_counts = {}
        
        # Aggregate record type counts across all zones
        for stats in zone_stats:
            for record_type, count in stats["record_counts"].items():
                if record_type not in record_counts:
                    record_counts[record_type] = []
                record_counts[record_type].append(count)
        
        # Calculate comparison statistics
        comparison = {
            "total_zones": len(zone_stats),
            "total_records_all_zones": sum(total_records),
            "average_records_per_zone": round(sum(total_records) / len(total_records), 2) if total_records else 0,
            "min_records": min(total_records) if total_records else 0,
            "max_records": max(total_records) if total_records else 0,
            "zones_with_most_records": [stats["zone_name"] for stats in zone_stats if stats["total_records"] == max(total_records)] if total_records else [],
            "zones_with_least_records": [stats["zone_name"] for stats in zone_stats if stats["total_records"] == min(total_records)] if total_records else [],
            "record_type_totals": {record_type: sum(counts) for record_type, counts in record_counts.items()},
            "most_common_record_type": max(record_counts.items(), key=lambda x: sum(x[1]))[0] if record_counts else None
        }
        
        return {
            "zones": zone_stats,
            "comparison": comparison
        }
    
    async def get_zone_size_statistics(self, zone_id: int) -> Optional[Dict[str, Any]]:
        """Get zone size and complexity statistics"""
        zone = await self.get_by_id(zone_id)
        if not zone:
            return None
        
        # Get detailed record information
        if self.is_async:
            # Get record value lengths for size analysis
            result = await self.db.execute(
                select(
                    DNSRecord.record_type,
                    func.count(DNSRecord.id).label('count'),
                    func.avg(func.length(DNSRecord.value)).label('avg_value_length'),
                    func.max(func.length(DNSRecord.value)).label('max_value_length'),
                    func.min(func.length(DNSRecord.value)).label('min_value_length')
                )
                .filter(DNSRecord.zone_id == zone_id, DNSRecord.is_active == True)
                .group_by(DNSRecord.record_type)
            )
            record_size_stats = result.fetchall()
            
            # Get records with custom TTL
            result = await self.db.execute(
                select(func.count(DNSRecord.id))
                .filter(DNSRecord.zone_id == zone_id, DNSRecord.is_active == True, DNSRecord.ttl.isnot(None))
            )
            records_with_custom_ttl = result.scalar()
            
            # Get records with priority (MX, SRV)
            result = await self.db.execute(
                select(func.count(DNSRecord.id))
                .filter(DNSRecord.zone_id == zone_id, DNSRecord.is_active == True, DNSRecord.priority.isnot(None))
            )
            records_with_priority = result.scalar()
        else:
            # Get record value lengths for size analysis
            record_size_stats = self.db.query(
                DNSRecord.record_type,
                func.count(DNSRecord.id).label('count'),
                func.avg(func.length(DNSRecord.value)).label('avg_value_length'),
                func.max(func.length(DNSRecord.value)).label('max_value_length'),
                func.min(func.length(DNSRecord.value)).label('min_value_length')
            ).filter(
                DNSRecord.zone_id == zone_id, DNSRecord.is_active == True
            ).group_by(DNSRecord.record_type).all()
            
            # Get records with custom TTL
            records_with_custom_ttl = self.db.query(func.count(DNSRecord.id)).filter(
                DNSRecord.zone_id == zone_id, DNSRecord.is_active == True, DNSRecord.ttl.isnot(None)
            ).scalar()
            
            # Get records with priority
            records_with_priority = self.db.query(func.count(DNSRecord.id)).filter(
                DNSRecord.zone_id == zone_id, DNSRecord.is_active == True, DNSRecord.priority.isnot(None)
            ).scalar()
        
        # Process size statistics
        size_by_type = {}
        total_estimated_size = 0
        
        for row in record_size_stats:
            record_type = row.record_type
            count = row.count
            avg_length = float(row.avg_value_length) if row.avg_value_length else 0
            max_length = row.max_value_length if row.max_value_length else 0
            min_length = row.min_value_length if row.min_value_length else 0
            
            # Estimate zone file size contribution (rough calculation)
            # Format: "name TTL class type value"
            estimated_line_size = len(zone.name) + 10 + len(record_type) + avg_length + 20  # rough estimate
            estimated_total_size = estimated_line_size * count
            total_estimated_size += estimated_total_size
            
            size_by_type[record_type] = {
                "count": count,
                "avg_value_length": round(avg_length, 2),
                "max_value_length": max_length,
                "min_value_length": min_length,
                "estimated_size_bytes": round(estimated_total_size)
            }
        
        # Determine complexity level
        total_records = sum(stats["count"] for stats in size_by_type.values())
        record_types_count = len(size_by_type)
        
        if total_records <= 10 and record_types_count <= 3:
            complexity = "simple"
        elif total_records <= 50 and record_types_count <= 5:
            complexity = "moderate"
        elif total_records <= 200 and record_types_count <= 8:
            complexity = "complex"
        else:
            complexity = "very_complex"
        
        return {
            "zone_id": zone_id,
            "zone_name": zone.name,
            "total_records": total_records,
            "record_types_count": record_types_count,
            "estimated_zone_file_size_bytes": round(total_estimated_size),
            "estimated_zone_file_size_kb": round(total_estimated_size / 1024, 2),
            "complexity_level": complexity,
            "size_by_record_type": size_by_type,
            "records_with_custom_ttl": records_with_custom_ttl,
            "records_with_priority": records_with_priority,
            "customization_percentage": round((records_with_custom_ttl / total_records * 100) if total_records > 0 else 0, 2)
        }
    
    async def _get_zone_recommendations(self, zone: Zone, basic_stats: Dict[str, Any]) -> List[str]:
        """Get recommendations for zone optimization"""
        recommendations = []
        
        # Check record count
        if basic_stats["total_records"] == 0:
            recommendations.append("Add DNS records to make this zone functional")
        elif basic_stats["total_records"] > 1000:
            recommendations.append("Consider splitting large zones for better performance")
        
        # Check SOA parameters
        if zone.refresh > 86400:
            recommendations.append("Consider reducing refresh interval for more frequent updates")
        
        if zone.retry > zone.refresh:
            recommendations.append("Retry interval should be less than refresh interval")
        
        if zone.expire < (zone.refresh * 7):
            recommendations.append("Increase expire time to at least 7 times the refresh interval")
        
        # Check serial number
        if zone.serial and basic_stats.get("serial_info"):
            serial_info = basic_stats["serial_info"]
            if not serial_info.get("valid"):
                recommendations.append("Fix serial number format to use YYYYMMDDNN format")
            else:
                from datetime import datetime
                try:
                    serial_date = datetime.strptime(serial_info["date_str"], "%Y-%m-%d")
                    days_old = (datetime.now() - serial_date).days
                    if days_old > 30:
                        recommendations.append("Consider updating the serial number to reflect recent changes")
                except ValueError:
                    pass
        
        # Check record types
        record_counts = basic_stats.get("record_counts", {})
        if "A" not in record_counts and "AAAA" not in record_counts:
            recommendations.append("Add A or AAAA records for hostname resolution")
        
        if zone.zone_type == "master" and "NS" not in record_counts:
            recommendations.append("Add NS records to specify authoritative name servers")
        
        return recommendations
    
    @staticmethod
    async def trigger_serial_increment_for_record_change(db: Session, zone_id: int, change_type: str, record_name: str = ""):
        """Static method to trigger serial increment from other services"""
        zone_service = ZoneService(db)
        record_info = record_name if record_name else "unknown"
        return await zone_service.increment_serial_for_record_change(zone_id, change_type, record_info)
    
    # Import/Export functionality
    async def import_zone_from_data(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """Import zone from various formats"""
        from ..schemas.dns import ZoneImportFormat, ZoneImportResult
        
        format_type = import_data.get('format', ZoneImportFormat.JSON)
        validate_only = import_data.get('validate_only', False)
        overwrite_existing = import_data.get('overwrite_existing', False)
        
        zone_data = import_data.get('zone', {})
        records_data = import_data.get('records', [])
        
        errors = []
        warnings = []
        zone_id = None
        zone_name = zone_data.get('name', 'unknown')
        records_imported = 0
        records_skipped = 0
        
        try:
            # Validate zone data first
            zone_validation = await self.validate_zone_data(zone_data)
            if not zone_validation["valid"]:
                errors.extend(zone_validation["errors"])
                warnings.extend(zone_validation["warnings"])
            
            # Check if zone already exists
            existing_zone = None
            if zone_name != 'unknown':
                if self.is_async:
                    result = await self.db.execute(
                        select(Zone).filter(Zone.name == zone_name)
                    )
                    existing_zone = result.scalar_one_or_none()
                else:
                    existing_zone = self.db.query(Zone).filter(Zone.name == zone_name).first()
            
            if existing_zone and not overwrite_existing:
                errors.append(f"Zone '{zone_name}' already exists. Use overwrite_existing=true to replace it.")
                return {
                    "success": False,
                    "zone_id": None,
                    "zone_name": zone_name,
                    "records_imported": 0,
                    "records_skipped": 0,
                    "errors": errors,
                    "warnings": warnings,
                    "validation_only": validate_only
                }
            
            # Validate records
            valid_records = []
            for i, record_data in enumerate(records_data):
                record_validation = await self.validate_import_record(record_data, i + 1)
                if record_validation["valid"]:
                    valid_records.append(record_data)
                else:
                    errors.extend(record_validation["errors"])
                    warnings.extend(record_validation["warnings"])
                    records_skipped += 1
            
            # If validation only, return results without importing
            if validate_only:
                return {
                    "success": len(errors) == 0,
                    "zone_id": None,
                    "zone_name": zone_name,
                    "records_imported": 0,
                    "records_skipped": records_skipped,
                    "errors": errors,
                    "warnings": warnings,
                    "validation_only": True,
                    "records_to_import": len(valid_records)
                }
            
            # Stop if there are validation errors
            if errors:
                return {
                    "success": False,
                    "zone_id": None,
                    "zone_name": zone_name,
                    "records_imported": 0,
                    "records_skipped": records_skipped,
                    "errors": errors,
                    "warnings": warnings,
                    "validation_only": False
                }
            
            # Import the zone
            if existing_zone and overwrite_existing:
                # Update existing zone
                zone = await self.update_zone(existing_zone.id, zone_data)
                zone_id = existing_zone.id
                
                # Delete existing records if overwriting
                if self.is_async:
                    await self.db.execute(
                        DNSRecord.__table__.delete().where(DNSRecord.zone_id == zone_id)
                    )
                else:
                    self.db.query(DNSRecord).filter(DNSRecord.zone_id == zone_id).delete()
            else:
                # Create new zone
                zone = await self.create_zone(zone_data)
                zone_id = zone.id
            
            # Import records
            from ..services.record_service import RecordService
            record_service = RecordService(self.db)
            
            for record_data in valid_records:
                try:
                    await record_service.create_record(zone_id, record_data)
                    records_imported += 1
                except Exception as e:
                    errors.append(f"Failed to import record {record_data.get('name', 'unknown')}: {str(e)}")
                    records_skipped += 1
            
            # Commit transaction
            if self.is_async:
                await self.db.commit()
            else:
                self.db.commit()
            
            logger.info(f"Imported zone '{zone_name}' with {records_imported} records")
            
            return {
                "success": len(errors) == 0,
                "zone_id": zone_id,
                "zone_name": zone_name,
                "records_imported": records_imported,
                "records_skipped": records_skipped,
                "errors": errors,
                "warnings": warnings,
                "validation_only": False
            }
            
        except Exception as e:
            logger.error(f"Zone import failed: {str(e)}")
            errors.append(f"Import failed: {str(e)}")
            
            # Rollback transaction
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            
            return {
                "success": False,
                "zone_id": None,
                "zone_name": zone_name,
                "records_imported": 0,
                "records_skipped": records_skipped,
                "errors": errors,
                "warnings": warnings,
                "validation_only": validate_only
            }
    
    async def export_zone_in_format(self, zone_id: int, format_type: str = "json") -> Optional[Dict[str, Any]]:
        """Export zone in specified format"""
        from ..schemas.dns import ZoneExportFormat
        
        # Get zone with records
        zone_data = await self.get_zone_with_records(zone_id)
        if not zone_data:
            return None
        
        zone = zone_data["zone"]
        records = zone_data["records"]
        
        if format_type.lower() == ZoneExportFormat.JSON.value:
            return await self._export_zone_json(zone, records)
        elif format_type.lower() == ZoneExportFormat.BIND.value:
            return await self._export_zone_bind(zone, records)
        elif format_type.lower() == ZoneExportFormat.CSV.value:
            return await self._export_zone_csv(zone, records)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    async def _export_zone_json(self, zone: Zone, records: List[DNSRecord]) -> Dict[str, Any]:
        """Export zone in JSON format"""
        from datetime import datetime
        
        export_data = {
            "format": "json",
            "export_timestamp": datetime.now().isoformat(),
            "export_version": "1.0",
            "zone": {
                "name": zone.name,
                "zone_type": zone.zone_type,
                "email": zone.email,
                "description": zone.description,
                "refresh": zone.refresh,
                "retry": zone.retry,
                "expire": zone.expire,
                "minimum": zone.minimum,
                "master_servers": zone.master_servers,
                "forwarders": zone.forwarders,
                "serial": zone.serial,
                "is_active": zone.is_active,
                "created_at": zone.created_at.isoformat() if zone.created_at else None,
                "updated_at": zone.updated_at.isoformat() if zone.updated_at else None
            },
            "records": [
                {
                    "name": record.name,
                    "record_type": record.record_type,
                    "value": record.value,
                    "ttl": record.ttl,
                    "priority": record.priority,
                    "weight": record.weight,
                    "port": record.port,
                    "is_active": record.is_active
                }
                for record in records if record.is_active
            ],
            "statistics": {
                "total_records": len([r for r in records if r.is_active]),
                "record_types": list(set(r.record_type for r in records if r.is_active))
            }
        }
        
        return export_data
    
    async def _export_zone_bind(self, zone: Zone, records: List[DNSRecord]) -> Dict[str, Any]:
        """Export zone in BIND zone file format"""
        from datetime import datetime
        
        # Generate BIND zone file content
        zone_file_lines = []
        
        # Zone header
        zone_file_lines.append(f"; Zone file for {zone.name}")
        zone_file_lines.append(f"; Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        zone_file_lines.append(f"; Zone type: {zone.zone_type}")
        zone_file_lines.append("")
        
        # TTL directive
        zone_file_lines.append(f"$TTL {zone.minimum}")
        zone_file_lines.append("")
        
        # SOA record (if exists)
        soa_records = [r for r in records if r.record_type == 'SOA' and r.is_active]
        if soa_records:
            soa = soa_records[0]
            zone_file_lines.append(f"@\tIN\tSOA\t{soa.value}")
        else:
            # Generate default SOA
            zone_file_lines.append(f"@\tIN\tSOA\tns1.{zone.name}. {zone.email}. (")
            zone_file_lines.append(f"\t\t\t{zone.serial}\t; Serial")
            zone_file_lines.append(f"\t\t\t{zone.refresh}\t; Refresh")
            zone_file_lines.append(f"\t\t\t{zone.retry}\t; Retry")
            zone_file_lines.append(f"\t\t\t{zone.expire}\t; Expire")
            zone_file_lines.append(f"\t\t\t{zone.minimum}\t; Minimum TTL")
            zone_file_lines.append("\t\t\t)")
        
        zone_file_lines.append("")
        
        # Other records grouped by type
        record_types = ['NS', 'A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR']
        
        for record_type in record_types:
            type_records = [r for r in records if r.record_type == record_type and r.is_active]
            if type_records:
                zone_file_lines.append(f"; {record_type} records")
                for record in type_records:
                    ttl_str = f"{record.ttl}\t" if record.ttl else ""
                    priority_str = f"{record.priority} " if record.priority else ""
                    
                    if record.record_type == 'SRV':
                        srv_data = f"{record.priority} {record.weight} {record.port} {record.value}"
                        zone_file_lines.append(f"{record.name}\t{ttl_str}IN\t{record.record_type}\t{srv_data}")
                    else:
                        zone_file_lines.append(f"{record.name}\t{ttl_str}IN\t{record.record_type}\t{priority_str}{record.value}")
                
                zone_file_lines.append("")
        
        # Add any other record types not in the standard list
        other_records = [r for r in records if r.record_type not in record_types + ['SOA'] and r.is_active]
        if other_records:
            zone_file_lines.append("; Other records")
            for record in other_records:
                ttl_str = f"{record.ttl}\t" if record.ttl else ""
                priority_str = f"{record.priority} " if record.priority else ""
                zone_file_lines.append(f"{record.name}\t{ttl_str}IN\t{record.record_type}\t{priority_str}{record.value}")
        
        zone_file_content = "\n".join(zone_file_lines)
        
        return {
            "format": "bind",
            "export_timestamp": datetime.now().isoformat(),
            "export_version": "1.0",
            "zone_name": zone.name,
            "zone_file_content": zone_file_content,
            "filename": f"db.{zone.name}",
            "statistics": {
                "total_records": len([r for r in records if r.is_active]),
                "zone_file_lines": len(zone_file_lines)
            }
        }
    
    async def _export_zone_csv(self, zone: Zone, records: List[DNSRecord]) -> Dict[str, Any]:
        """Export zone in CSV format"""
        from datetime import datetime
        import csv
        from io import StringIO
        
        # Create CSV content
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        
        # CSV header
        csv_writer.writerow([
            'name', 'type', 'value', 'ttl', 'priority', 'weight', 'port', 'active'
        ])
        
        # Write records
        for record in records:
            if record.is_active:
                csv_writer.writerow([
                    record.name,
                    record.record_type,
                    record.value,
                    record.ttl or '',
                    record.priority or '',
                    record.weight or '',
                    record.port or '',
                    'yes' if record.is_active else 'no'
                ])
        
        csv_content = csv_buffer.getvalue()
        csv_buffer.close()
        
        return {
            "format": "csv",
            "export_timestamp": datetime.now().isoformat(),
            "export_version": "1.0",
            "zone_name": zone.name,
            "csv_content": csv_content,
            "filename": f"{zone.name}_records.csv",
            "zone_info": {
                "name": zone.name,
                "type": zone.zone_type,
                "email": zone.email,
                "serial": zone.serial
            },
            "statistics": {
                "total_records": len([r for r in records if r.is_active])
            }
        }
    
    async def validate_import_record(self, record_data: Dict[str, Any], line_number: int = 0) -> Dict[str, Any]:
        """Validate a single record for import"""
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['name', 'record_type', 'value']
        for field in required_fields:
            if field not in record_data or not record_data[field]:
                errors.append(f"Line {line_number}: Missing required field '{field}'")
        
        if errors:
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Validate record type
        valid_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'NS', 'SOA']
        record_type = record_data.get('record_type', '').upper()
        if record_type not in valid_types:
            errors.append(f"Line {line_number}: Invalid record type '{record_type}'")
        
        # Validate based on record type
        value = record_data.get('value', '')
        name = record_data.get('name', '')
        
        if record_type == 'A':
            import ipaddress
            try:
                ipaddress.IPv4Address(value)
            except ValueError:
                errors.append(f"Line {line_number}: Invalid IPv4 address '{value}' for A record")
        
        elif record_type == 'AAAA':
            import ipaddress
            try:
                ipaddress.IPv6Address(value)
            except ValueError:
                errors.append(f"Line {line_number}: Invalid IPv6 address '{value}' for AAAA record")
        
        elif record_type in ['MX', 'SRV']:
            if 'priority' not in record_data or record_data['priority'] is None:
                errors.append(f"Line {line_number}: {record_type} record requires priority field")
        
        elif record_type == 'SRV':
            if 'weight' not in record_data or record_data['weight'] is None:
                errors.append(f"Line {line_number}: SRV record requires weight field")
            if 'port' not in record_data or record_data['port'] is None:
                errors.append(f"Line {line_number}: SRV record requires port field")
        
        # Validate TTL if provided
        ttl = record_data.get('ttl')
        if ttl is not None:
            try:
                ttl_int = int(ttl)
                if ttl_int < 1 or ttl_int > 2147483647:
                    errors.append(f"Line {line_number}: TTL must be between 1 and 2147483647")
            except (ValueError, TypeError):
                errors.append(f"Line {line_number}: TTL must be a valid integer")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def parse_bind_zone_file(self, zone_file_content: str, zone_name: str) -> Dict[str, Any]:
        """Parse BIND zone file format for import"""
        lines = zone_file_content.strip().split('\n')
        records = []
        errors = []
        warnings = []
        
        current_ttl = None
        current_origin = zone_name
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith(';'):
                continue
            
            # Handle $TTL directive
            if line.startswith('$TTL'):
                try:
                    current_ttl = int(line.split()[1])
                except (IndexError, ValueError):
                    errors.append(f"Line {line_num}: Invalid $TTL directive")
                continue
            
            # Handle $ORIGIN directive
            if line.startswith('$ORIGIN'):
                try:
                    current_origin = line.split()[1]
                except IndexError:
                    errors.append(f"Line {line_num}: Invalid $ORIGIN directive")
                continue
            
            # Parse DNS record
            try:
                parts = line.split()
                if len(parts) < 4:
                    warnings.append(f"Line {line_num}: Incomplete record, skipping")
                    continue
                
                name = parts[0] if parts[0] != '@' else current_origin
                
                # Handle TTL and class
                ttl = None
                class_pos = 1
                
                # Check if second field is TTL
                try:
                    ttl = int(parts[1])
                    class_pos = 2
                except ValueError:
                    ttl = current_ttl
                
                # Skip class field (usually IN)
                if parts[class_pos].upper() == 'IN':
                    type_pos = class_pos + 1
                else:
                    type_pos = class_pos
                
                if type_pos >= len(parts):
                    warnings.append(f"Line {line_num}: Missing record type, skipping")
                    continue
                
                record_type = parts[type_pos].upper()
                value_parts = parts[type_pos + 1:]
                
                if not value_parts:
                    warnings.append(f"Line {line_num}: Missing record value, skipping")
                    continue
                
                # Handle different record types
                record_data = {
                    'name': name,
                    'record_type': record_type,
                    'ttl': ttl
                }
                
                if record_type == 'MX':
                    if len(value_parts) >= 2:
                        record_data['priority'] = int(value_parts[0])
                        record_data['value'] = value_parts[1]
                    else:
                        errors.append(f"Line {line_num}: MX record missing priority or value")
                        continue
                
                elif record_type == 'SRV':
                    if len(value_parts) >= 4:
                        record_data['priority'] = int(value_parts[0])
                        record_data['weight'] = int(value_parts[1])
                        record_data['port'] = int(value_parts[2])
                        record_data['value'] = value_parts[3]
                    else:
                        errors.append(f"Line {line_num}: SRV record missing required fields")
                        continue
                
                else:
                    record_data['value'] = ' '.join(value_parts)
                
                records.append(record_data)
                
            except Exception as e:
                errors.append(f"Line {line_num}: Error parsing record - {str(e)}")
        
        return {
            "records": records,
            "errors": errors,
            "warnings": warnings,
            "total_lines": len(lines),
            "records_parsed": len(records)
        }
    
    async def parse_csv_zone_data(self, csv_content: str) -> Dict[str, Any]:
        """Parse CSV format for zone import"""
        import csv
        from io import StringIO
        
        records = []
        errors = []
        warnings = []
        
        try:
            csv_buffer = StringIO(csv_content)
            csv_reader = csv.DictReader(csv_buffer)
            
            for line_num, row in enumerate(csv_reader, 2):  # Start at 2 because of header
                try:
                    # Clean up the row data
                    record_data = {}
                    for key, value in row.items():
                        if key and value and str(value).strip():
                            clean_key = key.strip().lower()
                            clean_value = str(value).strip()
                            
                            # Map common field names
                            if clean_key in ['name', 'hostname', 'record_name']:
                                record_data['name'] = clean_value
                            elif clean_key in ['type', 'record_type', 'rtype']:
                                record_data['record_type'] = clean_value.upper()
                            elif clean_key in ['value', 'data', 'target']:
                                record_data['value'] = clean_value
                            elif clean_key == 'ttl':
                                try:
                                    record_data['ttl'] = int(clean_value)
                                except ValueError:
                                    warnings.append(f"Line {line_num}: Invalid TTL value '{clean_value}', ignoring")
                            elif clean_key == 'priority':
                                try:
                                    record_data['priority'] = int(clean_value)
                                except ValueError:
                                    warnings.append(f"Line {line_num}: Invalid priority value '{clean_value}', ignoring")
                            elif clean_key == 'weight':
                                try:
                                    record_data['weight'] = int(clean_value)
                                except ValueError:
                                    warnings.append(f"Line {line_num}: Invalid weight value '{clean_value}', ignoring")
                            elif clean_key == 'port':
                                try:
                                    record_data['port'] = int(clean_value)
                                except ValueError:
                                    warnings.append(f"Line {line_num}: Invalid port value '{clean_value}', ignoring")
                    
                    # Validate required fields
                    if 'name' in record_data and 'record_type' in record_data and 'value' in record_data:
                        records.append(record_data)
                    else:
                        missing_fields = []
                        if 'name' not in record_data:
                            missing_fields.append('name')
                        if 'record_type' not in record_data:
                            missing_fields.append('record_type')
                        if 'value' not in record_data:
                            missing_fields.append('value')
                        warnings.append(f"Line {line_num}: Missing required fields: {', '.join(missing_fields)}, skipping")
                
                except Exception as e:
                    errors.append(f"Line {line_num}: Error parsing CSV row - {str(e)}")
            
            csv_buffer.close()
            
        except Exception as e:
            errors.append(f"Error parsing CSV content: {str(e)}")
        
        return {
            "records": records,
            "errors": errors,
            "warnings": warnings,
            "records_parsed": len(records)
        }    
    
async def _emit_zone_event(self, event_type: EventType, zone: Optional[Zone], action: str, details: Dict[str, Any]):
        """Helper method to emit zone-related events"""
        try:
            user_id = get_current_user_id()
            
            # Create event data
            event_data = {
                "action": action,
                "zone_id": zone.id if zone else details.get("zone_id"),
                "zone_name": zone.name if zone else details.get("zone_name"),
                "zone_type": zone.zone_type if zone else details.get("zone_type"),
                **details
            }
            
            # Determine event priority
            priority = EventPriority.HIGH if action == "delete" else EventPriority.NORMAL
            
            # Create and emit the event
            event = create_event(
                event_type=event_type,
                category=EventCategory.DNS,
                data=event_data,
                user_id=user_id,
                priority=priority,
                metadata={
                    "service": "zone_service",
                    "action": action,
                    "zone_name": zone.name if zone else details.get("zone_name")
                }
            )
            
            await self.event_service.emit_event(event)
            
        except Exception as e:
            logger.error(f"Failed to emit zone event: {e}")
            # Don't raise the exception to avoid breaking the main operation