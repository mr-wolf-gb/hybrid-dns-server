"""
WebSocket connection data models and types
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Set, Optional, List
from fastapi import WebSocket

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class EventType(Enum):
    """WebSocket event types"""
    # Health and monitoring events
    HEALTH_UPDATE = "health_update"
    HEALTH_ALERT = "health_alert"
    FORWARDER_STATUS_CHANGE = "forwarder_status_change"
    SYSTEM_STATUS = "system_status"
    
    # DNS management events
    ZONE_CREATED = "zone_created"
    ZONE_UPDATED = "zone_updated"
    ZONE_DELETED = "zone_deleted"
    RECORD_CREATED = "record_created"
    RECORD_UPDATED = "record_updated"
    RECORD_DELETED = "record_deleted"
    BIND_RELOAD = "bind_reload"
    CONFIG_CHANGE = "config_change"
    
    # Security events
    SECURITY_ALERT = "security_alert"
    RPZ_UPDATE = "rpz_update"
    THREAT_DETECTED = "threat_detected"
    
    # User and session events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    SESSION_EXPIRED = "session_expired"
    
    # Connection events
    CONNECTION_ESTABLISHED = "connection_established"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    PING = "ping"
    PONG = "pong"
    
    # Administrative events
    ADMIN_BROADCAST = "admin_broadcast"


class EventPriority(Enum):
    """Event priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ConnectionStatus(Enum):
    """WebSocket connection status"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECOVERING = "recovering"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class WSUser:
    """WebSocket user information"""
    id: int
    username: str
    email: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True
    created_at: Optional[str] = None
    
    def has_permission(self, event_type: EventType) -> bool:
        """Check if user has permission to receive event type"""
        # Admin users can access all events
        if self.is_admin:
            return True
        
        # Regular users cannot access admin-only events
        admin_only_events = {
            EventType.USER_LOGIN,
            EventType.USER_LOGOUT,
            EventType.SESSION_EXPIRED
        }
        
        return event_type not in admin_only_events


@dataclass
class WebSocketConnection:
    """WebSocket connection with health monitoring, message queuing, and error recovery"""
    websocket: WebSocket
    user: WSUser
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: datetime = field(default_factory=datetime.utcnow)
    last_pong: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    subscriptions: Set[EventType] = field(default_factory=set)
    message_count: int = 0
    error_count: int = 0
    consecutive_errors: int = 0
    status: ConnectionStatus = ConnectionStatus.CONNECTING
    message_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=100))
    _ping_task: Optional[asyncio.Task] = None
    _send_task: Optional[asyncio.Task] = None
    _recovery_task: Optional[asyncio.Task] = None
    
    # Error recovery configuration
    max_consecutive_errors: int = 5
    error_recovery_delay: float = 1.0
    max_error_recovery_delay: float = 30.0
    ping_timeout: float = 10.0
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def __post_init__(self):
        """Initialize connection after creation"""
        self.status = ConnectionStatus.CONNECTED
        self.subscriptions = self._get_default_subscriptions()
    
    def _get_default_subscriptions(self) -> Set[EventType]:
        """Get default event subscriptions based on user permissions"""
        default_events = {
            EventType.HEALTH_UPDATE,
            EventType.SYSTEM_STATUS,
            EventType.CONNECTION_ESTABLISHED,
            EventType.SUBSCRIPTION_UPDATED,
            EventType.PING,
            EventType.PONG
        }
        
        # Add DNS management events for all users
        default_events.update({
            EventType.ZONE_CREATED,
            EventType.ZONE_UPDATED,
            EventType.ZONE_DELETED,
            EventType.RECORD_CREATED,
            EventType.RECORD_UPDATED,
            EventType.RECORD_DELETED,
            EventType.BIND_RELOAD,
            EventType.CONFIG_CHANGE
        })
        
        # Add security events for all users
        default_events.update({
            EventType.SECURITY_ALERT,
            EventType.RPZ_UPDATE,
            EventType.THREAT_DETECTED
        })
        
        # Add admin events for admin users
        if self.user.is_admin:
            default_events.update({
                EventType.USER_LOGIN,
                EventType.USER_LOGOUT,
                EventType.SESSION_EXPIRED
            })
        
        return default_events
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a message to the WebSocket connection with error recovery"""
        try:
            if self.status not in [ConnectionStatus.CONNECTED, ConnectionStatus.RECOVERING]:
                return False
            
            # Add message to queue for processing
            try:
                self.message_queue.put_nowait(message)
                return True
            except asyncio.QueueFull:
                logger.warning(f"Message queue full for user {self.user.username}")
                # Try to send immediately as fallback
                return await self._send_message_direct(message)
                
        except Exception as e:
            logger.error(f"Failed to queue message for {self.user.username}: {e}")
            await self._handle_error(e)
            return False
    
    async def _send_message_direct(self, message: Dict[str, Any]) -> bool:
        """Send message directly to WebSocket with retry logic"""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                await self.websocket.send_text(json.dumps(message, default=self._json_serializer))
                self.message_count += 1
                self.last_activity = datetime.utcnow()
                self.consecutive_errors = 0  # Reset on success
                return True
                
            except Exception as e:
                self.error_count += 1
                self.consecutive_errors += 1
                
                if attempt < max_retries - 1:
                    logger.debug(f"Message send attempt {attempt + 1} failed for {self.user.username}, retrying: {e}")
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"Failed to send message to {self.user.username} after {max_retries} attempts: {e}")
                    await self._handle_error(e)
                    return False
        
        return False
    
    async def _handle_error(self, error: Exception):
        """Handle connection errors with recovery logic"""
        logger.error(f"Connection error for {self.user.username}: {error}")
        
        # Check if we should attempt recovery
        if self.consecutive_errors >= self.max_consecutive_errors:
            logger.error(f"Too many consecutive errors for {self.user.username}, marking as failed")
            self.status = ConnectionStatus.ERROR
            return
        
        # Start error recovery if not already running
        if self.status != ConnectionStatus.RECOVERING:
            self.status = ConnectionStatus.RECOVERING
            if not self._recovery_task or self._recovery_task.done():
                self._recovery_task = asyncio.create_task(self._error_recovery_loop())
    
    async def _error_recovery_loop(self):
        """Error recovery loop with exponential backoff"""
        recovery_attempts = 0
        max_recovery_attempts = 5
        
        while (self.status == ConnectionStatus.RECOVERING and 
               recovery_attempts < max_recovery_attempts):
            
            recovery_attempts += 1
            delay = min(self.error_recovery_delay * (2 ** recovery_attempts), 
                       self.max_error_recovery_delay)
            
            logger.info(f"Attempting error recovery for {self.user.username} "
                       f"(attempt {recovery_attempts}/{max_recovery_attempts}) "
                       f"after {delay}s delay")
            
            await asyncio.sleep(delay)
            
            # Test connection health
            if await self._test_connection_health():
                logger.info(f"Connection recovered for {self.user.username}")
                self.status = ConnectionStatus.CONNECTED
                self.consecutive_errors = 0
                return
            
            logger.warning(f"Recovery attempt {recovery_attempts} failed for {self.user.username}")
        
        # Recovery failed
        logger.error(f"Error recovery failed for {self.user.username} after {recovery_attempts} attempts")
        self.status = ConnectionStatus.ERROR
    
    async def _test_connection_health(self) -> bool:
        """Test if connection is healthy"""
        try:
            # Send a simple ping to test connection
            test_message = {
                "type": "connection_test",
                "data": {"timestamp": datetime.utcnow().isoformat()},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Try to send test message with short timeout
            await asyncio.wait_for(
                self.websocket.send_text(json.dumps(test_message, default=self._json_serializer)),
                timeout=5.0
            )
            
            return True
            
        except Exception as e:
            logger.debug(f"Connection health test failed for {self.user.username}: {e}")
            return False
    
    async def start_message_processor(self):
        """Start background task to process message queue"""
        if self._send_task and not self._send_task.done():
            return
        
        self._send_task = asyncio.create_task(self._process_message_queue())
    
    async def _process_message_queue(self):
        """Process messages from the queue"""
        while self.status == ConnectionStatus.CONNECTED:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                await self._send_message_direct(message)
                self.message_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message queue for {self.user.username}: {e}")
                break
    
    async def ping(self) -> bool:
        """Send ping to check connection health with timeout"""
        try:
            ping_message = {
                "type": EventType.PING.value,
                "data": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "connection_id": self.connection_id,
                    "expect_pong": True
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send ping with timeout
            success = await asyncio.wait_for(
                self._send_message_direct(ping_message),
                timeout=self.ping_timeout
            )
            
            if success:
                self.last_ping = datetime.utcnow()
            return success
            
        except asyncio.TimeoutError:
            logger.warning(f"Ping timeout for {self.user.username}")
            await self._handle_error(Exception("Ping timeout"))
            return False
        except Exception as e:
            logger.debug(f"Ping failed for {self.user.username}: {e}")
            await self._handle_error(e)
            return False
    
    def handle_pong(self, pong_data: Dict[str, Any] = None):
        """Handle pong response from client"""
        self.last_pong = datetime.utcnow()
        
        # Validate pong if it contains connection_id
        if pong_data and "connection_id" in pong_data:
            if pong_data["connection_id"] != self.connection_id:
                logger.warning(f"Pong connection_id mismatch for {self.user.username}")
                return False
        
        # Reset consecutive errors on successful pong
        if self.consecutive_errors > 0:
            logger.debug(f"Pong received, resetting error count for {self.user.username}")
            self.consecutive_errors = 0
        
        return True
    
    async def start_health_monitoring(self, ping_interval: int = 30):
        """Start health monitoring with periodic pings"""
        if self._ping_task and not self._ping_task.done():
            return
        
        self._ping_task = asyncio.create_task(self._health_monitor_loop(ping_interval))
    
    async def _health_monitor_loop(self, ping_interval: int):
        """Background task for connection health monitoring"""
        while self.status == ConnectionStatus.CONNECTED:
            try:
                await asyncio.sleep(ping_interval)
                
                # Check if connection is still healthy
                if not await self.ping():
                    logger.warning(f"Health check failed for {self.user.username}")
                    self.status = ConnectionStatus.ERROR
                    break
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor for {self.user.username}: {e}")
                break
    
    def is_subscribed_to(self, event_type: EventType) -> bool:
        """Check if connection is subscribed to event type"""
        return event_type in self.subscriptions
    
    def subscribe_to_events(self, event_types: List[EventType]) -> Set[EventType]:
        """Subscribe to additional event types"""
        allowed_events = set()
        
        for event_type in event_types:
            if self.user.has_permission(event_type):
                self.subscriptions.add(event_type)
                allowed_events.add(event_type)
            else:
                logger.warning(f"User {self.user.username} denied subscription to {event_type.value}")
        
        return allowed_events
    
    def unsubscribe_from_events(self, event_types: List[EventType]) -> Set[EventType]:
        """Unsubscribe from event types"""
        removed_events = set()
        
        for event_type in event_types:
            if event_type in self.subscriptions:
                self.subscriptions.remove(event_type)
                removed_events.add(event_type)
        
        return removed_events
    
    def is_healthy(self) -> bool:
        """Check if connection is healthy with comprehensive checks"""
        # Connection must be in a good state
        if self.status not in [ConnectionStatus.CONNECTED, ConnectionStatus.RECOVERING]:
            return False
        
        now = datetime.utcnow()
        
        # Check if last ping was recent (within 2 minutes)
        time_since_ping = now - self.last_ping
        if time_since_ping.total_seconds() > 120:
            return False
        
        # Check if we received a pong recently (within 3 minutes)
        time_since_pong = now - self.last_pong
        if time_since_pong.total_seconds() > 180:
            return False
        
        # Check consecutive error count
        if self.consecutive_errors >= self.max_consecutive_errors:
            return False
        
        # Check total error rate (errors per minute)
        connection_duration = (now - self.connected_at).total_seconds() / 60.0
        if connection_duration > 1:  # Only check after 1 minute
            error_rate = self.error_count / connection_duration
            if error_rate > 5:  # More than 5 errors per minute
                return False
        
        # Check message queue health
        if self.message_queue.qsize() >= self.message_queue.maxsize * 0.9:
            logger.warning(f"Message queue nearly full for {self.user.username}")
            return False
        
        return True
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status"""
        now = datetime.utcnow()
        connection_duration = (now - self.connected_at).total_seconds()
        
        return {
            "is_healthy": self.is_healthy(),
            "status": self.status.value,
            "connection_duration": connection_duration,
            "last_ping_ago": (now - self.last_ping).total_seconds(),
            "last_pong_ago": (now - self.last_pong).total_seconds(),
            "last_activity_ago": (now - self.last_activity).total_seconds(),
            "error_count": self.error_count,
            "consecutive_errors": self.consecutive_errors,
            "message_count": self.message_count,
            "queue_size": self.message_queue.qsize(),
            "queue_capacity": self.message_queue.maxsize,
            "error_rate_per_minute": self.error_count / max(connection_duration / 60.0, 1),
            "connection_id": self.connection_id
        }
    
    async def close(self, code: int = 1000, reason: str = "Connection closed"):
        """Close the WebSocket connection gracefully with comprehensive cleanup"""
        logger.info(f"Closing connection for {self.user.username}: {reason}")
        self.status = ConnectionStatus.DISCONNECTING
        
        # Cancel all background tasks
        tasks_to_cancel = []
        if self._ping_task and not self._ping_task.done():
            tasks_to_cancel.append(self._ping_task)
        if self._send_task and not self._send_task.done():
            tasks_to_cancel.append(self._send_task)
        if self._recovery_task and not self._recovery_task.done():
            tasks_to_cancel.append(self._recovery_task)
        
        # Cancel tasks
        for task in tasks_to_cancel:
            task.cancel()
        
        # Wait for tasks to complete with timeout
        if tasks_to_cancel:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for background tasks to complete for {self.user.username}")
        
        # Clear message queue
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        # Close WebSocket
        try:
            await self.websocket.close(code=code, reason=reason)
        except Exception as e:
            logger.debug(f"Error closing WebSocket for {self.user.username}: {e}")
        
        self.status = ConnectionStatus.DISCONNECTED
        logger.info(f"Connection closed for {self.user.username}")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get comprehensive connection information"""
        health_status = self.get_health_status()
        
        return {
            "user_id": self.user.id,
            "username": self.user.username,
            "is_admin": self.user.is_admin,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "last_pong": self.last_pong.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "message_count": self.message_count,
            "error_count": self.error_count,
            "consecutive_errors": self.consecutive_errors,
            "status": self.status.value,
            "subscriptions": [event.value for event in self.subscriptions],
            "queue_size": self.message_queue.qsize(),
            "queue_capacity": self.message_queue.maxsize,
            "connection_id": self.connection_id,
            "health_status": health_status,
            "is_healthy": health_status["is_healthy"]
        }
    
    @staticmethod
    def _json_serializer(obj):
        """JSON serializer for datetime objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@dataclass
class Event:
    """WebSocket event data model"""
    id: str
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_user_id: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_websocket_message(self) -> Dict[str, Any]:
        """Convert event to WebSocket message format"""
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "metadata": self.metadata
        }
    
    def should_send_to_user(self, user: WSUser) -> bool:
        """Check if event should be sent to user based on permissions"""
        return user.has_permission(self.type)