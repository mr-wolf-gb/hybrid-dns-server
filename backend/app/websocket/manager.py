"""
WebSocket manager for real-time updates across the application
Supports health monitoring, DNS events, security alerts, and system notifications
"""

import json
from datetime import datetime, date
import asyncio
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, Callable
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum

from ..core.logging_config import get_logger
from ..services.health_service import get_health_service

logger = get_logger(__name__)


class EventType(Enum):
    """WebSocket event types"""
    # Health monitoring events
    HEALTH_UPDATE = "health_update"
    HEALTH_ALERT = "health_alert"
    FORWARDER_STATUS_CHANGE = "forwarder_status_change"
    
    # DNS zone events
    ZONE_CREATED = "zone_created"
    ZONE_UPDATED = "zone_updated"
    ZONE_DELETED = "zone_deleted"
    RECORD_CREATED = "record_created"
    RECORD_UPDATED = "record_updated"
    RECORD_DELETED = "record_deleted"
    
    # Security events
    SECURITY_ALERT = "security_alert"
    RPZ_UPDATE = "rpz_update"
    THREAT_DETECTED = "threat_detected"
    
    # System events
    SYSTEM_STATUS = "system_status"
    BIND_RELOAD = "bind_reload"
    CONFIG_CHANGE = "config_change"
    
    # User events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    SESSION_EXPIRED = "session_expired"


class ConnectionType(Enum):
    """WebSocket connection types"""
    HEALTH = "health"
    DNS_MANAGEMENT = "dns_management"
    SECURITY = "security"
    SYSTEM = "system"
    ADMIN = "admin"  # Receives all event types


class WebSocketManager:
    """Manages WebSocket connections for real-time updates across the application"""
    
    def __init__(self):
        # Store active connections by user ID and connection type
        self.active_connections: Dict[str, Dict[str, Set[WebSocket]]] = {}
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        # Event handlers for different event types
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        # Background tasks
        self._broadcast_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        # Message queue for reliable delivery
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._queue_processor_task: Optional[asyncio.Task] = None
        # Connection limits to prevent resource exhaustion
        self.max_connections_per_user = 10
        self.max_total_connections = 1000
    
    async def connect(self, websocket: WebSocket, user_id: str, connection_type: str = "health"):
        """Accept a new WebSocket connection"""
        # Check connection limits before accepting
        total_connections = len(self.connection_metadata)
        if total_connections >= self.max_total_connections:
            logger.warning(f"Maximum total connections ({self.max_total_connections}) reached, rejecting connection for user {user_id}")
            await websocket.close(code=1013, reason="Server overloaded - too many connections")
            return
        
        # Check per-user connection limits
        user_connections = 0
        if user_id in self.active_connections:
            for conn_type_set in self.active_connections[user_id].values():
                user_connections += len(conn_type_set)
        
        if user_connections >= self.max_connections_per_user:
            logger.warning(f"Maximum connections per user ({self.max_connections_per_user}) reached for user {user_id}")
            await websocket.close(code=1013, reason="Too many connections for this user")
            return
        
        try:
            await websocket.accept()
        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection for user {user_id}: {e}")
            return
        
        # Initialize user connections if not exists
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        # Initialize connection type if not exists
        if connection_type not in self.active_connections[user_id]:
            self.active_connections[user_id][connection_type] = set()
        
        self.active_connections[user_id][connection_type].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connection_type": connection_type,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow(),
            "message_count": 0,
            "subscribed_events": self._get_default_events_for_connection_type(connection_type)
        }
        
        logger.info(f"WebSocket connected for user {user_id}, type: {connection_type} (total: {total_connections + 1})")
        
        # Send initial connection confirmation
        await self.send_personal_message({
            "type": "connection_established",
            "data": {
                "connection_type": connection_type,
                "subscribed_events": self.connection_metadata[websocket]["subscribed_events"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
        # Start broadcasting services if this is the first connection
        if not self._running:
            await self.start_broadcasting()
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            user_id = metadata["user_id"]
            connection_type = metadata["connection_type"]
            
            # Remove from active connections
            if user_id in self.active_connections:
                if connection_type in self.active_connections[user_id]:
                    self.active_connections[user_id][connection_type].discard(websocket)
                    if not self.active_connections[user_id][connection_type]:
                        del self.active_connections[user_id][connection_type]
                
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info(f"WebSocket disconnected for user {user_id}, type: {connection_type}")
            
            # Stop broadcasting if no connections remain
            if not self.active_connections and self._running:
                asyncio.create_task(self.stop_broadcasting())

    async def disconnect_user(self, user_id: str, reason: str = "User logged out"):
        """Disconnect all WebSocket connections for a specific user"""
        if user_id not in self.active_connections:
            return
        
        disconnected_count = 0
        websockets_to_close = []
        
        # Collect all websockets for this user
        for connection_type, websockets in self.active_connections[user_id].items():
            for websocket in websockets.copy():
                websockets_to_close.append(websocket)
        
        # Close all connections for this user
        for websocket in websockets_to_close:
            try:
                await websocket.close(code=1008, reason=reason)
                disconnected_count += 1
            except Exception as e:
                logger.error(f"Error closing WebSocket for user {user_id}: {e}")
            finally:
                # Ensure cleanup even if close fails
                self.disconnect(websocket)
        
        logger.info(f"Disconnected {disconnected_count} WebSocket connections for user {user_id}: {reason}")
        return disconnected_count
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message, default=self._json_default))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str, connection_type: Optional[str] = None):
        """Send a message to all connections for a specific user"""
        if user_id not in self.active_connections:
            return
        
        disconnected = []
        connection_types = [connection_type] if connection_type else self.active_connections[user_id].keys()
        
        for conn_type in connection_types:
            if conn_type in self.active_connections[user_id]:
                for websocket in self.active_connections[user_id][conn_type].copy():
                    try:
                        # Check if user is subscribed to this event type
                        metadata = self.connection_metadata.get(websocket, {})
                        subscribed_events = metadata.get("subscribed_events", [])
                        message_type = message.get("type")
                        
                        if message_type and message_type not in subscribed_events:
                            continue
                        
                        await websocket.send_text(json.dumps(message, default=self._json_default))
                        # Update message count
                        metadata["message_count"] = metadata.get("message_count", 0) + 1
                    except Exception as e:
                        logger.error(f"Error sending message to user {user_id}: {e}")
                        disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any], connection_type: Optional[str] = None, event_type: Optional[EventType] = None):
        """Broadcast a message to all connected clients"""
        if not self.active_connections:
            return
        
        # Add to message queue for reliable delivery
        await self._message_queue.put({
            "message": message,
            "connection_type": connection_type,
            "event_type": event_type,
            "timestamp": datetime.utcnow()
        })
    
    async def _process_message_queue(self):
        """Process messages from the queue for reliable delivery"""
        while self._running:
            try:
                # Get message from queue with timeout
                queue_item = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                
                message = queue_item["message"]
                connection_type = queue_item["connection_type"]
                event_type = queue_item["event_type"]
                
                await self._broadcast_message(message, connection_type, event_type)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
                await asyncio.sleep(1)
    
    async def _broadcast_message(self, message: Dict[str, Any], connection_type: Optional[str] = None, event_type: Optional[EventType] = None):
        """Internal method to broadcast a message"""
        if not self.active_connections:
            return
        
        disconnected = []
        message_type = message.get("type")
        
        for user_id, connection_types in self.active_connections.items():
            for conn_type, websockets in connection_types.items():
                # Filter by connection type if specified
                if connection_type and conn_type != connection_type:
                    continue
                
                for websocket in websockets.copy():
                    try:
                        # Check if connection is subscribed to this event type
                        metadata = self.connection_metadata.get(websocket, {})
                        subscribed_events = metadata.get("subscribed_events", [])
                        
                        if message_type and message_type not in subscribed_events:
                            continue
                        
                        await websocket.send_text(json.dumps(message, default=self._json_default))
                        # Update message count
                        metadata["message_count"] = metadata.get("message_count", 0) + 1
                        
                    except Exception as e:
                        logger.error(f"Error broadcasting to user {user_id}: {e}")
                        disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    def _get_default_events_for_connection_type(self, connection_type: str) -> List[str]:
        """Get default subscribed events for a connection type"""
        event_map = {
            ConnectionType.HEALTH.value: [
                EventType.HEALTH_UPDATE.value,
                EventType.HEALTH_ALERT.value,
                EventType.FORWARDER_STATUS_CHANGE.value,
                EventType.SYSTEM_STATUS.value
            ],
            ConnectionType.DNS_MANAGEMENT.value: [
                EventType.ZONE_CREATED.value,
                EventType.ZONE_UPDATED.value,
                EventType.ZONE_DELETED.value,
                EventType.RECORD_CREATED.value,
                EventType.RECORD_UPDATED.value,
                EventType.RECORD_DELETED.value,
                EventType.BIND_RELOAD.value,
                EventType.CONFIG_CHANGE.value
            ],
            ConnectionType.SECURITY.value: [
                EventType.SECURITY_ALERT.value,
                EventType.RPZ_UPDATE.value,
                EventType.THREAT_DETECTED.value,
                EventType.SYSTEM_STATUS.value
            ],
            ConnectionType.SYSTEM.value: [
                EventType.SYSTEM_STATUS.value,
                EventType.BIND_RELOAD.value,
                EventType.CONFIG_CHANGE.value,
                EventType.USER_LOGIN.value,
                EventType.USER_LOGOUT.value
            ],
            ConnectionType.ADMIN.value: [event.value for event in EventType]  # All events
        }
        
        return event_map.get(connection_type, [EventType.SYSTEM_STATUS.value])
    
    async def subscribe_to_events(self, websocket: WebSocket, event_types: List[str]):
        """Subscribe a connection to specific event types"""
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscribed_events"] = event_types
            await self.send_personal_message({
                "type": "subscription_updated",
                "data": {"subscribed_events": event_types},
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
    
    async def emit_event(self, event_type: EventType, data: Dict[str, Any], user_id: Optional[str] = None, connection_type: Optional[str] = None):
        """Emit an event to subscribers"""
        message = {
            "type": event_type.value,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id:
            await self.send_to_user(message, user_id, connection_type)
        else:
            await self.broadcast(message, connection_type, event_type)
        
        # Call registered event handlers
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type.value}: {e}")
    
    def register_event_handler(self, event_type: EventType, handler: Callable):
        """Register an event handler for a specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def start_broadcasting(self):
        """Start the background tasks for broadcasting updates"""
        if self._running:
            return
        
        self._running = True
        
        # Start message queue processor
        self._queue_processor_task = asyncio.create_task(self._process_message_queue())
        
        # Start health monitoring task
        self._broadcast_tasks["health"] = asyncio.create_task(self._broadcast_health_updates())
        
        # Start system monitoring task
        self._broadcast_tasks["system"] = asyncio.create_task(self._broadcast_system_updates())
        
        logger.info("Started WebSocket broadcasting services")
    
    async def stop_broadcasting(self):
        """Stop all background broadcasting tasks"""
        if not self._running:
            return
        
        self._running = False
        
        # Stop message queue processor
        if self._queue_processor_task and not self._queue_processor_task.done():
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
        
        # Stop all broadcast tasks
        for task_name, task in self._broadcast_tasks.items():
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._broadcast_tasks.clear()
        logger.info("Stopped WebSocket broadcasting services")
    
    async def _broadcast_health_updates(self):
        """Background task to broadcast health updates periodically"""
        health_service = get_health_service()
        
        while self._running:
            try:
                # Check if we have health connections
                has_health_connections = any(
                    ConnectionType.HEALTH.value in conn_types or ConnectionType.ADMIN.value in conn_types
                    for conn_types in self.active_connections.values()
                )
                
                if not has_health_connections:
                    await asyncio.sleep(5)
                    continue
                
                # Get health summary from service
                from ..core.database import get_database_session
                async for db in get_database_session():
                    try:
                        health_summary = await health_service.get_forwarder_health_summary(db)
                        
                        # Emit health update event
                        await self.emit_event(
                            EventType.HEALTH_UPDATE,
                            health_summary,
                            connection_type=ConnectionType.HEALTH.value
                        )
                        
                        break  # Exit the async for loop after successful execution
                        
                    except Exception as e:
                        logger.error(f"Error getting health summary for broadcast: {e}")
                        break
                
                # Wait before next update (30 seconds)
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                logger.info("Health broadcasting cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health broadcasting loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _broadcast_system_updates(self):
        """Background task to broadcast system status updates"""
        while self._running:
            try:
                # Check if we have system connections
                has_system_connections = any(
                    ConnectionType.SYSTEM.value in conn_types or ConnectionType.ADMIN.value in conn_types
                    for conn_types in self.active_connections.values()
                )
                
                if not has_system_connections:
                    await asyncio.sleep(10)
                    continue
                
                # Get system status
                system_status = await self._get_system_status()
                
                # Emit system status event
                await self.emit_event(
                    EventType.SYSTEM_STATUS,
                    system_status,
                    connection_type=ConnectionType.SYSTEM.value
                )
                
                # Wait before next update (60 seconds)
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("System broadcasting cancelled")
                break
            except Exception as e:
                logger.error(f"Error in system broadcasting loop: {e}")
                await asyncio.sleep(120)  # Wait longer on error
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        import psutil
        import os
        
        try:
            # Get basic system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Check if BIND9 is running
            bind_running = False
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    if 'named' in proc.info['name'].lower():
                        bind_running = True
                        break
            except:
                pass
            
            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "disk_usage": disk.percent,
                "bind9_running": bind_running,
                "active_connections": len(self.connection_metadata),
                "uptime": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "error": "Unable to get system status",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def broadcast_health_alert(self, alert_data: Dict[str, Any]):
        """Broadcast a health alert immediately"""
        await self.broadcast({
            "type": "health_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_type="health")
    
    async def broadcast_forwarder_status_change(self, forwarder_id: int, old_status: str, new_status: str):
        """Broadcast when a forwarder's health status changes"""
        await self.emit_event(
            EventType.FORWARDER_STATUS_CHANGE,
            {
                "forwarder_id": forwarder_id,
                "old_status": old_status,
                "new_status": new_status
            },
            connection_type=ConnectionType.HEALTH.value
        )
    
    # DNS Zone Events
    async def broadcast_zone_created(self, zone_data: Dict[str, Any], user_id: Optional[str] = None):
        """Broadcast when a DNS zone is created"""
        await self.emit_event(
            EventType.ZONE_CREATED,
            zone_data,
            user_id=user_id,
            connection_type=ConnectionType.DNS_MANAGEMENT.value
        )
    
    async def broadcast_zone_updated(self, zone_data: Dict[str, Any], user_id: Optional[str] = None):
        """Broadcast when a DNS zone is updated"""
        await self.emit_event(
            EventType.ZONE_UPDATED,
            zone_data,
            user_id=user_id,
            connection_type=ConnectionType.DNS_MANAGEMENT.value
        )
    
    async def broadcast_zone_deleted(self, zone_data: Dict[str, Any], user_id: Optional[str] = None):
        """Broadcast when a DNS zone is deleted"""
        await self.emit_event(
            EventType.ZONE_DELETED,
            zone_data,
            user_id=user_id,
            connection_type=ConnectionType.DNS_MANAGEMENT.value
        )
    
    async def broadcast_record_created(self, record_data: Dict[str, Any], user_id: Optional[str] = None):
        """Broadcast when a DNS record is created"""
        await self.emit_event(
            EventType.RECORD_CREATED,
            record_data,
            user_id=user_id,
            connection_type=ConnectionType.DNS_MANAGEMENT.value
        )
    
    async def broadcast_record_updated(self, record_data: Dict[str, Any], user_id: Optional[str] = None):
        """Broadcast when a DNS record is updated"""
        await self.emit_event(
            EventType.RECORD_UPDATED,
            record_data,
            user_id=user_id,
            connection_type=ConnectionType.DNS_MANAGEMENT.value
        )
    
    async def broadcast_record_deleted(self, record_data: Dict[str, Any], user_id: Optional[str] = None):
        """Broadcast when a DNS record is deleted"""
        await self.emit_event(
            EventType.RECORD_DELETED,
            record_data,
            user_id=user_id,
            connection_type=ConnectionType.DNS_MANAGEMENT.value
        )
    
    async def broadcast_bind_reload(self, reload_data: Dict[str, Any]):
        """Broadcast when BIND9 configuration is reloaded"""
        await self.emit_event(
            EventType.BIND_RELOAD,
            reload_data,
            connection_type=ConnectionType.DNS_MANAGEMENT.value
        )
    
    # Security Events
    async def broadcast_security_alert(self, alert_data: Dict[str, Any]):
        """Broadcast a security alert"""
        await self.emit_event(
            EventType.SECURITY_ALERT,
            alert_data,
            connection_type=ConnectionType.SECURITY.value
        )
    
    async def broadcast_rpz_update(self, rpz_data: Dict[str, Any]):
        """Broadcast when RPZ rules are updated"""
        await self.emit_event(
            EventType.RPZ_UPDATE,
            rpz_data,
            connection_type=ConnectionType.SECURITY.value
        )
    
    async def broadcast_threat_detected(self, threat_data: Dict[str, Any]):
        """Broadcast when a threat is detected"""
        await self.emit_event(
            EventType.THREAT_DETECTED,
            threat_data,
            connection_type=ConnectionType.SECURITY.value
        )
    
    # User Events
    async def broadcast_user_login(self, user_data: Dict[str, Any]):
        """Broadcast when a user logs in"""
        await self.emit_event(
            EventType.USER_LOGIN,
            user_data,
            connection_type=ConnectionType.ADMIN.value
        )
    
    async def broadcast_user_logout(self, user_data: Dict[str, Any]):
        """Broadcast when a user logs out"""
        await self.emit_event(
            EventType.USER_LOGOUT,
            user_data,
            connection_type=ConnectionType.ADMIN.value
        )
    
    async def broadcast_session_expired(self, user_id: str):
        """Broadcast when a user's session expires"""
        await self.emit_event(
            EventType.SESSION_EXPIRED,
            {"user_id": user_id},
            user_id=user_id
        )
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections"""
        total_connections = 0
        connection_types = {}
        
        for user_id, user_connections in self.active_connections.items():
            for conn_type, websockets in user_connections.items():
                total_connections += len(websockets)
                if conn_type not in connection_types:
                    connection_types[conn_type] = 0
                connection_types[conn_type] += len(websockets)
        
        # Get message statistics
        total_messages = sum(
            metadata.get("message_count", 0) 
            for metadata in self.connection_metadata.values()
        )
        
        return {
            "total_users": len(self.active_connections),
            "total_connections": total_connections,
            "total_messages_sent": total_messages,
            "broadcasting": self._running,
            "connection_types": connection_types,
            "queue_size": self._message_queue.qsize(),
            "active_tasks": len([t for t in self._broadcast_tasks.values() if not t.done()]),
            "supported_events": [event.value for event in EventType],
            "supported_connection_types": [conn_type.value for conn_type in ConnectionType]
        }

    @staticmethod
    def _json_default(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return str(obj)


# Global WebSocket manager instance
_websocket_manager = None

def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager