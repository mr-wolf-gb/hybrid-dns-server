"""
DNS Record History service for tracking changes to DNS records
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError

from .base_service import BaseService
from ..models.dns import DNSRecord, DNSRecordHistory, Zone
from ..models.auth import User
from ..core.auth_context import get_current_user_id
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class RecordHistoryService(BaseService[DNSRecordHistory]):
    """DNS Record History service for tracking and querying record changes"""
    
    def __init__(self, db: Session | AsyncSession):
        super().__init__(db, DNSRecordHistory)
    
    async def create_history_entry(self, record: DNSRecord, change_type: str, 
                                  previous_values: Optional[Dict[str, Any]] = None,
                                  change_details: Optional[Dict[str, Any]] = None) -> DNSRecordHistory:
        """Create a history entry for a DNS record change"""
        logger.debug(f"Creating history entry for record {record.id}: {change_type}")
        
        # Get current user ID
        user_id = get_current_user_id()
        
        # Prepare history data
        history_data = {
            'record_id': record.id,
            'zone_id': record.zone_id,
            'name': record.name,
            'record_type': record.record_type,
            'value': record.value,
            'ttl': record.ttl,
            'priority': record.priority,
            'weight': record.weight,
            'port': record.port,
            'is_active': record.is_active,
            'change_type': change_type,
            'changed_by': user_id,
            'previous_values': previous_values,
            'change_details': change_details
        }
        
        # Create history entry
        history_entry = await self.create(history_data)
        
        logger.info(f"Created history entry {history_entry.id} for record {record.id}: {change_type}")
        return history_entry
    
    async def get_record_history(self, record_id: int, limit: int = 50) -> List[DNSRecordHistory]:
        """Get history for a specific record"""
        logger.debug(f"Getting history for record {record_id}")
        
        filters = {"record_id": record_id}
        
        if self.is_async:
            query = select(DNSRecordHistory).filter(
                DNSRecordHistory.record_id == record_id
            ).order_by(desc(DNSRecordHistory.changed_at)).limit(limit)
            
            result = await self.db.execute(query)
            history_entries = result.scalars().all()
        else:
            history_entries = (
                self.db.query(DNSRecordHistory)
                .filter(DNSRecordHistory.record_id == record_id)
                .order_by(desc(DNSRecordHistory.changed_at))
                .limit(limit)
                .all()
            )
        
        logger.debug(f"Retrieved {len(history_entries)} history entries for record {record_id}")
        return history_entries
    
    async def get_zone_history(self, zone_id: int, limit: int = 100) -> List[DNSRecordHistory]:
        """Get history for all records in a zone"""
        logger.debug(f"Getting history for zone {zone_id}")
        
        if self.is_async:
            query = select(DNSRecordHistory).filter(
                DNSRecordHistory.zone_id == zone_id
            ).order_by(desc(DNSRecordHistory.changed_at)).limit(limit)
            
            result = await self.db.execute(query)
            history_entries = result.scalars().all()
        else:
            history_entries = (
                self.db.query(DNSRecordHistory)
                .filter(DNSRecordHistory.zone_id == zone_id)
                .order_by(desc(DNSRecordHistory.changed_at))
                .limit(limit)
                .all()
            )
        
        logger.debug(f"Retrieved {len(history_entries)} history entries for zone {zone_id}")
        return history_entries
    
    async def get_user_history(self, user_id: int, limit: int = 100) -> List[DNSRecordHistory]:
        """Get history of changes made by a specific user"""
        logger.debug(f"Getting history for user {user_id}")
        
        if self.is_async:
            query = select(DNSRecordHistory).filter(
                DNSRecordHistory.changed_by == user_id
            ).order_by(desc(DNSRecordHistory.changed_at)).limit(limit)
            
            result = await self.db.execute(query)
            history_entries = result.scalars().all()
        else:
            history_entries = (
                self.db.query(DNSRecordHistory)
                .filter(DNSRecordHistory.changed_by == user_id)
                .order_by(desc(DNSRecordHistory.changed_at))
                .limit(limit)
                .all()
            )
        
        logger.debug(f"Retrieved {len(history_entries)} history entries for user {user_id}")
        return history_entries
    
    async def search_history(self, 
                           record_id: Optional[int] = None,
                           zone_id: Optional[int] = None,
                           change_type: Optional[str] = None,
                           changed_by: Optional[int] = None,
                           date_from: Optional[datetime] = None,
                           date_to: Optional[datetime] = None,
                           record_type: Optional[str] = None,
                           record_name: Optional[str] = None,
                           skip: int = 0,
                           limit: int = 100,
                           sort_by: str = "changed_at",
                           sort_order: str = "desc") -> Dict[str, Any]:
        """Search history with multiple filters"""
        logger.debug(f"Searching history with filters")
        
        # Build the base query
        if self.is_async:
            query = select(DNSRecordHistory)
            count_query = select(func.count(DNSRecordHistory.id))
        else:
            query = self.db.query(DNSRecordHistory)
            count_query = self.db.query(func.count(DNSRecordHistory.id))
        
        # Apply filters
        conditions = []
        
        if record_id:
            conditions.append(DNSRecordHistory.record_id == record_id)
        
        if zone_id:
            conditions.append(DNSRecordHistory.zone_id == zone_id)
        
        if change_type:
            conditions.append(DNSRecordHistory.change_type == change_type)
        
        if changed_by:
            conditions.append(DNSRecordHistory.changed_by == changed_by)
        
        if date_from:
            conditions.append(DNSRecordHistory.changed_at >= date_from)
        
        if date_to:
            conditions.append(DNSRecordHistory.changed_at <= date_to)
        
        if record_type:
            conditions.append(DNSRecordHistory.record_type == record_type.upper())
        
        if record_name:
            conditions.append(DNSRecordHistory.name.ilike(f"%{record_name}%"))
        
        # Apply all conditions
        if conditions:
            if self.is_async:
                query = query.filter(and_(*conditions))
                count_query = count_query.filter(and_(*conditions))
            else:
                query = query.filter(and_(*conditions))
                count_query = count_query.filter(and_(*conditions))
        
        # Apply sorting
        if sort_by and hasattr(DNSRecordHistory, sort_by):
            sort_column = getattr(DNSRecordHistory, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        else:
            # Default sorting by changed_at descending
            query = query.order_by(desc(DNSRecordHistory.changed_at))
        
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
            history_entries = result.scalars().all()
        else:
            history_entries = query.all()
        
        # Calculate pagination info
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1
        
        logger.debug(f"History search returned {len(history_entries)} entries")
        
        return {
            "items": history_entries,
            "total": total,
            "page": current_page,
            "per_page": limit,
            "pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1
        }
    
    async def get_recent_changes(self, hours: int = 24, limit: int = 50) -> List[DNSRecordHistory]:
        """Get recent changes within the specified time period"""
        logger.debug(f"Getting recent changes from last {hours} hours")
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        if self.is_async:
            query = select(DNSRecordHistory).filter(
                DNSRecordHistory.changed_at >= cutoff_time
            ).order_by(desc(DNSRecordHistory.changed_at)).limit(limit)
            
            result = await self.db.execute(query)
            history_entries = result.scalars().all()
        else:
            history_entries = (
                self.db.query(DNSRecordHistory)
                .filter(DNSRecordHistory.changed_at >= cutoff_time)
                .order_by(desc(DNSRecordHistory.changed_at))
                .limit(limit)
                .all()
            )
        
        logger.debug(f"Retrieved {len(history_entries)} recent changes")
        return history_entries
    
    async def get_history_statistics(self, zone_id: Optional[int] = None, 
                                   days: int = 30) -> Dict[str, Any]:
        """Get statistics about record changes"""
        logger.debug(f"Getting history statistics for {days} days")
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # Base query conditions
        conditions = [DNSRecordHistory.changed_at >= cutoff_time]
        if zone_id:
            conditions.append(DNSRecordHistory.zone_id == zone_id)
        
        if self.is_async:
            # Total changes
            total_query = select(func.count(DNSRecordHistory.id)).filter(and_(*conditions))
            total_result = await self.db.execute(total_query)
            total_changes = total_result.scalar()
            
            # Changes by type
            type_query = select(
                DNSRecordHistory.change_type, 
                func.count(DNSRecordHistory.id)
            ).filter(and_(*conditions)).group_by(DNSRecordHistory.change_type)
            type_result = await self.db.execute(type_query)
            changes_by_type = dict(type_result.fetchall())
            
            # Changes by record type
            record_type_query = select(
                DNSRecordHistory.record_type, 
                func.count(DNSRecordHistory.id)
            ).filter(and_(*conditions)).group_by(DNSRecordHistory.record_type)
            record_type_result = await self.db.execute(record_type_query)
            changes_by_record_type = dict(record_type_result.fetchall())
            
            # Most active users
            user_query = select(
                DNSRecordHistory.changed_by, 
                func.count(DNSRecordHistory.id)
            ).filter(and_(*conditions)).group_by(DNSRecordHistory.changed_by).order_by(
                desc(func.count(DNSRecordHistory.id))
            ).limit(10)
            user_result = await self.db.execute(user_query)
            most_active_users = dict(user_result.fetchall())
            
        else:
            # Total changes
            total_changes = (
                self.db.query(func.count(DNSRecordHistory.id))
                .filter(and_(*conditions))
                .scalar()
            )
            
            # Changes by type
            changes_by_type = dict(
                self.db.query(DNSRecordHistory.change_type, func.count(DNSRecordHistory.id))
                .filter(and_(*conditions))
                .group_by(DNSRecordHistory.change_type)
                .all()
            )
            
            # Changes by record type
            changes_by_record_type = dict(
                self.db.query(DNSRecordHistory.record_type, func.count(DNSRecordHistory.id))
                .filter(and_(*conditions))
                .group_by(DNSRecordHistory.record_type)
                .all()
            )
            
            # Most active users
            most_active_users = dict(
                self.db.query(DNSRecordHistory.changed_by, func.count(DNSRecordHistory.id))
                .filter(and_(*conditions))
                .group_by(DNSRecordHistory.changed_by)
                .order_by(desc(func.count(DNSRecordHistory.id)))
                .limit(10)
                .all()
            )
        
        return {
            "total_changes": total_changes,
            "changes_by_type": changes_by_type,
            "changes_by_record_type": changes_by_record_type,
            "most_active_users": most_active_users,
            "period_days": days,
            "zone_id": zone_id
        }
    
    async def cleanup_old_history(self, days_to_keep: int = 365) -> int:
        """Clean up old history entries beyond the retention period"""
        logger.info(f"Cleaning up history entries older than {days_to_keep} days")
        
        cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
        
        if self.is_async:
            # Count entries to be deleted
            count_query = select(func.count(DNSRecordHistory.id)).filter(
                DNSRecordHistory.changed_at < cutoff_time
            )
            count_result = await self.db.execute(count_query)
            count_to_delete = count_result.scalar()
            
            # Delete old entries
            delete_query = select(DNSRecordHistory).filter(
                DNSRecordHistory.changed_at < cutoff_time
            )
            result = await self.db.execute(delete_query)
            old_entries = result.scalars().all()
            
            for entry in old_entries:
                await self.db.delete(entry)
            
            await self.db.commit()
            
        else:
            # Count and delete old entries
            old_entries = (
                self.db.query(DNSRecordHistory)
                .filter(DNSRecordHistory.changed_at < cutoff_time)
                .all()
            )
            
            count_to_delete = len(old_entries)
            
            for entry in old_entries:
                self.db.delete(entry)
            
            self.db.commit()
        
        logger.info(f"Cleaned up {count_to_delete} old history entries")
        return count_to_delete