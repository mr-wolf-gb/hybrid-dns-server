#!/usr/bin/env python3
"""
WebSocket Production Monitoring Dashboard

Real-time dashboard for monitoring WebSocket deployment performance, user adoption,
error rates, and system health during production rollout.
"""

import asyncio
import json
import time
import signal
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.services.websocket_deployment_monitoring import get_deployment_monitoring_service
from app.config.websocket_monitoring import get_websocket_monitoring_config

logger = get_logger(__name__)


class WebSocketMonitoringDashboard:
    """Real-time monitoring dashboard for WebSocket deployment"""
    
    def __init__(self):
        self.settings = get_settings()
        self.monitoring_config = get_websocket_monitoring_config()
        self.deployment_service = get_deployment_monitoring_service()
        
        self.dashboard_active = False
        self.shutdown_requested = False
        self.refresh_interval = 5  # seconds
        
        # Dashboard state
        self.last_update = None
        self.display_mode = "summary"  # summary, detailed, alerts, metrics
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received signal {signum}, shutting down dashboard...")
        self.shutdown_requested = True
    
    async def start_dashboard(self, mode: str = "summary"):
        """Start the monitoring dashboard"""
        self.display_mode = mode
        self.dashboard_active = True
        
        print("🚀 Starting WebSocket Monitoring Dashboard")
        print(f"Display Mode: {mode}")
        print(f"Refresh Interval: {self.refresh_interval}s")
        print("=" * 80)
        
        # Start deployment monitoring if not already active
        if not self.deployment_service.monitoring_active:
            asyncio.create_task(self.deployment_service.start_monitoring())
            await asyncio.sleep(2)  # Give it time to start
        
        try:
            while self.dashboard_active and not self.shutdown_requested:
                await self._update_dashboard()
                await asyncio.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            print("\n⏹️  Dashboard stopped by user")
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            print(f"❌ Dashboard error: {e}")
        finally:
            self.dashboard_active = False
            print("\n✅ Dashboard stopped")
    
    async def _update_dashboard(self):
        """Update dashboard display"""
        try:
            # Clear screen
            self._clear_screen()
            
            # Get current deployment status
            deployment_status = self.deployment_service.get_deployment_status()
            
            # Display header
            self._display_header()
            
            # Display content based on mode
            if self.display_mode == "summary":
                await self._display_summary(deployment_status)
            elif self.display_mode == "detailed":
                await self._display_detailed(deployment_status)
            elif self.display_mode == "alerts":
                await self._display_alerts(deployment_status)
            elif self.display_mode == "metrics":
                await self._display_metrics(deployment_status)
            else:
                await self._display_summary(deployment_status)
            
            # Display footer
            self._display_footer()
            
            self.last_update = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
            print(f"❌ Dashboard update error: {e}")
    
    def _clear_screen(self):
        """Clear the terminal screen"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _display_header(self):
        """Display dashboard header"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        print("🔍 WebSocket Production Monitoring Dashboard")
        print(f"Last Updated: {timestamp} | Mode: {self.display_mode.title()}")
        print("=" * 80)
    
    async def _display_summary(self, deployment_status: Dict[str, Any]):
        """Display summary view"""
        if deployment_status.get("status") == "no_data":
            print("⏳ Waiting for monitoring data...")
            return
        
        latest_metrics = deployment_status.get("latest_metrics", {})
        active_alerts = deployment_status.get("active_alerts", [])
        consecutive_failures = deployment_status.get("consecutive_failures", 0)
        
        # Deployment Overview
        print("📊 DEPLOYMENT OVERVIEW")
        print("-" * 40)
        migration_mode = latest_metrics.get("migration_mode", "unknown")
        rollout_percentage = latest_metrics.get("rollout_percentage", 0)
        print(f"Migration Mode: {migration_mode}")
        print(f"Rollout Percentage: {rollout_percentage}%")
        print(f"Monitoring Status: {'🟢 Active' if deployment_status.get('monitoring_active') else '🔴 Inactive'}")
        print()
        
        # Connection Statistics
        print("🔗 CONNECTION STATISTICS")
        print("-" * 40)
        total_connections = latest_metrics.get("total_connections", 0)
        legacy_connections = latest_metrics.get("legacy_connections", 0)
        unified_connections = latest_metrics.get("unified_connections", 0)
        
        print(f"Total Connections: {total_connections}")
        print(f"Legacy Connections: {legacy_connections}")
        print(f"Unified Connections: {unified_connections}")
        
        if total_connections > 0:
            unified_percentage = (unified_connections / total_connections) * 100
            print(f"Unified Adoption: {unified_percentage:.1f}%")
        print()
        
        # Performance Metrics
        print("⚡ PERFORMANCE METRICS")
        print("-" * 40)
        error_rate = latest_metrics.get("error_rate", 0.0)
        success_rate = latest_metrics.get("success_rate", 0.0)
        user_adoption_rate = latest_metrics.get("user_adoption_rate", 0.0)
        performance_score = latest_metrics.get("performance_score", 0.0)
        health_score = latest_metrics.get("health_score", 0.0)
        
        print(f"Error Rate: {self._format_rate(error_rate)}%")
        print(f"Success Rate: {self._format_rate(success_rate)}%")
        print(f"User Adoption: {self._format_rate(user_adoption_rate)}%")
        print(f"Performance Score: {self._format_score(performance_score)}")
        print(f"Health Score: {self._format_score(health_score)}")
        print()
        
        # Alert Status
        print("🚨 ALERT STATUS")
        print("-" * 40)
        if active_alerts:
            critical_alerts = len([a for a in active_alerts if a.get("severity") == "critical"])
            warning_alerts = len([a for a in active_alerts if a.get("severity") == "warning"])
            
            print(f"Active Alerts: {len(active_alerts)}")
            print(f"Critical: {critical_alerts} | Warning: {warning_alerts}")
            print(f"Consecutive Failures: {consecutive_failures}")
            
            # Show most recent alert
            if active_alerts:
                recent_alert = active_alerts[0]
                print(f"Latest: {recent_alert.get('title', 'Unknown')}")
        else:
            print("✅ No active alerts")
        print()
        
        # System Health
        print("💚 SYSTEM HEALTH")
        print("-" * 40)
        routing_errors = latest_metrics.get("routing_errors", 0)
        fallback_activations = latest_metrics.get("fallback_activations", 0)
        
        print(f"Routing Errors: {routing_errors}")
        print(f"Fallback Activations: {fallback_activations}")
        
        # Overall status indicator
        overall_status = self._calculate_overall_status(latest_metrics, active_alerts)
        print(f"Overall Status: {overall_status}")
    
    async def _display_detailed(self, deployment_status: Dict[str, Any]):
        """Display detailed metrics view"""
        if deployment_status.get("status") == "no_data":
            print("⏳ Waiting for monitoring data...")
            return
        
        latest_metrics = deployment_status.get("latest_metrics", {})
        
        print("📈 DETAILED METRICS")
        print("-" * 80)
        
        # Deployment Information
        print("🚀 Deployment Information:")
        print(f"  Migration Mode: {latest_metrics.get('migration_mode', 'unknown')}")
        print(f"  Rollout Percentage: {latest_metrics.get('rollout_percentage', 0)}%")
        print(f"  Timestamp: {latest_metrics.get('timestamp', 'unknown')}")
        print()
        
        # Connection Details
        print("🔗 Connection Details:")
        print(f"  Total Connections: {latest_metrics.get('total_connections', 0)}")
        print(f"  Legacy Connections: {latest_metrics.get('legacy_connections', 0)}")
        print(f"  Unified Connections: {latest_metrics.get('unified_connections', 0)}")
        print(f"  Routing Errors: {latest_metrics.get('routing_errors', 0)}")
        print(f"  Fallback Activations: {latest_metrics.get('fallback_activations', 0)}")
        print()
        
        # Performance Metrics
        print("⚡ Performance Metrics:")
        print(f"  Error Rate: {latest_metrics.get('error_rate', 0.0):.2f}%")
        print(f"  Success Rate: {latest_metrics.get('success_rate', 0.0):.2f}%")
        print(f"  User Adoption Rate: {latest_metrics.get('user_adoption_rate', 0.0):.2f}%")
        print(f"  Performance Score: {latest_metrics.get('performance_score', 0.0):.1f}/100")
        print(f"  Health Score: {latest_metrics.get('health_score', 0.0):.1f}/100")
        print()
        
        # Threshold Information
        thresholds = deployment_status.get("thresholds", {})
        if thresholds:
            print("🎯 Alert Thresholds:")
            print(f"  Max Error Rate: {thresholds.get('max_error_rate', 0)}%")
            print(f"  Min Success Rate: {thresholds.get('min_success_rate', 0)}%")
            print(f"  Min User Adoption: {thresholds.get('min_user_adoption_rate', 0)}%")
            print(f"  Min Performance Score: {thresholds.get('min_performance_score', 0)}")
            print(f"  Min Health Score: {thresholds.get('min_health_score', 0)}")
            print()
        
        # Historical Data Summary
        metrics_count = deployment_status.get("metrics_count", 0)
        alert_history_count = deployment_status.get("alert_history_count", 0)
        
        print("📊 Historical Data:")
        print(f"  Metrics Collected: {metrics_count}")
        print(f"  Total Alerts: {alert_history_count}")
        print(f"  Consecutive Failures: {deployment_status.get('consecutive_failures', 0)}")
    
    async def _display_alerts(self, deployment_status: Dict[str, Any]):
        """Display alerts view"""
        active_alerts = deployment_status.get("active_alerts", [])
        
        print("🚨 ACTIVE ALERTS")
        print("-" * 80)
        
        if not active_alerts:
            print("✅ No active alerts")
            print()
            print("🎉 System is operating normally")
            return
        
        for i, alert in enumerate(active_alerts, 1):
            severity = alert.get("severity", "unknown")
            title = alert.get("title", "Unknown Alert")
            message = alert.get("message", "No message")
            timestamp = alert.get("timestamp", "Unknown time")
            
            # Format severity with emoji
            severity_icon = {
                "critical": "🔴",
                "warning": "🟡",
                "info": "🔵"
            }.get(severity, "⚪")
            
            print(f"{severity_icon} Alert #{i} - {severity.upper()}")
            print(f"  Title: {title}")
            print(f"  Message: {message}")
            print(f"  Time: {timestamp}")
            
            # Show related metrics if available
            metrics = alert.get("metrics", {})
            if metrics:
                print(f"  Related Metrics:")
                if "error_rate" in metrics:
                    print(f"    Error Rate: {metrics['error_rate']:.2f}%")
                if "success_rate" in metrics:
                    print(f"    Success Rate: {metrics['success_rate']:.2f}%")
                if "performance_score" in metrics:
                    print(f"    Performance Score: {metrics['performance_score']:.1f}")
            print()
        
        # Alert summary
        critical_count = len([a for a in active_alerts if a.get("severity") == "critical"])
        warning_count = len([a for a in active_alerts if a.get("severity") == "warning"])
        
        print("📊 Alert Summary:")
        print(f"  Total Active: {len(active_alerts)}")
        print(f"  Critical: {critical_count}")
        print(f"  Warning: {warning_count}")
        print(f"  Consecutive Failures: {deployment_status.get('consecutive_failures', 0)}")
    
    async def _display_metrics(self, deployment_status: Dict[str, Any]):
        """Display metrics history view"""
        print("📈 METRICS HISTORY")
        print("-" * 80)
        
        # Generate a simple report for the last hour
        try:
            report = self.deployment_service.get_deployment_report(hours=1)
            
            if "error" in report:
                print(f"❌ {report['error']}")
                return
            
            period = report.get("period", {})
            summary = report.get("summary_metrics", {})
            alerts = report.get("alerts", {})
            current = report.get("current_status", {})
            health = report.get("deployment_health", {})
            trends = report.get("performance_trends", {})
            
            print("⏱️  Report Period:")
            print(f"  Duration: {period.get('duration_hours', 0)} hours")
            print(f"  Samples: {period.get('sample_count', 0)}")
            print(f"  Start: {period.get('start_time', 'unknown')}")
            print()
            
            print("📊 Average Metrics (Last Hour):")
            print(f"  Error Rate: {summary.get('average_error_rate', 0):.2f}%")
            print(f"  Success Rate: {summary.get('average_success_rate', 0):.2f}%")
            print(f"  User Adoption: {summary.get('average_adoption_rate', 0):.2f}%")
            print(f"  Performance Score: {summary.get('average_performance_score', 0):.1f}/100")
            print(f"  Health Score: {summary.get('average_health_score', 0):.1f}/100")
            print()
            
            print("🔗 Connection Statistics:")
            print(f"  Max Concurrent: {summary.get('max_concurrent_connections', 0)}")
            print(f"  Total Routing Errors: {summary.get('total_routing_errors', 0)}")
            print(f"  Total Fallbacks: {summary.get('total_fallback_activations', 0)}")
            print()
            
            print("🚨 Alert Statistics:")
            print(f"  Total Alerts: {alerts.get('total_alerts', 0)}")
            print(f"  Critical: {alerts.get('critical_alerts', 0)}")
            print(f"  Warning: {alerts.get('warning_alerts', 0)}")
            print(f"  Resolved: {alerts.get('resolved_alerts', 0)}")
            print()
            
            print("💚 Deployment Health:")
            print(f"  Status: {health.get('status', 'unknown').title()}")
            print(f"  Score: {health.get('score', 0)}/100")
            print(f"  Trend: {health.get('trend', 'unknown').title()}")
            if health.get('factors'):
                print(f"  Key Factor: {health['factors'][0]}")
            print()
            
            print("📈 Performance Trends:")
            if "error" not in trends:
                error_trend = trends.get("error_rate_trend", {})
                success_trend = trends.get("success_rate_trend", {})
                
                print(f"  Error Rate: {error_trend.get('trend', 'unknown')} ({error_trend.get('change_percent', 0):+.1f}%)")
                print(f"  Success Rate: {success_trend.get('trend', 'unknown')} ({success_trend.get('change_percent', 0):+.1f}%)")
                
                stability = trends.get("stability_indicators", {})
                print(f"  Performance: {stability.get('consistent_performance', 'unknown')}")
            print()
            
            print("📍 Current Status:")
            print(f"  Active Alerts: {current.get('active_alerts', 0)}")
            print(f"  Consecutive Failures: {current.get('consecutive_failures', 0)}")
            
            # Show top recommendations
            recommendations = report.get("recommendations", [])
            if recommendations:
                print()
                print("💡 Top Recommendations:")
                for i, rec in enumerate(recommendations[:3], 1):
                    print(f"  {i}. {rec}")
            
        except Exception as e:
            logger.error(f"Error displaying metrics: {e}")
            print(f"❌ Error loading metrics: {e}")
    
    def _display_footer(self):
        """Display dashboard footer with controls"""
        print()
        print("=" * 80)
        print("Controls: Ctrl+C to exit | Modes: summary, detailed, alerts, metrics")
        print(f"Refresh: {self.refresh_interval}s | Last Update: {self.last_update.strftime('%H:%M:%S') if self.last_update else 'Never'}")
    
    def _format_rate(self, rate: float) -> str:
        """Format rate with color coding"""
        if rate >= 95:
            return f"🟢 {rate:.1f}"
        elif rate >= 90:
            return f"🟡 {rate:.1f}"
        else:
            return f"🔴 {rate:.1f}"
    
    def _format_score(self, score: float) -> str:
        """Format score with color coding"""
        if score >= 80:
            return f"🟢 {score:.1f}/100"
        elif score >= 60:
            return f"🟡 {score:.1f}/100"
        else:
            return f"🔴 {score:.1f}/100"
    
    def _calculate_overall_status(self, metrics: Dict[str, Any], alerts: List[Dict[str, Any]]) -> str:
        """Calculate overall system status"""
        if not metrics:
            return "⚪ Unknown"
        
        # Check for critical alerts
        critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
        if critical_alerts:
            return "🔴 Critical Issues"
        
        # Check for warning alerts
        warning_alerts = [a for a in alerts if a.get("severity") == "warning"]
        if warning_alerts:
            return "🟡 Warning Issues"
        
        # Check performance metrics
        error_rate = metrics.get("error_rate", 0.0)
        success_rate = metrics.get("success_rate", 100.0)
        health_score = metrics.get("health_score", 100.0)
        
        if error_rate > 5.0 or success_rate < 95.0 or health_score < 80.0:
            return "🟡 Performance Issues"
        
        return "🟢 Healthy"


async def main():
    """Main function for monitoring dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket Monitoring Dashboard")
    parser.add_argument(
        "--mode",
        choices=["summary", "detailed", "alerts", "metrics"],
        default="summary",
        help="Dashboard display mode"
    )
    parser.add_argument(
        "--refresh",
        type=int,
        default=5,
        help="Refresh interval in seconds"
    )
    
    args = parser.parse_args()
    
    dashboard = WebSocketMonitoringDashboard()
    dashboard.refresh_interval = args.refresh
    
    await dashboard.start_dashboard(mode=args.mode)


if __name__ == "__main__":
    asyncio.run(main())