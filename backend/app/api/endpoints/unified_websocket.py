"""
Unified WebSocket endpoint - Single connection per user
Enhanced with comprehensive error handling and recovery
"""

import json
import asyncio
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from datetime import datetime
import traceback

from ...websocket.unified_manager import get_unified_websocket_manager
from ...websocket.auth import get_websocket_authenticator
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


class WebSocketError(Exception):
    """Custom WebSocket error with error codes"""
    def __init__(self, message: str, error_code: str = "WEBSOCKET_ERROR", close_code: int = 1011):
        self.message = message
        self.error_code = error_code
        self.close_code = close_code
        super().__init__(message)


class AuthenticationError(WebSocketError):
    """Authentication-related WebSocket error"""
    def __init__(self, message: str):
        super().__init__(message, "AUTH_ERROR", 1008)


class ConnectionLimitError(WebSocketError):
    """Connection limit exceeded error"""
    def __init__(self, message: str):
        super().__init__(message, "CONNECTION_LIMIT", 1013)


class MessageProcessingError(WebSocketError):
    """Message processing error"""
    def __init__(self, message: str):
        super().__init__(message, "MESSAGE_ERROR", 1011)


@router.websocket("/ws")
async def unified_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Authentication token")
):
    """
    Unified WebSocket endpoint for all real-time communication
    
    Features:
    - Single connection per user
    - Dynamic event subscription management
    - Enhanced authentication and authorization
    - Connection health monitoring
    - Comprehensive error handling and recovery
    - Automatic reconnection support
    """
    websocket_manager = get_unified_websocket_manager()
    authenticator = get_websocket_authenticator()
    user = None
    connection_established = False
    
    try:
        # Enhanced authentication with detailed error handling
        if not token:
            raise AuthenticationError("Authentication token required")
        
        # Get client IP for security and logging
        client_ip = None
        try:
            client_ip = websocket.client.host if websocket.client else None
        except Exception as e:
            logger.warning(f"Could not get client IP: {e}")
        
        # Authenticate user with enhanced error handling
        try:
            user = await authenticator.authenticate_user(token, client_ip)
            if not user:
                raise AuthenticationError("Invalid authentication token")
        except Exception as e:
            logger.error(f"Authentication error for IP {client_ip}: {e}")
            raise AuthenticationError(f"Authentication failed: {str(e)}")
        
        # Connect user to unified manager with error handling
        try:
            connection_success = await websocket_manager.connect_user(websocket, user, client_ip)
            if not connection_success:
                raise ConnectionLimitError("Failed to establish connection - server may be overloaded")
            connection_established = True
        except Exception as e:
            logger.error(f"Connection error for user {user.username}: {e}")
            raise ConnectionLimitError(f"Connection failed: {str(e)}")
        
        logger.info(f"Unified WebSocket established: {user.username} from {client_ip}")
        
        # Enhanced message handling loop with recovery mechanisms
        consecutive_errors = 0
        max_consecutive_errors = 5
        last_activity = datetime.utcnow()
        
        while True:
            try:
                # Receive message with configurable timeout
                timeout = 300.0  # 5 minutes default
                data = await asyncio.wait_for(websocket.receive_text(), timeout=timeout)
                
                # Reset error counter on successful message receive
                consecutive_errors = 0
                last_activity = datetime.utcnow()
                
                # Enhanced JSON parsing with detailed error info
                try:
                    message = json.loads(data)
                    if not isinstance(message, dict):
                        raise ValueError("Message must be a JSON object")
                except json.JSONDecodeError as e:
                    raise MessageProcessingError(f"Invalid JSON format: {str(e)}")
                except ValueError as e:
                    raise MessageProcessingError(str(e))
                
                # Validate message structure
                if "type" not in message:
                    raise MessageProcessingError("Message must contain 'type' field")
                
                # Handle message through unified manager with error recovery
                try:
                    success = await websocket_manager.handle_user_message(user.username, message)
                    if not success:
                        logger.warning(f"Message handling failed for {user.username}: {message.get('type')}")
                except Exception as e:
                    logger.error(f"Error in message handler for {user.username}: {e}")
                    await _send_error_message(websocket_manager, user.username, 
                                            f"Message processing error: {str(e)}", "MESSAGE_HANDLER_ERROR")
                
            except asyncio.TimeoutError:
                # Enhanced heartbeat with connection health check
                try:
                    # Check if connection is still healthy
                    connection_info = websocket_manager.get_user_connection_info(user.username)
                    if not connection_info:
                        logger.warning(f"Connection lost for {user.username}")
                        break
                    
                    # Send heartbeat ping
                    await websocket_manager.send_to_user(user.username, {
                        "type": "heartbeat",
                        "data": {
                            "server_time": datetime.utcnow().isoformat(),
                            "last_activity": last_activity.isoformat(),
                            "connection_healthy": True
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Heartbeat error for {user.username}: {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Too many consecutive errors for {user.username}, closing connection")
                        break
                
            except WebSocketDisconnect as e:
                logger.info(f"Unified WebSocket disconnected: {user.username} (code: {e.code})")
                break
                
            except MessageProcessingError as e:
                consecutive_errors += 1
                logger.warning(f"Message processing error for {user.username}: {e.message}")
                await _send_error_message(websocket_manager, user.username, e.message, e.error_code)
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many message errors for {user.username}, closing connection")
                    break
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Unexpected error in WebSocket loop for {user.username}: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                await _send_error_message(websocket_manager, user.username, 
                                        f"Unexpected error: {str(e)}", "UNEXPECTED_ERROR")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors for {user.username}, closing connection")
                    break
                
                # Brief pause to prevent tight error loops
                await asyncio.sleep(1.0)
    
    except AuthenticationError as e:
        logger.warning(f"Authentication error: {e.message}")
        try:
            await websocket.close(code=e.close_code, reason=e.message)
        except:
            pass
        return
    
    except ConnectionLimitError as e:
        logger.warning(f"Connection limit error: {e.message}")
        try:
            await websocket.close(code=e.close_code, reason=e.message)
        except:
            pass
        return
    
    except Exception as e:
        logger.error(f"Critical WebSocket error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    
    finally:
        # Enhanced cleanup with error handling
        if user and connection_established:
            try:
                await websocket_manager.disconnect_user(user.username)
                logger.info(f"Cleaned up connection for {user.username}")
            except Exception as e:
                logger.error(f"Error during connection cleanup for {user.username}: {e}")


async def _send_error_message(websocket_manager, user_id: str, message: str, error_code: str):
    """Send error message with enhanced error handling"""
    try:
        await websocket_manager.send_to_user(user_id, {
            "type": "error",
            "data": {
                "message": message,
                "error_code": error_code,
                "timestamp": datetime.utcnow().isoformat(),
                "recoverable": error_code in ["MESSAGE_ERROR", "MESSAGE_HANDLER_ERROR"]
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to send error message to {user_id}: {e}")


@router.get("/ws/stats")
async def get_unified_websocket_stats():
    """Get unified WebSocket connection statistics"""
    websocket_manager = get_unified_websocket_manager()
    return websocket_manager.get_connection_stats()


@router.get("/ws/user/{user_id}")
async def get_user_connection_info(user_id: str):
    """Get connection information for specific user"""
    websocket_manager = get_unified_websocket_manager()
    connection_info = websocket_manager.get_user_connection_info(user_id)
    
    if not connection_info:
        raise HTTPException(status_code=404, detail="User connection not found")
    
    return connection_info


@router.post("/ws/disconnect/{user_id}")
async def force_disconnect_user(user_id: str, reason: str = "Admin disconnect"):
    """Force disconnect a user (admin only)"""
    websocket_manager = get_unified_websocket_manager()
    await websocket_manager.disconnect_user(user_id, reason)
    
    return {
        "message": f"User {user_id} disconnected",
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/ws/broadcast")
async def broadcast_event(
    event_type: str,
    data: Dict[str, Any],
    priority: str = "normal",
    source_user_id: Optional[str] = None
):
    """Broadcast event to all connected users"""
    from ...websocket.models import EventType, EventPriority
    
    try:
        event_type_enum = EventType(event_type)
        priority_enum = EventPriority(priority)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid event type or priority: {e}")
    
    websocket_manager = get_unified_websocket_manager()
    event_id = await websocket_manager.emit_event(
        event_type=event_type_enum,
        data=data,
        source_user_id=source_user_id,
        priority=priority_enum
    )
    
    return {
        "message": "Event broadcasted successfully",
        "event_id": event_id,
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ws/health")
async def get_websocket_health():
    """Get WebSocket system health status"""
    websocket_manager = get_unified_websocket_manager()
    stats = websocket_manager.get_connection_stats()
    
    # Calculate health metrics
    total_connections = stats.get("total_connections", 0)
    healthy_connections = 0
    error_connections = 0
    recovering_connections = 0
    
    for user_id, connection_info in stats.get("connection_details", {}).items():
        health_status = connection_info.get("health_status", {})
        if health_status.get("is_healthy", False):
            healthy_connections += 1
        elif health_status.get("status") == "recovering":
            recovering_connections += 1
        elif health_status.get("status") == "error":
            error_connections += 1
    
    health_score = (healthy_connections / max(total_connections, 1)) * 100
    
    return {
        "overall_health": "healthy" if health_score >= 90 else "degraded" if health_score >= 70 else "unhealthy",
        "health_score": health_score,
        "total_connections": total_connections,
        "healthy_connections": healthy_connections,
        "recovering_connections": recovering_connections,
        "error_connections": error_connections,
        "event_queue_size": stats.get("event_queue_size", 0),
        "background_services_running": stats.get("background_services_running", False),
        "uptime_seconds": stats.get("uptime_seconds", 0),
        "total_messages_sent": stats.get("total_messages_sent", 0),
        "total_events_processed": stats.get("total_events_processed", 0)
    }


@router.get("/ws/errors")
async def get_websocket_errors():
    """Get WebSocket error statistics and recent errors"""
    websocket_manager = get_unified_websocket_manager()
    stats = websocket_manager.get_connection_stats()
    
    error_summary = {
        "total_errors": 0,
        "connections_with_errors": 0,
        "high_error_rate_connections": [],
        "recent_errors": []
    }
    
    for user_id, connection_info in stats.get("connection_details", {}).items():
        health_status = connection_info.get("health_status", {})
        error_count = health_status.get("error_count", 0)
        error_rate = health_status.get("error_rate_per_minute", 0)
        
        error_summary["total_errors"] += error_count
        
        if error_count > 0:
            error_summary["connections_with_errors"] += 1
        
        if error_rate > 2:  # More than 2 errors per minute
            error_summary["high_error_rate_connections"].append({
                "user_id": user_id,
                "username": connection_info.get("username"),
                "error_count": error_count,
                "error_rate_per_minute": error_rate,
                "consecutive_errors": health_status.get("consecutive_errors", 0),
                "status": health_status.get("status")
            })
    
    return error_summary


@router.get("/ws/info")
async def get_unified_websocket_info():
    """Get information about the unified WebSocket endpoint"""
    from ...websocket.models import EventType, EventPriority
    
    return {
        "endpoint": "/ws",
        "description": "Unified WebSocket endpoint with single connection per user and comprehensive error recovery",
        "features": [
            "Single connection per user",
            "Dynamic event subscription management",
            "Enhanced authentication and authorization",
            "Connection health monitoring",
            "Automatic error recovery with exponential backoff",
            "Message queuing and batching",
            "Rate limiting and security",
            "Comprehensive error handling and logging",
            "Connection health diagnostics"
        ],
        "supported_event_types": [event.value for event in EventType],
        "event_priorities": [priority.value for priority in EventPriority],
        "supported_messages": {
            "client_to_server": [
                {
                    "type": "ping",
                    "description": "Health check ping",
                    "data": {"expect_pong": True}
                },
                {
                    "type": "pong",
                    "description": "Response to server ping",
                    "data": {"connection_id": "connection_id"}
                },
                {
                    "type": "subscribe_events",
                    "description": "Subscribe to specific event types",
                    "data": {"event_types": ["event_type1", "event_type2"]}
                },
                {
                    "type": "unsubscribe_events",
                    "description": "Unsubscribe from specific event types",
                    "data": {"event_types": ["event_type1", "event_type2"]}
                },
                {
                    "type": "get_connection_status",
                    "description": "Get current connection status",
                    "data": {}
                },
                {
                    "type": "health_check",
                    "description": "Comprehensive health check",
                    "data": {}
                },
                {
                    "type": "get_connection_stats",
                    "description": "Get connection statistics (admin only)",
                    "data": {}
                }
            ],
            "server_to_client": [
                {
                    "type": "connection_established",
                    "description": "Connection established successfully"
                },
                {
                    "type": "subscription_updated",
                    "description": "Event subscription updated"
                },
                {
                    "type": "pong",
                    "description": "Response to client ping"
                },
                {
                    "type": "heartbeat",
                    "description": "Server heartbeat with health info"
                },
                {
                    "type": "connection_status",
                    "description": "Current connection status"
                },
                {
                    "type": "health_check_response",
                    "description": "Health check results"
                },
                {
                    "type": "error",
                    "description": "Error message with recovery info"
                },
                {
                    "type": "validation_error",
                    "description": "Data validation error"
                },
                {
                    "type": "[event_type]",
                    "description": "Real-time events based on subscriptions"
                }
            ]
        },
        "error_recovery": {
            "max_consecutive_errors": 5,
            "error_recovery_delay": "1.0s to 30.0s (exponential backoff)",
            "max_recovery_attempts": 5,
            "ping_timeout": "10.0s",
            "connection_health_checks": "Every 30s"
        },
        "authentication": {
            "method": "Bearer token in query parameter",
            "parameter": "token",
            "example": "/ws?token=your_jwt_token"
        },
        "limits": {
            "max_total_connections": 500,
            "message_queue_size": 100,
            "health_check_interval": 30,
            "message_timeout": 300,
            "max_consecutive_errors": 5
        }
    }