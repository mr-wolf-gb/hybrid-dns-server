"""
Monitoring service for DNS queries and system metrics
"""

import asyncio
import json
import psutil
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from ..core.config import get_settings
from ..core.database import database
from ..core.logging_config import get_monitoring_logger


class MonitoringService:
    """DNS monitoring and log parsing service"""
    
    def __init__(self):
        self.running = False
        settings = get_settings()
        self.query_log_path = settings.log_dir / "query.log"
        self.rpz_log_path = settings.log_dir / "rpz.log"
        self.last_position = 0
    
    async def start(self) -> None:
        """Start monitoring service"""
        self.running = True
        logger = get_monitoring_logger()
        logger.info("Starting monitoring service")
        
        # Start background tasks
        asyncio.create_task(self._monitor_query_logs())
        asyncio.create_task(self._collect_system_metrics())
        
        logger.info("Monitoring service started")
    
    async def start_monitoring(self) -> None:
        """Start monitoring service (alias for install script compatibility)"""
        await self.start()
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """Stop monitoring service"""
        self.running = False
        logger = get_monitoring_logger()
        logger.info("Monitoring service stopped")
    
    async def _monitor_query_logs(self):
        """Monitor BIND query logs and parse DNS queries"""
        while self.running:
            try:
                await self._parse_query_log()
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger = get_monitoring_logger()
                logger.error(f"Error monitoring query logs: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def _parse_query_log(self):
        """Parse BIND query log file"""
        if not self.query_log_path.exists():
            return
        
        try:
            with open(self.query_log_path, 'r') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()
            
            for line in new_lines:
                await self._process_query_log_line(line.strip())
                
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error parsing query log: {e}")
    
    async def _process_query_log_line(self, line: str):
        """Process a single query log line"""
        try:
            # Parse BIND query log format
            # Example: 15-Aug-2024 10:30:15.123 client 192.168.1.100#54321 (example.com): query: example.com IN A +E(0)K (10.0.0.1)
            
            query_pattern = r'(\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) client (\d+\.\d+\.\d+\.\d+)#\d+ \(([^)]+)\): query: ([^\s]+) IN ([A-Z]+)'
            
            match = re.match(query_pattern, line)
            if not match:
                return
            
            timestamp_str, client_ip, query_domain, domain, query_type = match.groups()
            
            # Parse timestamp
            timestamp = datetime.strptime(timestamp_str, '%d-%b-%Y %H:%M:%S.%f')
            
            # Check if query was blocked (would appear in RPZ logs)
            blocked = await self._check_if_blocked(query_domain, timestamp)
            
            # Store query in database
            try:
                await database.execute("""
                    INSERT INTO dns_logs (
                        timestamp, client_ip, query_domain, query_type,
                        response_code, blocked, response_time
                    ) VALUES (
                        :timestamp, :client_ip, :query_domain, :query_type,
                        :response_code, :blocked, :response_time
                    )
                """, {
                    "timestamp": timestamp,
                    "client_ip": client_ip,
                    "query_domain": query_domain,
                    "query_type": query_type,
                    "response_code": "NOERROR",  # Default, could be parsed from logs
                    "blocked": blocked,
                    "response_time": 0  # Would need more detailed logging to get actual response times
                })
            except Exception as db_error:
                logger = get_monitoring_logger()
                logger.warning(f"Failed to store query log in database: {db_error}")
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error processing query log line: {e}")
    
    async def _check_if_blocked(self, domain: str, timestamp: datetime) -> bool:
        """Check if a domain query was blocked by RPZ"""
        # This is a simplified check - in reality, you'd parse RPZ logs
        # or integrate more deeply with BIND's logging
        
        try:
            # Check against active RPZ rules
            result = await database.fetch_one("""
                SELECT id FROM rpz_rules 
                WHERE domain = :domain AND is_active = true
                LIMIT 1
            """, {"domain": domain})
            
            return result is not None
            
        except Exception:
            # Table might not exist yet, return False
            return False
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        while self.running:
            try:
                # Collect CPU, memory, disk usage
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                timestamp = datetime.utcnow()
                
                # Store metrics
                metrics = [
                    ("cpu_usage", cpu_percent, "gauge"),
                    ("memory_usage", memory.percent, "gauge"),
                    ("memory_total", memory.total, "gauge"),
                    ("memory_available", memory.available, "gauge"),
                    ("disk_usage", disk.percent, "gauge"),
                    ("disk_total", disk.total, "gauge"),
                    ("disk_free", disk.free, "gauge"),
                ]
                
                for metric_name, metric_value, metric_type in metrics:
                    try:
                        await database.execute("""
                            INSERT INTO system_stats (
                                timestamp, metric_name, metric_value, metric_type
                            ) VALUES (:timestamp, :metric_name, :metric_value, :metric_type)
                        """, {
                            "timestamp": timestamp,
                            "metric_name": metric_name,
                            "metric_value": str(metric_value),
                            "metric_type": metric_type
                        })
                    except Exception as db_error:
                        logger = get_monitoring_logger()
                        logger.warning(f"Failed to store system metric: {db_error}")
                
                # Clean up old metrics (keep only last 24 hours)
                try:
                    cutoff = datetime.utcnow() - timedelta(hours=24)
                    await database.execute(
                        "DELETE FROM system_stats WHERE timestamp < :cutoff",
                        {"cutoff": cutoff}
                    )
                except Exception as db_error:
                    logger = get_monitoring_logger()
                    logger.warning(f"Failed to clean up old metrics: {db_error}")
                
                await asyncio.sleep(60)  # Collect metrics every minute
                
            except Exception as e:
                logger = get_monitoring_logger()
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(60)
    
    async def get_query_statistics(self, hours: int = 24) -> Dict:
        """Get query statistics for the specified time period"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(hours=hours)
            
            stats = await database.fetch_one("""
                SELECT 
                    COUNT(*) as total_queries,
                    COUNT(*) FILTER (WHERE blocked = true) as blocked_queries,
                    COUNT(DISTINCT client_ip) as unique_clients,
                    COUNT(DISTINCT query_domain) as unique_domains,
                    AVG(response_time) as avg_response_time
                FROM dns_logs 
                WHERE timestamp >= :since
            """, {"since": since})
            
            if stats:
                return dict(stats)
            
            return {
                "total_queries": 0,
                "blocked_queries": 0,
                "unique_clients": 0,
                "unique_domains": 0,
                "avg_response_time": 0.0
            }
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting query statistics: {e}")
            return {}
    
    async def get_top_domains(self, hours: int = 24, limit: int = 20) -> list:
        """Get top queried domains"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(hours=hours)
            
            domains = await database.fetch_all("""
                SELECT query_domain, COUNT(*) as query_count
                FROM dns_logs 
                WHERE timestamp >= :since
                GROUP BY query_domain
                ORDER BY query_count DESC
                LIMIT :limit
            """, {"since": since, "limit": limit})
            
            return [dict(domain) for domain in domains]
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting top domains: {e}")
            return []
    
    async def get_blocked_query_stats(self, hours: int = 24) -> Dict:
        """Get blocked query statistics for the specified time period"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(hours=hours)
            
            stats = await database.fetch_one("""
                SELECT 
                    COUNT(*) as total_queries,
                    COUNT(*) FILTER (WHERE blocked = true) as blocked_queries,
                    COUNT(DISTINCT client_ip) FILTER (WHERE blocked = true) as blocked_clients,
                    COUNT(DISTINCT query_domain) FILTER (WHERE blocked = true) as blocked_domains
                FROM dns_logs 
                WHERE timestamp >= :since
            """, {"since": since})
            
            if stats:
                result = dict(stats)
                # Calculate block rate percentage
                if result['total_queries'] > 0:
                    result['block_rate_percentage'] = round(
                        (result['blocked_queries'] / result['total_queries']) * 100, 2
                    )
                else:
                    result['block_rate_percentage'] = 0.0
                return result
            
            return {
                "total_queries": 0,
                "blocked_queries": 0,
                "blocked_clients": 0,
                "blocked_domains": 0,
                "block_rate_percentage": 0.0
            }
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting blocked query statistics: {e}")
            return {}
    
    async def get_top_blocked_domains(self, hours: int = 24, limit: int = 20, category: Optional[str] = None) -> list:
        """Get top blocked domains"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(hours=hours)
            
            query = """
                SELECT 
                    dl.query_domain, 
                    COUNT(*) as block_count,
                    rr.rpz_zone as category,
                    rr.action,
                    MIN(dl.timestamp) as first_blocked,
                    MAX(dl.timestamp) as last_blocked
                FROM dns_logs dl
                LEFT JOIN rpz_rules rr ON dl.query_domain = rr.domain
                WHERE dl.timestamp >= :since 
                AND dl.blocked = true
            """
            
            params = {"since": since, "limit": limit}
            
            if category:
                query += " AND rr.rpz_zone = :category"
                params["category"] = category
            
            query += """
                GROUP BY dl.query_domain, rr.rpz_zone, rr.action
                ORDER BY block_count DESC
                LIMIT :limit
            """
            
            domains = await database.fetch_all(query, params)
            
            return [dict(domain) for domain in domains]
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting top blocked domains: {e}")
            return []
    
    async def get_blocking_by_category(self, hours: int = 24) -> Dict:
        """Get blocking statistics by RPZ category"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(hours=hours)
            
            categories = await database.fetch_all("""
                SELECT 
                    rr.rpz_zone as category,
                    COUNT(*) as blocked_count,
                    COUNT(DISTINCT dl.query_domain) as unique_domains,
                    COUNT(DISTINCT dl.client_ip) as unique_clients
                FROM dns_logs dl
                JOIN rpz_rules rr ON dl.query_domain = rr.domain
                WHERE dl.timestamp >= :since 
                AND dl.blocked = true
                GROUP BY rr.rpz_zone
                ORDER BY blocked_count DESC
            """, {"since": since})
            
            return {cat['category']: dict(cat) for cat in categories}
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting blocking by category: {e}")
            return {}
    
    async def get_blocking_trends(self, days: int = 30) -> Dict:
        """Get blocking trends over time"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(days=days)
            
            # Daily blocking trends
            daily_trends = await database.fetch_all("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as total_queries,
                    COUNT(*) FILTER (WHERE blocked = true) as blocked_queries
                FROM dns_logs 
                WHERE timestamp >= :since
                GROUP BY DATE(timestamp)
                ORDER BY date
            """, {"since": since})
            
            # Hourly trends for last 24 hours
            last_24h = datetime.utcnow() - timedelta(hours=24)
            hourly_trends = await database.fetch_all("""
                SELECT 
                    DATE_TRUNC('hour', timestamp) as hour,
                    COUNT(*) as total_queries,
                    COUNT(*) FILTER (WHERE blocked = true) as blocked_queries
                FROM dns_logs 
                WHERE timestamp >= :since
                GROUP BY DATE_TRUNC('hour', timestamp)
                ORDER BY hour
            """, {"since": last_24h})
            
            return {
                'daily_trends': [dict(trend) for trend in daily_trends],
                'hourly_trends': [dict(trend) for trend in hourly_trends]
            }
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting blocking trends: {e}")
            return {'daily_trends': [], 'hourly_trends': []}
    
    async def get_blocked_queries(self, hours: int = 24, category: Optional[str] = None, 
                                 client_ip: Optional[str] = None, domain: Optional[str] = None,
                                 limit: int = 100, skip: int = 0) -> list:
        """Get detailed blocked queries with filtering"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(hours=hours)
            
            query = """
                SELECT 
                    dl.timestamp,
                    dl.client_ip,
                    dl.query_domain,
                    dl.query_type,
                    rr.rpz_zone as category,
                    rr.action,
                    rr.redirect_target
                FROM dns_logs dl
                LEFT JOIN rpz_rules rr ON dl.query_domain = rr.domain
                WHERE dl.timestamp >= :since 
                AND dl.blocked = true
            """
            
            params = {"since": since, "limit": limit, "skip": skip}
            
            if category:
                query += " AND rr.rpz_zone = :category"
                params["category"] = category
            
            if client_ip:
                query += " AND dl.client_ip = :client_ip"
                params["client_ip"] = client_ip
            
            if domain:
                query += " AND dl.query_domain ILIKE :domain"
                params["domain"] = f"%{domain}%"
            
            query += " ORDER BY dl.timestamp DESC LIMIT :limit OFFSET :skip"
            
            queries = await database.fetch_all(query, params)
            
            return [dict(query) for query in queries]
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting blocked queries: {e}")
            return []
    
    async def get_blocked_query_summary(self, hours: int = 24, category: Optional[str] = None,
                                       client_ip: Optional[str] = None, domain: Optional[str] = None) -> Dict:
        """Get summary statistics for blocked queries with filters"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(hours=hours)
            
            query = """
                SELECT 
                    COUNT(*) as total_blocked,
                    COUNT(DISTINCT dl.client_ip) as unique_clients,
                    COUNT(DISTINCT dl.query_domain) as unique_domains,
                    COUNT(DISTINCT rr.rpz_zone) as categories_triggered
                FROM dns_logs dl
                LEFT JOIN rpz_rules rr ON dl.query_domain = rr.domain
                WHERE dl.timestamp >= :since 
                AND dl.blocked = true
            """
            
            params = {"since": since}
            
            if category:
                query += " AND rr.rpz_zone = :category"
                params["category"] = category
            
            if client_ip:
                query += " AND dl.client_ip = :client_ip"
                params["client_ip"] = client_ip
            
            if domain:
                query += " AND dl.query_domain ILIKE :domain"
                params["domain"] = f"%{domain}%"
            
            result = await database.fetch_one(query, params)
            
            return dict(result) if result else {}
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting blocked query summary: {e}")
            return {}
    
    async def get_blocked_queries_hourly(self, hours: int = 24, category: Optional[str] = None) -> list:
        """Get hourly breakdown of blocked queries"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(hours=hours)
            
            query = """
                SELECT 
                    DATE_TRUNC('hour', dl.timestamp) as hour,
                    COUNT(*) as blocked_count
                FROM dns_logs dl
                LEFT JOIN rpz_rules rr ON dl.query_domain = rr.domain
                WHERE dl.timestamp >= :since 
                AND dl.blocked = true
            """
            
            params = {"since": since}
            
            if category:
                query += " AND rr.rpz_zone = :category"
                params["category"] = category
            
            query += " GROUP BY DATE_TRUNC('hour', dl.timestamp) ORDER BY hour"
            
            hourly_data = await database.fetch_all(query, params)
            
            return [dict(hour) for hour in hourly_data]
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting hourly blocked queries: {e}")
            return []
    
    async def get_threat_detection_stats(self, days: int = 30) -> Dict:
        """Get comprehensive threat detection statistics"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(days=days)
            
            stats = await database.fetch_one("""
                SELECT 
                    COUNT(*) FILTER (WHERE blocked = true) as total_blocked,
                    COUNT(DISTINCT query_domain) FILTER (WHERE blocked = true) as unique_domains,
                    COUNT(DISTINCT client_ip) FILTER (WHERE blocked = true) as unique_sources,
                    AVG(CASE WHEN blocked = true THEN 1 ELSE 0 END) * 100 as detection_rate_percent
                FROM dns_logs 
                WHERE timestamp >= :since
            """, {"since": since})
            
            if stats:
                result = dict(stats)
                result['daily_average'] = result['total_blocked'] / days if days > 0 else 0
                
                # Get top category
                top_category = await database.fetch_one("""
                    SELECT rr.rpz_zone as category, COUNT(*) as count
                    FROM dns_logs dl
                    JOIN rpz_rules rr ON dl.query_domain = rr.domain
                    WHERE dl.timestamp >= :since AND dl.blocked = true
                    GROUP BY rr.rpz_zone
                    ORDER BY count DESC
                    LIMIT 1
                """, {"since": since})
                
                result['top_category'] = top_category['category'] if top_category else 'Unknown'
                
                return result
            
            return {}
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting threat detection stats: {e}")
            return {}
    
    async def get_threats_by_category(self, days: int = 30) -> Dict:
        """Get threat statistics by category"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(days=days)
            
            categories = await database.fetch_all("""
                SELECT 
                    rr.rpz_zone as category,
                    COUNT(*) as threat_count,
                    COUNT(DISTINCT dl.query_domain) as unique_threats,
                    COUNT(DISTINCT dl.client_ip) as affected_clients,
                    rr.action as primary_action
                FROM dns_logs dl
                JOIN rpz_rules rr ON dl.query_domain = rr.domain
                WHERE dl.timestamp >= :since AND dl.blocked = true
                GROUP BY rr.rpz_zone, rr.action
                ORDER BY threat_count DESC
            """, {"since": since})
            
            return {cat['category']: dict(cat) for cat in categories}
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting threats by category: {e}")
            return {}
    
    async def get_top_threat_sources(self, days: int = 30, limit: int = 50) -> list:
        """Get top threat sources (domains that triggered most blocks)"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(days=days)
            
            sources = await database.fetch_all("""
                SELECT 
                    dl.query_domain as domain,
                    COUNT(*) as block_count,
                    rr.rpz_zone as category,
                    MIN(dl.timestamp) as first_seen,
                    MAX(dl.timestamp) as last_seen,
                    COUNT(DISTINCT dl.client_ip) as affected_clients
                FROM dns_logs dl
                JOIN rpz_rules rr ON dl.query_domain = rr.domain
                WHERE dl.timestamp >= :since AND dl.blocked = true
                GROUP BY dl.query_domain, rr.rpz_zone
                ORDER BY block_count DESC
                LIMIT :limit
            """, {"since": since, "limit": limit})
            
            return [dict(source) for source in sources]
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting top threat sources: {e}")
            return []
    
    async def get_threat_timeline(self, days: int = 30) -> list:
        """Get daily threat detection timeline"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(days=days)
            
            timeline = await database.fetch_all("""
                SELECT 
                    DATE(dl.timestamp) as date,
                    COUNT(*) FILTER (WHERE dl.blocked = true) as threats_blocked,
                    COUNT(DISTINCT dl.query_domain) FILTER (WHERE dl.blocked = true) as unique_threats,
                    COUNT(DISTINCT dl.client_ip) FILTER (WHERE dl.blocked = true) as affected_clients
                FROM dns_logs dl
                WHERE dl.timestamp >= :since
                GROUP BY DATE(dl.timestamp)
                ORDER BY date
            """, {"since": since})
            
            return [dict(day) for day in timeline]
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting threat timeline: {e}")
            return []
    
    async def get_geographic_threat_distribution(self, days: int = 30) -> Dict:
        """Get geographic distribution of threats (simplified - by IP ranges)"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(days=days)
            
            # Simple geographic distribution based on IP address ranges
            # In a real implementation, you'd use a GeoIP database
            geo_data = await database.fetch_all("""
                SELECT 
                    CASE 
                        WHEN client_ip LIKE '192.168.%' THEN 'Internal Network'
                        WHEN client_ip LIKE '10.%' THEN 'Internal Network'
                        WHEN client_ip LIKE '172.16.%' OR client_ip LIKE '172.17.%' OR 
                             client_ip LIKE '172.18.%' OR client_ip LIKE '172.19.%' OR
                             client_ip LIKE '172.20.%' OR client_ip LIKE '172.21.%' OR
                             client_ip LIKE '172.22.%' OR client_ip LIKE '172.23.%' OR
                             client_ip LIKE '172.24.%' OR client_ip LIKE '172.25.%' OR
                             client_ip LIKE '172.26.%' OR client_ip LIKE '172.27.%' OR
                             client_ip LIKE '172.28.%' OR client_ip LIKE '172.29.%' OR
                             client_ip LIKE '172.30.%' OR client_ip LIKE '172.31.%' THEN 'Internal Network'
                        ELSE 'External Network'
                    END as network_type,
                    COUNT(*) as threat_count,
                    COUNT(DISTINCT client_ip) as unique_sources
                FROM dns_logs 
                WHERE timestamp >= :since AND blocked = true
                GROUP BY network_type
            """, {"since": since})
            
            return {geo['network_type']: dict(geo) for geo in geo_data}
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting geographic threat distribution: {e}")
            return {}
    
    async def get_detailed_threat_breakdown(self, days: int = 30) -> Dict:
        """Get detailed threat breakdown by various dimensions"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(days=days)
            
            # Threats by action type
            by_action = await database.fetch_all("""
                SELECT 
                    rr.action,
                    COUNT(*) as count,
                    COUNT(DISTINCT dl.query_domain) as unique_domains
                FROM dns_logs dl
                JOIN rpz_rules rr ON dl.query_domain = rr.domain
                WHERE dl.timestamp >= :since AND dl.blocked = true
                GROUP BY rr.action
            """, {"since": since})
            
            # Threats by time of day
            by_hour = await database.fetch_all("""
                SELECT 
                    EXTRACT(hour FROM timestamp) as hour,
                    COUNT(*) as threat_count
                FROM dns_logs 
                WHERE timestamp >= :since AND blocked = true
                GROUP BY EXTRACT(hour FROM timestamp)
                ORDER BY hour
            """, {"since": since})
            
            # Threats by day of week
            by_weekday = await database.fetch_all("""
                SELECT 
                    EXTRACT(dow FROM timestamp) as day_of_week,
                    COUNT(*) as threat_count
                FROM dns_logs 
                WHERE timestamp >= :since AND blocked = true
                GROUP BY EXTRACT(dow FROM timestamp)
                ORDER BY day_of_week
            """, {"since": since})
            
            return {
                'by_action': [dict(item) for item in by_action],
                'by_hour': [dict(item) for item in by_hour],
                'by_weekday': [dict(item) for item in by_weekday]
            }
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting detailed threat breakdown: {e}")
            return {}
    
    async def get_category_blocking_stats(self, category: str, hours: int = 24) -> Dict:
        """Get blocking statistics for a specific category"""
        try:
            from datetime import timedelta
            since = datetime.utcnow() - timedelta(hours=hours)
            
            stats = await database.fetch_one("""
                SELECT 
                    COUNT(*) as blocked_queries,
                    COUNT(DISTINCT dl.client_ip) as blocked_clients,
                    COUNT(DISTINCT dl.query_domain) as blocked_domains,
                    AVG(dl.response_time) as avg_response_time
                FROM dns_logs dl
                JOIN rpz_rules rr ON dl.query_domain = rr.domain
                WHERE dl.timestamp >= :since 
                AND dl.blocked = true 
                AND rr.rpz_zone = :category
            """, {"since": since, "category": category})
            
            return dict(stats) if stats else {}
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting category blocking stats: {e}")
            return {}