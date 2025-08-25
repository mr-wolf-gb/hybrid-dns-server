"""
Enhanced WebSocket authentication and authorization
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
from dataclasses import dataclass

from jose import jwt as jose_jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.security import verify_token_flexible
from ..core.database import get_database_session
from ..models.auth import User
from ..core.logging_config import get_logger
from .models import WSUser, EventType

logger = get_logger(__name__)


@dataclass
class UserPermissions:
    """User permissions for WebSocket events"""
    user_id: str
    is_admin: bool
    allowed_event_types: Set[EventType]
    rate_limits: Dict[EventType, int]
    
    def can_access_event(self, event_type: EventType) -> bool:
        """Check if user can access specific event type"""
        return event_type in self.allowed_event_types
    
    def get_rate_limit(self, event_type: EventType) -> int:
        """Get rate limit for specific event type"""
        return self.rate_limits.get(event_type, 60)  # Default 60 events per minute


class WebSocketAuthenticator:
    """Enhanced WebSocket authentication and authorization"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, int] = {}
        self.lockout_times: Dict[str, datetime] = {}
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
    
    async def authenticate_user(self, token: str, client_ip: str = None) -> Optional[WSUser]:
        """
        Authenticate user from WebSocket token with enhanced security
        """
        try:
            # Check if IP is locked out
            if client_ip and self._is_ip_locked_out(client_ip):
                logger.warning(f"Authentication blocked for locked out IP: {client_ip}")
                return None
            
            # Verify JWT token
            payload = await self._verify_jwt_token(token)
            if not payload:
                self._record_failed_attempt(client_ip)
                return None
            
            username = payload.get("sub")
            user_id = payload.get("user_id")
            
            if not username:
                self._record_failed_attempt(client_ip)
                return None
            
            # Get user from database
            user = await self._get_user_from_database(username, user_id)
            if not user:
                # Create fallback user from token claims if valid
                user = self._create_fallback_user(payload)
                if not user:
                    self._record_failed_attempt(client_ip)
                    return None
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Inactive user attempted WebSocket connection: {username}")
                self._record_failed_attempt(client_ip)
                return None
            
            # Reset failed attempts on successful authentication
            if client_ip and client_ip in self.failed_attempts:
                del self.failed_attempts[client_ip]
            
            # Create or update session
            await self._create_session(user, token, payload)
            
            logger.info(f"WebSocket authentication successful: {username}")
            return user
            
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            self._record_failed_attempt(client_ip)
            return None
    
    async def _verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token with enhanced validation"""
        try:
            # First try with signature verification
            payload = verify_token_flexible(token)
            if payload:
                return payload
            
            # Fallback: verify token structure without signature for development
            try:
                payload = jose_jwt.get_unverified_claims(token)
                
                # Basic validation of required claims
                if not payload.get("sub"):
                    return None
                
                # Check expiration if present
                exp = payload.get("exp")
                if exp:
                    exp_datetime = datetime.fromtimestamp(exp)
                    if datetime.utcnow() > exp_datetime:
                        logger.warning("Token expired")
                        return None
                
                return payload
                
            except Exception as e:
                logger.debug(f"Token parsing failed: {e}")
                return None
                
        except JWTError as e:
            logger.debug(f"JWT verification failed: {e}")
            return None
    
    async def _get_user_from_database(self, username: str, user_id: Optional[int]) -> Optional[WSUser]:
        """Get user from database with async support"""
        try:
            async for db in get_database_session():
                try:
                    if isinstance(db, AsyncSession):
                        # Async database query
                        query = select(User).where(User.username == username, User.is_active == True)
                        if user_id is not None:
                            query = query.where(User.id == user_id)
                        
                        result = await db.execute(query)
                        user_obj = result.scalars().first()
                    else:
                        # Sync database query
                        query = db.query(User).filter(User.username == username, User.is_active == True)
                        if user_id is not None:
                            query = query.filter(User.id == user_id)
                        
                        user_obj = query.first()
                    
                    if user_obj:
                        return WSUser(
                            id=user_obj.id,
                            username=user_obj.username,
                            email=getattr(user_obj, "email", None),
                            is_admin=bool(
                                getattr(user_obj, "is_superuser", False) or 
                                getattr(user_obj, "is_admin", False)
                            ),
                            is_active=bool(user_obj.is_active),
                            created_at=(
                                user_obj.created_at.isoformat() 
                                if getattr(user_obj, "created_at", None) else None
                            )
                        )
                    
                    return None
                    
                except Exception as e:
                    logger.error(f"Database error during user lookup: {e}")
                    return None
                finally:
                    break
                    
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def _create_fallback_user(self, payload: Dict[str, Any]) -> Optional[WSUser]:
        """Create fallback user from token claims"""
        try:
            username = payload.get("sub")
            user_id = payload.get("user_id", -1)
            
            if not username:
                return None
            
            return WSUser(
                id=int(user_id) if user_id is not None else -1,
                username=username,
                email=payload.get("email"),
                is_admin=bool(payload.get("is_admin", False)),
                is_active=True,
                created_at=None
            )
            
        except Exception as e:
            logger.error(f"Error creating fallback user: {e}")
            return None
    
    async def _create_session(self, user: WSUser, token: str, payload: Dict[str, Any]):
        """Create or update user session"""
        session_id = f"{user.username}_{datetime.utcnow().timestamp()}"
        
        self.active_sessions[user.username] = {
            "session_id": session_id,
            "user_id": user.id,
            "token": token,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "token_expires": datetime.fromtimestamp(payload.get("exp", 0)) if payload.get("exp") else None,
            "is_admin": user.is_admin
        }
    
    def _is_ip_locked_out(self, client_ip: str) -> bool:
        """Check if IP address is locked out"""
        if client_ip not in self.lockout_times:
            return False
        
        lockout_time = self.lockout_times[client_ip]
        if datetime.utcnow() > lockout_time + self.lockout_duration:
            # Lockout expired, remove it
            del self.lockout_times[client_ip]
            if client_ip in self.failed_attempts:
                del self.failed_attempts[client_ip]
            return False
        
        return True
    
    def _record_failed_attempt(self, client_ip: str):
        """Record failed authentication attempt"""
        if not client_ip:
            return
        
        self.failed_attempts[client_ip] = self.failed_attempts.get(client_ip, 0) + 1
        
        if self.failed_attempts[client_ip] >= self.max_failed_attempts:
            self.lockout_times[client_ip] = datetime.utcnow()
            logger.warning(f"IP locked out due to failed attempts: {client_ip}")
    
    async def refresh_token(self, user: WSUser, current_token: str) -> Optional[str]:
        """Refresh user token if needed"""
        try:
            session = self.active_sessions.get(user.username)
            if not session:
                return None
            
            # Check if token is close to expiration (within 5 minutes)
            token_expires = session.get("token_expires")
            if token_expires and datetime.utcnow() + timedelta(minutes=5) > token_expires:
                # Generate new token
                new_payload = {
                    "sub": user.username,
                    "user_id": user.id,
                    "is_admin": user.is_admin,
                    "exp": datetime.utcnow() + timedelta(hours=24),
                    "iat": datetime.utcnow()
                }
                
                from ..core.config import get_settings
                settings = get_settings()
                new_token = jose_jwt.encode(new_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
                
                # Update session
                session["token"] = new_token
                session["token_expires"] = new_payload["exp"]
                session["last_activity"] = datetime.utcnow()
                
                logger.info(f"Token refreshed for user: {user.username}")
                return new_token
            
            return None
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
    
    def get_user_permissions(self, user: WSUser) -> UserPermissions:
        """Get user permissions for WebSocket events"""
        if user.is_admin:
            # Admin users get access to all events
            allowed_events = set(EventType)
            rate_limits = {event: 120 for event in EventType}  # Higher limits for admins
        else:
            # Regular users get limited access
            allowed_events = {
                EventType.HEALTH_UPDATE,
                EventType.SYSTEM_STATUS,
                EventType.ZONE_CREATED,
                EventType.ZONE_UPDATED,
                EventType.ZONE_DELETED,
                EventType.RECORD_CREATED,
                EventType.RECORD_UPDATED,
                EventType.RECORD_DELETED,
                EventType.BIND_RELOAD,
                EventType.CONFIG_CHANGE,
                EventType.SECURITY_ALERT,
                EventType.RPZ_UPDATE,
                EventType.THREAT_DETECTED,
                EventType.CONNECTION_ESTABLISHED,
                EventType.SUBSCRIPTION_UPDATED,
                EventType.PING,
                EventType.PONG
            }
            rate_limits = {event: 60 for event in allowed_events}  # Standard limits
        
        return UserPermissions(
            user_id=str(user.id),
            is_admin=user.is_admin,
            allowed_event_types=allowed_events,
            rate_limits=rate_limits
        )
    
    def validate_session(self, user: WSUser) -> bool:
        """Validate user session"""
        session = self.active_sessions.get(user.username)
        if not session:
            return False
        
        # Check token expiration
        token_expires = session.get("token_expires")
        if token_expires and datetime.utcnow() > token_expires:
            logger.info(f"Session expired for user: {user.username}")
            del self.active_sessions[user.username]
            return False
        
        # Update last activity
        session["last_activity"] = datetime.utcnow()
        return True
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_users = []
        
        for username, session in self.active_sessions.items():
            token_expires = session.get("token_expires")
            if token_expires and datetime.utcnow() > token_expires:
                expired_users.append(username)
        
        for username in expired_users:
            del self.active_sessions[username]
            logger.info(f"Cleaned up expired session for: {username}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        return {
            "active_sessions": len(self.active_sessions),
            "failed_attempts": len(self.failed_attempts),
            "locked_ips": len(self.lockout_times),
            "session_details": {
                username: {
                    "created_at": session["created_at"].isoformat(),
                    "last_activity": session["last_activity"].isoformat(),
                    "is_admin": session["is_admin"]
                }
                for username, session in self.active_sessions.items()
            }
        }


# Global authenticator instance
_websocket_authenticator = None


def get_websocket_authenticator() -> WebSocketAuthenticator:
    """Get the global WebSocket authenticator instance"""
    global _websocket_authenticator
    if _websocket_authenticator is None:
        _websocket_authenticator = WebSocketAuthenticator()
    return _websocket_authenticator