"""
WebSocket manager for real-time health monitoring updates
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging_config import get_logger
from ..services.health_service import get_health_service

logger = get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time health updates"""
    
    def __init__(self):
        # Store active connections by user ID
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Store connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        # Background task for broadcasting updates
        self._broadcast_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def connect(self, websocket: WebSocket, user_id: str, connection_type: str = "health"):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connection_type": connection_type,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        logger.info(f"WebSocket connected for user {user_id}, type: {connection_type}")
        
        # Start broadcasting if this is the first connection
        if not self._running:
            await self.start_broadcasting()
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.connection_metadata:
            user_id = self.connection_metadata[websocket]["user_id"]
            
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info(f"WebSocket disconnected for user {user_id}")
            
            # Stop broadcasting if no connections remain
            if not self.active_connections and self._running:
                asyncio.create_task(self.stop_broadcasting())
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """Send a message to all connections for a specific user"""
        if user_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[user_id].copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.append(websocket)
            
            # Clean up disconnected websockets
            for websocket in disconnected:
                self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any], connection_type: Optional[str] = None):
        """Broadcast a message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = []
        for user_id, websockets in self.active_connections.items():
            for websocket in websockets.copy():
                # Filter by connection type if specified
                if connection_type:
                    metadata = self.connection_metadata.get(websocket, {})
                    if metadata.get("connection_type") != connection_type:
                        continue
                
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def start_broadcasting(self):
        """Start the background task for broadcasting health updates"""
        if self._running:
            return
        
        self._running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_health_updates())
        logger.info("Started WebSocket health broadcasting")
    
    async def stop_broadcasting(self):
        """Stop the background broadcasting task"""
        if not self._running:
            return
        
        self._running = False
        
        if self._broadcast_task and not self._broadcast_task.done():
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped WebSocket health broadcasting")
    
    async def _broadcast_health_updates(self):
        """Background task to broadcast health updates periodically"""
        health_service = get_health_service()
        
        while self._running:
            try:
                if not self.active_connections:
                    await asyncio.sleep(5)
                    continue
                
                # Get health summary from service
                from ..core.database import get_database_session
                async for db in get_database_session():
                    try:
                        health_summary = await health_service.get_forwarder_health_summary(db)
                        
                        # Broadcast health update
                        await self.broadcast({
                            "type": "health_update",
                            "data": health_summary,
                            "timestamp": datetime.utcnow().isoformat()
                        }, connection_type="health")
                        
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
    
    async def broadcast_health_alert(self, alert_data: Dict[str, Any]):
        """Broadcast a health alert immediately"""
        await self.broadcast({
            "type": "health_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_type="health")
    
    async def broadcast_forwarder_status_change(self, forwarder_id: int, old_status: str, new_status: str):
        """Broadcast when a forwarder's health status changes"""
        await self.broadcast({
            "type": "forwarder_status_change",
            "data": {
                "forwarder_id": forwarder_id,
                "old_status": old_status,
                "new_status": new_status
            },
            "timestamp": datetime.utcnow().isoformat()
        }, connection_type="health")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections"""
        total_connections = sum(len(websockets) for websockets in self.active_connections.values())
        
        return {
            "total_users": len(self.active_connections),
            "total_connections": total_connections,
            "broadcasting": self._running,
            "connection_types": {}
        }


# Global WebSocket manager instance
_websocket_manager = None

def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager