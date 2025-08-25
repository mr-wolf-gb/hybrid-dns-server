#!/usr/bin/env python3
"""
Production WebSocket Monitoring Script

Comprehensive production monitoring for WebSocket deployment with real-time metrics,
alerting, resource tracking, and automatic rollback capabilities.
"""

import os
import sys
import asyncio
import json
import time
import signal
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.services.websocket_deployment_monitoring import get_deployment_monitoring_service
from app.config.websocket_monitoring import get_websocket_monitoring_config

logger = get_logger(__name__)


@dataclass
class ProductionMonitoringSession:
    """Production monitoring session information"""
    session_id: str
    started_at: datetime
    started_by: str
    monitoring_level: str
    auto_rollback_enabled: bool
    alert_channels: List[str]
    expected_duration_hours: Optional[int] = None
    ended_at: Optional[datetime] = None
    rollback_triggered: bool = False
    total_alerts: int = 0
    critical_alerts: int = 0


class ProductionWebSocketMonitor:
    """Production-grade WebSocket deployment monitor with comprehensive alerting"""
    
    def __init__(self):
        self.settings = get_settings()
        self.monitoring_config = get_websocket_monitoring_config()
        self.deployment_service = get_deployment_monitoring_service()
        
        self.session: Optional[ProductionMonitoringSession] = None
        self.monitoring_active = False
        self.shutdown_requested = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Monitoring state
        self.last_health_check = None
        self.last_resource_check = None
        self.performance_history = []
        
        # Create monitoring directories
        self.log_dir = Path("logs/websocket_monitoring")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_log_file = self.log_dir / "production_sessions.log"
        self.metrics_log_file = self.log_dir / "production_metrics.log"
        self.alerts_log_file = self.log_dir / "production_alerts.log"
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    async def start_production_monitoring(
        self,
        duration_hours: Optional[int] = None,
        monitoring_level: Optional[str] = None,
        started_by: str = "system"
    ):
        """
        Start comprehensive production monitoring
        
        Args:
            duration_hours: How long to monitor (None for indefinite)
            monitoring_level: Override monitoring level
            started_by: Who started the monitoring session
        """
        try:
            # Create monitoring session
            session_id = f"prod_monitor_{int(time.time())}"
            self.session = ProductionMonitoringSession(
                session_id=session_id,
                started_at=datetime.utcnow(),
                started_by=started_by,
                monitoring_level=monitoring_level or self.monitoring_config.monitoring.monitoring_level.value,
                auto_rollback_enabled=self.monitoring_config.monitoring.alerts.enable_auto_rollback,
                alert_channels=self._get_configured_alert_channels(),
                expected_duration_hours=duration_hours
            )
            
            self.monitoring_active = True
            
            # Log session start
            await self._log_session_event("SESSION_STARTED", {
                "session": asdict(self.session),
                "configuration": {
                    "monitoring_level": self.session.monitoring_level,
                    "auto_rollback": self.session.auto_rollback_enabled,
                    "alert_channels": self.session.alert_channels
                }
            })
            
            print(f"🚀 Starting Production WebSocket Monitoring")
            print(f"Session ID: {session_id}")
            print(f"Started by: {started_by}")
            print(f"Monitoring Level: {self.session.monitoring_level}")
            print(f"Auto-rollback: {'Enabled' if self.session.auto_rollback_enabled else 'Disabled'}")
            print(f"Alert Channels: {', '.join(self.session.alert_channels) if self.session.alert_channels else 'None configured'}")
            if duration_hours:
                print(f"Duration: {duration_hours} hours")
            print("-" * 80)
            
            # Start monitoring components
            await self._start_monitoring_components()
            
            # Main monitoring loop
            await self._run_monitoring_loop(duration_hours)
            
        except Exception as e:
            logger.error(f"Error in production monitoring: {e}")
            print(f"❌ Production monitoring error: {e}")
        finally:
            await self._stop_monitoring_session()
    
    async def _start_monitoring_components(self):
        """Start all monitoring components"""
        try:
            # Start deployment monitoring service
            if not self.deployment_service.monitoring_active:
                asyncio.create_task(self.deployment_service.start_monitoring())
                await asyncio.sleep(2)  # Give it time to start
            
            # Initialize WebSocket metrics if available
            try:
                from app.websocket.metrics_integration import initialize_websocket_metrics
                await initialize_websocket_metrics()
                print("✅ WebSocket metrics system initialized")
            except Exception as e:
                logger.warning(f"Could not initialize WebSocket metrics: {e}")
                print(f"⚠️  WebSocket metrics not available: {e}")
            
            print("✅ Monitoring components started")
            
        except Exception as e:
            logger.error(f"Error starting monitoring components: {e}")
            raise
    
    async def _run_monitoring_loop(self, duration_hours: Optional[int]):
        """Main monitoring loop"""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=duration_hours) if duration_hours else None
        
        config = self.monitoring_config.get_monitoring_config()
        
        try:
            while self.monitoring_active and not self.shutdown_requested:
                # Check if duration exceeded
                if end_time and datetime.utcnow() >= end_time:
                    print("⏰ Monitoring duration completed")
                    break
                
                # Collect and display metrics
                await self._collect_and_display_metrics()
                
                # Perform health checks
                if self._should_perform_health_check():
                    await self._perform_health_checks()
                
                # Perform resource checks
                if self._should_perform_resource_check():
                    await self._perform_resource_checks()
                
                # Check for alerts
                await self._check_and_handle_alerts()
                
                # Sleep until next check
                await asyncio.sleep(config.metrics_collection_interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            print(f"❌ Monitoring loop error: {e}")
    
    async def _collect_and_display_metrics(self):
        """Collect and display current metrics"""
        try:
            # Get deployment status
            deployment_status = self.deployment_service.get_deployment_status()
            
            if deployment_status.get("status") == "no_data":
                print("⏳ Waiting for metrics data...")
                return
            
            latest_metrics = deployment_status.get("latest_metrics", {})
            active_alerts = deployment_status.get("active_alerts", [])
            
            # Display current status
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            migration_mode = latest_metrics.get("migration_mode", "unknown")
            rollout_percentage = latest_metrics.get("rollout_percentage", 0)
            total_connections = latest_metrics.get("total_connections", 0)
            error_rate = latest_metrics.get("error_rate", 0.0)
            success_rate = latest_metrics.get("success_rate", 0.0)
            
            status_line = (
                f"\r⏱️  {timestamp} | "
                f"Mode: {migration_mode} ({rollout_percentage}%) | "
                f"Connections: {total_connections} | "
                f"Success: {success_rate:.1f}% | "
                f"Errors: {error_rate:.1f}%"
            )
            
            if active_alerts:
                status_line += f" | 🚨 Alerts: {len(active_alerts)}"
            
            print(status_line, end="", flush=True)
            
            # Log metrics to file
            await self._log_metrics(latest_metrics)
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    def _should_perform_health_check(self) -> bool:
        """Check if it's time for a health check"""
        if self.last_health_check is None:
            return True
        
        config = self.monitoring_config.get_monitoring_config()
        return (datetime.utcnow() - self.last_health_check).total_seconds() >= config.health_check_interval
    
    def _should_perform_resource_check(self) -> bool:
        """Check if it's time for a resource check"""
        if self.last_resource_check is None:
            return True
        
        config = self.monitoring_config.get_monitoring_config()
        return (datetime.utcnow() - self.last_resource_check).total_seconds() >= config.resource_check_interval
    
    async def _perform_health_checks(self):
        """Perform comprehensive health checks"""
        try:
            self.last_health_check = datetime.utcnow()
            
            # Check WebSocket health if available
            try:
                from app.websocket.health_monitor import get_websocket_health_monitor
                health_monitor = get_websocket_health_monitor()
                health_status = health_monitor.get_health_status()
                
                if health_status.get("overall_status") != "healthy":
                    print(f"\n⚠️  Health issue detected: {health_status.get('overall_status')}")
                    
            except Exception as e:
                logger.debug(f"WebSocket health check not available: {e}")
            
        except Exception as e:
            logger.error(f"Error performing health checks: {e}")
    
    async def _perform_resource_checks(self):
        """Perform resource usage checks"""
        try:
            self.last_resource_check = datetime.utcnow()
            
            # Get system resource usage
            try:
                import psutil
                
                # Memory usage
                memory = psutil.virtual_memory()
                process = psutil.Process()
                process_memory = process.memory_info().rss / 1024 / 1024  # MB
                
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                process_cpu = process.cpu_percent()
                
                config = self.monitoring_config.get_monitoring_config()
                
                # Check thresholds
                if process_memory > config.max_memory_usage_mb:
                    print(f"\n⚠️  High memory usage: {process_memory:.1f}MB (threshold: {config.max_memory_usage_mb}MB)")
                
                if process_cpu > config.max_cpu_usage_percent:
                    print(f"\n⚠️  High CPU usage: {process_cpu:.1f}% (threshold: {config.max_cpu_usage_percent}%)")
                
            except ImportError:
                logger.debug("psutil not available for resource monitoring")
            
        except Exception as e:
            logger.error(f"Error performing resource checks: {e}")
    
    async def _check_and_handle_alerts(self):
        """Check for alerts and handle them"""
        try:
            deployment_status = self.deployment_service.get_deployment_status()
            active_alerts = deployment_status.get("active_alerts", [])
            
            # Update session alert counts
            if self.session:
                self.session.total_alerts = len(self.deployment_service.alert_history)
                self.session.critical_alerts = len([
                    a for a in self.deployment_service.alert_history 
                    if a.severity == "critical"
                ])
            
            # Handle new alerts
            for alert in active_alerts:
                await self._handle_alert(alert)
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def _handle_alert(self, alert: Dict[str, Any]):
        """Handle a specific alert"""
        try:
            alert_id = alert.get("id")
            severity = alert.get("severity", "unknown")
            title = alert.get("title", "Unknown Alert")
            message = alert.get("message", "")
            
            print(f"\n🚨 ALERT [{severity.upper()}]: {title}")
            print(f"   {message}")
            
            # Log alert
            await self._log_alert(alert)
            
            # Check for rollback conditions
            if (severity == "critical" and 
                self.session and 
                self.session.auto_rollback_enabled and
                self.deployment_service.consecutive_failures >= self.monitoring_config.monitoring.alerts.auto_rollback_threshold):
                
                print("🔄 Auto-rollback threshold reached, initiating rollback...")
                await self._trigger_emergency_rollback("Auto-rollback due to critical alerts")
            
        except Exception as e:
            logger.error(f"Error handling alert: {e}")
    
    async def _trigger_emergency_rollback(self, reason: str):
        """Trigger emergency rollback"""
        try:
            print(f"🚨 EMERGENCY ROLLBACK: {reason}")
            
            # Import and execute rollback
            from .rollback_websocket import WebSocketRollbackManager
            
            rollback_manager = WebSocketRollbackManager()
            success = await rollback_manager.emergency_rollback(reason)
            
            if success:
                print("✅ Emergency rollback completed successfully")
                if self.session:
                    self.session.rollback_triggered = True
            else:
                print("❌ Emergency rollback failed")
            
            # Log rollback event
            await self._log_session_event("EMERGENCY_ROLLBACK", {
                "reason": reason,
                "success": success,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error triggering emergency rollback: {e}")
            print(f"❌ Rollback error: {e}")
    
    def _get_configured_alert_channels(self) -> List[str]:
        """Get list of configured alert channels"""
        channels = []
        notification_config = self.monitoring_config.get_notification_config()
        
        if notification_config.webhook_enabled:
            channels.append("webhook")
        if notification_config.email_enabled:
            channels.append("email")
        if notification_config.slack_enabled:
            channels.append("slack")
        if notification_config.file_logging_enabled:
            channels.append("file")
        
        return channels
    
    async def _log_session_event(self, event_type: str, data: Dict[str, Any]):
        """Log session event"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": self.session.session_id if self.session else "unknown",
                "event_type": event_type,
                "data": data
            }
            
            with open(self.session_log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging session event: {e}")
    
    async def _log_metrics(self, metrics: Dict[str, Any]):
        """Log metrics to file"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": self.session.session_id if self.session else "unknown",
                "metrics": metrics
            }
            
            with open(self.metrics_log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging metrics: {e}")
    
    async def _log_alert(self, alert: Dict[str, Any]):
        """Log alert to file"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": self.session.session_id if self.session else "unknown",
                "alert": alert
            }
            
            with open(self.alerts_log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
    
    async def _stop_monitoring_session(self):
        """Stop monitoring session and cleanup"""
        try:
            self.monitoring_active = False
            
            if self.session:
                self.session.ended_at = datetime.utcnow()
                
                # Generate final report
                final_report = await self._generate_final_report()
                
                # Log session end
                await self._log_session_event("SESSION_ENDED", {
                    "session": asdict(self.session),
                    "final_report": final_report
                })
                
                print(f"\n\n📊 MONITORING SESSION COMPLETED")
                print(f"Session ID: {self.session.session_id}")
                print(f"Duration: {(self.session.ended_at - self.session.started_at).total_seconds() / 3600:.2f} hours")
                print(f"Total Alerts: {self.session.total_alerts}")
                print(f"Critical Alerts: {self.session.critical_alerts}")
                print(f"Rollback Triggered: {'Yes' if self.session.rollback_triggered else 'No'}")
                print("-" * 80)
                
                # Display final report summary
                if final_report:
                    health = final_report.get("deployment_health", {})
                    print(f"Final Health Status: {health.get('status', 'unknown')} (Score: {health.get('score', 0)})")
                    
                    recommendations = final_report.get("recommendations", [])
                    if recommendations:
                        print("\nRecommendations:")
                        for rec in recommendations[:3]:  # Show top 3
                            print(f"  • {rec}")
            
            # Stop deployment monitoring service
            if self.deployment_service.monitoring_active:
                self.deployment_service.stop_monitoring()
            
            print("\n✅ Monitoring session ended successfully")
            
        except Exception as e:
            logger.error(f"Error stopping monitoring session: {e}")
    
    async def _generate_final_report(self) -> Dict[str, Any]:
        """Generate final monitoring report"""
        try:
            if not self.session:
                return {}
            
            duration_hours = (self.session.ended_at - self.session.started_at).total_seconds() / 3600
            return self.deployment_service.get_deployment_report(int(duration_hours) + 1)
            
        except Exception as e:
            logger.error(f"Error generating final report: {e}")
            return {"error": str(e)}


async def main():
    """Main function for production monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Production WebSocket Monitoring")
    parser.add_argument(
        "--duration",
        type=int,
        help="Monitoring duration in hours (default: indefinite)"
    )
    parser.add_argument(
        "--level",
        choices=["basic", "standard", "comprehensive", "debug"],
        help="Monitoring level (overrides configuration)"
    )
    parser.add_argument(
        "--started-by",
        default="cli",
        help="Who started the monitoring session"
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Check production readiness and exit"
    )
    
    args = parser.parse_args()
    
    monitor = ProductionWebSocketMonitor()
    
    if args.check_config:
        # Check production readiness
        config = monitor.monitoring_config
        checklist = config.get_production_readiness_checklist()
        
        print("🔍 Production Readiness Check")
        print("=" * 50)
        print(f"Production Ready: {'✅ Yes' if checklist['production_ready'] else '❌ No'}")
        print(f"Monitoring Configured: {'✅' if checklist['monitoring_configured'] else '❌'}")
        print(f"Alerts Configured: {'✅' if checklist['alerts_configured'] else '❌'}")
        print(f"Notifications Configured: {'✅' if checklist['notifications_configured'] else '❌'}")
        
        if checklist['issues']:
            print("\n⚠️  Issues:")
            for issue in checklist['issues']:
                print(f"  • {issue}")
        
        if checklist['recommendations']:
            print("\n💡 Recommendations:")
            for rec in checklist['recommendations']:
                print(f"  • {rec}")
        
        return
    
    # Start production monitoring
    await monitor.start_production_monitoring(
        duration_hours=args.duration,
        monitoring_level=args.level,
        started_by=args.started_by
    )


if __name__ == "__main__":
    asyncio.run(main())