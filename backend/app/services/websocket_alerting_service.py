"""
WebSocket Production Alerting Service

Comprehensive alerting system for WebSocket deployment monitoring with multiple
notification channels, escalation policies, and intelligent alert management.
"""

import asyncio
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
except ImportError:
    # Fallback for systems where email modules are not available
    MimeText = None
    MimeMultipart = None
from pathlib import Path

from ..core.logging_config import get_logger
from ..config.websocket_monitoring import get_websocket_monitoring_config

logger = get_logger(__name__)


@dataclass
class AlertRule:
    """Configuration for an alert rule"""
    id: str
    name: str
    condition: str  # Python expression to evaluate
    severity: str  # critical, warning, info
    cooldown_minutes: int = 5
    escalation_minutes: int = 15
    auto_resolve: bool = True
    notification_channels: List[str] = None
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = ["log", "webhook"]


@dataclass
class Alert:
    """Alert instance"""
    id: str
    rule_id: str
    title: str
    message: str
    severity: str
    timestamp: datetime
    metrics: Dict[str, Any]
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    escalated: bool = False
    escalated_at: Optional[datetime] = None
    notification_attempts: int = 0
    last_notification: Optional[datetime] = None


@dataclass
class NotificationChannel:
    """Configuration for a notification channel"""
    name: str
    type: str  # webhook, email, slack, sms, pagerduty
    enabled: bool
    config: Dict[str, Any]
    retry_count: int = 3
    retry_delay_seconds: int = 60


class WebSocketAlertingService:
    """Production alerting service for WebSocket monitoring"""
    
    def __init__(self):
        self.monitoring_config = get_websocket_monitoring_config()
        
        # Alert management
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_rules: Dict[str, AlertRule] = {}
        self.notification_channels: Dict[str, NotificationChannel] = {}
        
        # Alert state
        self.last_rule_evaluation = {}
        self.alert_cooldowns: Dict[str, datetime] = {}
        
        # Initialize default alert rules
        self._initialize_default_alert_rules()
        
        # Initialize notification channels
        self._initialize_notification_channels()
        
        # Create alert log directory
        self.alert_log_dir = Path("logs/websocket_alerts")
        self.alert_log_dir.mkdir(parents=True, exist_ok=True)
    
    def _initialize_default_alert_rules(self):
        """Initialize default alert rules for WebSocket monitoring"""
        default_rules = [
            AlertRule(
                id="high_error_rate",
                name="High Error Rate",
                condition="metrics.get('error_rate', 0) > 5.0",
                severity="critical",
                cooldown_minutes=5,
                escalation_minutes=10,
                notification_channels=["log", "webhook", "email"]
            ),
            AlertRule(
                id="low_success_rate",
                name="Low Success Rate",
                condition="metrics.get('success_rate', 100) < 95.0",
                severity="critical",
                cooldown_minutes=5,
                escalation_minutes=10,
                notification_channels=["log", "webhook", "email"]
            ),
            AlertRule(
                id="low_user_adoption",
                name="Low User Adoption Rate",
                condition="metrics.get('user_adoption_rate', 100) < 80.0 and metrics.get('rollout_percentage', 0) > 0",
                severity="warning",
                cooldown_minutes=10,
                escalation_minutes=30,
                notification_channels=["log", "webhook"]
            ),
            AlertRule(
                id="high_fallback_rate",
                name="High Fallback Rate",
                condition="metrics.get('total_connections', 0) > 0 and (metrics.get('fallback_activations', 0) / metrics.get('total_connections', 1)) > 0.1",
                severity="warning",
                cooldown_minutes=5,
                escalation_minutes=15,
                notification_channels=["log", "webhook"]
            ),
            AlertRule(
                id="low_performance_score",
                name="Low Performance Score",
                condition="metrics.get('performance_score', 100) < 70.0",
                severity="warning",
                cooldown_minutes=10,
                escalation_minutes=20,
                notification_channels=["log", "webhook"]
            ),
            AlertRule(
                id="low_health_score",
                name="Low Health Score",
                condition="metrics.get('health_score', 100) < 80.0",
                severity="critical",
                cooldown_minutes=5,
                escalation_minutes=10,
                notification_channels=["log", "webhook", "email"]
            ),
            AlertRule(
                id="connection_spike",
                name="Connection Count Spike",
                condition="metrics.get('total_connections', 0) > 5000",
                severity="warning",
                cooldown_minutes=15,
                escalation_minutes=30,
                notification_channels=["log", "webhook"]
            ),
            AlertRule(
                id="routing_errors",
                name="High Routing Errors",
                condition="metrics.get('routing_errors', 0) > 10",
                severity="warning",
                cooldown_minutes=5,
                escalation_minutes=15,
                notification_channels=["log", "webhook"]
            ),
            AlertRule(
                id="deployment_stalled",
                name="Deployment Progress Stalled",
                condition="metrics.get('migration_mode') == 'gradual_rollout' and metrics.get('rollout_percentage', 0) < 50 and self._is_deployment_stalled()",
                severity="warning",
                cooldown_minutes=30,
                escalation_minutes=60,
                notification_channels=["log", "webhook", "email"]
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.id] = rule
    
    def _initialize_notification_channels(self):
        """Initialize notification channels from configuration"""
        notification_config = self.monitoring_config.get_notification_config()
        
        # Log channel (always enabled)
        self.notification_channels["log"] = NotificationChannel(
            name="log",
            type="log",
            enabled=True,
            config={"log_file": "websocket_alerts.log"}
        )
        
        # Webhook channel
        if notification_config.webhook_enabled and notification_config.webhook_url:
            self.notification_channels["webhook"] = NotificationChannel(
                name="webhook",
                type="webhook",
                enabled=True,
                config={
                    "url": notification_config.webhook_url,
                    "timeout": notification_config.webhook_timeout,
                    "retry_count": notification_config.webhook_retry_count
                }
            )
        
        # Email channel
        if notification_config.email_enabled and notification_config.smtp_server:
            self.notification_channels["email"] = NotificationChannel(
                name="email",
                type="email",
                enabled=True,
                config={
                    "smtp_server": notification_config.smtp_server,
                    "smtp_port": notification_config.smtp_port,
                    "username": notification_config.smtp_username,
                    "password": notification_config.smtp_password,
                    "use_tls": notification_config.smtp_use_tls,
                    "recipients": notification_config.alert_email_recipients
                }
            )
        
        # Slack channel
        if notification_config.slack_enabled and notification_config.slack_webhook_url:
            self.notification_channels["slack"] = NotificationChannel(
                name="slack",
                type="slack",
                enabled=True,
                config={
                    "webhook_url": notification_config.slack_webhook_url,
                    "channel": notification_config.slack_channel
                }
            )
    
    async def evaluate_alerts(self, metrics: Dict[str, Any]):
        """Evaluate all alert rules against current metrics"""
        try:
            current_time = datetime.utcnow()
            
            for rule_id, rule in self.alert_rules.items():
                try:
                    # Check cooldown
                    if rule_id in self.alert_cooldowns:
                        if current_time < self.alert_cooldowns[rule_id]:
                            continue
                    
                    # Evaluate rule condition
                    should_alert = self._evaluate_rule_condition(rule, metrics)
                    
                    if should_alert:
                        # Check if alert already exists
                        existing_alert = self._find_active_alert(rule_id)
                        
                        if not existing_alert:
                            # Create new alert
                            await self._create_alert(rule, metrics)
                        else:
                            # Check for escalation
                            await self._check_escalation(existing_alert)
                    else:
                        # Check for auto-resolution
                        existing_alert = self._find_active_alert(rule_id)
                        if existing_alert and rule.auto_resolve:
                            await self._resolve_alert(existing_alert.id, "Auto-resolved")
                
                except Exception as e:
                    logger.error(f"Error evaluating alert rule {rule_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error in alert evaluation: {e}")
    
    def _evaluate_rule_condition(self, rule: AlertRule, metrics: Dict[str, Any]) -> bool:
        """Evaluate a rule condition against metrics"""
        try:
            # Create evaluation context
            context = {
                "metrics": metrics,
                "self": self,
                "datetime": datetime,
                "timedelta": timedelta
            }
            
            # Evaluate the condition
            return eval(rule.condition, {"__builtins__": {}}, context)
            
        except Exception as e:
            logger.error(f"Error evaluating rule condition '{rule.condition}': {e}")
            return False
    
    def _is_deployment_stalled(self) -> bool:
        """Check if deployment progress has stalled"""
        # This would check if rollout percentage hasn't changed in a while
        # For now, return False as a placeholder
        return False
    
    def _find_active_alert(self, rule_id: str) -> Optional[Alert]:
        """Find active alert for a rule"""
        for alert in self.active_alerts.values():
            if alert.rule_id == rule_id and not alert.resolved:
                return alert
        return None
    
    async def _create_alert(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Create a new alert"""
        try:
            alert_id = f"{rule.id}_{int(datetime.utcnow().timestamp())}"
            
            # Generate alert message
            message = self._generate_alert_message(rule, metrics)
            
            alert = Alert(
                id=alert_id,
                rule_id=rule.id,
                title=rule.name,
                message=message,
                severity=rule.severity,
                timestamp=datetime.utcnow(),
                metrics=metrics.copy()
            )
            
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            # Set cooldown
            self.alert_cooldowns[rule.id] = datetime.utcnow() + timedelta(minutes=rule.cooldown_minutes)
            
            logger.warning(f"Alert created: {alert.title} - {alert.message}")
            
            # Send notifications
            await self._send_alert_notifications(alert, rule)
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    def _generate_alert_message(self, rule: AlertRule, metrics: Dict[str, Any]) -> str:
        """Generate alert message based on rule and metrics"""
        base_message = f"Alert condition triggered: {rule.condition}"
        
        # Add relevant metric values
        relevant_metrics = []
        
        if "error_rate" in rule.condition:
            relevant_metrics.append(f"Error Rate: {metrics.get('error_rate', 0):.2f}%")
        
        if "success_rate" in rule.condition:
            relevant_metrics.append(f"Success Rate: {metrics.get('success_rate', 0):.2f}%")
        
        if "user_adoption_rate" in rule.condition:
            relevant_metrics.append(f"User Adoption: {metrics.get('user_adoption_rate', 0):.2f}%")
        
        if "performance_score" in rule.condition:
            relevant_metrics.append(f"Performance Score: {metrics.get('performance_score', 0):.1f}")
        
        if "health_score" in rule.condition:
            relevant_metrics.append(f"Health Score: {metrics.get('health_score', 0):.1f}")
        
        if "total_connections" in rule.condition:
            relevant_metrics.append(f"Total Connections: {metrics.get('total_connections', 0)}")
        
        if relevant_metrics:
            base_message += f" | {' | '.join(relevant_metrics)}"
        
        return base_message
    
    async def _send_alert_notifications(self, alert: Alert, rule: AlertRule):
        """Send alert notifications through configured channels"""
        for channel_name in rule.notification_channels:
            if channel_name in self.notification_channels:
                channel = self.notification_channels[channel_name]
                if channel.enabled:
                    try:
                        await self._send_notification(alert, channel)
                        alert.notification_attempts += 1
                        alert.last_notification = datetime.utcnow()
                    except Exception as e:
                        logger.error(f"Error sending notification to {channel_name}: {e}")
    
    async def _send_notification(self, alert: Alert, channel: NotificationChannel):
        """Send notification through a specific channel"""
        if channel.type == "log":
            await self._send_log_notification(alert, channel)
        elif channel.type == "webhook":
            await self._send_webhook_notification(alert, channel)
        elif channel.type == "email":
            await self._send_email_notification(alert, channel)
        elif channel.type == "slack":
            await self._send_slack_notification(alert, channel)
        else:
            logger.warning(f"Unknown notification channel type: {channel.type}")
    
    async def _send_log_notification(self, alert: Alert, channel: NotificationChannel):
        """Send log notification"""
        log_file = self.alert_log_dir / channel.config.get("log_file", "alerts.log")
        
        log_entry = {
            "timestamp": alert.timestamp.isoformat(),
            "alert_id": alert.id,
            "rule_id": alert.rule_id,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "metrics": alert.metrics
        }
        
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    async def _send_webhook_notification(self, alert: Alert, channel: NotificationChannel):
        """Send webhook notification"""
        try:
            import aiohttp
            
            url = channel.config["url"]
            timeout = channel.config.get("timeout", 10)
            
            payload = {
                "alert_id": alert.id,
                "rule_id": alert.rule_id,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "metrics": alert.metrics,
                "acknowledged": alert.acknowledged,
                "escalated": alert.escalated
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook notification sent for alert {alert.id}")
                    else:
                        logger.warning(f"Webhook notification failed with status {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            raise
    
    async def _send_email_notification(self, alert: Alert, channel: NotificationChannel):
        """Send email notification"""
        try:
            if MimeText is None or MimeMultipart is None:
                logger.warning("Email modules not available, skipping email notification")
                return
            
            config = channel.config
            
            # Create message
            msg = MimeMultipart()
            msg["From"] = config["username"]
            msg["Subject"] = f"[{alert.severity.upper()}] WebSocket Alert: {alert.title}"
            
            # Create email body
            body = f"""
WebSocket Production Alert

Severity: {alert.severity.upper()}
Alert: {alert.title}
Message: {alert.message}
Time: {alert.timestamp.isoformat()}

Deployment Status:
- Migration Mode: {alert.metrics.get('migration_mode', 'unknown')}
- Rollout Percentage: {alert.metrics.get('rollout_percentage', 0)}%
- Total Connections: {alert.metrics.get('total_connections', 0)}
- Error Rate: {alert.metrics.get('error_rate', 0):.2f}%
- Success Rate: {alert.metrics.get('success_rate', 0):.2f}%

Please investigate immediately if this is a critical alert.

Alert ID: {alert.id}
Rule ID: {alert.rule_id}
"""
            
            msg.attach(MimeText(body, "plain"))
            
            # Send email to all recipients
            recipients = config.get("recipients", [])
            if not recipients:
                logger.warning("No email recipients configured")
                return
            
            msg["To"] = ", ".join(recipients)
            
            # Connect to SMTP server and send
            server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
            
            if config.get("use_tls", True):
                server.starttls()
            
            if config.get("username") and config.get("password"):
                server.login(config["username"], config["password"])
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email notification sent for alert {alert.id} to {len(recipients)} recipients")
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            raise
    
    async def _send_slack_notification(self, alert: Alert, channel: NotificationChannel):
        """Send Slack notification"""
        try:
            import aiohttp
            
            webhook_url = channel.config["webhook_url"]
            slack_channel = channel.config.get("channel")
            
            # Create Slack message
            color = {
                "critical": "danger",
                "warning": "warning",
                "info": "good"
            }.get(alert.severity, "warning")
            
            payload = {
                "channel": slack_channel,
                "username": "WebSocket Monitor",
                "icon_emoji": ":warning:",
                "attachments": [
                    {
                        "color": color,
                        "title": f"[{alert.severity.upper()}] {alert.title}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Migration Mode",
                                "value": alert.metrics.get("migration_mode", "unknown"),
                                "short": True
                            },
                            {
                                "title": "Rollout %",
                                "value": f"{alert.metrics.get('rollout_percentage', 0)}%",
                                "short": True
                            },
                            {
                                "title": "Error Rate",
                                "value": f"{alert.metrics.get('error_rate', 0):.2f}%",
                                "short": True
                            },
                            {
                                "title": "Success Rate",
                                "value": f"{alert.metrics.get('success_rate', 0):.2f}%",
                                "short": True
                            }
                        ],
                        "footer": f"Alert ID: {alert.id}",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent for alert {alert.id}")
                    else:
                        logger.warning(f"Slack notification failed with status {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            raise
    
    async def _check_escalation(self, alert: Alert):
        """Check if alert should be escalated"""
        if alert.escalated:
            return
        
        rule = self.alert_rules.get(alert.rule_id)
        if not rule:
            return
        
        # Check if escalation time has passed
        escalation_time = alert.timestamp + timedelta(minutes=rule.escalation_minutes)
        
        if datetime.utcnow() >= escalation_time and not alert.acknowledged:
            await self._escalate_alert(alert)
    
    async def _escalate_alert(self, alert: Alert):
        """Escalate an alert"""
        try:
            alert.escalated = True
            alert.escalated_at = datetime.utcnow()
            
            logger.warning(f"Alert escalated: {alert.title} (ID: {alert.id})")
            
            # Send escalation notifications
            escalation_alert = Alert(
                id=f"{alert.id}_escalation",
                rule_id=alert.rule_id,
                title=f"ESCALATED: {alert.title}",
                message=f"Alert has been escalated due to no acknowledgment. Original: {alert.message}",
                severity="critical",  # Escalated alerts are always critical
                timestamp=datetime.utcnow(),
                metrics=alert.metrics
            )
            
            # Send to all critical notification channels
            rule = self.alert_rules.get(alert.rule_id)
            if rule:
                await self._send_alert_notifications(escalation_alert, rule)
            
        except Exception as e:
            logger.error(f"Error escalating alert: {e}")
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        try:
            if alert_id not in self.active_alerts:
                return False
            
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            
            logger.info(f"Alert acknowledged: {alert.title} (ID: {alert_id}) by {acknowledged_by}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    async def _resolve_alert(self, alert_id: str, resolved_by: str = "System"):
        """Resolve an alert"""
        try:
            if alert_id not in self.active_alerts:
                return
            
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert resolved: {alert.title} (ID: {alert_id}) by {resolved_by}")
            
            # Send resolution notification
            await self._send_resolution_notification(alert)
            
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
    
    async def _send_resolution_notification(self, alert: Alert):
        """Send alert resolution notification"""
        try:
            resolution_time = (
                (alert.resolved_at - alert.timestamp).total_seconds() / 60
                if alert.resolved_at else 0
            )
            
            # Log resolution
            log_file = self.alert_log_dir / "alert_resolutions.log"
            resolution_entry = {
                "timestamp": alert.resolved_at.isoformat() if alert.resolved_at else datetime.utcnow().isoformat(),
                "alert_id": alert.id,
                "rule_id": alert.rule_id,
                "title": alert.title,
                "resolution_time_minutes": resolution_time,
                "acknowledged": alert.acknowledged,
                "escalated": alert.escalated
            }
            
            with open(log_file, "a") as f:
                f.write(json.dumps(resolution_entry) + "\n")
            
        except Exception as e:
            logger.error(f"Error sending resolution notification: {e}")
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return [asdict(alert) for alert in self.active_alerts.values()]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)
        
        # Count by severity
        critical_alerts = len([a for a in self.alert_history if a.severity == "critical"])
        warning_alerts = len([a for a in self.alert_history if a.severity == "warning"])
        
        # Count acknowledged and escalated
        acknowledged_alerts = len([a for a in self.alert_history if a.acknowledged])
        escalated_alerts = len([a for a in self.alert_history if a.escalated])
        
        # Calculate average resolution time
        resolved_alerts = [a for a in self.alert_history if a.resolved and a.resolved_at]
        avg_resolution_time = 0
        if resolved_alerts:
            total_resolution_time = sum(
                (a.resolved_at - a.timestamp).total_seconds() / 60
                for a in resolved_alerts
            )
            avg_resolution_time = total_resolution_time / len(resolved_alerts)
        
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
            "acknowledged_alerts": acknowledged_alerts,
            "escalated_alerts": escalated_alerts,
            "average_resolution_time_minutes": round(avg_resolution_time, 2),
            "alert_rules_count": len(self.alert_rules),
            "notification_channels_count": len([c for c in self.notification_channels.values() if c.enabled])
        }
    
    def add_alert_rule(self, rule: AlertRule) -> bool:
        """Add a new alert rule"""
        try:
            self.alert_rules[rule.id] = rule
            logger.info(f"Alert rule added: {rule.name} (ID: {rule.id})")
            return True
        except Exception as e:
            logger.error(f"Error adding alert rule: {e}")
            return False
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule"""
        try:
            if rule_id in self.alert_rules:
                del self.alert_rules[rule_id]
                logger.info(f"Alert rule removed: {rule_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing alert rule: {e}")
            return False


# Global instance
_alerting_service = None


def get_websocket_alerting_service() -> WebSocketAlertingService:
    """Get the global WebSocket alerting service instance"""
    global _alerting_service
    if _alerting_service is None:
        _alerting_service = WebSocketAlertingService()
    return _alerting_service