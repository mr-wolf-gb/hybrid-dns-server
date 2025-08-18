"""
Dashboard endpoints for real-time DNS monitoring and statistics
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from ...core.database import database
from ...core.dependencies import get_current_user
from ...services.monitoring_service import MonitoringService
from ...services.bind_service import BindService

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
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
        
        # Get forwarder counts
        forwarder_stats = await database.fetch_one("""
            SELECT COUNT(*) as total_forwarders
            FROM forwarders 
            WHERE is_active = true
        """)
        
        if forwarder_stats:
            stats["forwarders"]["total"] = forwarder_stats["total_forwarders"] or 0
            # TODO: Implement health checking to get healthy/unhealthy counts
            stats["forwarders"]["healthy"] = forwarder_stats["total_forwarders"] or 0
        
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