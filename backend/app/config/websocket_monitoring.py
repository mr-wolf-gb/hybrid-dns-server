"""
WebSocket Production Monitoring Configuration

Configuration settings for production deployment monitoring, alerting, and resource tracking.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..core.config import get_settings


class MonitoringLevel(Enum):
    """Monitoring intensity levels"""
    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    DEBUG = "debug"


@dataclass
class AlertConfiguration:
    """Configuration for deployment alerts"""
    # Error rate thresholds
    max_error_rate_warning: float = 2.0
    max_error_rate_critical: float = 5.0
    
    # Success rate thresholds
    min_success_rate_warning: float = 97.0
    min_success_rate_critical: float = 95.0
    
    # Fallback rate thresholds
    max_fallback_rate_warning: float = 5.0
    max_fallback_rate_critical: float = 10.0
    
    # User adoption thresholds
    min_user_adoption_rate_warning: float = 85.0
    min_user_adoption_rate_critical: float = 80.0
    
    # Performance score thresholds
    min_performance_score_warning: float = 80.0
    min_performance_score_critical: float = 70.0
    
    # Health score thresholds
    min_health_score_warning: float = 85.0
    min_health_score_critical: float = 80.0
    
    # Consecutive failure thresholds
    consecutive_failures_warning: int = 2
    consecutive_failures_critical: int = 3
    
    # Alert cooldown periods (seconds)
    warning_cooldown: int = 300  # 5 minutes
    critical_cooldown: int = 180  # 3 minutes
    
    # Auto-rollback settings
    enable_auto_rollback: bool = True
    auto_rollback_threshold: int = 3  # consecutive critical alerts


@dataclass
class MonitoringConfiguration:
    """Configuration for production monitoring"""
    # Monitoring intervals
    metrics_collection_interval: int = 30  # seconds
    health_check_interval: int = 60  # seconds
    resource_check_interval: int = 120  # seconds
    
    # Data retention
    metrics_retention_hours: int = 24
    alert_history_retention_days: int = 7
    log_retention_days: int = 30
    
    # Monitoring level
    monitoring_level: MonitoringLevel = MonitoringLevel.STANDARD
    
    # Resource monitoring thresholds
    max_memory_usage_mb: float = 1024.0  # 1GB
    max_cpu_usage_percent: float = 80.0
    max_connection_count: int = 10000
    
    # Network monitoring
    max_network_latency_ms: float = 500.0
    max_message_queue_size: int = 10000
    
    # Alert configuration
    alerts: AlertConfiguration = None
    
    def __post_init__(self):
        if self.alerts is None:
            self.alerts = AlertConfiguration()


@dataclass
class NotificationConfiguration:
    """Configuration for alert notifications"""
    # Webhook settings
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    webhook_timeout: int = 10
    webhook_retry_count: int = 3
    
    # Email settings
    email_enabled: bool = False
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    alert_email_recipients: List[str] = None
    
    # Slack settings
    slack_enabled: bool = False
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    
    # File logging settings
    file_logging_enabled: bool = True
    alert_log_file: str = "websocket_deployment_alerts.log"
    monitoring_log_file: str = "websocket_deployment_monitor.log"
    
    def __post_init__(self):
        if self.alert_email_recipients is None:
            self.alert_email_recipients = []


class WebSocketMonitoringConfig:
    """Main configuration class for WebSocket monitoring"""
    
    def __init__(self):
        self.settings = get_settings()
        self.monitoring = self._load_monitoring_config()
        self.notifications = self._load_notification_config()
    
    def _load_monitoring_config(self) -> MonitoringConfiguration:
        """Load monitoring configuration from settings"""
        # Get monitoring level from environment
        monitoring_level_str = getattr(self.settings, 'WEBSOCKET_MONITORING_LEVEL', 'standard')
        try:
            monitoring_level = MonitoringLevel(monitoring_level_str.lower())
        except ValueError:
            monitoring_level = MonitoringLevel.STANDARD
        
        # Create configuration based on monitoring level
        if monitoring_level == MonitoringLevel.BASIC:
            return MonitoringConfiguration(
                metrics_collection_interval=60,
                health_check_interval=120,
                resource_check_interval=300,
                monitoring_level=monitoring_level,
                alerts=AlertConfiguration(
                    max_error_rate_critical=10.0,
                    min_success_rate_critical=90.0,
                    consecutive_failures_critical=5
                )
            )
        elif monitoring_level == MonitoringLevel.COMPREHENSIVE:
            return MonitoringConfiguration(
                metrics_collection_interval=15,
                health_check_interval=30,
                resource_check_interval=60,
                monitoring_level=monitoring_level,
                alerts=AlertConfiguration(
                    max_error_rate_warning=1.0,
                    max_error_rate_critical=3.0,
                    min_success_rate_warning=98.0,
                    min_success_rate_critical=97.0,
                    consecutive_failures_warning=1,
                    consecutive_failures_critical=2
                )
            )
        elif monitoring_level == MonitoringLevel.DEBUG:
            return MonitoringConfiguration(
                metrics_collection_interval=10,
                health_check_interval=15,
                resource_check_interval=30,
                monitoring_level=monitoring_level,
                metrics_retention_hours=48,
                alerts=AlertConfiguration(
                    max_error_rate_warning=0.5,
                    max_error_rate_critical=2.0,
                    min_success_rate_warning=99.0,
                    min_success_rate_critical=98.0,
                    consecutive_failures_warning=1,
                    consecutive_failures_critical=1,
                    enable_auto_rollback=False  # Disable auto-rollback in debug mode
                )
            )
        else:  # STANDARD
            return MonitoringConfiguration(monitoring_level=monitoring_level)
    
    def _load_notification_config(self) -> NotificationConfiguration:
        """Load notification configuration from settings"""
        return NotificationConfiguration(
            webhook_enabled=getattr(self.settings, 'WEBSOCKET_ALERT_WEBHOOK_ENABLED', False),
            webhook_url=getattr(self.settings, 'WEBSOCKET_ALERT_WEBHOOK_URL', None),
            email_enabled=getattr(self.settings, 'WEBSOCKET_ALERT_EMAIL_ENABLED', False),
            smtp_server=getattr(self.settings, 'WEBSOCKET_ALERT_SMTP_SERVER', None),
            smtp_port=getattr(self.settings, 'WEBSOCKET_ALERT_SMTP_PORT', 587),
            smtp_username=getattr(self.settings, 'WEBSOCKET_ALERT_SMTP_USERNAME', None),
            smtp_password=getattr(self.settings, 'WEBSOCKET_ALERT_SMTP_PASSWORD', None),
            alert_email_recipients=getattr(self.settings, 'WEBSOCKET_ALERT_EMAIL_RECIPIENTS', '').split(',') if getattr(self.settings, 'WEBSOCKET_ALERT_EMAIL_RECIPIENTS', '') else [],
            slack_enabled=getattr(self.settings, 'WEBSOCKET_ALERT_SLACK_ENABLED', False),
            slack_webhook_url=getattr(self.settings, 'WEBSOCKET_ALERT_SLACK_WEBHOOK_URL', None),
            slack_channel=getattr(self.settings, 'WEBSOCKET_ALERT_SLACK_CHANNEL', None)
        )
    
    def get_monitoring_config(self) -> MonitoringConfiguration:
        """Get monitoring configuration"""
        return self.monitoring
    
    def get_notification_config(self) -> NotificationConfiguration:
        """Get notification configuration"""
        return self.notifications
    
    def update_monitoring_config(self, updates: Dict[str, Any]) -> bool:
        """Update monitoring configuration"""
        try:
            for key, value in updates.items():
                if hasattr(self.monitoring, key):
                    setattr(self.monitoring, key, value)
                elif hasattr(self.monitoring.alerts, key):
                    setattr(self.monitoring.alerts, key, value)
            return True
        except Exception:
            return False
    
    def get_production_readiness_checklist(self) -> Dict[str, Any]:
        """Get production readiness checklist"""
        checklist = {
            "monitoring_configured": True,
            "alerts_configured": True,
            "notifications_configured": False,
            "thresholds_appropriate": True,
            "auto_rollback_enabled": self.monitoring.alerts.enable_auto_rollback,
            "issues": [],
            "recommendations": []
        }
        
        # Check notification configuration
        if not (self.notifications.webhook_enabled or 
                self.notifications.email_enabled or 
                self.notifications.slack_enabled):
            checklist["notifications_configured"] = False
            checklist["issues"].append("No notification channels configured")
            checklist["recommendations"].append("Configure at least one notification channel (webhook, email, or Slack)")
        
        # Check webhook configuration
        if self.notifications.webhook_enabled and not self.notifications.webhook_url:
            checklist["issues"].append("Webhook enabled but URL not configured")
            checklist["recommendations"].append("Configure webhook URL or disable webhook notifications")
        
        # Check email configuration
        if self.notifications.email_enabled:
            if not self.notifications.smtp_server:
                checklist["issues"].append("Email enabled but SMTP server not configured")
                checklist["recommendations"].append("Configure SMTP server settings")
            if not self.notifications.alert_email_recipients:
                checklist["issues"].append("Email enabled but no recipients configured")
                checklist["recommendations"].append("Configure alert email recipients")
        
        # Check Slack configuration
        if self.notifications.slack_enabled and not self.notifications.slack_webhook_url:
            checklist["issues"].append("Slack enabled but webhook URL not configured")
            checklist["recommendations"].append("Configure Slack webhook URL")
        
        # Check monitoring level appropriateness
        if self.monitoring.monitoring_level == MonitoringLevel.DEBUG:
            checklist["recommendations"].append("Debug monitoring level detected - consider using STANDARD or COMPREHENSIVE for production")
        
        # Check auto-rollback settings
        if not self.monitoring.alerts.enable_auto_rollback:
            checklist["recommendations"].append("Auto-rollback is disabled - consider enabling for production safety")
        
        # Overall readiness
        checklist["production_ready"] = (
            checklist["monitoring_configured"] and
            checklist["alerts_configured"] and
            checklist["notifications_configured"] and
            len(checklist["issues"]) == 0
        )
        
        return checklist


# Global configuration instance
_websocket_monitoring_config = None


def get_websocket_monitoring_config() -> WebSocketMonitoringConfig:
    """Get the global WebSocket monitoring configuration"""
    global _websocket_monitoring_config
    if _websocket_monitoring_config is None:
        _websocket_monitoring_config = WebSocketMonitoringConfig()
    return _websocket_monitoring_config