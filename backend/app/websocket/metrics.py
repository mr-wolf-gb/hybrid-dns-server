"""
WebSocket Performance Metrics System
Comprehensive metrics collection for WebSocket operations, connection management, and event processing
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics collected"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Individual metric value with timestamp"""
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ConnectionMetrics:
    """Metrics for individual WebSocket connections"""
    user_id: str
    connected_at: datetime
    last_activity: datetime
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors: int = 0
    ping_count: int = 0
    pong_count: int = 0
    average_latency_ms: float = 0.0
    subscription_count: int = 0
    events_received: int = 0
    reconnection_count: int = 0
    
    def update_latency(self, latency_ms: float):
        """Update average latency with exponential moving average"""
        if self.average_latency_ms == 0:
            self.average_latency_ms = latency_ms
        else:
            # Exponential moving average with alpha = 0.1
            self.average_latency_ms = self.average_latency_ms * 0.9 + latency_ms * 0.1
    
    def get_connection_duration(self) -> timedelta:
        """Get total connection duration"""
        return datetime.utcnow() - self.connected_at
    
    def get_activity_duration(self) -> timedelta:
        """Get time since last activity"""
        return datetime.utcnow() - self.last_activity


@dataclass
class EventProcessingMetrics:
    """Metrics for event processing"""
    event_type: str
    total_processed: int = 0
    total_errors: int = 0
    total_processing_time_ms: float = 0.0
    average_processing_time_ms: float = 0.0
    min_processing_time_ms: float = float('inf')
    max_processing_time_ms: float = 0.0
    last_processed: Optional[datetime] = None
    
    def add_processing_time(self, processing_time_ms: float):
        """Add a new processing time measurement"""
        self.total_processed += 1
        self.total_processing_time_ms += processing_time_ms
        self.average_processing_time_ms = self.total_processing_time_ms / self.total_processed
        self.min_processing_time_ms = min(self.min_processing_time_ms, processing_time_ms)
        self.max_processing_time_ms = max(self.max_processing_time_ms, processing_time_ms)
        self.last_processed = datetime.utcnow()


@dataclass
class SystemResourceMetrics:
    """System resource usage metrics"""
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    disk_usage_percent: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_received: int = 0
    open_file_descriptors: int = 0
    thread_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class WebSocketMetrics:
    """
    Comprehensive WebSocket metrics collection system
    Tracks connections, events, performance, and resource usage
    """
    
    def __init__(self, retention_hours: int = 24, collection_interval: int = 30):
        # Configuration
        self.retention_hours = retention_hours
        self.collection_interval = collection_interval
        
        # Connection metrics
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}
        self.connection_history: deque = deque(maxlen=1000)
        
        # Event processing metrics
        self.event_metrics: Dict[str, EventProcessingMetrics] = defaultdict(EventProcessingMetrics)
        
        # System metrics
        self.system_metrics_history: deque = deque(maxlen=2880)  # 24 hours at 30s intervals
        self.current_system_metrics: Optional[SystemResourceMetrics] = None
        
        # Performance metrics
        self.performance_metrics: Dict[str, deque] = {
            "message_throughput": deque(maxlen=120),  # 1 hour at 30s intervals
            "event_throughput": deque(maxlen=120),
            "connection_count": deque(maxlen=120),
            "error_rate": deque(maxlen=120),
            "average_latency": deque(maxlen=120)
        }
        
        # Alerting thresholds
        self.alert_thresholds = {
            "max_connections": 400,
            "max_error_rate": 0.05,  # 5%
            "max_latency_ms": 1000,
            "max_cpu_usage": 80.0,
            "max_memory_usage": 85.0,
            "max_event_queue_size": 500
        }
        
        # Alert state tracking
        self.active_alerts: Set[str] = set()
        self.alert_history: deque = deque(maxlen=100)
        
        # Background tasks
        self._collection_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Metrics aggregation
        self.start_time = datetime.utcnow()
        self.total_connections_created = 0
        self.total_connections_closed = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.total_events_processed = 0
        self.total_errors = 0
    
    async def start(self):
        """Start metrics collection"""
        if self._running:
            return
        
        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("WebSocket metrics collection started")
    
    async def stop(self):
        """Stop metrics collection"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel tasks
        for task in [self._collection_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(self._collection_task, self._cleanup_task, return_exceptions=True)
        
        logger.info("WebSocket metrics collection stopped")
    
    def record_connection_created(self, user_id: str):
        """Record a new connection"""
        self.total_connections_created += 1
        
        metrics = ConnectionMetrics(
            user_id=user_id,
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        self.connection_metrics[user_id] = metrics
        
        # Add to history
        self.connection_history.append({
            "event": "connected",
            "user_id": user_id,
            "timestamp": datetime.utcnow()
        })
        
        logger.debug(f"Recorded connection created for user: {user_id}")
    
    def record_connection_closed(self, user_id: str, reason: str = "unknown"):
        """Record a connection closure"""
        self.total_connections_closed += 1
        
        if user_id in self.connection_metrics:
            connection_metrics = self.connection_metrics[user_id]
            duration = connection_metrics.get_connection_duration()
            
            # Add to history
            self.connection_history.append({
                "event": "disconnected",
                "user_id": user_id,
                "reason": reason,
                "duration_seconds": duration.total_seconds(),
                "messages_sent": connection_metrics.messages_sent,
                "messages_received": connection_metrics.messages_received,
                "timestamp": datetime.utcnow()
            })
            
            # Remove from active metrics
            del self.connection_metrics[user_id]
        
        logger.debug(f"Recorded connection closed for user: {user_id}, reason: {reason}")
    
    def record_message_sent(self, user_id: str, message_size_bytes: int):
        """Record a message sent to a connection"""
        self.total_messages_sent += 1
        
        if user_id in self.connection_metrics:
            metrics = self.connection_metrics[user_id]
            metrics.messages_sent += 1
            metrics.bytes_sent += message_size_bytes
            metrics.last_activity = datetime.utcnow()
    
    def record_message_received(self, user_id: str, message_size_bytes: int):
        """Record a message received from a connection"""
        self.total_messages_received += 1
        
        if user_id in self.connection_metrics:
            metrics = self.connection_metrics[user_id]
            metrics.messages_received += 1
            metrics.bytes_received += message_size_bytes
            metrics.last_activity = datetime.utcnow()
    
    def record_event_processed(self, event_type: str, processing_time_ms: float, success: bool = True):
        """Record event processing metrics"""
        self.total_events_processed += 1
        
        if event_type not in self.event_metrics:
            self.event_metrics[event_type] = EventProcessingMetrics(event_type=event_type)
        
        metrics = self.event_metrics[event_type]
        
        if success:
            metrics.add_processing_time(processing_time_ms)
        else:
            metrics.total_errors += 1
            self.total_errors += 1
    
    def record_connection_error(self, user_id: str, error_type: str):
        """Record a connection error"""
        self.total_errors += 1
        
        if user_id in self.connection_metrics:
            self.connection_metrics[user_id].errors += 1
        
        logger.warning(f"Connection error for {user_id}: {error_type}")
    
    def record_ping_pong(self, user_id: str, latency_ms: float, is_pong: bool = False):
        """Record ping/pong metrics"""
        if user_id in self.connection_metrics:
            metrics = self.connection_metrics[user_id]
            
            if is_pong:
                metrics.pong_count += 1
                metrics.update_latency(latency_ms)
            else:
                metrics.ping_count += 1
    
    def record_subscription_change(self, user_id: str, subscription_count: int):
        """Record subscription count change"""
        if user_id in self.connection_metrics:
            self.connection_metrics[user_id].subscription_count = subscription_count
    
    def record_event_received(self, user_id: str):
        """Record an event received by a connection"""
        if user_id in self.connection_metrics:
            self.connection_metrics[user_id].events_received += 1
    
    def record_reconnection(self, user_id: str):
        """Record a reconnection attempt"""
        if user_id in self.connection_metrics:
            self.connection_metrics[user_id].reconnection_count += 1
    
    async def collect_system_metrics(self):
        """Collect current system resource metrics"""
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Get network stats
            net_io = psutil.net_io_counters()
            
            metrics = SystemResourceMetrics(
                cpu_usage=cpu_percent,
                memory_usage_mb=process_memory.rss / 1024 / 1024,
                memory_usage_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_bytes_sent=net_io.bytes_sent if net_io else 0,
                network_bytes_received=net_io.bytes_recv if net_io else 0,
                open_file_descriptors=process.num_fds() if hasattr(process, 'num_fds') else 0,
                thread_count=process.num_threads()
            )
            
            self.current_system_metrics = metrics
            self.system_metrics_history.append(metrics)
            
            # Check for alerts
            await self._check_system_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _check_system_alerts(self, metrics: SystemResourceMetrics):
        """Check system metrics against alert thresholds"""
        alerts_to_add = set()
        alerts_to_remove = set()
        
        # CPU usage alert
        if metrics.cpu_usage > self.alert_thresholds["max_cpu_usage"]:
            alerts_to_add.add("high_cpu_usage")
        else:
            alerts_to_remove.add("high_cpu_usage")
        
        # Memory usage alert
        if metrics.memory_usage_percent > self.alert_thresholds["max_memory_usage"]:
            alerts_to_add.add("high_memory_usage")
        else:
            alerts_to_remove.add("high_memory_usage")
        
        # Connection count alert
        if len(self.connection_metrics) > self.alert_thresholds["max_connections"]:
            alerts_to_add.add("high_connection_count")
        else:
            alerts_to_remove.add("high_connection_count")
        
        # Process new alerts
        for alert in alerts_to_add:
            if alert not in self.active_alerts:
                self.active_alerts.add(alert)
                await self._trigger_alert(alert, metrics)
        
        # Remove resolved alerts
        for alert in alerts_to_remove:
            if alert in self.active_alerts:
                self.active_alerts.remove(alert)
                await self._resolve_alert(alert)
    
    async def _trigger_alert(self, alert_type: str, metrics: SystemResourceMetrics):
        """Trigger an alert"""
        alert_data = {
            "type": alert_type,
            "triggered_at": datetime.utcnow(),
            "metrics": metrics,
            "status": "active"
        }
        
        self.alert_history.append(alert_data)
        logger.warning(f"WebSocket alert triggered: {alert_type}")
        
        # Here you could integrate with external alerting systems
        # For now, we just log the alert
    
    async def _resolve_alert(self, alert_type: str):
        """Resolve an alert"""
        logger.info(f"WebSocket alert resolved: {alert_type}")
    
    async def _collection_loop(self):
        """Background task for periodic metrics collection"""
        while self._running:
            try:
                await self.collect_system_metrics()
                await self._update_performance_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _update_performance_metrics(self):
        """Update performance metrics"""
        now = datetime.utcnow()
        
        # Message throughput (messages per second)
        message_throughput = self.total_messages_sent / max(1, (now - self.start_time).total_seconds())
        self.performance_metrics["message_throughput"].append({
            "value": message_throughput,
            "timestamp": now
        })
        
        # Event throughput
        event_throughput = self.total_events_processed / max(1, (now - self.start_time).total_seconds())
        self.performance_metrics["event_throughput"].append({
            "value": event_throughput,
            "timestamp": now
        })
        
        # Connection count
        self.performance_metrics["connection_count"].append({
            "value": len(self.connection_metrics),
            "timestamp": now
        })
        
        # Error rate
        total_operations = self.total_messages_sent + self.total_events_processed
        error_rate = self.total_errors / max(1, total_operations)
        self.performance_metrics["error_rate"].append({
            "value": error_rate,
            "timestamp": now
        })
        
        # Average latency
        if self.connection_metrics:
            avg_latency = sum(m.average_latency_ms for m in self.connection_metrics.values()) / len(self.connection_metrics)
        else:
            avg_latency = 0.0
        
        self.performance_metrics["average_latency"].append({
            "value": avg_latency,
            "timestamp": now
        })
    
    async def _cleanup_loop(self):
        """Background task for cleaning up old metrics"""
        while self._running:
            try:
                await self._cleanup_old_metrics()
                await asyncio.sleep(3600)  # Run cleanup every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics data"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        # Clean up system metrics history
        while (self.system_metrics_history and 
               self.system_metrics_history[0].timestamp < cutoff_time):
            self.system_metrics_history.popleft()
        
        # Clean up connection history
        while (self.connection_history and 
               self.connection_history[0]["timestamp"] < cutoff_time):
            self.connection_history.popleft()
        
        # Clean up alert history
        while (self.alert_history and 
               self.alert_history[0]["triggered_at"] < cutoff_time):
            self.alert_history.popleft()
        
        logger.debug("Cleaned up old metrics data")
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        uptime = datetime.utcnow() - self.start_time
        
        return {
            "uptime_seconds": uptime.total_seconds(),
            "total_connections_created": self.total_connections_created,
            "total_connections_closed": self.total_connections_closed,
            "active_connections": len(self.connection_metrics),
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "total_events_processed": self.total_events_processed,
            "total_errors": self.total_errors,
            "error_rate": self.total_errors / max(1, self.total_messages_sent + self.total_events_processed),
            "active_alerts": list(self.active_alerts),
            "alert_count": len(self.active_alerts)
        }
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get detailed connection statistics"""
        if not self.connection_metrics:
            return {"active_connections": 0}
        
        connections = list(self.connection_metrics.values())
        
        return {
            "active_connections": len(connections),
            "total_messages_sent": sum(c.messages_sent for c in connections),
            "total_messages_received": sum(c.messages_received for c in connections),
            "total_bytes_sent": sum(c.bytes_sent for c in connections),
            "total_bytes_received": sum(c.bytes_received for c in connections),
            "total_errors": sum(c.errors for c in connections),
            "average_latency_ms": sum(c.average_latency_ms for c in connections) / len(connections),
            "total_subscriptions": sum(c.subscription_count for c in connections),
            "total_events_received": sum(c.events_received for c in connections),
            "total_reconnections": sum(c.reconnection_count for c in connections)
        }
    
    def get_event_processing_stats(self) -> Dict[str, Any]:
        """Get event processing statistics"""
        if not self.event_metrics:
            return {"event_types": 0}
        
        return {
            "event_types": len(self.event_metrics),
            "total_events_processed": sum(m.total_processed for m in self.event_metrics.values()),
            "total_processing_errors": sum(m.total_errors for m in self.event_metrics.values()),
            "average_processing_time_ms": sum(m.average_processing_time_ms for m in self.event_metrics.values()) / len(self.event_metrics),
            "event_type_breakdown": {
                event_type: {
                    "processed": metrics.total_processed,
                    "errors": metrics.total_errors,
                    "avg_time_ms": metrics.average_processing_time_ms,
                    "min_time_ms": metrics.min_processing_time_ms if metrics.min_processing_time_ms != float('inf') else 0,
                    "max_time_ms": metrics.max_processing_time_ms
                }
                for event_type, metrics in self.event_metrics.items()
            }
        }
    
    def get_performance_metrics(self, metric_name: str, limit: int = 60) -> List[Dict[str, Any]]:
        """Get performance metrics history"""
        if metric_name not in self.performance_metrics:
            return []
        
        metrics = list(self.performance_metrics[metric_name])
        return metrics[-limit:] if limit else metrics
    
    def get_system_metrics_history(self, limit: int = 60) -> List[Dict[str, Any]]:
        """Get system metrics history"""
        metrics = list(self.system_metrics_history)
        recent_metrics = metrics[-limit:] if limit else metrics
        
        return [
            {
                "cpu_usage": m.cpu_usage,
                "memory_usage_mb": m.memory_usage_mb,
                "memory_usage_percent": m.memory_usage_percent,
                "disk_usage_percent": m.disk_usage_percent,
                "network_bytes_sent": m.network_bytes_sent,
                "network_bytes_received": m.network_bytes_received,
                "thread_count": m.thread_count,
                "timestamp": m.timestamp.isoformat()
            }
            for m in recent_metrics
        ]
    
    def get_alert_status(self) -> Dict[str, Any]:
        """Get current alert status"""
        return {
            "active_alerts": list(self.active_alerts),
            "alert_count": len(self.active_alerts),
            "alert_history": [
                {
                    "type": alert["type"],
                    "triggered_at": alert["triggered_at"].isoformat(),
                    "status": alert["status"]
                }
                for alert in list(self.alert_history)[-10:]  # Last 10 alerts
            ],
            "thresholds": self.alert_thresholds
        }


# Global metrics instance
_websocket_metrics = None


def get_websocket_metrics() -> WebSocketMetrics:
    """Get the global WebSocket metrics instance"""
    global _websocket_metrics
    if _websocket_metrics is None:
        _websocket_metrics = WebSocketMetrics()
    return _websocket_metrics