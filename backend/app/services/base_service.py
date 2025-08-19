"""
Base service class with authentication integration
"""

from typing import Optional, Dict, Any, Type, TypeVar, Generic
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from ..core.auth_context import get_current_user_id, track_user_action
from ..core.logging_config import get_logger

T = TypeVar('T')

logger = get_logger(__name__)


class BaseService(Generic[T]):
    """Base service class with authentication and audit logging"""
    
    def __init__(self, db: Session | AsyncSession, model_class: Type[T]):
        self.db = db
        self.model_class = model_class
        self.resource_type = model_class.__name__.lower()
        self.is_async = isinstance(db, AsyncSession)
    
    async def create(self, data: Dict[str, Any], track_action: bool = True) -> T:
        """Create a new instance with user tracking"""
        try:
            # Add user tracking fields if they exist
            user_id = get_current_user_id()
            if user_id:
                if hasattr(self.model_class, 'created_by'):
                    data['created_by'] = user_id
                if hasattr(self.model_class, 'updated_by'):
                    data['updated_by'] = user_id
            
            # Create the instance
            instance = self.model_class(**data)
            self.db.add(instance)
            
            if self.is_async:
                await self.db.flush()  # Flush to get the ID
            else:
                self.db.flush()
            
            # Track the action
            if track_action:
                track_user_action(
                    action="create",
                    resource_type=self.resource_type,
                    resource_id=str(instance.id),
                    details=f"Created {self.resource_type}",
                    db=self.db
                )
            
            if self.is_async:
                await self.db.commit()
            else:
                self.db.commit()
                
            logger.info(f"Created {self.resource_type} with ID {instance.id}")
            return instance
            
        except SQLAlchemyError as e:
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"Failed to create {self.resource_type}: {e}")
            raise
    
    async def update(self, instance_id: int, data: Dict[str, Any], track_action: bool = True) -> Optional[T]:
        """Update an instance with user tracking"""
        try:
            if self.is_async:
                result = await self.db.execute(select(self.model_class).filter(self.model_class.id == instance_id))
                instance = result.scalar_one_or_none()
            else:
                instance = self.db.query(self.model_class).filter(self.model_class.id == instance_id).first()
                
            if not instance:
                return None
            
            # Add user tracking fields if they exist
            user_id = get_current_user_id()
            if user_id and hasattr(self.model_class, 'updated_by'):
                data['updated_by'] = user_id
            
            # Update the instance
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            # Track the action
            if track_action:
                track_user_action(
                    action="update",
                    resource_type=self.resource_type,
                    resource_id=str(instance.id),
                    details=f"Updated {self.resource_type}",
                    db=self.db
                )
            
            if self.is_async:
                await self.db.commit()
            else:
                self.db.commit()
                
            logger.info(f"Updated {self.resource_type} with ID {instance.id}")
            return instance
            
        except SQLAlchemyError as e:
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"Failed to update {self.resource_type} {instance_id}: {e}")
            raise
    
    async def delete(self, instance_id: int, track_action: bool = True) -> bool:
        """Delete an instance with audit logging"""
        try:
            if self.is_async:
                result = await self.db.execute(select(self.model_class).filter(self.model_class.id == instance_id))
                instance = result.scalar_one_or_none()
            else:
                instance = self.db.query(self.model_class).filter(self.model_class.id == instance_id).first()
                
            if not instance:
                return False
            
            # Track the action before deletion
            if track_action:
                track_user_action(
                    action="delete",
                    resource_type=self.resource_type,
                    resource_id=str(instance.id),
                    details=f"Deleted {self.resource_type}",
                    db=self.db
                )
            
            if self.is_async:
                await self.db.delete(instance)
                await self.db.commit()
            else:
                self.db.delete(instance)
                self.db.commit()
                
            logger.info(f"Deleted {self.resource_type} with ID {instance_id}")
            return True
            
        except SQLAlchemyError as e:
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"Failed to delete {self.resource_type} {instance_id}: {e}")
            raise
    
    async def get_by_id(self, instance_id: int) -> Optional[T]:
        """Get an instance by ID"""
        if self.is_async:
            result = await self.db.execute(select(self.model_class).filter(self.model_class.id == instance_id))
            return result.scalar_one_or_none()
        else:
            return self.db.query(self.model_class).filter(self.model_class.id == instance_id).first()
    
    async def get_all(self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> list[T]:
        """Get all instances with optional filtering"""
        if self.is_async:
            query = select(self.model_class)
            
            # Apply filters if provided
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        query = query.filter(getattr(self.model_class, key) == value)
            
            query = query.offset(skip).limit(limit)
            result = await self.db.execute(query)
            return result.scalars().all()
        else:
            query = self.db.query(self.model_class)
            
            # Apply filters if provided
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        query = query.filter(getattr(self.model_class, key) == value)
            
            return query.offset(skip).limit(limit).all()
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count instances with optional filtering"""
        if self.is_async:
            from sqlalchemy import func
            query = select(func.count(self.model_class.id))
            
            # Apply filters if provided
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        query = query.filter(getattr(self.model_class, key) == value)
            
            result = await self.db.execute(query)
            return result.scalar()
        else:
            query = self.db.query(self.model_class)
            
            # Apply filters if provided
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        query = query.filter(getattr(self.model_class, key) == value)
            
            return query.count()
    
    async def get_by_user(self, user_id: int, created_only: bool = False) -> list[T]:
        """Get instances created or updated by a specific user"""
        if self.is_async:
            if created_only and hasattr(self.model_class, 'created_by'):
                query = select(self.model_class).filter(self.model_class.created_by == user_id)
            elif hasattr(self.model_class, 'created_by') and hasattr(self.model_class, 'updated_by'):
                query = select(self.model_class).filter(
                    (self.model_class.created_by == user_id) | 
                    (self.model_class.updated_by == user_id)
                )
            elif hasattr(self.model_class, 'created_by'):
                query = select(self.model_class).filter(self.model_class.created_by == user_id)
            else:
                return []
            
            result = await self.db.execute(query)
            return result.scalars().all()
        else:
            query = self.db.query(self.model_class)
            
            if created_only and hasattr(self.model_class, 'created_by'):
                query = query.filter(self.model_class.created_by == user_id)
            elif hasattr(self.model_class, 'created_by') and hasattr(self.model_class, 'updated_by'):
                query = query.filter(
                    (self.model_class.created_by == user_id) | 
                    (self.model_class.updated_by == user_id)
                )
            elif hasattr(self.model_class, 'created_by'):
                query = query.filter(self.model_class.created_by == user_id)
            else:
                return []
            
            return query.all()