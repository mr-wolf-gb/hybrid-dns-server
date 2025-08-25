"""
Integration module for the centralized event broadcasting system
Provides easy setup and configuration for the unified WebSocket system
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..core.logging_config import get_logger
from .unified_manager import UnifiedWebSocketManager, get_unified_websocket_manager
from .message_batcher import MessageBatcher, BatchingConfig, get_message_batcher
from ..services.enhanced_event_service import EnhancedEventBroadcastingService, get_enhanced_event_service
from .event_types import EventType, EventPriority, EventCategory

logger = get_logger(__name__)


class WebSocketSystemIntegration:
    """
    Integration class for the complete WebSocket system
    Manages all components and provides a unified interface
    """
    
    def __init__(self, 
                 batching_config: Optional[BatchingConfig] = None,
                 websocket_config: Optional[Dict[str, Any]] = None):
        self.batching_config = batching_config or self._get_default_batching_config()
        self.websocket_config = websocket_config or {}
        
        # Components
        self.websocket_manager: Optional[UnifiedWebSocketManager] = None
        self.message_batcher: Optional[MessageBatcher] = None
        self.event_service: Optional[EnhancedEventBroadcastingService] = None
        
        self._initialized = False
        self._running = False
    
    def _get_default_batching_config(self) -> BatchingConfig:
        """Get default batching configuration optimized for DNS server"""
        return BatchingConfig(
            max_batch_size=25,  # Smaller batches for lower latency
            max_batch_bytes=32 * 1024,  # 32KB max batch size
            batch_timeout_ms=500,  # 500ms timeout for responsiveness
            compression_enabled=True,
            compression_threshold=512,  # Compress messages > 512 bytes
            priority_bypass=True,
            adaptive_sizing=True,
            max_queue_size=500  # Reasonable queue size
        )
    
    async def initialize(self) -> bool:
        """Initialize all WebSocket system components"""
        if self._initialized:
            return True
        
        try:
            logger.info("Initializing WebSocket system integration...")
            
            # Initialize WebSocket manager
            self.websocket_manager = get_unified_websocket_manager()
            
            # Initialize message batcher
            self.message_batcher = get_message_batcher(self.batching_config)
            
            # Initialize enhanced event service
            self.event_service = get_enhanced_event_service(
                websocket_manager=self.websocket_manager,
                message_batcher=self.message_batcher,
                batching_config=self.batching_config
            )
            
            self._initialized = True
            logger.info("WebSocket system integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket system: {e}")
            return False
    
    async def start(self) -> bool:
        """Start all WebSocket system components"""
        if not self._initialized:
            if not await self.initialize():
                return False
        
        if self._running:
            return True
        
        try:
            logger.info("Starting WebSocket system...")
            
            # Start message batcher
            await self.message_batcher.start()
            
            # Start enhanced event service
            await self.event_service.start()
            
            # WebSocket manager starts automatically when connections are made
            
            self._running = True
            logger.info("WebSocket system started successfully")
            
            # Emit system startup event
            await self.event_service.emit_event(
                EventType.SERVICE_STARTED,
                {
                    "service": "websocket_system",
                    "components": ["websocket_manager", "message_batcher", "event_service"],
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=EventPriority.HIGH
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket system: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop all WebSocket system components"""
        if not self._running:
            return True
        
        try:
            logger.info("Stopping WebSocket system...")
            
            # Emit system shutdown event
            if self.event_service:
                await self.event_service.emit_event(
                    EventType.SERVICE_STOPPED,
                    {
                        "service": "websocket_system",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    priority=EventPriority.HIGH,
                    broadcast_immediately=True
                )
            
            # Stop components in reverse order
            if self.event_service:
                await self.event_service.stop()
            
            if self.message_batcher:
                await self.message_batcher.stop()
            
            if self.websocket_manager:
                await self.websocket_manager.shutdown()
            
            self._running = False
            logger.info("WebSocket system stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping WebSocket system: {e}")
            return False
    
    async def restart(self) -> bool:
        """Restart the WebSocket system"""
        logger.info("Restarting WebSocket system...")
        
        if not await self.stop():
            return False
        
        # Wait a moment for cleanup
        await asyncio.sleep(1)
        
        return await self.start()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "initialized": self._initialized,
            "running": self._running,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self._initialized:
            # WebSocket manager status
            if self.websocket_manager:
                status["websocket_manager"] = self.websocket_manager.get_connection_stats()
            
            # Message batcher status
            if self.message_batcher:
                status["message_batcher"] = self.message_batcher.get_metrics()
            
            # Event service status
            if self.event_service:
                status["event_service"] = asyncio.create_task(self.event_service.get_statistics())
        
        return status
    
    async def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed system status (async version)"""
        status = self.get_system_status()
        
        if self.event_service and self._running:
            try:
                event_stats = await self.event_service.get_statistics()
                status["event_service"] = event_stats
            except Exception as e:
                logger.error(f"Error getting event service stats: {e}")
                status["event_service"] = {"error": str(e)}
        
        return status
    
    # Convenience methods for common operations
    async def emit_event(self, event_type: EventType, data: Dict[str, Any], **kwargs):
        """Emit an event through the system"""
        if not self._running or not self.event_service:
            logger.warning("Cannot emit event: system not running")
            return None
        
        return await self.event_service.emit_event(event_type, data, **kwargs)
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected users"""
        if not self._running or not self.websocket_manager:
            logger.warning("Cannot broadcast message: system not running")
            return
        
        await self.websocket_manager.broadcast_event(message)
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send a message to a specific user"""
        if not self._running or not self.websocket_manager:
            logger.warning("Cannot send message: system not running")
            return
        
        await self.websocket_manager.send_to_user(user_id, message)
    
    def get_connected_users(self) -> List[str]:
        """Get list of connected user IDs"""
        if not self._running or not self.websocket_manager:
            return []
        
        stats = self.websocket_manager.get_connection_stats()
        return list(stats.get("connected_users", {}).keys())
    
    async def disconnect_user(self, user_id: str, reason: str = "Disconnected by admin"):
        """Disconnect a specific user"""
        if not self._running or not self.websocket_manager:
            logger.warning("Cannot disconnect user: system not running")
            return False
        
        return await self.websocket_manager.disconnect_user(user_id, reason)
    
    async def force_flush_batches(self):
        """Force flush all pending message batches"""
        if not self._running or not self.message_batcher:
            logger.warning("Cannot flush batches: system not running")
            return
        
        await self.message_batcher.force_flush_all()
    
    def register_event_processor(self, event_type: EventType, processor):
        """Register an event processor"""
        if not self._initialized or not self.event_service:
            logger.warning("Cannot register processor: system not initialized")
            return
        
        self.event_service.register_event_processor(event_type, processor)
    
    def add_global_filter(self, filter_func):
        """Add a global event filter"""
        if not self._initialized or not self.event_service:
            logger.warning("Cannot add filter: system not initialized")
            return
        
        self.event_service.add_global_filter(filter_func)


# Global system integration instance
_websocket_system: Optional[WebSocketSystemIntegration] = None


def get_websocket_system(
    batching_config: Optional[BatchingConfig] = None,
    websocket_config: Optional[Dict[str, Any]] = None
) -> WebSocketSystemIntegration:
    """Get the global WebSocket system integration instance"""
    global _websocket_system
    if _websocket_system is None:
        _websocket_system = WebSocketSystemIntegration(batching_config, websocket_config)
    return _websocket_system


async def initialize_websocket_system(
    batching_config: Optional[BatchingConfig] = None,
    websocket_config: Optional[Dict[str, Any]] = None
) -> WebSocketSystemIntegration:
    """Initialize and start the WebSocket system"""
    system = get_websocket_system(batching_config, websocket_config)
    await system.initialize()
    await system.start()
    return system


async def shutdown_websocket_system():
    """Shutdown the WebSocket system"""
    global _websocket_system
    if _websocket_system:
        await _websocket_system.stop()
        _websocket_system = None


# Health check function for the system
async def health_check() -> Dict[str, Any]:
    """Perform a health check on the WebSocket system"""
    system = get_websocket_system()
    
    health_status = {
        "healthy": True,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    try:
        if not system._initialized:
            health_status["healthy"] = False
            health_status["error"] = "System not initialized"
            return health_status
        
        if not system._running:
            health_status["healthy"] = False
            health_status["error"] = "System not running"
            return health_status
        
        # Check each component
        components = {
            "websocket_manager": system.websocket_manager,
            "message_batcher": system.message_batcher,
            "event_service": system.event_service
        }
        
        for name, component in components.items():
            if component is None:
                health_status["components"][name] = {"healthy": False, "error": "Component not initialized"}
                health_status["healthy"] = False
            else:
                health_status["components"][name] = {"healthy": True}
        
        # Get system metrics
        if health_status["healthy"]:
            status = await system.get_detailed_status()
            health_status["metrics"] = status
        
    except Exception as e:
        health_status["healthy"] = False
        health_status["error"] = str(e)
        logger.error(f"Health check failed: {e}")
    
    return health_status


# Utility functions for common operations
async def emit_system_event(event_type: EventType, data: Dict[str, Any], **kwargs):
    """Utility function to emit system events"""
    system = get_websocket_system()
    if system._running:
        return await system.emit_event(event_type, data, **kwargs)
    return None


async def broadcast_system_message(message: Dict[str, Any]):
    """Utility function to broadcast system messages"""
    system = get_websocket_system()
    if system._running:
        await system.broadcast_message(message)


async def send_user_notification(user_id: str, notification: Dict[str, Any]):
    """Utility function to send user notifications"""
    system = get_websocket_system()
    if system._running:
        await system.send_to_user(user_id, {
            "type": "notification",
            "data": notification,
            "timestamp": datetime.utcnow().isoformat()
        })