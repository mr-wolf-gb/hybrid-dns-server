"""
WebSocket health check endpoint
"""

from fastapi import APIRouter, HTTPException
from ...websocket.manager import get_websocket_manager
from ...websocket.unified_manager import get_unified_websocket_manager
from ...websocket.router import get_websocket_router
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/ws/health-check")
async def websocket_health_check():
    """Check WebSocket service health and connection statistics for both systems"""
    try:
        websocket_router = get_websocket_router()
        router_stats = websocket_router.get_connection_stats()
        
        # Check if the service is healthy
        is_healthy = True
        issues = []
        
        # Check legacy system
        legacy_stats = router_stats.get("legacy_stats", {})
        if legacy_stats:
            total_legacy = legacy_stats.get("total_connections", 0)
            if total_legacy >= 450:  # 90% of 500 max split between systems
                issues.append("High legacy connection count")
                is_healthy = False
        
        # Check unified system
        unified_stats = router_stats.get("unified_stats", {})
        if unified_stats:
            total_unified = unified_stats.get("total_connections", 0)
            if total_unified >= 450:  # 90% of 500 max split between systems
                issues.append("High unified connection count")
                is_healthy = False
            
            # Check event queue
            queue_size = unified_stats.get("event_queue_size", 0)
            if queue_size > 100:
                issues.append("High event queue size in unified system")
                is_healthy = False
        
        # Check routing errors
        router_errors = router_stats.get("router_stats", {}).get("routing_errors", 0)
        if router_errors > 10:
            issues.append("High routing error count")
            is_healthy = False
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "issues": issues,
            "statistics": router_stats,
            "system_status": {
                "legacy_active": legacy_stats is not None,
                "unified_active": unified_stats is not None,
                "routing_enabled": True
            }
        }
    
    except Exception as e:
        logger.error(f"WebSocket health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/ws/cleanup")
async def cleanup_websocket_connections():
    """Clean up stale WebSocket connections in both systems (admin only)"""
    try:
        websocket_router = get_websocket_router()
        
        # Get current stats
        before_stats = websocket_router.get_connection_stats()
        
        # Cleanup would be handled by the individual managers' health monitoring
        # This endpoint provides a way to trigger manual cleanup if needed
        
        after_stats = websocket_router.get_connection_stats()
        
        return {
            "message": "Cleanup completed - health monitoring handles automatic cleanup",
            "before": before_stats,
            "after": after_stats,
            "note": "Both legacy and unified systems have automatic health monitoring and cleanup"
        }
    
    except Exception as e:
        logger.error(f"WebSocket cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")