"""
Enhanced analytics API endpoints for DNS monitoring
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_database_session
from ...core.dependencies import get_current_user
from ...schemas.auth import UserInfo
from ...services.monitoring_service import MonitoringService
from ...core.logging_config import get_logger

router = APIRouter(tags=["analytics"])
logger = get_logger(__name__)

# Global monitoring service instance
monitoring_service = None

def get_monitoring_service() -> MonitoringService:
    """Get monitoring service instance"""
    global monitoring_service
    if monitoring_service is None:
        monitoring_service = MonitoringService()
    return monitoring_service


@router.get("/performance")
async def get_performance_metrics(
    hours: int = Query(1, ge=1, le=168, description="Hours to analyze (1-168)"),
    current_user: UserInfo = Depends(get_current_user)
):
    """Get comprehensive performance metrics"""
    try:
        service = get_monitoring_service()
        metrics = await service.get_performance_metrics(hours=hours)
        
        return {
            "success": True,
            "data": {
                "queries_per_second": metrics.queries_per_second,
                "avg_response_time": metrics.avg_response_time,
                "cache_hit_rate": metrics.cache_hit_rate,
                "error_rate": metrics.error_rate,
                "blocked_rate": metrics.blocked_rate,
                "time_range_hours": hours,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")


@router.get("/query-analytics")
async def get_query_analytics(
    hours: int = Query(24, ge=1, le=720, description="Hours to analyze (1-720)"),
    use_cache: bool = Query(True, description="Use cached results if available"),
    current_user: UserInfo = Depends(get_current_user)
):
    """Get comprehensive query analytics"""
    try:
        service = get_monitoring_service()
        analytics = await service.get_query_analytics(hours=hours, use_cache=use_cache)
        
        return {
            "success": True,
            "data": analytics
        }
        
    except Exception as e:
        logger.error(f"Error getting query analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get query analytics")


@router.get("/real-time")
async def get_real_time_analytics(
    current_user: UserInfo = Depends(get_current_user)
):
    """Get real-time analytics and metrics"""
    try:
        service = get_monitoring_service()
        stats = await service.get_real_time_stats()
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting real-time analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get real-time analytics")


@router.get("/trends")
async def get_trend_analysis(
    days: int = Query(30, ge=1, le=365, description="Days to analyze (1-365)"),
    current_user: UserInfo = Depends(get_current_user)
):
    """Get comprehensive trend analysis"""
    try:
        service = get_monitoring_service()
        trends = await service.get_trend_analysis(days=days)
        
        return {
            "success": True,
            "data": trends
        }
        
    except Exception as e:
        logger.error(f"Error getting trend analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trend analysis")


@router.get("/anomalies")
async def get_anomaly_detection(
    current_user: UserInfo = Depends(get_current_user)
):
    """Get current anomaly detection results"""
    try:
        service = get_monitoring_service()
        anomalies = await service.get_anomaly_detection()
        
        return {
            "success": True,
            "data": anomalies
        }
        
    except Exception as e:
        logger.error(f"Error getting anomaly detection: {e}")
        raise HTTPException(status_code=500, detail="Failed to get anomaly detection")


@router.get("/top-domains")
async def get_top_domains_analytics(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    limit: int = Query(50, ge=1, le=500, description="Number of domains to return"),
    include_blocked: bool = Query(True, description="Include blocked domains"),
    current_user: UserInfo = Depends(get_current_user)
):
    """Get top domains with detailed analytics"""
    try:
        service = get_monitoring_service()
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get top domains with analytics
        from ...core.database import database
        
        query = """
            SELECT 
                query_domain,
                COUNT(*) as query_count,
                COUNT(DISTINCT client_ip) as unique_clients,
                COUNT(*) FILTER (WHERE blocked = true) as blocked_count,
                AVG(response_time) as avg_response_time,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen,
                COUNT(DISTINCT query_type) as query_types_count
            FROM dns_logs 
            WHERE timestamp >= :since
        """
        
        params = {"since": since, "limit": limit}
        
        if not include_blocked:
            query += " AND blocked = false"
        
        query += """
            GROUP BY query_domain
            ORDER BY query_count DESC
            LIMIT :limit
        """
        
        domains = await database.fetch_all(query, params)
        
        return {
            "success": True,
            "data": {
                "domains": [dict(domain) for domain in domains],
                "time_range_hours": hours,
                "total_domains": len(domains),
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting top domains analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get top domains analytics")


@router.get("/client-analytics")
async def get_client_analytics(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    limit: int = Query(50, ge=1, le=200, description="Number of clients to return"),
    current_user: UserInfo = Depends(get_current_user)
):
    """Get detailed client analytics"""
    try:
        service = get_monitoring_service()
        since = datetime.utcnow() - timedelta(hours=hours)
        
        from ...core.database import database
        
        # Get client analytics
        clients = await database.fetch_all("""
            SELECT 
                client_ip,
                COUNT(*) as query_count,
                COUNT(DISTINCT query_domain) as unique_domains,
                COUNT(*) FILTER (WHERE blocked = true) as blocked_count,
                AVG(response_time) as avg_response_time,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen,
                COUNT(DISTINCT query_type) as query_types_used,
                ROUND((COUNT(*) FILTER (WHERE blocked = true)::float / COUNT(*)) * 100, 2) as block_rate_percent
            FROM dns_logs 
            WHERE timestamp >= :since
            GROUP BY client_ip
            ORDER BY query_count DESC
            LIMIT :limit
        """, {"since": since, "limit": limit})
        
        # Get client activity patterns
        activity_patterns = await database.fetch_all("""
            SELECT 
                EXTRACT(hour FROM timestamp) as hour,
                COUNT(DISTINCT client_ip) as active_clients,
                COUNT(*) as total_queries,
                AVG(response_time) as avg_response_time
            FROM dns_logs 
            WHERE timestamp >= :since
            GROUP BY EXTRACT(hour FROM timestamp)
            ORDER BY hour
        """, {"since": since})
        
        return {
            "success": True,
            "data": {
                "top_clients": [dict(client) for client in clients],
                "activity_patterns": [dict(pattern) for pattern in activity_patterns],
                "time_range_hours": hours,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting client analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get client analytics")


@router.get("/response-time-analytics")
async def get_response_time_analytics(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    current_user: UserInfo = Depends(get_current_user)
):
    """Get detailed response time analytics"""
    try:
        service = get_monitoring_service()
        since = datetime.utcnow() - timedelta(hours=hours)
        
        from ...core.database import database
        
        # Get response time statistics
        stats = await database.fetch_one("""
            SELECT 
                COUNT(*) as total_queries,
                AVG(response_time) as avg_response_time,
                MIN(response_time) as min_response_time,
                MAX(response_time) as max_response_time,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time) as median_response_time,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time) as p95_response_time,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time) as p99_response_time,
                COUNT(*) FILTER (WHERE response_time > 100) as slow_queries_count,
                COUNT(*) FILTER (WHERE response_time > 1000) as very_slow_queries_count
            FROM dns_logs 
            WHERE timestamp >= :since AND response_time > 0
        """, {"since": since})
        
        # Get response time by query type
        by_query_type = await database.fetch_all("""
            SELECT 
                query_type,
                COUNT(*) as query_count,
                AVG(response_time) as avg_response_time,
                MIN(response_time) as min_response_time,
                MAX(response_time) as max_response_time,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time) as p95_response_time
            FROM dns_logs 
            WHERE timestamp >= :since AND response_time > 0
            GROUP BY query_type
            ORDER BY avg_response_time DESC
        """, {"since": since})
        
        # Get hourly response time trends
        hourly_trends = await database.fetch_all("""
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                AVG(response_time) as avg_response_time,
                COUNT(*) as query_count,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time) as p95_response_time
            FROM dns_logs 
            WHERE timestamp >= :since AND response_time > 0
            GROUP BY DATE_TRUNC('hour', timestamp)
            ORDER BY hour
        """, {"since": since})
        
        return {
            "success": True,
            "data": {
                "overall_stats": dict(stats) if stats else {},
                "by_query_type": [dict(row) for row in by_query_type],
                "hourly_trends": [dict(row) for row in hourly_trends],
                "time_range_hours": hours,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting response time analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get response time analytics")


@router.get("/threat-analytics")
async def get_threat_analytics(
    days: int = Query(7, ge=1, le=90, description="Days to analyze"),
    category: Optional[str] = Query(None, description="Filter by threat category"),
    current_user: UserInfo = Depends(get_current_user)
):
    """Get comprehensive threat analytics"""
    try:
        service = get_monitoring_service()
        since = datetime.utcnow() - timedelta(days=days)
        
        from ...core.database import database
        
        # Base query for threat analytics
        base_query = """
            FROM dns_logs dl
            JOIN rpz_rules rr ON dl.query_domain = rr.domain
            WHERE dl.timestamp >= :since AND dl.blocked = true
        """
        
        params = {"since": since}
        
        if category:
            base_query += " AND rr.rpz_zone = :category"
            params["category"] = category
        
        # Get threat statistics
        threat_stats = await database.fetch_one(f"""
            SELECT 
                COUNT(*) as total_threats,
                COUNT(DISTINCT dl.query_domain) as unique_threat_domains,
                COUNT(DISTINCT dl.client_ip) as affected_clients,
                COUNT(DISTINCT rr.rpz_zone) as categories_triggered
            {base_query}
        """, params)
        
        # Get threats by category
        by_category = await database.fetch_all(f"""
            SELECT 
                rr.rpz_zone as category,
                COUNT(*) as threat_count,
                COUNT(DISTINCT dl.query_domain) as unique_domains,
                COUNT(DISTINCT dl.client_ip) as affected_clients,
                rr.action as primary_action
            {base_query}
            GROUP BY rr.rpz_zone, rr.action
            ORDER BY threat_count DESC
        """, params)
        
        # Get daily threat trends
        daily_trends = await database.fetch_all(f"""
            SELECT 
                DATE(dl.timestamp) as date,
                COUNT(*) as threat_count,
                COUNT(DISTINCT dl.query_domain) as unique_threats,
                COUNT(DISTINCT dl.client_ip) as affected_clients
            {base_query}
            GROUP BY DATE(dl.timestamp)
            ORDER BY date
        """, params)
        
        # Get top threat sources
        top_threats = await database.fetch_all(f"""
            SELECT 
                dl.query_domain as domain,
                COUNT(*) as block_count,
                rr.rpz_zone as category,
                rr.action,
                MIN(dl.timestamp) as first_seen,
                MAX(dl.timestamp) as last_seen,
                COUNT(DISTINCT dl.client_ip) as affected_clients
            {base_query}
            GROUP BY dl.query_domain, rr.rpz_zone, rr.action
            ORDER BY block_count DESC
            LIMIT 100
        """, params)
        
        return {
            "success": True,
            "data": {
                "overall_stats": dict(threat_stats) if threat_stats else {},
                "by_category": [dict(row) for row in by_category],
                "daily_trends": [dict(row) for row in daily_trends],
                "top_threat_sources": [dict(row) for row in top_threats],
                "time_range_days": days,
                "category_filter": category,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting threat analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get threat analytics")


@router.post("/cache/clear")
async def clear_analytics_cache(
    current_user: UserInfo = Depends(get_current_user)
):
    """Clear analytics cache to force refresh"""
    try:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        service = get_monitoring_service()
        service.clear_analytics_cache()
        
        return {
            "success": True,
            "message": "Analytics cache cleared successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing analytics cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear analytics cache")


@router.get("/export")
async def export_analytics_data(
    hours: int = Query(24, ge=1, le=168, description="Hours of data to export"),
    format: str = Query("json", regex="^(json|csv)$", description="Export format"),
    include_raw_logs: bool = Query(False, description="Include raw DNS logs"),
    current_user: UserInfo = Depends(get_current_user)
):
    """Export analytics data in various formats"""
    try:
        if not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        service = get_monitoring_service()
        since = datetime.utcnow() - timedelta(hours=hours)
        
        export_data = {
            "export_info": {
                "generated_at": datetime.utcnow().isoformat(),
                "time_range_hours": hours,
                "format": format,
                "exported_by": current_user.username
            }
        }
        
        # Get analytics data
        analytics = await service.get_query_analytics(hours=hours, use_cache=False)
        export_data["analytics"] = analytics
        
        # Get performance metrics
        performance = await service.get_performance_metrics(hours=hours)
        export_data["performance"] = {
            "queries_per_second": performance.queries_per_second,
            "avg_response_time": performance.avg_response_time,
            "cache_hit_rate": performance.cache_hit_rate,
            "error_rate": performance.error_rate,
            "blocked_rate": performance.blocked_rate
        }
        
        # Include raw logs if requested
        if include_raw_logs:
            from ...core.database import database
            
            raw_logs = await database.fetch_all("""
                SELECT 
                    timestamp, client_ip, query_domain, query_type,
                    response_code, blocked, response_time, rpz_zone
                FROM dns_logs 
                WHERE timestamp >= :since
                ORDER BY timestamp DESC
                LIMIT 10000
            """, {"since": since})
            
            export_data["raw_logs"] = [dict(log) for log in raw_logs]
        
        if format == "csv":
            # Convert to CSV format (simplified)
            import csv
            import io
            
            output = io.StringIO()
            
            # Write analytics summary as CSV
            writer = csv.writer(output)
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Export Generated", export_data["export_info"]["generated_at"]])
            writer.writerow(["Time Range Hours", hours])
            writer.writerow(["Queries Per Second", export_data["performance"]["queries_per_second"]])
            writer.writerow(["Avg Response Time", export_data["performance"]["avg_response_time"]])
            writer.writerow(["Blocked Rate", export_data["performance"]["blocked_rate"]])
            
            return {
                "success": True,
                "data": output.getvalue(),
                "content_type": "text/csv"
            }
        
        return {
            "success": True,
            "data": export_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting analytics data: {e}")
        raise HTTPException(status_code=500, detail="Failed to export analytics data")