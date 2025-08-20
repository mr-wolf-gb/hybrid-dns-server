"""
WebSocket event service for broadcasting DNS and system events
Integrates with existing services to emit real-time events
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..websocket.manager import get_websocket_manager, EventType
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class WebSocketEventService:
    """Service for emitting WebSocket events from various operations"""
    
    def __init__(self):
        self.websocket_manager = get_websocket_manager()
    
    # DNS Zone Events
    async def emit_zone_created(self, zone_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit event when a DNS zone is created"""
        try:
            await self.websocket_manager.broadcast_zone_created(zone_data, user_id)
            logger.info(f"Emitted zone_created event for zone: {zone_data.get('name')}")
        except Exception as e:
            logger.error(f"Error emitting zone_created event: {e}")
    
    async def emit_zone_updated(self, zone_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit event when a DNS zone is updated"""
        try:
            await self.websocket_manager.broadcast_zone_updated(zone_data, user_id)
            logger.info(f"Emitted zone_updated event for zone: {zone_data.get('name')}")
        except Exception as e:
            logger.error(f"Error emitting zone_updated event: {e}")
    
    async def emit_zone_deleted(self, zone_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit event when a DNS zone is deleted"""
        try:
            await self.websocket_manager.broadcast_zone_deleted(zone_data, user_id)
            logger.info(f"Emitted zone_deleted event for zone: {zone_data.get('name')}")
        except Exception as e:
            logger.error(f"Error emitting zone_deleted event: {e}")
    
    # DNS Record Events
    async def emit_record_created(self, record_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit event when a DNS record is created"""
        try:
            await self.websocket_manager.broadcast_record_created(record_data, user_id)
            logger.info(f"Emitted record_created event for record: {record_data.get('name')}")
        except Exception as e:
            logger.error(f"Error emitting record_created event: {e}")
    
    async def emit_record_updated(self, record_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit event when a DNS record is updated"""
        try:
            await self.websocket_manager.broadcast_record_updated(record_data, user_id)
            logger.info(f"Emitted record_updated event for record: {record_data.get('name')}")
        except Exception as e:
            logger.error(f"Error emitting record_updated event: {e}")
    
    async def emit_record_deleted(self, record_data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit event when a DNS record is deleted"""
        try:
            await self.websocket_manager.broadcast_record_deleted(record_data, user_id)
            logger.info(f"Emitted record_deleted event for record: {record_data.get('name')}")
        except Exception as e:
            logger.error(f"Error emitting record_deleted event: {e}")
    
    # BIND9 Events
    async def emit_bind_reload(self, reload_data: Dict[str, Any]):
        """Emit event when BIND9 configuration is reloaded"""
        try:
            await self.websocket_manager.broadcast_bind_reload(reload_data)
            logger.info("Emitted bind_reload event")
        except Exception as e:
            logger.error(f"Error emitting bind_reload event: {e}")
    
    async def emit_config_change(self, config_data: Dict[str, Any]):
        """Emit event when configuration changes"""
        try:
            await self.websocket_manager.emit_event(
                EventType.CONFIG_CHANGE,
                config_data
            )
            logger.info(f"Emitted config_change event for: {config_data.get('component')}")
        except Exception as e:
            logger.error(f"Error emitting config_change event: {e}")
    
    # Security Events
    async def emit_security_alert(self, alert_data: Dict[str, Any]):
        """Emit security alert event"""
        try:
            await self.websocket_manager.broadcast_security_alert(alert_data)
            logger.warning(f"Emitted security_alert event: {alert_data.get('message')}")
        except Exception as e:
            logger.error(f"Error emitting security_alert event: {e}")
    
    async def emit_rpz_update(self, rpz_data: Dict[str, Any]):
        """Emit event when RPZ rules are updated"""
        try:
            await self.websocket_manager.broadcast_rpz_update(rpz_data)
            logger.info(f"Emitted rpz_update event for: {rpz_data.get('zone')}")
        except Exception as e:
            logger.error(f"Error emitting rpz_update event: {e}")
    
    async def emit_threat_detected(self, threat_data: Dict[str, Any]):
        """Emit event when a threat is detected"""
        try:
            await self.websocket_manager.broadcast_threat_detected(threat_data)
            logger.warning(f"Emitted threat_detected event: {threat_data.get('threat_type')}")
        except Exception as e:
            logger.error(f"Error emitting threat_detected event: {e}")
    
    # User Events
    async def emit_user_login(self, user_data: Dict[str, Any]):
        """Emit event when a user logs in"""
        try:
            await self.websocket_manager.broadcast_user_login(user_data)
            logger.info(f"Emitted user_login event for user: {user_data.get('username')}")
        except Exception as e:
            logger.error(f"Error emitting user_login event: {e}")
    
    async def emit_user_logout(self, user_data: Dict[str, Any]):
        """Emit event when a user logs out"""
        try:
            await self.websocket_manager.broadcast_user_logout(user_data)
            logger.info(f"Emitted user_logout event for user: {user_data.get('username')}")
        except Exception as e:
            logger.error(f"Error emitting user_logout event: {e}")
    
    async def emit_session_expired(self, user_id: str):
        """Emit event when a user's session expires"""
        try:
            await self.websocket_manager.broadcast_session_expired(user_id)
            logger.info(f"Emitted session_expired event for user: {user_id}")
        except Exception as e:
            logger.error(f"Error emitting session_expired event: {e}")
    
    # Generic event emission
    async def emit_custom_event(self, event_type: str, data: Dict[str, Any], user_id: Optional[str] = None):
        """Emit a custom event"""
        try:
            message = {
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if user_id:
                await self.websocket_manager.send_to_user(message, user_id)
            else:
                await self.websocket_manager.broadcast(message)
            
            logger.info(f"Emitted custom event: {event_type}")
        except Exception as e:
            logger.error(f"Error emitting custom event {event_type}: {e}")


# Global instance
_websocket_event_service = None

def get_websocket_event_service() -> WebSocketEventService:
    """Get the global WebSocket event service instance"""
    global _websocket_event_service
    if _websocket_event_service is None:
        _websocket_event_service = WebSocketEventService()
    return _websocket_event_service


# Decorator for automatic event emission
def emit_websocket_event(event_type: str, data_extractor=None):
    """Decorator to automatically emit WebSocket events from function calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            try:
                # Extract event data
                if data_extractor:
                    event_data = data_extractor(result, *args, **kwargs)
                else:
                    event_data = {"result": str(result)}
                
                # Emit event
                event_service = get_websocket_event_service()
                await event_service.emit_custom_event(event_type, event_data)
                
            except Exception as e:
                logger.error(f"Error emitting event {event_type} from decorator: {e}")
            
            return result
        return wrapper
    return decorator


# Context manager for batch event emission
class WebSocketEventBatch:
    """Context manager for batching WebSocket events"""
    
    def __init__(self):
        self.events = []
        self.event_service = get_websocket_event_service()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Emit all batched events
        for event_type, data, user_id in self.events:
            await self.event_service.emit_custom_event(event_type, data, user_id)
    
    def add_event(self, event_type: str, data: Dict[str, Any], user_id: Optional[str] = None):
        """Add an event to the batch"""
        self.events.append((event_type, data, user_id))