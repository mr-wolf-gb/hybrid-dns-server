"""
Unified WebSocket Manager - Single connection per user architecture
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Set, Any, Optional, List
from fastapi import WebSocket

from ..core.logging_config import get_logger
from .models import WSUser, WebSocketConnection, Event, EventType, EventPriority, ConnectionStatus
from .auth import get_websocket_authenticator, WebSocketAuthenticator
from .event_router import get_event_router, EventRouter

logger = get_logger(__name__)


class UnifiedWebSocketManager:
    """
    Unified WebSocket manager that maintains single connection per user
    with dynamic subscription management and health monitoring
    """
    
    def __init__(self):
        # Single connection per user: user_id -> WebSocketConnection
        self.connections: Dict[str, WebSocketConnection] = {}
        
        # Connection metadata and statistics
        self.connection_stats: Dict[str, Any] = {
            "total_connections": 0,
            "total_messages_sent": 0,
            "total_events_processed": 0,
            "start_time": datetime.utcnow()
        }
        
        # Event processing
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.event_processors: Dict[EventType, List[callable]] = {}
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        self._running = False
        
        # Connection limits and configuration
        self.max_total_connections = 500
        self.max_queue_size = 100
        self.health_check_interval = 30  # seconds
        self.cleanup_interval = 300  # 5 minutes
        
        # Authentication
        self.authenticator: WebSocketAuthenticator = get_websocket_authenticator()
        
        # Event routing
        self.event_router: EventRouter = get_event_router()
        
        # Connection lock for thread safety
        self._connection_lock = asyncio.Lock()
    
    async def connect_user(self, websocket: WebSocket, user: WSUser, client_ip: str = None) -> bool:
        """
        Connect a user with single connection per user architecture
        """
        async with self._connection_lock:
            try:
                # Check connection limits
                if len(self.connections) >= self.max_total_connections:
                    logger.warning(f"Max connections reached: {len(self.connections)}")
                    await websocket.close(code=1013, reason="Server overloaded")
                    return False
                
                # Validate session
                if not self.authenticator.validate_session(user):
                    logger.warning(f"Invalid session for user: {user.username}")
                    await websocket.close(code=1008, reason="Invalid session")
                    return False
                
                # Close existing connection if present
                existing_connection = self.connections.get(user.username)
                if existing_connection:
                    logger.info(f"Closing existing connection for user: {user.username}")
                    await existing_connection.close(code=1000, reason="Replaced by new connection")
                    await self._cleanup_connection(user.username)
                
                # Accept new WebSocket connection
                await websocket.accept()
                
                # Create new connection
                connection = WebSocketConnection(websocket=websocket, user=user)
                self.connections[user.username] = connection
                
                # Start connection services
                await connection.start_message_processor()
                await connection.start_health_monitoring(self.health_check_interval)
                
                # Update statistics
                self.connection_stats["total_connections"] += 1
                
                # Start background services if this is the first connection
                if not self._running:
                    await self._start_background_services()
                    # Start event router
                    await self.event_router.start()
                
                # Send connection established event
                await self._send_connection_established(connection)
                
                logger.info(f"User connected: {user.username} (total: {len(self.connections)})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect user {user.username}: {e}")
                try:
                    await websocket.close(code=1011, reason="Connection failed")
                except:
                    pass
                return False
    
    async def disconnect_user(self, user_id: str, reason: str = "User disconnected") -> None:
        """Disconnect a user and cleanup resources"""
        connection = self.connections.get(user_id)
        if not connection:
            return
        
        logger.info(f"Disconnecting user: {user_id}")
        
        try:
            await connection.close(code=1000, reason=reason)
        except Exception as e:
            logger.debug(f"Error closing connection for {user_id}: {e}")
        
        await self._cleanup_connection(user_id)
    
    async def _cleanup_connection(self, user_id: str):
        """Clean up connection resources"""
        if user_id in self.connections:
            del self.connections[user_id]
        
        # Stop background services if no connections remain
        if not self.connections and self._running:
            await self._stop_background_services()
            # Stop event router
            await self.event_router.stop()
    
    async def subscribe_to_events(self, user_id: str, event_types: List[EventType]) -> Set[EventType]:
        """Subscribe user to specific event types"""
        connection = self.connections.get(user_id)
        if not connection:
            return set()
        
        # Use event router's subscription manager
        allowed_events, errors = await self.event_router.subscription_manager.subscribe_to_events(
            connection.user, event_types
        )
        
        # Also update connection's local subscriptions for compatibility
        connection.subscribe_to_events(list(allowed_events))
        
        # Send subscription update confirmation
        await self._send_subscription_update(connection, allowed_events, errors)
        
        logger.info(f"User {user_id} subscribed to {len(allowed_events)} events")
        return allowed_events
    
    async def unsubscribe_from_events(self, user_id: str, event_types: List[EventType]) -> Set[EventType]:
        """Unsubscribe user from specific event types"""
        connection = self.connections.get(user_id)
        if not connection:
            return set()
        
        # Use event router's subscription manager
        removed_events, errors = await self.event_router.subscription_manager.unsubscribe_from_events(
            connection.user, event_types
        )
        
        # Also update connection's local subscriptions for compatibility
        connection.unsubscribe_from_events(list(removed_events))
        
        # Send subscription update confirmation
        await self._send_subscription_update(connection, connection.subscriptions, errors)
        
        logger.info(f"User {user_id} unsubscribed from {len(removed_events)} events")
        return removed_events
    
    async def broadcast_event(self, event: Event) -> int:
        """Broadcast event to all subscribed users using intelligent routing"""
        if not self.connections:
            return 0
        
        # Use event router for intelligent routing and filtering
        routing_result = await self.event_router.route_event(event, {
            user_id: connection.user for user_id, connection in self.connections.items()
        })
        
        if routing_result.decision.value != "route":
            logger.debug(f"Event {event.id} not routed: {routing_result.routing_metadata}")
            return 0
        
        sent_count = 0
        failed_connections = []
        
        # Send to target users with filtered data
        for user_id in routing_result.target_users:
            connection = self.connections.get(user_id)
            if not connection:
                continue
            
            try:
                # Get filtered data for this user
                filtered_data = routing_result.filtered_data.get(user_id, event.data)
                
                # Create message with filtered data
                message = {
                    "id": event.id,
                    "type": event.type.value,
                    "data": filtered_data,
                    "timestamp": event.timestamp.isoformat(),
                    "priority": event.priority.value,
                    "metadata": event.metadata
                }
                
                success = await connection.send_message(message)
                
                if success:
                    sent_count += 1
                else:
                    failed_connections.append(user_id)
                    
            except Exception as e:
                logger.error(f"Error sending event to {user_id}: {e}")
                failed_connections.append(user_id)
        
        # Clean up failed connections
        for user_id in failed_connections:
            await self._cleanup_connection(user_id)
        
        # Update statistics
        self.connection_stats["total_events_processed"] += 1
        self.connection_stats["total_messages_sent"] += sent_count
        
        return sent_count
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific user"""
        connection = self.connections.get(user_id)
        if not connection:
            return False
        
        success = await connection.send_message(message)
        if success:
            self.connection_stats["total_messages_sent"] += 1
        
        return success
    
    def _should_send_event_to_user(self, event: Event, connection: WebSocketConnection) -> bool:
        """Check if event should be sent to user"""
        # Check if user is subscribed to event type
        if not connection.is_subscribed_to(event.type):
            return False
        
        # Check user permissions
        if not event.should_send_to_user(connection.user):
            return False
        
        # Check connection health
        if not connection.is_healthy():
            return False
        
        return True
    
    async def _send_connection_established(self, connection: WebSocketConnection):
        """Send connection established event"""
        message = {
            "type": EventType.CONNECTION_ESTABLISHED.value,
            "data": {
                "user_id": connection.user.id,
                "username": connection.user.username,
                "is_admin": connection.user.is_admin,
                "subscriptions": [event.value for event in connection.subscriptions],
                "connected_at": connection.connected_at.isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await connection.send_message(message)
    
    async def _send_subscription_update(self, connection: WebSocketConnection, subscriptions: Set[EventType], errors: List[str] = None):
        """Send subscription update event"""
        message = {
            "type": EventType.SUBSCRIPTION_UPDATED.value,
            "data": {
                "subscriptions": [event.value for event in subscriptions],
                "updated_at": datetime.utcnow().isoformat(),
                "errors": errors or []
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await connection.send_message(message)
    
    async def emit_event(self, event_type: EventType, data: Dict[str, Any], 
                        source_user_id: Optional[str] = None, 
                        priority: EventPriority = EventPriority.NORMAL) -> str:
        """Emit an event to the system"""
        event_id = str(uuid.uuid4())
        
        event = Event(
            id=event_id,
            type=event_type,
            data=data,
            source_user_id=source_user_id,
            priority=priority
        )
        
        # Add to event queue for processing
        try:
            await self.event_queue.put(event)
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping event")
        
        return event_id
    
    async def _start_background_services(self):
        """Start background services"""
        if self._running:
            return
        
        self._running = True
        
        # Start event processor
        task = asyncio.create_task(self._event_processor_loop())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        # Start health monitor
        task = asyncio.create_task(self._health_monitor_loop())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        # Start cleanup service
        task = asyncio.create_task(self._cleanup_loop())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        
        logger.info("Started unified WebSocket background services")
    
    async def _stop_background_services(self):
        """Stop all background services"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all background tasks
        for task in list(self._background_tasks):
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._background_tasks.clear()
        logger.info("Stopped unified WebSocket background services")
    
    async def _event_processor_loop(self):
        """Background task to process events from queue"""
        while self._running:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # Process event
                await self.broadcast_event(event)
                self.event_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def _health_monitor_loop(self):
        """Background task for connection health monitoring"""
        while self._running:
            try:
                unhealthy_connections = []
                
                for user_id, connection in list(self.connections.items()):
                    if not connection.is_healthy():
                        logger.warning(f"Unhealthy connection detected: {user_id}")
                        unhealthy_connections.append(user_id)
                
                # Clean up unhealthy connections
                for user_id in unhealthy_connections:
                    await self.disconnect_user(user_id, "Connection unhealthy")
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Background task for periodic cleanup"""
        while self._running:
            try:
                # Clean up expired sessions
                self.authenticator.cleanup_expired_sessions()
                
                # Clean up event queue if too large
                if self.event_queue.qsize() > self.max_queue_size * 2:
                    logger.warning("Event queue too large, clearing old events")
                    # Clear half the queue
                    for _ in range(self.event_queue.qsize() // 2):
                        try:
                            self.event_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                
                await asyncio.sleep(self.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(300)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics"""
        uptime = datetime.utcnow() - self.connection_stats["start_time"]
        
        connection_details = {}
        for user_id, connection in self.connections.items():
            connection_details[user_id] = connection.get_connection_info()
        
        return {
            "total_connections": len(self.connections),
            "max_connections": self.max_total_connections,
            "total_messages_sent": self.connection_stats["total_messages_sent"],
            "total_events_processed": self.connection_stats["total_events_processed"],
            "event_queue_size": self.event_queue.qsize(),
            "uptime_seconds": uptime.total_seconds(),
            "background_services_running": self._running,
            "connection_details": connection_details,
            "session_stats": self.authenticator.get_session_stats()
        }
    
    def get_user_connection_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get connection information for specific user"""
        connection = self.connections.get(user_id)
        if not connection:
            return None
        
        return connection.get_connection_info()
    
    async def handle_user_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle incoming message from user"""
        connection = self.connections.get(user_id)
        if not connection:
            return False
        
        message_type = message.get("type")
        data = message.get("data", {})
        
        try:
            # Basic connection messages
            if message_type == "ping":
                await self._handle_ping(connection)
            elif message_type == "pong":
                await self._handle_pong(connection, data)
            
            # Subscription management messages
            elif message_type == "subscribe_events":
                event_types = [EventType(et) for et in data.get("event_types", [])]
                await self.subscribe_to_events(user_id, event_types)
            elif message_type == "unsubscribe_events":
                event_types = [EventType(et) for et in data.get("event_types", [])]
                await self.unsubscribe_from_events(user_id, event_types)
            elif message_type == "subscribe_category":
                categories = data.get("categories", [])
                allowed_categories, errors = await self.event_router.subscription_manager.subscribe_to_category(
                    connection.user, categories
                )
                await connection.send_message({
                    "type": "category_subscription_updated",
                    "data": {
                        "categories": list(allowed_categories),
                        "errors": errors,
                        "updated_at": datetime.utcnow().isoformat()
                    },
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif message_type == "get_subscription_info":
                subscription_info = self.event_router.subscription_manager.get_user_subscriptions(user_id)
                await connection.send_message({
                    "type": "subscription_info",
                    "data": subscription_info,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Connection health and status messages
            elif message_type == "get_connection_status":
                await self._handle_get_connection_status(connection)
            elif message_type == "health_check":
                await self._handle_health_check(connection)
            
            # Administrative messages (admin only)
            elif message_type == "get_connection_stats" and connection.user.is_admin:
                stats = self.get_connection_stats()
                await connection.send_message({
                    "type": "connection_stats",
                    "data": stats,
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif message_type == "get_router_stats" and connection.user.is_admin:
                router_stats = self.event_router.get_router_stats()
                await connection.send_message({
                    "type": "router_stats",
                    "data": router_stats,
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif message_type == "get_all_connections" and connection.user.is_admin:
                await self._handle_get_all_connections(connection)
            elif message_type == "disconnect_user" and connection.user.is_admin:
                target_user_id = data.get("user_id")
                reason = data.get("reason", "Admin disconnect")
                if target_user_id:
                    await self.disconnect_user(target_user_id, reason)
                    await connection.send_message({
                        "type": "user_disconnected",
                        "data": {"user_id": target_user_id, "reason": reason},
                        "timestamp": datetime.utcnow().isoformat()
                    })
            elif message_type == "broadcast_admin_message" and connection.user.is_admin:
                admin_message = data.get("message", "")
                priority = data.get("priority", "normal")
                await self._handle_admin_broadcast(connection, admin_message, priority)
            
            # Debugging and monitoring messages (admin only)
            elif message_type == "get_event_queue_status" and connection.user.is_admin:
                await self._handle_get_event_queue_status(connection)
            elif message_type == "get_system_metrics" and connection.user.is_admin:
                await self._handle_get_system_metrics(connection)
            elif message_type == "clear_event_queue" and connection.user.is_admin:
                await self._handle_clear_event_queue(connection)
            
            # User preference messages
            elif message_type == "set_message_preferences":
                await self._handle_set_message_preferences(connection, data)
            elif message_type == "get_message_preferences":
                await self._handle_get_message_preferences(connection)
            
            # Unknown message type
            else:
                await connection.send_message({
                    "type": "error",
                    "data": {
                        "message": f"Unknown message type: {message_type}",
                        "supported_types": self._get_supported_message_types(connection.user.is_admin)
                    },
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return True
            
        except ValueError as e:
            # Handle validation errors (e.g., invalid event types)
            logger.warning(f"Validation error in message from {user_id}: {e}")
            await connection.send_message({
                "type": "validation_error",
                "data": {"message": f"Invalid data: {str(e)}"},
                "timestamp": datetime.utcnow().isoformat()
            })
            return False
        except Exception as e:
            logger.error(f"Error handling message from {user_id}: {e}")
            await connection.send_message({
                "type": "error",
                "data": {"message": f"Message processing error: {str(e)}"},
                "timestamp": datetime.utcnow().isoformat()
            })
            return False
    
    async def _handle_ping(self, connection: WebSocketConnection):
        """Handle ping message"""
        await connection.send_message({
            "type": EventType.PONG.value,
            "data": {
                "timestamp": datetime.utcnow().isoformat(),
                "connection_health": connection.is_healthy(),
                "uptime": (datetime.utcnow() - connection.connected_at).total_seconds()
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_pong(self, connection: WebSocketConnection, data: Dict[str, Any] = None):
        """Handle pong message from client"""
        success = connection.handle_pong(data)
        if success:
            logger.debug(f"Received valid pong from {connection.user.username}")
        else:
            logger.warning(f"Received invalid pong from {connection.user.username}")
            await connection.send_message({
                "type": "error",
                "data": {"message": "Invalid pong response"},
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _handle_get_connection_status(self, connection: WebSocketConnection):
        """Handle get connection status message"""
        status_data = {
            "user_id": connection.user.id,
            "username": connection.user.username,
            "connected_at": connection.connected_at.isoformat(),
            "is_healthy": connection.is_healthy(),
            "subscriptions": [event.value for event in connection.subscriptions],
            "message_count": connection.message_count,
            "last_activity": connection.last_activity.isoformat() if hasattr(connection, 'last_activity') else None,
            "connection_id": connection.connection_id if hasattr(connection, 'connection_id') else None
        }
        
        await connection.send_message({
            "type": "connection_status",
            "data": status_data,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_health_check(self, connection: WebSocketConnection):
        """Handle health check message"""
        health_data = {
            "connection_healthy": connection.is_healthy(),
            "websocket_state": connection.websocket.client_state.name if hasattr(connection.websocket, 'client_state') else "unknown",
            "last_ping": connection.last_ping.isoformat() if hasattr(connection, 'last_ping') else None,
            "last_pong": connection.last_pong.isoformat() if hasattr(connection, 'last_pong') else None,
            "message_queue_size": len(connection.message_queue) if hasattr(connection, 'message_queue') else 0,
            "server_time": datetime.utcnow().isoformat()
        }
        
        await connection.send_message({
            "type": "health_check_response",
            "data": health_data,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_get_all_connections(self, connection: WebSocketConnection):
        """Handle get all connections message (admin only)"""
        all_connections = {}
        for user_id, conn in self.connections.items():
            all_connections[user_id] = {
                "username": conn.user.username,
                "is_admin": conn.user.is_admin,
                "connected_at": conn.connected_at.isoformat(),
                "is_healthy": conn.is_healthy(),
                "subscriptions": [event.value for event in conn.subscriptions],
                "message_count": conn.message_count
            }
        
        await connection.send_message({
            "type": "all_connections",
            "data": {
                "connections": all_connections,
                "total_count": len(all_connections)
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_admin_broadcast(self, connection: WebSocketConnection, message: str, priority: str):
        """Handle admin broadcast message"""
        try:
            priority_enum = EventPriority(priority)
        except ValueError:
            priority_enum = EventPriority.NORMAL
        
        # Create admin broadcast event
        event_id = await self.emit_event(
            event_type=EventType.ADMIN_BROADCAST,
            data={
                "message": message,
                "from_admin": connection.user.username,
                "broadcast_time": datetime.utcnow().isoformat()
            },
            source_user_id=connection.user.id,
            priority=priority_enum
        )
        
        await connection.send_message({
            "type": "admin_broadcast_sent",
            "data": {
                "event_id": event_id,
                "message": message,
                "priority": priority,
                "sent_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_get_event_queue_status(self, connection: WebSocketConnection):
        """Handle get event queue status message (admin only)"""
        queue_status = {
            "queue_size": self.event_queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "queue_full": self.event_queue.full(),
            "background_services_running": self._running,
            "active_background_tasks": len(self._background_tasks)
        }
        
        await connection.send_message({
            "type": "event_queue_status",
            "data": queue_status,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_get_system_metrics(self, connection: WebSocketConnection):
        """Handle get system metrics message (admin only)"""
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            metrics = {
                "system": {
                    "cpu_usage": cpu_percent,
                    "memory_usage": memory.percent,
                    "memory_available": memory.available,
                    "disk_usage": disk.percent,
                    "disk_free": disk.free
                },
                "process": {
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads()
                },
                "websocket": {
                    "total_connections": len(self.connections),
                    "event_queue_size": self.event_queue.qsize(),
                    "total_messages_sent": self.connection_stats["total_messages_sent"],
                    "total_events_processed": self.connection_stats["total_events_processed"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            metrics = {
                "error": "Unable to get system metrics",
                "error_details": str(e)
            }
        
        await connection.send_message({
            "type": "system_metrics",
            "data": metrics,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_clear_event_queue(self, connection: WebSocketConnection):
        """Handle clear event queue message (admin only)"""
        cleared_count = 0
        
        # Clear the event queue
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
                cleared_count += 1
            except asyncio.QueueEmpty:
                break
        
        await connection.send_message({
            "type": "event_queue_cleared",
            "data": {
                "cleared_events": cleared_count,
                "cleared_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Admin {connection.user.username} cleared {cleared_count} events from queue")
    
    async def _handle_set_message_preferences(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle set message preferences message"""
        preferences = data.get("preferences", {})
        
        # Store preferences in connection metadata
        if not hasattr(connection, 'preferences'):
            connection.preferences = {}
        
        connection.preferences.update(preferences)
        
        await connection.send_message({
            "type": "message_preferences_updated",
            "data": {
                "preferences": connection.preferences,
                "updated_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _handle_get_message_preferences(self, connection: WebSocketConnection):
        """Handle get message preferences message"""
        preferences = getattr(connection, 'preferences', {})
        
        await connection.send_message({
            "type": "message_preferences",
            "data": {
                "preferences": preferences,
                "default_preferences": {
                    "batch_messages": True,
                    "compress_data": False,
                    "max_message_rate": 100,
                    "priority_filter": "normal"
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def _get_supported_message_types(self, is_admin: bool = False) -> List[str]:
        """Get list of supported message types"""
        basic_types = [
            "ping", "pong", "subscribe_events", "unsubscribe_events",
            "subscribe_category", "get_subscription_info", "get_connection_status",
            "health_check", "set_message_preferences", "get_message_preferences"
        ]
        
        admin_types = [
            "get_connection_stats", "get_router_stats", "get_all_connections",
            "disconnect_user", "broadcast_admin_message", "get_event_queue_status",
            "get_system_metrics", "clear_event_queue"
        ]
        
        if is_admin:
            return basic_types + admin_types
        return basic_types
    
    async def shutdown(self):
        """Gracefully shutdown the WebSocket manager"""
        logger.info("Shutting down unified WebSocket manager")
        
        # Disconnect all users
        for user_id in list(self.connections.keys()):
            await self.disconnect_user(user_id, "Server shutdown")
        
        # Stop background services
        await self._stop_background_services()
        
        # Stop event router
        await self.event_router.stop()
        
        logger.info("Unified WebSocket manager shutdown complete")


# Global unified WebSocket manager instance
_unified_websocket_manager = None


def get_unified_websocket_manager() -> UnifiedWebSocketManager:
    """Get the global unified WebSocket manager instance"""
    global _unified_websocket_manager
    if _unified_websocket_manager is None:
        _unified_websocket_manager = UnifiedWebSocketManager()
    return _unified_websocket_manager