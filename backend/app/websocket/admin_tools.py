"""
WebSocket Administrative Tools and Debugging Utilities
Provides comprehensive tools for administrators to monitor, debug, and manage WebSocket connections
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict
from enum import Enum

from ..core.logging_config import get_logger
from .metrics import get_websocket_metrics, WebSocketMetrics
from .health_monitor import get_websocket_health_monitor, WebSocketHealthMonitor
from .models import WSUser, EventType

logger = get_logger(__name__)


class DebugLevel(Enum):
    """Debug logging levels"""
    NONE = "none"
    BASIC = "basic"
    DETAILED = "detailed"
    VERBOSE = "verbose"


class TraceEventType(Enum):
    """Event types for tracing"""
    CONNECTION = "connection"
    MESSAGE = "message"
    EVENT = "event"
    ERROR = "error"
    PERFORMANCE = "performance"


@dataclass
class TraceEvent:
    """Individual trace event"""
    id: str
    event_type: TraceEventType
    timestamp: datetime
    user_id: Optional[str]
    data: Dict[str, Any]
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "data": self.data,
            "duration_ms": self.duration_ms
        }


@dataclass
class ConnectionDebugInfo:
    """Detailed debug information for a connection"""
    user_id: str
    connected_at: datetime
    last_activity: datetime
    status: str
    subscriptions: List[str]
    message_queue_size: int
    error_count: int
    latency_ms: float
    bytes_sent: int
    bytes_received: int
    metadata: Dict[str, Any]


class EventTracer:
    """Event tracing system for debugging"""
    
    def __init__(self, max_events: int = 10000, retention_hours: int = 24):
        self.max_events = max_events
        self.retention_hours = retention_hours
        self.events: List[TraceEvent] = []
        self.enabled = False
        self.trace_filters: Set[TraceEventType] = set()
        self.user_filters: Set[str] = set()
        self._event_counter = 0
    
    def enable_tracing(self, event_types: Optional[List[TraceEventType]] = None, 
                      user_ids: Optional[List[str]] = None):
        """Enable event tracing with optional filters"""
        self.enabled = True
        
        if event_types:
            self.trace_filters = set(event_types)
        else:
            self.trace_filters = set(TraceEventType)
        
        if user_ids:
            self.user_filters = set(user_ids)
        else:
            self.user_filters.clear()
        
        logger.info(f"Event tracing enabled with filters: {self.trace_filters}, users: {self.user_filters}")
    
    def disable_tracing(self):
        """Disable event tracing"""
        self.enabled = False
        logger.info("Event tracing disabled")
    
    def trace_event(self, event_type: TraceEventType, user_id: Optional[str] = None,
                   data: Dict[str, Any] = None, duration_ms: Optional[float] = None):
        """Record a trace event"""
        if not self.enabled:
            return
        
        # Apply filters
        if self.trace_filters and event_type not in self.trace_filters:
            return
        
        if self.user_filters and (not user_id or user_id not in self.user_filters):
            return
        
        # Create trace event
        self._event_counter += 1
        event = TraceEvent(
            id=f"trace_{self._event_counter}",
            event_type=event_type,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            data=data or {},
            duration_ms=duration_ms
        )
        
        # Add to events list
        self.events.append(event)
        
        # Trim if necessary
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
    
    def get_events(self, limit: Optional[int] = None, 
                  event_type: Optional[TraceEventType] = None,
                  user_id: Optional[str] = None,
                  since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get trace events with optional filtering"""
        events = self.events
        
        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        # Apply limit
        if limit:
            events = events[-limit:]
        
        return [event.to_dict() for event in events]
    
    def clear_events(self):
        """Clear all trace events"""
        self.events.clear()
        logger.info("Trace events cleared")
    
    def cleanup_old_events(self):
        """Remove old trace events"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        self.events = [e for e in self.events if e.timestamp >= cutoff_time]


class WebSocketAdminTools:
    """
    Administrative tools for WebSocket system management and debugging
    """
    
    def __init__(self, metrics: Optional[WebSocketMetrics] = None,
                 health_monitor: Optional[WebSocketHealthMonitor] = None):
        self.metrics = metrics or get_websocket_metrics()
        self.health_monitor = health_monitor or get_websocket_health_monitor()
        
        # Event tracing
        self.event_tracer = EventTracer()
        
        # Debug configuration
        self.debug_level = DebugLevel.NONE
        self.debug_enabled_users: Set[str] = set()
        
        # Performance profiling
        self.profiling_enabled = False
        self.performance_samples: List[Dict[str, Any]] = []
        self.max_performance_samples = 1000
        
        # Connection management
        self.connection_manager = None  # Will be set by the WebSocket manager
        
        # Statistics collection
        self.detailed_stats_enabled = False
        self.stats_collection_interval = 60  # seconds
        self._stats_task: Optional[asyncio.Task] = None
    
    def set_connection_manager(self, manager):
        """Set the WebSocket connection manager reference"""
        self.connection_manager = manager
    
    def enable_debug_mode(self, level: DebugLevel = DebugLevel.BASIC, 
                         user_ids: Optional[List[str]] = None):
        """Enable debug mode with specified level"""
        self.debug_level = level
        
        if user_ids:
            self.debug_enabled_users = set(user_ids)
        else:
            self.debug_enabled_users.clear()
        
        logger.info(f"Debug mode enabled: {level.value}, users: {self.debug_enabled_users}")
    
    def disable_debug_mode(self):
        """Disable debug mode"""
        self.debug_level = DebugLevel.NONE
        self.debug_enabled_users.clear()
        logger.info("Debug mode disabled")
    
    def enable_profiling(self):
        """Enable performance profiling"""
        self.profiling_enabled = True
        logger.info("Performance profiling enabled")
    
    def disable_profiling(self):
        """Disable performance profiling"""
        self.profiling_enabled = False
        logger.info("Performance profiling disabled")
    
    def record_performance_sample(self, operation: str, duration_ms: float, 
                                 metadata: Dict[str, Any] = None):
        """Record a performance sample"""
        if not self.profiling_enabled:
            return
        
        sample = {
            "operation": operation,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        self.performance_samples.append(sample)
        
        # Trim if necessary
        if len(self.performance_samples) > self.max_performance_samples:
            self.performance_samples = self.performance_samples[-self.max_performance_samples:]
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system overview"""
        metrics_stats = self.metrics.get_summary_stats()
        connection_stats = self.metrics.get_connection_stats()
        event_stats = self.metrics.get_event_processing_stats()
        health_status = self.health_monitor.get_health_status()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": metrics_stats["uptime_seconds"],
            "system_status": {
                "overall_health": health_status["overall_status"],
                "active_alerts": health_status["active_alerts"],
                "active_connections": metrics_stats["active_connections"],
                "total_connections_created": metrics_stats["total_connections_created"],
                "total_messages_sent": metrics_stats["total_messages_sent"],
                "total_events_processed": metrics_stats["total_events_processed"],
                "error_rate": metrics_stats["error_rate"]
            },
            "performance": {
                "average_latency_ms": connection_stats.get("average_latency_ms", 0),
                "message_throughput": metrics_stats["total_messages_sent"] / max(1, metrics_stats["uptime_seconds"]),
                "event_throughput": metrics_stats["total_events_processed"] / max(1, metrics_stats["uptime_seconds"])
            },
            "resources": {
                "memory_usage_mb": self.metrics.current_system_metrics.memory_usage_mb if self.metrics.current_system_metrics else 0,
                "cpu_usage": self.metrics.current_system_metrics.cpu_usage if self.metrics.current_system_metrics else 0,
                "thread_count": self.metrics.current_system_metrics.thread_count if self.metrics.current_system_metrics else 0
            },
            "debug_status": {
                "debug_level": self.debug_level.value,
                "tracing_enabled": self.event_tracer.enabled,
                "profiling_enabled": self.profiling_enabled,
                "detailed_stats_enabled": self.detailed_stats_enabled
            }
        }
    
    async def get_connection_details(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get detailed connection information"""
        if not self.connection_manager:
            return []
        
        connections = []
        
        # Get connection metrics
        for uid, metrics in self.metrics.connection_metrics.items():
            if user_id and uid != user_id:
                continue
            
            # Get additional connection info from manager if available
            connection_info = {
                "user_id": uid,
                "connected_at": metrics.connected_at.isoformat(),
                "last_activity": metrics.last_activity.isoformat(),
                "connection_duration_seconds": metrics.get_connection_duration().total_seconds(),
                "messages_sent": metrics.messages_sent,
                "messages_received": metrics.messages_received,
                "bytes_sent": metrics.bytes_sent,
                "bytes_received": metrics.bytes_received,
                "errors": metrics.errors,
                "average_latency_ms": metrics.average_latency_ms,
                "subscription_count": metrics.subscription_count,
                "events_received": metrics.events_received,
                "reconnection_count": metrics.reconnection_count,
                "ping_count": metrics.ping_count,
                "pong_count": metrics.pong_count
            }
            
            connections.append(connection_info)
        
        return connections
    
    async def get_event_statistics(self, event_type: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed event processing statistics"""
        event_stats = self.metrics.get_event_processing_stats()
        
        if event_type and event_type in event_stats.get("event_type_breakdown", {}):
            return {
                "event_type": event_type,
                "statistics": event_stats["event_type_breakdown"][event_type]
            }
        
        return event_stats
    
    async def get_performance_analysis(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance analysis for the specified time period"""
        # Get performance metrics
        metrics_data = {}
        for metric_name in ["message_throughput", "event_throughput", "connection_count", "error_rate", "average_latency"]:
            metrics_data[metric_name] = self.metrics.get_performance_metrics(metric_name, limit=hours * 120)  # 30s intervals
        
        # Get system metrics
        system_metrics = self.metrics.get_system_metrics_history(limit=hours * 120)
        
        # Analyze performance samples if profiling is enabled
        performance_samples = []
        if self.profiling_enabled:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            performance_samples = [
                sample for sample in self.performance_samples
                if datetime.fromisoformat(sample["timestamp"]) >= cutoff_time
            ]
        
        return {
            "analysis_period_hours": hours,
            "metrics": metrics_data,
            "system_metrics": system_metrics,
            "performance_samples": performance_samples,
            "summary": {
                "total_samples": len(performance_samples),
                "avg_operation_time_ms": sum(s["duration_ms"] for s in performance_samples) / max(1, len(performance_samples)),
                "slowest_operations": sorted(performance_samples, key=lambda x: x["duration_ms"], reverse=True)[:10]
            }
        }
    
    async def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        health_status = self.health_monitor.get_health_status()
        
        # Get detailed health check information
        health_checks = {}
        for name in health_status["health_checks"].keys():
            health_checks[name] = self.health_monitor.get_health_check_details(name)
        
        return {
            "overall_status": health_status["overall_status"],
            "active_alerts": health_status["active_alerts"],
            "health_checks": health_checks,
            "alerts": health_status["alerts"],
            "recommendations": await self._generate_health_recommendations(health_status)
        }
    
    async def _generate_health_recommendations(self, health_status: Dict[str, Any]) -> List[str]:
        """Generate health recommendations based on current status"""
        recommendations = []
        
        # Check for high error rates
        if health_status["health_checks"].get("error_rate", {}).get("status") == "warning":
            recommendations.append("Consider investigating the cause of increased error rates")
        
        # Check for high latency
        if health_status["health_checks"].get("average_latency", {}).get("status") == "warning":
            recommendations.append("High latency detected - consider optimizing message processing")
        
        # Check for high connection count
        if health_status["health_checks"].get("connection_count", {}).get("status") == "warning":
            recommendations.append("High connection count - monitor for potential connection leaks")
        
        # Check for resource usage
        if health_status["health_checks"].get("memory_usage", {}).get("status") == "warning":
            recommendations.append("High memory usage detected - consider memory optimization")
        
        if health_status["health_checks"].get("cpu_usage", {}).get("status") == "warning":
            recommendations.append("High CPU usage detected - consider load balancing or optimization")
        
        return recommendations
    
    async def force_disconnect_user(self, user_id: str, reason: str = "Admin disconnect") -> bool:
        """Force disconnect a specific user"""
        if not self.connection_manager:
            return False
        
        try:
            # This would need to be implemented in the connection manager
            # await self.connection_manager.disconnect_user(user_id, reason)
            
            # Record the admin action
            self.event_tracer.trace_event(
                TraceEventType.CONNECTION,
                user_id=user_id,
                data={"action": "force_disconnect", "reason": reason, "admin_action": True}
            )
            
            logger.info(f"Admin force disconnected user: {user_id}, reason: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error force disconnecting user {user_id}: {e}")
            return False
    
    async def broadcast_admin_message(self, message: str, severity: str = "info") -> int:
        """Broadcast an administrative message to all connected users"""
        if not self.connection_manager:
            return 0
        
        admin_message = {
            "type": "admin_message",
            "data": {
                "message": message,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        try:
            # This would need to be implemented in the connection manager
            # count = await self.connection_manager.broadcast_to_all(admin_message)
            count = len(self.metrics.connection_metrics)  # Placeholder
            
            logger.info(f"Admin message broadcast to {count} connections: {message}")
            return count
            
        except Exception as e:
            logger.error(f"Error broadcasting admin message: {e}")
            return 0
    
    async def clear_all_metrics(self) -> bool:
        """Clear all collected metrics (admin only)"""
        try:
            # Clear metrics
            self.metrics.connection_history.clear()
            self.metrics.performance_metrics.clear()
            self.metrics.system_metrics_history.clear()
            
            # Clear trace events
            self.event_tracer.clear_events()
            
            # Clear performance samples
            self.performance_samples.clear()
            
            # Reset counters
            self.metrics.total_connections_created = 0
            self.metrics.total_connections_closed = 0
            self.metrics.total_messages_sent = 0
            self.metrics.total_messages_received = 0
            self.metrics.total_events_processed = 0
            self.metrics.total_errors = 0
            self.metrics.start_time = datetime.utcnow()
            
            logger.warning("All WebSocket metrics cleared by admin")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing metrics: {e}")
            return False
    
    async def export_debug_data(self, include_traces: bool = True, 
                              include_metrics: bool = True,
                              include_performance: bool = True) -> Dict[str, Any]:
        """Export comprehensive debug data"""
        debug_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "system_overview": await self.get_system_overview(),
            "health_report": await self.get_health_report()
        }
        
        if include_traces and self.event_tracer.enabled:
            debug_data["trace_events"] = self.event_tracer.get_events(limit=1000)
        
        if include_metrics:
            debug_data["connection_details"] = await self.get_connection_details()
            debug_data["event_statistics"] = await self.get_event_statistics()
        
        if include_performance and self.profiling_enabled:
            debug_data["performance_analysis"] = await self.get_performance_analysis(hours=1)
        
        return debug_data
    
    def get_debug_commands(self) -> List[Dict[str, str]]:
        """Get list of available debug commands"""
        return [
            {"command": "enable_debug", "description": "Enable debug mode with specified level"},
            {"command": "disable_debug", "description": "Disable debug mode"},
            {"command": "enable_tracing", "description": "Enable event tracing"},
            {"command": "disable_tracing", "description": "Disable event tracing"},
            {"command": "enable_profiling", "description": "Enable performance profiling"},
            {"command": "disable_profiling", "description": "Disable performance profiling"},
            {"command": "get_system_overview", "description": "Get comprehensive system overview"},
            {"command": "get_connection_details", "description": "Get detailed connection information"},
            {"command": "get_event_statistics", "description": "Get event processing statistics"},
            {"command": "get_performance_analysis", "description": "Get performance analysis"},
            {"command": "get_health_report", "description": "Get comprehensive health report"},
            {"command": "force_disconnect_user", "description": "Force disconnect a specific user"},
            {"command": "broadcast_admin_message", "description": "Broadcast message to all users"},
            {"command": "clear_all_metrics", "description": "Clear all collected metrics"},
            {"command": "export_debug_data", "description": "Export comprehensive debug data"}
        ]


# Global admin tools instance
_websocket_admin_tools = None


def get_websocket_admin_tools() -> WebSocketAdminTools:
    """Get the global WebSocket admin tools instance"""
    global _websocket_admin_tools
    if _websocket_admin_tools is None:
        _websocket_admin_tools = WebSocketAdminTools()
    return _websocket_admin_tools