#!/usr/bin/env python3
"""
WebSocket Deployment Monitoring Script

This script monitors the WebSocket system deployment and can automatically
trigger rollbacks based on error rates and performance metrics.
"""

import os
import sys
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.core.feature_flags import get_websocket_feature_flags
from app.websocket.router import get_websocket_router

logger = get_logger(__name__)


@dataclass
class MonitoringThresholds:
    """Thresholds for automatic rollback triggers"""
    max_error_rate: float = 5.0  # Maximum error rate percentage
    max_routing_errors: int = 50  # Maximum routing errors in monitoring window
    max_fallback_rate: float = 10.0  # Maximum fallback activation rate percentage
    min_success_rate: float = 95.0  # Minimum connection success rate
    monitoring_window_minutes: int = 5  # Monitoring window in minutes
    consecutive_failures_threshold: int = 3  # Consecutive monitoring failures before rollback


@dataclass
class MonitoringMetrics:
    """Metrics collected during monitoring"""
    timestamp: datetime
    legacy_connections: int
    unified_connections: int
    routing_errors: int
    fallback_activations: int
    total_connections: int
    error_rate: float
    fallback_rate: float
    success_rate: float
    migration_mode: str
    rollout_percentage: int


class WebSocketDeploymentMonitor:
    """Monitors WebSocket deployment and triggers rollbacks when needed"""
    
    def __init__(self, thresholds: Optional[MonitoringThresholds] = None):
        self.settings = get_settings()
        self.feature_flags = get_websocket_feature_flags()
        self.router = get_websocket_router()
        self.thresholds = thresholds or MonitoringThresholds()
        
        self.metrics_history: List[MonitoringMetrics] = []
        self.consecutive_failures = 0
        self.monitoring_active = False
        self.rollback_triggered = False
        
        # Create monitoring log file
        self.log_file = Path("websocket_deployment_monitor.log")
    
    async def start_monitoring(self, duration_minutes: Optional[int] = None):
        """
        Start monitoring the WebSocket deployment
        
        Args:
            duration_minutes: How long to monitor (None for indefinite)
        """
        self.monitoring_active = True
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=duration_minutes) if duration_minutes else None
        
        print(f"🔍 Starting WebSocket deployment monitoring")
        print(f"Start time: {start_time.isoformat()}")
        if end_time:
            print(f"End time: {end_time.isoformat()}")
        print(f"Monitoring window: {self.thresholds.monitoring_window_minutes} minutes")
        print("-" * 60)
        
        self._log_event("MONITORING_STARTED", {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else None,
            "thresholds": asdict(self.thresholds)
        })
        
        try:
            while self.monitoring_active:
                if end_time and datetime.utcnow() >= end_time:
                    print("⏰ Monitoring duration completed")
                    break
                
                # Collect metrics
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Analyze metrics and check for rollback conditions
                rollback_needed = await self._analyze_metrics(metrics)
                
                if rollback_needed and not self.rollback_triggered:
                    print("🚨 AUTOMATIC ROLLBACK TRIGGERED!")
                    await self._trigger_automatic_rollback(metrics)
                    break
                
                # Display current status
                self._display_status(metrics)
                
                # Clean up old metrics (keep only monitoring window)
                self._cleanup_old_metrics()
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
            logger.error(f"Monitoring error: {e}")
        finally:
            self.monitoring_active = False
            self._log_event("MONITORING_STOPPED", {
                "end_time": datetime.utcnow().isoformat(),
                "rollback_triggered": self.rollback_triggered
            })
    
    async def _collect_metrics(self) -> MonitoringMetrics:
        """Collect current WebSocket system metrics"""
        try:
            # Get connection statistics
            stats = self.router.get_connection_stats()
            router_stats = stats.get("router_stats", {})
            rollout_stats = stats.get("feature_flags", {})
            
            legacy_connections = router_stats.get("legacy_connections", 0)
            unified_connections = router_stats.get("unified_connections", 0)
            routing_errors = router_stats.get("routing_errors", 0)
            fallback_activations = router_stats.get("fallback_activations", 0)
            
            total_connections = legacy_connections + unified_connections
            
            # Calculate rates
            error_rate = 0.0
            fallback_rate = 0.0
            success_rate = 100.0
            
            if total_connections > 0:
                error_rate = (routing_errors / total_connections) * 100
                fallback_rate = (fallback_activations / total_connections) * 100
                success_rate = 100.0 - error_rate
            
            return MonitoringMetrics(
                timestamp=datetime.utcnow(),
                legacy_connections=legacy_connections,
                unified_connections=unified_connections,
                routing_errors=routing_errors,
                fallback_activations=fallback_activations,
                total_connections=total_connections,
                error_rate=error_rate,
                fallback_rate=fallback_rate,
                success_rate=success_rate,
                migration_mode=rollout_stats.get("migration_mode", "unknown"),
                rollout_percentage=rollout_stats.get("rollout_percentage", 0)
            )
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            # Return empty metrics on error
            return MonitoringMetrics(
                timestamp=datetime.utcnow(),
                legacy_connections=0,
                unified_connections=0,
                routing_errors=0,
                fallback_activations=0,
                total_connections=0,
                error_rate=0.0,
                fallback_rate=0.0,
                success_rate=0.0,
                migration_mode="error",
                rollout_percentage=0
            )
    
    async def _analyze_metrics(self, current_metrics: MonitoringMetrics) -> bool:
        """
        Analyze metrics to determine if rollback is needed
        
        Args:
            current_metrics: Current metrics
            
        Returns:
            True if rollback should be triggered
        """
        rollback_reasons = []
        
        # Check error rate threshold
        if current_metrics.error_rate > self.thresholds.max_error_rate:
            rollback_reasons.append(f"Error rate too high: {current_metrics.error_rate:.1f}% > {self.thresholds.max_error_rate}%")
        
        # Check routing errors threshold
        if current_metrics.routing_errors > self.thresholds.max_routing_errors:
            rollback_reasons.append(f"Too many routing errors: {current_metrics.routing_errors} > {self.thresholds.max_routing_errors}")
        
        # Check fallback rate threshold
        if current_metrics.fallback_rate > self.thresholds.max_fallback_rate:
            rollback_reasons.append(f"Fallback rate too high: {current_metrics.fallback_rate:.1f}% > {self.thresholds.max_fallback_rate}%")
        
        # Check success rate threshold
        if current_metrics.success_rate < self.thresholds.min_success_rate:
            rollback_reasons.append(f"Success rate too low: {current_metrics.success_rate:.1f}% < {self.thresholds.min_success_rate}%")
        
        # Check for consecutive failures
        if rollback_reasons:
            self.consecutive_failures += 1
            print(f"⚠️  Issues detected ({self.consecutive_failures}/{self.thresholds.consecutive_failures_threshold}):")
            for reason in rollback_reasons:
                print(f"   - {reason}")
        else:
            self.consecutive_failures = 0
        
        # Trigger rollback if consecutive failures threshold reached
        if self.consecutive_failures >= self.thresholds.consecutive_failures_threshold:
            self._log_event("ROLLBACK_TRIGGERED", {
                "reasons": rollback_reasons,
                "consecutive_failures": self.consecutive_failures,
                "metrics": asdict(current_metrics)
            })
            return True
        
        return False
    
    async def _trigger_automatic_rollback(self, metrics: MonitoringMetrics):
        """Trigger automatic rollback to legacy system"""
        self.rollback_triggered = True
        
        try:
            print("🔄 Executing automatic rollback...")
            
            # Import rollback manager
            from .rollback_websocket import WebSocketRollbackManager
            
            rollback_manager = WebSocketRollbackManager()
            success = await rollback_manager.emergency_rollback(
                f"Automatic rollback due to monitoring thresholds exceeded at {datetime.utcnow().isoformat()}"
            )
            
            if success:
                print("✅ Automatic rollback completed successfully")
                self._log_event("ROLLBACK_COMPLETED", {
                    "success": True,
                    "trigger_metrics": asdict(metrics)
                })
            else:
                print("❌ Automatic rollback failed")
                self._log_event("ROLLBACK_FAILED", {
                    "success": False,
                    "trigger_metrics": asdict(metrics)
                })
                
        except Exception as e:
            print(f"❌ Error during automatic rollback: {e}")
            logger.error(f"Automatic rollback error: {e}")
            self._log_event("ROLLBACK_ERROR", {
                "error": str(e),
                "trigger_metrics": asdict(metrics)
            })
    
    def _display_status(self, metrics: MonitoringMetrics):
        """Display current monitoring status"""
        print(f"\r⏱️  {metrics.timestamp.strftime('%H:%M:%S')} | "
              f"Connections: L{metrics.legacy_connections} U{metrics.unified_connections} | "
              f"Errors: {metrics.routing_errors} ({metrics.error_rate:.1f}%) | "
              f"Fallbacks: {metrics.fallback_activations} ({metrics.fallback_rate:.1f}%) | "
              f"Success: {metrics.success_rate:.1f}% | "
              f"Mode: {metrics.migration_mode} ({metrics.rollout_percentage}%)", end="")
        
        if self.consecutive_failures > 0:
            print(f" | ⚠️  Failures: {self.consecutive_failures}", end="")
        
        print("", flush=True)
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than the monitoring window"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.thresholds.monitoring_window_minutes)
        self.metrics_history = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log monitoring events to file"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "data": data
            }
            
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging event: {e}")
    
    async def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        if not self.metrics_history:
            return {"error": "No metrics collected"}
        
        # Calculate summary statistics
        total_metrics = len(self.metrics_history)
        avg_error_rate = sum(m.error_rate for m in self.metrics_history) / total_metrics
        avg_fallback_rate = sum(m.fallback_rate for m in self.metrics_history) / total_metrics
        avg_success_rate = sum(m.success_rate for m in self.metrics_history) / total_metrics
        
        max_connections = max(m.total_connections for m in self.metrics_history)
        total_routing_errors = sum(m.routing_errors for m in self.metrics_history)
        total_fallback_activations = sum(m.fallback_activations for m in self.metrics_history)
        
        # Calculate performance trends
        performance_trend = self._calculate_performance_trend()
        stability_score = self._calculate_stability_score()
        
        # Get resource usage statistics
        resource_stats = await self._get_resource_statistics()
        
        return {
            "monitoring_summary": {
                "start_time": self.metrics_history[0].timestamp.isoformat(),
                "end_time": self.metrics_history[-1].timestamp.isoformat(),
                "duration_minutes": (self.metrics_history[-1].timestamp - self.metrics_history[0].timestamp).total_seconds() / 60,
                "total_samples": total_metrics,
                "monitoring_status": "completed" if not self.monitoring_active else "active"
            },
            "performance_metrics": {
                "average_error_rate": round(avg_error_rate, 2),
                "average_fallback_rate": round(avg_fallback_rate, 2),
                "average_success_rate": round(avg_success_rate, 2),
                "max_concurrent_connections": max_connections,
                "total_routing_errors": total_routing_errors,
                "total_fallback_activations": total_fallback_activations,
                "performance_trend": performance_trend,
                "stability_score": stability_score
            },
            "rollback_info": {
                "rollback_triggered": self.rollback_triggered,
                "consecutive_failures": self.consecutive_failures,
                "thresholds": asdict(self.thresholds),
                "rollback_reason": "Automatic rollback due to threshold violations" if self.rollback_triggered else None
            },
            "resource_usage": resource_stats,
            "deployment_health": self._assess_deployment_health(),
            "recommendations": self._generate_recommendations(),
            "final_state": asdict(self.metrics_history[-1]) if self.metrics_history else None
        }
    
    def _calculate_performance_trend(self) -> str:
        """Calculate performance trend over monitoring period"""
        if len(self.metrics_history) < 2:
            return "insufficient_data"
        
        # Compare first and last quarters of monitoring period
        quarter_size = max(1, len(self.metrics_history) // 4)
        first_quarter = self.metrics_history[:quarter_size]
        last_quarter = self.metrics_history[-quarter_size:]
        
        first_avg_success = sum(m.success_rate for m in first_quarter) / len(first_quarter)
        last_avg_success = sum(m.success_rate for m in last_quarter) / len(last_quarter)
        
        if last_avg_success > first_avg_success + 2:
            return "improving"
        elif last_avg_success < first_avg_success - 2:
            return "degrading"
        else:
            return "stable"
    
    def _calculate_stability_score(self) -> float:
        """Calculate stability score (0-100) based on consistency of metrics"""
        if len(self.metrics_history) < 2:
            return 50.0
        
        # Calculate coefficient of variation for success rate
        success_rates = [m.success_rate for m in self.metrics_history]
        mean_success = sum(success_rates) / len(success_rates)
        
        if mean_success == 0:
            return 0.0
        
        variance = sum((x - mean_success) ** 2 for x in success_rates) / len(success_rates)
        std_dev = variance ** 0.5
        cv = std_dev / mean_success
        
        # Convert coefficient of variation to stability score (lower CV = higher stability)
        stability_score = max(0, 100 - (cv * 100))
        return round(stability_score, 2)
    
    async def _get_resource_statistics(self) -> Dict[str, Any]:
        """Get system resource usage statistics"""
        try:
            import psutil
            
            # Get current process info
            process = psutil.Process()
            
            # Memory usage
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            # CPU usage
            cpu_percent = process.cpu_percent()
            
            # System-wide stats
            system_memory = psutil.virtual_memory()
            system_cpu = psutil.cpu_percent(interval=1)
            
            return {
                "process_memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                "process_memory_percent": round(memory_percent, 2),
                "process_cpu_percent": round(cpu_percent, 2),
                "system_memory_percent": round(system_memory.percent, 2),
                "system_cpu_percent": round(system_cpu, 2),
                "system_memory_available_gb": round(system_memory.available / 1024 / 1024 / 1024, 2)
            }
            
        except ImportError:
            logger.warning("psutil not available, skipping resource statistics")
            return {"error": "psutil not available"}
        except Exception as e:
            logger.error(f"Error getting resource statistics: {e}")
            return {"error": str(e)}
    
    def _assess_deployment_health(self) -> Dict[str, Any]:
        """Assess overall deployment health"""
        if not self.metrics_history:
            return {"status": "unknown", "score": 0}
        
        latest_metrics = self.metrics_history[-1]
        
        # Calculate health score based on multiple factors
        health_score = 100.0
        issues = []
        
        # Error rate impact
        if latest_metrics.error_rate > 5:
            health_score -= 30
            issues.append(f"High error rate: {latest_metrics.error_rate:.1f}%")
        elif latest_metrics.error_rate > 2:
            health_score -= 15
            issues.append(f"Elevated error rate: {latest_metrics.error_rate:.1f}%")
        
        # Fallback rate impact
        if latest_metrics.fallback_rate > 10:
            health_score -= 25
            issues.append(f"High fallback rate: {latest_metrics.fallback_rate:.1f}%")
        elif latest_metrics.fallback_rate > 5:
            health_score -= 10
            issues.append(f"Elevated fallback rate: {latest_metrics.fallback_rate:.1f}%")
        
        # Success rate impact
        if latest_metrics.success_rate < 90:
            health_score -= 40
            issues.append(f"Low success rate: {latest_metrics.success_rate:.1f}%")
        elif latest_metrics.success_rate < 95:
            health_score -= 20
            issues.append(f"Below target success rate: {latest_metrics.success_rate:.1f}%")
        
        # Consecutive failures impact
        if self.consecutive_failures > 0:
            health_score -= (self.consecutive_failures * 10)
            issues.append(f"Consecutive failures: {self.consecutive_failures}")
        
        health_score = max(0, health_score)
        
        # Determine status
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 75:
            status = "good"
        elif health_score >= 50:
            status = "fair"
        elif health_score >= 25:
            status = "poor"
        else:
            status = "critical"
        
        return {
            "status": status,
            "score": round(health_score, 1),
            "issues": issues,
            "rollback_triggered": self.rollback_triggered
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on monitoring results"""
        recommendations = []
        
        if not self.metrics_history:
            return ["Insufficient monitoring data to generate recommendations"]
        
        latest_metrics = self.metrics_history[-1]
        
        # Error rate recommendations
        if latest_metrics.error_rate > 5:
            recommendations.append("Investigate high error rate - check logs for connection failures")
            recommendations.append("Consider reducing rollout percentage until issues are resolved")
        
        # Fallback recommendations
        if latest_metrics.fallback_rate > 10:
            recommendations.append("High fallback rate indicates unified system issues")
            recommendations.append("Review unified WebSocket system logs and performance")
        
        # Connection distribution recommendations
        if latest_metrics.total_connections > 0:
            unified_percentage = (latest_metrics.unified_connections / latest_metrics.total_connections) * 100
            expected_percentage = latest_metrics.rollout_percentage
            
            if unified_percentage < expected_percentage * 0.8:
                recommendations.append(f"Unified system adoption ({unified_percentage:.1f}%) below expected ({expected_percentage}%)")
                recommendations.append("Check feature flag configuration and user assignment logic")
        
        # Stability recommendations
        stability_score = self._calculate_stability_score()
        if stability_score < 70:
            recommendations.append("System showing instability - consider pausing rollout")
            recommendations.append("Monitor for patterns in connection failures")
        
        # Performance trend recommendations
        trend = self._calculate_performance_trend()
        if trend == "degrading":
            recommendations.append("Performance is degrading over time")
            recommendations.append("Consider rollback or investigation of root cause")
        
        # Consecutive failures recommendations
        if self.consecutive_failures > 2:
            recommendations.append("Multiple consecutive monitoring failures detected")
            recommendations.append("System may be experiencing persistent issues")
        
        if not recommendations:
            recommendations.append("System appears to be operating within normal parameters")
            recommendations.append("Continue monitoring and consider gradual rollout increase")
        
        return recommendations


async def main():
    """Main function for the monitoring script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket Deployment Monitor")
    parser.add_argument(
        "--duration",
        type=int,
        help="Monitoring duration in minutes (default: indefinite)"
    )
    parser.add_argument(
        "--max-error-rate",
        type=float,
        default=5.0,
        help="Maximum error rate percentage before rollback (default: 5.0)"
    )
    parser.add_argument(
        "--max-routing-errors",
        type=int,
        default=50,
        help="Maximum routing errors before rollback (default: 50)"
    )
    parser.add_argument(
        "--max-fallback-rate",
        type=float,
        default=10.0,
        help="Maximum fallback rate percentage before rollback (default: 10.0)"
    )
    parser.add_argument(
        "--min-success-rate",
        type=float,
        default=95.0,
        help="Minimum success rate percentage (default: 95.0)"
    )
    parser.add_argument(
        "--consecutive-failures",
        type=int,
        default=3,
        help="Consecutive failures before rollback (default: 3)"
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate report from existing log file only"
    )
    
    args = parser.parse_args()
    
    # Create custom thresholds
    thresholds = MonitoringThresholds(
        max_error_rate=args.max_error_rate,
        max_routing_errors=args.max_routing_errors,
        max_fallback_rate=args.max_fallback_rate,
        min_success_rate=args.min_success_rate,
        consecutive_failures_threshold=args.consecutive_failures
    )
    
    monitor = WebSocketDeploymentMonitor(thresholds)
    
    if args.report_only:
        # Generate report from existing data
        report = await monitor.generate_report()
        print(json.dumps(report, indent=2))
    else:
        # Start monitoring
        await monitor.start_monitoring(args.duration)
        
        # Generate final report
        print("\n" + "=" * 60)
        print("📊 FINAL MONITORING REPORT")
        print("=" * 60)
        report = await monitor.generate_report()
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())