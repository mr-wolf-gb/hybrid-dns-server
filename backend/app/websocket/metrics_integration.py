"""
WebSocket Metrics Integration
Integrates the metrics system with the unified WebSocket manager and other components
"""

import asyncio
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from functools import wraps

from ..core.logging_config import get_logger
from .metrics import get_websocket_metrics
from .health_monitor import get_websocket_health_monitor
from .admin_tools import get_websocket_admin_tools, TraceEventType

logger = get_logger(__name__)


class MetricsIntegration:
    """
    Integration layer between WebSocket components and metrics system
    """
    
    def __init__(self):
        self.metrics = get_websocket_metrics()
        self.health_monitor = get_websocket_health_monitor()
        self.admin_tools = get_websocket_admin_tools()
        self._initialized = False
    
    async def initialize(self):
        """Initialize metrics integration"""
        if self._initialized:
            return
        
        # Start metrics collection
        await self.metrics.start()
        
        # Start health monitoring
        await self.health_monitor.start()
        
        # Set up admin tools connection manager reference
        # This will be set by the WebSocket manager when it's created
        
        self._initialized = True
        logger.info("WebSocket metrics integration initialized")
    
    async def shutdown(self):
        """Shutdown metrics integration"""
        if not self._initialized:
            return
        
        await self.metrics.stop()
        await self.health_monitor.stop()
        
        self._initialized = False
        logger.info("WebSocket metrics integration shutdown")
    
    def set_connection_manager(self, manager):
        """Set the connection manager reference for admin tools"""
        self.admin_tools.set_connection_manager(manager)
    
    # Connection lifecycle events
    def on_connection_created(self, user_id: str, client_ip: str = None):
        """Record connection creation"""
        self.metrics.record_connection_created(user_id)
        
        # Trace event
        self.admin_tools.event_tracer.trace_event(
            TraceEventType.CONNECTION,
            user_id=user_id,
            data={"action": "connected", "client_ip": client_ip}
        )
    
    def on_connection_closed(self, user_id: str, reason: str = "unknown"):
        """Record connection closure"""
        self.metrics.record_connection_closed(user_id, reason)
        
        # Trace event
        self.admin_tools.event_tracer.trace_event(
            TraceEventType.CONNECTION,
            user_id=user_id,
            data={"action": "disconnected", "reason": reason}
        )
    
    def on_message_sent(self, user_id: str, message: Dict[str, Any]):
        """Record message sent"""
        message_size = len(json.dumps(message, default=str))
        self.metrics.record_message_sent(user_id, message_size)
        
        # Trace event
        if self.admin_tools.debug_level.value != "none":
            self.admin_tools.event_tracer.trace_event(
                TraceEventType.MESSAGE,
                user_id=user_id,
                data={"action": "sent", "type": message.get("type"), "size_bytes": message_size}
            )
    
    def on_message_received(self, user_id: str, message: Dict[str, Any]):
        """Record message received"""
        message_size = len(json.dumps(message, default=str))
        self.metrics.record_message_received(user_id, message_size)
        
        # Trace event
        if self.admin_tools.debug_level.value != "none":
            self.admin_tools.event_tracer.trace_event(
                TraceEventType.MESSAGE,
                user_id=user_id,
                data={"action": "received", "type": message.get("type"), "size_bytes": message_size}
            )
    
    def on_event_processed(self, event_type: str, processing_time_ms: float, success: bool = True, user_id: str = None):
        """Record event processing"""
        self.metrics.record_event_processed(event_type, processing_time_ms, success)
        
        # Trace event
        self.admin_tools.event_tracer.trace_event(
            TraceEventType.EVENT,
            user_id=user_id,
            data={
                "event_type": event_type,
                "success": success,
                "processing_time_ms": processing_time_ms
            },
            duration_ms=processing_time_ms
        )
        
        # Record performance sample
        self.admin_tools.record_performance_sample(
            f"event_processing_{event_type}",
            processing_time_ms,
            {"success": success, "user_id": user_id}
        )
    
    def on_connection_error(self, user_id: str, error_type: str, error_details: str = None):
        """Record connection error"""
        self.metrics.record_connection_error(user_id, error_type)
        
        # Trace event
        self.admin_tools.event_tracer.trace_event(
            TraceEventType.ERROR,
            user_id=user_id,
            data={
                "error_type": error_type,
                "error_details": error_details,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def on_ping_pong(self, user_id: str, latency_ms: float, is_pong: bool = False):
        """Record ping/pong metrics"""
        self.metrics.record_ping_pong(user_id, latency_ms, is_pong)
        
        # Record performance sample for latency
        if is_pong:
            self.admin_tools.record_performance_sample(
                "websocket_latency",
                latency_ms,
                {"user_id": user_id}
            )
    
    def on_subscription_change(self, user_id: str, subscription_count: int, added: List[str] = None, removed: List[str] = None):
        """Record subscription changes"""
        self.metrics.record_subscription_change(user_id, subscription_count)
        
        # Trace event
        self.admin_tools.event_tracer.trace_event(
            TraceEventType.EVENT,
            user_id=user_id,
            data={
                "action": "subscription_change",
                "subscription_count": subscription_count,
                "added": added or [],
                "removed": removed or []
            }
        )
    
    def on_event_received(self, user_id: str, event_type: str):
        """Record event received by connection"""
        self.metrics.record_event_received(user_id)
        
        # Trace event for detailed debugging
        if self.admin_tools.debug_level.value in ["detailed", "verbose"]:
            self.admin_tools.event_tracer.trace_event(
                TraceEventType.EVENT,
                user_id=user_id,
                data={"action": "event_received", "event_type": event_type}
            )
    
    def on_reconnection(self, user_id: str):
        """Record reconnection attempt"""
        self.metrics.record_reconnection(user_id)
        
        # Trace event
        self.admin_tools.event_tracer.trace_event(
            TraceEventType.CONNECTION,
            user_id=user_id,
            data={"action": "reconnection"}
        )


# Decorator for automatic metrics collection
def collect_metrics(operation_name: str, record_performance: bool = True):
    """Decorator to automatically collect metrics for WebSocket operations"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                # Get metrics integration instance
                integration = get_metrics_integration()
                
                # Record event processing
                integration.on_event_processed(
                    operation_name,
                    duration_ms,
                    success,
                    user_id=kwargs.get('user_id') or (args[1] if len(args) > 1 and hasattr(args[1], 'username') else None)
                )
                
                # Record performance sample
                if record_performance:
                    integration.admin_tools.record_performance_sample(
                        operation_name,
                        duration_ms,
                        {"success": success, "error": error}
                    )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                # Get metrics integration instance
                integration = get_metrics_integration()
                
                # Record performance sample
                if record_performance:
                    integration.admin_tools.record_performance_sample(
                        operation_name,
                        duration_ms,
                        {"success": success, "error": error}
                    )
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Context manager for operation timing
class MetricsTimer:
    """Context manager for timing operations and recording metrics"""
    
    def __init__(self, operation_name: str, user_id: str = None, metadata: Dict[str, Any] = None):
        self.operation_name = operation_name
        self.user_id = user_id
        self.metadata = metadata or {}
        self.start_time = None
        self.integration = get_metrics_integration()
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        duration_ms = (end_time - self.start_time) * 1000
        success = exc_type is None
        
        # Record metrics
        self.integration.on_event_processed(
            self.operation_name,
            duration_ms,
            success,
            self.user_id
        )
        
        # Record performance sample
        self.integration.admin_tools.record_performance_sample(
            self.operation_name,
            duration_ms,
            {**self.metadata, "success": success, "error": str(exc_val) if exc_val else None}
        )
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        duration_ms = (end_time - self.start_time) * 1000
        success = exc_type is None
        
        # Record metrics
        self.integration.on_event_processed(
            self.operation_name,
            duration_ms,
            success,
            self.user_id
        )
        
        # Record performance sample
        self.integration.admin_tools.record_performance_sample(
            self.operation_name,
            duration_ms,
            {**self.metadata, "success": success, "error": str(exc_val) if exc_val else None}
        )


# Global metrics integration instance
_metrics_integration = None


def get_metrics_integration() -> MetricsIntegration:
    """Get the global metrics integration instance"""
    global _metrics_integration
    if _metrics_integration is None:
        _metrics_integration = MetricsIntegration()
    return _metrics_integration


# Utility functions for easy metrics collection
async def record_websocket_operation(operation_name: str, user_id: str = None, 
                                   duration_ms: float = None, success: bool = True,
                                   metadata: Dict[str, Any] = None):
    """Record a WebSocket operation for metrics"""
    integration = get_metrics_integration()
    
    if duration_ms is not None:
        integration.on_event_processed(operation_name, duration_ms, success, user_id)
    
    if metadata:
        integration.admin_tools.record_performance_sample(
            operation_name,
            duration_ms or 0,
            {**metadata, "success": success, "user_id": user_id}
        )


def trace_websocket_event(event_type: TraceEventType, user_id: str = None, 
                         data: Dict[str, Any] = None, duration_ms: float = None):
    """Trace a WebSocket event for debugging"""
    integration = get_metrics_integration()
    integration.admin_tools.event_tracer.trace_event(event_type, user_id, data, duration_ms)


async def initialize_websocket_metrics():
    """Initialize WebSocket metrics system"""
    integration = get_metrics_integration()
    await integration.initialize()
    logger.info("WebSocket metrics system initialized")


async def shutdown_websocket_metrics():
    """Shutdown WebSocket metrics system"""
    integration = get_metrics_integration()
    await integration.shutdown()
    logger.info("WebSocket metrics system shutdown")