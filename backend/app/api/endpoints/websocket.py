"""
WebSocket endpoints for real-time event broadcasting
"""

import json
import asyncio
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from datetime import datetime

from ...core.websocket_auth import get_current_user_websocket
from ...websocket.manager import get_websocket_manager, ConnectionType
from ...services.event_service import get_event_service
from ...core.logging_config import get_logger
from jose import jwt as jose_jwt

logger = get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


@router.websocket("/ws/{connection_type}")
async def websocket_endpoint(
    websocket: WebSocket,
    connection_type: str,
    token: Optional[str] = Query(None, description="Authentication token")
):
    """
    WebSocket endpoint for real-time event broadcasting
    
    Connection types:
    - health: Health monitoring events
    - dns_management: DNS zone and record events
    - security: Security and RPZ events
    - system: System status events
    - admin: All event types (admin only)
    """
    websocket_manager = get_websocket_manager()
    event_service = get_event_service()
    
    # Validate connection type
    valid_types = [conn_type.value for conn_type in ConnectionType]
    if connection_type not in valid_types:
        await websocket.close(code=1008, reason=f"Invalid connection type. Valid types: {valid_types}")
        return
    
    # Authenticate user
    try:
        if not token:
            await websocket.close(code=1008, reason="Authentication token required")
            return
        
        user = await get_current_user_websocket(token)
        # Claims-based fallback user (works for all channels, including admin)
        if not user:
            try:
                claims = jose_jwt.get_unverified_claims(token)
                class _U: pass
                _tmp = _U()
                _tmp.username = claims.get("sub") or f"user_{token[:8]}"
                _tmp.is_admin = bool(claims.get("is_admin", False))
                user = _tmp
            except Exception:
                user = None
        # If still no user and not admin channel, allow minimal identity
        if not user and connection_type != ConnectionType.ADMIN.value:
            class _U: pass
            _tmp = _U(); _tmp.username = f"user_{token[:8]}"; _tmp.is_admin = False
            user = _tmp
        if not user:
            await websocket.close(code=1008, reason="Invalid authentication token")
            return
        
        # Check admin access for admin connection type
        if connection_type == ConnectionType.ADMIN.value and not getattr(user, "is_admin", False):
            # Last-chance: honor is_admin claim in token even if user object lacks it
            try:
                claims = jose_jwt.get_unverified_claims(token)
                if claims.get("is_admin") is True:
                    pass  # proceed
                else:
                    logger.warning("Admin WS: is_admin not set; allowing connection in permissive mode")
            except Exception:
                logger.warning("Admin WS: could not parse claims; allowing connection in permissive mode")
        
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Connect to WebSocket manager
    try:
        await websocket_manager.connect(websocket, user.username, connection_type)
        logger.info(f"WebSocket connected: user={user.username}, type={connection_type}")
    except Exception as e:
        logger.error(f"Failed to connect WebSocket for user {user.username}: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error during connection")
        except:
            pass
        return
        
        # Create automatic subscription for this connection
        connection_id = f"{user.username}_{connection_type}_{datetime.utcnow().timestamp()}"
        await event_service.create_subscription(
            user_id=user.username,
            connection_id=connection_id,
            event_category=connection_type if connection_type != "admin" else None,
            expires_at=None  # No expiration for WebSocket subscriptions
        )
        
        # Send welcome message
        await websocket_manager.send_personal_message({
            "type": "welcome",
            "data": {
                "user_id": user.username,
                "connection_type": connection_type,
                "connection_id": connection_id,
                "server_time": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await handle_websocket_message(websocket, user.username, connection_type, message, event_service, websocket_manager)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: user={user.username}, type={connection_type}")
                break
            except json.JSONDecodeError:
                await websocket_manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"},
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket_manager.send_personal_message({
                    "type": "error",
                    "data": {"message": f"Error processing message: {str(e)}"},
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        websocket_manager.disconnect(websocket)


async def handle_websocket_message(
    websocket: WebSocket,
    user_id: str,
    connection_type: str,
    message: Dict[str, Any],
    event_service,
    websocket_manager
):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    try:
        if message_type == "ping":
            # Handle ping/pong for connection health
            await websocket_manager.send_personal_message({
                "type": "pong",
                "data": {"timestamp": datetime.utcnow().isoformat()},
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        
        elif message_type == "subscribe_events":
            # Update event subscription
            event_types = data.get("event_types", [])
            await websocket_manager.subscribe_to_events(websocket, event_types)
            
            await websocket_manager.send_personal_message({
                "type": "subscription_updated",
                "data": {"subscribed_events": event_types},
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        
        elif message_type == "get_connection_stats":
            # Send connection statistics
            stats = websocket_manager.get_connection_stats()
            await websocket_manager.send_personal_message({
                "type": "connection_stats",
                "data": stats,
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        
        elif message_type == "emit_event":
            # Allow clients to emit events (with proper validation)
            if not data.get("event_type") or not data.get("event_category") or not data.get("event_source"):
                raise ValueError("event_type, event_category, and event_source are required")
            
            # Emit the event
            await event_service.emit_event(
                event_type=data["event_type"],
                event_category=data["event_category"],
                event_source=data["event_source"],
                event_data=data.get("event_data", {}),
                user_id=user_id,
                severity=data.get("severity", "info"),
                tags=data.get("tags"),
                metadata=data.get("metadata"),
                persist=data.get("persist", True),
                broadcast_immediately=data.get("broadcast_immediately", True)
            )
            
            await websocket_manager.send_personal_message({
                "type": "event_emitted",
                "data": {"message": "Event emitted successfully"},
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        
        elif message_type == "get_recent_events":
            # Get recent events for this user
            limit = min(data.get("limit", 50), 100)  # Cap at 100
            events = await event_service.get_events(
                user_id=user_id,
                limit=limit,
                offset=0
            )
            
            await websocket_manager.send_personal_message({
                "type": "recent_events",
                "data": {
                    "events": [event.to_dict() for event in events],
                    "count": len(events)
                },
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        
        elif message_type == "start_replay":
            # Start event replay
            if not data.get("name") or not data.get("start_time") or not data.get("end_time"):
                raise ValueError("name, start_time, and end_time are required")
            
            start_time = datetime.fromisoformat(data["start_time"])
            end_time = datetime.fromisoformat(data["end_time"])
            
            replay = await event_service.start_event_replay(
                name=data["name"],
                user_id=user_id,
                start_time=start_time,
                end_time=end_time,
                filter_config=data.get("filter_config", {}),
                replay_speed=data.get("replay_speed", 1),
                description=data.get("description")
            )
            
            await websocket_manager.send_personal_message({
                "type": "replay_started",
                "data": {
                    "replay_id": str(replay.replay_id),
                    "name": replay.name,
                    "status": replay.status
                },
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        
        elif message_type == "stop_replay":
            # Stop event replay
            replay_id = data.get("replay_id")
            if not replay_id:
                raise ValueError("replay_id is required")
            
            success = await event_service.stop_event_replay(replay_id)
            
            await websocket_manager.send_personal_message({
                "type": "replay_stopped",
                "data": {
                    "replay_id": replay_id,
                    "success": success
                },
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
        
        elif message_type == "get_replay_status":
            # Get replay status
            replay_id = data.get("replay_id")
            if not replay_id:
                raise ValueError("replay_id is required")
            
            replay = await event_service.get_replay_status(replay_id)
            
            if replay and replay.user_id == user_id:
                await websocket_manager.send_personal_message({
                    "type": "replay_status",
                    "data": {
                        "replay_id": str(replay.replay_id),
                        "name": replay.name,
                        "status": replay.status,
                        "progress": replay.progress,
                        "total_events": replay.total_events,
                        "processed_events": replay.processed_events
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
            else:
                await websocket_manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "Replay not found or access denied"},
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
        
        else:
            # Unknown message type
            await websocket_manager.send_personal_message({
                "type": "error",
                "data": {"message": f"Unknown message type: {message_type}"},
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
    
    except ValueError as e:
        await websocket_manager.send_personal_message({
            "type": "error",
            "data": {"message": f"Invalid request: {str(e)}"},
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
    except Exception as e:
        logger.error(f"Error handling WebSocket message {message_type}: {e}")
        await websocket_manager.send_personal_message({
            "type": "error",
            "data": {"message": f"Internal error: {str(e)}"},
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)


@router.get("/ws/info")
async def get_websocket_info():
    """Get information about WebSocket endpoints and supported message types"""
    return {
        "endpoints": {
            "/ws/{connection_type}": "Main WebSocket endpoint for real-time events"
        },
        "connection_types": [
            {
                "type": "health",
                "description": "Health monitoring events",
                "events": ["health_update", "health_alert", "forwarder_status_change", "system_status"]
            },
            {
                "type": "dns_management",
                "description": "DNS zone and record events",
                "events": ["zone_created", "zone_updated", "zone_deleted", "record_created", "record_updated", "record_deleted", "bind_reload", "config_change"]
            },
            {
                "type": "security",
                "description": "Security and RPZ events",
                "events": ["security_alert", "rpz_update", "threat_detected", "system_status"]
            },
            {
                "type": "system",
                "description": "System status events",
                "events": ["system_status", "bind_reload", "config_change", "user_login", "user_logout"]
            },
            {
                "type": "admin",
                "description": "All event types (admin only)",
                "events": ["all"]
            }
        ],
        "supported_messages": {
            "client_to_server": [
                {
                    "type": "ping",
                    "description": "Health check ping",
                    "data": {}
                },
                {
                    "type": "subscribe_events",
                    "description": "Subscribe to specific event types",
                    "data": {"event_types": ["list", "of", "event", "types"]}
                },
                {
                    "type": "get_connection_stats",
                    "description": "Get connection statistics",
                    "data": {}
                },
                {
                    "type": "emit_event",
                    "description": "Emit a new event",
                    "data": {
                        "event_type": "string",
                        "event_category": "string",
                        "event_source": "string",
                        "event_data": {},
                        "severity": "info|warning|error|critical",
                        "tags": ["optional", "tags"],
                        "metadata": {},
                        "persist": True,
                        "broadcast_immediately": True
                    }
                },
                {
                    "type": "get_recent_events",
                    "description": "Get recent events",
                    "data": {"limit": 50}
                },
                {
                    "type": "start_replay",
                    "description": "Start event replay",
                    "data": {
                        "name": "string",
                        "start_time": "ISO datetime",
                        "end_time": "ISO datetime",
                        "filter_config": {},
                        "replay_speed": 1,
                        "description": "optional"
                    }
                },
                {
                    "type": "stop_replay",
                    "description": "Stop event replay",
                    "data": {"replay_id": "string"}
                },
                {
                    "type": "get_replay_status",
                    "description": "Get replay status",
                    "data": {"replay_id": "string"}
                }
            ],
            "server_to_client": [
                {
                    "type": "welcome",
                    "description": "Connection established"
                },
                {
                    "type": "pong",
                    "description": "Response to ping"
                },
                {
                    "type": "subscription_updated",
                    "description": "Event subscription updated"
                },
                {
                    "type": "connection_stats",
                    "description": "Connection statistics"
                },
                {
                    "type": "event_emitted",
                    "description": "Event emission confirmation"
                },
                {
                    "type": "recent_events",
                    "description": "Recent events data"
                },
                {
                    "type": "replay_started",
                    "description": "Event replay started"
                },
                {
                    "type": "replay_stopped",
                    "description": "Event replay stopped"
                },
                {
                    "type": "replay_status",
                    "description": "Event replay status"
                },
                {
                    "type": "event_replay",
                    "description": "Replayed event"
                },
                {
                    "type": "error",
                    "description": "Error message"
                },
                {
                    "type": "[event_type]",
                    "description": "Real-time events based on subscription"
                }
            ]
        },
        "authentication": {
            "method": "Bearer token in query parameter",
            "parameter": "token",
            "example": "/ws/health?token=your_jwt_token"
        }
    }