"""
Authentication context utilities for tracking user actions
"""

from typing import Optional, Dict, Any
from contextvars import ContextVar
from sqlalchemy.orm import Session

# Context variable to store current user information
current_user_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('current_user', default=None)


def set_current_user(user_data: Dict[str, Any]) -> None:
    """Set the current user context for the request"""
    current_user_context.set(user_data)


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get the current user from context"""
    return current_user_context.get()


def get_current_user_id() -> Optional[int]:
    """Get the current user ID from context"""
    user = get_current_user()
    return user.get('id') if user else None


def clear_current_user() -> None:
    """Clear the current user context"""
    current_user_context.set(None)


def get_current_user_from_token_sync(token: str) -> Optional[Dict[str, Any]]:
    """Get user information from JWT token (synchronous version)"""
    try:
        from ..core.security import verify_token
        
        payload = verify_token(token)
        if not payload:
            return None
            
        user_id = payload.get('user_id')
        username = payload.get('sub')
        
        if not user_id and not username:
            return None
            
        # Return basic user info from token payload
        return {
            'id': user_id or 1,  # Default to 1 if not present
            'username': username or 'unknown',
            'is_admin': payload.get('is_admin', False),
            'is_superuser': payload.get('is_admin', False),  # For compatibility
            'permissions': []
        }
            
    except Exception as e:
        from ..core.logging_config import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error getting user from token: {e}")
        
    return None


async def get_current_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Get user information from JWT token (async version)"""
    try:
        from ..core.security import verify_token
        
        payload = verify_token(token)
        if not payload:
            return None
            
        user_id = payload.get('user_id')
        username = payload.get('sub')
        
        if not user_id and not username:
            return None
            
        # Return basic user info from token payload
        return {
            'id': user_id or 1,  # Default to 1 if not present
            'username': username or 'unknown',
            'is_admin': payload.get('is_admin', False),
            'is_superuser': payload.get('is_admin', False),  # For compatibility
            'permissions': []
        }
            
    except Exception as e:
        from ..core.logging_config import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error getting user from token: {e}")
        
    return None


class UserTrackingMixin:
    """Mixin class to add user tracking functionality to models"""
    
    @classmethod
    def create_with_user(cls, db: Session, **kwargs):
        """Create a new instance with automatic user tracking"""
        user_id = get_current_user_id()
        if user_id and hasattr(cls, 'created_by'):
            kwargs['created_by'] = user_id
        if user_id and hasattr(cls, 'updated_by'):
            kwargs['updated_by'] = user_id
        
        instance = cls(**kwargs)
        db.add(instance)
        return instance
    
    def update_with_user(self, db: Session, **kwargs):
        """Update an instance with automatic user tracking"""
        user_id = get_current_user_id()
        if user_id and hasattr(self, 'updated_by'):
            kwargs['updated_by'] = user_id
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        return self


def track_user_action(action: str, resource_type: str, resource_id: Optional[str] = None, 
                     details: Optional[str] = None, db: Optional[Session] = None) -> None:
    """Track user action in audit log"""
    from ..models.monitoring import AuditLog
    
    if not db:
        return
    
    user = get_current_user()
    if not user:
        return
    
    audit_log = AuditLog(
        user_id=user.get('id'),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        details=details,
        ip_address=user.get('ip_address'),
        user_agent=user.get('user_agent')
    )
    
    db.add(audit_log)


def require_authentication():
    """Decorator to require authentication for a function"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                raise ValueError("Authentication required")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(permission: str):
    """Decorator to require specific permission for a function"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                raise ValueError("Authentication required")
            
            # Check if user is superuser (has all permissions)
            if user.get('is_superuser'):
                return func(*args, **kwargs)
            
            # TODO: Implement role-based permission checking
            # For now, all authenticated users have access
            return func(*args, **kwargs)
        return wrapper
    return decorator