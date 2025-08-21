"""
WebSocket authentication helpers
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass

from .security import verify_token_flexible
from .database import get_database_session
from ..models.auth import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


@dataclass
class WSUser:
    id: int
    username: str
    email: Optional[str]
    is_admin: bool
    is_active: bool
    created_at: Optional[str]


async def get_current_user_websocket(token: str) -> Optional[WSUser]:
    """
    Authenticate user from WebSocket token
    Returns user dict or None if authentication fails
    """
    try:
        # Verify JWT token
        payload = verify_token_flexible(token)
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
                    # Fallback: allow connection based on token claims if present
                    return WSUser(
                        id=int(user_id),
                        username=username,
                        email=None,
                        is_admin=bool(payload.get("is_admin", False)),
                        is_active=True,
                        created_at=None
                    )
                
                return WSUser(
                    id=user_obj.id,
                    username=user_obj.username,
                    email=getattr(user_obj, "email", None),
                    is_admin=bool(getattr(user_obj, "is_superuser", False) or getattr(user_obj, "is_admin", False)),
                    is_active=bool(user_obj.is_active),
                    created_at=(user_obj.created_at.isoformat() if getattr(user_obj, "created_at", None) else None)
                )
            except Exception:
                # On DB error, fallback to token-only user if claims exist
                return WSUser(
                    id=int(user_id),
                    username=username,
                    email=None,
                    is_admin=bool(payload.get("is_admin", False)),
                    is_active=True,
                    created_at=None
                )
            finally:
                break
        
        return None
        
    except Exception:
        return None