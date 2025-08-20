"""
WebSocket authentication helpers
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from .security import verify_token
from .database import get_database_session
from ..models.auth import User


async def get_current_user_websocket(token: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user from WebSocket token
    Returns user dict or None if authentication fails
    """
    try:
        # Verify JWT token
        payload = verify_token(token)
        if not payload:
            return None
        
        username = payload.get("sub")
        user_id = payload.get("user_id")
        
        if not username or not user_id:
            return None
        
        # Get user from database
        async for db in get_database_session():
            try:
                user = db.query(User).filter(
                    User.username == username, 
                    User.id == user_id,
                    User.is_active == True
                ).first()
                
                if not user:
                    return None
                
                return {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
                
            except Exception:
                return None
            finally:
                break
        
        return None
        
    except Exception:
        return None