#!/usr/bin/env python3
"""
Production Deployment Monitor

Comprehensive production monitoring system that integrates all monitoring components
for complete WebSocket deployment oversight with automated alerting and reporting.
"""

import asyncio
import json
import signal
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
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
class ProductionMonitoringConfig:
    """Configuration for production monitoring"""
    monitoring_duration_hours: Optional[int] = None
    monitoring_level: str = "standard"
    enable_auto_rollback: bool = True
    enable_alerting: bool = True
    enable_dashboard: bool = True
    report_interval_minutes: int = 30
    health_check_interval_seconds: int = 60
    resource_check_interval_seconds: int = 120
    alert_escalation_minutes: int = 15
    max_consecutive_failures: int = 3


class ProductionDeploymentMonitor:
    """Comprehensive production deployment monitoring system"""
    
    def __init__(self, config: ProductionMonitoringConfig):
        self.config = config
        self.settings = get_settings()
        self.monitoring_config = get_websocket_monitoring_config()
        self.deployment_service = get_deployment_monitoring_service()
        
        self.monitoring_active = False
        self.shutdown_requested = False
        self.start_time = None
        self.last_report_time = None
        self.last_health_check = None
        self.last_resource_check = None
        
        # Monitoring state
        self.monitoring_session_id = f"prod_monitor_{int(datetime.utcnow().timestamp())}"
        self.performance_snapshots = []
        self.resource_snapshots = []
        self.alert_summary = {"total": 0, "critical": 0, "warning": 0, "resolved": 0}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Create monitoring directories
        self.log_dir = Path("logs/production_monitoring")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_log = self.log_dir / f"session_{self.monitoring_session_id}.log"
        self.performance_log = self.log_dir / "performance_snapshots.log"
        self.resource_log = self.log_dir / "resource_snapshots.log"
        self.alerts_log = self.log_dir / "production_alerts.log"
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
    
    async def start_production_monitoring(self):
        """Start comprehensive production monitoring"""
        try:
            self.monitoring_active = True
            self.start_time = datetime.utcnow()
            
            print("🚀 Starting Production Deployment Monitoring")
            print("=" * 80)
            print(f"Session ID: {self.monitoring_session_id}")
            print(f"Start Time: {self.start_time.isoformat()}")
            print(f"Monitoring Level: {self.config.monitoring_level}")
            print(f"Auto-Rollback: {'Enabled' if self.config.enable_auto_rollback else 'Disabled'}")
            print(f"Alerting: {'Enabled' if self.config.enable_alerting else 'Disabled'}")
            
            if self.config.monitoring_duration_hours:
                end_time = self.start_time + timedelta(hours=self.config.monitoring_duration_hours)
                print(f"Duration: {self.config.monitoring_duration_hours} hours (until {end_time.strftime('%H:%M:%S')})")
            else:
                print("Duration: Indefinite (until stopped)")
            
            print("-" * 80)
            
            # Log session start
            await self._log_session_event("MONITORING_SESSION_STARTED", {
                "session_id": self.monitoring_session_id,
                "config": asdict(self.config),
                "monitoring_config": {
                    "level": self.monitoring_config.monitoring.monitoring_level.value,
                    "auto_rollback": self.monitoring_config.monitoring.alerts.enable_auto_rollback
                }
            })
            
            # Start deployment monitoring service if not active
            if not self.deployment_service.monitoring_active:
                print("📊 Starting deployment monitoring service...")
                asyncio.create_task(self.deployment_service.start_monitoring())
                await asyncio.sleep(3)  # Give it time to start
                print("✅ Deployment monitoring service started")
            else:
                print("✅ Deployment monitoring service already active")
            
            # Display initial system status
            await self._display_initial_status()
            
            # Main monitoring loop
            await self._run_monitoring_loop()
            
        except Exception as e:
            logger.error(f"Error in production monitoring: {e}")
            print(f"❌ Production monitoring error: {e}")
        finally:
            await self._stop_production_monitoring()
    
    async def _display_initial_status(self):
        """Display initial system status and readiness check"""
        print("\n🔍 SYSTEM READINESS CHECK")
        print("-" * 50)
        
        # Check production readiness
        readiness = self.monitoring_config.get_production_readiness_checklist()
        
        print(f"Production Ready: {'✅ Yes' if readiness['production_ready'] else '❌ No'}")
        print(f"Monitoring Configured: {'✅' if readiness['monitoring_configured'] else '❌'}")
        print(f"Alerts Configured: {'✅' if readiness['alerts_configured'] else '❌'}")
        print(f"Notifications Configured: {'✅' if readiness['notifications_configured'] else '❌'}")
        
        if readiness['issues']:
            print("\n⚠️  Configuration Issues:")
            for issue in readiness['issues']:
                print(f"  • {issue}")
        
        if readiness['recommendations']:
            print("\n💡 Recommendations:")
            for rec in readiness['recommendations'][:3]:  # Show top 3
                print(f"  • {rec}")
        
        # Get initial deployment status
        deployment_status = self.deployment_service.get_deployment_status()
        
        if deployment_status.get("status") != "no_data":
            latest_metrics = deployment_status.get("latest_metrics", {})
            print(f"\n📊 CURRENT DEPLOYMENT STATUS")
            print("-" * 50)
            print(f"Migration Mode: {latest_metrics.get('migration_mode', 'unknown')}")
            print(f"Rollout Percentage: {latest_metrics.get('rollout_percentage', 0)}%")
            print(f"Total Connections: {latest_metrics.get('total_connections', 0)}")
            print(f"Error Rate: {latest_metrics.get('error_rate', 0):.2f}%")
            print(f"Success Rate: {latest_metrics.get('success_rate', 0):.2f}%")
            
            active_alerts = deployment_status.get("active_alerts", [])
            if active_alerts:
                print(f"Active Alerts: {len(active_alerts)}")
            else:
                print("Active Alerts: None")
        
        print("\n" + "=" * 80)
        print("🔄 Starting monitoring loop...")
    
    async def _run_monitoring_loop(self):
        """Main monitoring loop"""
        try:
            while self.monitoring_active and not self.shutdown_requested:
                current_time = datetime.utcnow()
                
                # Check if monitoring duration exceeded
                if (self.config.monitoring_duration_hours and 
                    current_time >= self.start_time + timedelta(hours=self.config.monitoring_duration_hours)):
                    print("\n⏰ Monitoring duration completed")
                    break
                
                # Perform periodic tasks
                await self._perform_health_checks(current_time)
                await self._perform_resource_checks(current_time)
                await self._generate_periodic_report(current_time)
                await self._check_alert_escalations()
                
                # Display real-time status
                await self._display_realtime_status()
                
                # Sleep until next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            print(f"❌ Monitoring loop error: {e}")
    
    async def _perform_health_checks(self, current_time: datetime):
        """Perform comprehensive health checks"""
        if (self.last_health_check is None or 
            (current_time - self.last_health_check).total_seconds() >= self.config.health_check_interval_seconds):
            
            self.last_health_check = current_time
            
            try:
                # Get deployment status
                deployment_status = self.deployment_service.get_deployment_status()
                
                if deployment_status.get("status") != "no_data":
                    latest_metrics = deployment_status.get("latest_metrics", {})
                    active_alerts = deployment_status.get("active_alerts", [])
                    consecutive_failures = deployment_status.get("consecutive_failures", 0)
                    
                    # Create performance snapshot
                    snapshot = {
                        "timestamp": current_time.isoformat(),
                        "metrics": latest_metrics,
                        "active_alerts_count": len(active_alerts),
                        "consecutive_failures": consecutive_failures,
                        "monitoring_active": deployment_status.get("monitoring_active", False)
                    }
                    
                    self.performance_snapshots.append(snapshot)
                    
                    # Log performance snapshot
                    with open(self.performance_log, "a") as f:
                        f.write(json.dumps(snapshot) + "\n")
                    
                    # Check for critical conditions
                    await self._check_critical_conditions(latest_metrics, active_alerts, consecutive_failures)
                
            except Exception as e:
                logger.error(f"Error performing health checks: {e}")
    
    async def _perform_resource_checks(self, current_time: datetime):
        """Perform resource usage checks"""
        if (self.last_resource_check is None or 
            (current_time - self.last_resource_check).total_seconds() >= self.config.resource_check_interval_seconds):
            
            self.last_resource_check = current_time
            
            try:
                # Get resource usage
                resource_data = await self._get_resource_usage()
                resource_data["timestamp"] = current_time.isoformat()
                
                self.resource_snapshots.append(resource_data)
                
                # Log resource snapshot
                with open(self.resource_log, "a") as f:
                    f.write(json.dumps(resource_data) + "\n")
                
                # Check resource thresholds
                await self._check_resource_thresholds(resource_data)
                
            except Exception as e:
                logger.error(f"Error performing resource checks: {e}")
    
    async def _generate_periodic_report(self, current_time: datetime):
        """Generate periodic monitoring reports"""
        if (self.last_report_time is None or 
            (current_time - self.last_report_time).total_seconds() >= self.config.report_interval_minutes * 60):
            
            self.last_report_time = current_time
            
            try:
                # Generate deployment report
                report = self.deployment_service.get_deployment_report(hours=1)
                
                if "error" not in report:
                    print(f"\n📊 PERIODIC REPORT - {current_time.strftime('%H:%M:%S')}")
                    print("-" * 60)
                    
                    summary = report.get("summary_metrics", {})
                    alerts = report.get("alerts", {})
                    health = report.get("deployment_health", {})
                    
                    print(f"Average Error Rate: {summary.get('average_error_rate', 0):.2f}%")
                    print(f"Average Success Rate: {summary.get('average_success_rate', 0):.2f}%")
                    print(f"Max Connections: {summary.get('max_concurrent_connections', 0)}")
                    print(f"Total Alerts: {alerts.get('total_alerts', 0)} (Critical: {alerts.get('critical_alerts', 0)})")
                    print(f"Deployment Health: {health.get('status', 'unknown')} ({health.get('score', 0)}/100)")
                    
                    recommendations = report.get("recommendations", [])
                    if recommendations:
                        print(f"Top Recommendation: {recommendations[0]}")
                    
                    print("-" * 60)
                
                # Log periodic report
                await self._log_session_event("PERIODIC_REPORT", report)
                
            except Exception as e:
                logger.error(f"Error generating periodic report: {e}")
    
    async def _check_alert_escalations(self):
        """Check for alert escalations"""
        try:
            deployment_status = self.deployment_service.get_deployment_status()
            active_alerts = deployment_status.get("active_alerts", [])
            
            for alert in active_alerts:
                alert_time = datetime.fromisoformat(alert.get("timestamp", datetime.utcnow().isoformat()))
                time_since_alert = (datetime.utcnow() - alert_time).total_seconds() / 60
                
                if (time_since_alert >= self.config.alert_escalation_minutes and 
                    not alert.get("escalated", False) and 
                    alert.get("severity") == "critical"):
                    
                    print(f"\n🚨 ALERT ESCALATION: {alert.get('title', 'Unknown Alert')}")
                    print(f"   Alert has been active for {time_since_alert:.1f} minutes")
                    
                    await self._log_session_event("ALERT_ESCALATION", {
                        "alert_id": alert.get("id"),
                        "title": alert.get("title"),
                        "time_since_alert_minutes": time_since_alert
                    })
        
        except Exception as e:
            logger.error(f"Error checking alert escalations: {e}")
    
    async def _check_critical_conditions(self, metrics: Dict[str, Any], alerts: List[Dict[str, Any]], consecutive_failures: int):
        """Check for critical conditions that may require intervention"""
        critical_conditions = []
        
        # Check error rate
        error_rate = metrics.get("error_rate", 0)
        if error_rate > 10.0:
            critical_conditions.append(f"Extremely high error rate: {error_rate:.1f}%")
        
        # Check success rate
        success_rate = metrics.get("success_rate", 100)
        if success_rate < 90.0:
            critical_conditions.append(f"Very low success rate: {success_rate:.1f}%")
        
        # Check consecutive failures
        if consecutive_failures >= self.config.max_consecutive_failures:
            critical_conditions.append(f"Too many consecutive failures: {consecutive_failures}")
        
        # Check critical alerts
        critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
        if len(critical_alerts) >= 3:
            critical_conditions.append(f"Multiple critical alerts: {len(critical_alerts)}")
        
        # Log critical conditions
        if critical_conditions:
            print(f"\n🚨 CRITICAL CONDITIONS DETECTED:")
            for condition in critical_conditions:
                print(f"   • {condition}")
            
            await self._log_session_event("CRITICAL_CONDITIONS", {
                "conditions": critical_conditions,
                "metrics": metrics,
                "alert_count": len(alerts)
            })
            
            # Consider auto-rollback if enabled
            if (self.config.enable_auto_rollback and 
                consecutive_failures >= self.config.max_consecutive_failures):
                
                print("🔄 Auto-rollback conditions met - triggering emergency rollback...")
                await self._trigger_emergency_rollback(critical_conditions)
    
    async def _check_resource_thresholds(self, resource_data: Dict[str, Any]):
        """Check resource usage against thresholds"""
        warnings = []
        
        # Check memory usage
        process_memory = resource_data.get("process_memory_mb", 0)
        if process_memory > 2048:  # 2GB
            warnings.append(f"High process memory usage: {process_memory:.1f}MB")
        
        system_memory = resource_data.get("system_memory_percent", 0)
        if system_memory > 90:
            warnings.append(f"High system memory usage: {system_memory:.1f}%")
        
        # Check CPU usage
        system_cpu = resource_data.get("system_cpu_percent", 0)
        if system_cpu > 90:
            warnings.append(f"High system CPU usage: {system_cpu:.1f}%")
        
        if warnings:
            print(f"\n⚠️  Resource Warnings:")
            for warning in warnings:
                print(f"   • {warning}")
    
    async def _trigger_emergency_rollback(self, conditions: List[str]):
        """Trigger emergency rollback"""
        try:
            print("🚨 TRIGGERING EMERGENCY ROLLBACK")
            
            # Import and execute rollback
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'websocket'))
            from rollback_websocket import WebSocketRollbackManager
            
            rollback_manager = WebSocketRollbackManager()
            reason = f"Emergency rollback due to critical conditions: {'; '.join(conditions)}"
            
            success = await rollback_manager.emergency_rollback(reason)
            
            if success:
                print("✅ Emergency rollback completed successfully")
                await self._log_session_event("EMERGENCY_ROLLBACK_SUCCESS", {
                    "reason": reason,
                    "conditions": conditions
                })
            else:
                print("❌ Emergency rollback failed")
                await self._log_session_event("EMERGENCY_ROLLBACK_FAILED", {
                    "reason": reason,
                    "conditions": conditions
                })
            
            # Stop monitoring after rollback
            self.shutdown_requested = True
            
        except Exception as e:
            logger.error(f"Error triggering emergency rollback: {e}")
            print(f"❌ Rollback error: {e}")
    
    async def _display_realtime_status(self):
        """Display real-time monitoring status"""
        try:
            deployment_status = self.deployment_service.get_deployment_status()
            
            if deployment_status.get("status") == "no_data":
                print("\r⏳ Waiting for monitoring data...", end="", flush=True)
                return
            
            latest_metrics = deployment_status.get("latest_metrics", {})
            active_alerts = deployment_status.get("active_alerts", [])
            
            # Calculate uptime
            uptime = datetime.utcnow() - self.start_time
            uptime_str = f"{int(uptime.total_seconds() // 3600):02d}:{int((uptime.total_seconds() % 3600) // 60):02d}:{int(uptime.total_seconds() % 60):02d}"
            
            # Format status line
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            migration_mode = latest_metrics.get("migration_mode", "unknown")
            rollout_percentage = latest_metrics.get("rollout_percentage", 0)
            total_connections = latest_metrics.get("total_connections", 0)
            error_rate = latest_metrics.get("error_rate", 0.0)
            success_rate = latest_metrics.get("success_rate", 0.0)
            
            status_line = (
                f"\r🔍 {timestamp} | Uptime: {uptime_str} | "
                f"Mode: {migration_mode} ({rollout_percentage}%) | "
                f"Connections: {total_connections} | "
                f"Success: {success_rate:.1f}% | "
                f"Errors: {error_rate:.1f}%"
            )
            
            if active_alerts:
                critical_count = len([a for a in active_alerts if a.get("severity") == "critical"])
                warning_count = len([a for a in active_alerts if a.get("severity") == "warning"])
                status_line += f" | 🚨 Alerts: {critical_count}C/{warning_count}W"
            
            print(status_line, end="", flush=True)
            
        except Exception as e:
            logger.error(f"Error displaying realtime status: {e}")
    
    async def _get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage"""
        try:
            import psutil
            
            # Process info
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # System info
            system_memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            return {
                "process_memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                "process_memory_percent": round(process.memory_percent(), 2),
                "system_memory_percent": round(system_memory.percent, 2),
                "system_cpu_percent": round(cpu_percent, 2),
                "available_memory_gb": round(system_memory.available / 1024 / 1024 / 1024, 2),
                "process_threads": process.num_threads(),
                "process_connections": len(process.connections())
            }
        except Exception as e:
            logger.debug(f"Could not get resource usage: {e}")
            return {"error": str(e)}
    
    async def _log_session_event(self, event_type: str, data: Dict[str, Any]):
        """Log session events"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": self.monitoring_session_id,
                "event_type": event_type,
                "data": data
            }
            
            with open(self.session_log, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging session event: {e}")
    
    async def _stop_production_monitoring(self):
        """Stop production monitoring and generate final report"""
        try:
            self.monitoring_active = False
            end_time = datetime.utcnow()
            duration = end_time - self.start_time
            
            print(f"\n\n📊 PRODUCTION MONITORING SESSION COMPLETED")
            print("=" * 80)
            print(f"Session ID: {self.monitoring_session_id}")
            print(f"Duration: {duration.total_seconds() / 3600:.2f} hours")
            print(f"Performance Snapshots: {len(self.performance_snapshots)}")
            print(f"Resource Snapshots: {len(self.resource_snapshots)}")
            
            # Generate final comprehensive report
            final_report = await self._generate_final_report(duration)
            
            # Display summary
            if "error" not in final_report:
                summary = final_report.get("session_summary", {})
                health = final_report.get("final_health_assessment", {})
                
                print(f"Final Health Status: {health.get('status', 'unknown')} ({health.get('score', 0)}/100)")
                print(f"Total Alerts Generated: {summary.get('total_alerts', 0)}")
                print(f"Emergency Rollbacks: {summary.get('emergency_rollbacks', 0)}")
                print(f"Average Error Rate: {summary.get('average_error_rate', 0):.2f}%")
                print(f"Average Success Rate: {summary.get('average_success_rate', 0):.2f}%")
                
                recommendations = final_report.get("final_recommendations", [])
                if recommendations:
                    print("\nKey Recommendations:")
                    for i, rec in enumerate(recommendations[:3], 1):
                        print(f"  {i}. {rec}")
            
            # Log session end
            await self._log_session_event("MONITORING_SESSION_COMPLETED", final_report)
            
            # Save final report
            final_report_file = self.log_dir / f"final_report_{self.monitoring_session_id}.json"
            with open(final_report_file, "w") as f:
                json.dump(final_report, f, indent=2)
            
            print(f"\nFinal report saved to: {final_report_file}")
            print("✅ Production monitoring session ended successfully")
            
        except Exception as e:
            logger.error(f"Error stopping production monitoring: {e}")
    
    async def _generate_final_report(self, duration: timedelta) -> Dict[str, Any]:
        """Generate comprehensive final monitoring report"""
        try:
            # Get deployment report for the entire monitoring period
            hours = max(1, int(duration.total_seconds() / 3600) + 1)
            deployment_report = self.deployment_service.get_deployment_report(hours=hours)
            
            # Calculate session statistics
            session_summary = {
                "session_id": self.monitoring_session_id,
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration_hours": duration.total_seconds() / 3600,
                "performance_snapshots": len(self.performance_snapshots),
                "resource_snapshots": len(self.resource_snapshots),
                "monitoring_level": self.config.monitoring_level,
                "auto_rollback_enabled": self.config.enable_auto_rollback
            }
            
            # Calculate averages from snapshots
            if self.performance_snapshots:
                error_rates = [s["metrics"].get("error_rate", 0) for s in self.performance_snapshots if "metrics" in s]
                success_rates = [s["metrics"].get("success_rate", 0) for s in self.performance_snapshots if "metrics" in s]
                
                session_summary.update({
                    "average_error_rate": sum(error_rates) / len(error_rates) if error_rates else 0,
                    "average_success_rate": sum(success_rates) / len(success_rates) if success_rates else 0,
                    "total_alerts": sum(s.get("active_alerts_count", 0) for s in self.performance_snapshots),
                    "max_consecutive_failures": max(s.get("consecutive_failures", 0) for s in self.performance_snapshots)
                })
            
            # Resource usage summary
            resource_summary = {}
            if self.resource_snapshots:
                memory_usage = [r.get("process_memory_mb", 0) for r in self.resource_snapshots if "error" not in r]
                cpu_usage = [r.get("system_cpu_percent", 0) for r in self.resource_snapshots if "error" not in r]
                
                if memory_usage and cpu_usage:
                    resource_summary = {
                        "average_memory_mb": sum(memory_usage) / len(memory_usage),
                        "peak_memory_mb": max(memory_usage),
                        "average_cpu_percent": sum(cpu_usage) / len(cpu_usage),
                        "peak_cpu_percent": max(cpu_usage)
                    }
            
            # Final health assessment
            final_health = {"status": "unknown", "score": 0}
            if "error" not in deployment_report:
                final_health = deployment_report.get("deployment_health", final_health)
            
            # Generate final recommendations
            final_recommendations = self._generate_final_recommendations(deployment_report, session_summary)
            
            return {
                "session_summary": session_summary,
                "deployment_report": deployment_report,
                "resource_summary": resource_summary,
                "final_health_assessment": final_health,
                "final_recommendations": final_recommendations,
                "monitoring_effectiveness": self._assess_monitoring_effectiveness()
            }
            
        except Exception as e:
            logger.error(f"Error generating final report: {e}")
            return {"error": str(e)}
    
    def _generate_final_recommendations(self, deployment_report: Dict[str, Any], session_summary: Dict[str, Any]) -> List[str]:
        """Generate final recommendations based on entire monitoring session"""
        recommendations = []
        
        if "error" in deployment_report:
            recommendations.append("Monitoring data incomplete - extend monitoring duration for better insights")
            return recommendations
        
        # Performance-based recommendations
        avg_error_rate = session_summary.get("average_error_rate", 0)
        avg_success_rate = session_summary.get("average_success_rate", 100)
        
        if avg_error_rate > 5.0:
            recommendations.append("High average error rate indicates system instability - investigate root causes")
        elif avg_error_rate > 2.0:
            recommendations.append("Elevated error rate - monitor closely and consider gradual rollout")
        elif avg_error_rate < 1.0 and avg_success_rate > 99.0:
            recommendations.append("Excellent performance metrics - consider accelerating rollout")
        
        # Alert-based recommendations
        total_alerts = session_summary.get("total_alerts", 0)
        max_failures = session_summary.get("max_consecutive_failures", 0)
        
        if max_failures >= 3:
            recommendations.append("System showed instability with consecutive failures - review deployment strategy")
        
        if total_alerts > 10:
            recommendations.append("High alert volume - review alert thresholds and system stability")
        
        # Health-based recommendations
        health = deployment_report.get("deployment_health", {})
        health_status = health.get("status", "unknown")
        
        if health_status in ["critical", "poor"]:
            recommendations.append("Poor deployment health - consider rollback and system review")
        elif health_status == "fair":
            recommendations.append("Moderate deployment health - proceed with caution")
        elif health_status in ["good", "excellent"]:
            recommendations.append("Good deployment health - continue with planned rollout")
        
        # Duration-based recommendations
        duration_hours = session_summary.get("duration_hours", 0)
        if duration_hours < 2:
            recommendations.append("Short monitoring duration - consider longer monitoring for production deployments")
        
        if not recommendations:
            recommendations.append("System performed well during monitoring - proceed with deployment plan")
        
        return recommendations[:8]  # Limit to top 8 recommendations
    
    def _assess_monitoring_effectiveness(self) -> Dict[str, Any]:
        """Assess the effectiveness of the monitoring session"""
        effectiveness = {
            "data_collection_rate": 0,
            "alert_coverage": "unknown",
            "resource_monitoring": "unavailable",
            "overall_effectiveness": "poor"
        }
        
        # Data collection effectiveness
        expected_snapshots = max(1, (datetime.utcnow() - self.start_time).total_seconds() / 60)  # Expected per minute
        actual_snapshots = len(self.performance_snapshots)
        
        if expected_snapshots > 0:
            effectiveness["data_collection_rate"] = min(100, (actual_snapshots / expected_snapshots) * 100)
        
        # Alert coverage
        if self.config.enable_alerting:
            effectiveness["alert_coverage"] = "enabled"
        else:
            effectiveness["alert_coverage"] = "disabled"
        
        # Resource monitoring
        if self.resource_snapshots and "error" not in self.resource_snapshots[-1]:
            effectiveness["resource_monitoring"] = "available"
        
        # Overall effectiveness
        if (effectiveness["data_collection_rate"] > 80 and 
            effectiveness["alert_coverage"] == "enabled" and
            effectiveness["resource_monitoring"] == "available"):
            effectiveness["overall_effectiveness"] = "excellent"
        elif effectiveness["data_collection_rate"] > 60:
            effectiveness["overall_effectiveness"] = "good"
        elif effectiveness["data_collection_rate"] > 40:
            effectiveness["overall_effectiveness"] = "fair"
        
        return effectiveness


async def main():
    """Main function for production deployment monitoring"""
    parser = argparse.ArgumentParser(description="Production Deployment Monitor")
    parser.add_argument(
        "--duration",
        type=int,
        help="Monitoring duration in hours (default: indefinite)"
    )
    parser.add_argument(
        "--level",
        choices=["basic", "standard", "comprehensive", "debug"],
        default="standard",
        help="Monitoring level"
    )
    parser.add_argument(
        "--disable-auto-rollback",
        action="store_true",
        help="Disable automatic rollback"
    )
    parser.add_argument(
        "--disable-alerting",
        action="store_true",
        help="Disable alerting system"
    )
    parser.add_argument(
        "--report-interval",
        type=int,
        default=30,
        help="Report interval in minutes"
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=3,
        help="Maximum consecutive failures before rollback"
    )
    
    args = parser.parse_args()
    
    # Create monitoring configuration
    config = ProductionMonitoringConfig(
        monitoring_duration_hours=args.duration,
        monitoring_level=args.level,
        enable_auto_rollback=not args.disable_auto_rollback,
        enable_alerting=not args.disable_alerting,
        report_interval_minutes=args.report_interval,
        max_consecutive_failures=args.max_failures
    )
    
    # Start monitoring
    monitor = ProductionDeploymentMonitor(config)
    await monitor.start_production_monitoring()


if __name__ == "__main__":
    asyncio.run(main())