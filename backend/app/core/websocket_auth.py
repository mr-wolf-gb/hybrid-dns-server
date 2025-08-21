"""
WebSocket authentication helpers
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from .security import verify_token
from .database import get_database_session
from ..models.auth import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


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
        
        # Get user from database (async)
        async for db in get_database_session():
            try:
                if isinstance(db, AsyncSession):
                    result = await db.execute(
                        select(User).where(
                            User.username == username,
                            User.id == user_id,
                            User.is_active == True
                        )
                    )
                    user_obj = result.scalars().first()
                else:
                    user_obj = db.query(User).filter(
                        User.username == username,
                        User.id == user_id,
                        User.is_active == True
                    ).first()
                
                if not user_obj:
                    return None
                
                return {
                    "id": user_obj.id,
                    "username": user_obj.username,
                    "email": user_obj.email,
                    "is_admin": getattr(user_obj, "is_superuser", False) or getattr(user_obj, "is_admin", False),
                    "is_active": user_obj.is_active,
                    "created_at": user_obj.created_at.isoformat() if user_obj.created_at else None
                }
            except Exception:
                return None
            finally:
                break
        
        return None
        
    except Exception:
        return None