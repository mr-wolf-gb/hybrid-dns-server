"""
Simple, robust WebSocket manager
Handles rapid connection attempts gracefully
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket
from enum import Enum

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class EventType(Enum):
    """WebSocket event types"""
    HEALTH_UPDATE = "health_update"
    HEALTH_ALERT = "health_alert"
    FORWARDER_STATUS_CHANGE = "forwarder_status_change"
    ZONE_CREATED = "zone_created"
    ZONE_UPDATED = "zone_updated"
    ZONE_DELETED = "zone_deleted"
    RECORD_CREATED = "record_created"
    RECORD_UPDATED = "record_updated"
    RECORD_DELETED = "record_deleted"
    SECURITY_ALERT = "security_alert"
    RPZ_UPDATE = "rpz_update"
    THREAT_DETECTED = "threat_detected"
    SYSTEM_STATUS = "system_status"
    BIND_RELOAD = "bind_reload"
    CONFIG_CHANGE = "config_change"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    SESSION_EXPIRED = "session_expired"


class ConnectionType(Enum):
    """WebSocket connection types"""
    HEALTH = "health"
    DNS_MANAGEMENT = "dns_management"
    SECURITY = "security"
    SYSTEM = "system"
    ADMIN = "admin"


class WebSocketManager:
    """Simple, robust WebSocket manager"""
    
    def __init__(self):
        # Structure: user_id -> connection_type -> websocket (only ONE per type)
        self.connections: Dict[str, Dict[str, WebSocket]] = {}
        # Connection metadata
        self.metadata: Dict[WebSocket, Dict[str, Any]] = {}
        # Background tasks
        self._tasks: Set[asyncio.Task] = set()
        self._running = False
        # Connection limits - much stricter
        self.max_connections_per_user = 5  # Only 5 connection types max
        self.max_total_connections = 100
        # Connection lock to prevent race conditions
        self._connection_lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: str, connection_type: str) -> bool:
        """Accept a new WebSocket connection - ONLY ONE per connection type per user"""
        async with self._connection_lock:
            try:
                # Ensure user_id is always a string for consistency
                user_id = str(user_id)
                
                # Check total connections
                total_connections = sum(len(user_conns) for user_conns in self.connections.values())
                if total_connections >= self.max_total_connections:
                    logger.warning(f"Max total connections reached: {total_connections}")
                    await websocket.close(code=1013, reason="Server overloaded")
                    return False
                
                # Initialize user connections if needed
                if user_id not in self.connections:
                    self.connections[user_id] = {}
                
                # Check if we already have this connection type - CLOSE IT IMMEDIATELY
                if connection_type in self.connections[user_id]:
                    old_websocket = self.connections[user_id][connection_type]
                    logger.info(f"FORCE CLOSING existing {connection_type} connection for {user_id}")
                    try:
                        await old_websocket.close(code=1000, reason="Replaced by new connection")
                    except:
                        pass
                    # Remove old connection
                    if old_websocket in self.metadata:
                        del self.metadata[old_websocket]
                
                # Accept the NEW WebSocket connection
                await websocket.accept()
                
                # Store the NEW connection (replaces old one)
                self.connections[user_id][connection_type] = websocket
                
                # Store metadata
                self.metadata[websocket] = {
                    "user_id": user_id,
                    "connection_type": connection_type,
                    "connected_at": datetime.utcnow(),
                    "message_count": 0,
                    "subscribed_events": self._get_default_events(connection_type)
                }
                
                logger.info(f"WebSocket connected: {user_id}:{connection_type} (total: {total_connections + 1})")
                
                # Start background services if this is the first connection
                if not self._running:
                    await self._start_background_services()
                
                # Send connection confirmation
                await self._send_message(websocket, {
                    "type": "connection_established",
                    "data": {
                        "connection_type": connection_type,
                        "subscribed_events": self.metadata[websocket]["subscribed_events"]
                    },
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect WebSocket for {user_id}:{connection_type}: {e}")
                try:
                    await websocket.close(code=1011, reason="Connection failed")
                except:
                    pass
                return False
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket connection"""
        if websocket not in self.metadata:
            return
        
        metadata = self.metadata[websocket]
        user_id = str(metadata["user_id"])  # Ensure string consistency
        connection_type = metadata["connection_type"]
        
        # Remove from connections
        if user_id in self.connections:
            if connection_type in self.connections[user_id]:
                if self.connections[user_id][connection_type] == websocket:
                    del self.connections[user_id][connection_type]
            
            # Clean up empty user entry
            if not self.connections[user_id]:
                del self.connections[user_id]
        
        # Remove metadata
        del self.metadata[websocket]
        
        logger.info(f"WebSocket disconnected: {user_id}:{connection_type}")
        
        # Stop background services if no connections remain
        if not self.connections and self._running:
            asyncio.create_task(self._stop_background_services())
    
    async def _close_oldest_connection(self, user_id: str):
        """Close the oldest connection for a user"""
        user_id = str(user_id)  # Ensure string consistency
        if user_id not in self.connections:
            return
        
        # Find oldest connection
        oldest_ws = None
        oldest_time = datetime.utcnow()
        
        for connection_type, ws in self.connections[user_id].items():
            if ws in self.metadata:
                connected_at = self.metadata[ws].get("connected_at", datetime.utcnow())
                if connected_at < oldest_time:
                    oldest_time = connected_at
                    oldest_ws = ws
        
        if oldest_ws:
            try:
                logger.info(f"Closing oldest connection for user {user_id}")
                await oldest_ws.close(code=1000, reason="Making room for new connection")
            except Exception as e:
                logger.debug(f"Error closing old connection: {e}")
            finally:
                self.disconnect(oldest_ws)
    
    def _get_default_events(self, connection_type: str) -> list:
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
            ConnectionType.ADMIN.value: [event.value for event in EventType]
        }
        return event_map.get(connection_type, [EventType.SYSTEM_STATUS.value])
    
    async def _send_message(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(json.dumps(message, default=self._json_default))
            if websocket in self.metadata:
                self.metadata[websocket]["message_count"] += 1
            return True
        except Exception as e:
            logger.debug(f"Failed to send message: {e}")
            self.disconnect(websocket)
            return False
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """Send a message to all connections for a user"""
        user_id = str(user_id)  # Ensure string consistency
        if user_id not in self.connections:
            return
        
        failed_connections = []
        for connection_type, websocket in list(self.connections[user_id].items()):
            # Check if connection should receive this event
            if websocket in self.metadata:
                subscribed_events = self.metadata[websocket].get("subscribed_events", [])
                message_type = message.get("type", "")
                if message_type and message_type not in subscribed_events:
                    continue
            
            success = await self._send_message(websocket, message)
            if not success:
                failed_connections.append(websocket)
        
        # Clean up failed connections
        for websocket in failed_connections:
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any], connection_type: Optional[str] = None):
        """Broadcast a message to all connected clients"""
        if not self.connections:
            return
        
        failed_connections = []
        message_type = message.get("type", "")
        
        for user_id, user_connection_types in self.connections.items():
            for conn_type, websocket in list(user_connection_types.items()):
                if websocket not in self.metadata:
                    continue
                
                # Filter by connection type if specified
                if connection_type and conn_type != connection_type:
                    continue
                
                # Check if connection should receive this event
                subscribed_events = self.metadata[websocket].get("subscribed_events", [])
                if message_type and message_type not in subscribed_events:
                    continue
                
                success = await self._send_message(websocket, message)
                if not success:
                    failed_connections.append(websocket)
        
        # Clean up failed connections
        for websocket in failed_connections:
            self.disconnect(websocket)
    
    async def emit_event(self, event_type: EventType, data: Dict[str, Any], 
                        user_id: Optional[str] = None, connection_type: Optional[str] = None):
        """Emit an event to subscribers"""
        message = {
            "type": event_type.value,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id:
            await self.send_to_user(message, user_id)
        else:
            await self.broadcast(message, connection_type)
    
    async def disconnect_user(self, user_id: str, reason: str = "User logged out"):
        """Disconnect all connections for a user"""
        user_id = str(user_id)  # Ensure string consistency
        if user_id not in self.connections:
            return 0
        
        websockets_to_close = list(self.connections[user_id].values())
        disconnected_count = 0
        
        for websocket in websockets_to_close:
            try:
                await websocket.close(code=1008, reason=reason)
                disconnected_count += 1
            except Exception as e:
                logger.debug(f"Error closing connection for {user_id}: {e}")
            finally:
                self.disconnect(websocket)
        
        logger.info(f"Disconnected {disconnected_count} connections for user {user_id}")
        return disconnected_count
    
    async def broadcast_user_logout(self, logout_data: Dict[str, Any]):
        """Broadcast user logout event to admin connections"""
        await self.emit_event(
            EventType.USER_LOGOUT,
            logout_data,
            connection_type=ConnectionType.ADMIN.value
        )
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        total_connections = sum(len(user_conns) for user_conns in self.connections.values())
        connection_types = {}
        user_counts = {}
        
        for user_id, user_connection_types in self.connections.items():
            user_counts[user_id] = len(user_connection_types)
            
            for conn_type, websocket in user_connection_types.items():
                connection_types[conn_type] = connection_types.get(conn_type, 0) + 1
        
        return {
            "total_users": len(self.connections),
            "total_connections": total_connections,
            "connection_types": connection_types,
            "user_counts": user_counts,
            "max_connections_per_user": self.max_connections_per_user,
            "max_total_connections": self.max_total_connections,
            "background_services_running": self._running,
            "supported_events": [event.value for event in EventType],
            "supported_connection_types": [conn_type.value for conn_type in ConnectionType]
        }
    
    async def _start_background_services(self):
        """Start background services"""
        if self._running:
            return
        
        self._running = True
        
        # Start health monitoring
        task = asyncio.create_task(self._health_monitor_loop())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        
        # Start system monitoring
        task = asyncio.create_task(self._system_monitor_loop())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        
        logger.info("Started WebSocket background services")
    
    async def _stop_background_services(self):
        """Stop all background services"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all tasks
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        logger.info("Stopped WebSocket background services")
    
    async def _health_monitor_loop(self):
        """Background task for health monitoring"""
        while self._running:
            try:
                # Check if we have health connections
                has_health_connections = any(
                    "health" in user_connection_types or "admin" in user_connection_types
                    for user_connection_types in self.connections.values()
                )
                
                if has_health_connections:
                    try:
                        from ..services.health_service import get_health_service
                        from ..core.database import get_database_session
                        
                        health_service = get_health_service()
                        async for db in get_database_session():
                            try:
                                health_summary = await health_service.get_forwarder_health_summary(db)
                                await self.emit_event(EventType.HEALTH_UPDATE, health_summary)
                                break
                            except Exception as e:
                                logger.error(f"Error getting health summary: {e}")
                                break
                    except Exception as e:
                        logger.error(f"Error in health monitoring: {e}")
                
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(60)
    
    async def _system_monitor_loop(self):
        """Background task for system monitoring"""
        while self._running:
            try:
                # Check if we have system connections
                has_system_connections = any(
                    "system" in user_connection_types or "admin" in user_connection_types
                    for user_connection_types in self.connections.values()
                )
                
                if has_system_connections:
                    system_status = await self._get_system_status()
                    await self.emit_event(EventType.SYSTEM_STATUS, system_status)
                
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in system monitor loop: {e}")
                await asyncio.sleep(120)
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        try:
            import psutil
            
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
                "active_connections": sum(len(user_conns) for user_conns in self.connections.values()),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "error": "Unable to get system status",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def _json_default(obj):
        """JSON serializer for datetime objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# Global WebSocket manager instance
_websocket_manager = None


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager