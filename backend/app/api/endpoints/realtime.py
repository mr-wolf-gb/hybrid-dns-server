"""
Real-time API endpoints for live dashboard updates
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_database_session
from sqlalchemy import text
from ...core.logging_config import get_logger
from ...services.monitoring_service import MonitoringService
from ...services.health_service import get_health_service
from ...websocket.manager import get_websocket_manager, EventType

logger = get_logger(__name__)
router = APIRouter()

# Global monitoring service instance
monitoring_service = MonitoringService()


@router.get("/stats/live")
async def get_live_stats():
    """Get real-time statistics for live dashboard updates"""
    try:
        # Get real-time stats from monitoring service
        real_time_stats = await monitoring_service.get_real_time_stats()
        
        # Get recent query statistics
        query_stats = await monitoring_service.get_query_statistics(hours=1)
        
        # Get system metrics
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "queries": {
                "total_today": real_time_stats.get("total_queries", 0),
                "blocked_today": real_time_stats.get("blocked_queries", 0),
                "block_rate": real_time_stats.get("block_rate", 0),
                "last_hour": query_stats.get("total_queries", 0),
                "unique_clients_hour": query_stats.get("unique_clients", 0),
                "unique_domains_hour": query_stats.get("unique_domains", 0)
            },
            "system": {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "disk_usage": disk.percent,
                "uptime_seconds": real_time_stats.get("uptime_seconds", 0)
            },
            "performance": {
                "avg_response_time": query_stats.get("avg_response_time", 0),
                "cache_hit_rate": 85.2  # This would come from BIND stats in production
            }
        }
    except Exception as e:
        logger.error(f"Error getting live stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get live statistics")


@router.get("/queries/recent")
async def get_recent_queries(
    limit: int = Query(10, ge=1, le=100),
    include_blocked: bool = Query(True),
    db: AsyncSession = Depends(get_database_session)
):
    """Get recent DNS queries for live monitoring"""
    try:
        query = """
            SELECT 
                timestamp,
                client_ip,
                query_domain,
                query_type,
                response_code,
                blocked,
                response_time
            FROM dns_logs 
            ORDER BY timestamp DESC 
            LIMIT :limit
        """
        
        result = await db.execute(text(query), {"limit": limit})
        queries = result.fetchall()
        
        return {
            "queries": [
                {
                    "timestamp": query.timestamp.isoformat(),
                    "client_ip": query.client_ip,
                    "domain": query.query_domain,
                    "type": query.query_type,
                    "response_code": query.response_code,
                    "blocked": query.blocked,
                    "response_time": query.response_time
                }
                for query in queries
            ],
            "total": len(queries),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting recent queries: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent queries")


@router.get("/queries/stream")
async def get_query_stream(
    minutes: int = Query(5, ge=1, le=60),
    db: AsyncSession = Depends(get_database_session)
):
    """Get query stream data for real-time charts"""
    try:
        since = datetime.utcnow() - timedelta(minutes=minutes)
        
        # Get queries grouped by minute
        query = """
            SELECT 
                DATE_TRUNC('minute', timestamp) as minute,
                COUNT(*) as total_queries,
                COUNT(*) FILTER (WHERE blocked = true) as blocked_queries,
                COUNT(DISTINCT client_ip) as unique_clients,
                AVG(response_time) as avg_response_time
            FROM dns_logs 
            WHERE timestamp >= :since
            GROUP BY DATE_TRUNC('minute', timestamp)
            ORDER BY minute
        """
        
        result = await db.execute(text(query), {"since": since})
        stream_data = result.fetchall()
        
        return {
            "stream": [
                {
                    "timestamp": row.minute.isoformat(),
                    "total_queries": row.total_queries,
                    "blocked_queries": row.blocked_queries,
                    "allowed_queries": row.total_queries - row.blocked_queries,
                    "unique_clients": row.unique_clients,
                    "avg_response_time": float(row.avg_response_time) if row.avg_response_time else 0
                }
                for row in stream_data
            ],
            "period_minutes": minutes,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting query stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to get query stream")


@router.get("/health/live")
async def get_live_health_status(db: AsyncSession = Depends(get_database_session)):
    """Get real-time health status"""
    try:
        health_service = get_health_service()
        
        # Get forwarder health summary
        health_summary = await health_service.get_forwarder_health_summary(db)
        
        # Get recent health alerts (derived from current health status; no DB table)
        alerts_payload = await health_service.get_health_alerts_with_tracking(db)
        recent_alerts = alerts_payload.get("alerts", [])
        
        return {
            "health_summary": health_summary,
            "recent_alerts": recent_alerts,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting live health status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get live health status")


@router.post("/broadcast/test")
async def test_broadcast(message: str = "Test message"):
    """Test WebSocket broadcasting (development only)"""
    try:
        websocket_manager = get_websocket_manager()
        
        await websocket_manager.emit_event(
            EventType.SYSTEM_STATUS,
            {
                "type": "test_broadcast",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        return {
            "success": True,
            "message": "Test broadcast sent",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error sending test broadcast: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test broadcast")


@router.get("/websocket/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    try:
        websocket_manager = get_websocket_manager()
        stats = websocket_manager.get_connection_stats()
        
        return {
            "connection_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get WebSocket statistics")


@router.get("/security/live")
async def get_live_security_status(
    hours: int = Query(1, ge=1, le=24),
    db: AsyncSession = Depends(get_database_session)
):
    """Get real-time security status and threat detection"""
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get recent security events
        security_query = """
            SELECT 
                dl.timestamp,
                dl.client_ip,
                dl.query_domain,
                rr.rpz_zone as category,
                rr.action,
                COUNT(*) OVER (PARTITION BY dl.query_domain) as frequency
            FROM dns_logs dl
            JOIN rpz_rules rr ON dl.query_domain = rr.domain
            WHERE dl.timestamp >= :since 
            AND dl.blocked = true
            ORDER BY dl.timestamp DESC
            LIMIT 50
        """
        
        result = await db.execute(text(security_query), {"since": since})
        security_events = result.fetchall()
        
        # Get threat statistics
        threat_stats_query = """
            SELECT 
                rr.rpz_zone as category,
                COUNT(*) as threat_count,
                COUNT(DISTINCT dl.client_ip) as affected_clients,
                COUNT(DISTINCT dl.query_domain) as unique_threats
            FROM dns_logs dl
            JOIN rpz_rules rr ON dl.query_domain = rr.domain
            WHERE dl.timestamp >= :since 
            AND dl.blocked = true
            GROUP BY rr.rpz_zone
            ORDER BY threat_count DESC
        """
        
        result = await db.execute(text(threat_stats_query), {"since": since})
        threat_stats = result.fetchall()
        
        return {
            "recent_threats": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "client_ip": event.client_ip,
                    "domain": event.query_domain,
                    "category": event.category,
                    "action": event.action,
                    "frequency": event.frequency
                }
                for event in security_events
            ],
            "threat_categories": [
                {
                    "category": stat.category,
                    "threat_count": stat.threat_count,
                    "affected_clients": stat.affected_clients,
                    "unique_threats": stat.unique_threats
                }
                for stat in threat_stats
            ],
            "period_hours": hours,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting live security status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get live security status")


@router.post("/alerts/acknowledge/{alert_id}")
async def acknowledge_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_database_session)
):
    """Acknowledge a health or security alert"""
    try:
        # No persistent alerts table; treat this as a no-op and broadcast acknowledgment
        websocket_manager = get_websocket_manager()
        await websocket_manager.emit_event(
            EventType.HEALTH_ALERT,
            {
                "type": "alert_acknowledged",
                "alert_id": alert_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        return {
            "success": True,
            "message": "Alert acknowledged",
            "alert_id": alert_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")