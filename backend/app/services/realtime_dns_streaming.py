"""
Real-time DNS query streaming service with efficient parsing and filtering
Implements optimized DNS query log streaming with aggregation and statistics
"""

import asyncio
import json
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor

from ..core.config import get_settings
from ..core.logging_config import get_logger
from ..websocket.event_types import EventType, EventPriority, EventSeverity, create_event
from ..services.enhanced_event_service import get_enhanced_event_service

logger = get_logger(__name__)


@dataclass
class DNSQueryEvent:
    """DNS query event data structure"""
    timestamp: datetime
    client_ip: str
    query_domain: str
    query_type: str
    response_code: str
    response_time: float
    blocked: bool
    rpz_zone: Optional[str] = None
    forwarder_used: Optional[str] = None
    cache_hit: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "client_ip": self.client_ip,
            "query_domain": self.query_domain,
            "query_type": self.query_type,
            "response_code": self.response_code,
            "response_time": self.response_time,
            "blocked": self.blocked,
            "rpz_zone": self.rpz_zone,
            "forwarder_used": self.forwarder_used,
            "cache_hit": self.cache_hit
        }


@dataclass
class QueryStatistics:
    """Real-time query statistics"""
    total_queries: int = 0
    blocked_queries: int = 0
    queries_per_second: float = 0.0
    avg_response_time: float = 0.0
    cache_hit_rate: float = 0.0
    top_domains: Dict[str, int] = None
    top_clients: Dict[str, int] = None
    query_types: Dict[str, int] = None
    response_codes: Dict[str, int] = None
    
    def __post_init__(self):
        if self.top_domains is None:
            self.top_domains = {}
        if self.top_clients is None:
            self.top_clients = {}
        if self.query_types is None:
            self.query_types = {}
        if self.response_codes is None:
            self.response_codes = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class QueryFilter:
    """DNS query filter for performance optimization"""
    
    def __init__(self, 
                 allowed_domains: Optional[Set[str]] = None,
                 blocked_domains: Optional[Set[str]] = None,
                 allowed_clients: Optional[Set[str]] = None,
                 blocked_clients: Optional[Set[str]] = None,
                 query_types: Optional[Set[str]] = None,
                 min_response_time: Optional[float] = None,
                 max_response_time: Optional[float] = None):
        self.allowed_domains = allowed_domains or set()
        self.blocked_domains = blocked_domains or set()
        self.allowed_clients = allowed_clients or set()
        self.blocked_clients = blocked_clients or set()
        self.query_types = query_types or set()
        self.min_response_time = min_response_time
        self.max_response_time = max_response_time
    
    def should_include(self, query: DNSQueryEvent) -> bool:
        """Check if query should be included based on filter criteria"""
        # Domain filtering
        if self.blocked_domains and query.query_domain in self.blocked_domains:
            return False
        if self.allowed_domains and query.query_domain not in self.allowed_domains:
            return False
        
        # Client filtering
        if self.blocked_clients and query.client_ip in self.blocked_clients:
            return False
        if self.allowed_clients and query.client_ip not in self.allowed_clients:
            return False
        
        # Query type filtering
        if self.query_types and query.query_type not in self.query_types:
            return False
        
        # Response time filtering
        if self.min_response_time is not None and query.response_time < self.min_response_time:
            return False
        if self.max_response_time is not None and query.response_time > self.max_response_time:
            return False
        
        return True


class QueryAggregator:
    """Aggregates DNS queries for performance optimization"""
    
    def __init__(self, window_size: int = 60, max_entries: int = 1000):
        self.window_size = window_size  # seconds
        self.max_entries = max_entries
        self.queries = deque(maxlen=max_entries)
        self.statistics = QueryStatistics()
        self.lock = threading.Lock()
        
        # Time-based aggregation windows
        self.minute_stats = deque(maxlen=60)  # Last 60 minutes
        self.hour_stats = deque(maxlen=24)    # Last 24 hours
        
        # Real-time counters
        self.current_minute_queries = 0
        self.current_minute_blocked = 0
        self.current_minute_start = datetime.utcnow().replace(second=0, microsecond=0)
    
    def add_query(self, query: DNSQueryEvent):
        """Add a query to the aggregator"""
        with self.lock:
            self.queries.append(query)
            self._update_statistics(query)
            self._update_time_windows(query)
    
    def _update_statistics(self, query: DNSQueryEvent):
        """Update real-time statistics"""
        self.statistics.total_queries += 1
        
        if query.blocked:
            self.statistics.blocked_queries += 1
        
        # Update top domains (keep only top 50)
        self.statistics.top_domains[query.query_domain] = \
            self.statistics.top_domains.get(query.query_domain, 0) + 1
        if len(self.statistics.top_domains) > 50:
            # Keep only top 25 domains
            sorted_domains = sorted(self.statistics.top_domains.items(), 
                                  key=lambda x: x[1], reverse=True)[:25]
            self.statistics.top_domains = dict(sorted_domains)
        
        # Update top clients (keep only top 50)
        self.statistics.top_clients[query.client_ip] = \
            self.statistics.top_clients.get(query.client_ip, 0) + 1
        if len(self.statistics.top_clients) > 50:
            # Keep only top 25 clients
            sorted_clients = sorted(self.statistics.top_clients.items(), 
                                  key=lambda x: x[1], reverse=True)[:25]
            self.statistics.top_clients = dict(sorted_clients)
        
        # Update query types
        self.statistics.query_types[query.query_type] = \
            self.statistics.query_types.get(query.query_type, 0) + 1
        
        # Update response codes
        self.statistics.response_codes[query.response_code] = \
            self.statistics.response_codes.get(query.response_code, 0) + 1
        
        # Calculate rates and averages
        self._calculate_rates()
    
    def _update_time_windows(self, query: DNSQueryEvent):
        """Update time-based aggregation windows"""
        current_minute = query.timestamp.replace(second=0, microsecond=0)
        
        # Check if we've moved to a new minute
        if current_minute > self.current_minute_start:
            # Store previous minute stats
            if self.current_minute_queries > 0:
                self.minute_stats.append({
                    "timestamp": self.current_minute_start,
                    "queries": self.current_minute_queries,
                    "blocked": self.current_minute_blocked
                })
            
            # Reset for new minute
            self.current_minute_start = current_minute
            self.current_minute_queries = 0
            self.current_minute_blocked = 0
        
        # Update current minute counters
        self.current_minute_queries += 1
        if query.blocked:
            self.current_minute_blocked += 1
    
    def _calculate_rates(self):
        """Calculate queries per second and other rates"""
        if len(self.queries) < 2:
            return
        
        # Calculate QPS based on last minute of queries
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        recent_queries = [q for q in self.queries if q.timestamp >= minute_ago]
        self.statistics.queries_per_second = len(recent_queries) / 60.0
        
        # Calculate average response time
        response_times = [q.response_time for q in recent_queries if q.response_time > 0]
        if response_times:
            self.statistics.avg_response_time = sum(response_times) / len(response_times)
        
        # Calculate cache hit rate
        cache_hits = sum(1 for q in recent_queries if q.cache_hit)
        if recent_queries:
            self.statistics.cache_hit_rate = (cache_hits / len(recent_queries)) * 100
    
    def get_statistics(self) -> QueryStatistics:
        """Get current statistics"""
        with self.lock:
            # Update rates before returning
            self._calculate_rates()
            return self.statistics
    
    def get_recent_queries(self, limit: int = 100) -> List[DNSQueryEvent]:
        """Get recent queries"""
        with self.lock:
            return list(self.queries)[-limit:]
    
    def get_minute_stats(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get per-minute statistics"""
        with self.lock:
            return list(self.minute_stats)[-minutes:]


class RealtimeDNSStreamingService:
    """Real-time DNS query streaming service with optimization"""
    
    def __init__(self):
        self.settings = get_settings()
        self.event_service = get_enhanced_event_service()
        
        # Log file paths
        self.query_log_path = self.settings.log_dir / "query.log"
        self.rpz_log_path = self.settings.log_dir / "rpz.log"
        
        # File monitoring
        self.last_query_position = 0
        self.last_rpz_position = 0
        
        # Query processing
        self.query_aggregator = QueryAggregator()
        self.query_filter = QueryFilter()
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Streaming configuration
        self.streaming_enabled = True
        self.batch_size = 50
        self.batch_timeout = 2.0  # seconds
        self.max_events_per_second = 100
        
        # Background tasks
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._stats_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Event batching
        self._event_batch: List[DNSQueryEvent] = []
        self._last_batch_time = time.time()
        
        # Rate limiting
        self._events_this_second = 0
        self._current_second = int(time.time())
        
        # Regex patterns for log parsing
        self._compile_regex_patterns()
    
    def _compile_regex_patterns(self):
        """Compile regex patterns for log parsing"""
        # BIND query log pattern
        # Example: 15-Aug-2024 10:30:15.123 client 192.168.1.100#54321 (example.com): query: example.com IN A +E(0)K (10.0.0.1)
        self.query_pattern = re.compile(
            r'(\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) '
            r'client (\d+\.\d+\.\d+\.\d+)#\d+ '
            r'\(([^)]+)\): query: ([^\s]+) IN ([A-Z]+)'
            r'.*?'
            r'(?:\(([^)]+)\))?'  # Optional forwarder info
        )
        
        # BIND response log pattern (if available)
        # Example: 15-Aug-2024 10:30:15.125 client 192.168.1.100#54321 (example.com): response: example.com IN A NOERROR 1.2.3.4 (5ms)
        self.response_pattern = re.compile(
            r'(\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) '
            r'client (\d+\.\d+\.\d+\.\d+)#\d+ '
            r'\(([^)]+)\): response: ([^\s]+) IN ([A-Z]+) '
            r'([A-Z]+)'  # Response code
            r'.*?'
            r'\((\d+)ms\)'  # Response time
        )
        
        # RPZ log pattern
        # Example: 15-Aug-2024 10:30:15.123 client 192.168.1.100#54321: rpz QNAME NXDOMAIN rewrite malware.example.com via malware.rpz
        self.rpz_pattern = re.compile(
            r'(\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) '
            r'client (\d+\.\d+\.\d+\.\d+)#\d+: '
            r'rpz [A-Z]+ [A-Z]+ rewrite ([^\s]+) via ([^\s]+)'
        )
    
    async def start(self):
        """Start the real-time DNS streaming service"""
        if self._running:
            return
        
        self._running = True
        
        # Start background tasks
        self._monitor_task = asyncio.create_task(self._monitor_logs())
        self._stats_task = asyncio.create_task(self._broadcast_statistics())
        self._cleanup_task = asyncio.create_task(self._cleanup_old_data())
        
        logger.info("Real-time DNS streaming service started")
    
    async def stop(self):
        """Stop the real-time DNS streaming service"""
        if not self._running:
            return
        
        self._running = False
        
        # Flush any remaining events
        await self._flush_event_batch()
        
        # Cancel background tasks
        for task in [self._monitor_task, self._stats_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger.info("Real-time DNS streaming service stopped")
    
    async def _monitor_logs(self):
        """Monitor DNS log files for new entries"""
        while self._running:
            try:
                # Monitor query log
                await self._process_query_log()
                
                # Monitor RPZ log
                await self._process_rpz_log()
                
                # Process event batch if needed
                await self._check_batch_timeout()
                
                await asyncio.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                logger.error(f"Error monitoring logs: {e}")
                await asyncio.sleep(1)
    
    async def _process_query_log(self):
        """Process BIND query log file"""
        if not self.query_log_path.exists():
            return
        
        try:
            with open(self.query_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_query_position)
                new_lines = f.readlines()
                self.last_query_position = f.tell()
            
            # Process lines in thread pool for better performance
            if new_lines:
                loop = asyncio.get_event_loop()
                processed_queries = await loop.run_in_executor(
                    self.thread_pool, 
                    self._parse_query_lines, 
                    new_lines
                )
                
                for query in processed_queries:
                    await self._handle_dns_query(query)
                    
        except Exception as e:
            logger.error(f"Error processing query log: {e}")
    
    def _parse_query_lines(self, lines: List[str]) -> List[DNSQueryEvent]:
        """Parse query log lines (runs in thread pool)"""
        queries = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            try:
                query = self._parse_query_line(line)
                if query:
                    queries.append(query)
            except Exception as e:
                logger.debug(f"Error parsing query line: {e}")
        
        return queries
    
    def _parse_query_line(self, line: str) -> Optional[DNSQueryEvent]:
        """Parse a single query log line"""
        match = self.query_pattern.match(line)
        if not match:
            return None
        
        timestamp_str, client_ip, query_domain, domain, query_type, forwarder = match.groups()
        
        # Parse timestamp
        try:
            timestamp = datetime.strptime(timestamp_str, '%d-%b-%Y %H:%M:%S.%f')
        except ValueError:
            timestamp = datetime.utcnow()
        
        # Create query event
        query = DNSQueryEvent(
            timestamp=timestamp,
            client_ip=client_ip,
            query_domain=query_domain,
            query_type=query_type,
            response_code="NOERROR",  # Default, will be updated if response found
            response_time=0.0,  # Will be calculated if response found
            blocked=False,  # Will be updated if RPZ match found
            forwarder_used=forwarder
        )
        
        return query
    
    async def _process_rpz_log(self):
        """Process RPZ log file for blocked queries"""
        if not self.rpz_log_path.exists():
            return
        
        try:
            with open(self.rpz_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_rpz_position)
                new_lines = f.readlines()
                self.last_rpz_position = f.tell()
            
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    await self._parse_rpz_line(line)
                except Exception as e:
                    logger.debug(f"Error parsing RPZ line: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing RPZ log: {e}")
    
    async def _parse_rpz_line(self, line: str):
        """Parse RPZ log line and update blocked queries"""
        match = self.rpz_pattern.match(line)
        if not match:
            return
        
        timestamp_str, client_ip, blocked_domain, rpz_zone = match.groups()
        
        # Parse timestamp
        try:
            timestamp = datetime.strptime(timestamp_str, '%d-%b-%Y %H:%M:%S.%f')
        except ValueError:
            timestamp = datetime.utcnow()
        
        # Create blocked query event
        query = DNSQueryEvent(
            timestamp=timestamp,
            client_ip=client_ip,
            query_domain=blocked_domain,
            query_type="A",  # Default, actual type may vary
            response_code="NXDOMAIN",
            response_time=0.0,
            blocked=True,
            rpz_zone=rpz_zone
        )
        
        await self._handle_dns_query(query)
    
    async def _handle_dns_query(self, query: DNSQueryEvent):
        """Handle a parsed DNS query"""
        # Apply filter
        if not self.query_filter.should_include(query):
            return
        
        # Add to aggregator
        self.query_aggregator.add_query(query)
        
        # Add to event batch for streaming
        if self.streaming_enabled:
            await self._add_to_batch(query)
    
    async def _add_to_batch(self, query: DNSQueryEvent):
        """Add query to event batch"""
        # Rate limiting
        current_second = int(time.time())
        if current_second != self._current_second:
            self._current_second = current_second
            self._events_this_second = 0
        
        if self._events_this_second >= self.max_events_per_second:
            return  # Skip this event due to rate limiting
        
        self._events_this_second += 1
        self._event_batch.append(query)
        
        # Check if batch is full
        if len(self._event_batch) >= self.batch_size:
            await self._flush_event_batch()
    
    async def _check_batch_timeout(self):
        """Check if batch timeout has been reached"""
        if (self._event_batch and 
            time.time() - self._last_batch_time >= self.batch_timeout):
            await self._flush_event_batch()
    
    async def _flush_event_batch(self):
        """Flush the current event batch"""
        if not self._event_batch:
            return
        
        try:
            # Create batch event
            batch_data = {
                "queries": [query.to_dict() for query in self._event_batch],
                "batch_size": len(self._event_batch),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Emit batch event
            await self.event_service.emit_event(
                event_type=EventType.DNS_QUERY_BATCH,
                data=batch_data,
                priority=EventPriority.NORMAL,
                severity=EventSeverity.INFO
            )
            
            # Clear batch
            self._event_batch.clear()
            self._last_batch_time = time.time()
            
        except Exception as e:
            logger.error(f"Error flushing event batch: {e}")
    
    async def _broadcast_statistics(self):
        """Broadcast real-time statistics"""
        while self._running:
            try:
                stats = self.query_aggregator.get_statistics()
                
                # Emit statistics event
                await self.event_service.emit_event(
                    event_type=EventType.DNS_QUERY_STATISTICS,
                    data=stats.to_dict(),
                    priority=EventPriority.LOW,
                    severity=EventSeverity.INFO
                )
                
                await asyncio.sleep(30)  # Broadcast every 30 seconds
                
            except Exception as e:
                logger.error(f"Error broadcasting statistics: {e}")
                await asyncio.sleep(30)
    
    async def _cleanup_old_data(self):
        """Clean up old data to prevent memory leaks"""
        while self._running:
            try:
                # Reset aggregator statistics periodically
                # This prevents memory buildup in the top domains/clients dictionaries
                current_time = datetime.utcnow()
                
                # Reset every hour
                await asyncio.sleep(3600)
                
                # Clear old entries but keep recent statistics
                with self.query_aggregator.lock:
                    # Keep only recent queries (last 1000)
                    if len(self.query_aggregator.queries) > 1000:
                        recent_queries = list(self.query_aggregator.queries)[-500:]
                        self.query_aggregator.queries.clear()
                        self.query_aggregator.queries.extend(recent_queries)
                    
                    # Trim top domains/clients to reasonable size
                    for stat_dict in [self.query_aggregator.statistics.top_domains,
                                    self.query_aggregator.statistics.top_clients]:
                        if len(stat_dict) > 100:
                            sorted_items = sorted(stat_dict.items(), 
                                                key=lambda x: x[1], reverse=True)[:50]
                            stat_dict.clear()
                            stat_dict.update(sorted_items)
                
                logger.debug("Cleaned up old DNS streaming data")
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    def set_filter(self, query_filter: QueryFilter):
        """Set query filter"""
        self.query_filter = query_filter
        logger.info("Updated DNS query filter")
    
    def enable_streaming(self):
        """Enable real-time streaming"""
        self.streaming_enabled = True
        logger.info("DNS query streaming enabled")
    
    def disable_streaming(self):
        """Disable real-time streaming"""
        self.streaming_enabled = False
        logger.info("DNS query streaming disabled")
    
    def get_statistics(self) -> QueryStatistics:
        """Get current query statistics"""
        return self.query_aggregator.get_statistics()
    
    def get_recent_queries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent queries"""
        queries = self.query_aggregator.get_recent_queries(limit)
        return [query.to_dict() for query in queries]
    
    def get_minute_stats(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get per-minute statistics"""
        return self.query_aggregator.get_minute_stats(minutes)


# Global service instance
_realtime_dns_service: Optional[RealtimeDNSStreamingService] = None


def get_realtime_dns_service() -> RealtimeDNSStreamingService:
    """Get the global real-time DNS streaming service instance"""
    global _realtime_dns_service
    if _realtime_dns_service is None:
        _realtime_dns_service = RealtimeDNSStreamingService()
    return _realtime_dns_service


async def initialize_realtime_dns_service() -> RealtimeDNSStreamingService:
    """Initialize and start the real-time DNS streaming service"""
    service = get_realtime_dns_service()
    await service.start()
    return service


async def shutdown_realtime_dns_service():
    """Shutdown the real-time DNS streaming service"""
    global _realtime_dns_service
    if _realtime_dns_service:
        await _realtime_dns_service.stop()
        _realtime_dns_service = None