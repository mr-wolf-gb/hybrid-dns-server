"""
WebSocket Metrics API Endpoints
Provides REST API endpoints for WebSocket performance monitoring, health checks, and administrative tools
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.security import HTTPBearer

from ...core.auth_context import get_current_user, require_admin
from ...models.auth import User
from ...websocket.metrics import get_websocket_metrics
from ...websocket.health_monitor import get_websocket_health_monitor, DebugLevel, TraceEventType
from ...websocket.admin_tools import get_websocket_admin_tools
from ...core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


@router.get("/metrics/summary")
async def get_metrics_summary(current_user: User = Depends(get_current_user)):
    """Get WebSocket metrics summary"""
    try:
        metrics = get_websocket_metrics()
        summary = metrics.get_summary_stats()
        
        return {
            "success": True,
            "data": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics summary")


@router.get("/metrics/connections")
async def get_connection_metrics(
    current_user: User = Depends(get_current_user),
    user_id: Optional[str] = Query(None, description="Filter by specific user ID")
):
    """Get detailed connection metrics"""
    try:
        admin_tools = get_websocket_admin_tools()
        connections = await admin_tools.get_connection_details(user_id)
        
        return {
            "success": True,
            "data": {
                "connections": connections,
                "total_connections": len(connections)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting connection metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get connection metrics")


@router.get("/metrics/events")
async def get_event_metrics(
    current_user: User = Depends(get_current_user),
    event_type: Optional[str] = Query(None, description="Filter by specific event type")
):
    """Get event processing metrics"""
    try:
        admin_tools = get_websocket_admin_tools()
        events = await admin_tools.get_event_statistics(event_type)
        
        return {
            "success": True,
            "data": events,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting event metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get event metrics")


@router.get("/metrics/performance")
async def get_performance_metrics(
    current_user: User = Depends(get_current_user),
    metric_name: str = Query(..., description="Performance metric name"),
    limit: int = Query(60, description="Number of data points to return")
):
    """Get performance metrics history"""
    try:
        metrics = get_websocket_metrics()
        performance_data = metrics.get_performance_metrics(metric_name, limit)
        
        return {
            "success": True,
            "data": {
                "metric_name": metric_name,
                "data_points": performance_data,
                "count": len(performance_data)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")


@router.get("/metrics/system")
async def get_system_metrics(
    current_user: User = Depends(get_current_user),
    limit: int = Query(60, description="Number of data points to return")
):
    """Get system resource metrics history"""
    try:
        metrics = get_websocket_metrics()
        system_data = metrics.get_system_metrics_history(limit)
        
        return {
            "success": True,
            "data": {
                "metrics": system_data,
                "count": len(system_data)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system metrics")


@router.get("/health/status")
async def get_health_status(current_user: User = Depends(get_current_user)):
    """Get overall WebSocket system health status"""
    try:
        health_monitor = get_websocket_health_monitor()
        health_status = health_monitor.get_health_status()
        
        return {
            "success": True,
            "data": health_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health status")


@router.get("/health/report")
async def get_health_report(current_user: User = Depends(get_current_user)):
    """Get comprehensive health report"""
    try:
        admin_tools = get_websocket_admin_tools()
        health_report = await admin_tools.get_health_report()
        
        return {
            "success": True,
            "data": health_report,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting health report: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health report")


@router.get("/health/check/{check_name}")
async def get_health_check_details(
    check_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific health check"""
    try:
        health_monitor = get_websocket_health_monitor()
        check_details = health_monitor.get_health_check_details(check_name)
        
        if not check_details:
            raise HTTPException(status_code=404, detail=f"Health check '{check_name}' not found")
        
        return {
            "success": True,
            "data": check_details,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting health check details: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health check details")


@router.get("/alerts")
async def get_alerts(current_user: User = Depends(get_current_user)):
    """Get current alert status"""
    try:
        metrics = get_websocket_metrics()
        alert_status = metrics.get_alert_status()
        
        return {
            "success": True,
            "data": alert_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")


# Admin-only endpoints
@router.get("/admin/overview")
async def get_admin_overview(current_user: User = Depends(require_admin)):
    """Get comprehensive system overview (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        overview = await admin_tools.get_system_overview()
        
        return {
            "success": True,
            "data": overview,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting admin overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin overview")


@router.get("/admin/performance-analysis")
async def get_performance_analysis(
    current_user: User = Depends(require_admin),
    hours: int = Query(1, description="Analysis period in hours")
):
    """Get detailed performance analysis (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        analysis = await admin_tools.get_performance_analysis(hours)
        
        return {
            "success": True,
            "data": analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting performance analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance analysis")


@router.post("/admin/debug/enable")
async def enable_debug_mode(
    current_user: User = Depends(require_admin),
    config: Dict[str, Any] = Body(...)
):
    """Enable debug mode (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        
        level = DebugLevel(config.get("level", "basic"))
        user_ids = config.get("user_ids")
        
        admin_tools.enable_debug_mode(level, user_ids)
        
        return {
            "success": True,
            "message": f"Debug mode enabled with level: {level.value}",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error enabling debug mode: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable debug mode")


@router.post("/admin/debug/disable")
async def disable_debug_mode(current_user: User = Depends(require_admin)):
    """Disable debug mode (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        admin_tools.disable_debug_mode()
        
        return {
            "success": True,
            "message": "Debug mode disabled",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error disabling debug mode: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable debug mode")


@router.post("/admin/tracing/enable")
async def enable_event_tracing(
    current_user: User = Depends(require_admin),
    config: Dict[str, Any] = Body(...)
):
    """Enable event tracing (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        
        event_types = None
        if "event_types" in config:
            event_types = [TraceEventType(et) for et in config["event_types"]]
        
        user_ids = config.get("user_ids")
        
        admin_tools.event_tracer.enable_tracing(event_types, user_ids)
        
        return {
            "success": True,
            "message": "Event tracing enabled",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error enabling event tracing: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable event tracing")


@router.post("/admin/tracing/disable")
async def disable_event_tracing(current_user: User = Depends(require_admin)):
    """Disable event tracing (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        admin_tools.event_tracer.disable_tracing()
        
        return {
            "success": True,
            "message": "Event tracing disabled",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error disabling event tracing: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable event tracing")


@router.get("/admin/tracing/events")
async def get_trace_events(
    current_user: User = Depends(require_admin),
    limit: Optional[int] = Query(100, description="Maximum number of events to return"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    since_hours: Optional[int] = Query(None, description="Get events from last N hours")
):
    """Get trace events (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        
        since = None
        if since_hours:
            since = datetime.utcnow() - timedelta(hours=since_hours)
        
        trace_event_type = None
        if event_type:
            trace_event_type = TraceEventType(event_type)
        
        events = admin_tools.event_tracer.get_events(
            limit=limit,
            event_type=trace_event_type,
            user_id=user_id,
            since=since
        )
        
        return {
            "success": True,
            "data": {
                "events": events,
                "count": len(events),
                "tracing_enabled": admin_tools.event_tracer.enabled
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting trace events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trace events")


@router.post("/admin/profiling/enable")
async def enable_profiling(current_user: User = Depends(require_admin)):
    """Enable performance profiling (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        admin_tools.enable_profiling()
        
        return {
            "success": True,
            "message": "Performance profiling enabled",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error enabling profiling: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable profiling")


@router.post("/admin/profiling/disable")
async def disable_profiling(current_user: User = Depends(require_admin)):
    """Disable performance profiling (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        admin_tools.disable_profiling()
        
        return {
            "success": True,
            "message": "Performance profiling disabled",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error disabling profiling: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable profiling")


@router.post("/admin/connections/{user_id}/disconnect")
async def force_disconnect_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    reason: str = Body("Admin disconnect", embed=True)
):
    """Force disconnect a specific user (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        success = await admin_tools.force_disconnect_user(user_id, reason)
        
        if success:
            return {
                "success": True,
                "message": f"User {user_id} disconnected",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found or not connected")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error force disconnecting user: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect user")


@router.post("/admin/broadcast")
async def broadcast_admin_message(
    current_user: User = Depends(require_admin),
    message_data: Dict[str, Any] = Body(...)
):
    """Broadcast administrative message to all users (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        
        message = message_data.get("message", "")
        severity = message_data.get("severity", "info")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        count = await admin_tools.broadcast_admin_message(message, severity)
        
        return {
            "success": True,
            "message": f"Message broadcast to {count} connections",
            "recipients": count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error broadcasting admin message: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast message")


@router.delete("/admin/metrics")
async def clear_all_metrics(current_user: User = Depends(require_admin)):
    """Clear all collected metrics (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        success = await admin_tools.clear_all_metrics()
        
        if success:
            return {
                "success": True,
                "message": "All metrics cleared",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to clear metrics")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear metrics")


@router.get("/admin/export")
async def export_debug_data(
    current_user: User = Depends(require_admin),
    include_traces: bool = Query(True, description="Include trace events"),
    include_metrics: bool = Query(True, description="Include metrics data"),
    include_performance: bool = Query(True, description="Include performance data")
):
    """Export comprehensive debug data (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        debug_data = await admin_tools.export_debug_data(
            include_traces=include_traces,
            include_metrics=include_metrics,
            include_performance=include_performance
        )
        
        return {
            "success": True,
            "data": debug_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error exporting debug data: {e}")
        raise HTTPException(status_code=500, detail="Failed to export debug data")


@router.get("/admin/commands")
async def get_debug_commands(current_user: User = Depends(require_admin)):
    """Get list of available debug commands (admin only)"""
    try:
        admin_tools = get_websocket_admin_tools()
        commands = admin_tools.get_debug_commands()
        
        return {
            "success": True,
            "data": {
                "commands": commands,
                "count": len(commands)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting debug commands: {e}")
        raise HTTPException(status_code=500, detail="Failed to get debug commands")


# Health check endpoint for monitoring systems
@router.get("/health")
async def websocket_health_check():
    """Simple health check endpoint for monitoring systems"""
    try:
        metrics = get_websocket_metrics()
        health_monitor = get_websocket_health_monitor()
        
        # Get basic health status
        health_status = health_monitor.get_health_status()
        summary_stats = metrics.get_summary_stats()
        
        # Determine if system is healthy
        is_healthy = (
            health_status["overall_status"] in ["healthy", "warning"] and
            health_status["active_alerts"] < 5 and
            summary_stats["error_rate"] < 0.1
        )
        
        status_code = 200 if is_healthy else 503
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "active_connections": summary_stats["active_connections"],
            "error_rate": summary_stats["error_rate"],
            "active_alerts": health_status["active_alerts"],
            "uptime_seconds": summary_stats["uptime_seconds"],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "status": "unhealthy",
            "error": "Health check failed",
            "timestamp": datetime.utcnow().isoformat()
        }