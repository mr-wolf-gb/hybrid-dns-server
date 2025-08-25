"""
WebSocket endpoints with feature flag support for legacy/unified system routing
"""

import json
import asyncio
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime

from ...core.websocket_auth import get_current_user_websocket
from ...websocket.manager import get_websocket_manager, ConnectionType
from ...websocket.router import get_websocket_router
from ...core.logging_config import get_logger
from jose import jwt as jose_jwt

logger = get_logger(__name__)
router = APIRouter()


@router.websocket("/ws/{connection_type}")
async def websocket_endpoint_legacy(
    websocket: WebSocket,
    connection_type: str,
    token: Optional[str] = Query(None, description="Authentication token")
):
    """
    Legacy WebSocket endpoint for backward compatibility
    
    This endpoint maintains the old multi-connection behavior for users
    who haven't been migrated to the unified system yet.
    
    Connection types:
    - health: Health monitoring events
    - dns_management: DNS zone and record events
    - security: Security and RPZ events
    - system: System status events
    - admin: All event types (admin only)
    """
    # Use the router to determine which system to use
    websocket_router = get_websocket_router()
    
    # Validate connection type
    valid_types = [conn_type.value for conn_type in ConnectionType]
    if connection_type not in valid_types:
        await websocket.close(code=1008, reason=f"Invalid connection type")
        return
    
    if not token:
        await websocket.close(code=1008, reason="Authentication token required")
        return
    
    # Route to appropriate WebSocket system
    connection_success = await websocket_router.route_websocket_connection(
        websocket, token, connection_type
    )
    
    if not connection_success:
        return
    
    try:
        # Handle incoming messages
        while True:
            try:
                # Receive message from client with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300.0)
                message = json.loads(data)
                
                # Handle the message (this will be routed to the appropriate system)
                await handle_websocket_message_routed(websocket, message, websocket_router)
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_text(json.dumps({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected")
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"},
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": f"Message error: {str(e)}"},
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # Disconnect from router (handles both systems)
        websocket_router.disconnect_user(websocket, "unknown")


@router.websocket("/ws")
async def websocket_endpoint_unified(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Authentication token")
):
    """
    Unified WebSocket endpoint - single connection per user
    
    This is the new unified endpoint that handles all event types
    through a single connection with dynamic subscription management.
    """
    # Use the router to determine which system to use
    websocket_router = get_websocket_router()
    
    if not token:
        await websocket.close(code=1008, reason="Authentication token required")
        return
    
    # Route to appropriate WebSocket system (will prefer unified for this endpoint)
    connection_success = await websocket_router.route_websocket_connection(
        websocket, token, "unified"
    )
    
    if not connection_success:
        return
    
    try:
        # Handle incoming messages
        while True:
            try:
                # Receive message from client with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300.0)
                message = json.loads(data)
                
                # Handle the message
                await handle_websocket_message_routed(websocket, message, websocket_router)
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_text(json.dumps({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except WebSocketDisconnect:
                logger.info(f"Unified WebSocket disconnected")
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"},
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except Exception as e:
                logger.error(f"Error handling unified WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": f"Message error: {str(e)}"},
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
    except Exception as e:
        logger.error(f"Unified WebSocket connection error: {e}")
    finally:
        # Disconnect from router
        websocket_router.disconnect_user(websocket, "unknown")


async def handle_websocket_message_routed(
    websocket: WebSocket,
    message: Dict[str, Any],
    websocket_router
):
    """Handle incoming WebSocket messages through the router"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    try:
        if message_type == "ping":
            await websocket.send_text(json.dumps({
                "type": "pong",
                "data": {"timestamp": datetime.utcnow().isoformat()},
                "timestamp": datetime.utcnow().isoformat()
            }))
        
        elif message_type == "get_system_info":
            # Return information about which WebSocket system is being used
            stats = websocket_router.get_connection_stats()
            await websocket.send_text(json.dumps({
                "type": "system_info",
                "data": {
                    "router_stats": stats.get("router_stats", {}),
                    "feature_flags": stats.get("feature_flags", {}),
                    "timestamp": datetime.utcnow().isoformat()
                },
                "timestamp": datetime.utcnow().isoformat()
            }))
        
        elif message_type == "subscribe_events":
            # For unified system, this will be handled by the unified manager
            # For legacy system, this will update the legacy manager metadata
            event_types = data.get("event_types", [])
            
            # Send confirmation (the actual subscription logic is handled by the respective managers)
            await websocket.send_text(json.dumps({
                "type": "subscription_updated",
                "data": {"subscribed_events": event_types},
                "timestamp": datetime.utcnow().isoformat()
            }))
        
        else:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {"message": f"Unknown message type: {message_type}"},
                "timestamp": datetime.utcnow().isoformat()
            }))
    
    except Exception as e:
        logger.error(f"Error handling routed WebSocket message {message_type}: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {"message": f"Internal error: {str(e)}"},
            "timestamp": datetime.utcnow().isoformat()
        }))


async def handle_websocket_message(
    websocket: WebSocket,
    user_id: str,
    message: Dict[str, Any],
    websocket_manager
):
    """Handle incoming WebSocket messages (legacy function for backward compatibility)"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    try:
        if message_type == "ping":
            await send_message_safe(websocket, {
                "type": "pong",
                "data": {"timestamp": datetime.utcnow().isoformat()},
                "timestamp": datetime.utcnow().isoformat()
            }, websocket_manager)
        
        elif message_type == "subscribe_events":
            event_types = data.get("event_types", [])
            
            # Update subscriptions in metadata
            if websocket in websocket_manager.metadata:
                websocket_manager.metadata[websocket]["subscribed_events"] = event_types
                
                await send_message_safe(websocket, {
                    "type": "subscription_updated",
                    "data": {"subscribed_events": event_types},
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket_manager)
        
        elif message_type == "get_connection_stats":
            stats = websocket_manager.get_connection_stats()
            await send_message_safe(websocket, {
                "type": "connection_stats",
                "data": stats,
                "timestamp": datetime.utcnow().isoformat()
            }, websocket_manager)
        
        elif message_type == "get_user_connections":
            user_connections = {}
            if user_id in websocket_manager.connections:
                for ws in websocket_manager.connections[user_id]:
                    if ws in websocket_manager.metadata:
                        metadata = websocket_manager.metadata[ws]
                        conn_type = metadata.get("connection_type", "unknown")
                        user_connections[f"{conn_type}_{id(ws)}"] = {
                            "connection_type": conn_type,
                            "connected_at": metadata.get("connected_at", datetime.utcnow()).isoformat(),
                            "message_count": metadata.get("message_count", 0),
                            "subscribed_events": metadata.get("subscribed_events", [])
                        }
            
            await send_message_safe(websocket, {
                "type": "user_connections",
                "data": {"connections": user_connections},
                "timestamp": datetime.utcnow().isoformat()
            }, websocket_manager)
        
        else:
            await send_error_safe(websocket, f"Unknown message type: {message_type}", websocket_manager)
    
    except Exception as e:
        logger.error(f"Error handling WebSocket message {message_type}: {e}")
        await send_error_safe(websocket, f"Internal error: {str(e)}", websocket_manager)


async def send_message_safe(websocket: WebSocket, message: Dict[str, Any], websocket_manager):
    """Send a message safely to a WebSocket connection"""
    try:
        await websocket.send_text(json.dumps(message, default=lambda obj: obj.isoformat() if isinstance(obj, datetime) else str(obj)))
        if websocket in websocket_manager.metadata:
            websocket_manager.metadata[websocket]["message_count"] += 1
    except Exception as e:
        logger.debug(f"Failed to send message: {e}")
        websocket_manager.disconnect(websocket)


async def send_error_safe(websocket: WebSocket, error_message: str, websocket_manager):
    """Send an error message safely to a WebSocket connection"""
    await send_message_safe(websocket, {
        "type": "error",
        "data": {"message": error_message},
        "timestamp": datetime.utcnow().isoformat()
    }, websocket_manager)


@router.get("/ws/stats")
async def get_websocket_stats():
    """Get current WebSocket connection statistics from both systems"""
    websocket_router = get_websocket_router()
    return websocket_router.get_connection_stats()


@router.post("/ws/cleanup/{user_id}")
async def force_cleanup_user_connections(user_id: str):
    """Force cleanup all connections for a user"""
    websocket_manager = get_websocket_manager()
    cleaned_count = await websocket_manager.disconnect_user(user_id, "Admin cleanup")
    return {
        "message": f"Cleaned up {cleaned_count} connections for user {user_id}",
        "cleaned_count": cleaned_count
    }


@router.post("/ws/broadcast")
async def broadcast_message(message: Dict[str, Any], connection_type: Optional[str] = None):
    """Broadcast a message to all connected clients"""
    websocket_manager = get_websocket_manager()
    await websocket_manager.broadcast(message, connection_type)
    return {"message": "Message broadcasted successfully"}


@router.get("/ws/info")
async def get_websocket_info():
    """Get information about WebSocket endpoints"""
    return {
        "endpoints": {
            "/ws/{connection_type}": "Main WebSocket endpoint for real-time events"
        },
        "connection_types": [
            {
                "type": "health",
                "description": "Health monitoring events"
            },
            {
                "type": "dns_management", 
                "description": "DNS zone and record events"
            },
            {
                "type": "security",
                "description": "Security and RPZ events"
            },
            {
                "type": "system",
                "description": "System status events"
            },
            {
                "type": "admin",
                "description": "All event types (admin only)"
            }
        ],
        "supported_messages": {
            "client_to_server": [
                {"type": "ping", "description": "Health check ping"},
                {"type": "subscribe_events", "description": "Subscribe to specific event types"},
                {"type": "get_connection_stats", "description": "Get connection statistics"},
                {"type": "get_user_connections", "description": "Get current user's connections"}
            ],
            "server_to_client": [
                {"type": "connection_established", "description": "Connection established"},
                {"type": "pong", "description": "Response to ping"},
                {"type": "subscription_updated", "description": "Event subscription updated"},
                {"type": "connection_stats", "description": "Connection statistics"},
                {"type": "user_connections", "description": "User's connection information"},
                {"type": "error", "description": "Error message"},
                {"type": "[event_type]", "description": "Real-time events"}
            ]
        },
        "authentication": {
            "method": "Bearer token in query parameter",
            "parameter": "token",
            "example": "/ws/health?token=your_jwt_token"
        },
        "limits": {
            "max_connections_per_user": 10,
            "max_total_connections": 500,
            "message_timeout": 300
        }
    }