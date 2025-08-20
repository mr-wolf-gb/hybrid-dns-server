"""
Analytics Service for DNS Server Data Analysis

This service provides advanced analytics capabilities for DNS query data,
performance metrics, and trend analysis.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
import statistics
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from app.core.database import get_db
from app.models.dns import Zone, DNSRecord
from app.models.security import RPZRule
from app.services.monitoring_service import MonitoringService

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for DNS analytics and data analysis"""
    
    def __init__(self):
        self.monitoring_service = MonitoringService()
    
    async def get_query_trends(self, start_date: datetime, end_date: datetime,
                              interval: str = "hour") -> Dict[str, Any]:
        """Get query volume trends over time"""
        
        # Get query data from monitoring service
        query_data = await self.monitoring_service.get_query_logs(start_date, end_date)
        
        # Group by time interval
        trends = defaultdict(int)
        
        for query in query_data:
            timestamp = query.get("timestamp", datetime.utcnow())
            
            if interval == "hour":
                key = timestamp.strftime("%Y-%m-%d %H:00")
            elif interval == "day":
                key = timestamp.strftime("%Y-%m-%d")
            elif interval == "week":
                # Get start of week
                start_of_week = timestamp - timedelta(days=timestamp.weekday())
                key = start_of_week.strftime("%Y-%m-%d")
            else:
                key = timestamp.strftime("%Y-%m-%d %H:%M")
            
            trends[key] += 1
        
        # Convert to sorted list
        trend_data = [
            {"timestamp": timestamp, "count": count}
            for timestamp, count in sorted(trends.items())
        ]
        
        return {
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date,
            "data": trend_data,
            "total_queries": sum(trends.values()),
            "peak_hour": max(trends.items(), key=lambda x: x[1]) if trends else None
        }
    
    async def get_top_queried_domains(self, start_date: datetime, end_date: datetime,
                                    limit: int = 50) -> List[Dict[str, Any]]:
        """Get most queried domains"""
        
        query_data = await self.monitoring_service.get_query_logs(start_date, end_date)
        
        domain_counts = Counter()
        for query in query_data:
            domain = query.get("domain", "").lower()
            if domain:
                domain_counts[domain] += 1
        
        top_domains = [
            {
                "domain": domain,
                "query_count": count,
                "percentage": round((count / len(query_data)) * 100, 2) if query_data else 0
            }
            for domain, count in domain_counts.most_common(limit)
        ]
        
        return top_domains
    
    async def get_client_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get client-based analytics"""
        
        query_data = await self.monitoring_service.get_query_logs(start_date, end_date)
        
        client_stats = defaultdict(lambda: {
            "query_count": 0,
            "unique_domains": set(),
            "query_types": Counter(),
            "response_codes": Counter()
        })
        
        for query in query_data:
            client_ip = query.get("client_ip", "unknown")
            domain = query.get("domain", "")
            query_type = query.get("query_type", "A")
            response_code = query.get("response_code", "NOERROR")
            
            stats = client_stats[client_ip]
            stats["query_count"] += 1
            stats["unique_domains"].add(domain)
            stats["query_types"][query_type] += 1
            stats["response_codes"][response_code] += 1
        
        # Convert to list format
        client_analytics = []
        for client_ip, stats in client_stats.items():
            client_analytics.append({
                "client_ip": client_ip,
                "query_count": stats["query_count"],
                "unique_domains": len(stats["unique_domains"]),
                "top_query_type": stats["query_types"].most_common(1)[0] if stats["query_types"] else ("A", 0),
                "success_rate": round((stats["response_codes"]["NOERROR"] / stats["query_count"]) * 100, 2) if stats["query_count"] > 0 else 0
            })
        
        # Sort by query count
        client_analytics.sort(key=lambda x: x["query_count"], reverse=True)
        
        return {
            "total_clients": len(client_analytics),
            "clients": client_analytics[:50],  # Top 50 clients
            "total_queries": sum(stats["query_count"] for stats in client_stats.values())
        }
    
    async def get_response_time_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get response time analytics"""
        
        query_data = await self.monitoring_service.get_query_logs(start_date, end_date)
        
        response_times = []
        response_time_by_type = defaultdict(list)
        
        for query in query_data:
            response_time = query.get("response_time", 0)
            query_type = query.get("query_type", "A")
            
            if response_time > 0:
                response_times.append(response_time)
                response_time_by_type[query_type].append(response_time)
        
        if not response_times:
            return {
                "total_queries": 0,
                "avg_response_time": 0,
                "median_response_time": 0,
                "p95_response_time": 0,
                "p99_response_time": 0,
                "by_query_type": {}
            }
        
        # Calculate percentiles
        response_times.sort()
        p95_index = int(len(response_times) * 0.95)
        p99_index = int(len(response_times) * 0.99)
        
        # Calculate by query type
        by_query_type = {}
        for query_type, times in response_time_by_type.items():
            if times:
                by_query_type[query_type] = {
                    "count": len(times),
                    "avg_response_time": round(statistics.mean(times), 2),
                    "median_response_time": round(statistics.median(times), 2)
                }
        
        return {
            "total_queries": len(response_times),
            "avg_response_time": round(statistics.mean(response_times), 2),
            "median_response_time": round(statistics.median(response_times), 2),
            "p95_response_time": round(response_times[p95_index], 2),
            "p99_response_time": round(response_times[p99_index], 2),
            "by_query_type": by_query_type
        }
    
    async def get_error_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get error and failure analytics"""
        
        query_data = await self.monitoring_service.get_query_logs(start_date, end_date)
        
        response_codes = Counter()
        error_domains = Counter()
        error_trends = defaultdict(int)
        
        for query in query_data:
            response_code = query.get("response_code", "NOERROR")
            domain = query.get("domain", "")
            timestamp = query.get("timestamp", datetime.utcnow())
            
            response_codes[response_code] += 1
            
            if response_code != "NOERROR":
                error_domains[domain] += 1
                hour_key = timestamp.strftime("%Y-%m-%d %H:00")
                error_trends[hour_key] += 1
        
        total_queries = len(query_data)
        error_queries = total_queries - response_codes["NOERROR"]
        error_rate = round((error_queries / total_queries) * 100, 2) if total_queries > 0 else 0
        
        return {
            "total_queries": total_queries,
            "error_queries": error_queries,
            "error_rate": error_rate,
            "response_codes": dict(response_codes.most_common()),
            "top_error_domains": [
                {"domain": domain, "error_count": count}
                for domain, count in error_domains.most_common(20)
            ],
            "error_trends": [
                {"timestamp": timestamp, "error_count": count}
                for timestamp, count in sorted(error_trends.items())
            ]
        }
    
    async def get_security_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get security-related analytics"""
        
        # Get blocked queries from monitoring service
        blocked_data = await self.monitoring_service.get_blocked_queries(start_date, end_date)
        
        blocked_by_category = Counter()
        blocked_by_client = Counter()
        blocked_trends = defaultdict(int)
        threat_sources = Counter()
        
        for blocked_query in blocked_data:
            category = blocked_query.get("category", "unknown")
            client_ip = blocked_query.get("client_ip", "unknown")
            timestamp = blocked_query.get("timestamp", datetime.utcnow())
            source = blocked_query.get("threat_source", "custom")
            
            blocked_by_category[category] += 1
            blocked_by_client[client_ip] += 1
            threat_sources[source] += 1
            
            hour_key = timestamp.strftime("%Y-%m-%d %H:00")
            blocked_trends[hour_key] += 1
        
        # Get RPZ rule statistics
        db = next(get_db())
        try:
            rpz_stats = db.query(
                RPZRule.category,
                func.count(RPZRule.id).label('rule_count')
            ).filter(
                RPZRule.enabled == True
            ).group_by(RPZRule.category).all()
            
            category_rules = {category: count for category, count in rpz_stats}
            
        finally:
            db.close()
        
        return {
            "total_blocked": len(blocked_data),
            "blocked_by_category": [
                {
                    "category": category,
                    "blocked_count": count,
                    "rule_count": category_rules.get(category, 0)
                }
                for category, count in blocked_by_category.most_common()
            ],
            "top_blocked_clients": [
                {"client_ip": client, "blocked_count": count}
                for client, count in blocked_by_client.most_common(20)
            ],
            "blocked_trends": [
                {"timestamp": timestamp, "blocked_count": count}
                for timestamp, count in sorted(blocked_trends.items())
            ],
            "threat_sources": dict(threat_sources.most_common())
        }
    
    async def get_zone_analytics(self, zone_id: Optional[int] = None) -> Dict[str, Any]:
        """Get zone-specific analytics"""
        
        db = next(get_db())
        try:
            if zone_id:
                zones = db.query(Zone).filter(Zone.id == zone_id).all()
            else:
                zones = db.query(Zone).all()
            
            zone_analytics = []
            
            for zone in zones:
                # Get record count by type
                record_stats = db.query(
                    DNSRecord.record_type,
                    func.count(DNSRecord.id).label('count')
                ).filter(
                    DNSRecord.zone_id == zone.id
                ).group_by(DNSRecord.record_type).all()
                
                record_types = {record_type: count for record_type, count in record_stats}
                total_records = sum(record_types.values())
                
                # Get query statistics for this zone (from monitoring service)
                zone_queries = await self.monitoring_service.get_zone_queries(
                    zone.name,
                    datetime.utcnow() - timedelta(days=7),
                    datetime.utcnow()
                )
                
                zone_analytics.append({
                    "zone_id": zone.id,
                    "zone_name": zone.name,
                    "zone_type": zone.zone_type,
                    "enabled": zone.enabled,
                    "total_records": total_records,
                    "record_types": record_types,
                    "query_count_7d": len(zone_queries),
                    "last_modified": zone.updated_at.isoformat() if zone.updated_at else None
                })
            
            return {
                "zones": zone_analytics,
                "total_zones": len(zone_analytics),
                "active_zones": len([z for z in zone_analytics if z["enabled"]]),
                "total_records": sum(z["total_records"] for z in zone_analytics)
            }
            
        finally:
            db.close()
    
    async def get_performance_benchmarks(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get performance benchmarks and comparisons"""
        
        # Get current period data
        current_data = await self.get_response_time_analytics(start_date, end_date)
        
        # Get previous period for comparison
        period_length = end_date - start_date
        prev_start = start_date - period_length
        prev_end = start_date
        
        previous_data = await self.get_response_time_analytics(prev_start, prev_end)
        
        # Calculate changes
        avg_change = current_data["avg_response_time"] - previous_data["avg_response_time"]
        p95_change = current_data["p95_response_time"] - previous_data["p95_response_time"]
        
        # Get query volume comparison
        current_trends = await self.get_query_trends(start_date, end_date)
        previous_trends = await self.get_query_trends(prev_start, prev_end)
        
        volume_change = current_trends["total_queries"] - previous_trends["total_queries"]
        volume_change_pct = round((volume_change / previous_trends["total_queries"]) * 100, 2) if previous_trends["total_queries"] > 0 else 0
        
        return {
            "current_period": {
                "start_date": start_date,
                "end_date": end_date,
                "avg_response_time": current_data["avg_response_time"],
                "p95_response_time": current_data["p95_response_time"],
                "total_queries": current_trends["total_queries"]
            },
            "previous_period": {
                "start_date": prev_start,
                "end_date": prev_end,
                "avg_response_time": previous_data["avg_response_time"],
                "p95_response_time": previous_data["p95_response_time"],
                "total_queries": previous_trends["total_queries"]
            },
            "changes": {
                "avg_response_time_change": round(avg_change, 2),
                "p95_response_time_change": round(p95_change, 2),
                "query_volume_change": volume_change,
                "query_volume_change_pct": volume_change_pct
            },
            "benchmarks": {
                "target_avg_response_time": 50,  # ms
                "target_p95_response_time": 200,  # ms
                "target_error_rate": 1.0  # %
            }
        }
    
    async def generate_insights(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Generate automated insights from analytics data"""
        
        insights = []
        
        # Get various analytics
        trends = await self.get_query_trends(start_date, end_date)
        response_times = await self.get_response_time_analytics(start_date, end_date)
        errors = await self.get_error_analytics(start_date, end_date)
        security = await self.get_security_analytics(start_date, end_date)
        
        # Query volume insights
        if trends["total_queries"] > 10000:
            insights.append({
                "type": "volume",
                "severity": "info",
                "title": "High Query Volume",
                "description": f"Processed {trends['total_queries']:,} queries in the selected period.",
                "recommendation": "Monitor system resources and consider scaling if performance degrades."
            })
        
        # Performance insights
        if response_times["avg_response_time"] > 100:
            insights.append({
                "type": "performance",
                "severity": "warning",
                "title": "High Response Times",
                "description": f"Average response time is {response_times['avg_response_time']}ms, above recommended 50ms.",
                "recommendation": "Check forwarder health and network connectivity. Consider optimizing DNS configuration."
            })
        
        # Error rate insights
        if errors["error_rate"] > 5:
            insights.append({
                "type": "errors",
                "severity": "warning",
                "title": "High Error Rate",
                "description": f"Error rate is {errors['error_rate']}%, above recommended 1%.",
                "recommendation": "Review DNS configuration and check for misconfigured zones or records."
            })
        
        # Security insights
        if security["total_blocked"] > 1000:
            insights.append({
                "type": "security",
                "severity": "info",
                "title": "Active Threat Blocking",
                "description": f"Blocked {security['total_blocked']:,} malicious queries.",
                "recommendation": "Review blocked domains and consider updating threat intelligence feeds."
            })
        
        return insights

# Global analytics service instance
analytics_service = AnalyticsService()