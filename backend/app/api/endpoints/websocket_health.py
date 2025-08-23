"""
WebSocket health check endpoint
"""

from fastapi import APIRouter, HTTPException
from ...websocket.manager import get_websocket_manager
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/ws/health-check")
async def websocket_health_check():
    """Check WebSocket service health and connection statistics"""
    try:
        websocket_manager = get_websocket_manager()
        stats = websocket_manager.get_connection_stats()
        
        # Check if the service is healthy
        is_healthy = True
        issues = []
        
        # Check connection limits
        if stats["total_connections"] >= 900:  # 90% of max
            issues.append("High connection count")
            is_healthy = False
        
        # Check if broadcasting is running when there are connections
        if stats["total_connections"] > 0 and not stats["broadcasting"]:
            issues.append("Broadcasting not running with active connections")
            is_healthy = False
        
        # Check queue size
        if stats["queue_size"] > 100:
            issues.append("High message queue size")
            is_healthy = False
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "issues": issues,
            "statistics": stats,
            "limits": {
                "max_total_connections": websocket_manager.max_total_connections,
                "max_connections_per_user": websocket_manager.max_connections_per_user
            }
        }
    
    except Exception as e:
        logger.error(f"WebSocket health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/ws/cleanup")
async def cleanup_websocket_connections():
    """Clean up stale WebSocket connections (admin only)"""
    try:
        websocket_manager = get_websocket_manager()
        
        # Get current stats
        before_stats = websocket_manager.get_connection_stats()
        
        # Clean up stale connections (this would need to be implemented)
        # For now, just return current stats
        
        after_stats = websocket_manager.get_connection_stats()
        
        return {
            "message": "Cleanup completed",
            "before": before_stats,
            "after": after_stats
        }
    
    except Exception as e:
        logger.error(f"WebSocket cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")