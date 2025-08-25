#!/usr/bin/env python3
"""
Production Monitoring Integration

Comprehensive production monitoring system that integrates all monitoring components
for WebSocket deployment tracking, alerting, and automatic response.
"""

import asyncio
import json
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.services.websocket_deployment_monitoring import get_deployment_monitoring_service
from app.services.websocket_alerting_service import get_websocket_alerting_service
from app.config.websocket_monitoring import get_websocket_monitoring_config

logger = get_logger(__name__)


@dataclass
class ProductionMonitoringConfig:
    """Configuration for production monitoring integration"""
    monitoring_enabled: bool = True
    alerting_enabled: bool = True
    dashboard_enabled: bool = True
    auto_rollback_enabled: bool = True
    metrics_retention_hours: int = 48
    alert_retention_days: int = 14
    health_check_interval: int = 60
    performance_check_interval: int = 30
    resource_check_interval: int = 120


class ProductionMonitoringIntegration:
    """Integrated production monitoring system"""
    
    def __init__(self):
        self.settings = get_settings()
        self.monitoring_config = get_websocket_monitoring_config()
        self.deployment_service = get_deployment_monitoring_service()
        
        # Initialize alerting service
        try:
            self.alerting_service = get_websocket_alerting_service()
        except Exception as e:
            logger.warning(f"Alerting service not available: {e}")
            self.alerting_service = None
        
        self.config = ProductionMonitoringConfig()
        self.monitoring_active = False
        self.shutdown_requested = False
        
        # Monitoring state
        self.last_health_check = None
        self.last_performance_check = None
        self.last_resource_check = None
        
        # Performance tracking
        self.performance_history = []
        self.resource_usage_history = []
        self.user_adoption_history = []
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Create monitoring directories
        self.monitoring_dir = Path("logs/production_monitoring")
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        
        self.performance_log = self.monitoring_dir / "performance_metrics.log"
        self.resource_log = self.monitoring_dir / "resource_usage.log"
        self.adoption_log = self.monitoring_dir / "user_adoption.log"
        self.integration_log = self.monitoring_dir / "integration_events.log"
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    async def start_production_monitoring(self):
        """Start comprehensive production monitoring"""
        try:
            self.monitoring_active = True
            
            print("🚀 Starting Production Monitoring Integration")
            print("=" * 60)
            
            # Log monitoring start
            await self._log_integration_event("PRODUCTION_MONITORING_STARTED", {
                "config": asdict(self.config),
                "monitoring_level": self.monitoring_config.monitoring.monitoring_level.value,
                "alerting_enabled": self.alerting_service is not None
            })
            
            # Start deployment monitoring service
            if self.config.monitoring_enabled and not self.deployment_service.monitoring_active:
                print("📊 Starting deployment monitoring service...")
                asyncio.create_task(self.deployment_service.start_monitoring())
                await asyncio.sleep(2)  # Give it time to start
                print("✅ Deployment monitoring service started")
            
            # Display initial status
            await self._display_startup_status()
            
            # Main monitoring loop
            await self._run_monitoring_loop()
            
        except Exception as e:
            logger.error(f"Error in production monitoring: {e}")
            print(f"❌ Production monitoring error: {e}")
        finally:
            await self._stop_production_monitoring()
    
    async def _display_startup_status(self):
        """Display startup status and configuration"""
        print("\n📋 MONITORING CONFIGURATION")
        print("-" * 40)
        print(f"Monitoring Level: {self.monitoring_config.monitoring.monitoring_level.value}")
        print(f"Deployment Monitoring: {'✅ Enabled' if self.config.monitoring_enabled else '❌ Disabled'}")
        print(f"Alerting System: {'✅ Enabled' if self.alerting_service else '❌ Disabled'}")
        print(f"Auto-Rollback: {'✅ Enabled' if self.config.auto_rollback_enabled else '❌ Disabled'}")
        print(f"Metrics Retention: {self.config.metrics_retention_hours} hours")
        print(f"Alert Retention: {self.config.alert_retention_days} days")
        
        # Check production readiness
        readiness = self.monitoring_config.get_production_readiness_checklist()
        print(f"\n🔍 PRODUCTION READINESS")
        print("-" * 40)
        print(f"Overall Status: {'✅ Ready' if readiness['production_ready'] else '⚠️  Issues Found'}")
        print(f"Monitoring Configured: {'✅' if readiness['monitoring_configured'] else '❌'}")
        print(f"Alerts Configured: {'✅' if readiness['alerts_configured'] else '❌'}")
        print(f"Notifications Configured: {'✅' if readiness['notifications_configured'] else '❌'}")
        
        if readiness['issues']:
            print("\n⚠️  Issues:")
            for issue in readiness['issues']:
                print(f"  • {issue}")
        
        if readiness['recommendations']:
            print("\n💡 Recommendations:")
            for rec in readiness['recommendations'][:3]:  # Show top 3
                print(f"  • {rec}")
        
        print("\n" + "=" * 60)
        print("🔄 Starting monitoring loop...")
    
    async def _run_monitoring_loop(self):
        """Main monitoring loop"""
        try:
            while self.monitoring_active and not self.shutdown_requested:
                current_time = datetime.utcnow()
                
                # Perform health checks
                if self._should_perform_health_check(current_time):
                    await self._perform_health_checks()
                
                # Perform performance checks
                if self._should_perform_performance_check(current_time):
                    await self._perform_performance_checks()
                
                # Perform resource checks
                if self._should_perform_resource_check(current_time):
                    await self._perform_resource_checks()
                
                # Check user adoption trends
                await self._track_user_adoption()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                # Display status update
                await self._display_status_update()
                
                # Sleep until next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            print(f"❌ Monitoring loop error: {e}")
    
    def _should_perform_health_check(self, current_time: datetime) -> bool:
        """Check if it's time for a health check"""
        if self.last_health_check is None:
            return True
        return (current_time - self.last_health_check).total_seconds() >= self.config.health_check_interval
    
    def _should_perform_performance_check(self, current_time: datetime) -> bool:
        """Check if it's time for a performance check"""
        if self.last_performance_check is None:
            return True
        return (current_time - self.last_performance_check).total_seconds() >= self.config.performance_check_interval
    
    def _should_perform_resource_check(self, current_time: datetime) -> bool:
        """Check if it's time for a resource check"""
        if self.last_resource_check is None:
            return True
        return (current_time - self.last_resource_check).total_seconds() >= self.config.resource_check_interval
    
    async def _perform_health_checks(self):
        """Perform comprehensive health checks"""
        try:
            self.last_health_check = datetime.utcnow()
            
            health_status = {
                "timestamp": self.last_health_check.isoformat(),
                "deployment_service_active": self.deployment_service.monitoring_active,
                "alerting_service_active": self.alerting_service is not None,
                "consecutive_failures": self.deployment_service.consecutive_failures,
                "active_alerts": len(self.deployment_service.active_alerts)
            }
            
            # Check WebSocket system health if available
            try:
                from app.websocket.health_monitor import get_websocket_health_monitor
                health_monitor = get_websocket_health_monitor()
                ws_health = health_monitor.get_health_status()
                health_status["websocket_health"] = ws_health
            except Exception as e:
                logger.debug(f"WebSocket health check not available: {e}")
                health_status["websocket_health"] = {"status": "unavailable", "error": str(e)}
            
            # Log health status
            await self._log_integration_event("HEALTH_CHECK", health_status)
            
            # Check for critical health issues
            if health_status["consecutive_failures"] >= 3:
                print(f"\n⚠️  Health Alert: {health_status['consecutive_failures']} consecutive failures detected")
            
            if health_status["active_alerts"] > 5:
                print(f"\n⚠️  Health Alert: {health_status['active_alerts']} active alerts")
            
        except Exception as e:
            logger.error(f"Error performing health checks: {e}")
    
    async def _perform_performance_checks(self):
        """Perform performance monitoring checks"""
        try:
            self.last_performance_check = datetime.utcnow()
            
            # Get deployment status
            deployment_status = self.deployment_service.get_deployment_status()
            
            if deployment_status.get("status") == "no_data":
                return
            
            latest_metrics = deployment_status.get("latest_metrics", {})
            
            performance_data = {
                "timestamp": self.last_performance_check.isoformat(),
                "error_rate": latest_metrics.get("error_rate", 0.0),
                "success_rate": latest_metrics.get("success_rate", 0.0),
                "performance_score": latest_metrics.get("performance_score", 0.0),
                "health_score": latest_metrics.get("health_score", 0.0),
                "total_connections": latest_metrics.get("total_connections", 0),
                "routing_errors": latest_metrics.get("routing_errors", 0),
                "fallback_activations": latest_metrics.get("fallback_activations", 0)
            }
            
            self.performance_history.append(performance_data)
            
            # Log performance data
            with open(self.performance_log, "a") as f:
                f.write(json.dumps(performance_data) + "\n")
            
            # Check for performance degradation
            await self._check_performance_trends()
            
        except Exception as e:
            logger.error(f"Error performing performance checks: {e}")
    
    async def _perform_resource_checks(self):
        """Perform resource usage monitoring"""
        try:
            self.last_resource_check = datetime.utcnow()
            
            resource_data = {
                "timestamp": self.last_resource_check.isoformat()
            }
            
            # Get system resource usage
            try:
                import psutil
                
                # Process-specific resources
                process = psutil.Process()
                resource_data.update({
                    "process_memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                    "process_memory_percent": round(process.memory_percent(), 2),
                    "process_cpu_percent": round(process.cpu_percent(), 2),
                    "process_threads": process.num_threads(),
                    "process_connections": len(process.connections())
                })
                
                # System-wide resources
                memory = psutil.virtual_memory()
                resource_data.update({
                    "system_memory_percent": round(memory.percent, 2),
                    "system_memory_available_gb": round(memory.available / 1024 / 1024 / 1024, 2),
                    "system_cpu_percent": round(psutil.cpu_percent(interval=1), 2),
                    "system_load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                })
                
            except ImportError:
                logger.debug("psutil not available for resource monitoring")
                resource_data["error"] = "psutil not available"
            
            self.resource_usage_history.append(resource_data)
            
            # Log resource data
            with open(self.resource_log, "a") as f:
                f.write(json.dumps(resource_data) + "\n")
            
            # Check for resource issues
            await self._check_resource_thresholds(resource_data)
            
        except Exception as e:
            logger.error(f"Error performing resource checks: {e}")
    
    async def _track_user_adoption(self):
        """Track user adoption metrics"""
        try:
            deployment_status = self.deployment_service.get_deployment_status()
            
            if deployment_status.get("status") == "no_data":
                return
            
            latest_metrics = deployment_status.get("latest_metrics", {})
            
            adoption_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "migration_mode": latest_metrics.get("migration_mode", "unknown"),
                "rollout_percentage": latest_metrics.get("rollout_percentage", 0),
                "user_adoption_rate": latest_metrics.get("user_adoption_rate", 0.0),
                "total_connections": latest_metrics.get("total_connections", 0),
                "unified_connections": latest_metrics.get("unified_connections", 0),
                "legacy_connections": latest_metrics.get("legacy_connections", 0)
            }
            
            self.user_adoption_history.append(adoption_data)
            
            # Log adoption data
            with open(self.adoption_log, "a") as f:
                f.write(json.dumps(adoption_data) + "\n")
            
        except Exception as e:
            logger.error(f"Error tracking user adoption: {e}")
    
    async def _check_performance_trends(self):
        """Check for performance trends and issues"""
        if len(self.performance_history) < 5:
            return
        
        # Get recent performance data
        recent_data = self.performance_history[-5:]
        
        # Check for degrading trends
        error_rates = [d["error_rate"] for d in recent_data]
        success_rates = [d["success_rate"] for d in recent_data]
        
        # Simple trend detection
        if len(error_rates) >= 3:
            if all(error_rates[i] <= error_rates[i+1] for i in range(len(error_rates)-1)):
                if error_rates[-1] > 2.0:  # Error rate increasing and above 2%
                    print(f"\n⚠️  Performance Alert: Error rate trending upward ({error_rates[-1]:.1f}%)")
        
        if len(success_rates) >= 3:
            if all(success_rates[i] >= success_rates[i+1] for i in range(len(success_rates)-1)):
                if success_rates[-1] < 98.0:  # Success rate decreasing and below 98%
                    print(f"\n⚠️  Performance Alert: Success rate trending downward ({success_rates[-1]:.1f}%)")
    
    async def _check_resource_thresholds(self, resource_data: Dict[str, Any]):
        """Check resource usage against thresholds"""
        if "error" in resource_data:
            return
        
        # Check memory usage
        process_memory = resource_data.get("process_memory_mb", 0)
        if process_memory > 1024:  # 1GB
            print(f"\n⚠️  Resource Alert: High memory usage ({process_memory:.1f}MB)")
        
        # Check CPU usage
        process_cpu = resource_data.get("process_cpu_percent", 0)
        if process_cpu > 80:
            print(f"\n⚠️  Resource Alert: High CPU usage ({process_cpu:.1f}%)")
        
        # Check system resources
        system_memory = resource_data.get("system_memory_percent", 0)
        if system_memory > 90:
            print(f"\n⚠️  System Alert: High system memory usage ({system_memory:.1f}%)")
        
        system_cpu = resource_data.get("system_cpu_percent", 0)
        if system_cpu > 90:
            print(f"\n⚠️  System Alert: High system CPU usage ({system_cpu:.1f}%)")
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.config.metrics_retention_hours)
            
            # Clean performance history
            self.performance_history = [
                d for d in self.performance_history
                if datetime.fromisoformat(d["timestamp"]) >= cutoff_time
            ]
            
            # Clean resource usage history
            self.resource_usage_history = [
                d for d in self.resource_usage_history
                if datetime.fromisoformat(d["timestamp"]) >= cutoff_time
            ]
            
            # Clean user adoption history
            self.user_adoption_history = [
                d for d in self.user_adoption_history
                if datetime.fromisoformat(d["timestamp"]) >= cutoff_time
            ]
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    async def _display_status_update(self):
        """Display periodic status update"""
        try:
            deployment_status = self.deployment_service.get_deployment_status()
            
            if deployment_status.get("status") == "no_data":
                print("\r⏳ Waiting for monitoring data...", end="", flush=True)
                return
            
            latest_metrics = deployment_status.get("latest_metrics", {})
            active_alerts = deployment_status.get("active_alerts", [])
            
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            migration_mode = latest_metrics.get("migration_mode", "unknown")
            rollout_percentage = latest_metrics.get("rollout_percentage", 0)
            total_connections = latest_metrics.get("total_connections", 0)
            error_rate = latest_metrics.get("error_rate", 0.0)
            success_rate = latest_metrics.get("success_rate", 0.0)
            
            status_line = (
                f"\r🔍 {timestamp} | "
                f"Mode: {migration_mode} ({rollout_percentage}%) | "
                f"Connections: {total_connections} | "
                f"Success: {success_rate:.1f}% | "
                f"Errors: {error_rate:.1f}%"
            )
            
            if active_alerts:
                critical_alerts = len([a for a in active_alerts if a.get("severity") == "critical"])
                warning_alerts = len([a for a in active_alerts if a.get("severity") == "warning"])
                status_line += f" | 🚨 Alerts: {critical_alerts}C/{warning_alerts}W"
            
            print(status_line, end="", flush=True)
            
        except Exception as e:
            logger.error(f"Error displaying status update: {e}")
    
    async def _log_integration_event(self, event_type: str, data: Dict[str, Any]):
        """Log integration events"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "data": data
            }
            
            with open(self.integration_log, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging integration event: {e}")
    
    async def _stop_production_monitoring(self):
        """Stop production monitoring and cleanup"""
        try:
            self.monitoring_active = False
            
            print(f"\n\n📊 PRODUCTION MONITORING SUMMARY")
            print("=" * 60)
            
            # Generate final summary
            summary = await self._generate_monitoring_summary()
            
            print(f"Monitoring Duration: {summary.get('duration_hours', 0):.2f} hours")
            print(f"Performance Samples: {len(self.performance_history)}")
            print(f"Resource Samples: {len(self.resource_usage_history)}")
            print(f"Adoption Samples: {len(self.user_adoption_history)}")
            
            if summary.get("alerts_summary"):
                alerts = summary["alerts_summary"]
                print(f"Total Alerts: {alerts.get('total', 0)}")
                print(f"Critical Alerts: {alerts.get('critical', 0)}")
                print(f"Warning Alerts: {alerts.get('warning', 0)}")
            
            # Log monitoring stop
            await self._log_integration_event("PRODUCTION_MONITORING_STOPPED", summary)
            
            # Stop deployment monitoring service
            if self.deployment_service.monitoring_active:
                self.deployment_service.stop_monitoring()
            
            print("\n✅ Production monitoring stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping production monitoring: {e}")
    
    async def _generate_monitoring_summary(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring summary"""
        try:
            summary = {
                "monitoring_stopped_at": datetime.utcnow().isoformat(),
                "duration_hours": 0,
                "performance_summary": {},
                "resource_summary": {},
                "adoption_summary": {},
                "alerts_summary": {}
            }
            
            # Calculate duration
            if self.performance_history:
                start_time = datetime.fromisoformat(self.performance_history[0]["timestamp"])
                end_time = datetime.fromisoformat(self.performance_history[-1]["timestamp"])
                summary["duration_hours"] = (end_time - start_time).total_seconds() / 3600
            
            # Performance summary
            if self.performance_history:
                error_rates = [d["error_rate"] for d in self.performance_history]
                success_rates = [d["success_rate"] for d in self.performance_history]
                
                summary["performance_summary"] = {
                    "avg_error_rate": sum(error_rates) / len(error_rates),
                    "max_error_rate": max(error_rates),
                    "avg_success_rate": sum(success_rates) / len(success_rates),
                    "min_success_rate": min(success_rates),
                    "samples": len(self.performance_history)
                }
            
            # Resource summary
            if self.resource_usage_history:
                memory_usage = [d.get("process_memory_mb", 0) for d in self.resource_usage_history if "process_memory_mb" in d]
                cpu_usage = [d.get("process_cpu_percent", 0) for d in self.resource_usage_history if "process_cpu_percent" in d]
                
                if memory_usage and cpu_usage:
                    summary["resource_summary"] = {
                        "avg_memory_mb": sum(memory_usage) / len(memory_usage),
                        "max_memory_mb": max(memory_usage),
                        "avg_cpu_percent": sum(cpu_usage) / len(cpu_usage),
                        "max_cpu_percent": max(cpu_usage),
                        "samples": len(self.resource_usage_history)
                    }
            
            # Adoption summary
            if self.user_adoption_history:
                adoption_rates = [d["user_adoption_rate"] for d in self.user_adoption_history]
                total_connections = [d["total_connections"] for d in self.user_adoption_history]
                
                summary["adoption_summary"] = {
                    "avg_adoption_rate": sum(adoption_rates) / len(adoption_rates),
                    "final_adoption_rate": adoption_rates[-1] if adoption_rates else 0,
                    "max_connections": max(total_connections) if total_connections else 0,
                    "samples": len(self.user_adoption_history)
                }
            
            # Alerts summary
            if self.alerting_service:
                alert_stats = self.alerting_service.get_alert_statistics()
                summary["alerts_summary"] = alert_stats
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating monitoring summary: {e}")
            return {"error": str(e)}


async def main():
    """Main function for production monitoring integration"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Production Monitoring Integration")
    parser.add_argument(
        "--config-check",
        action="store_true",
        help="Check production monitoring configuration and exit"
    )
    parser.add_argument(
        "--disable-alerting",
        action="store_true",
        help="Disable alerting system"
    )
    parser.add_argument(
        "--disable-auto-rollback",
        action="store_true",
        help="Disable automatic rollback"
    )
    
    args = parser.parse_args()
    
    integration = ProductionMonitoringIntegration()
    
    if args.disable_alerting:
        integration.alerting_service = None
        integration.config.alerting_enabled = False
    
    if args.disable_auto_rollback:
        integration.config.auto_rollback_enabled = False
    
    if args.config_check:
        # Check configuration and exit
        readiness = integration.monitoring_config.get_production_readiness_checklist()
        
        print("🔍 Production Monitoring Configuration Check")
        print("=" * 60)
        print(f"Production Ready: {'✅ Yes' if readiness['production_ready'] else '❌ No'}")
        print(f"Monitoring Configured: {'✅' if readiness['monitoring_configured'] else '❌'}")
        print(f"Alerts Configured: {'✅' if readiness['alerts_configured'] else '❌'}")
        print(f"Notifications Configured: {'✅' if readiness['notifications_configured'] else '❌'}")
        
        if readiness['issues']:
            print("\n⚠️  Issues:")
            for issue in readiness['issues']:
                print(f"  • {issue}")
        
        if readiness['recommendations']:
            print("\n💡 Recommendations:")
            for rec in readiness['recommendations']:
                print(f"  • {rec}")
        
        return
    
    # Start production monitoring
    await integration.start_production_monitoring()


if __name__ == "__main__":
    asyncio.run(main())