"""
Integration module for real-time data streaming services
Provides unified initialization and coordination of DNS streaming, system metrics, and critical notifications
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from ..core.logging_config import get_logger
from ..core.config import get_settings
from .realtime_dns_streaming import (
    get_realtime_dns_service, 
    initialize_realtime_dns_service,
    shutdown_realtime_dns_service,
    MetricsCollectionConfig as DNSMetricsConfig
)
from .system_metrics_broadcasting import (
    get_system_metrics_service,
    initialize_system_metrics_service, 
    shutdown_system_metrics_service,
    MetricsCollectionConfig as SystemMetricsConfig
)
from .critical_event_notification import (
    get_critical_notification_service,
    initialize_critical_notification_service,
    shutdown_critical_notification_service
)
from .enhanced_event_service import get_enhanced_event_service
from ..websocket.event_types import EventType, EventPriority, EventSeverity

logger = get_logger(__name__)


class RealtimeStreamingManager:
    """Manager for all real-time streaming services"""
    
    def __init__(self, 
                 dns_config: Optional[DNSMetricsConfig] = None,
                 system_config: Optional[SystemMetricsConfig] = None):
        self.settings = get_settings()
        self.dns_config = dns_config
        self.system_config = system_config
        
        # Service instances
        self.dns_service = None
        self.system_metrics_service = None
        self.critical_notification_service = None
        self.event_service = get_enhanced_event_service()
        
        # Service status
        self.services_running = False
        self.service_status = {
            "dns_streaming": False,
            "system_metrics": False,
            "critical_notifications": False,
            "event_service": False
        }
        
        # Integration tasks
        self._status_monitor_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def start_all_services(self) -> Dict[str, bool]:
        """Start all real-time streaming services"""
        if self.services_running:
            logger.warning("Services already running")
            return self.service_status
        
        logger.info("Starting real-time streaming services...")
        
        try:
            # Start enhanced event service first
            await self.event_service.start()
            self.service_status["event_service"] = True
            logger.info("Enhanced event service started")
            
            # Start DNS streaming service
            try:
                self.dns_service = await initialize_realtime_dns_service()
                self.service_status["dns_streaming"] = True
                logger.info("DNS streaming service started")
            except Exception as e:
                logger.error(f"Failed to start DNS streaming service: {e}")
                self.service_status["dns_streaming"] = False
            
            # Start system metrics service
            try:
                self.system_metrics_service = await initialize_system_metrics_service(self.system_config)
                self.service_status["system_metrics"] = True
                logger.info("System metrics service started")
            except Exception as e:
                logger.error(f"Failed to start system metrics service: {e}")
                self.service_status["system_metrics"] = False
            
            # Start critical notification service
            try:
                self.critical_notification_service = await initialize_critical_notification_service()
                self.service_status["critical_notifications"] = True
                logger.info("Critical notification service started")
            except Exception as e:
                logger.error(f"Failed to start critical notification service: {e}")
                self.service_status["critical_notifications"] = False
            
            # Start integration tasks
            self._status_monitor_task = asyncio.create_task(self._monitor_service_status())
            self._health_check_task = asyncio.create_task(self._perform_health_checks())
            
            self.services_running = True
            
            # Emit service startup event
            await self.event_service.emit_event(
                event_type=EventType.SERVICE_STARTED,
                data={
                    "service": "realtime_streaming_manager",
                    "services_started": self.service_status,
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=EventPriority.NORMAL,
                severity=EventSeverity.INFO
            )
            
            logger.info(f"Real-time streaming services started. Status: {self.service_status}")
            return self.service_status
            
        except Exception as e:
            logger.error(f"Error starting real-time streaming services: {e}")
            await self.stop_all_services()  # Cleanup on failure
            raise
    
    async def stop_all_services(self) -> Dict[str, bool]:
        """Stop all real-time streaming services"""
        if not self.services_running:
            logger.warning("Services not running")
            return self.service_status
        
        logger.info("Stopping real-time streaming services...")
        
        try:
            # Cancel integration tasks
            for task in [self._status_monitor_task, self._health_check_task]:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Stop services in reverse order
            if self.critical_notification_service:
                try:
                    await shutdown_critical_notification_service()
                    self.service_status["critical_notifications"] = False
                    logger.info("Critical notification service stopped")
                except Exception as e:
                    logger.error(f"Error stopping critical notification service: {e}")
            
            if self.system_metrics_service:
                try:
                    await shutdown_system_metrics_service()
                    self.service_status["system_metrics"] = False
                    logger.info("System metrics service stopped")
                except Exception as e:
                    logger.error(f"Error stopping system metrics service: {e}")
            
            if self.dns_service:
                try:
                    await shutdown_realtime_dns_service()
                    self.service_status["dns_streaming"] = False
                    logger.info("DNS streaming service stopped")
                except Exception as e:
                    logger.error(f"Error stopping DNS streaming service: {e}")
            
            # Stop event service last
            try:
                await self.event_service.stop()
                self.service_status["event_service"] = False
                logger.info("Enhanced event service stopped")
            except Exception as e:
                logger.error(f"Error stopping enhanced event service: {e}")
            
            self.services_running = False
            
            logger.info(f"Real-time streaming services stopped. Final status: {self.service_status}")
            return self.service_status
            
        except Exception as e:
            logger.error(f"Error stopping real-time streaming services: {e}")
            raise
    
    async def restart_service(self, service_name: str) -> bool:
        """Restart a specific service"""
        logger.info(f"Restarting service: {service_name}")
        
        try:
            if service_name == "dns_streaming":
                if self.dns_service:
                    await shutdown_realtime_dns_service()
                self.dns_service = await initialize_realtime_dns_service()
                self.service_status["dns_streaming"] = True
                
            elif service_name == "system_metrics":
                if self.system_metrics_service:
                    await shutdown_system_metrics_service()
                self.system_metrics_service = await initialize_system_metrics_service(self.system_config)
                self.service_status["system_metrics"] = True
                
            elif service_name == "critical_notifications":
                if self.critical_notification_service:
                    await shutdown_critical_notification_service()
                self.critical_notification_service = await initialize_critical_notification_service()
                self.service_status["critical_notifications"] = True
                
            elif service_name == "event_service":
                await self.event_service.stop()
                await self.event_service.start()
                self.service_status["event_service"] = True
                
            else:
                logger.error(f"Unknown service: {service_name}")
                return False
            
            # Emit service restart event
            await self.event_service.emit_event(
                event_type=EventType.SERVICE_RESTARTED,
                data={
                    "service": service_name,
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=EventPriority.NORMAL,
                severity=EventSeverity.INFO
            )
            
            logger.info(f"Service {service_name} restarted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error restarting service {service_name}: {e}")
            self.service_status[service_name] = False
            return False
    
    async def _monitor_service_status(self):
        """Monitor service status and emit updates"""
        while self.services_running:
            try:
                # Check service health
                current_status = await self._check_service_health()
                
                # Compare with previous status
                status_changed = False
                for service, status in current_status.items():
                    if self.service_status.get(service) != status:
                        status_changed = True
                        self.service_status[service] = status
                
                # Emit status update if changed
                if status_changed:
                    await self.event_service.emit_event(
                        event_type=EventType.SYSTEM_STATUS,
                        data={
                            "component": "realtime_streaming_services",
                            "services": self.service_status,
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        priority=EventPriority.NORMAL,
                        severity=EventSeverity.INFO
                    )
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in service status monitor: {e}")
                await asyncio.sleep(60)
    
    async def _check_service_health(self) -> Dict[str, bool]:
        """Check health of all services"""
        health_status = {}
        
        try:
            # Check DNS streaming service
            if self.dns_service:
                health_status["dns_streaming"] = self.dns_service._running
            else:
                health_status["dns_streaming"] = False
            
            # Check system metrics service
            if self.system_metrics_service:
                health_status["system_metrics"] = self.system_metrics_service._running
            else:
                health_status["system_metrics"] = False
            
            # Check critical notification service
            if self.critical_notification_service:
                health_status["critical_notifications"] = self.critical_notification_service._running
            else:
                health_status["critical_notifications"] = False
            
            # Check event service
            health_status["event_service"] = self.event_service._running
            
        except Exception as e:
            logger.error(f"Error checking service health: {e}")
        
        return health_status
    
    async def _perform_health_checks(self):
        """Perform periodic health checks and auto-recovery"""
        while self.services_running:
            try:
                # Perform health checks every 5 minutes
                await asyncio.sleep(300)
                
                health_status = await self._check_service_health()
                
                # Check for failed services and attempt recovery
                for service_name, is_healthy in health_status.items():
                    if not is_healthy and self.service_status.get(service_name, False):
                        logger.warning(f"Service {service_name} appears unhealthy, attempting restart")
                        
                        # Emit health alert
                        await self.event_service.emit_event(
                            event_type=EventType.HEALTH_ALERT,
                            data={
                                "service": service_name,
                                "status": "unhealthy",
                                "action": "attempting_restart",
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            priority=EventPriority.HIGH,
                            severity=EventSeverity.WARNING
                        )
                        
                        # Attempt restart
                        restart_success = await self.restart_service(service_name)
                        
                        if restart_success:
                            logger.info(f"Successfully restarted {service_name}")
                        else:
                            logger.error(f"Failed to restart {service_name}")
                            
                            # Emit critical alert for failed restart
                            await self.event_service.emit_event(
                                event_type=EventType.HEALTH_ALERT,
                                data={
                                    "service": service_name,
                                    "status": "failed_restart",
                                    "timestamp": datetime.utcnow().isoformat()
                                },
                                priority=EventPriority.CRITICAL,
                                severity=EventSeverity.CRITICAL
                            )
                
            except Exception as e:
                logger.error(f"Error in health check task: {e}")
                await asyncio.sleep(300)
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current service status"""
        return {
            "services_running": self.services_running,
            "service_status": self.service_status.copy(),
            "dns_service_stats": self.dns_service.get_statistics().to_dict() if self.dns_service else None,
            "system_metrics_stats": {
                "current_system": self.system_metrics_service.get_current_system_metrics().to_dict() if self.system_metrics_service and self.system_metrics_service.get_current_system_metrics() else None,
                "current_bind9": self.system_metrics_service.get_current_bind9_metrics().to_dict() if self.system_metrics_service and self.system_metrics_service.get_current_bind9_metrics() else None
            } if self.system_metrics_service else None,
            "critical_notifications_stats": self.critical_notification_service.get_statistics() if self.critical_notification_service else None,
            "event_service_stats": asyncio.create_task(self.event_service.get_statistics()) if self.event_service else None
        }
    
    async def configure_dns_streaming(self, **config_updates):
        """Configure DNS streaming service"""
        if self.dns_service:
            # Update configuration
            for key, value in config_updates.items():
                if hasattr(self.dns_service, key):
                    setattr(self.dns_service, key, value)
            
            logger.info(f"Updated DNS streaming configuration: {config_updates}")
    
    async def configure_system_metrics(self, config: SystemMetricsConfig):
        """Configure system metrics service"""
        if self.system_metrics_service:
            self.system_metrics_service.update_config(config)
            logger.info("Updated system metrics configuration")
    
    async def configure_critical_notifications(self, **config_updates):
        """Configure critical notification service"""
        if self.critical_notification_service:
            # Update thresholds or other configuration
            for key, value in config_updates.items():
                if hasattr(self.critical_notification_service, key):
                    setattr(self.critical_notification_service, key, value)
            
            logger.info(f"Updated critical notification configuration: {config_updates}")


# Global manager instance
_streaming_manager: Optional[RealtimeStreamingManager] = None


def get_streaming_manager(dns_config: Optional[DNSMetricsConfig] = None,
                         system_config: Optional[SystemMetricsConfig] = None) -> RealtimeStreamingManager:
    """Get the global real-time streaming manager instance"""
    global _streaming_manager
    if _streaming_manager is None:
        _streaming_manager = RealtimeStreamingManager(dns_config, system_config)
    return _streaming_manager


async def initialize_realtime_streaming(dns_config: Optional[DNSMetricsConfig] = None,
                                      system_config: Optional[SystemMetricsConfig] = None) -> RealtimeStreamingManager:
    """Initialize and start all real-time streaming services"""
    manager = get_streaming_manager(dns_config, system_config)
    await manager.start_all_services()
    return manager


async def shutdown_realtime_streaming():
    """Shutdown all real-time streaming services"""
    global _streaming_manager
    if _streaming_manager:
        await _streaming_manager.stop_all_services()
        _streaming_manager = None