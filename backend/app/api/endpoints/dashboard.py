"""
Dashboard endpoints for real-time DNS monitoring and statistics
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from ...core.database import database, get_database_session
from ...core.dependencies import get_current_user
from ...services.monitoring_service import MonitoringService
from ...services.bind_service import BindService
from ...services.health_service import get_health_service

router = APIRouter()


@router.get("/query-logs")
async def get_query_logs(
    page: int = 1,
    per_page: int = 50,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database_session)
):
    """Paginated DNS query logs for the dashboard query logs page"""
    # Clamp values
    page = max(1, page)
    per_page = max(1, min(200, per_page))

    try:
        # Build base query with optional search filter
        conditions = []
        params = {"limit": per_page, "offset": (page - 1) * per_page}

        if search:
            # Search in domain or client_ip
            conditions.append("(query_domain ILIKE :search OR client_ip ILIKE :search)")
            params["search"] = f"%{search}%"

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Total count
        total_query = f"""
            SELECT COUNT(*) AS total
            FROM dns_logs
            {where_sql}
        """

        # Items page
        items_query = f"""
            SELECT 
                timestamp,
                client_ip,
                query_domain,
                query_type,
                response_code,
                response_time,
                blocked AS is_blocked,
                rpz_zone AS blocked_category
            FROM dns_logs
            {where_sql}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """

        # Use shared database helper for simplicity
        total_row = await database.fetch_one(total_query, params)
        items = await database.fetch_all(items_query, params)

        total = (total_row or {}).get("total", 0)
        pages = max(1, (total + per_page - 1) // per_page)

        return {
            "items": items,
            "total": total,
            "page": page,
            "pages": pages,
        }
    except Exception:
        # Return empty page on failure rather than 500 so UI stays functional
        return {
            "items": [],
            "total": 0,
            "page": page,
            "pages": 1,
        }


@router.get("/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database_session)
):
    """Get real-time dashboard statistics"""
    
    # Get basic DNS statistics
    stats = {
        "queries": {
            "total_today": 0,
            "blocked_today": 0,
            "cached_hits": 0,
            "average_response_time": 0.0
        },
        "security": {
            "blocked_domains": 0,
            "threats_blocked": 0,
            "rpz_zones_active": 0
        },
        "system": {
            "uptime": "0 days, 0 hours",
            "memory_usage": 0.0,
            "cpu_usage": 0.0,
            "cache_size": 0
        },
        "forwarders": {
            "healthy": 0,
            "unhealthy": 0,
            "total": 0
        },
        "zones": {
            "authoritative": 0,
            "forward": 0,
            "total": 0
        }
    }
    
    try:
        # Get query statistics from today
        today = datetime.utcnow().date()
        query_stats = await database.fetch_one("""
            SELECT 
                COUNT(*) as total_queries,
                COUNT(*) FILTER (WHERE blocked = true) as blocked_queries,
                AVG(response_time) as avg_response_time
            FROM dns_logs 
            WHERE DATE(timestamp) = :today
        """, {"today": today})
        
        if query_stats:
            stats["queries"]["total_today"] = query_stats["total_queries"] or 0
            stats["queries"]["blocked_today"] = query_stats["blocked_queries"] or 0
            stats["queries"]["average_response_time"] = float(query_stats["avg_response_time"] or 0)
        
        # Get RPZ statistics
        rpz_stats = await database.fetch_one("""
            SELECT COUNT(*) as active_rules
            FROM rpz_rules 
            WHERE is_active = true
        """)
        
        if rpz_stats:
            stats["security"]["blocked_domains"] = rpz_stats["active_rules"] or 0
        
        # Get zone counts
        zone_stats = await database.fetch_one("""
            SELECT 
                COUNT(*) as total_zones,
                COUNT(*) FILTER (WHERE zone_type = 'master') as auth_zones,
                COUNT(*) FILTER (WHERE zone_type = 'forward') as forward_zones
            FROM zones 
            WHERE is_active = true
        """)
        
        if zone_stats:
            stats["zones"]["total"] = zone_stats["total_zones"] or 0
            stats["zones"]["authoritative"] = zone_stats["auth_zones"] or 0
            stats["zones"]["forward"] = zone_stats["forward_zones"] or 0
        
        # Get forwarder counts with health status
        forwarder_stats = await database.fetch_one("""
            SELECT COUNT(*) as total_forwarders
            FROM forwarders 
            WHERE is_active = true
        """)
        
        if forwarder_stats:
            stats["forwarders"]["total"] = forwarder_stats["total_forwarders"] or 0
            
            # Get health status for all forwarders
            health_service = get_health_service()
            health_summary = await health_service.get_forwarder_health_summary(db)
            
            stats["forwarders"]["healthy"] = health_summary.get("healthy_forwarders", 0)
            stats["forwarders"]["unhealthy"] = health_summary.get("unhealthy_forwarders", 0) + health_summary.get("degraded_forwarders", 0)
        
    except Exception as e:
        # Log error but don't fail the entire request
        pass
    
    return stats


@router.get("/recent-queries")
async def get_recent_queries(
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get recent DNS queries"""
    
    try:
        queries = await database.fetch_all("""
            SELECT timestamp, client_ip, query_domain, query_type, 
                   response_code, response_time, blocked, rpz_zone
            FROM dns_logs 
            ORDER BY timestamp DESC 
            LIMIT :limit
        """, {"limit": limit})
        
        return [dict(query) for query in queries]
        
    except Exception as e:
        return []


@router.get("/blocked-queries")
async def get_blocked_queries(
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get recent blocked queries"""
    
    try:
        queries = await database.fetch_all("""
            SELECT timestamp, client_ip, query_domain, query_type, rpz_zone
            FROM dns_logs 
            WHERE blocked = true
            ORDER BY timestamp DESC 
            LIMIT :limit
        """, {"limit": limit})
        
        return [dict(query) for query in queries]
        
    except Exception as e:
        return []


@router.get("/top-domains")
async def get_top_domains(
    hours: int = 24,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get top queried domains"""
    
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        domains = await database.fetch_all("""
            SELECT query_domain, COUNT(*) as query_count
            FROM dns_logs 
            WHERE timestamp >= :since AND blocked = false
            GROUP BY query_domain
            ORDER BY query_count DESC
            LIMIT :limit
        """, {"since": since, "limit": limit})
        
        return [dict(domain) for domain in domains]
        
    except Exception as e:
        return []


@router.get("/top-blocked")
async def get_top_blocked_domains(
    hours: int = 24,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get top blocked domains"""
    
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        domains = await database.fetch_all("""
            SELECT query_domain, COUNT(*) as block_count, rpz_zone
            FROM dns_logs 
            WHERE timestamp >= :since AND blocked = true
            GROUP BY query_domain, rpz_zone
            ORDER BY block_count DESC
            LIMIT :limit
        """, {"since": since, "limit": limit})
        
        return [dict(domain) for domain in domains]
        
    except Exception as e:
        return []


@router.get("/query-trends")
async def get_query_trends(
    hours: int = 24,
    current_user: dict = Depends(get_current_user)
):
    """Get query volume trends over time"""
    
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Group by hour
        trends = await database.fetch_all("""
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as total_queries,
                COUNT(*) FILTER (WHERE blocked = true) as blocked_queries
            FROM dns_logs 
            WHERE timestamp >= :since
            GROUP BY DATE_TRUNC('hour', timestamp)
            ORDER BY hour
        """, {"since": since})
        
        return [dict(trend) for trend in trends]
        
    except Exception as e:
        return []


@router.get("/bind-status")
async def get_bind_status(current_user: dict = Depends(get_current_user)):
    """Get BIND9 service status"""
    
    bind_service = BindService()
    status = await bind_service.get_service_status()
    
    return {
        "status": status.get("status", "unknown"),
        "uptime": status.get("uptime", "unknown"),
        "version": status.get("version", "unknown"),
        "config_valid": status.get("config_valid", False),
        "zones_loaded": status.get("zones_loaded", 0),
        "cache_size": status.get("cache_size", 0)
    }


@router.get("/health-status")
async def get_health_status_tracking(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database_session)
):
    """Get comprehensive health status tracking for all forwarders"""
    
    health_service = get_health_service()
    health_summary = await health_service.get_forwarder_health_summary(db)
    
    # Add additional tracking metrics
    health_tracking = {
        "summary": {
            "total_forwarders": health_summary.get("total_forwarders", 0),
            "active_forwarders": health_summary.get("active_forwarders", 0),
            "health_check_enabled": health_summary.get("health_check_enabled", 0),
            "healthy_forwarders": health_summary.get("healthy_forwarders", 0),
            "unhealthy_forwarders": health_summary.get("unhealthy_forwarders", 0),
            "degraded_forwarders": health_summary.get("degraded_forwarders", 0),
            "unknown_forwarders": health_summary.get("unknown_forwarders", 0),
            "last_updated": health_summary.get("last_updated")
        },
        "forwarder_details": health_summary.get("forwarder_details", []),
        "health_trends": {
            "healthy_percentage": 0.0,
            "unhealthy_percentage": 0.0,
            "degraded_percentage": 0.0,
            "unknown_percentage": 0.0
        }
    }
    
    # Calculate health percentages
    total_with_health_check = health_summary.get("health_check_enabled", 0)
    if total_with_health_check > 0:
        health_tracking["health_trends"]["healthy_percentage"] = (
            health_summary.get("healthy_forwarders", 0) / total_with_health_check * 100
        )
        health_tracking["health_trends"]["unhealthy_percentage"] = (
            health_summary.get("unhealthy_forwarders", 0) / total_with_health_check * 100
        )
        health_tracking["health_trends"]["degraded_percentage"] = (
            health_summary.get("degraded_forwarders", 0) / total_with_health_check * 100
        )
        health_tracking["health_trends"]["unknown_percentage"] = (
            health_summary.get("unknown_forwarders", 0) / total_with_health_check * 100
        )
    
    return health_tracking


@router.get("/health-alerts")
async def get_health_alerts(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database_session)
):
    """Get health alerts for unhealthy forwarders"""
    
    health_service = get_health_service()
    unhealthy_forwarders = await health_service.get_unhealthy_forwarders(db)
    
    alerts = []
    for forwarder in unhealthy_forwarders:
        alert_level = "critical" if forwarder["status"] == "unhealthy" else "warning"
        
        alerts.append({
            "id": f"forwarder_{forwarder['id']}",
            "level": alert_level,
            "title": f"Forwarder '{forwarder['name']}' is {forwarder['status']}",
            "message": f"Forwarder {forwarder['name']} ({forwarder['type']}) has {forwarder['healthy_servers']}/{forwarder['total_servers']} healthy servers",
            "timestamp": forwarder["last_checked"],
            "forwarder_id": forwarder["id"],
            "forwarder_name": forwarder["name"],
            "status": forwarder["status"],
            "healthy_servers": forwarder["healthy_servers"],
            "total_servers": forwarder["total_servers"],
            "server_details": forwarder.get("server_statuses", {})
        })
    
    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "critical_alerts": len([a for a in alerts if a["level"] == "critical"]),
        "warning_alerts": len([a for a in alerts if a["level"] == "warning"])
    }