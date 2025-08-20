"""
Enhanced monitoring service for DNS queries and system metrics with performance optimizations
"""

import asyncio
import json
import psutil
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

from ..core.config import get_settings
from ..core.database import database
from ..core.logging_config import get_monitoring_logger
from ..websocket.manager import get_websocket_manager, EventType


@dataclass
class QueryMetrics:
    """Data class for query metrics"""
    timestamp: datetime
    client_ip: str
    query_domain: str
    query_type: str
    response_time: float
    blocked: bool
    rpz_zone: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Data class for performance metrics"""
    queries_per_second: float
    avg_response_time: float
    cache_hit_rate: float
    error_rate: float
    blocked_rate: float


class MetricsBuffer:
    """Thread-safe buffer for collecting metrics before batch processing"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
    
    def add(self, metric: QueryMetrics):
        """Add metric to buffer"""
        with self.lock:
            self.buffer.append(metric)
    
    def flush(self) -> List[QueryMetrics]:
        """Flush and return all metrics from buffer"""
        with self.lock:
            metrics = list(self.buffer)
            self.buffer.clear()
            return metrics
    
    def size(self) -> int:
        """Get current buffer size"""
        with self.lock:
            return len(self.buffer)


class MonitoringService:
    """Enhanced DNS monitoring and log parsing service with performance optimizations"""
    
    def __init__(self):
        self.running = False
        settings = get_settings()
        self.query_log_path = settings.log_dir / "query.log"
        self.rpz_log_path = settings.log_dir / "rpz.log"
        self.last_position = 0
        self.websocket_manager = get_websocket_manager()
        
        # Enhanced metrics tracking
        self.query_stats = {
            'total_queries': 0,
            'blocked_queries': 0,
            'last_reset': datetime.utcnow(),
            'response_times': deque(maxlen=1000),  # Keep last 1000 response times
            'queries_per_minute': deque(maxlen=60),  # Keep last 60 minutes
            'error_count': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Performance optimization components
        self.metrics_buffer = MetricsBuffer(max_size=2000)
        self.batch_size = 100
        self.batch_timeout = 5.0  # seconds
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Analytics caching
        self.analytics_cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.cache_timestamps = {}
        
        # Real-time metrics
        self.real_time_metrics = {
            'current_qps': 0.0,
            'avg_response_time': 0.0,
            'blocked_rate': 0.0,
            'top_domains': defaultdict(int),
            'top_clients': defaultdict(int),
            'query_types': defaultdict(int)
        }
        
        # Trend analysis data
        self.trend_data = {
            'hourly_queries': defaultdict(int),
            'hourly_blocks': defaultdict(int),
            'daily_queries': defaultdict(int),
            'daily_blocks': defaultdict(int)
        }
    
    async def start(self) -> None:
        """Start enhanced monitoring service"""
        self.running = True
        logger = get_monitoring_logger()
        logger.info("Starting enhanced monitoring service")
        
        # Start background tasks
        asyncio.create_task(self._monitor_query_logs())
        asyncio.create_task(self._collect_system_metrics())
        asyncio.create_task(self._batch_process_metrics())
        asyncio.create_task(self._update_real_time_metrics())
        asyncio.create_task(self._cleanup_old_data())
        asyncio.create_task(self._generate_trend_analysis())
        
        logger.info("Enhanced monitoring service started with performance optimizations")
    
    async def start_monitoring(self) -> None:
        """Start monitoring service (alias for install script compatibility)"""
        await self.start()
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """Stop monitoring service"""
        self.running = False
        
        # Flush remaining metrics
        await self._flush_metrics_buffer()
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger = get_monitoring_logger()
        logger.info("Enhanced monitoring service stopped")
    
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
        """Process a single query log line with enhanced performance tracking"""
        try:
            # Parse BIND query log format with enhanced regex for response times
            # Example: 15-Aug-2024 10:30:15.123 client 192.168.1.100#54321 (example.com): query: example.com IN A +E(0)K (10.0.0.1) [response_time: 5ms]
            
            query_pattern = r'(\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) client (\d+\.\d+\.\d+\.\d+)#\d+ \(([^)]+)\): query: ([^\s]+) IN ([A-Z]+).*?(?:\[response_time: (\d+)ms\])?'
            
            match = re.match(query_pattern, line)
            if not match:
                return
            
            timestamp_str, client_ip, query_domain, domain, query_type, response_time_str = match.groups()
            
            # Parse timestamp
            timestamp = datetime.strptime(timestamp_str, '%d-%b-%Y %H:%M:%S.%f')
            
            # Parse response time
            response_time = float(response_time_str) if response_time_str else 0.0
            
            # Check if query was blocked (would appear in RPZ logs)
            blocked = await self._check_if_blocked(query_domain, timestamp)
            
            # Create metrics object for buffer
            metric = QueryMetrics(
                timestamp=timestamp,
                client_ip=client_ip,
                query_domain=query_domain,
                query_type=query_type,
                response_time=response_time,
                blocked=blocked,
                rpz_zone=None  # Will be populated if blocked
            )
            
            # Add to buffer for batch processing
            self.metrics_buffer.add(metric)
            
            # Update real-time stats
            self.query_stats['total_queries'] += 1
            if blocked:
                self.query_stats['blocked_queries'] += 1
            
            # Update response time tracking
            if response_time > 0:
                self.query_stats['response_times'].append(response_time)
            
            # Update real-time metrics
            self._update_real_time_counters(metric)
            
            # Broadcast real-time query event (throttled)
            if self.query_stats['total_queries'] % 10 == 0:  # Broadcast every 10th query
                await self._broadcast_query_event({
                    "timestamp": timestamp.isoformat(),
                    "client_ip": client_ip,
                    "query_domain": query_domain,
                    "query_type": query_type,
                    "blocked": blocked,
                    "response_time": response_time,
                    "total_queries_today": self.query_stats['total_queries'],
                    "blocked_queries_today": self.query_stats['blocked_queries'],
                    "current_qps": self.real_time_metrics['current_qps'],
                    "avg_response_time": self.real_time_metrics['avg_response_time']
                })
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error processing query log line: {e}")
    
    def _update_real_time_counters(self, metric: QueryMetrics):
        """Update real-time metrics counters"""
        # Update top domains
        self.real_time_metrics['top_domains'][metric.query_domain] += 1
        
        # Update top clients
        self.real_time_metrics['top_clients'][metric.client_ip] += 1
        
        # Update query types
        self.real_time_metrics['query_types'][metric.query_type] += 1
        
        # Update trend data
        hour_key = metric.timestamp.strftime('%Y-%m-%d %H:00')
        day_key = metric.timestamp.strftime('%Y-%m-%d')
        
        self.trend_data['hourly_queries'][hour_key] += 1
        self.trend_data['daily_queries'][day_key] += 1
        
        if metric.blocked:
            self.trend_data['hourly_blocks'][hour_key] += 1
            self.trend_data['daily_blocks'][day_key] += 1
    
    async def _batch_process_metrics(self):
        """Batch process metrics for improved database performance"""
        while self.running:
            try:
                # Wait for buffer to fill or timeout
                await asyncio.sleep(self.batch_timeout)
                
                if self.metrics_buffer.size() >= self.batch_size or self.metrics_buffer.size() > 0:
                    await self._flush_metrics_buffer()
                
            except Exception as e:
                logger = get_monitoring_logger()
                logger.error(f"Error in batch processing: {e}")
                await asyncio.sleep(5)
    
    async def _flush_metrics_buffer(self):
        """Flush metrics buffer to database"""
        metrics = self.metrics_buffer.flush()
        if not metrics:
            return
        
        try:
            # Prepare batch insert data
            insert_data = []
            for metric in metrics:
                insert_data.append({
                    "timestamp": metric.timestamp,
                    "client_ip": metric.client_ip,
                    "query_domain": metric.query_domain,
                    "query_type": metric.query_type,
                    "response_code": "NOERROR",  # Default
                    "blocked": metric.blocked,
                    "response_time": int(metric.response_time),
                    "rpz_zone": metric.rpz_zone,
                    "forwarder_used": None
                })
            
            # Batch insert using executemany equivalent
            if insert_data:
                await self._batch_insert_dns_logs(insert_data)
                
                logger = get_monitoring_logger()
                logger.debug(f"Batch processed {len(insert_data)} DNS log entries")
                
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error flushing metrics buffer: {e}")
    
    async def _batch_insert_dns_logs(self, data: List[Dict]):
        """Perform batch insert of DNS logs"""
        if not data:
            return
        
        try:
            # Use VALUES clause for efficient batch insert
            values_list = []
            for item in data:
                rpz_zone = 'NULL' if item['rpz_zone'] is None else f"'{item['rpz_zone']}'"
                forwarder_used = 'NULL' if item['forwarder_used'] is None else f"'{item['forwarder_used']}'"
                values_list.append(
                    f"('{item['timestamp']}', '{item['client_ip']}', '{item['query_domain']}', "
                    f"'{item['query_type']}', '{item['response_code']}', {item['blocked']}, "
                    f"{item['response_time']}, {rpz_zone}, {forwarder_used})"
                )
            values_clause = ", ".join(values_list)
            
            query = f"""
                INSERT INTO dns_logs (
                    timestamp, client_ip, query_domain, query_type,
                    response_code, blocked, response_time, rpz_zone, forwarder_used
                ) VALUES {values_clause}
            """
            
            await database.execute(query)
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error in batch insert: {e}")
            # Fallback to individual inserts
            for item in data:
                try:
                    await database.execute("""
                        INSERT INTO dns_logs (
                            timestamp, client_ip, query_domain, query_type,
                            response_code, blocked, response_time, rpz_zone, forwarder_used
                        ) VALUES (
                            :timestamp, :client_ip, :query_domain, :query_type,
                            :response_code, :blocked, :response_time, :rpz_zone, :forwarder_used
                        )
                    """, item)
                except Exception as individual_error:
                    logger = get_monitoring_logger()
                    logger.warning(f"Failed to insert individual DNS log: {individual_error}")
    
    async def _update_real_time_metrics(self):
        """Update real-time performance metrics"""
        while self.running:
            try:
                # Calculate queries per second
                current_time = time.time()
                minute_ago = current_time - 60
                
                # Count queries in last minute
                recent_queries = sum(1 for _ in self.query_stats['response_times'])
                self.real_time_metrics['current_qps'] = recent_queries / 60.0
                
                # Calculate average response time
                if self.query_stats['response_times']:
                    self.real_time_metrics['avg_response_time'] = sum(self.query_stats['response_times']) / len(self.query_stats['response_times'])
                
                # Calculate blocked rate
                if self.query_stats['total_queries'] > 0:
                    self.real_time_metrics['blocked_rate'] = (self.query_stats['blocked_queries'] / self.query_stats['total_queries']) * 100
                
                # Trim old data from real-time metrics
                self._trim_real_time_data()
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                logger = get_monitoring_logger()
                logger.error(f"Error updating real-time metrics: {e}")
                await asyncio.sleep(10)
    
    def _trim_real_time_data(self):
        """Trim old data from real-time metrics to prevent memory bloat"""
        # Keep only top 100 domains, clients, and query types
        for metric_dict in [self.real_time_metrics['top_domains'], 
                           self.real_time_metrics['top_clients'],
                           self.real_time_metrics['query_types']]:
            if len(metric_dict) > 100:
                # Keep only top 50 items
                sorted_items = sorted(metric_dict.items(), key=lambda x: x[1], reverse=True)[:50]
                metric_dict.clear()
                metric_dict.update(sorted_items)
        
        # Trim trend data to keep only recent data
        current_time = datetime.utcnow()
        
        # Keep only last 24 hours for hourly data
        cutoff_hour = (current_time - timedelta(hours=24)).strftime('%Y-%m-%d %H:00')
        self.trend_data['hourly_queries'] = {k: v for k, v in self.trend_data['hourly_queries'].items() if k >= cutoff_hour}
        self.trend_data['hourly_blocks'] = {k: v for k, v in self.trend_data['hourly_blocks'].items() if k >= cutoff_hour}
        
        # Keep only last 30 days for daily data
        cutoff_day = (current_time - timedelta(days=30)).strftime('%Y-%m-%d')
        self.trend_data['daily_queries'] = {k: v for k, v in self.trend_data['daily_queries'].items() if k >= cutoff_day}
        self.trend_data['daily_blocks'] = {k: v for k, v in self.trend_data['daily_blocks'].items() if k >= cutoff_day}
    
    async def _cleanup_old_data(self):
        """Clean up old data from database to maintain performance"""
        while self.running:
            try:
                # Run cleanup every hour
                await asyncio.sleep(3600)
                
                # Clean up old DNS logs (keep last 30 days by default)
                cutoff = datetime.utcnow() - timedelta(days=30)
                
                deleted_count = await database.execute(
                    "DELETE FROM dns_logs WHERE timestamp < :cutoff",
                    {"cutoff": cutoff}
                )
                
                # Clean up old system stats (keep last 7 days)
                stats_cutoff = datetime.utcnow() - timedelta(days=7)
                await database.execute(
                    "DELETE FROM system_stats WHERE timestamp < :cutoff",
                    {"cutoff": stats_cutoff}
                )
                
                # Vacuum database if using SQLite
                try:
                    await database.execute("VACUUM")
                except:
                    pass  # Not all databases support VACUUM
                
                logger = get_monitoring_logger()
                logger.info(f"Cleaned up old monitoring data")
                
            except Exception as e:
                logger = get_monitoring_logger()
                logger.error(f"Error cleaning up old data: {e}")
    
    async def _generate_trend_analysis(self):
        """Generate trend analysis and predictions"""
        while self.running:
            try:
                # Run trend analysis every 15 minutes
                await asyncio.sleep(900)
                
                await self._analyze_query_trends()
                await self._analyze_threat_trends()
                await self._detect_anomalies()
                
            except Exception as e:
                logger = get_monitoring_logger()
                logger.error(f"Error generating trend analysis: {e}")
    
    async def _analyze_query_trends(self):
        """Analyze query volume trends"""
        try:
            # Get hourly query data for last 24 hours
            since = datetime.utcnow() - timedelta(hours=24)
            
            hourly_data = await database.fetch_all("""
                SELECT 
                    DATE_TRUNC('hour', timestamp) as hour,
                    COUNT(*) as query_count,
                    AVG(response_time) as avg_response_time,
                    COUNT(*) FILTER (WHERE blocked = true) as blocked_count
                FROM dns_logs 
                WHERE timestamp >= :since
                GROUP BY DATE_TRUNC('hour', timestamp)
                ORDER BY hour
            """, {"since": since})
            
            if len(hourly_data) >= 3:
                # Calculate trend metrics
                query_counts = [row['query_count'] for row in hourly_data]
                response_times = [row['avg_response_time'] or 0 for row in hourly_data]
                
                # Simple trend calculation (could be enhanced with more sophisticated algorithms)
                query_trend = self._calculate_trend(query_counts)
                response_trend = self._calculate_trend(response_times)
                
                # Store trend analysis results
                self.analytics_cache['query_trends'] = {
                    'query_volume_trend': query_trend,
                    'response_time_trend': response_trend,
                    'hourly_data': [dict(row) for row in hourly_data],
                    'generated_at': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error analyzing query trends: {e}")
    
    async def _analyze_threat_trends(self):
        """Analyze threat detection trends"""
        try:
            # Get threat data for last 7 days
            since = datetime.utcnow() - timedelta(days=7)
            
            threat_data = await database.fetch_all("""
                SELECT 
                    DATE(dl.timestamp) as date,
                    rr.rpz_zone as category,
                    COUNT(*) as threat_count,
                    COUNT(DISTINCT dl.query_domain) as unique_threats,
                    COUNT(DISTINCT dl.client_ip) as affected_clients
                FROM dns_logs dl
                JOIN rpz_rules rr ON dl.query_domain = rr.domain
                WHERE dl.timestamp >= :since AND dl.blocked = true
                GROUP BY DATE(dl.timestamp), rr.rpz_zone
                ORDER BY date, threat_count DESC
            """, {"since": since})
            
            # Analyze threat patterns
            threat_by_category = defaultdict(list)
            for row in threat_data:
                threat_by_category[row['category']].append(row['threat_count'])
            
            threat_trends = {}
            for category, counts in threat_by_category.items():
                if len(counts) >= 3:
                    threat_trends[category] = {
                        'trend': self._calculate_trend(counts),
                        'total_threats': sum(counts),
                        'avg_daily': sum(counts) / len(counts)
                    }
            
            self.analytics_cache['threat_trends'] = {
                'by_category': threat_trends,
                'daily_data': [dict(row) for row in threat_data],
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error analyzing threat trends: {e}")
    
    async def _detect_anomalies(self):
        """Detect anomalies in DNS query patterns"""
        try:
            # Get recent query patterns
            since = datetime.utcnow() - timedelta(hours=1)
            
            recent_stats = await database.fetch_one("""
                SELECT 
                    COUNT(*) as total_queries,
                    COUNT(*) FILTER (WHERE blocked = true) as blocked_queries,
                    AVG(response_time) as avg_response_time,
                    COUNT(DISTINCT client_ip) as unique_clients,
                    COUNT(DISTINCT query_domain) as unique_domains
                FROM dns_logs 
                WHERE timestamp >= :since
            """, {"since": since})
            
            if recent_stats:
                # Compare with historical averages (last 7 days, same hour)
                week_ago = datetime.utcnow() - timedelta(days=7)
                current_hour = datetime.utcnow().hour
                
                historical_stats = await database.fetch_one("""
                    SELECT 
                        AVG(hourly_queries) as avg_queries,
                        AVG(hourly_blocks) as avg_blocks,
                        AVG(hourly_response_time) as avg_response_time
                    FROM (
                        SELECT 
                            DATE_TRUNC('hour', timestamp) as hour,
                            COUNT(*) as hourly_queries,
                            COUNT(*) FILTER (WHERE blocked = true) as hourly_blocks,
                            AVG(response_time) as hourly_response_time
                        FROM dns_logs 
                        WHERE timestamp >= :week_ago 
                        AND EXTRACT(hour FROM timestamp) = :current_hour
                        GROUP BY DATE_TRUNC('hour', timestamp)
                    ) hourly_stats
                """, {"week_ago": week_ago, "current_hour": current_hour})
                
                anomalies = []
                
                if historical_stats:
                    # Detect query volume anomalies (>200% or <50% of normal)
                    if recent_stats['total_queries'] > historical_stats['avg_queries'] * 2:
                        anomalies.append({
                            'type': 'high_query_volume',
                            'severity': 'warning',
                            'current': recent_stats['total_queries'],
                            'expected': historical_stats['avg_queries'],
                            'description': 'Query volume significantly higher than normal'
                        })
                    elif recent_stats['total_queries'] < historical_stats['avg_queries'] * 0.5:
                        anomalies.append({
                            'type': 'low_query_volume',
                            'severity': 'info',
                            'current': recent_stats['total_queries'],
                            'expected': historical_stats['avg_queries'],
                            'description': 'Query volume significantly lower than normal'
                        })
                    
                    # Detect response time anomalies
                    if recent_stats['avg_response_time'] and historical_stats['avg_response_time']:
                        if recent_stats['avg_response_time'] > historical_stats['avg_response_time'] * 2:
                            anomalies.append({
                                'type': 'high_response_time',
                                'severity': 'warning',
                                'current': recent_stats['avg_response_time'],
                                'expected': historical_stats['avg_response_time'],
                                'description': 'Response times significantly higher than normal'
                            })
                
                self.analytics_cache['anomalies'] = {
                    'detected_anomalies': anomalies,
                    'current_stats': dict(recent_stats),
                    'historical_stats': dict(historical_stats) if historical_stats else None,
                    'generated_at': datetime.utcnow().isoformat()
                }
                
                # Broadcast critical anomalies
                critical_anomalies = [a for a in anomalies if a['severity'] == 'warning']
                if critical_anomalies:
                    await self._broadcast_anomaly_alert(critical_anomalies)
                
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error detecting anomalies: {e}")
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a series of values"""
        if len(values) < 2:
            return "stable"
        
        # Simple linear trend calculation
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        
        # Determine trend based on slope
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    async def _broadcast_anomaly_alert(self, anomalies: List[Dict]):
        """Broadcast anomaly alerts via WebSocket"""
        try:
            await self.websocket_manager.emit_event(
                EventType.SYSTEM_STATUS,
                {
                    "type": "anomaly_alert",
                    "data": {
                        "anomalies": anomalies,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error broadcasting anomaly alert: {e}")
    
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
                
                # Broadcast real-time system metrics
                await self._broadcast_system_metrics({
                    "cpu_usage": cpu_percent,
                    "memory_usage": memory.percent,
                    "disk_usage": disk.percent,
                    "timestamp": timestamp.isoformat()
                })
                
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
    
    async def _broadcast_query_event(self, query_data: Dict):
        """Broadcast real-time query event via WebSocket"""
        try:
            await self.websocket_manager.emit_event(
                EventType.SYSTEM_STATUS,
                {
                    "type": "query_update",
                    "data": query_data
                }
            )
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error broadcasting query event: {e}")
    
    async def _broadcast_system_metrics(self, metrics_data: Dict):
        """Broadcast real-time system metrics via WebSocket"""
        try:
            await self.websocket_manager.emit_event(
                EventType.SYSTEM_STATUS,
                {
                    "type": "system_metrics",
                    "data": metrics_data
                }
            )
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error broadcasting system metrics: {e}")
    
    async def get_real_time_stats(self) -> Dict:
        """Get enhanced real-time statistics"""
        return {
            "total_queries": self.query_stats['total_queries'],
            "blocked_queries": self.query_stats['blocked_queries'],
            "block_rate": (
                (self.query_stats['blocked_queries'] / self.query_stats['total_queries'] * 100)
                if self.query_stats['total_queries'] > 0 else 0
            ),
            "last_reset": self.query_stats['last_reset'].isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.query_stats['last_reset']).total_seconds(),
            "current_qps": self.real_time_metrics['current_qps'],
            "avg_response_time": self.real_time_metrics['avg_response_time'],
            "blocked_rate": self.real_time_metrics['blocked_rate'],
            "buffer_size": self.metrics_buffer.size(),
            "top_domains": dict(list(self.real_time_metrics['top_domains'].items())[:10]),
            "top_clients": dict(list(self.real_time_metrics['top_clients'].items())[:10]),
            "query_types": dict(self.real_time_metrics['query_types'])
        }
    
    async def get_performance_metrics(self, hours: int = 1) -> PerformanceMetrics:
        """Get comprehensive performance metrics"""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            stats = await database.fetch_one("""
                SELECT 
                    COUNT(*) as total_queries,
                    COUNT(*) FILTER (WHERE blocked = true) as blocked_queries,
                    AVG(response_time) as avg_response_time,
                    COUNT(*) FILTER (WHERE response_code != 'NOERROR') as error_count,
                    COUNT(DISTINCT client_ip) as unique_clients
                FROM dns_logs 
                WHERE timestamp >= :since
            """, {"since": since})
            
            if stats and stats['total_queries'] > 0:
                queries_per_second = stats['total_queries'] / (hours * 3600)
                avg_response_time = stats['avg_response_time'] or 0.0
                error_rate = (stats['error_count'] / stats['total_queries']) * 100
                blocked_rate = (stats['blocked_queries'] / stats['total_queries']) * 100
                
                # Cache hit rate would need to be implemented in DNS server
                cache_hit_rate = 0.0  # Placeholder
                
                return PerformanceMetrics(
                    queries_per_second=queries_per_second,
                    avg_response_time=avg_response_time,
                    cache_hit_rate=cache_hit_rate,
                    error_rate=error_rate,
                    blocked_rate=blocked_rate
                )
            
            return PerformanceMetrics(0.0, 0.0, 0.0, 0.0, 0.0)
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting performance metrics: {e}")
            return PerformanceMetrics(0.0, 0.0, 0.0, 0.0, 0.0)
    
    async def get_query_analytics(self, hours: int = 24, use_cache: bool = True) -> Dict:
        """Get comprehensive query analytics with caching"""
        cache_key = f"query_analytics_{hours}"
        
        # Check cache first
        if use_cache and cache_key in self.analytics_cache:
            cache_time = self.cache_timestamps.get(cache_key, 0)
            if time.time() - cache_time < self.cache_ttl:
                return self.analytics_cache[cache_key]
        
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Get comprehensive analytics in parallel
            analytics_tasks = [
                self._get_query_volume_analytics(since),
                self._get_domain_analytics(since),
                self._get_client_analytics(since),
                self._get_response_time_analytics(since),
                self._get_geographic_analytics(since)
            ]
            
            results = await asyncio.gather(*analytics_tasks, return_exceptions=True)
            
            analytics = {
                "query_volume": results[0] if not isinstance(results[0], Exception) else {},
                "domain_analytics": results[1] if not isinstance(results[1], Exception) else {},
                "client_analytics": results[2] if not isinstance(results[2], Exception) else {},
                "response_time_analytics": results[3] if not isinstance(results[3], Exception) else {},
                "geographic_analytics": results[4] if not isinstance(results[4], Exception) else {},
                "generated_at": datetime.utcnow().isoformat(),
                "time_range_hours": hours
            }
            
            # Cache results
            self.analytics_cache[cache_key] = analytics
            self.cache_timestamps[cache_key] = time.time()
            
            return analytics
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting query analytics: {e}")
            return {}
    
    async def _get_query_volume_analytics(self, since: datetime) -> Dict:
        """Get query volume analytics"""
        try:
            # Hourly breakdown
            hourly_data = await database.fetch_all("""
                SELECT 
                    DATE_TRUNC('hour', timestamp) as hour,
                    COUNT(*) as query_count,
                    COUNT(*) FILTER (WHERE blocked = true) as blocked_count,
                    AVG(response_time) as avg_response_time
                FROM dns_logs 
                WHERE timestamp >= :since
                GROUP BY DATE_TRUNC('hour', timestamp)
                ORDER BY hour
            """, {"since": since})
            
            # Query type distribution
            query_types = await database.fetch_all("""
                SELECT 
                    query_type,
                    COUNT(*) as count,
                    COUNT(*) FILTER (WHERE blocked = true) as blocked_count
                FROM dns_logs 
                WHERE timestamp >= :since
                GROUP BY query_type
                ORDER BY count DESC
            """, {"since": since})
            
            return {
                "hourly_breakdown": [dict(row) for row in hourly_data],
                "query_type_distribution": [dict(row) for row in query_types],
                "total_hours": len(hourly_data)
            }
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting query volume analytics: {e}")
            return {}
    
    async def _get_domain_analytics(self, since: datetime) -> Dict:
        """Get domain analytics"""
        try:
            # Top queried domains
            top_domains = await database.fetch_all("""
                SELECT 
                    query_domain,
                    COUNT(*) as query_count,
                    COUNT(DISTINCT client_ip) as unique_clients,
                    COUNT(*) FILTER (WHERE blocked = true) as blocked_count
                FROM dns_logs 
                WHERE timestamp >= :since
                GROUP BY query_domain
                ORDER BY query_count DESC
                LIMIT 50
            """, {"since": since})
            
            # Domain categories (based on TLD)
            tld_stats = await database.fetch_all("""
                SELECT 
                    CASE 
                        WHEN query_domain LIKE '%.com' THEN 'com'
                        WHEN query_domain LIKE '%.org' THEN 'org'
                        WHEN query_domain LIKE '%.net' THEN 'net'
                        WHEN query_domain LIKE '%.edu' THEN 'edu'
                        WHEN query_domain LIKE '%.gov' THEN 'gov'
                        ELSE 'other'
                    END as tld,
                    COUNT(*) as query_count
                FROM dns_logs 
                WHERE timestamp >= :since
                GROUP BY tld
                ORDER BY query_count DESC
            """, {"since": since})
            
            return {
                "top_domains": [dict(row) for row in top_domains],
                "tld_distribution": [dict(row) for row in tld_stats]
            }
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting domain analytics: {e}")
            return {}
    
    async def _get_client_analytics(self, since: datetime) -> Dict:
        """Get client analytics"""
        try:
            # Top clients by query volume
            top_clients = await database.fetch_all("""
                SELECT 
                    client_ip,
                    COUNT(*) as query_count,
                    COUNT(DISTINCT query_domain) as unique_domains,
                    COUNT(*) FILTER (WHERE blocked = true) as blocked_count,
                    AVG(response_time) as avg_response_time
                FROM dns_logs 
                WHERE timestamp >= :since
                GROUP BY client_ip
                ORDER BY query_count DESC
                LIMIT 50
            """, {"since": since})
            
            # Client activity patterns
            client_patterns = await database.fetch_all("""
                SELECT 
                    EXTRACT(hour FROM timestamp) as hour,
                    COUNT(DISTINCT client_ip) as active_clients,
                    COUNT(*) as total_queries
                FROM dns_logs 
                WHERE timestamp >= :since
                GROUP BY EXTRACT(hour FROM timestamp)
                ORDER BY hour
            """, {"since": since})
            
            return {
                "top_clients": [dict(row) for row in top_clients],
                "hourly_activity": [dict(row) for row in client_patterns]
            }
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting client analytics: {e}")
            return {}
    
    async def _get_response_time_analytics(self, since: datetime) -> Dict:
        """Get response time analytics"""
        try:
            # Response time distribution
            response_time_stats = await database.fetch_one("""
                SELECT 
                    AVG(response_time) as avg_response_time,
                    MIN(response_time) as min_response_time,
                    MAX(response_time) as max_response_time,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time) as median_response_time,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time) as p95_response_time,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time) as p99_response_time
                FROM dns_logs 
                WHERE timestamp >= :since AND response_time > 0
            """, {"since": since})
            
            # Response time by query type
            response_by_type = await database.fetch_all("""
                SELECT 
                    query_type,
                    AVG(response_time) as avg_response_time,
                    COUNT(*) as query_count
                FROM dns_logs 
                WHERE timestamp >= :since AND response_time > 0
                GROUP BY query_type
                ORDER BY avg_response_time DESC
            """, {"since": since})
            
            return {
                "overall_stats": dict(response_time_stats) if response_time_stats else {},
                "by_query_type": [dict(row) for row in response_by_type]
            }
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting response time analytics: {e}")
            return {}
    
    async def _get_geographic_analytics(self, since: datetime) -> Dict:
        """Get geographic analytics (simplified IP-based)"""
        try:
            # IP range analysis (simplified)
            ip_ranges = await database.fetch_all("""
                SELECT 
                    CASE 
                        WHEN client_ip LIKE '192.168.%' THEN 'Private (192.168.x.x)'
                        WHEN client_ip LIKE '10.%' THEN 'Private (10.x.x.x)'
                        WHEN client_ip LIKE '172.16.%' OR client_ip LIKE '172.17.%' OR 
                             client_ip LIKE '172.18.%' OR client_ip LIKE '172.19.%' OR
                             client_ip LIKE '172.2_.%' OR client_ip LIKE '172.30.%' OR
                             client_ip LIKE '172.31.%' THEN 'Private (172.16-31.x.x)'
                        WHEN client_ip LIKE '127.%' THEN 'Localhost'
                        ELSE 'Public'
                    END as ip_range,
                    COUNT(*) as query_count,
                    COUNT(DISTINCT client_ip) as unique_ips
                FROM dns_logs 
                WHERE timestamp >= :since
                GROUP BY ip_range
                ORDER BY query_count DESC
            """, {"since": since})
            
            return {
                "ip_range_distribution": [dict(row) for row in ip_ranges]
            }
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting geographic analytics: {e}")
            return {}
    
    async def get_trend_analysis(self, days: int = 30) -> Dict:
        """Get comprehensive trend analysis"""
        try:
            # Check cache first
            cache_key = f"trend_analysis_{days}"
            if cache_key in self.analytics_cache:
                cache_time = self.cache_timestamps.get(cache_key, 0)
                if time.time() - cache_time < self.cache_ttl:
                    return self.analytics_cache[cache_key]
            
            # Get cached trend data if available
            trends = {}
            if 'query_trends' in self.analytics_cache:
                trends['query_trends'] = self.analytics_cache['query_trends']
            
            if 'threat_trends' in self.analytics_cache:
                trends['threat_trends'] = self.analytics_cache['threat_trends']
            
            # Add real-time trend data
            trends['real_time_trends'] = {
                'hourly_queries': dict(self.trend_data['hourly_queries']),
                'hourly_blocks': dict(self.trend_data['hourly_blocks']),
                'daily_queries': dict(self.trend_data['daily_queries']),
                'daily_blocks': dict(self.trend_data['daily_blocks'])
            }
            
            # Add predictions (simple linear extrapolation)
            trends['predictions'] = await self._generate_predictions()
            
            trends['generated_at'] = datetime.utcnow().isoformat()
            
            # Cache results
            self.analytics_cache[cache_key] = trends
            self.cache_timestamps[cache_key] = time.time()
            
            return trends
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error getting trend analysis: {e}")
            return {}
    
    async def _generate_predictions(self) -> Dict:
        """Generate simple predictions based on trends"""
        try:
            predictions = {}
            
            # Predict next hour query volume based on recent trend
            recent_hours = list(self.trend_data['hourly_queries'].values())[-6:]  # Last 6 hours
            if len(recent_hours) >= 3:
                trend = self._calculate_trend(recent_hours)
                avg_queries = sum(recent_hours) / len(recent_hours)
                
                if trend == "increasing":
                    predicted_queries = int(avg_queries * 1.1)
                elif trend == "decreasing":
                    predicted_queries = int(avg_queries * 0.9)
                else:
                    predicted_queries = int(avg_queries)
                
                predictions['next_hour_queries'] = {
                    'predicted_count': predicted_queries,
                    'confidence': 'medium',
                    'based_on_trend': trend
                }
            
            # Predict threat level
            recent_blocks = list(self.trend_data['hourly_blocks'].values())[-6:]
            if len(recent_blocks) >= 3:
                block_trend = self._calculate_trend(recent_blocks)
                avg_blocks = sum(recent_blocks) / len(recent_blocks)
                
                predictions['threat_level'] = {
                    'current_trend': block_trend,
                    'avg_blocks_per_hour': avg_blocks,
                    'risk_level': 'high' if avg_blocks > 100 else 'medium' if avg_blocks > 50 else 'low'
                }
            
            return predictions
            
        except Exception as e:
            logger = get_monitoring_logger()
            logger.error(f"Error generating predictions: {e}")
            return {}
    
    async def get_anomaly_detection(self) -> Dict:
        """Get current anomaly detection results"""
        return self.analytics_cache.get('anomalies', {
            'detected_anomalies': [],
            'generated_at': datetime.utcnow().isoformat()
        })
    
    def clear_analytics_cache(self):
        """Clear analytics cache to force refresh"""
        self.analytics_cache.clear()
        self.cache_timestamps.clear()
        logger = get_monitoring_logger()
        logger.info("Analytics cache cleared")
    
    async def reset_daily_stats(self):
        """Reset daily statistics (called at midnight)"""
        self.query_stats = {
            'total_queries': 0,
            'blocked_queries': 0,
            'last_reset': datetime.utcnow()
        }
    
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