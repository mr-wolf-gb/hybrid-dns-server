"""
Health monitoring endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from ...core.database import get_database_session
from ...core.security import get_current_user
from ...schemas.dns import HealthSummary, ForwarderHealthStatus
from ...services.health_service import get_health_service
from ...services.background_tasks import get_background_task_service

router = APIRouter()

@router.get("/summary", response_model=HealthSummary)
async def get_health_summary(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive health summary for all forwarders"""
    health_service = get_health_service()
    summary = await health_service.get_forwarder_health_summary(db)
    return summary

@router.get("/unhealthy")
async def get_unhealthy_forwarders(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get list of forwarders that are currently unhealthy"""
    health_service = get_health_service()
    unhealthy = await health_service.get_unhealthy_forwarders(db)
    return {"unhealthy_forwarders": unhealthy, "count": len(unhealthy)}

@router.post("/check/all")
async def trigger_health_check_all(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger health checks for all forwarders"""
    health_service = get_health_service()
    
    # Trigger health checks in background
    background_tasks.add_task(health_service.trigger_health_check_for_all, db)
    
    return {"message": "Health check initiated for all forwarders"}

@router.get("/service/status")
async def get_service_status(
    current_user: dict = Depends(get_current_user)
):
    """Get status of health monitoring services"""
    background_service = get_background_task_service()
    health_service = get_health_service()
    
    status = await background_service.get_service_status()
    status["health_service_details"] = {
        "running": health_service.is_running()
    }
    
    return status

@router.post("/service/restart")
async def restart_health_service(
    current_user: dict = Depends(get_current_user)
):
    """Restart the health monitoring service"""
    health_service = get_health_service()
    
    # Stop and restart the service
    await health_service.stop()
    await health_service.start()
    
    return {"message": "Health monitoring service restarted"}

@router.post("/cleanup")
async def cleanup_old_records(
    days_to_keep: int = 30,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Clean up old health check records"""
    if days_to_keep < 1 or days_to_keep > 365:
        raise HTTPException(status_code=400, detail="Days to keep must be between 1 and 365")
    
    health_service = get_health_service()
    deleted_count = await health_service.cleanup_old_health_records(db, days_to_keep)
    
    return {
        "message": f"Cleaned up {deleted_count} old health check records",
        "deleted_count": deleted_count,
        "days_kept": days_to_keep
    }

@router.get("/tracking/metrics")
async def get_health_tracking_metrics(
    hours: int = 24,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive health status tracking metrics"""
    if hours < 1 or hours > 168:  # Max 1 week
        raise HTTPException(status_code=400, detail="Hours must be between 1 and 168")
    
    health_service = get_health_service()
    metrics = await health_service.get_health_status_tracking_metrics(db, hours)
    
    return metrics

@router.get("/tracking/alerts")
async def get_health_tracking_alerts(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get health alerts with enhanced tracking information"""
    health_service = get_health_service()
    alerts = await health_service.get_health_alerts_with_tracking(db)
    
    return alerts

@router.get("/history")
async def get_health_history(
    forwarder_id: Optional[int] = None,
    hours: int = 24,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get health history data for charts"""
    if hours < 1 or hours > 168:  # Max 1 week
        raise HTTPException(status_code=400, detail="Hours must be between 1 and 168")
    
    health_service = get_health_service()
    history = await health_service.get_health_history_data(db, forwarder_id, hours)
    
    return history

@router.get("/performance")
async def get_performance_metrics(
    hours: int = 24,
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive performance metrics"""
    if hours < 1 or hours > 168:  # Max 1 week
        raise HTTPException(status_code=400, detail="Hours must be between 1 and 168")
    
    health_service = get_health_service()
    metrics = await health_service.get_performance_metrics(db, hours)
    
    return metrics

@router.get("/alerts")
async def get_health_alerts(
    db: Session = Depends(get_database_session),
    current_user: dict = Depends(get_current_user)
):
    """Get current health alerts"""
    health_service = get_health_service()
    alerts = await health_service.generate_health_alerts(db)
    
    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "critical_alerts": len([a for a in alerts if a["level"] == "critical"]),
        "warning_alerts": len([a for a in alerts if a["level"] == "warning"]),
        "generated_at": alerts[0]["created_at"] if alerts else None
    }

@router.get("/realtime/status")
async def get_realtime_status(
    current_user: dict = Depends(get_current_user)
):
    """Get real-time WebSocket connection status"""
    from ...websocket.manager import get_websocket_manager
    
    websocket_manager = get_websocket_manager()
    stats = websocket_manager.get_connection_stats()
    
    return {
        "websocket_enabled": True,
        "connection_stats": stats,
        "endpoint": "/ws/health/{user_id}"
    }