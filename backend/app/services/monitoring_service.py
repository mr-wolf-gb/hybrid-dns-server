"""
Monitoring service for DNS queries and system metrics
"""

import asyncio
import json
import psutil
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ..core.config import get_settings
from ..core.database import database
from ..core.logging_config import get_monitoring_logger

settings = get_settings()
logger = get_monitoring_logger()


class MonitoringService:
    """DNS monitoring and log parsing service"""
    
    def __init__(self):
        self.running = False
        self.query_log_path = settings.log_dir / "query.log"
        self.rpz_log_path = settings.log_dir / "rpz.log"
        self.last_position = 0
    
    async def start(self):
        """Start monitoring service"""
        self.running = True
        logger.info("Starting monitoring service")
        
        # Start background tasks
        asyncio.create_task(self._monitor_query_logs())
        asyncio.create_task(self._collect_system_metrics())
        
        logger.info("Monitoring service started")
    
    async def stop(self):
        """Stop monitoring service"""
        self.running = False
        logger.info("Monitoring service stopped")
    
    async def _monitor_query_logs(self):
        """Monitor BIND query logs and parse DNS queries"""
        while self.running:
            try:
                await self._parse_query_log()
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
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
            
        except Exception as e:
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
                
                # Clean up old metrics (keep only last 24 hours)
                cutoff = datetime.utcnow() - timedelta(hours=24)
                await database.execute(
                    "DELETE FROM system_stats WHERE timestamp < :cutoff",
                    {"cutoff": cutoff}
                )
                
                await asyncio.sleep(60)  # Collect metrics every minute
                
            except Exception as e:
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
            logger.error(f"Error getting top domains: {e}")
            return []