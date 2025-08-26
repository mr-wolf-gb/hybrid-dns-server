"""
DNS Record service with authentication integration, comprehensive CRUD operations, and event broadcasting
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, asc
from sqlalchemy.exc import SQLAlchemyError

from .base_service import BaseService
from ..models.dns import DNSRecord, Zone
from ..schemas.dns import DNSValidators
from ..core.auth_context import get_current_user_id, track_user_action
from ..core.logging_config import get_logger
from .enhanced_event_service import get_enhanced_event_service
from ..websocket.event_types import EventType, EventPriority, EventCategory, create_event

logger = get_logger(__name__)


class RecordService(BaseService[DNSRecord]):
    """DNS Record service with authentication, comprehensive CRUD operations, and event broadcasting"""
    
    def __init__(self, db: Session | AsyncSession):
        super().__init__(db, DNSRecord)
        self.event_service = get_enhanced_event_service()
    
    async def create_record(self, zone_id: int, record_data: Dict[str, Any]) -> DNSRecord:
        """Create a new DNS record with validation and user tracking"""
        logger.info(f"Creating DNS record in zone {zone_id}: {record_data.get('name')} {record_data.get('record_type')}")
        
        # Validate zone exists and is active
        zone = await self._get_zone(zone_id)
        if not zone:
            raise ValueError(f"Zone with ID {zone_id} not found")
        if not zone.is_active:
            raise ValueError(f"Cannot create record in inactive zone: {zone.name}")
        
        # Validate record data
        validation_result = await self.validate_record_data(record_data, zone_id)
        if not validation_result["valid"]:
            raise ValueError(f"Record validation failed: {'; '.join(validation_result['errors'])}")
        
        # Set zone_id and defaults
        record_data['zone_id'] = zone_id
        record_data.setdefault('is_active', True)
        
        # Validate record type-specific data
        await self._validate_record_type_specific(record_data)
        
        # Create the record
        record = await self.create(record_data, track_action=True)
        
        # Create history entry
        await self._create_history_entry(record, "create")
        
        # Emit record creation event
        await self._emit_record_event(
            event_type=EventType.RECORD_CREATED,
            record=record,
            zone=zone,
            action="create",
            details={
                "record_name": record.name,
                "record_type": record.record_type,
                "record_value": record.value,
                "zone_name": zone.name,
                "zone_id": zone_id,
                "ttl": record.ttl,
                "priority": record.priority
            }
        )
        
        logger.info(f"Created DNS record {record.name} {record.record_type} in zone {zone.name}")
        
        # Track specific action with more details
        track_user_action(
            action="dns_record_create",
            resource_type="dns_record",
            resource_id=str(record.id),
            details=f"Created {record.record_type} record '{record.name}' with value '{record.value}' in zone '{zone.name}'",
            db=self.db
        )
        
        return record
    
    async def update_record(self, record_id: int, record_data: Dict[str, Any]) -> Optional[DNSRecord]:
        """Update a DNS record with validation and user tracking"""
        logger.info(f"Updating DNS record ID: {record_id}")
        
        # Get existing record
        record = await self.get_by_id(record_id)
        if not record:
            logger.warning(f"DNS record {record_id} not found for update")
            return None
        
        # Store previous values for history
        previous_values = {
            'name': record.name,
            'record_type': record.record_type,
            'value': record.value,
            'ttl': record.ttl,
            'priority': record.priority,
            'weight': record.weight,
            'port': record.port,
            'is_active': record.is_active
        }
        
        # Get zone for validation
        zone = await self._get_zone(record.zone_id)
        if not zone:
            raise ValueError(f"Zone with ID {record.zone_id} not found")
        
        # Validate updated record data
        merged_data = {
            'name': record_data.get('name', record.name),
            'record_type': record_data.get('record_type', record.record_type),
            'value': record_data.get('value', record.value),
            'ttl': record_data.get('ttl', record.ttl),
            'priority': record_data.get('priority', record.priority),
            'weight': record_data.get('weight', record.weight),
            'port': record_data.get('port', record.port)
        }
        
        validation_result = await self.validate_record_data(merged_data, record.zone_id, record_id)
        if not validation_result["valid"]:
            raise ValueError(f"Record validation failed: {'; '.join(validation_result['errors'])}")
        
        # Validate record type-specific data if type is being changed
        if 'record_type' in record_data or any(key in record_data for key in ['value', 'priority', 'weight', 'port']):
            await self._validate_record_type_specific(merged_data)
        
        # Update the record
        updated_record = await self.update(record_id, record_data, track_action=True)
        
        if updated_record:
            # Create history entry with previous values
            change_details = {field: record_data[field] for field in record_data.keys()}
            await self._create_history_entry(updated_record, "update", previous_values, change_details)
            
            # Emit record update event
            await self._emit_record_event(
                event_type=EventType.RECORD_UPDATED,
                record=updated_record,
                zone=zone,
                action="update",
                details={
                    "record_name": updated_record.name,
                    "record_type": updated_record.record_type,
                    "record_value": updated_record.value,
                    "zone_name": zone.name,
                    "zone_id": record.zone_id,
                    "updated_fields": list(record_data.keys()),
                    "previous_values": previous_values,
                    "ttl": updated_record.ttl,
                    "priority": updated_record.priority
                }
            )
            
            logger.info(f"Updated DNS record {updated_record.name} {updated_record.record_type} in zone {zone.name}")
            
            # Track specific action with more details
            track_user_action(
                action="dns_record_update",
                resource_type="dns_record",
                resource_id=str(record_id),
                details=f"Updated {updated_record.record_type} record '{updated_record.name}' in zone '{zone.name}'",
                db=self.db
            )
        
        return updated_record
    
    async def delete_record(self, record_id: int) -> bool:
        """Delete a DNS record with user tracking"""
        logger.info(f"Deleting DNS record ID: {record_id}")
        
        # Get record info before deletion for logging
        record = await self.get_by_id(record_id)
        if not record:
            logger.warning(f"DNS record {record_id} not found for deletion")
            return False
        
        # Create history entry before deletion
        await self._create_history_entry(record, "delete")
        
        # Get zone for logging
        zone = await self._get_zone(record.zone_id)
        zone_name = zone.name if zone else f"Zone ID {record.zone_id}"
        
        record_info = f"{record.name} {record.record_type}"
        record_name = record.name
        record_type = record.record_type
        record_value = record.value
        zone_id = record.zone_id
        
        success = await self.delete(record_id, track_action=True)
        
        if success:
            # Emit record deletion event
            await self._emit_record_event(
                event_type=EventType.RECORD_DELETED,
                record=None,  # Record is deleted, so pass None
                zone=zone,
                action="delete",
                details={
                    "record_id": record_id,
                    "record_name": record_name,
                    "record_type": record_type,
                    "record_value": record_value,
                    "zone_name": zone_name,
                    "zone_id": zone_id
                }
            )
            
            logger.info(f"Deleted DNS record {record_info} from zone {zone_name}")
            
            # Track specific action with more details
            track_user_action(
                action="dns_record_delete",
                resource_type="dns_record",
                resource_id=str(record_id),
                details=f"Deleted {record_type} record '{record_name}' from zone '{zone_name}'",
                db=self.db
            )
        
        return success
    
    async def get_record(self, record_id: int) -> Optional[DNSRecord]:
        """Get a DNS record by ID"""
        return await self.get_by_id(record_id)
    
    async def get_records(self, zone_id: Optional[int] = None, 
                         record_type: Optional[str] = None,
                         name: Optional[str] = None,
                         active_only: bool = True,
                         skip: int = 0,
                         limit: int = 100,
                         search: Optional[str] = None,
                         sort_by: Optional[str] = None,
                         sort_order: str = "asc") -> Dict[str, Any]:
        """Get DNS records with enhanced filtering and pagination"""
        
        # Build the base query
        if self.is_async:
            query = select(DNSRecord)
            count_query = select(func.count(DNSRecord.id))
        else:
            query = self.db.query(DNSRecord)
            count_query = self.db.query(func.count(DNSRecord.id))
        
        # Apply filters
        conditions = []
        
        if zone_id:
            conditions.append(DNSRecord.zone_id == zone_id)
        
        if record_type:
            conditions.append(DNSRecord.record_type == record_type.upper())
        
        if name:
            conditions.append(DNSRecord.name.ilike(f"%{name}%"))
        
        if active_only:
            conditions.append(DNSRecord.is_active == True)
        
        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            search_conditions = [
                DNSRecord.name.ilike(search_term),
                DNSRecord.value.ilike(search_term),
                DNSRecord.record_type.ilike(search_term)
            ]
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
        if sort_by and hasattr(DNSRecord, sort_by):
            sort_column = getattr(DNSRecord, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            # Default sorting by name, then record type
            query = query.order_by(asc(DNSRecord.name), asc(DNSRecord.record_type))
        
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
            records = result.scalars().all()
        else:
            records = query.all()
        
        # Calculate pagination info
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1
        
        return {
            "items": records,
            "total": total,
            "page": current_page,
            "per_page": limit,
            "pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1
        }
    
    async def get_records_by_zone(self, zone_id: int, active_only: bool = True) -> List[DNSRecord]:
        """Get all DNS records for a specific zone"""
        filters = {"zone_id": zone_id}
        if active_only:
            filters["is_active"] = True
        
        return await self.get_all(filters=filters)
    
    async def get_records_by_type(self, record_type: str, zone_id: Optional[int] = None, 
                                 active_only: bool = True) -> List[DNSRecord]:
        """Get DNS records by type, optionally filtered by zone"""
        filters = {"record_type": record_type.upper()}
        if zone_id:
            filters["zone_id"] = zone_id
        if active_only:
            filters["is_active"] = True
        
        return await self.get_all(filters=filters)
    
    async def get_record_zone_id(self, record_id: int) -> Optional[int]:
        """Get the zone ID for a specific record"""
        record = await self.get_by_id(record_id)
        return record.zone_id if record else None
    
    async def toggle_record(self, record_id: int) -> Optional[DNSRecord]:
        """Toggle record active status"""
        record = await self.get_by_id(record_id)
        if not record:
            return None
        
        previous_status = record.is_active
        new_status = not record.is_active
        updated_record = await self.update(record_id, {"is_active": new_status}, track_action=True)
        
        if updated_record:
            # Create history entry
            change_type = "activate" if new_status else "deactivate"
            previous_values = {"is_active": previous_status}
            change_details = {"is_active": new_status}
            await self._create_history_entry(updated_record, change_type, previous_values, change_details)
            
            status_text = "activated" if new_status else "deactivated"
            logger.info(f"DNS record {record.name} {record.record_type} {status_text}")
            
            # Track specific action
            track_user_action(
                action=f"dns_record_{'activate' if new_status else 'deactivate'}",
                resource_type="dns_record",
                resource_id=str(record_id),
                details=f"DNS record {record.name} {record.record_type} {status_text}",
                db=self.db
            )
        
        return updated_record
    
    async def bulk_create_records(self, zone_id: int, records_data: List[Dict[str, Any]]) -> List[DNSRecord]:
        """Bulk create multiple DNS records"""
        logger.info(f"Bulk creating {len(records_data)} DNS records in zone {zone_id}")
        
        # Validate zone exists and is active
        zone = await self._get_zone(zone_id)
        if not zone:
            raise ValueError(f"Zone with ID {zone_id} not found")
        if not zone.is_active:
            raise ValueError(f"Cannot create records in inactive zone: {zone.name}")
        
        created_records = []
        errors = []
        
        for i, record_data in enumerate(records_data):
            try:
                record = await self.create_record(zone_id, record_data)
                created_records.append(record)
            except Exception as e:
                error_msg = f"Record {i+1}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Failed to create record {i+1} in bulk operation: {e}")
        
        # Emit bulk operation progress event
        await self._emit_bulk_operation_event(
            event_type=EventType.BULK_OPERATION_PROGRESS,
            zone=zone,
            operation="bulk_create",
            total_records=len(records_data),
            processed_records=len(created_records),
            failed_records=len(errors),
            errors=errors[:5]  # Limit errors in event
        )
        
        logger.info(f"Bulk created {len(created_records)} records, {len(errors)} errors")
        
        if errors:
            # Log errors but don't fail the entire operation
            logger.warning(f"Bulk create had {len(errors)} errors: {'; '.join(errors[:5])}")
        
        return created_records
    
    async def bulk_update_records(self, record_ids: List[int], update_data: Dict[str, Any]) -> List[DNSRecord]:
        """Bulk update multiple DNS records"""
        logger.info(f"Bulk updating {len(record_ids)} DNS records")
        
        updated_records = []
        for record_id in record_ids:
            try:
                updated_record = await self.update_record(record_id, update_data)
                if updated_record:
                    updated_records.append(updated_record)
            except Exception as e:
                logger.error(f"Failed to update record {record_id} in bulk operation: {e}")
                continue
        
        logger.info(f"Successfully updated {len(updated_records)} records")
        return updated_records
    
    async def bulk_delete_records(self, record_ids: List[int]) -> int:
        """Bulk delete multiple DNS records"""
        logger.info(f"Bulk deleting {len(record_ids)} DNS records")
        
        deleted_count = 0
        for record_id in record_ids:
            try:
                if await self.delete_record(record_id):
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete record {record_id} in bulk operation: {e}")
                continue
        
        logger.info(f"Successfully deleted {deleted_count} records")
        return deleted_count
    
    async def bulk_toggle_records(self, record_ids: List[int], active: bool) -> List[DNSRecord]:
        """Bulk toggle record active status"""
        logger.info(f"Bulk {'activating' if active else 'deactivating'} {len(record_ids)} DNS records")
        
        updated_records = []
        for record_id in record_ids:
            try:
                updated_record = await self.update(record_id, {"is_active": active}, track_action=True)
                if updated_record:
                    updated_records.append(updated_record)
                    
                    # Track specific action
                    action = "dns_record_bulk_activate" if active else "dns_record_bulk_deactivate"
                    track_user_action(
                        action=action,
                        resource_type="dns_record",
                        resource_id=str(record_id),
                        details=f"DNS record {updated_record.name} {updated_record.record_type} {'activated' if active else 'deactivated'} in bulk operation",
                        db=self.db
                    )
            except Exception as e:
                logger.error(f"Failed to toggle record {record_id}: {e}")
                continue
        
        logger.info(f"Successfully {'activated' if active else 'deactivated'} {len(updated_records)} records")
        return updated_records
    
    async def search_records(self, search_term: str, zone_id: Optional[int] = None,
                           record_type: Optional[str] = None, active_only: bool = True,
                           skip: int = 0, limit: int = 100) -> List[DNSRecord]:
        """Search DNS records by name or value"""
        filters = {}
        
        if zone_id:
            filters['zone_id'] = zone_id
        if record_type:
            filters['record_type'] = record_type.upper()
        if active_only:
            filters['is_active'] = True
        
        if self.is_async:
            query = select(DNSRecord)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(DNSRecord, key):
                    query = query.filter(getattr(DNSRecord, key) == value)
            
            # Add search condition
            search_condition = or_(
                DNSRecord.name.ilike(f'%{search_term}%'),
                DNSRecord.value.ilike(f'%{search_term}%')
            )
            
            query = query.filter(search_condition).offset(skip).limit(limit)
            result = await self.db.execute(query)
            return result.scalars().all()
        else:
            query = self.db.query(DNSRecord)
            
            # Apply filters
            for key, value in filters.items():
                if hasattr(DNSRecord, key):
                    query = query.filter(getattr(DNSRecord, key) == value)
            
            # Add search condition
            search_condition = or_(
                DNSRecord.name.ilike(f'%{search_term}%'),
                DNSRecord.value.ilike(f'%{search_term}%')
            )
            
            return query.filter(search_condition).offset(skip).limit(limit).all()
    
    async def get_record_statistics(self, zone_id: Optional[int] = None) -> Dict[str, Any]:
        """Get statistics about DNS records"""
        
        if self.is_async:
            # Base query
            base_query = select(DNSRecord)
            if zone_id:
                base_query = base_query.filter(DNSRecord.zone_id == zone_id)
            
            # Total records
            total_query = select(func.count(DNSRecord.id))
            if zone_id:
                total_query = total_query.filter(DNSRecord.zone_id == zone_id)
            result = await self.db.execute(total_query)
            total_records = result.scalar()
            
            # Active records
            active_query = select(func.count(DNSRecord.id)).filter(DNSRecord.is_active == True)
            if zone_id:
                active_query = active_query.filter(DNSRecord.zone_id == zone_id)
            result = await self.db.execute(active_query)
            active_records = result.scalar()
            
            # Records by type
            type_query = select(DNSRecord.record_type, func.count(DNSRecord.id)).group_by(DNSRecord.record_type)
            if zone_id:
                type_query = type_query.filter(DNSRecord.zone_id == zone_id)
            result = await self.db.execute(type_query)
            records_by_type = dict(result.fetchall())
            
        else:
            # Base query
            base_query = self.db.query(DNSRecord)
            if zone_id:
                base_query = base_query.filter(DNSRecord.zone_id == zone_id)
            
            # Total records
            total_records = base_query.count()
            
            # Active records
            active_records = base_query.filter(DNSRecord.is_active == True).count()
            
            # Records by type
            records_by_type = dict(
                base_query.with_entities(DNSRecord.record_type, func.count(DNSRecord.id))
                .group_by(DNSRecord.record_type)
                .all()
            )
        
        return {
            "total_records": total_records,
            "active_records": active_records,
            "inactive_records": total_records - active_records,
            "records_by_type": records_by_type,
            "zone_id": zone_id
        }
    
    async def validate_record_data(self, record_data: Dict[str, Any], zone_id: int, 
                                  record_id: Optional[int] = None) -> Dict[str, Any]:
        """Validate DNS record data and return validation results"""
        errors = []
        warnings = []
        
        # Required fields
        if not record_data.get('name'):
            errors.append("Record name is required")
        elif len(record_data['name']) > 255:
            errors.append("Record name must be 255 characters or less")
        
        if not record_data.get('record_type'):
            errors.append("Record type is required")
        elif record_data['record_type'].upper() not in ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'NS', 'SOA']:
            errors.append(f"Invalid record type: {record_data['record_type']}")
        
        if not record_data.get('value'):
            errors.append("Record value is required")
        elif len(record_data['value']) > 500:
            errors.append("Record value must be 500 characters or less")
        
        # TTL validation
        if record_data.get('ttl') is not None:
            ttl = record_data['ttl']
            if not isinstance(ttl, int) or ttl < 60 or ttl > 86400:
                errors.append("TTL must be between 60 and 86400 seconds")
        
        # Priority validation (for MX and SRV records)
        if record_data.get('priority') is not None:
            priority = record_data['priority']
            if not isinstance(priority, int) or priority < 0 or priority > 65535:
                errors.append("Priority must be between 0 and 65535")
        
        # Weight validation (for SRV records)
        if record_data.get('weight') is not None:
            weight = record_data['weight']
            if not isinstance(weight, int) or weight < 0 or weight > 65535:
                errors.append("Weight must be between 0 and 65535")
        
        # Port validation (for SRV records)
        if record_data.get('port') is not None:
            port = record_data['port']
            if not isinstance(port, int) or port < 1 or port > 65535:
                errors.append("Port must be between 1 and 65535")
        
        # Record type-specific validation
        if record_data.get('record_type') and record_data.get('value'):
            try:
                await self._validate_record_value_format(
                    record_data['record_type'].upper(), 
                    record_data['value']
                )
            except ValueError as e:
                errors.append(str(e))
        
        # Check for duplicate records (same name and type in zone)
        if record_data.get('name') and record_data.get('record_type'):
            duplicate_count = await self._check_duplicate_record(
                zone_id, 
                record_data['name'], 
                record_data['record_type'].upper(),
                record_id
            )
            if duplicate_count > 0:
                # Allow multiple A/AAAA records for load balancing
                if record_data['record_type'].upper() not in ['A', 'AAAA', 'MX', 'TXT']:
                    errors.append(f"Record '{record_data['name']}' with type '{record_data['record_type']}' already exists in this zone")
                else:
                    warnings.append(f"Multiple {record_data['record_type']} records exist for '{record_data['name']}'")
        
        # CNAME specific validation
        if record_data.get('record_type', '').upper() == 'CNAME':
            # CNAME records cannot coexist with other record types for the same name
            other_records_count = await self._check_other_records_for_name(
                zone_id, 
                record_data['name'], 
                record_id
            )
            if other_records_count > 0:
                errors.append("CNAME records cannot coexist with other record types for the same name")
        
        # MX and SRV records must have priority
        if record_data.get('record_type', '').upper() in ['MX', 'SRV']:
            if record_data.get('priority') is None:
                errors.append(f"{record_data['record_type']} records must have a priority value")
        
        # SRV records must have weight and port
        if record_data.get('record_type', '').upper() == 'SRV':
            if record_data.get('weight') is None:
                errors.append("SRV records must have a weight value")
            if record_data.get('port') is None:
                errors.append("SRV records must have a port value")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def _get_zone(self, zone_id: int) -> Optional[Zone]:
        """Get zone by ID"""
        if self.is_async:
            result = await self.db.execute(select(Zone).filter(Zone.id == zone_id))
            return result.scalar_one_or_none()
        else:
            return self.db.query(Zone).filter(Zone.id == zone_id).first()
    
    async def _validate_record_type_specific(self, record_data: Dict[str, Any]) -> None:
        """Validate record type-specific requirements"""
        record_type = record_data.get('record_type', '').upper()
        
        # MX and SRV records require priority
        if record_type in ['MX', 'SRV'] and record_data.get('priority') is None:
            raise ValueError(f"{record_type} records must have a priority value")
        
        # SRV records require weight and port
        if record_type == 'SRV':
            if record_data.get('weight') is None:
                raise ValueError("SRV records must have a weight value")
            if record_data.get('port') is None:
                raise ValueError("SRV records must have a port value")
        
        # NAPTR records require priority (order) and weight (preference)
        if record_type == 'NAPTR':
            if record_data.get('priority') is None:
                raise ValueError("NAPTR records must have a priority (order) value")
            if record_data.get('weight') is None:
                raise ValueError("NAPTR records must have a weight (preference) value")
        
        # CAA records require priority (flags)
        if record_type == 'CAA' and record_data.get('priority') is None:
            raise ValueError("CAA records must have a priority (flags) value")
        
        # Other record types should not have priority, weight, or port
        if record_type not in ['MX', 'SRV', 'NAPTR', 'CAA']:
            if record_data.get('priority') is not None:
                raise ValueError(f"{record_type} records cannot have a priority value")
            if record_data.get('weight') is not None:
                raise ValueError(f"{record_type} records cannot have a weight value")
            if record_data.get('port') is not None:
                raise ValueError(f"{record_type} records cannot have a port value")
        
        # Validate record name format for specific types
        record_name = record_data.get('name', '').lower()
        
        # SRV records must follow _service._proto.name format
        if record_type == 'SRV':
            if not record_name.startswith('_') or record_name.count('._') < 1:
                raise ValueError("SRV record name must follow _service._proto.name format (e.g., _http._tcp)")
        
        # DMARC records must be _dmarc
        if record_type == 'TXT' and 'v=DMARC1' in record_data.get('value', ''):
            if not record_name.startswith('_dmarc'):
                raise ValueError("DMARC TXT records must have name starting with '_dmarc'")
        
        # SPF records should be at zone apex or specific subdomain
        if record_type == 'TXT' and record_data.get('value', '').startswith('v=spf1'):
            # SPF records are typically at @ (zone apex) but can be elsewhere
            pass  # No specific name validation needed
        
        # DKIM records must follow _selector._domainkey format
        if record_type == 'TXT' and 'v=DKIM1' in record_data.get('value', ''):
            if not (record_name.startswith('_') and '._domainkey' in record_name):
                raise ValueError("DKIM TXT records must follow _selector._domainkey.domain format")
        
        # Validate CNAME restrictions
        if record_type == 'CNAME':
            if record_name in ['@', '']:
                raise ValueError("CNAME records cannot be created at the zone apex (@)")
        
        # Validate PTR record names for reverse zones
        if record_type == 'PTR':
            # PTR records in reverse zones should have numeric names
            if record_name.replace('.', '').isdigit():
                # This looks like a reverse zone PTR record, which is valid
                pass
            elif not record_name or record_name == '@':
                # PTR at zone apex might be valid in some cases
                pass
            else:
                # Regular PTR record, validate as hostname
                try:
                    from ..schemas.dns import DNSValidators
                    DNSValidators.validate_hostname_format(record_name)
                except ValueError:
                    # Allow it anyway, as PTR records can have various formats
                    pass
    
    async def _validate_record_value_format(self, record_type: str, value: str) -> None:
        """Validate record value format based on record type"""
        try:
            if record_type == 'A':
                DNSValidators.validate_ipv4_address(value)
            elif record_type == 'AAAA':
                DNSValidators.validate_ipv6_address(value)
            elif record_type == 'CNAME':
                DNSValidators.validate_cname_record_format(value)
            elif record_type == 'MX':
                DNSValidators.validate_mx_record_format(value)
            elif record_type == 'NS':
                DNSValidators.validate_ns_record_format(value)
            elif record_type == 'PTR':
                DNSValidators.validate_ptr_record_format(value)
            elif record_type == 'SRV':
                DNSValidators.validate_srv_record_format(value)
            elif record_type == 'TXT':
                DNSValidators.validate_txt_record_format(value)
            elif record_type == 'SOA':
                DNSValidators.validate_soa_record_format(value)
            elif record_type == 'CAA':
                DNSValidators.validate_caa_record_format(value)
            elif record_type == 'SSHFP':
                DNSValidators.validate_sshfp_record_format(value)
            elif record_type == 'TLSA':
                DNSValidators.validate_tlsa_record_format(value)
            elif record_type == 'NAPTR':
                DNSValidators.validate_naptr_record_format(value)
            elif record_type == 'LOC':
                DNSValidators.validate_loc_record_format(value)
            elif record_type == 'URL':
                DNSValidators.validate_url_record_format(value)
            # Add more record type validations as needed
        except ValueError as e:
            raise ValueError(f"Invalid {record_type} record format: {str(e)}")
    
    async def _check_duplicate_record(self, zone_id: int, name: str, record_type: str, 
                                    exclude_record_id: Optional[int] = None) -> int:
        """Check for duplicate records in the same zone"""
        if self.is_async:
            query = select(func.count(DNSRecord.id)).filter(
                DNSRecord.zone_id == zone_id,
                DNSRecord.name == name,
                DNSRecord.record_type == record_type,
                DNSRecord.is_active == True
            )
            if exclude_record_id:
                query = query.filter(DNSRecord.id != exclude_record_id)
            
            result = await self.db.execute(query)
            return result.scalar()
        else:
            query = self.db.query(func.count(DNSRecord.id)).filter(
                DNSRecord.zone_id == zone_id,
                DNSRecord.name == name,
                DNSRecord.record_type == record_type,
                DNSRecord.is_active == True
            )
            if exclude_record_id:
                query = query.filter(DNSRecord.id != exclude_record_id)
            
            return query.scalar()
    
    async def _check_other_records_for_name(self, zone_id: int, name: str, 
                                          exclude_record_id: Optional[int] = None) -> int:
        """Check for other records with the same name (for CNAME validation)"""
        if self.is_async:
            query = select(func.count(DNSRecord.id)).filter(
                DNSRecord.zone_id == zone_id,
                DNSRecord.name == name,
                DNSRecord.record_type != 'CNAME',
                DNSRecord.is_active == True
            )
            if exclude_record_id:
                query = query.filter(DNSRecord.id != exclude_record_id)
            
            result = await self.db.execute(query)
            return result.scalar()
        else:
            query = self.db.query(func.count(DNSRecord.id)).filter(
                DNSRecord.zone_id == zone_id,
                DNSRecord.name == name,
                DNSRecord.record_type != 'CNAME',
                DNSRecord.is_active == True
            )
            if exclude_record_id:
                query = query.filter(DNSRecord.id != exclude_record_id)
            
            return query.scalar()
    
    async def import_records_from_zone_file(self, zone_id: int, zone_file_content: str) -> Dict[str, Any]:
        """Import DNS records from a zone file format"""
        logger.info(f"Importing records from zone file for zone {zone_id}")
        
        # Validate zone exists
        zone = await self._get_zone(zone_id)
        if not zone:
            raise ValueError(f"Zone with ID {zone_id} not found")
        
        imported_records = []
        errors = []
        
        # Parse zone file content (basic implementation)
        lines = zone_file_content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith(';') or line.startswith('#'):
                continue
            
            # Skip SOA and NS records at zone level
            if line.startswith('@') or line.startswith(zone.name):
                continue
            
            try:
                # Basic zone file parsing (simplified)
                parts = line.split()
                if len(parts) >= 3:
                    name = parts[0]
                    record_type = parts[1] if parts[1].upper() in ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'NS'] else parts[2]
                    value_start = 2 if parts[1].upper() in ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'PTR', 'NS'] else 3
                    value = ' '.join(parts[value_start:])
                    
                    record_data = {
                        'name': name,
                        'record_type': record_type.upper(),
                        'value': value
                    }
                    
                    # Handle MX records with priority
                    if record_type.upper() == 'MX' and len(parts) >= 4:
                        try:
                            record_data['priority'] = int(parts[value_start])
                            record_data['value'] = ' '.join(parts[value_start + 1:])
                        except ValueError:
                            pass
                    
                    record = await self.create_record(zone_id, record_data)
                    imported_records.append(record)
                    
            except Exception as e:
                error_msg = f"Line {line_num}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Failed to import record from line {line_num}: {e}")
        
        logger.info(f"Imported {len(imported_records)} records, {len(errors)} errors")
        
        return {
            "imported_count": len(imported_records),
            "error_count": len(errors),
            "errors": errors,
            "records": imported_records
        }
    
    async def export_records_to_zone_file(self, zone_id: int) -> str:
        """Export DNS records to zone file format"""
        logger.info(f"Exporting records to zone file format for zone {zone_id}")
        
        # Get zone and records
        zone = await self._get_zone(zone_id)
        if not zone:
            raise ValueError(f"Zone with ID {zone_id} not found")
        
        records = await self.get_records_by_zone(zone_id, active_only=True)
        
        # Generate zone file content
        zone_file_lines = [
            f"; Zone file for {zone.name}",
            f"; Generated on {datetime.now().isoformat()}",
            f"; Serial: {zone.serial}",
            "",
            f"$ORIGIN {zone.name}.",
            f"$TTL {zone.minimum}",
            "",
            f"@ IN SOA {zone.name}. {zone.email.replace('@', '.')}. (",
            f"    {zone.serial}  ; Serial",
            f"    {zone.refresh}  ; Refresh",
            f"    {zone.retry}    ; Retry", 
            f"    {zone.expire}   ; Expire",
            f"    {zone.minimum}  ; Minimum TTL",
            ")",
            ""
        ]
        
        # Add records
        for record in sorted(records, key=lambda r: (r.name, r.record_type)):
            ttl_str = f" {record.ttl}" if record.ttl else ""
            
            if record.record_type == 'MX':
                line = f"{record.name}{ttl_str} IN {record.record_type} {record.priority} {record.value}"
            elif record.record_type == 'SRV':
                line = f"{record.name}{ttl_str} IN {record.record_type} {record.priority} {record.weight} {record.port} {record.value}"
            else:
                line = f"{record.name}{ttl_str} IN {record.record_type} {record.value}"
            
            zone_file_lines.append(line)
        
        return '\n'.join(zone_file_lines)
    
    async def _create_history_entry(self, record: DNSRecord, change_type: str, 
                                   previous_values: Optional[Dict[str, Any]] = None,
                                   change_details: Optional[Dict[str, Any]] = None) -> None:
        """Create a history entry for a DNS record change"""
        try:
            from .record_history_service import RecordHistoryService
            history_service = RecordHistoryService(self.db)
            await history_service.create_history_entry(record, change_type, previous_values, change_details)
        except Exception as e:
            # Log error but don't fail the main operation
            logger.error(f"Failed to create history entry for record {record.id}: {e}") 
   
    async def _emit_record_event(self, event_type: EventType, record: Optional[DNSRecord], 
                                zone: Zone, action: str, details: Dict[str, Any]):
        """Helper method to emit record-related events"""
        try:
            user_id = get_current_user_id()
            
            # Create event data
            event_data = {
                "action": action,
                "record_id": record.id if record else details.get("record_id"),
                "record_name": record.name if record else details.get("record_name"),
                "record_type": record.record_type if record else details.get("record_type"),
                "record_value": record.value if record else details.get("record_value"),
                "zone_id": zone.id,
                "zone_name": zone.name,
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
                    "service": "record_service",
                    "action": action,
                    "record_type": record.record_type if record else details.get("record_type"),
                    "zone_name": zone.name
                }
            )
            
            await self.event_service.emit_event(event)
            
        except Exception as e:
            logger.error(f"Failed to emit record event: {e}")
            # Don't raise the exception to avoid breaking the main operation
    
    async def _emit_bulk_operation_event(self, event_type: EventType, zone: Zone, 
                                        operation: str, total_records: int, 
                                        processed_records: int, failed_records: int,
                                        errors: List[str] = None):
        """Helper method to emit bulk operation events"""
        try:
            user_id = get_current_user_id()
            
            # Create event data
            event_data = {
                "operation": operation,
                "zone_id": zone.id,
                "zone_name": zone.name,
                "total_records": total_records,
                "processed_records": processed_records,
                "failed_records": failed_records,
                "success_rate": round((processed_records / total_records * 100) if total_records > 0 else 0, 2),
                "errors": errors or []
            }
            
            # Determine event priority based on success rate
            success_rate = (processed_records / total_records * 100) if total_records > 0 else 0
            priority = EventPriority.HIGH if success_rate < 50 else EventPriority.NORMAL
            
            # Create and emit the event
            event = create_event(
                event_type=event_type,
                category=EventCategory.DNS,
                data=event_data,
                user_id=user_id,
                priority=priority,
                metadata={
                    "service": "record_service",
                    "operation": operation,
                    "zone_name": zone.name,
                    "success_rate": success_rate
                }
            )
            
            await self.event_service.emit_event(event)
            
        except Exception as e:
            logger.error(f"Failed to emit bulk operation event: {e}")
            # Don't raise the exception to avoid breaking the main operation