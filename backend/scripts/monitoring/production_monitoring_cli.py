#!/usr/bin/env python3
"""
Production Monitoring CLI

Unified command-line interface for all WebSocket production monitoring tools.
Provides easy access to monitoring, alerting, dashboard, and reporting functionality.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.logging_config import get_logger
from app.config.websocket_monitoring import get_websocket_monitoring_config

logger = get_logger(__name__)


class ProductionMonitoringCLI:
    """Unified CLI for production monitoring tools"""
    
    def __init__(self):
        self.monitoring_config = get_websocket_monitoring_config()
    
    async def run_command(self, args):
        """Run the specified monitoring command"""
        try:
            if args.command == "monitor":
                await self._run_monitor(args)
            elif args.command == "dashboard":
                await self._run_dashboard(args)
            elif args.command == "alerts":
                await self._run_alerts(args)
            elif args.command == "report":
                await self._run_report(args)
            elif args.command == "status":
                await self._run_status(args)
            elif args.command == "config":
                await self._run_config(args)
            else:
                print(f"Unknown command: {args.command}")
                return 1
            
            return 0
            
        except Exception as e:
            logger.error(f"Error running command {args.command}: {e}")
            print(f"❌ Error: {e}")
            return 1
    
    async def _run_monitor(self, args):
        """Run production monitoring"""
        print("🚀 Starting Production Monitoring...")
        
        # Import and run production monitor
        from production_deployment_monitor import ProductionDeploymentMonitor, ProductionMonitoringConfig
        
        config = ProductionMonitoringConfig(
            monitoring_duration_hours=args.duration,
            monitoring_level=args.level,
            enable_auto_rollback=not args.disable_auto_rollback,
            enable_alerting=not args.disable_alerting,
            report_interval_minutes=args.report_interval,
            max_consecutive_failures=args.max_failures
        )
        
        monitor = ProductionDeploymentMonitor(config)
        await monitor.start_production_monitoring()
    
    async def _run_dashboard(self, args):
        """Run monitoring dashboard"""
        print("📊 Starting Monitoring Dashboard...")
        
        # Import and run dashboard
        from websocket_monitoring_dashboard import WebSocketMonitoringDashboard
        
        dashboard = WebSocketMonitoringDashboard()
        dashboard.refresh_interval = args.refresh
        
        await dashboard.start_dashboard(mode=args.mode)
    
    async def _run_alerts(self, args):
        """Run alert management"""
        print("🚨 Alert Management")
        
        try:
            from app.services.websocket_alerting_service import get_websocket_alerting_service
            alerting_service = get_websocket_alerting_service()
            
            if args.action == "list":
                await self._list_alerts(alerting_service)
            elif args.action == "stats":
                await self._show_alert_stats(alerting_service)
            elif args.action == "acknowledge":
                await self._acknowledge_alert(alerting_service, args.alert_id, args.user)
            else:
                print(f"Unknown alert action: {args.action}")
                
        except Exception as e:
            print(f"❌ Alert service not available: {e}")
    
    async def _run_report(self, args):
        """Generate monitoring report"""
        print("📋 Generating Monitoring Report...")
        
        try:
            from app.services.websocket_deployment_monitoring import get_deployment_monitoring_service
            deployment_service = get_deployment_monitoring_service()
            
            report = deployment_service.get_deployment_report(hours=args.hours)
            
            if args.format == "json":
                import json
                print(json.dumps(report, indent=2))
            else:
                await self._display_report_summary(report)
                
        except Exception as e:
            print(f"❌ Error generating report: {e}")
    
    async def _run_status(self, args):
        """Show current system status"""
        print("📊 WebSocket System Status")
        print("=" * 50)
        
        try:
            from app.services.websocket_deployment_monitoring import get_deployment_monitoring_service
            deployment_service = get_deployment_monitoring_service()
            
            status = deployment_service.get_deployment_status()
            
            if status.get("status") == "no_data":
                print("⏳ No monitoring data available")
                print("💡 Start monitoring with: python production_monitoring_cli.py monitor")
                return
            
            latest_metrics = status.get("latest_metrics", {})
            active_alerts = status.get("active_alerts", [])
            
            # System Overview
            print("🔍 System Overview:")
            print(f"  Migration Mode: {latest_metrics.get('migration_mode', 'unknown')}")
            print(f"  Rollout Percentage: {latest_metrics.get('rollout_percentage', 0)}%")
            print(f"  Monitoring Active: {'✅ Yes' if status.get('monitoring_active') else '❌ No'}")
            print()
            
            # Connection Status
            print("🔗 Connection Status:")
            total_connections = latest_metrics.get('total_connections', 0)
            legacy_connections = latest_metrics.get('legacy_connections', 0)
            unified_connections = latest_metrics.get('unified_connections', 0)
            
            print(f"  Total Connections: {total_connections}")
            print(f"  Legacy: {legacy_connections}")
            print(f"  Unified: {unified_connections}")
            
            if total_connections > 0:
                unified_percent = (unified_connections / total_connections) * 100
                print(f"  Unified Adoption: {unified_percent:.1f}%")
            print()
            
            # Performance Metrics
            print("⚡ Performance Metrics:")
            print(f"  Error Rate: {latest_metrics.get('error_rate', 0):.2f}%")
            print(f"  Success Rate: {latest_metrics.get('success_rate', 0):.2f}%")
            print(f"  Performance Score: {latest_metrics.get('performance_score', 0):.1f}/100")
            print(f"  Health Score: {latest_metrics.get('health_score', 0):.1f}/100")
            print()
            
            # Alert Status
            print("🚨 Alert Status:")
            if active_alerts:
                critical_alerts = len([a for a in active_alerts if a.get("severity") == "critical"])
                warning_alerts = len([a for a in active_alerts if a.get("severity") == "warning"])
                
                print(f"  Active Alerts: {len(active_alerts)}")
                print(f"  Critical: {critical_alerts}")
                print(f"  Warning: {warning_alerts}")
                print(f"  Consecutive Failures: {status.get('consecutive_failures', 0)}")
            else:
                print("  ✅ No active alerts")
            
        except Exception as e:
            print(f"❌ Error getting status: {e}")
    
    async def _run_config(self, args):
        """Show or update configuration"""
        if args.action == "show":
            await self._show_config()
        elif args.action == "check":
            await self._check_config()
        elif args.action == "update":
            await self._update_config(args)
        else:
            print(f"Unknown config action: {args.action}")
    
    async def _show_config(self):
        """Show current monitoring configuration"""
        print("⚙️  Monitoring Configuration")
        print("=" * 50)
        
        monitoring_config = self.monitoring_config.get_monitoring_config()
        notification_config = self.monitoring_config.get_notification_config()
        
        print("📊 Monitoring Settings:")
        print(f"  Level: {monitoring_config.monitoring_level.value}")
        print(f"  Metrics Interval: {monitoring_config.metrics_collection_interval}s")
        print(f"  Health Check Interval: {monitoring_config.health_check_interval}s")
        print(f"  Resource Check Interval: {monitoring_config.resource_check_interval}s")
        print(f"  Metrics Retention: {monitoring_config.metrics_retention_hours}h")
        print()
        
        print("🚨 Alert Settings:")
        alerts = monitoring_config.alerts
        print(f"  Max Error Rate: {alerts.max_error_rate_critical}%")
        print(f"  Min Success Rate: {alerts.min_success_rate_critical}%")
        print(f"  Auto-Rollback: {'Enabled' if alerts.enable_auto_rollback else 'Disabled'}")
        print(f"  Rollback Threshold: {alerts.auto_rollback_threshold} failures")
        print()
        
        print("📧 Notification Settings:")
        print(f"  Webhook: {'Enabled' if notification_config.webhook_enabled else 'Disabled'}")
        print(f"  Email: {'Enabled' if notification_config.email_enabled else 'Disabled'}")
        print(f"  Slack: {'Enabled' if notification_config.slack_enabled else 'Disabled'}")
        print(f"  File Logging: {'Enabled' if notification_config.file_logging_enabled else 'Disabled'}")
    
    async def _check_config(self):
        """Check production readiness"""
        print("🔍 Production Readiness Check")
        print("=" * 50)
        
        checklist = self.monitoring_config.get_production_readiness_checklist()
        
        print(f"Production Ready: {'✅ Yes' if checklist['production_ready'] else '❌ No'}")
        print(f"Monitoring Configured: {'✅' if checklist['monitoring_configured'] else '❌'}")
        print(f"Alerts Configured: {'✅' if checklist['alerts_configured'] else '❌'}")
        print(f"Notifications Configured: {'✅' if checklist['notifications_configured'] else '❌'}")
        print()
        
        if checklist['issues']:
            print("⚠️  Issues Found:")
            for issue in checklist['issues']:
                print(f"  • {issue}")
            print()
        
        if checklist['recommendations']:
            print("💡 Recommendations:")
            for rec in checklist['recommendations']:
                print(f"  • {rec}")
    
    async def _update_config(self, args):
        """Update configuration"""
        print("⚙️  Configuration Update")
        print("This feature is not yet implemented.")
        print("Please update configuration through environment variables or config files.")
    
    async def _list_alerts(self, alerting_service):
        """List active alerts"""
        active_alerts = alerting_service.get_active_alerts()
        
        if not active_alerts:
            print("✅ No active alerts")
            return
        
        print(f"🚨 Active Alerts ({len(active_alerts)}):")
        print("-" * 60)
        
        for alert in active_alerts:
            severity_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(alert["severity"], "⚪")
            
            print(f"{severity_icon} {alert['title']}")
            print(f"   Severity: {alert['severity'].upper()}")
            print(f"   Message: {alert['message']}")
            print(f"   Time: {alert['timestamp']}")
            print(f"   Acknowledged: {'Yes' if alert['acknowledged'] else 'No'}")
            print()
    
    async def _show_alert_stats(self, alerting_service):
        """Show alert statistics"""
        stats = alerting_service.get_alert_statistics()
        
        print("📊 Alert Statistics:")
        print(f"  Total Alerts: {stats['total_alerts']}")
        print(f"  Active Alerts: {stats['active_alerts']}")
        print(f"  Critical Alerts: {stats['critical_alerts']}")
        print(f"  Warning Alerts: {stats['warning_alerts']}")
        print(f"  Acknowledged: {stats['acknowledged_alerts']}")
        print(f"  Escalated: {stats['escalated_alerts']}")
        print(f"  Avg Resolution Time: {stats['average_resolution_time_minutes']:.1f} minutes")
        print(f"  Alert Rules: {stats['alert_rules_count']}")
        print(f"  Notification Channels: {stats['notification_channels_count']}")
    
    async def _acknowledge_alert(self, alerting_service, alert_id: str, user: str):
        """Acknowledge an alert"""
        if not alert_id:
            print("❌ Alert ID is required")
            return
        
        success = await alerting_service.acknowledge_alert(alert_id, user or "cli_user")
        
        if success:
            print(f"✅ Alert {alert_id} acknowledged by {user or 'cli_user'}")
        else:
            print(f"❌ Failed to acknowledge alert {alert_id}")
    
    async def _display_report_summary(self, report: Dict[str, Any]):
        """Display report summary in human-readable format"""
        if "error" in report:
            print(f"❌ {report['error']}")
            return
        
        period = report.get("period", {})
        summary = report.get("summary_metrics", {})
        alerts = report.get("alerts", {})
        health = report.get("deployment_health", {})
        
        print("📊 Deployment Report Summary")
        print("=" * 50)
        
        print("⏱️  Report Period:")
        print(f"  Duration: {period.get('duration_hours', 0):.1f} hours")
        print(f"  Samples: {period.get('sample_count', 0)}")
        print()
        
        print("📈 Performance Summary:")
        print(f"  Average Error Rate: {summary.get('average_error_rate', 0):.2f}%")
        print(f"  Average Success Rate: {summary.get('average_success_rate', 0):.2f}%")
        print(f"  Average User Adoption: {summary.get('average_adoption_rate', 0):.2f}%")
        print(f"  Max Concurrent Connections: {summary.get('max_concurrent_connections', 0)}")
        print()
        
        print("🚨 Alert Summary:")
        print(f"  Total Alerts: {alerts.get('total_alerts', 0)}")
        print(f"  Critical: {alerts.get('critical_alerts', 0)}")
        print(f"  Warning: {alerts.get('warning_alerts', 0)}")
        print(f"  Resolved: {alerts.get('resolved_alerts', 0)}")
        print()
        
        print("💚 Deployment Health:")
        print(f"  Status: {health.get('status', 'unknown').title()}")
        print(f"  Score: {health.get('score', 0)}/100")
        print(f"  Trend: {health.get('trend', 'unknown').title()}")
        
        recommendations = report.get("recommendations", [])
        if recommendations:
            print()
            print("💡 Key Recommendations:")
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"  {i}. {rec}")


def create_parser():
    """Create argument parser for the CLI"""
    parser = argparse.ArgumentParser(
        description="Production Monitoring CLI for WebSocket Deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start production monitoring for 4 hours
  python production_monitoring_cli.py monitor --duration 4 --level comprehensive
  
  # Show real-time dashboard
  python production_monitoring_cli.py dashboard --mode summary --refresh 5
  
  # Generate deployment report
  python production_monitoring_cli.py report --hours 2 --format summary
  
  # Check system status
  python production_monitoring_cli.py status
  
  # List active alerts
  python production_monitoring_cli.py alerts list
  
  # Check production readiness
  python production_monitoring_cli.py config check
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Start production monitoring")
    monitor_parser.add_argument("--duration", type=int, help="Monitoring duration in hours")
    monitor_parser.add_argument("--level", choices=["basic", "standard", "comprehensive", "debug"], 
                               default="standard", help="Monitoring level")
    monitor_parser.add_argument("--disable-auto-rollback", action="store_true", 
                               help="Disable automatic rollback")
    monitor_parser.add_argument("--disable-alerting", action="store_true", 
                               help="Disable alerting system")
    monitor_parser.add_argument("--report-interval", type=int, default=30, 
                               help="Report interval in minutes")
    monitor_parser.add_argument("--max-failures", type=int, default=3, 
                               help="Maximum consecutive failures before rollback")
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Start monitoring dashboard")
    dashboard_parser.add_argument("--mode", choices=["summary", "detailed", "alerts", "metrics"], 
                                 default="summary", help="Dashboard display mode")
    dashboard_parser.add_argument("--refresh", type=int, default=5, 
                                 help="Refresh interval in seconds")
    
    # Alerts command
    alerts_parser = subparsers.add_parser("alerts", help="Manage alerts")
    alerts_parser.add_argument("action", choices=["list", "stats", "acknowledge"], 
                              help="Alert action")
    alerts_parser.add_argument("--alert-id", help="Alert ID for acknowledge action")
    alerts_parser.add_argument("--user", help="User acknowledging the alert")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate monitoring report")
    report_parser.add_argument("--hours", type=int, default=1, 
                              help="Report period in hours")
    report_parser.add_argument("--format", choices=["summary", "json"], default="summary", 
                              help="Report format")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show current system status")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_parser.add_argument("action", choices=["show", "check", "update"], 
                              help="Configuration action")
    
    return parser


async def main():
    """Main CLI function"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = ProductionMonitoringCLI()
    return await cli.run_command(args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))