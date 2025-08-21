"""
FastAPI dependencies for authentication and user context
"""

from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .database import get_database_session
from .security import verify_token, get_client_ip
from .auth_context import set_current_user, clear_current_user
from ..models.auth import User

security = HTTPBearer()


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current user payload from JWT token"""
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def get_current_user_from_db(
    request: Request,
    payload: Dict[str, Any] = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_database_session)
) -> Dict[str, Any]:
    """Get current user from database and set context"""
    username = payload.get("sub")
    user_id = payload.get("user_id")
    
    if not username or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Get user from database (async)
    result = await db.execute(
        select(User).where(User.username == username, User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create user context data
    user_context = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "two_factor_enabled": user.two_factor_enabled,
        "ip_address": get_client_ip(request),
        "user_agent": request.headers.get("User-Agent", "")[:500]
    }
    
    # Set the user context for this request
    set_current_user(user_context)
    
    return user_context


async def get_current_user(
    user_context: Dict[str, Any] = Depends(get_current_user_from_db)
) -> Dict[str, Any]:
    """Get current user (main dependency to use in endpoints)"""
    return user_context


async def get_current_superuser(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Dependency that requires superuser privileges"""
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return current_user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_database_session)
) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        payload = verify_token(credentials.credentials)
        if not payload:
            return None
        
        username = payload.get("sub")
        user_id = payload.get("user_id")
        
        if not username or not user_id:
            return None
        
        # Get user from database (async)
        result = await db.execute(
            select(User).where(User.username == username, User.id == user_id)
        )
        user = result.scalars().first()
        if not user or not user.is_active:
            return None
        
        # Create user context data
        user_context = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "two_factor_enabled": user.two_factor_enabled,
            "ip_address": get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", "")[:500]
        }
        
        # Set the user context for this request
        set_current_user(user_context)
        
        return user_context
        
    except Exception:
        return None


class UserContextMiddleware:
    """Middleware to clear user context after request"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Clear context before processing request
            clear_current_user()
            
            async def send_wrapper(message):
                # Clear context after response is sent
                if message["type"] == "http.response.body" and not message.get("more_body", False):
                    clear_current_user()
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


def require_permissions(*permissions: str):
    """Dependency factory for requiring specific permissions"""
    async def permission_dependency(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        # Superusers have all permissions
        if current_user.get("is_superuser"):
            return current_user
        
        # TODO: Implement role-based permission checking
        # For now, all authenticated users have access
        # In the future, check user roles and permissions here
        
        return current_user
    
    return permission_dependency


def require_zone_access(zone_id: int):
    """Dependency factory for requiring access to a specific zone"""
    async def zone_access_dependency(
        current_user: Dict[str, Any] = Depends(get_current_user),
        db: Session = Depends(get_database_session)
    ) -> Dict[str, Any]:
        # Superusers have access to all zones
        if current_user.get("is_superuser"):
            return current_user
        
        # TODO: Implement zone-level access control
        # For now, all authenticated users have access to all zones
        # In the future, check if user has access to specific zone
        
        return current_user
    
    return zone_access_dependency