"""
WebSocket Health Monitoring and Alerting System
Monitors WebSocket system health and triggers alerts for performance issues
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass
from enum import Enum

from ..core.logging_config import get_logger
from .metrics import get_websocket_metrics, WebSocketMetrics

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Individual health check definition"""
    name: str
    description: str
    check_function: Callable
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    enabled: bool = True
    interval_seconds: int = 30
    timeout_seconds: int = 10
    last_check: Optional[datetime] = None
    last_status: HealthStatus = HealthStatus.UNKNOWN
    last_value: Optional[float] = None
    consecutive_failures: int = 0
    max_consecutive_failures: int = 3


@dataclass
class Alert:
    """Alert definition"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    status: str = "active"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class WebSocketHealthMonitor:
    """
    Comprehensive health monitoring system for WebSocket operations
    Monitors performance, resource usage, and system health
    """
    
    def __init__(self, metrics: Optional[WebSocketMetrics] = None):
        self.metrics = metrics or get_websocket_metrics()
        
        # Health checks registry
        self.health_checks: Dict[str, HealthCheck] = {}
        
        # Alert management
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_callbacks: List[Callable] = []
        
        # Monitoring configuration
        self.monitoring_enabled = True
        self.check_interval = 30  # seconds
        self.alert_cooldown = 300  # 5 minutes
        self.max_alert_history = 1000
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Resource leak detection
        self.resource_baselines: Dict[str, float] = {}
        self.leak_detection_enabled = True
        self.leak_detection_window = 3600  # 1 hour
        
        # Performance degradation detection
        self.performance_baselines: Dict[str, float] = {}
        self.performance_degradation_threshold = 0.5  # 50% degradation
        
        # Initialize default health checks
        self._register_default_health_checks()
    
    def _register_default_health_checks(self):
        """Register default health checks"""
        
        # Connection count health check
        self.register_health_check(
            name="connection_count",
            description="Monitor active WebSocket connection count",
            check_function=self._check_connection_count,
            warning_threshold=300,
            critical_threshold=400
        )
        
        # Error rate health check
        self.register_health_check(
            name="error_rate",
            description="Monitor WebSocket error rate",
            check_function=self._check_error_rate,
            warning_threshold=0.05,  # 5%
            critical_threshold=0.10   # 10%
        )
        
        # Average latency health check
        self.register_health_check(
            name="average_latency",
            description="Monitor average WebSocket latency",
            check_function=self._check_average_latency,
            warning_threshold=500,   # 500ms
            critical_threshold=1000  # 1000ms
        )
        
        # Memory usage health check
        self.register_health_check(
            name="memory_usage",
            description="Monitor system memory usage",
            check_function=self._check_memory_usage,
            warning_threshold=80.0,  # 80%
            critical_threshold=90.0  # 90%
        )
        
        # CPU usage health check
        self.register_health_check(
            name="cpu_usage",
            description="Monitor system CPU usage",
            check_function=self._check_cpu_usage,
            warning_threshold=70.0,  # 70%
            critical_threshold=85.0  # 85%
        )
        
        # Event queue size health check
        self.register_health_check(
            name="event_queue_size",
            description="Monitor event queue size",
            check_function=self._check_event_queue_size,
            warning_threshold=100,
            critical_threshold=500
        )
        
        # Message throughput health check
        self.register_health_check(
            name="message_throughput",
            description="Monitor message processing throughput",
            check_function=self._check_message_throughput,
            warning_threshold=10.0,   # messages per second
            critical_threshold=5.0    # messages per second (lower is worse)
        )
        
        # Resource leak detection
        self.register_health_check(
            name="memory_leak_detection",
            description="Detect potential memory leaks",
            check_function=self._check_memory_leaks,
            interval_seconds=300,  # Check every 5 minutes
            enabled=self.leak_detection_enabled
        )
        
        # Connection leak detection
        self.register_health_check(
            name="connection_leak_detection",
            description="Detect connection leaks",
            check_function=self._check_connection_leaks,
            interval_seconds=300
        )
    
    def register_health_check(self, name: str, description: str, check_function: Callable,
                            warning_threshold: Optional[float] = None,
                            critical_threshold: Optional[float] = None,
                            enabled: bool = True, interval_seconds: int = 30,
                            timeout_seconds: int = 10, max_consecutive_failures: int = 3):
        """Register a new health check"""
        health_check = HealthCheck(
            name=name,
            description=description,
            check_function=check_function,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            enabled=enabled,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            max_consecutive_failures=max_consecutive_failures
        )
        
        self.health_checks[name] = health_check
        logger.info(f"Registered health check: {name}")
    
    def unregister_health_check(self, name: str):
        """Unregister a health check"""
        if name in self.health_checks:
            del self.health_checks[name]
            logger.info(f"Unregistered health check: {name}")
    
    def add_alert_callback(self, callback: Callable):
        """Add a callback function for alert notifications"""
        self.alert_callbacks.append(callback)
    
    async def start(self):
        """Start health monitoring"""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Initialize baselines
        await self._initialize_baselines()
        
        logger.info("WebSocket health monitoring started")
    
    async def stop(self):
        """Stop health monitoring"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel tasks
        for task in [self._monitoring_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(self._monitoring_task, self._cleanup_task, return_exceptions=True)
        
        logger.info("WebSocket health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._run_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _run_health_checks(self):
        """Run all enabled health checks"""
        current_time = datetime.utcnow()
        
        for name, health_check in self.health_checks.items():
            if not health_check.enabled:
                continue
            
            # Check if it's time to run this health check
            if (health_check.last_check and 
                (current_time - health_check.last_check).total_seconds() < health_check.interval_seconds):
                continue
            
            try:
                # Run the health check with timeout
                result = await asyncio.wait_for(
                    health_check.check_function(),
                    timeout=health_check.timeout_seconds
                )
                
                await self._process_health_check_result(health_check, result, current_time)
                
            except asyncio.TimeoutError:
                logger.warning(f"Health check {name} timed out")
                await self._process_health_check_failure(health_check, "timeout", current_time)
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                await self._process_health_check_failure(health_check, str(e), current_time)
    
    async def _process_health_check_result(self, health_check: HealthCheck, result: float, check_time: datetime):
        """Process the result of a health check"""
        health_check.last_check = check_time
        health_check.last_value = result
        health_check.consecutive_failures = 0
        
        # Determine status based on thresholds
        if health_check.critical_threshold is not None and result >= health_check.critical_threshold:
            status = HealthStatus.CRITICAL
        elif health_check.warning_threshold is not None and result >= health_check.warning_threshold:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY
        
        # Handle status changes
        if status != health_check.last_status:
            await self._handle_status_change(health_check, status, result)
        
        health_check.last_status = status
    
    async def _process_health_check_failure(self, health_check: HealthCheck, error: str, check_time: datetime):
        """Process a health check failure"""
        health_check.last_check = check_time
        health_check.consecutive_failures += 1
        
        # Trigger alert if consecutive failures exceed threshold
        if health_check.consecutive_failures >= health_check.max_consecutive_failures:
            await self._trigger_alert(
                alert_id=f"{health_check.name}_failure",
                name=f"Health Check Failure: {health_check.name}",
                description=f"Health check {health_check.name} has failed {health_check.consecutive_failures} consecutive times. Last error: {error}",
                severity=AlertSeverity.CRITICAL,
                metadata={"health_check": health_check.name, "error": error, "consecutive_failures": health_check.consecutive_failures}
            )
        
        health_check.last_status = HealthStatus.UNKNOWN
    
    async def _handle_status_change(self, health_check: HealthCheck, new_status: HealthStatus, value: float):
        """Handle health status changes"""
        logger.info(f"Health check {health_check.name} status changed to {new_status.value} (value: {value})")
        
        if new_status == HealthStatus.CRITICAL:
            await self._trigger_alert(
                alert_id=f"{health_check.name}_critical",
                name=f"Critical: {health_check.name}",
                description=f"{health_check.description} is in critical state (value: {value}, threshold: {health_check.critical_threshold})",
                severity=AlertSeverity.CRITICAL,
                metadata={"health_check": health_check.name, "value": value, "threshold": health_check.critical_threshold}
            )
        elif new_status == HealthStatus.WARNING:
            await self._trigger_alert(
                alert_id=f"{health_check.name}_warning",
                name=f"Warning: {health_check.name}",
                description=f"{health_check.description} is in warning state (value: {value}, threshold: {health_check.warning_threshold})",
                severity=AlertSeverity.WARNING,
                metadata={"health_check": health_check.name, "value": value, "threshold": health_check.warning_threshold}
            )
        elif new_status == HealthStatus.HEALTHY:
            # Resolve any existing alerts for this health check
            await self._resolve_alert(f"{health_check.name}_critical")
            await self._resolve_alert(f"{health_check.name}_warning")
    
    async def _trigger_alert(self, alert_id: str, name: str, description: str, 
                           severity: AlertSeverity, metadata: Dict[str, Any] = None):
        """Trigger an alert"""
        # Check if alert already exists and is within cooldown period
        if alert_id in self.active_alerts:
            return
        
        # Check cooldown for similar alerts
        recent_alert = next(
            (alert for alert in self.alert_history[-10:] 
             if alert.id == alert_id and 
             (datetime.utcnow() - alert.triggered_at).total_seconds() < self.alert_cooldown),
            None
        )
        
        if recent_alert:
            logger.debug(f"Alert {alert_id} is in cooldown period")
            return
        
        # Create and store alert
        alert = Alert(
            id=alert_id,
            name=name,
            description=description,
            severity=severity,
            triggered_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Trim alert history
        if len(self.alert_history) > self.max_alert_history:
            self.alert_history = self.alert_history[-self.max_alert_history:]
        
        logger.warning(f"Alert triggered: {name} ({severity.value})")
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    async def _resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved_at = datetime.utcnow()
            alert.status = "resolved"
            
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert resolved: {alert.name}")
    
    async def _initialize_baselines(self):
        """Initialize performance and resource baselines"""
        try:
            # Wait a bit for initial metrics to be collected
            await asyncio.sleep(60)
            
            # Set memory baseline
            if self.metrics.current_system_metrics:
                self.resource_baselines["memory_usage_mb"] = self.metrics.current_system_metrics.memory_usage_mb
            
            # Set performance baselines
            stats = self.metrics.get_summary_stats()
            if stats["total_messages_sent"] > 0:
                uptime_hours = stats["uptime_seconds"] / 3600
                self.performance_baselines["messages_per_hour"] = stats["total_messages_sent"] / max(1, uptime_hours)
            
            logger.info("Initialized health monitoring baselines")
            
        except Exception as e:
            logger.error(f"Error initializing baselines: {e}")
    
    async def _cleanup_loop(self):
        """Cleanup old alerts and data"""
        while self._running:
            try:
                await self._cleanup_old_alerts()
                await asyncio.sleep(3600)  # Run every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    async def _cleanup_old_alerts(self):
        """Clean up old resolved alerts"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Remove old alerts from history
        self.alert_history = [
            alert for alert in self.alert_history
            if alert.triggered_at > cutoff_time or alert.status == "active"
        ]
        
        logger.debug("Cleaned up old alerts")
    
    # Health check implementations
    async def _check_connection_count(self) -> float:
        """Check active connection count"""
        return len(self.metrics.connection_metrics)
    
    async def _check_error_rate(self) -> float:
        """Check error rate"""
        stats = self.metrics.get_summary_stats()
        return stats["error_rate"]
    
    async def _check_average_latency(self) -> float:
        """Check average latency"""
        connection_stats = self.metrics.get_connection_stats()
        return connection_stats.get("average_latency_ms", 0.0)
    
    async def _check_memory_usage(self) -> float:
        """Check memory usage percentage"""
        if self.metrics.current_system_metrics:
            return self.metrics.current_system_metrics.memory_usage_percent
        return 0.0
    
    async def _check_cpu_usage(self) -> float:
        """Check CPU usage percentage"""
        if self.metrics.current_system_metrics:
            return self.metrics.current_system_metrics.cpu_usage
        return 0.0
    
    async def _check_event_queue_size(self) -> float:
        """Check event queue size"""
        # This would need to be implemented based on your event queue implementation
        # For now, return 0 as placeholder
        return 0.0
    
    async def _check_message_throughput(self) -> float:
        """Check message throughput (messages per second)"""
        stats = self.metrics.get_summary_stats()
        if stats["uptime_seconds"] > 0:
            return stats["total_messages_sent"] / stats["uptime_seconds"]
        return 0.0
    
    async def _check_memory_leaks(self) -> float:
        """Check for potential memory leaks"""
        if not self.metrics.current_system_metrics or "memory_usage_mb" not in self.resource_baselines:
            return 0.0
        
        current_memory = self.metrics.current_system_metrics.memory_usage_mb
        baseline_memory = self.resource_baselines["memory_usage_mb"]
        
        # Calculate memory growth percentage
        if baseline_memory > 0:
            growth_percentage = ((current_memory - baseline_memory) / baseline_memory) * 100
            
            # Update baseline periodically (every hour)
            if len(self.metrics.system_metrics_history) > 120:  # 1 hour of data
                recent_avg = sum(m.memory_usage_mb for m in list(self.metrics.system_metrics_history)[-60:]) / 60
                self.resource_baselines["memory_usage_mb"] = recent_avg
            
            return max(0, growth_percentage)
        
        return 0.0
    
    async def _check_connection_leaks(self) -> float:
        """Check for connection leaks"""
        stats = self.metrics.get_summary_stats()
        
        # Check if we have significantly more connections created than closed
        if stats["total_connections_closed"] > 0:
            leak_ratio = (stats["total_connections_created"] - stats["total_connections_closed"]) / stats["total_connections_created"]
            return max(0, leak_ratio * 100)  # Return as percentage
        
        return 0.0
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        overall_status = HealthStatus.HEALTHY
        
        # Determine overall status based on individual health checks
        for health_check in self.health_checks.values():
            if not health_check.enabled:
                continue
            
            if health_check.last_status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                break
            elif health_check.last_status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
        
        return {
            "overall_status": overall_status.value,
            "active_alerts": len(self.active_alerts),
            "health_checks": {
                name: {
                    "status": check.last_status.value,
                    "last_check": check.last_check.isoformat() if check.last_check else None,
                    "last_value": check.last_value,
                    "consecutive_failures": check.consecutive_failures,
                    "enabled": check.enabled
                }
                for name, check in self.health_checks.items()
            },
            "alerts": [
                {
                    "id": alert.id,
                    "name": alert.name,
                    "severity": alert.severity.value,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "status": alert.status
                }
                for alert in self.active_alerts.values()
            ]
        }
    
    def get_health_check_details(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific health check"""
        if name not in self.health_checks:
            return None
        
        health_check = self.health_checks[name]
        
        return {
            "name": health_check.name,
            "description": health_check.description,
            "enabled": health_check.enabled,
            "status": health_check.last_status.value,
            "last_check": health_check.last_check.isoformat() if health_check.last_check else None,
            "last_value": health_check.last_value,
            "warning_threshold": health_check.warning_threshold,
            "critical_threshold": health_check.critical_threshold,
            "consecutive_failures": health_check.consecutive_failures,
            "max_consecutive_failures": health_check.max_consecutive_failures,
            "interval_seconds": health_check.interval_seconds,
            "timeout_seconds": health_check.timeout_seconds
        }


# Global health monitor instance
_websocket_health_monitor = None


def get_websocket_health_monitor() -> WebSocketHealthMonitor:
    """Get the global WebSocket health monitor instance"""
    global _websocket_health_monitor
    if _websocket_health_monitor is None:
        _websocket_health_monitor = WebSocketHealthMonitor()
    return _websocket_health_monitor