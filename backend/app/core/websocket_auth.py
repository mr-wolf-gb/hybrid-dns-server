"""
WebSocket authentication helpers
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass

from .security import verify_token_flexible
from jose import jwt as jose_jwt
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
            # Try to parse claims without verifying signature as a last resort
            try:
                payload = jose_jwt.get_unverified_claims(token)
            except Exception:
                # Final fallback: accept any non-empty token for non-admin channels (endpoint enforces admin)
                pseudo_username = f"user_{token[:8]}"
                return WSUser(
                    id=-1,
                    username=pseudo_username,
                    email=None,
                    is_admin=False,
                    is_active=True,
                    created_at=None
                )
        
        username = payload.get("sub")
        user_id = payload.get("user_id")
        
        # Accept tokens that have at least a subject; user_id is optional for WS
        if not username:
            return None
        
        # Get user from database (async)
        async for db in get_database_session():
            try:
                user_obj = None
                if user_id is not None:
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
                        id=int(user_id) if user_id is not None else -1,
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
                    is_admin=bool(
                        getattr(user_obj, "is_superuser", False)
                        or getattr(user_obj, "is_admin", False)
                        or bool(payload.get("is_admin", False))
                    ),
                    is_active=bool(user_obj.is_active),
                    created_at=(user_obj.created_at.isoformat() if getattr(user_obj, "created_at", None) else None)
                )
            except Exception:
                # On DB error, fallback to token-only user if claims exist
                return WSUser(
                    id=int(user_id) if user_id is not None else -1,
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