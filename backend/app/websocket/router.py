"""
WebSocket router that switches between legacy and unified systems based on feature flags
"""

import asyncio
from typing import Optional, Dict, Any
from fastapi import WebSocket, HTTPException, status
from datetime import datetime

from ..core.logging_config import get_logger
from ..core.feature_flags import get_websocket_feature_flags, WebSocketMigrationMode
from ..core.websocket_auth import get_current_user_websocket
from .manager import get_websocket_manager, WebSocketManager  # Legacy system
from .unified_manager import get_unified_websocket_manager, UnifiedWebSocketManager  # New system
from .models import WSUser

logger = get_logger(__name__)


class WebSocketRouter:
    """
    Router that directs WebSocket connections to either legacy or unified system
    based on feature flags and user configuration
    """
    
    def __init__(self):
        self.feature_flags = get_websocket_feature_flags()
        self.legacy_manager: Optional[WebSocketManager] = None
        self.unified_manager: Optional[UnifiedWebSocketManager] = None
        self._connection_stats = {
            "legacy_connections": 0,
            "unified_connections": 0,
            "routing_errors": 0,
            "fallback_activations": 0
        }
    
    async def route_websocket_connection(
        self, 
        websocket: WebSocket, 
        token: str, 
        connection_type: str = "system"
    ) -> bool:
        """
        Route WebSocket connection to appropriate system based on feature flags
        
        Args:
            websocket: The WebSocket connection
            token: Authentication token
            connection_type: Type of connection (for legacy compatibility)
            
        Returns:
            True if connection was successfully established
        """
        user = None
        try:
            # Authenticate user
            user = await self._authenticate_user(token)
            if not user:
                await websocket.close(code=4001, reason="Authentication failed")
                return False
            
            # Determine which system to use
            should_use_unified = self.feature_flags.should_use_unified_websocket(user.id)
            
            logger.debug(f"Routing WebSocket connection for user {user.id} to "
                       f"{'unified' if should_use_unified else 'legacy'} system")
            
            if should_use_unified:
                return await self._route_to_unified(websocket, user, connection_type)
            else:
                return await self._route_to_legacy(websocket, user, connection_type)
                
        except Exception as e:
            logger.error(f"Error routing WebSocket connection: {e}")
            self._connection_stats["routing_errors"] += 1
            
            # Try fallback if enabled and user is authenticated
            if user and self.feature_flags.settings.WEBSOCKET_LEGACY_FALLBACK:
                logger.info(f"Attempting fallback to legacy system for user {user.id}")
                try:
                    result = await self._route_to_legacy(websocket, user, connection_type)
                    if result:
                        self._connection_stats["fallback_activations"] += 1
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback to legacy system also failed: {fallback_error}")
            
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except:
                pass
            return False
    
    async def _authenticate_user(self, token: str) -> Optional[WSUser]:
        """
        Authenticate user from token
        
        Args:
            token: JWT token
            
        Returns:
            WSUser object if authentication successful, None otherwise
        """
        try:
            # Use WebSocket-specific authentication
            ws_user = await get_current_user_websocket(token)
            if not ws_user:
                logger.error("WebSocket authentication failed: get_current_user_websocket returned None")
                return None
            
            # Return the WSUser object directly (it's already the correct format)
            return ws_user
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def _route_to_unified(
        self, 
        websocket: WebSocket, 
        user: WSUser, 
        connection_type: str
    ) -> bool:
        """
        Route connection to unified WebSocket system
        
        Args:
            websocket: The WebSocket connection
            user: Authenticated user
            connection_type: Connection type (for compatibility)
            
        Returns:
            True if connection was successful
        """
        try:
            if not self.unified_manager:
                self.unified_manager = get_unified_websocket_manager()
            
            success = await self.unified_manager.connect_user(websocket, user)
            if success:
                self._connection_stats["unified_connections"] += 1
                logger.debug(f"Successfully connected user {user.id} to unified WebSocket system")
            
            return success
            
        except Exception as e:
            logger.error(f"Error connecting to unified WebSocket system: {e}")
            raise
    
    async def _route_to_legacy(
        self, 
        websocket: WebSocket, 
        user: WSUser, 
        connection_type: str
    ) -> bool:
        """
        Route connection to legacy WebSocket system
        
        Args:
            websocket: The WebSocket connection
            user: Authenticated user
            connection_type: Connection type
            
        Returns:
            True if connection was successful
        """
        try:
            if not self.legacy_manager:
                self.legacy_manager = get_websocket_manager()
            
            success = await self.legacy_manager.connect(websocket, str(user.id), connection_type)
            if success:
                self._connection_stats["legacy_connections"] += 1
                logger.debug(f"Successfully connected user {user.id} to legacy WebSocket system")
            
            return success
            
        except Exception as e:
            logger.error(f"Error connecting to legacy WebSocket system: {e}")
            raise
    
    def disconnect_user(self, websocket: WebSocket, user_id: str):
        """
        Disconnect user from appropriate WebSocket system
        
        Args:
            websocket: The WebSocket connection
            user_id: User ID
        """
        try:
            # Try to disconnect from both systems (one will be no-op)
            if self.legacy_manager:
                self.legacy_manager.disconnect(websocket)
            
            if self.unified_manager:
                self.unified_manager.disconnect_user(websocket)
                
        except Exception as e:
            logger.error(f"Error disconnecting user {user_id}: {e}")
    
    async def broadcast_event(self, event_type: str, data: Dict[str, Any], user_id: Optional[str] = None):
        """
        Broadcast event to both WebSocket systems
        
        Args:
            event_type: Type of event
            data: Event data
            user_id: Optional specific user ID
        """
        try:
            # Broadcast to legacy system
            if self.legacy_manager:
                if user_id:
                    await self.legacy_manager.send_to_user({
                        "type": event_type,
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }, user_id)
                else:
                    await self.legacy_manager.broadcast({
                        "type": event_type,
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # Broadcast to unified system
            if self.unified_manager:
                from .models import Event, EventType, EventPriority
                
                # Convert string event type to EventType enum if possible
                try:
                    event_enum = EventType(event_type)
                except ValueError:
                    # Create a generic event if type not found
                    event_enum = EventType.SYSTEM_STATUS
                
                event = Event(
                    id=f"broadcast_{datetime.utcnow().timestamp()}",
                    type=event_enum,
                    data=data,
                    priority=EventPriority.NORMAL,
                    source_user_id=user_id
                )
                
                if user_id:
                    await self.unified_manager.send_to_user(user_id, event.to_websocket_message())
                else:
                    await self.unified_manager.broadcast_event(event)
                    
        except Exception as e:
            logger.error(f"Error broadcasting event {event_type}: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics for both systems
        
        Returns:
            Dictionary with connection statistics
        """
        stats = {
            "router_stats": self._connection_stats.copy(),
            "feature_flags": self.feature_flags.get_rollout_statistics(),
            "legacy_stats": None,
            "unified_stats": None
        }
        
        try:
            if self.legacy_manager:
                stats["legacy_stats"] = self.legacy_manager.get_connection_stats()
        except Exception as e:
            logger.error(f"Error getting legacy stats: {e}")
        
        try:
            if self.unified_manager:
                stats["unified_stats"] = self.unified_manager.get_connection_stats()
        except Exception as e:
            logger.error(f"Error getting unified stats: {e}")
        
        return stats
    
    async def migrate_user_connections(self, user_id: str, to_unified: bool) -> Dict[str, Any]:
        """
        Migrate a user's connections from one system to another
        
        Args:
            user_id: User ID to migrate
            to_unified: True to migrate to unified, False to migrate to legacy
            
        Returns:
            Dictionary with migration results
        """
        result = {
            "user_id": user_id,
            "to_unified": to_unified,
            "success": False,
            "connections_migrated": 0,
            "errors": []
        }
        
        try:
            # Force user assignment in feature flags
            self.feature_flags.force_user_to_system(user_id, to_unified)
            
            if to_unified:
                # Disconnect from legacy system
                if self.legacy_manager:
                    disconnected = await self.legacy_manager.disconnect_user(
                        user_id, "Migrating to unified system"
                    )
                    result["connections_migrated"] = disconnected
            else:
                # Disconnect from unified system
                if self.unified_manager:
                    disconnected = await self.unified_manager.disconnect_user(
                        user_id, "Migrating to legacy system"
                    )
                    result["connections_migrated"] = disconnected
            
            result["success"] = True
            logger.info(f"Successfully migrated user {user_id} to "
                       f"{'unified' if to_unified else 'legacy'} system")
            
        except Exception as e:
            error_msg = f"Error migrating user {user_id}: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        
        return result


# Global WebSocket router instance
_websocket_router = None


def get_websocket_router() -> WebSocketRouter:
    """Get the global WebSocket router instance"""
    global _websocket_router
    if _websocket_router is None:
        _websocket_router = WebSocketRouter()
    return _websocket_router