"""
WebSocket System Startup and Initialization
Handles initialization of the WebSocket metrics, health monitoring, and admin tools
"""

import asyncio
from typing import Optional

from ..core.logging_config import get_logger
from .metrics_integration import get_metrics_integration, initialize_websocket_metrics, shutdown_websocket_metrics
from .unified_manager import UnifiedWebSocketManager

logger = get_logger(__name__)


class WebSocketSystemManager:
    """
    Manages the entire WebSocket system including metrics, health monitoring, and admin tools
    """
    
    def __init__(self):
        self.websocket_manager: Optional[UnifiedWebSocketManager] = None
        self.metrics_integration = get_metrics_integration()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the WebSocket system"""
        if self._initialized:
            logger.warning("WebSocket system already initialized")
            return
        
        try:
            logger.info("Initializing WebSocket system...")
            
            # Initialize metrics system
            await initialize_websocket_metrics()
            
            # Create WebSocket manager
            self.websocket_manager = UnifiedWebSocketManager()
            
            # Set up metrics integration with the manager
            self.metrics_integration.set_connection_manager(self.websocket_manager)
            
            # Integrate metrics collection with the WebSocket manager
            await self._integrate_metrics_with_manager()
            
            self._initialized = True
            logger.info("WebSocket system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket system: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the WebSocket system"""
        if not self._initialized:
            return
        
        try:
            logger.info("Shutting down WebSocket system...")
            
            # Shutdown WebSocket manager if it exists
            if self.websocket_manager:
                # Stop all background tasks in the manager
                if hasattr(self.websocket_manager, 'stop'):
                    await self.websocket_manager.stop()
            
            # Shutdown metrics system
            await shutdown_websocket_metrics()
            
            self._initialized = False
            logger.info("WebSocket system shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during WebSocket system shutdown: {e}")
    
    async def _integrate_metrics_with_manager(self):
        """Integrate metrics collection with the WebSocket manager"""
        if not self.websocket_manager:
            return
        
        # Monkey patch the WebSocket manager methods to include metrics collection
        original_connect_user = self.websocket_manager.connect_user
        original_disconnect_user = self.websocket_manager.disconnect_user
        original_send_to_user = self.websocket_manager.send_to_user
        original_broadcast_event = self.websocket_manager.broadcast_event
        
        async def connect_user_with_metrics(websocket, user, client_ip=None):
            """Connect user with metrics collection"""
            result = await original_connect_user(websocket, user, client_ip)
            if result:
                self.metrics_integration.on_connection_created(user.username, client_ip)
            return result
        
        async def disconnect_user_with_metrics(user_id, reason="unknown"):
            """Disconnect user with metrics collection"""
            result = await original_disconnect_user(user_id, reason)
            self.metrics_integration.on_connection_closed(user_id, reason)
            return result
        
        async def send_to_user_with_metrics(user_id, message):
            """Send to user with metrics collection"""
            result = await original_send_to_user(user_id, message)
            if result:
                self.metrics_integration.on_message_sent(user_id, message)
            return result
        
        async def broadcast_event_with_metrics(event):
            """Broadcast event with metrics collection"""
            import time
            start_time = time.time()
            
            try:
                result = await original_broadcast_event(event)
                processing_time = (time.time() - start_time) * 1000
                self.metrics_integration.on_event_processed(
                    event.type.value if hasattr(event, 'type') else 'unknown',
                    processing_time,
                    True
                )
                return result
            except Exception as e:
                processing_time = (time.time() - start_time) * 1000
                self.metrics_integration.on_event_processed(
                    event.type.value if hasattr(event, 'type') else 'unknown',
                    processing_time,
                    False
                )
                raise
        
        # Replace methods with metrics-enabled versions
        self.websocket_manager.connect_user = connect_user_with_metrics
        self.websocket_manager.disconnect_user = disconnect_user_with_metrics
        self.websocket_manager.send_to_user = send_to_user_with_metrics
        self.websocket_manager.broadcast_event = broadcast_event_with_metrics
        
        logger.info("Metrics integration with WebSocket manager completed")
    
    def get_websocket_manager(self) -> Optional[UnifiedWebSocketManager]:
        """Get the WebSocket manager instance"""
        return self.websocket_manager
    
    def is_initialized(self) -> bool:
        """Check if the system is initialized"""
        return self._initialized


# Global system manager instance
_websocket_system_manager = None


def get_websocket_system_manager() -> WebSocketSystemManager:
    """Get the global WebSocket system manager instance"""
    global _websocket_system_manager
    if _websocket_system_manager is None:
        _websocket_system_manager = WebSocketSystemManager()
    return _websocket_system_manager


# Convenience functions
async def initialize_websocket_system():
    """Initialize the WebSocket system"""
    manager = get_websocket_system_manager()
    await manager.initialize()


async def shutdown_websocket_system():
    """Shutdown the WebSocket system"""
    manager = get_websocket_system_manager()
    await manager.shutdown()


def get_unified_websocket_manager() -> Optional[UnifiedWebSocketManager]:
    """Get the unified WebSocket manager instance"""
    manager = get_websocket_system_manager()
    return manager.get_websocket_manager()